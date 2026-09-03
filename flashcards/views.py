from django.db.models import Count
from django.shortcuts import render

from .models import Card, Topic


def topic_practice(request):
    """Страница тренировки: выбор одной/нескольких/всех тем, затем карточки.

    Все карточки отдаются единым JSON в `deck-data`, а JS на клиенте
    фильтрует их по выбранным темам и перемешивает — сервер не дёргается
    между карточками, пока пользователь тренируется.
    """
    topics = (
        Topic.objects.annotate(n_cards=Count("cards"))
        .filter(n_cards__gt=0)
        .order_by("order", "name")
    )
    all_cards = list(
        Card.objects.order_by("topic__order", "topic__name", "id")[:500]
    )
    deck = [
        {
            "question": c.question,
            "answer": c.answer,
            "topic": str(c.topic),
            "topic_id": c.topic_id,
        }
        for c in all_cards
    ]
    return render(
        request,
        "flashcards/topic_list.html",
        {
            "topics": topics,
            "deck": deck,
            "total_cards": len(deck),
        },
    )
