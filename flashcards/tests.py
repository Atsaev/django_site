from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from .models import Card, Topic


class FlashcardViewsTests(TestCase):
    def setUp(self):
        self.python = Topic.objects.create(
            name="Python", slug="python", description="Основы Python", order=1
        )
        self.django = Topic.objects.create(
            name="Django", slug="django", description="Django-фреймворк", order=2
        )
        Card.objects.create(topic=self.python, question="Что такое GIL?", answer="Глобальная блокировка")
        Card.objects.create(topic=self.python, question="Как объявить список?", answer="arr = []")
        Card.objects.create(topic=self.django, question="Что делает ORM?", answer="Мост CMS/БД")

    def test_page_lists_only_topics_with_cards(self):
        # тема без карточек в списке выбора не показывается
        Topic.objects.create(name="Empty", slug="empty", order=3)
        resp = self.client.get(reverse("flashcards_topics"))
        self.assertEqual(resp.status_code, 200)
        names = [t.name for t in resp.context["topics"]]
        self.assertIn("Python", names)
        self.assertNotIn("Empty", names)

    def test_deck_includes_cards_of_all_topics(self):
        resp = self.client.get(reverse("flashcards_topics"))
        self.assertEqual(resp.status_code, 200)
        deck = resp.context["deck"]
        self.assertEqual(len(deck), 3)
        topic_names = {d["topic"] for d in deck}
        self.assertEqual(topic_names, {"Python", "Django"})

    def test_page_marks_render_and_json(self):
        resp = self.client.get(reverse("flashcards_topics"))
        self.assertContains(resp, "topic-check")
        self.assertContains(resp, "deck-data")
        self.assertContains(resp, "startBtn")

    def test_deck_limited(self):
        # больше 500 карточек не отдают одной простынёй — обрезаем
        for i in range(505):
            Card.objects.create(topic=self.python, question=f"q{i}", answer="a")
        resp = self.client.get(reverse("flashcards_topics"))
        self.assertEqual(resp.status_code, 200)
        self.assertLessEqual(len(resp.context["deck"]), 500)


class SeedCommandTests(TestCase):
    def test_seed_is_idempotent(self):
        # первый запуск
        call_command("seed_flashcards")
        topics_1 = Topic.objects.count()
        cards_1 = Card.objects.count()
        self.assertGreaterEqual(topics_1, 7)
        self.assertGreater(cards_1, 90)

        # повторный запуск не создаёт дубликатов
        call_command("seed_flashcards")
        self.assertEqual(Topic.objects.count(), topics_1)
        self.assertEqual(Card.objects.count(), cards_1)
        # карточки связаны только с корректными темами
        self.assertEqual(Card.objects.filter(topic__isnull=True).count(), 0)
