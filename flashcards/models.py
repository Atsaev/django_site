from django.db import models
from django.urls import reverse


class Topic(models.Model):
    """Тема набора карточек, например: FastAPI, Django, Python, ООП."""

    name = models.CharField("Название", max_length=80, unique=True)
    slug = models.SlugField("Слаг", unique=True)
    description = models.CharField(
        "Описание", max_length=200, blank=True,
        help_text="Короткая подпись под названием темы",
    )
    order = models.PositiveIntegerField("Порядок", default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order", "name"]
        verbose_name = "Тема"
        verbose_name_plural = "Темы"

    def __str__(self) -> str:
        return self.name

    def get_absolute_url(self) -> str:
        return reverse("flashcards_topic", args=[self.slug])

    def card_count(self) -> int:
        return self.cards.count()

    card_count.short_description = "Карточек"


class Card(models.Model):
    """Флеш-карточка: вопрос на лицевой стороне, ответ на обороте."""

    topic = models.ForeignKey(
        Topic,
        on_delete=models.CASCADE,
        related_name="cards",
        verbose_name="Тема",
    )
    question = models.TextField("Вопрос")
    answer = models.TextField("Ответ")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["id"]
        verbose_name = "Карточка"
        verbose_name_plural = "Карточки"

    def __str__(self) -> str:
        return self.question[:80]
