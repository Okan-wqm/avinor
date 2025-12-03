# services/booking-service/src/apps/api/apps.py
"""
API App Configuration
"""

from django.apps import AppConfig


class ApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.api'
    label = 'booking_api'
    verbose_name = 'Booking API'
