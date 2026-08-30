from django.shortcuts import render

from blog.models import Post

from .models import Project


def home(request):
    projects = Project.objects.all()
    latest_posts = Post.objects.filter(status="published")[:3]
    return render(
        request,
        "portfolio/home.html",
        {
            "projects": projects,
            "latest_posts": latest_posts,
        },
    )
