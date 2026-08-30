from django.db import migrations
from django.utils.text import slugify

DEFAULT_CATEGORIES = ['Код', 'Путь', 'Проекты', 'Дневник']


def migrate_tags(apps, schema_editor):
    Category = apps.get_model('blog', 'Category')
    Tag = apps.get_model('blog', 'Tag')
    Post = apps.get_model('blog', 'Post')

    # дефолтные рубрики
    for name in DEFAULT_CATEGORIES:
        Category.objects.get_or_create(
            name=name, defaults={'slug': slugify(name, allow_unicode=True)}
        )

    path_category = Category.objects.filter(slug='путь').first()

    # перенос строковых тегов из tags_legacy в M2M
    for post in Post.objects.all():
        raw = post.tags_legacy or ''
        names = [t.strip() for t in raw.split(',') if t.strip()]
        for name in names:
            tag, _ = Tag.objects.get_or_create(
                name=name, defaults={'slug': slugify(name, allow_unicode=True)}
            )
            post.tags.add(tag)

        # эвристика: челлендж-посты -> рубрика «Путь»
        if path_category and any('челлендж' in n.lower() or 'путь' in n.lower() for n in names):
            post.category = path_category
            post.save(update_fields=['category'])


class Migration(migrations.Migration):

    dependencies = [
        ('blog', '0002_category_tag_rename_post_tags'),
    ]

    operations = [
        migrations.RunPython(migrate_tags, migrations.RunPython.noop),
    ]
