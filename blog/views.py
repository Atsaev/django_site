from django.db.models import Count, F, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from portfolio.models import Project

from .models import REACTIONS_EMOJI, Category, Challenge, JobSearchStats, Post, PostReaction
from .toc import build_toc


def post_list(request, category_slug=None):
    posts = Post.objects.filter(status='published')
    current = None
    if category_slug:
        current = get_object_or_404(Category, slug=category_slug)
        posts = posts.filter(category=current)

    query = request.GET.get('q', '').strip()
    can_timeline = bool(current) and posts.count() >= 2
    if query:
        posts = posts.filter(
            Q(title__icontains=query)
            | Q(excerpt__icontains=query)
            | Q(content__icontains=query)
            | Q(tags__name__icontains=query)
        ).distinct()

    posts = posts.select_related('category').prefetch_related('tags')
    context = {
        'posts': posts,
        'categories': Category.objects.all(),
        'current_category': current,
        'can_timeline': can_timeline,
        'query': query,
        'active_challenge': Challenge.objects.filter(is_active=True).first(),
        'job_stats': _job_stats(),
    }
    # htmx-запрос: отдаём только фрагмент ленты (без обёртки страницы)
    if request.headers.get('HX-Request'):
        return render(request, 'blog/_post_list.html', context)
    return render(request, 'blog/post_list.html', context)


def category_timeline(request, category_slug):
    """Хронологический таймлайн любой рубрики: от ранних постов к новым.

    Правило сортировки: строго по дате публикации (published_at) по
    возрастанию — это хронология событий, а не порядок написания,
    поэтому бэкдейт даты осознанно переставляет пост в истории.
    При равных датах порядок стабилизирует created_at.
    Используется и для «Пути» (/blog/path/), и для любой другой рубрики
    (/blog/timeline/<slug>/): разбор фреймворка, дневник и т.д.
    """
    category = get_object_or_404(Category, slug=category_slug)
    posts = (
        Post.objects.filter(status='published', category=category)
        .select_related('category')
        .prefetch_related('tags')
        .order_by('published_at', 'created_at')
    )
    return render(request, 'blog/category_timeline.html', {
        'category': category,
        'posts': posts,
        'categories': Category.objects.all(),
    })


def _job_stats():
    """Статистика поиска работы — только если есть хоть одно ненулевое значение."""
    stats = JobSearchStats.objects.filter(pk=1).first()
    if not stats or not (stats.applications or stats.interviews or stats.offers):
        return None
    return stats


def challenge_detail(request, slug):
    """Страница челленджа: прогресс-бар + таймлайн постов.

    Правило сортировки: строго по day_number (День 1 → 2 → …), дата
    публикации на порядок не влияет — она только для отображения.
    При равных day_number порядок стабилизирует created_at, чтобы
    между прогонами не было недетерминированного порядка.
    """
    challenge = get_object_or_404(Challenge, slug=slug)
    posts = (
        challenge.posts.filter(status='published')
        .select_related('category')
        .prefetch_related('tags')
        .order_by('day_number', 'created_at')
    )
    return render(request, 'blog/challenge_detail.html', {
        'challenge': challenge,
        'posts': posts,
    })


def _reaction_list(post: Post) -> list[tuple[str, str, int]]:
    """Список (ключ, эмодзи, счётчик) для блока реакций поста."""
    counts = {
        r['reaction']: r['count']
        for r in post.reactions.values('reaction').annotate(count=Count('id'))
    }
    return [(key, emoji, counts.get(key, 0)) for key, emoji in REACTIONS_EMOJI]


@require_POST
def react(request, slug):
    """Добавить/снять реакцию на пост. Возвращает обновлённый блок реакций."""
    post = get_object_or_404(Post, slug=slug, status='published')
    reaction = request.POST.get('reaction', '')
    action = request.POST.get('action', 'add')
    if reaction not in {key for key, _ in REACTIONS_EMOJI}:
        return JsonResponse({'error': 'unknown reaction'}, status=400)
    if action == 'add':
        PostReaction.objects.create(post=post, reaction=reaction)
    elif action == 'remove':
        first = PostReaction.objects.filter(post=post, reaction=reaction).order_by('pk').first()
        if first:
            first.delete()
    else:
        return JsonResponse({'error': 'unknown action'}, status=400)
    return render(request, 'blog/_reactions.html', {
        'post': post,
        'reaction_list': _reaction_list(post),
    })


def post_detail(request, slug):
    post = get_object_or_404(Post, slug=slug, status='published')
    Post.objects.filter(pk=post.pk).update(views=F('views') + 1)
    toc, content_html = build_toc(post.content)

    project = None
    if post.project_slug:
        project = Project.objects.filter(slug=post.project_slug).first()

    og_image = post.get_og_image()
    if og_image:
        og_image = request.build_absolute_uri(og_image)

    return render(request, 'blog/post_detail.html', {
        'post': post,
        'toc': toc,
        'content_html': content_html,
        'related': related_posts(post),
        'project': project,
        'reaction_list': _reaction_list(post),
        'og_image': og_image,
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
