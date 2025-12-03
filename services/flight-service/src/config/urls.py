# services/flight-service/src/config/urls.py
"""
Flight Service URL Configuration
"""

from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from django.db import connection


def health_check(request):
    """Basic health check endpoint."""
    return JsonResponse({
        'status': 'healthy',
        'service': 'flight-service',
        'version': '1.0.0'
    })


def readiness_check(request):
    """Readiness check with database connectivity."""
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
        db_status = 'connected'
    except Exception as e:
        db_status = f'error: {str(e)}'

    is_ready = db_status == 'connected'

    return JsonResponse({
        'status': 'ready' if is_ready else 'not_ready',
        'service': 'flight-service',
        'checks': {
            'database': db_status,
        }
    }, status=200 if is_ready else 503)


urlpatterns = [
    path('admin/', admin.site.urls),
    path('health/', health_check, name='health_check'),
    path('ready/', readiness_check, name='readiness_check'),
    path('api/v1/flights/', include('apps.api.urls', namespace='api')),
]
