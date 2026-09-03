from datetime import date

from django.core.exceptions import ValidationError
from django.db import models
from django_ckeditor_5.fields import CKEditor5Field
from imagekit.models import ProcessedImageField
from imagekit.processors import ResizeToFill


class Profile(models.Model):
    EMPLOYMENT_CHOICES = [
        ("open_to_work", "Рассматриваю предложения"),
        ("actively_looking", "В активном поиске"),
        ("not_looking", "Не ищу работу"),
    ]

    name = models.CharField(max_length=100)
    role = models.CharField(max_length=150)
    location = models.CharField(max_length=100, default="Россия")
    employment_status = models.CharField(
        max_length=20, choices=EMPLOYMENT_CHOICES, default="open_to_work"
    )
    about = CKEditor5Field("О себе", config_name="default")
    photo = ProcessedImageField(
        upload_to="resume/",
        processors=[ResizeToFill(300, 300)],
        format="WEBP",
        options={"quality": 90},
        blank=True,
        null=True,
    )
    email = models.EmailField()
    telegram = models.CharField(max_length=100, blank=True)
    github = models.CharField(max_length=100, blank=True)

    class Meta:
        verbose_name = "Профиль"
        verbose_name_plural = "Профиль"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.pk and Profile.objects.exists():
            raise ValidationError(
                "Может существовать только один профиль. Отредактируйте существующий."
            )
        super().save(*args, **kwargs)


class Experience(models.Model):
    """Опыт работы. Период формируется автоматически из start/end дат."""

    _MONTH_ABBR = [
        "Янв", "Фев", "Мар", "Апр", "Май", "Июн",
        "Июл", "Авг", "Сен", "Окт", "Ноя", "Дек",
    ]

    company = models.CharField(max_length=150)
    position = models.CharField(max_length=200)
    location = models.CharField(max_length=100, blank=True)
    start_date = models.DateField(verbose_name="Дата начала")
    end_date = models.DateField(
        verbose_name="Дата окончания",
        blank=True,
        null=True,
        help_text="Не заполняйте, если работаете по настоящее время",
    )
    description = CKEditor5Field("Описание", config_name="default", blank=True)
    tech_stack = models.CharField(max_length=300, blank=True, help_text="Через запятую")
    is_dev_role = models.BooleanField(
        default=True, help_text="False — для не-IT ролей (продажи и т.п.)"
    )
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "-start_date"]
        verbose_name = "Опыт работы"
        verbose_name_plural = "Опыт работы"

    def __str__(self):
        return f"{self.position} — {self.company}"

    def tech_list(self):
        return [t.strip() for t in self.tech_stack.split(",") if t.strip()]

    @property
    def period_text(self) -> str:
        """«Мар 2025 — настоящее время» либо «Ноя 2022 — Фев 2024»."""
        start = self._format_month(self.start_date)
        if self.end_date:
            return f"{start} — {self._format_month(self.end_date)}"
        return f"{start} — настоящее время"

    @staticmethod
    def _format_month(date: date) -> str:
        return f"{Experience._MONTH_ABBR[date.month - 1]} {date.year}"

    def clean(self):
        if self.end_date and self.start_date and self.end_date <= self.start_date:
            raise ValidationError(
                {"end_date": "Дата окончания должна быть позже даты начала."}
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class SkillCategory(models.Model):
    title = models.CharField(max_length=100)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]
        verbose_name = "Категория навыков"
        verbose_name_plural = "Категории навыков"

    def __str__(self):
        return self.title


class Skill(models.Model):
    category = models.ForeignKey(
        SkillCategory, on_delete=models.CASCADE, related_name="skills"
    )
    name = models.CharField(max_length=50)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]
        verbose_name = "Навык"
        verbose_name_plural = "Навыки"

    def __str__(self):
        return self.name


class EducationItem(models.Model):
    title = models.CharField(max_length=200)
    place = models.CharField(max_length=200, blank=True)
    date_text = models.CharField(max_length=50)
    description = models.CharField(max_length=300, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]
        verbose_name = "Образование"
        verbose_name_plural = "Образование"

    def __str__(self):
        return self.title


class Language(models.Model):
    name = models.CharField(max_length=50)
    level = models.CharField(
        max_length=100, help_text="Например: Родной, B2 — Средне-продвинутый"
    )
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]
        verbose_name = "Язык"
        verbose_name_plural = "Языки"

    def __str__(self):
        return f"{self.name} ({self.level})"
