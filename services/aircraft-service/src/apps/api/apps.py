# services/aircraft-service/src/apps/api/apps.py
"""
API Application Configuration
"""

from django.apps import AppConfig


class ApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.api'
    verbose_name = 'Aircraft API'
