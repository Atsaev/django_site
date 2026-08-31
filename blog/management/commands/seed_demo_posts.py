"""Демо-данные для локальной разработки: генерирует тестовые посты.

Запуск:  manage.py seed_demo_posts [--count 25] [--with-reactions]
Создаёт только опубликованные посты по категориям с тегами и датами.
Никогда не вызывается автоматически — только вручную, локально.
"""
import random
from datetime import date, timedelta

from django.core.management.base import BaseCommand

from blog.models import Category, Post, Tag, inflate_reactions
from blog.translit import translit_slug

_TEMPLATES = [
    'Разбор {topic}: от идеи до деплоя',
    'День {n}: {topic} на практике',
    'Почему {topic} — это не так страшно, как кажется',
    '{topic}: подводные камни, которые я нашёл',
    'Как я ускорил {topic} в три раза',
    'Заметки о {topic} после первой недели',
    '{topic} для себя: что бы я сделал иначе',
    'Чек-лист по {topic} перед релизом',
]
_TOPICS = [
    'FastAPI', 'Django ORM', 'PostgreSQL', 'Docker', 'htmx', 'Celery',
    'Redis', 'Nginx', 'Gunicorn', 'LangGraph', 'Pydantic', 'SQL-индексы',
    'CI/CD', 'Whitenoise', 'imagekit', 'TDD',
]

_TAGS = ['Python', 'Django', 'Docker', 'SQL', '30 дней', 'собеседование', 'проекты']


def _content(title: str) -> str:
    return (
        '<h2>Введение</h2>'
        f'<p>Решил разобраться с {title} и зафиксировать выводы здесь.</p>'
        '<h2>Что делал</h2>'
        '<ul><li>построил минимальный пример;</li><li>замерил, что было «до»;</li>'
        '<li>поправил очевидное и неочевидное;</li></ul>'
        '<h2>Код</h2>'
        '<pre><code class="language-python">def main():\n    return "hello"</code></pre>'
        '<h2>Выводы</h2>'
        '<p>Главное — не останавливаться на первом рабочем варианте.</p>'
    )


class Command(BaseCommand):
    help = 'Создать тестовые посты для локальной разработки'

    def add_arguments(self, parser):
        parser.add_argument('--count', type=int, default=25)
        parser.add_argument('--with-reactions', action='store_true', help='Накрутить случайные реакции')

    def handle(self, *args, **options):
        count = options['count']
        with_reactions = options['with_reactions']

        categories = {c.slug: c for c in Category.objects.all()}
        if not categories:
            self.stderr.write('Категории не найдены — сначала примени миграции.')
            return

        tags = {}
        for name in _TAGS:
            tag, _ = Tag.objects.get_or_create(name=name)
            tags[name] = tag

        start = date.today() - timedelta(days=count)
        created = 0
        for i in range(count):
            title = random.choice(_TEMPLATES).format(
                topic=random.choice(_TOPICS), n=i + 1,
            )
            slug = translit_slug(title)
            if Post.objects.filter(slug=slug).exists():
                slug = f'{slug}-{i}'[:50]
            post = Post.objects.create(
                title=title,
                slug=slug,
                category=random.choice(list(categories.values())),
                status='published',
                published_at=start + timedelta(days=i),
                excerpt=f'Заметка #{i + 1}: {title}',
                content=_content(title),
            )
            post.tags.add(*random.sample(list(tags.values()), k=random.randint(1, 3)))
            if with_reactions:
                inflate_reactions(post, random.randint(0, 20))
            created += 1

        total = Post.objects.filter(status='published').count()
        self.stdout.write(self.style.SUCCESS(f'Создано постов: {created}. Всего опубликовано: {total}.'))
