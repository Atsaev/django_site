from datetime import date

from django.db import models
from django.utils.text import slugify
from django_ckeditor_5.fields import CKEditor5Field

from .translit import translit_slug


class Challenge(models.Model):
    """Челлендж: «День N из 30» — прогресс считается из дат, а не парсится из тегов."""
    title = models.CharField(max_length=200, verbose_name='Название')  # «30 дней после курса»
    slug = models.SlugField(unique=True, blank=True, verbose_name='Слаг')
    start_date = models.DateField(verbose_name='Дата старта')
    total_days = models.PositiveIntegerField(default=30, verbose_name='Всего дней')
    description = models.TextField(blank=True, verbose_name='Описание')
    is_active = models.BooleanField(default=True, verbose_name='Активен')

    class Meta:
        verbose_name = 'Челлендж'
        verbose_name_plural = 'Челленджи'
        ordering = ['-start_date']

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = translit_slug(self.title)
        super().save(*args, **kwargs)

    @property
    def current_day(self) -> int:
        delta = (date.today() - self.start_date).days + 1
        return max(0, min(delta, self.total_days))

    @property
    def progress_percent(self) -> int:
        return round(self.current_day / self.total_days * 100)

    def days_left(self) -> int:
        """Сколько дней осталось до конца челленджа."""
        return max(0, self.total_days - self.current_day)


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
    challenge = models.ForeignKey(
        Challenge, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='posts', verbose_name='Челлендж',
    )
    day_number = models.PositiveIntegerField(null=True, blank=True, verbose_name='День N')
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
        # автопростановка дня: следующий после последнего в этом челлендже
        if self.challenge_id and self.day_number is None:
            last = self.challenge.posts.aggregate(models.Max('day_number'))
            self.day_number = (last['day_number__max'] or 0) + 1
        super().save(*args, **kwargs)
