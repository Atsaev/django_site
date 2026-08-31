from django.contrib import admin

from .models import EducationItem, Experience, Language, Profile, Skill, SkillCategory


class SkillInline(admin.TabularInline):
    model = Skill
    extra = 1


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("name", "role", "employment_status")

    def has_add_permission(self, request):
        return not Profile.objects.exists()


@admin.register(Experience)
class ExperienceAdmin(admin.ModelAdmin):
    list_display = ("position", "company", "period_text", "is_dev_role", "order")
    list_editable = ("order", "is_dev_role")
    list_filter = ("is_dev_role",)


@admin.register(SkillCategory)
class SkillCategoryAdmin(admin.ModelAdmin):
    list_display = ("title", "order")
    list_editable = ("order",)
    inlines = [SkillInline]


@admin.register(EducationItem)
class EducationItemAdmin(admin.ModelAdmin):
    list_display = ("title", "place", "date_text", "order")
    list_editable = ("order",)


@admin.register(Language)
class LanguageAdmin(admin.ModelAdmin):
    list_display = ("name", "level", "order")
    list_editable = ("level", "order")
