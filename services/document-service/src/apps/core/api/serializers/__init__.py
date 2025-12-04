# services/document-service/src/apps/core/api/serializers/__init__.py
"""
Document Service Serializers
"""

from .document_serializers import (
    DocumentSerializer,
    DocumentListSerializer,
    DocumentDetailSerializer,
    DocumentUploadSerializer,
    DocumentUpdateSerializer,
    DocumentVersionSerializer,
    DocumentSearchSerializer,
)
from .folder_serializers import (
    FolderSerializer,
    FolderListSerializer,
    FolderDetailSerializer,
    FolderCreateSerializer,
    FolderMoveSerializer,
    FolderTreeSerializer,
)
from .signature_serializers import (
    SignatureSerializer,
    SignatureRequestSerializer,
    SignatureRequestCreateSerializer,
    SignatureVerifySerializer,
)
from .template_serializers import (
    TemplateSerializer,
    TemplateListSerializer,
    TemplateDetailSerializer,
    TemplateCreateSerializer,
    TemplateGenerateSerializer,
)
from .share_serializers import (
    ShareSerializer,
    ShareCreateSerializer,
    ShareUpdateSerializer,
    PublicShareSerializer,
)


__all__ = [
    # Document
    'DocumentSerializer',
    'DocumentListSerializer',
    'DocumentDetailSerializer',
    'DocumentUploadSerializer',
    'DocumentUpdateSerializer',
    'DocumentVersionSerializer',
    'DocumentSearchSerializer',
    # Folder
    'FolderSerializer',
    'FolderListSerializer',
    'FolderDetailSerializer',
    'FolderCreateSerializer',
    'FolderMoveSerializer',
    'FolderTreeSerializer',
    # Signature
    'SignatureSerializer',
    'SignatureRequestSerializer',
    'SignatureRequestCreateSerializer',
    'SignatureVerifySerializer',
    # Template
    'TemplateSerializer',
    'TemplateListSerializer',
    'TemplateDetailSerializer',
    'TemplateCreateSerializer',
    'TemplateGenerateSerializer',
    # Share
    'ShareSerializer',
    'ShareCreateSerializer',
    'ShareUpdateSerializer',
    'PublicShareSerializer',
]
