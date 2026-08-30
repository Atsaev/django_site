from django.db.models import F
from django.shortcuts import get_object_or_404, render

from .models import Category, Post
from .toc import build_toc


def post_list(request, category_slug=None):
    posts = Post.objects.filter(status='published')
    current = None
    if category_slug:
        current = get_object_or_404(Category, slug=category_slug)
        posts = posts.filter(category=current)
    posts = posts.select_related('category').prefetch_related('tags')
    categories = Category.objects.all()
    context = {
        'posts': posts,
        'categories': categories,
        'current_category': current,
    }
    # htmx-запрос: отдаём только фрагмент ленты (без обёртки страницы)
    if request.headers.get('HX-Request'):
        return render(request, 'blog/_post_list.html', context)
    return render(request, 'blog/post_list.html', context)


def post_detail(request, slug):
    post = get_object_or_404(Post, slug=slug, status='published')
    Post.objects.filter(pk=post.pk).update(views=F('views') + 1)
    toc, content_html = build_toc(post.content)
    return render(request, 'blog/post_detail.html', {
        'post': post,
        'toc': toc,
        'content_html': content_html,
    })
