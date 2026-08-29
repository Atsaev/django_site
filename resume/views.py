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
    from playwright.sync_api import sync_playwright

    context = _get_resume_context()

    # делаем абсолютный URL для фото, если оно есть
    if context["profile"] and context["profile"].photo:
        context["photo_url"] = request.build_absolute_uri(context["profile"].photo.url)
    else:
        context["photo_url"] = None

    html_string = render_to_string("resume/resume_pdf.html", context)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.set_content(html_string, wait_until="networkidle")
        pdf_bytes = page.pdf(format="A4", print_background=True, margin={"top": "20px", "bottom": "20px"})
        browser.close()

    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="atsaev_resume.pdf"'
    return response
