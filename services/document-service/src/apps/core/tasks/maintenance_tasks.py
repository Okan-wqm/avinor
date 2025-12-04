# services/document-service/src/apps/core/tasks/maintenance_tasks.py
"""
Document Maintenance Celery Tasks

Background tasks for storage cleanup, integrity checks, and statistics.
"""

import logging
from datetime import timedelta
from celery import shared_task

from django.utils import timezone
from django.db.models import Sum

from ..models import Document, DocumentFolder, DocumentStatus
from ..services.storage_service import StorageService


logger = logging.getLogger(__name__)


@shared_task(name='document.cleanup_orphan_files')
def cleanup_orphan_files(dry_run: bool = True):
    """
    Clean up orphaned files in storage.

    Finds files in storage that have no corresponding database record.
    Used after failed uploads or manual deletions.

    Args:
        dry_run: If True, only report orphans without deleting

    Returns:
        Dict with cleanup results
    """
    storage = StorageService()

    results = {
        'dry_run': dry_run,
        'total_files_scanned': 0,
        'orphan_files_found': 0,
        'orphan_files_deleted': 0,
        'bytes_freed': 0,
        'errors': [],
    }

    try:
        # List all files in storage
        continuation_token = None

        while True:
            list_result = storage.list_files(
                continuation_token=continuation_token,
                max_keys=1000,
            )

            for file_info in list_result['files']:
                results['total_files_scanned'] += 1

                key = file_info['key']

                # Skip system files (thumbnails, previews)
                if '/thumbnails/' in key or '/previews/' in key:
                    # Check if parent document exists
                    parent_key = key.split('/thumbnails/')[0].split('/previews/')[0]
                    doc_exists = Document.objects.filter(
                        file_path__startswith=parent_key
                    ).exists()
                    if doc_exists:
                        continue

                # Check if document record exists
                document_exists = Document.objects.filter(
                    file_path=key
                ).exists()

                if not document_exists:
                    results['orphan_files_found'] += 1
                    results['bytes_freed'] += file_info['size']

                    if not dry_run:
                        try:
                            storage.delete_file(key)
                            results['orphan_files_deleted'] += 1
                        except Exception as e:
                            results['errors'].append({
                                'key': key,
                                'error': str(e),
                            })

            # Check for more files
            if not list_result['is_truncated']:
                break

            continuation_token = list_result['continuation_token']

    except Exception as e:
        logger.error(f"Orphan cleanup failed: {e}")
        results['errors'].append({'error': str(e)})

    action = "would be deleted" if dry_run else "deleted"
    logger.info(
        f"Orphan cleanup: {results['orphan_files_found']} files {action}, "
        f"{results['bytes_freed']} bytes"
    )

    return results


@shared_task(name='document.cleanup_deleted_documents')
def cleanup_deleted_documents(days_old: int = 30, dry_run: bool = True):
    """
    Permanently delete soft-deleted documents after retention period.

    Args:
        days_old: Days since deletion before permanent removal
        dry_run: If True, only report without deleting

    Returns:
        Dict with cleanup results
    """
    cutoff = timezone.now() - timedelta(days=days_old)

    deleted_docs = Document.objects.filter(
        status=DocumentStatus.DELETED,
        deleted_at__lt=cutoff,
    )

    results = {
        'dry_run': dry_run,
        'documents_found': deleted_docs.count(),
        'documents_deleted': 0,
        'bytes_freed': 0,
        'errors': [],
    }

    storage = StorageService()

    for document in deleted_docs:
        results['bytes_freed'] += document.file_size

        if not dry_run:
            try:
                # Delete from storage
                storage.delete_file(document.file_path)

                if document.thumbnail_path:
                    storage.delete_file(document.thumbnail_path)
                if document.preview_path:
                    storage.delete_file(document.preview_path)

                # Delete from database
                document.delete()
                results['documents_deleted'] += 1

            except Exception as e:
                results['errors'].append({
                    'document_id': str(document.id),
                    'error': str(e),
                })

    logger.info(
        f"Deleted documents cleanup: {results['documents_deleted']} "
        f"permanently removed"
    )

    return results


@shared_task(name='document.recalculate_folder_statistics')
def recalculate_folder_statistics(organization_id: str = None):
    """
    Recalculate statistics for all folders.

    Updates document count and total size for each folder.

    Args:
        organization_id: Specific organization to update (all if None)

    Returns:
        Dict with update results
    """
    queryset = DocumentFolder.objects.all()

    if organization_id:
        queryset = queryset.filter(organization_id=organization_id)

    # Process deepest folders first (to roll up correctly)
    folders = queryset.order_by('-depth')

    results = {
        'folders_processed': 0,
        'discrepancies_found': 0,
    }

    for folder in folders:
        old_count = folder.document_count
        old_size = folder.total_size_bytes

        folder.recalculate_statistics()

        if old_count != folder.document_count or old_size != folder.total_size_bytes:
            results['discrepancies_found'] += 1
            logger.debug(
                f"Folder {folder.path}: count {old_count}->{folder.document_count}, "
                f"size {old_size}->{folder.total_size_bytes}"
            )

        results['folders_processed'] += 1

    logger.info(
        f"Folder statistics recalculated: {results['folders_processed']} folders, "
        f"{results['discrepancies_found']} discrepancies found"
    )

    return results


@shared_task(name='document.verify_document_checksums')
def verify_document_checksums(organization_id: str = None, limit: int = 100):
    """
    Verify document file integrity by checking checksums.

    Downloads files and compares checksums to detect corruption.

    Args:
        organization_id: Specific organization to check
        limit: Maximum documents to check per run

    Returns:
        Dict with verification results
    """
    import hashlib

    queryset = Document.objects.filter(
        status=DocumentStatus.ACTIVE,
        checksum__isnull=False,
    )

    if organization_id:
        queryset = queryset.filter(organization_id=organization_id)

    # Prioritize documents not recently verified (oldest updated first)
    documents = queryset.order_by('updated_at')[:limit]

    storage = StorageService()

    results = {
        'documents_checked': 0,
        'valid': 0,
        'corrupted': 0,
        'missing': 0,
        'errors': [],
    }

    for document in documents:
        try:
            # Download file
            file_content = storage.download_file(document.file_path)

            # Calculate checksum
            calculated = hashlib.sha256(file_content).hexdigest()

            if calculated == document.checksum:
                results['valid'] += 1
            else:
                results['corrupted'] += 1
                logger.warning(
                    f"Checksum mismatch for document {document.id}: "
                    f"stored={document.checksum[:16]}..., "
                    f"calculated={calculated[:16]}..."
                )
                results['errors'].append({
                    'document_id': str(document.id),
                    'error': 'checksum_mismatch',
                    'stored': document.checksum,
                    'calculated': calculated,
                })

            results['documents_checked'] += 1

        except Exception as e:
            if 'not found' in str(e).lower():
                results['missing'] += 1
            else:
                results['errors'].append({
                    'document_id': str(document.id),
                    'error': str(e),
                })

    logger.info(
        f"Checksum verification: {results['valid']} valid, "
        f"{results['corrupted']} corrupted, {results['missing']} missing"
    )

    return results


@shared_task(name='document.generate_storage_report')
def generate_storage_report(organization_id: str = None):
    """
    Generate storage usage report.

    Args:
        organization_id: Specific organization (all if None)

    Returns:
        Dict with storage statistics
    """
    queryset = Document.objects.filter(status=DocumentStatus.ACTIVE)

    if organization_id:
        queryset = queryset.filter(organization_id=organization_id)

    # Overall stats
    total_stats = queryset.aggregate(
        total_count=Sum('file_size'),
        total_size=Sum('file_size'),
    )

    # By document type
    by_type = {}
    for doc_type in queryset.values_list('document_type', flat=True).distinct():
        type_docs = queryset.filter(document_type=doc_type)
        by_type[doc_type] = {
            'count': type_docs.count(),
            'size': type_docs.aggregate(s=Sum('file_size'))['s'] or 0,
        }

    # By month (last 12 months)
    from django.db.models.functions import TruncMonth

    by_month = list(
        queryset.annotate(
            month=TruncMonth('created_at')
        ).values('month').annotate(
            count=Sum('file_size'),
            size=Sum('file_size'),
        ).order_by('-month')[:12]
    )

    report = {
        'organization_id': organization_id,
        'generated_at': timezone.now().isoformat(),
        'total_documents': queryset.count(),
        'total_size_bytes': total_stats['total_size'] or 0,
        'total_size_display': _format_bytes(total_stats['total_size'] or 0),
        'by_document_type': by_type,
        'by_month': [
            {
                'month': m['month'].strftime('%Y-%m'),
                'count': m['count'],
                'size': m['size'],
            }
            for m in by_month
        ],
    }

    logger.info(
        f"Storage report generated: {report['total_documents']} documents, "
        f"{report['total_size_display']}"
    )

    return report


def _format_bytes(size: int) -> str:
    """Format bytes to human-readable string."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{size:.2f} PB"
