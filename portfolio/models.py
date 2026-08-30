from django.db import models
from imagekit.models import ProcessedImageField
from imagekit.processors import ResizeToFill


class Project(models.Model):
    STATUS_CHOICES = [
        ('live', 'Live'),
        ('wip', 'In progress'),
    ]
    title = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    short_description = models.CharField(max_length=200)
    tech_stack = models.CharField(
        max_length=200,
        help_text='Через запятую: FastAPI, Postgres, Docker',
    )
    github_url = models.URLField(blank=True)
    demo_url = models.URLField(blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='live')
    cover_image = ProcessedImageField(
        upload_to='projects/',
        processors=[ResizeToFill(600, 400)],
        format='WEBP',
        options={'quality': 85},
        blank=True,
        null=True,
    )
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', '-created_at']

    def __str__(self):
        return self.title

    def tech_list(self):
        return [t.strip() for t in self.tech_stack.split(',') if t.strip()]
