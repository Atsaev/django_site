from typing import ClassVar

from django.contrib import admin

from .models import Category, Post, Tag


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "status", "views", "published_at")
    list_editable = ("status",)
    list_filter = ("status", "category")
    search_fields = ("title", "tags__name")
    filter_horizontal = ("tags",)
    prepopulated_fields: ClassVar[dict] = {"slug": ("title",)}
