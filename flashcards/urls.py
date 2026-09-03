from django.urls import path

from . import views

urlpatterns = [
    path("", views.topic_practice, name="flashcards_topics"),
]
