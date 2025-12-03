from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    NotificationTemplateViewSet, NotificationViewSet,
    NotificationPreferenceViewSet, DeviceTokenViewSet, NotificationBatchViewSet
)

router = DefaultRouter()
router.register(r'templates', NotificationTemplateViewSet, basename='template')
router.register(r'notifications', NotificationViewSet, basename='notification')
router.register(r'preferences', NotificationPreferenceViewSet, basename='preference')
router.register(r'devices', DeviceTokenViewSet, basename='device')
router.register(r'batches', NotificationBatchViewSet, basename='batch')

urlpatterns = [path('', include(router.urls))]
