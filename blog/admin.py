from typing import ClassVar

from django.contrib import admin

from .models import Post


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ("title", "status", "views", "published_at", "created_at")
    list_editable = ("status",)
    list_filter = ("status",)
    search_fields = ("title", "tags")
    prepopulated_fields: ClassVar[dict] = {"slug": ("title",)}
