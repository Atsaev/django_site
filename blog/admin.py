from typing import ClassVar

from django.contrib import admin

from .models import Category, Challenge, JobSearchStats, Post, Tag


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Challenge)
class ChallengeAdmin(admin.ModelAdmin):
    list_display = ("title", "start_date", "total_days", "is_active")
    list_editable = ("is_active",)
    prepopulated_fields = {"slug": ("title",)}


@admin.register(JobSearchStats)
class JobSearchStatsAdmin(admin.ModelAdmin):
    list_display = ("applications", "interviews", "offers", "updated_at")

    def has_add_permission(self, request):
        return not JobSearchStats.objects.exists()


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "challenge", "status", "views", "published_at")
    list_editable = ("status",)
    list_filter = ("status", "category", "challenge")
    search_fields = ("title", "tags__name")
    filter_horizontal = ("tags",)
    prepopulated_fields: ClassVar[dict] = {"slug": ("title",)}
