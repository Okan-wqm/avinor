# services/document-service/src/apps/core/services/__init__.py
"""
Document Service Layer

Business logic services for document management.
"""

from .storage_service import StorageService, StorageError
from .document_service import (
    DocumentService,
    DocumentNotFoundError,
    DocumentAccessDeniedError,
    DocumentProcessingError,
)
from .folder_service import FolderService, FolderNotFoundError
from .signature_service import SignatureService, SignatureError
from .template_service import TemplateService, TemplateError
from .share_service import ShareService, ShareError
from .pdf_service import PDFService
from .thumbnail_service import ThumbnailService


__all__ = [
    # Storage
    'StorageService',
    'StorageError',
    # Document
    'DocumentService',
    'DocumentNotFoundError',
    'DocumentAccessDeniedError',
    'DocumentProcessingError',
    # Folder
    'FolderService',
    'FolderNotFoundError',
    # Signature
    'SignatureService',
    'SignatureError',
    # Template
    'TemplateService',
    'TemplateError',
    # Share
    'ShareService',
    'ShareError',
    # PDF
    'PDFService',
    # Thumbnail
    'ThumbnailService',
]
