import random
import re
from datetime import date

from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django_ckeditor_5.fields import CKEditor5Field
from imagekit.models import ProcessedImageField
from imagekit.processors import ResizeToFill

from .translit import translit_slug

# Типы реакций и их эмодзи (порядок — порядок кнопок в блоке реакций)
REACTIONS_EMOJI = [
    ('like', '👍'),
    ('love', '❤️'),
    ('fire', '🔥'),
    ('rocket', '🚀'),
    ('dislike', '👎'),
]
REACTIONS = [key for key, _ in REACTIONS_EMOJI]


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
        # ровно один активный челлендж: сохранение активного выключает остальные.
        # exclude(pk=self.pk) — иначе повторное сохранение деактивирует сам себя
        # до того, как super().save() запишет изменения.
        if self.is_active:
            Challenge.objects.filter(is_active=True).exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)

    def clean(self):
        """Нельзя уменьшать челлендж ниже уже написанных дней: иначе посты
        выпадут из сетки дней (напр. день 32 при total_days 30)."""
        super().clean()
        if self.pk:
            max_written = (
                self.posts.filter(day_number__isnull=False)
                .aggregate(models.Max('day_number'))['day_number__max']
            )
            if max_written and self.total_days < max_written:
                raise ValidationError({
                    'total_days': (
                        f'Меньше нельзя: в челлендже уже написан пост с днём {max_written}. '
                        f'Максимум дней должен быть не меньше {max_written}.'
                    )
                })

    def _today(self) -> date:
        """Сегодня по локальной таймзоне (Europe/Moscow)."""
        return timezone.localtime().date()

    @property
    def current_day(self) -> int:
        """Календарный день челленджа сегодня (1-индекс от start_date).
        Может превышать total_days, если прошло больше дней, чем в челлендже."""
        return (self._today() - self.start_date).days + 1

    def finished(self) -> bool:
        """Период челленджа закончился (наступил день после total_days)."""
        return self.current_day > self.total_days

    @property
    def progress_percent(self) -> int:
        """Процент выполненных дней (по факту написанных постов), а не по календарю."""
        if self.total_days <= 0:
            return 0
        return round(self.done_count / self.total_days * 100)

    def days_left(self) -> int:
        """Сколько календарных дней осталось до конца челленджа."""
        return max(0, self.total_days - self.current_day)

    def _done_numbers(self) -> set:
        """Множество day_number, для которых есть опубликованный пост."""
        return set(
            self.posts.filter(status='published', day_number__isnull=False)
            .values_list('day_number', flat=True)
        )

    @property
    def done_count(self) -> int:
        return len(self._done_numbers())

    def days_grid(self):
        """Массив состояния каждого дня челленджа (по календарю Москвы).

        state для дня N:
        - 'done'  — N наступил и есть опубликованный пост с day_number == N
        - 'today' — N == current_day (сегодня, ещё можно написать)
        - 'missed'— N миновал, но поста в этот календарный день нет
        - 'future'— N ещё не наступил
        """
        done = self._done_numbers()
        today_n = self.current_day
        return [
            {
                'n': n,
                'state': (
                    'done' if n in done
                    else 'today' if n == today_n
                    else 'missed' if n < today_n
                    else 'future'
                ),
            }
            for n in range(1, self.total_days + 1)
        ]

    def status(self) -> str:
        """Вердикт: 'active' — идёт, 'done' — завершён, 'missed' — провален.

        done достигается и досрочно, если все дни уже закрыты постами;
        missed — если период закончился, но закрыты не все дни.
        """
        required = set(range(1, self.total_days + 1))
        if self._done_numbers() >= required:
            return 'done'
        if not self.finished():
            return 'active'
        return 'missed'


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
    """Рубрика поста: код, путь, проекты, дневник.

    description показывается как субтитр на странице-таймлайне рубрики.
    """
    name = models.CharField(max_length=50, unique=True, verbose_name='Название')
    slug = models.SlugField(unique=True, verbose_name='Слаг')
    description = models.TextField(blank=True, verbose_name='Описание')

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
    content = CKEditor5Field(
        'Текст поста',
        config_name='default',
        help_text='Картинки, вставленные через редактор, не отслеживаются автоматически. '
                  'Проверяйте вручную перед удалением файлов из медиа.',
    )
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
    cover_image = ProcessedImageField(
        upload_to='posts/',
        processors=[ResizeToFill(1200, 630)],
        format='WEBP',
        options={'quality': 85},
        blank=True,
        null=True,
        verbose_name='Обложка (для превью)',
        help_text='Картинка для превью при шаринге. Приоритетнее первой картинки из текста.',
    )
    tags = models.ManyToManyField(Tag, blank=True, related_name='posts', verbose_name='Теги')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='draft')
    # счётчики событий поиска работы, привязанные к дате поста
    applications_count = models.PositiveIntegerField(default=0, verbose_name='Откликов отправлено')
    interviews_count = models.PositiveIntegerField(default=0, verbose_name='Собеседований')
    offers_count = models.PositiveIntegerField(default=0, verbose_name='Офферов')
    views = models.PositiveIntegerField(default=0)
    published_at = models.DateField(blank=True, null=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-published_at', '-created_at']
        verbose_name = 'Пост'
        verbose_name_plural = 'Посты'

    def __str__(self):
        return self.title

    @property
    def has_job_events(self) -> bool:
        """Хоть одно ненулевое событие поиска работы на этом посте."""
        return bool(self.applications_count or self.interviews_count or self.offers_count)

    def get_absolute_url(self):
        return reverse('post_detail', args=[self.slug])

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = translit_slug(self.title)
        # day_number — календарный день от старта челленджа по дате создания (не счётчик).
        if self.challenge_id:
            created = timezone.localtime(self.created_at) if self.created_at else timezone.localtime()
            day = (created.date() - self.challenge.start_date).days + 1
            self.day_number = max(1, min(day, self.challenge.total_days))
        else:
            self.day_number = None
        super().save(*args, **kwargs)

    def clean(self):
        """День челленджа не вводится вручную — он считается в save() от created_at."""
        super().clean()

    _IMG_SRC_RE = re.compile(r'<img[^>]+src="([^"]+)"')

    def _first_image_src(self) -> str | None:
        m = self._IMG_SRC_RE.search(self.content or '')
        return m.group(1) if m else None

    def get_og_image(self) -> str | None:
        """Картинка для og:image: обложка или первая картинка из текста."""
        if self.cover_image:
            return self.cover_image.url
        return self._first_image_src()


class PostReaction(models.Model):
    """Одна реакция читателя на пост: тип + время. Счётчики считаются из неё."""
    post = models.ForeignKey(
        Post, on_delete=models.CASCADE, related_name='reactions', verbose_name='Пост',
    )
    reaction = models.CharField(
        max_length=20, choices=REACTIONS_EMOJI, verbose_name='Реакция',
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Когда')

    class Meta:
        verbose_name = 'Реакция'
        verbose_name_plural = 'Реакции'
        ordering = ['created_at']

    def __str__(self):
        return f'{self.post_id}:{self.reaction}'


def inflate_reactions(post, count: int) -> None:
    """Накрутка: случайные реакции (включая дизлайки) для поста."""
    PostReaction.objects.bulk_create([
        PostReaction(post=post, reaction=r) for r in random.choices(REACTIONS, k=count)
    ])
