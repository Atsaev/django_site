from django.db import models
from django.utils.text import slugify
from django_ckeditor_5.fields import CKEditor5Field

from .translit import translit_slug


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
