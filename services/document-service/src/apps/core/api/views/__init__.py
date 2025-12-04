# services/document-service/src/apps/core/api/views/__init__.py
"""
Document Service Views
"""

from .document_views import DocumentViewSet
from .folder_views import FolderViewSet
from .signature_views import SignatureViewSet, SignatureRequestViewSet
from .template_views import TemplateViewSet
from .share_views import ShareViewSet, PublicShareView


__all__ = [
    'DocumentViewSet',
    'FolderViewSet',
    'SignatureViewSet',
    'SignatureRequestViewSet',
    'TemplateViewSet',
    'ShareViewSet',
    'PublicShareView',
]
