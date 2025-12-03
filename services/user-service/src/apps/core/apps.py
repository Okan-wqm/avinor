# services/user-service/src/apps/core/apps.py
from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.core'
    verbose_name = 'User Management'

    def ready(self):
        # Import signals
        try:
            from apps.core import signals  # noqa
        except ImportError:
            pass
