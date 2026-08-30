import re
from datetime import datetime, time

from django.contrib.syndication.views import Feed
from django.urls import reverse

from .models import Post

_TAG_RE = re.compile(r'<[^>]+>')


def _plain_text(html: str) -> str:
    """Грубое извлечение текста из HTML-контента поста."""
    text = _TAG_RE.sub(' ', html or '')
    return re.sub(r'\s+', ' ', text).strip()


class LatestPostsFeed(Feed):
    title = 'atsaev-dev.ru — блог'
    link = '/blog/'
    description = 'Заметки Python-разработчика: код, путь, проекты.'

    def items(self):
        return (
            Post.objects.filter(status='published')
            .select_related('category')
            .prefetch_related('tags')[:20]
        )

    def item_title(self, item):
        return item.title

    def item_description(self, item):
        return item.excerpt or _plain_text(item.content)[:300]

    def item_pubdate(self, item):
        if not item.published_at:
            return None
        return datetime.combine(item.published_at, time.min)

    def item_categories(self, item):
        categories = [item.category.name] if item.category else []
        categories += [tag.name for tag in item.tags.all()]
        return categories

    def item_link(self, item):
        return reverse('post_detail', args=[item.slug])
