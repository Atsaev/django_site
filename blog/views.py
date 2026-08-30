from django.db.models import F
from django.shortcuts import get_object_or_404, render

from portfolio.models import Project

from .models import Category, Challenge, JobSearchStats, Post
from .toc import build_toc

# Слаг рубрики «Путь» (транслитерация) — для хронологического таймлайна
PATH_CATEGORY_SLUG = 'put'


def post_list(request, category_slug=None):
    posts = Post.objects.filter(status='published')
    current = None
    if category_slug:
        current = get_object_or_404(Category, slug=category_slug)
        posts = posts.filter(category=current)

    # Рубрика «Путь» при обычном переходе — хронологический таймлайн
    # (самый ранний пост сверху, чтобы история читалась как история).
    # htmx-фильтр из ленты отдаёт обычный фрагмент.
    if current and current.slug == PATH_CATEGORY_SLUG and not request.headers.get('HX-Request'):
        timeline = posts.select_related('category').prefetch_related('tags').order_by('published_at', 'created_at')
        return render(request, 'blog/path_timeline.html', {
            'posts': timeline,
            'categories': Category.objects.all(),
            'current_category': current,
        })

    posts = posts.select_related('category').prefetch_related('tags')
    context = {
        'posts': posts,
        'categories': Category.objects.all(),
        'current_category': current,
        'active_challenge': Challenge.objects.filter(active=True).first(),
        'job_stats': _job_stats(),
    }
    # htmx-запрос: отдаём только фрагмент ленты (без обёртки страницы)
    if request.headers.get('HX-Request'):
        return render(request, 'blog/_post_list.html', context)
    return render(request, 'blog/post_list.html', context)


def _job_stats():
    """Статистика поиска работы — только если есть хоть одно ненулевое значение."""
    stats = JobSearchStats.objects.filter(pk=1).first()
    if not stats or not (stats.applications or stats.interviews or stats.offers):
        return None
    return stats


def post_detail(request, slug):
    post = get_object_or_404(Post, slug=slug, status='published')
    Post.objects.filter(pk=post.pk).update(views=F('views') + 1)
    toc, content_html = build_toc(post.content)

    project = None
    if post.project_slug:
        project = Project.objects.filter(slug=post.project_slug).first()

    return render(request, 'blog/post_detail.html', {
        'post': post,
        'toc': toc,
        'content_html': content_html,
        'related': related_posts(post),
        'project': project,
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
