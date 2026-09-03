from django.contrib import admin

from .models import Card, Topic


class CardInline(admin.TabularInline):
    model = Card
    extra = 3
    fields = ("question", "answer")


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ("name", "description", "order", "card_count")
    list_editable = ("order",)
    prepopulated_fields = {"slug": ("name",)}
    inlines = [CardInline]


@admin.register(Card)
class CardAdmin(admin.ModelAdmin):
    list_display = ("question", "topic", "updated_at")
    list_filter = ("topic",)
    search_fields = ("question", "answer")
    list_select_related = ("topic",)
