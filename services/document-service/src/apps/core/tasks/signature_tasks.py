# services/document-service/src/apps/core/tasks/signature_tasks.py
"""
Signature Celery Tasks

Background tasks for signature request management.
"""

import logging
from datetime import timedelta
from celery import shared_task

from django.utils import timezone

from ..models.signature import SignatureRequest


logger = logging.getLogger(__name__)


@shared_task(name='document.send_signature_request_email')
def send_signature_request_email(request_id: str):
    """
    Send email notification for signature request.

    Args:
        request_id: SignatureRequest UUID string
    """
    try:
        request = SignatureRequest.objects.select_related('document').get(
            id=request_id
        )
    except SignatureRequest.DoesNotExist:
        logger.error(f"Signature request not found: {request_id}")
        return

    if request.email_sent:
        logger.debug(f"Email already sent for request: {request_id}")
        return

    # Prepare email data
    email_data = {
        'to': request.signer_email,
        'subject': f"Signature Required: {request.document.title or request.document.original_name}",
        'template': 'signature_request',
        'context': {
            'signer_name': request.signer_name,
            'requested_by_name': request.requested_by_name,
            'document_title': request.document.title or request.document.original_name,
            'message': request.message,
            'deadline': request.deadline.isoformat() if request.deadline else None,
            'sign_url': f"/documents/{request.document_id}/sign?request_id={request_id}",
        },
    }

    # Publish to notification service
    _publish_email_request(email_data)

    # Update request
    request.email_sent = True
    request.email_sent_at = timezone.now()
    request.save(update_fields=['email_sent', 'email_sent_at'])

    logger.info(f"Signature request email sent to {request.signer_email}")


@shared_task(name='document.send_signature_reminder')
def send_signature_reminder(request_id: str):
    """
    Send reminder email for pending signature request.

    Args:
        request_id: SignatureRequest UUID string
    """
    try:
        request = SignatureRequest.objects.select_related('document').get(
            id=request_id
        )
    except SignatureRequest.DoesNotExist:
        logger.error(f"Signature request not found: {request_id}")
        return

    if request.status != 'pending':
        logger.debug(f"Request no longer pending: {request_id}")
        return

    # Prepare email data
    days_left = None
    if request.deadline:
        days_left = (request.deadline.date() - timezone.now().date()).days

    email_data = {
        'to': request.signer_email,
        'subject': f"Reminder: Signature Required - {request.document.title or request.document.original_name}",
        'template': 'signature_reminder',
        'context': {
            'signer_name': request.signer_name,
            'requested_by_name': request.requested_by_name,
            'document_title': request.document.title or request.document.original_name,
            'days_left': days_left,
            'deadline': request.deadline.isoformat() if request.deadline else None,
            'sign_url': f"/documents/{request.document_id}/sign?request_id={request_id}",
        },
    }

    # Publish to notification service
    _publish_email_request(email_data)

    # Update reminder tracking
    request.reminder_count += 1
    request.last_reminder_at = timezone.now()
    request.save(update_fields=['reminder_count', 'last_reminder_at'])

    logger.info(f"Signature reminder sent to {request.signer_email}")


@shared_task(name='document.check_overdue_signature_requests')
def check_overdue_signature_requests():
    """
    Check for overdue signature requests.

    Finds requests past their deadline and sends reminders or marks as expired.
    """
    now = timezone.now()

    results = {
        'checked': 0,
        'overdue': 0,
        'expired': 0,
        'reminders_sent': 0,
    }

    # Find requests with deadlines
    pending_requests = SignatureRequest.objects.filter(
        status='pending',
        deadline__isnull=False,
    ).select_related('document')

    for request in pending_requests:
        results['checked'] += 1

        if request.deadline < now:
            results['overdue'] += 1

            # Check how long overdue
            days_overdue = (now - request.deadline).days

            if days_overdue >= 7:
                # Auto-expire after 7 days overdue
                request.status = 'expired'
                request.completed_at = now
                request.save(update_fields=['status', 'completed_at'])
                results['expired'] += 1

                # Notify requester
                _publish_request_expired(request)

            else:
                # Send reminder if not sent recently
                should_send = (
                    request.last_reminder_at is None or
                    (now - request.last_reminder_at) > timedelta(days=1)
                )

                if should_send:
                    send_signature_reminder.delay(str(request.id))
                    results['reminders_sent'] += 1

    logger.info(
        f"Overdue signature check: {results['overdue']} overdue, "
        f"{results['expired']} expired, {results['reminders_sent']} reminders"
    )

    return results


@shared_task(name='document.send_pending_request_reminders')
def send_pending_request_reminders():
    """
    Send reminders for pending signature requests approaching deadline.

    Sends reminders at 7 days, 3 days, and 1 day before deadline.
    """
    now = timezone.now()
    reminder_thresholds = [7, 3, 1]  # Days before deadline

    results = {
        'reminders_sent': 0,
    }

    for days in reminder_thresholds:
        deadline_date = now + timedelta(days=days)
        deadline_start = deadline_date.replace(hour=0, minute=0, second=0)
        deadline_end = deadline_date.replace(hour=23, minute=59, second=59)

        requests = SignatureRequest.objects.filter(
            status='pending',
            deadline__range=(deadline_start, deadline_end),
        )

        for request in requests:
            # Check if reminder already sent today
            if request.last_reminder_at:
                if request.last_reminder_at.date() == now.date():
                    continue

            send_signature_reminder.delay(str(request.id))
            results['reminders_sent'] += 1

    logger.info(f"Pending request reminders: {results['reminders_sent']} sent")

    return results


@shared_task(name='document.notify_signature_completed')
def notify_signature_completed(signature_id: str):
    """
    Notify requester when signature is completed.

    Args:
        signature_id: DocumentSignature UUID string
    """
    from ..models import DocumentSignature

    try:
        signature = DocumentSignature.objects.select_related(
            'document'
        ).get(id=signature_id)
    except DocumentSignature.DoesNotExist:
        logger.error(f"Signature not found: {signature_id}")
        return

    # Find associated request
    request = SignatureRequest.objects.filter(
        document=signature.document,
        signer_id=signature.signer_id,
        signature=signature,
    ).first()

    if not request:
        logger.debug(f"No request found for signature: {signature_id}")
        return

    # Notify the requester
    email_data = {
        'to_user_id': str(request.requested_by),
        'subject': f"Signature Received: {signature.document.title}",
        'template': 'signature_completed',
        'context': {
            'signer_name': signature.signer_name,
            'document_title': signature.document.title or signature.document.original_name,
            'signed_at': signature.signed_at.isoformat(),
            'document_url': f"/documents/{signature.document_id}",
        },
    }

    _publish_email_request(email_data)

    logger.info(
        f"Signature completion notification sent for {signature_id}"
    )


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _publish_email_request(email_data: dict):
    """Publish email request to notification service."""
    try:
        import redis
        import json
        from django.conf import settings

        r = redis.Redis.from_url(settings.REDIS_URL)
        r.publish('notification.email', json.dumps(email_data))
    except Exception as e:
        logger.warning(f"Failed to publish email request: {e}")


def _publish_request_expired(request: SignatureRequest):
    """Publish signature request expired event."""
    try:
        import redis
        import json
        from django.conf import settings

        r = redis.Redis.from_url(settings.REDIS_URL)
        r.publish('document.signature_request_expired', json.dumps({
            'request_id': str(request.id),
            'document_id': str(request.document_id),
            'requested_by': str(request.requested_by),
            'signer_name': request.signer_name,
            'signer_email': request.signer_email,
        }))
    except Exception as e:
        logger.warning(f"Failed to publish expired event: {e}")
