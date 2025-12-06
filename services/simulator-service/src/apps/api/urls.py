# services/simulator-service/src/apps/api/urls.py
"""
API URL Configuration for Simulator Service
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views.fstd_views import FSTDeviceViewSet
from .views.session_views import FSTDSessionViewSet

router = DefaultRouter()
router.register(r'devices', FSTDeviceViewSet, basename='fstd-device')
router.register(r'sessions', FSTDSessionViewSet, basename='fstd-session')

urlpatterns = [
    path('', include(router.urls)),
]
