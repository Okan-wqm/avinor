# services/document-service/src/apps/core/api/urls.py
"""
Document Service API URL Configuration
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    DocumentViewSet,
    FolderViewSet,
    SignatureViewSet,
    SignatureRequestViewSet,
    TemplateViewSet,
    ShareViewSet,
    PublicShareView,
)
from .views.share_views import PublicShareDownloadView


# Create router
router = DefaultRouter()
router.register(r'documents', DocumentViewSet, basename='document')
router.register(r'folders', FolderViewSet, basename='folder')
router.register(r'signatures', SignatureViewSet, basename='signature')
router.register(r'signature-requests', SignatureRequestViewSet, basename='signature-request')
router.register(r'templates', TemplateViewSet, basename='template')
router.register(r'shares', ShareViewSet, basename='share')


urlpatterns = [
    # API v1
    path('api/v1/', include(router.urls)),

    # Public share endpoints (no auth required)
    path(
        'share/<str:token>/',
        PublicShareView.as_view(),
        name='public-share'
    ),
    path(
        'share/<str:token>/download/',
        PublicShareDownloadView.as_view(),
        name='public-share-download'
    ),
]
