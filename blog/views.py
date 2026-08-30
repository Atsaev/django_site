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
        'related': related_posts(post),
    })


def related_posts(post: Post, limit: int = 3) -> list[Post]:
    """Посты той же рубрики; при нехватке — по общим тегам."""
    qs = (
        Post.objects.filter(status='published')
        .exclude(pk=post.pk)
        .select_related('category')
        .prefetch_related('tags')
    )
    result: list[Post] = []

    if post.category_id:
        result = list(qs.filter(category_id=post.category_id)[:limit])

    if len(result) < limit:
        taken = {post.pk, *(p.pk for p in result)}
        tag_ids = list(post.tags.values_list('pk', flat=True))
        if tag_ids:
            by_tags = (
                qs.filter(tags__in=tag_ids)
                .exclude(pk__in=taken)
                .distinct()[: limit - len(result)]
            )
            result += list(by_tags)

    return result
