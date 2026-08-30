# Backfill: сохранить текущий субтитр «Пути» как описание категории.
# После этого текст можно менять в админке — он больше не зашит в шаблоне.

from django.db import migrations


def backfill_path_description(apps, schema_editor):
    Category = apps.get_model('blog', 'Category')
    path = Category.objects.filter(slug='put').first()
    if path and not path.description:
        path.description = (
            'Хронология поиска работы: от первого отклика до оффера. '
            'Сверху — самое начало пути.'
        )
        path.save(update_fields=['description'])


class Migration(migrations.Migration):

    dependencies = [
        ('blog', '0009_category_description'),
    ]

    operations = [
        migrations.RunPython(backfill_path_description, migrations.RunPython.noop),
    ]
