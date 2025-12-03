# services/certificate-service/src/apps/core/urls.py
"""
Core App URLs

URL routing for core app.
"""

from django.urls import path, include

app_name = 'core'

urlpatterns = [
    path('', include('apps.core.api.urls')),
]
