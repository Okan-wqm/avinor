from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.core'
    verbose_name = 'Booking Service Core'

    def ready(self):
        """Import signals when app is ready."""
        from . import signals  # noqa: F401
