from datetime import date

from django.db import models
from django.utils.text import slugify
from django_ckeditor_5.fields import CKEditor5Field

from .translit import translit_slug


class Challenge(models.Model):
    """Активный челлендж: «День N из 30» на странице блога."""
    name = models.CharField(max_length=100, verbose_name='Название')
    start_date = models.DateField(verbose_name='Дата старта')
    days_total = models.PositiveIntegerField(default=30, verbose_name='Всего дней')
    active = models.BooleanField(default=True, verbose_name='Активен')

    class Meta:
        verbose_name = 'Челлендж'
        verbose_name_plural = 'Челленджи'

    def __str__(self):
        return self.name

    def day_number(self) -> int:
        days = (date.today() - self.start_date).days + 1
        return max(1, min(days, self.days_total))

    def progress(self) -> int:
        return round(self.day_number() / self.days_total * 100)


class JobSearchStats(models.Model):
    """Виджет поиска работы: отклики / собеседования / офферы."""
    applications = models.PositiveIntegerField(default=0, verbose_name='Откликов отправлено')
    interviews = models.PositiveIntegerField(default=0, verbose_name='Собеседований')
    offers = models.PositiveIntegerField(default=0, verbose_name='Офферов')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Обновлено')

    class Meta:
        verbose_name = 'Статистика поиска работы'
        verbose_name_plural = 'Статистика поиска работы'

    def __str__(self):
        return f'Отклики: {self.applications}, интервью: {self.interviews}, офферы: {self.offers}'

    @classmethod
    def get_singleton(cls) -> 'JobSearchStats':
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class Category(models.Model):
    """Рубрика поста: код, путь, проекты, дневник."""
    name = models.CharField(max_length=50, unique=True, verbose_name='Название')
    slug = models.SlugField(unique=True, verbose_name='Слаг')

    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = translit_slug(self.name)
        super().save(*args, **kwargs)


class Tag(models.Model):
    """Гибкая метка поста: Django, SQL, 30 дней, собеседование."""
    name = models.CharField(max_length=50, unique=True, verbose_name='Название')
    slug = models.SlugField(unique=True, verbose_name='Слаг')

    class Meta:
        verbose_name = 'Тег'
        verbose_name_plural = 'Теги'
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = translit_slug(self.name)
        super().save(*args, **kwargs)


class Post(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('published', 'Published'),
    ]
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True)
    excerpt = models.CharField(max_length=250, blank=True, help_text='Краткое описание для карточки в списке')
    content = CKEditor5Field('Текст поста', config_name='default')
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='posts', verbose_name='Категория',
    )
    project_slug = models.CharField(
        max_length=100, blank=True, verbose_name='Проект (слаг на главной)',
        help_text='Слаг проекта из /admin/portfolio/project/ — ссылка на его карточку на главной',
    )
    tags = models.ManyToManyField(Tag, blank=True, related_name='posts', verbose_name='Теги')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='draft')
    views = models.PositiveIntegerField(default=0)
    published_at = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-published_at', '-created_at']
        verbose_name = 'Пост'
        verbose_name_plural = 'Посты'

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = translit_slug(self.title)
        super().save(*args, **kwargs)
