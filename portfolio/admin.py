from typing import ClassVar

from django.contrib import admin

from .models import Project


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("title", "status", "order", "created_at")
    list_editable = ("order", "status")
    prepopulated_fields: ClassVar[dict] = {"slug": ("title",)}
    list_filter = ("status",)
    search_fields = ("title", "tech_stack")
