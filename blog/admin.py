from typing import ClassVar

from django import forms
from django.contrib import admin
from django.db.models import Count

from .models import REACTIONS_EMOJI, Category, Challenge, JobSearchStats, Post, PostReaction, Tag
from .models import inflate_reactions


class PostAdminForm(forms.ModelForm):
    """Форма поста + поля накрутки реакций (в модель не сохраняются)."""
    inflate_reactions = forms.BooleanField(
        required=False,
        label='Накрутить реакции',
        help_text='Добавить случайные реакции (включая дизлайки) при сохранении',
    )
    inflate_count = forms.IntegerField(
        required=False, min_value=0, initial=0,
        label='Сколько реакций',
        help_text='Повторное сохранение с отмеченным чекбоксом добавит ещё',
    )

    class Meta:
        model = Post
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # при редактировании показываем текущие счётчики рядом с чекбоксом,
        # чтобы не накрутить поверх уже собранных реакций
        if self.instance.pk:
            counts = dict(
                self.instance.reactions.values('reaction')
                .annotate(count=Count('id')).values_list('reaction', 'count')
            )
            summary = ' '.join(f'{emoji} {counts.get(key, 0)}' for key, emoji in REACTIONS_EMOJI)
            self.fields['inflate_reactions'].help_text = (
                f'Сейчас: {summary}. Добавить случайные реакции (включая дизлайки) при сохранении.'
            )


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
    form = PostAdminForm
    actions = ["reset_reactions"]
    list_display = ("title", "category", "challenge", "status", "views", "published_at")
    list_editable = ("status",)
    list_filter = ("status", "category", "challenge")
    search_fields = ("title", "tags__name")
    filter_horizontal = ("tags",)
    prepopulated_fields: ClassVar[dict] = {"slug": ("title",)}

    @admin.action(description='Сбросить реакции у выбранных постов')
    def reset_reactions(self, request, queryset):
        deleted = PostReaction.objects.filter(post__in=queryset).delete()[0]
        self.message_user(request, f'Реакции удалены: {deleted}.')

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if form.cleaned_data.get('inflate_reactions'):
            count = form.cleaned_data.get('inflate_count') or 0
            if count > 0:
                inflate_reactions(obj, count)
