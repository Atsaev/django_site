from django.urls import path

from . import views
from .feeds import LatestPostsFeed

urlpatterns = [
    path("", views.post_list, name="post_list"),
    path("feed/", LatestPostsFeed(), name="blog_feed"),
    path("category/<str:category_slug>/", views.post_list, name="post_list_category"),
    path("<slug:slug>/", views.post_detail, name="post_detail"),
]
