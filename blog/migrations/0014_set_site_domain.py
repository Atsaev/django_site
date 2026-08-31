# Настройка домена сайта для sitemap.xml (django.contrib.sites).
# Ставим atsaev-dev.ru вместо дефолтного example.com.

from django.db import migrations


def set_site_domain(apps, schema_editor):
    Site = apps.get_model('sites', 'Site')
    Site.objects.update_or_create(
        id=1,
        defaults={'domain': 'atsaev-dev.ru', 'name': 'atsaev-dev.ru'},
    )


class Migration(migrations.Migration):

    dependencies = [
        ('blog', '0013_alter_post_published_at'),
        ('sites', '0002_alter_domain_unique'),
    ]

    operations = [
        migrations.RunPython(set_site_domain, migrations.RunPython.noop),
    ]
