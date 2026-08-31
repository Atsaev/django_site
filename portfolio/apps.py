from django.apps import AppConfig


class PortfolioConfig(AppConfig):
    name = 'portfolio'

    def ready(self):
        from functools import partial

        from django.db.models.signals import post_delete, pre_save

        from config.file_cleanup import cleanup_file_on_change, cleanup_file_on_delete

        from .models import Project

        post_delete.connect(
            partial(cleanup_file_on_delete, field_name='cover_image'),
            sender=Project,
            weak=False,
            dispatch_uid='portfolio_project_cover_image_cleanup',
        )
        pre_save.connect(
            partial(cleanup_file_on_change, field_name='cover_image'),
            sender=Project,
            weak=False,
            dispatch_uid='portfolio_project_cover_image_cleanup_change',
        )
