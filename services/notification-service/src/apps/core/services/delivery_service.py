"""
Delivery Service.

Handles actual delivery of notifications via various channels.
"""
import logging
from typing import Optional, Dict, Any
from uuid import UUID

from django.conf import settings

from ..models import Notification, DeviceToken
from ..exceptions import DeliveryFailed
from ..constants import CHANNEL_EMAIL, CHANNEL_SMS, CHANNEL_PUSH, CHANNEL_IN_APP

logger = logging.getLogger(__name__)


class DeliveryService:
    """Service for delivering notifications."""

    @classmethod
    def deliver(cls, notification: Notification) -> bool:
        """
        Deliver a notification via its channel.

        Returns True if successful, False otherwise.
        """
        from .notification_service import NotificationService

        try:
            channel_handlers = {
                CHANNEL_EMAIL: cls._deliver_email,
                CHANNEL_SMS: cls._deliver_sms,
                CHANNEL_PUSH: cls._deliver_push,
                CHANNEL_IN_APP: cls._deliver_in_app,
            }

            handler = channel_handlers.get(notification.channel)
            if not handler:
                raise DeliveryFailed(detail=f"Unknown channel: {notification.channel}")

            external_id = handler(notification)
            NotificationService.mark_as_sent(notification.id, external_id or "")

            logger.info(
                f"Delivered notification {notification.id} via {notification.channel}",
                extra={'external_id': external_id}
            )
            return True

        except Exception as e:
            logger.error(f"Failed to deliver notification {notification.id}: {e}")
            NotificationService.mark_as_failed(notification.id, str(e))
            return False

    @classmethod
    def _deliver_email(cls, notification: Notification) -> str:
        """Deliver via email."""
        # In production, integrate with email service (SendGrid, SES, etc.)
        from django.core.mail import send_mail

        try:
            send_mail(
                subject=notification.subject,
                message=notification.body,
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@example.com'),
                recipient_list=[notification.recipient_email],
                html_message=notification.body_html or None,
                fail_silently=False,
            )
            return f"email-{notification.id}"
        except Exception as e:
            raise DeliveryFailed(detail=f"Email delivery failed: {e}")

    @classmethod
    def _deliver_sms(cls, notification: Notification) -> str:
        """Deliver via SMS."""
        # In production, integrate with SMS service (Twilio, etc.)
        twilio_enabled = getattr(settings, 'TWILIO_ENABLED', False)

        if twilio_enabled:
            # Twilio integration placeholder
            pass

        logger.info(f"SMS delivery simulated for {notification.recipient_phone}")
        return f"sms-{notification.id}"

    @classmethod
    def _deliver_push(cls, notification: Notification) -> str:
        """Deliver via push notification."""
        # Get user's device tokens
        tokens = DeviceToken.objects.filter(
            user_id=notification.user_id,
            is_active=True
        )

        if not tokens.exists():
            logger.warning(f"No active devices for user {notification.user_id}")
            return ""

        # In production, integrate with FCM/APNS
        for token in tokens:
            cls._send_push_to_device(
                token=token.token,
                platform=token.platform,
                title=notification.subject,
                body=notification.body,
                data=notification.metadata,
            )

        return f"push-{notification.id}"

    @classmethod
    def _send_push_to_device(
        cls,
        token: str,
        platform: str,
        title: str,
        body: str,
        data: Dict = None
    ) -> bool:
        """Send push to a specific device."""
        # FCM/APNS integration placeholder
        logger.info(f"Push sent to {platform} device")
        return True

    @classmethod
    def _deliver_in_app(cls, notification: Notification) -> str:
        """
        Deliver as in-app notification.

        In-app notifications are stored and marked as sent immediately.
        Real-time delivery is handled via WebSocket/SSE.
        """
        # Publish to real-time channel (e.g., NATS, Redis Pub/Sub)
        try:
            cls._publish_realtime(notification)
        except Exception as e:
            logger.warning(f"Real-time publish failed: {e}")

        return f"in_app-{notification.id}"

    @classmethod
    def _publish_realtime(cls, notification: Notification) -> None:
        """Publish notification to real-time channel."""
        # NATS/Redis integration placeholder
        pass

    @classmethod
    def check_delivery_status(cls, notification: Notification) -> Dict[str, Any]:
        """
        Check delivery status from external provider.

        Returns status info from the email/SMS provider.
        """
        # Provider webhook/API integration placeholder
        return {
            'status': notification.status,
            'external_id': notification.external_id,
            'delivered_at': notification.delivered_at,
        }
