# Backfill: слаг челленджа из title (транслитерация), если он пуст.
# Отдельная миграция — RunPython нельзя смешивать с ALTER TABLE на Postgres.

from django.db import migrations
from django.utils.text import slugify

# копия карты из blog/translit.py — миграция должна быть самодостаточной
_TRANSLIT = {
    'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo',
    'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
    'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
    'ф': 'f', 'х': 'kh', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'shch',
    'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
}


def _translit(text: str) -> str:
    return slugify(''.join(_TRANSLIT.get(ch, ch) for ch in text.lower()))


def backfill_challenge_slugs(apps, schema_editor):
    Challenge = apps.get_model('blog', 'Challenge')
    for obj in Challenge.objects.all():
        if obj.slug:
            continue
        base = _translit(obj.title) or 'challenge'
        obj.slug = base
        i = 2
        while Challenge.objects.exclude(pk=obj.pk).filter(slug=obj.slug).exists():
            obj.slug = f'{base}-{i}'
            i += 1
        obj.save(update_fields=['slug'])


class Migration(migrations.Migration):

    dependencies = [
        ('blog', '0007_challenge_refactor'),
    ]

    operations = [
        migrations.RunPython(backfill_challenge_slugs, migrations.RunPython.noop),
    ]
