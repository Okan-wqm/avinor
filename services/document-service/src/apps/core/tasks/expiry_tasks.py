# services/document-service/src/apps/core/tasks/expiry_tasks.py
"""
Document Expiry Celery Tasks

Background tasks for document expiration management.
"""

import logging
from datetime import date, timedelta
from celery import shared_task

from django.utils import timezone
from django.db.models import Q

from ..models import Document, DocumentStatus


logger = logging.getLogger(__name__)


@shared_task(name='document.check_expiring_documents')
def check_expiring_documents():
    """
    Check for documents expiring soon.

    Runs daily to identify documents that will expire within 30 days.
    Publishes events for notification service.
    """
    today = date.today()
    notification_thresholds = [30, 14, 7, 1]  # Days before expiry

    results = {
        'checked': 0,
        'expiring': {},
    }

    for days in notification_thresholds:
        expiry_date = today + timedelta(days=days)

        # Find documents expiring on this date
        documents = Document.objects.filter(
            status=DocumentStatus.ACTIVE,
            expiry_date=expiry_date,
        ).select_related('folder')

        count = documents.count()
        results['expiring'][f'{days}_days'] = count

        for document in documents:
            # Publish expiry notification event
            _publish_expiry_notification(document, days)

        results['checked'] += count

    logger.info(f"Expiry check completed: {results}")

    return results


@shared_task(name='document.archive_expired_documents')
def archive_expired_documents(auto_archive: bool = False):
    """
    Process expired documents.

    Identifies documents past their expiry date.
    Optionally archives them automatically.

    Args:
        auto_archive: If True, automatically archive expired documents
    """
    today = date.today()

    expired = Document.objects.filter(
        status=DocumentStatus.ACTIVE,
        expiry_date__lt=today,
    )

    results = {
        'expired_count': expired.count(),
        'archived_count': 0,
        'document_ids': [],
    }

    if auto_archive:
        for document in expired:
            document.archive()
            results['archived_count'] += 1
            results['document_ids'].append(str(document.id))

            # Publish archived event
            _publish_document_archived(document)

    logger.info(
        f"Expired documents: {results['expired_count']}, "
        f"Archived: {results['archived_count']}"
    )

    return results


@shared_task(name='document.send_expiry_notifications')
def send_expiry_notifications():
    """
    Send batch expiry notifications.

    Groups expiring documents by owner and sends consolidated notifications.
    """
    today = date.today()
    notification_windows = [
        (30, "30 days"),
        (14, "2 weeks"),
        (7, "1 week"),
        (1, "tomorrow"),
    ]

    notifications_sent = 0

    for days, label in notification_windows:
        expiry_date = today + timedelta(days=days)

        # Group documents by owner
        expiring_docs = Document.objects.filter(
            status=DocumentStatus.ACTIVE,
            expiry_date=expiry_date,
        ).values('owner_id', 'organization_id').distinct()

        for owner_info in expiring_docs:
            owner_id = owner_info['owner_id']
            org_id = owner_info['organization_id']

            # Get all expiring documents for this owner
            documents = Document.objects.filter(
                status=DocumentStatus.ACTIVE,
                expiry_date=expiry_date,
                owner_id=owner_id,
            )

            # Prepare notification data
            doc_list = [
                {
                    'id': str(doc.id),
                    'title': doc.title or doc.original_name,
                    'document_type': doc.document_type,
                    'expiry_date': expiry_date.isoformat(),
                }
                for doc in documents
            ]

            # Publish notification event
            _publish_batch_expiry_notification(
                owner_id=owner_id,
                organization_id=org_id,
                documents=doc_list,
                days_until_expiry=days,
                label=label,
            )

            notifications_sent += 1

    logger.info(f"Expiry notifications sent: {notifications_sent}")

    return {'notifications_sent': notifications_sent}


@shared_task(name='document.get_expiring_documents_report')
def get_expiring_documents_report(organization_id: str, days: int = 30):
    """
    Generate report of expiring documents for an organization.

    Args:
        organization_id: Organization UUID string
        days: Look-ahead window in days

    Returns:
        Dict with report data
    """
    today = date.today()
    cutoff = today + timedelta(days=days)

    documents = Document.objects.filter(
        organization_id=organization_id,
        status=DocumentStatus.ACTIVE,
        expiry_date__isnull=False,
        expiry_date__lte=cutoff,
    ).order_by('expiry_date')

    report = {
        'organization_id': organization_id,
        'report_date': today.isoformat(),
        'look_ahead_days': days,
        'total_expiring': documents.count(),
        'by_status': {
            'already_expired': 0,
            'expiring_this_week': 0,
            'expiring_this_month': 0,
        },
        'by_type': {},
        'documents': [],
    }

    week_from_now = today + timedelta(days=7)

    for doc in documents:
        # Categorize
        if doc.expiry_date < today:
            report['by_status']['already_expired'] += 1
        elif doc.expiry_date <= week_from_now:
            report['by_status']['expiring_this_week'] += 1
        else:
            report['by_status']['expiring_this_month'] += 1

        # Count by type
        doc_type = doc.document_type
        report['by_type'][doc_type] = report['by_type'].get(doc_type, 0) + 1

        # Add document detail
        report['documents'].append({
            'id': str(doc.id),
            'title': doc.title or doc.original_name,
            'document_type': doc.document_type,
            'expiry_date': doc.expiry_date.isoformat(),
            'days_until_expiry': (doc.expiry_date - today).days,
            'owner_id': str(doc.owner_id),
            'related_entity_type': doc.related_entity_type,
            'related_entity_id': str(doc.related_entity_id) if doc.related_entity_id else None,
        })

    logger.info(
        f"Generated expiry report for org {organization_id}: "
        f"{report['total_expiring']} expiring documents"
    )

    return report


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _publish_expiry_notification(document, days_until_expiry: int):
    """Publish single document expiry notification."""
    try:
        import redis
        import json
        from django.conf import settings

        r = redis.Redis.from_url(settings.REDIS_URL)
        r.publish('document.expiring', json.dumps({
            'document_id': str(document.id),
            'organization_id': str(document.organization_id),
            'owner_id': str(document.owner_id),
            'title': document.title or document.original_name,
            'document_type': document.document_type,
            'expiry_date': document.expiry_date.isoformat(),
            'days_until_expiry': days_until_expiry,
        }))
    except Exception as e:
        logger.warning(f"Failed to publish expiry notification: {e}")


def _publish_batch_expiry_notification(
    owner_id,
    organization_id,
    documents: list,
    days_until_expiry: int,
    label: str,
):
    """Publish batch expiry notification."""
    try:
        import redis
        import json
        from django.conf import settings

        r = redis.Redis.from_url(settings.REDIS_URL)
        r.publish('document.batch_expiring', json.dumps({
            'owner_id': str(owner_id),
            'organization_id': str(organization_id),
            'documents': documents,
            'document_count': len(documents),
            'days_until_expiry': days_until_expiry,
            'expiry_label': label,
        }))
    except Exception as e:
        logger.warning(f"Failed to publish batch expiry notification: {e}")


def _publish_document_archived(document):
    """Publish document archived event."""
    try:
        import redis
        import json
        from django.conf import settings

        r = redis.Redis.from_url(settings.REDIS_URL)
        r.publish('document.archived', json.dumps({
            'document_id': str(document.id),
            'organization_id': str(document.organization_id),
            'owner_id': str(document.owner_id),
            'reason': 'expired',
        }))
    except Exception as e:
        logger.warning(f"Failed to publish archived notification: {e}")
