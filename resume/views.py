from pathlib import Path

from django.http import HttpResponse
from django.shortcuts import render
from django.template.loader import render_to_string

from portfolio.models import Project

from .models import EducationItem, Experience, Language, Profile, SkillCategory


def _get_resume_context():
    return {
        "profile": Profile.objects.first(),
        "experiences": Experience.objects.all(),
        "skill_categories": SkillCategory.objects.prefetch_related("skills"),
        "education": EducationItem.objects.all(),
        "languages": Language.objects.all(),
        "projects": Project.objects.filter(status="live"),
    }


def resume(request):
    return render(request, "resume/resume.html", _get_resume_context())


def resume_pdf(request):
    from weasyprint import HTML  # импорт ленивый: pango нужен только для PDF

    context = _get_resume_context()

    # фото подставляем локальным файлом, чтобы WeasyPrint рендерил без сети
    if context["profile"] and context["profile"].photo:
        context["photo_url"] = Path(context["profile"].photo.path).as_uri()
    else:
        context["photo_url"] = None

    html_string = render_to_string("resume/resume_pdf.html", context)
    pdf_bytes = HTML(string=html_string).write_pdf()

    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="atsaev_resume.pdf"'
    return response
