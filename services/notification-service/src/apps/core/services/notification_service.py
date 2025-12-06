"""
Notification Service.

Core business logic for managing notifications.
"""
import logging
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import timedelta

from django.db import transaction
from django.db.models import QuerySet
from django.utils import timezone

from ..models import Notification, NotificationTemplate
from ..exceptions import NotificationNotFound, RecipientRequired
from ..constants import (
    STATUS_PENDING,
    STATUS_SENT,
    STATUS_DELIVERED,
    STATUS_READ,
    STATUS_FAILED,
    CHANNEL_EMAIL,
    CHANNEL_SMS,
    CHANNEL_PUSH,
    CHANNEL_IN_APP,
)

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for managing notifications."""

    @staticmethod
    def get_by_id(notification_id: UUID, user_id: Optional[UUID] = None) -> Notification:
        """Get a notification by ID."""
        queryset = Notification.objects.select_related('template')
        if user_id:
            queryset = queryset.filter(user_id=user_id)

        try:
            return queryset.get(id=notification_id)
        except Notification.DoesNotExist:
            raise NotificationNotFound()

    @staticmethod
    def get_for_user(
        user_id: UUID,
        channel: Optional[str] = None,
        status: Optional[str] = None,
        unread_only: bool = False,
        limit: int = 50,
    ) -> QuerySet[Notification]:
        """Get notifications for a user."""
        queryset = Notification.objects.filter(user_id=user_id)

        if channel:
            queryset = queryset.filter(channel=channel)

        if status:
            queryset = queryset.filter(status=status)

        if unread_only:
            queryset = queryset.filter(read_at__isnull=True)

        return queryset.order_by('-created_at')[:limit]

    @staticmethod
    def get_unread_count(user_id: UUID) -> int:
        """Get unread notification count for a user."""
        return Notification.objects.filter(
            user_id=user_id,
            read_at__isnull=True,
            channel=CHANNEL_IN_APP,
        ).count()

    @staticmethod
    @transaction.atomic
    def create(
        user_id: UUID,
        channel: str,
        body: str,
        subject: str = "",
        template_id: Optional[UUID] = None,
        organization_id: Optional[UUID] = None,
        priority: str = "normal",
        recipient_email: str = "",
        recipient_phone: str = "",
        context: Optional[Dict] = None,
        metadata: Optional[Dict] = None,
        scheduled_at: Optional[str] = None,
    ) -> Notification:
        """Create a new notification."""
        # Validate recipient
        if channel == CHANNEL_EMAIL and not recipient_email:
            raise RecipientRequired(detail="Email address required for email notifications")
        if channel == CHANNEL_SMS and not recipient_phone:
            raise RecipientRequired(detail="Phone number required for SMS notifications")

        notification = Notification.objects.create(
            user_id=user_id,
            organization_id=organization_id,
            template_id=template_id,
            channel=channel,
            priority=priority,
            subject=subject,
            body=body,
            recipient_email=recipient_email,
            recipient_phone=recipient_phone,
            context=context or {},
            metadata=metadata or {},
            scheduled_at=scheduled_at,
            status=STATUS_PENDING,
        )

        logger.info(
            f"Created notification: {notification.id}",
            extra={
                'notification_id': str(notification.id),
                'user_id': str(user_id),
                'channel': channel,
            }
        )

        return notification

    @staticmethod
    def create_from_template(
        user_id: UUID,
        template_code: str,
        context: Dict[str, Any],
        recipient_email: str = "",
        recipient_phone: str = "",
        organization_id: Optional[UUID] = None,
        priority: str = "normal",
        scheduled_at: Optional[str] = None,
    ) -> Notification:
        """Create notification from a template."""
        from .template_service import TemplateService

        template = TemplateService.get_by_code(template_code)

        # Render template
        subject = TemplateService.render_template(template.subject, context)
        body_html = TemplateService.render_template(template.body_html, context)
        body_text = TemplateService.render_template(template.body_text, context)

        return NotificationService.create(
            user_id=user_id,
            channel=template.template_type,
            subject=subject,
            body=body_text or body_html,
            template_id=template.id,
            organization_id=organization_id,
            priority=priority,
            recipient_email=recipient_email,
            recipient_phone=recipient_phone,
            context=context,
            scheduled_at=scheduled_at,
        )

    @staticmethod
    @transaction.atomic
    def mark_as_sent(notification_id: UUID, external_id: str = "") -> Notification:
        """Mark notification as sent."""
        notification = NotificationService.get_by_id(notification_id)
        notification.status = STATUS_SENT
        notification.sent_at = timezone.now()
        notification.external_id = external_id
        notification.save(update_fields=['status', 'sent_at', 'external_id', 'updated_at'])
        return notification

    @staticmethod
    @transaction.atomic
    def mark_as_delivered(notification_id: UUID) -> Notification:
        """Mark notification as delivered."""
        notification = NotificationService.get_by_id(notification_id)
        notification.status = STATUS_DELIVERED
        notification.delivered_at = timezone.now()
        notification.save(update_fields=['status', 'delivered_at', 'updated_at'])
        return notification

    @staticmethod
    @transaction.atomic
    def mark_as_read(notification_id: UUID, user_id: UUID) -> Notification:
        """Mark notification as read."""
        notification = NotificationService.get_by_id(notification_id, user_id)
        notification.status = STATUS_READ
        notification.read_at = timezone.now()
        notification.save(update_fields=['status', 'read_at', 'updated_at'])
        return notification

    @staticmethod
    @transaction.atomic
    def mark_all_as_read(user_id: UUID) -> int:
        """Mark all notifications as read for a user."""
        now = timezone.now()
        count = Notification.objects.filter(
            user_id=user_id,
            read_at__isnull=True,
            channel=CHANNEL_IN_APP,
        ).update(status=STATUS_READ, read_at=now)

        logger.info(f"Marked {count} notifications as read for user {user_id}")
        return count

    @staticmethod
    @transaction.atomic
    def mark_as_failed(notification_id: UUID, reason: str) -> Notification:
        """Mark notification as failed."""
        notification = NotificationService.get_by_id(notification_id)
        notification.status = STATUS_FAILED
        notification.failed_at = timezone.now()
        notification.failure_reason = reason
        notification.save(update_fields=['status', 'failed_at', 'failure_reason', 'updated_at'])
        return notification

    @staticmethod
    def get_pending(limit: int = 100) -> QuerySet[Notification]:
        """Get pending notifications ready to send."""
        now = timezone.now()
        return Notification.objects.filter(
            status=STATUS_PENDING,
        ).filter(
            # Either no scheduled time or scheduled time has passed
            scheduled_at__isnull=True
        ).union(
            Notification.objects.filter(
                status=STATUS_PENDING,
                scheduled_at__lte=now,
            )
        ).order_by('created_at')[:limit]

    @staticmethod
    def get_failed_for_retry(limit: int = 50) -> QuerySet[Notification]:
        """Get failed notifications eligible for retry."""
        now = timezone.now()
        return Notification.objects.filter(
            status=STATUS_FAILED,
            retry_count__lt=3,
            next_retry_at__lte=now,
        ).order_by('next_retry_at')[:limit]

    @staticmethod
    @transaction.atomic
    def schedule_retry(notification_id: UUID) -> Notification:
        """Schedule a notification for retry."""
        notification = NotificationService.get_by_id(notification_id)

        notification.retry_count += 1
        delay = 60 * (2 ** notification.retry_count)  # Exponential backoff
        notification.next_retry_at = timezone.now() + timedelta(seconds=delay)
        notification.status = STATUS_PENDING
        notification.save()

        logger.info(
            f"Scheduled retry for notification {notification_id}",
            extra={'retry_count': notification.retry_count}
        )

        return notification

    @staticmethod
    def delete_old_notifications(days: int = 90) -> int:
        """Delete notifications older than specified days."""
        threshold = timezone.now() - timedelta(days=days)
        deleted, _ = Notification.objects.filter(
            created_at__lt=threshold,
            status__in=[STATUS_DELIVERED, STATUS_READ, STATUS_FAILED],
        ).delete()

        logger.info(f"Deleted {deleted} old notifications")
        return deleted
