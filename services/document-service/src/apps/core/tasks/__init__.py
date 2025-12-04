# services/document-service/src/apps/core/tasks/__init__.py
"""
Document Service Celery Tasks

Background task processing for documents.
"""

from .processing_tasks import (
    process_document,
    generate_thumbnail,
    extract_text_ocr,
    scan_virus,
)
from .expiry_tasks import (
    check_expiring_documents,
    archive_expired_documents,
    send_expiry_notifications,
)
from .maintenance_tasks import (
    cleanup_orphan_files,
    recalculate_folder_statistics,
    verify_document_checksums,
)
from .signature_tasks import (
    send_signature_request_email,
    check_overdue_signature_requests,
)


__all__ = [
    # Processing
    'process_document',
    'generate_thumbnail',
    'extract_text_ocr',
    'scan_virus',
    # Expiry
    'check_expiring_documents',
    'archive_expired_documents',
    'send_expiry_notifications',
    # Maintenance
    'cleanup_orphan_files',
    'recalculate_folder_statistics',
    'verify_document_checksums',
    # Signature
    'send_signature_request_email',
    'check_overdue_signature_requests',
]
