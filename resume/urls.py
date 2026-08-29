from django.urls import path

from . import views

urlpatterns = [
    path("", views.resume, name="resume"),
    path("pdf/", views.resume_pdf, name="resume_pdf")
]
