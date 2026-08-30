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


def translit_slugs(apps, schema_editor):
    for model_name in ('Category', 'Tag'):
        Model = apps.get_model('blog', model_name)
        for obj in Model.objects.all():
            if obj.slug and obj.slug.isascii():
                continue  # уже латиница — не трогаем
            base = _translit(obj.name) or 'item'
            slug = base
            i = 2
            while Model.objects.exclude(pk=obj.pk).filter(slug=slug).exists():
                slug = f'{base}-{i}'
                i += 1
            obj.slug = slug
            obj.save(update_fields=['slug'])


class Migration(migrations.Migration):

    dependencies = [
        ('blog', '0004_remove_post_tags_legacy'),
    ]

    operations = [
        migrations.RunPython(translit_slugs, migrations.RunPython.noop),
    ]
