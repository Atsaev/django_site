from io import BytesIO
from tempfile import mkdtemp

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from resume.models import Profile


def _png(name='img.png', color='red'):
    buf = BytesIO()
    Image.new('RGB', (300, 300), color).save(buf, 'PNG')
    return SimpleUploadedFile(name, buf.getvalue(), content_type='image/png')


class ProfileAdminTests(TestCase):
    """Воспроизводит реальное поведение админ-формы профиля."""

    def setUp(self):
        self.admin = User.objects.create_superuser('admin', 'a@a.ru', 'x')
        self.client.force_login(self.admin)
        # изолированный pk — в тестовой БД могут уже быть Profile из синглтона
        self.profile = Profile.objects.create(
            pk=5001,
            name='Тест', role='Backend', location='Москва',
            about='<p>о себе</p>', email='t@t.ru',
        )

    def _edit_url(self):
        return reverse('admin:resume_profile_change', args=[self.profile.pk])

    @override_settings(MEDIA_ROOT=mkdtemp())
    def test_replace_photo_directly_without_clear(self):
        """Замена фото одним шагом: выбрать новый файл -> сохранить (без 'очистить')."""
        self.profile.photo = _png('one.png')
        self.profile.save()
        old_name = self.profile.photo.name
        self.assertTrue(self.profile.photo.storage.exists(old_name))

        # POST той же формы с НОВЫМ файлом (нет _clear checkbox'а)
        new_photo = _png('two.png', 'blue')
        response = self.client.post(self._edit_url(), {
            'name': self.profile.name,
            'role': self.profile.role,
            'location': self.profile.location,
            'employment_status': self.profile.employment_status,
            'about': self.profile.about,
            'email': self.profile.email,
            'photo': new_photo,
            '_save': 'Save',
        })
        self.assertRedirects(response, reverse('admin:resume_profile_changelist'))

        self.profile.refresh_from_db()
        self.assertTrue(self.profile.photo)                      # новый файл сохранён
        self.assertNotEqual(self.profile.photo.name, old_name)   # имя изменилось
        self.assertFalse(self.profile.photo.storage.exists(old_name))  # старый физически удалён

    @override_settings(MEDIA_ROOT=mkdtemp())
    def test_delete_profile_cleans_photo(self):
        """Удаление профиля из админки должно чистить photo и с диска."""
        self.profile.photo = _png('del.png')
        self.profile.save()
        name = self.profile.photo.name
        self.assertTrue(self.profile.photo.storage.exists(name))

        response = self.client.post(
            reverse('admin:resume_profile_delete', args=[self.profile.pk]),
            {'post': 'yes'},
        )
        self.assertRedirects(response, reverse('admin:resume_profile_changelist'))
        self.assertFalse(Profile.objects.filter(pk=self.profile.pk).exists())
        self.assertFalse(self.profile.photo.storage.exists(name))  # файл удалён с диска
