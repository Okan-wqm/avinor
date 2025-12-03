from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.core'
    verbose_name = 'Document Management'

    def ready(self):
        try:
            from apps.core import signals  # noqa
        except ImportError:
            pass
