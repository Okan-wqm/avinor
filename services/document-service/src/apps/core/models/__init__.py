# services/document-service/src/apps/core/models/__init__.py
"""
Document Service Models

Complete model definitions for document management system.
"""

from .document import (
    Document,
    DocumentType,
    DocumentStatus,
    AccessLevel,
    ProcessingStatus,
)
from .folder import DocumentFolder
from .signature import DocumentSignature, SignatureType, SignatureStatus
from .template import DocumentTemplate, TemplateType, OutputFormat
from .share import DocumentShare, SharePermission, ShareTargetType


__all__ = [
    # Document
    'Document',
    'DocumentType',
    'DocumentStatus',
    'AccessLevel',
    'ProcessingStatus',
    # Folder
    'DocumentFolder',
    # Signature
    'DocumentSignature',
    'SignatureType',
    'SignatureStatus',
    # Template
    'DocumentTemplate',
    'TemplateType',
    'OutputFormat',
    # Share
    'DocumentShare',
    'SharePermission',
    'ShareTargetType',
]
