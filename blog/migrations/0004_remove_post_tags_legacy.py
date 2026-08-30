from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('blog', '0003_migrate_tags_to_m2m'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='post',
            name='tags_legacy',
        ),
    ]
