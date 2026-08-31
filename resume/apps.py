from django.apps import AppConfig


class ResumeConfig(AppConfig):
    name = 'resume'

    def ready(self):
        from functools import partial

        from django.db.models.signals import post_delete, pre_save

        from config.file_cleanup import cleanup_file_on_change, cleanup_file_on_delete

        from .models import Profile

        post_delete.connect(
            partial(cleanup_file_on_delete, field_name='photo'),
            sender=Profile,
            weak=False,
            dispatch_uid='resume_profile_photo_cleanup',
        )
        pre_save.connect(
            partial(cleanup_file_on_change, field_name='photo'),
            sender=Profile,
            weak=False,
            dispatch_uid='resume_profile_photo_cleanup_change',
        )
