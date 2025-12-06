# services/notification-service/src/apps/core/tasks.py
"""
Celery Tasks for Notification Service

Handles asynchronous sending of notifications via:
- Email (SMTP/SendGrid/SES)
- SMS (Twilio/AWS SNS)
- Push Notifications (FCM/APNs)
- In-App Notifications
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail, EmailMultiAlternatives
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_notification(self, notification_id: str) -> Dict[str, Any]:
    """
    Main task to send a notification.
    Routes to appropriate channel handler.

    Args:
        notification_id: UUID of the notification to send

    Returns:
        Dict with send result
    """
    from .models import Notification

    try:
        notification = Notification.objects.get(id=notification_id)
    except Notification.DoesNotExist:
        logger.error(f"Notification not found: {notification_id}")
        return {'success': False, 'error': 'Notification not found'}

    # Check if already sent
    if notification.status == Notification.Status.SENT:
        logger.info(f"Notification {notification_id} already sent")
        return {'success': True, 'message': 'Already sent'}

    # Check if scheduled for later
    if notification.scheduled_at and notification.scheduled_at > timezone.now():
        logger.info(f"Notification {notification_id} scheduled for {notification.scheduled_at}")
        return {'success': True, 'message': 'Scheduled for later'}

    # Route to channel-specific handler
    channel_handlers = {
        Notification.Channel.EMAIL: send_email_notification,
        Notification.Channel.SMS: send_sms_notification,
        Notification.Channel.PUSH: send_push_notification,
        Notification.Channel.IN_APP: send_in_app_notification,
    }

    handler = channel_handlers.get(notification.channel)
    if not handler:
        notification.status = Notification.Status.FAILED
        notification.failure_reason = f"Unknown channel: {notification.channel}"
        notification.save()
        return {'success': False, 'error': notification.failure_reason}

    try:
        result = handler.delay(str(notification.id))
        return {'success': True, 'task_id': str(result.id)}
    except Exception as e:
        logger.error(f"Failed to queue notification {notification_id}: {e}")
        notification.status = Notification.Status.FAILED
        notification.failure_reason = str(e)
        notification.retry_count += 1
        notification.save()

        # Retry the task
        if notification.retry_count < notification.max_retries:
            raise self.retry(exc=e)

        return {'success': False, 'error': str(e)}


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def send_email_notification(self, notification_id: str) -> Dict[str, Any]:
    """
    Send an email notification.

    Args:
        notification_id: UUID of the notification

    Returns:
        Dict with send result
    """
    from .models import Notification

    try:
        notification = Notification.objects.get(id=notification_id)
    except Notification.DoesNotExist:
        return {'success': False, 'error': 'Notification not found'}

    notification.status = Notification.Status.SENDING
    notification.save()

    try:
        # Get recipient email (would typically come from user service)
        recipient_email = notification.context.get('email')
        if not recipient_email:
            raise ValueError("No recipient email in notification context")

        # Create email
        if notification.body_html:
            email = EmailMultiAlternatives(
                subject=notification.subject,
                body=notification.body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[recipient_email],
            )
            email.attach_alternative(notification.body_html, "text/html")
            email.send(fail_silently=False)
        else:
            send_mail(
                subject=notification.subject,
                message=notification.body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient_email],
                fail_silently=False,
            )

        # Update notification status
        notification.status = Notification.Status.SENT
        notification.sent_at = timezone.now()
        notification.save()

        logger.info(f"Email notification {notification_id} sent to {recipient_email}")
        return {'success': True, 'recipient': recipient_email}

    except Exception as e:
        logger.error(f"Failed to send email notification {notification_id}: {e}")
        notification.status = Notification.Status.FAILED
        notification.failure_reason = str(e)
        notification.retry_count += 1
        notification.save()

        if notification.retry_count < notification.max_retries:
            raise self.retry(exc=e)

        return {'success': False, 'error': str(e)}


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def send_sms_notification(self, notification_id: str) -> Dict[str, Any]:
    """
    Send an SMS notification.

    Uses Twilio or AWS SNS based on configuration.

    Args:
        notification_id: UUID of the notification

    Returns:
        Dict with send result
    """
    from .models import Notification

    try:
        notification = Notification.objects.get(id=notification_id)
    except Notification.DoesNotExist:
        return {'success': False, 'error': 'Notification not found'}

    notification.status = Notification.Status.SENDING
    notification.save()

    try:
        # Get recipient phone number
        phone_number = notification.context.get('phone')
        if not phone_number:
            raise ValueError("No phone number in notification context")

        # Send via configured SMS provider
        sms_provider = getattr(settings, 'SMS_PROVIDER', 'twilio')

        if sms_provider == 'twilio':
            result = _send_twilio_sms(phone_number, notification.body)
        elif sms_provider == 'sns':
            result = _send_sns_sms(phone_number, notification.body)
        else:
            raise ValueError(f"Unknown SMS provider: {sms_provider}")

        notification.status = Notification.Status.SENT
        notification.sent_at = timezone.now()
        notification.metadata['sms_result'] = result
        notification.save()

        logger.info(f"SMS notification {notification_id} sent to {phone_number}")
        return {'success': True, 'recipient': phone_number}

    except Exception as e:
        logger.error(f"Failed to send SMS notification {notification_id}: {e}")
        notification.status = Notification.Status.FAILED
        notification.failure_reason = str(e)
        notification.retry_count += 1
        notification.save()

        if notification.retry_count < notification.max_retries:
            raise self.retry(exc=e)

        return {'success': False, 'error': str(e)}


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def send_push_notification(self, notification_id: str) -> Dict[str, Any]:
    """
    Send a push notification via FCM.

    Args:
        notification_id: UUID of the notification

    Returns:
        Dict with send result
    """
    from .models import Notification, DeviceToken

    try:
        notification = Notification.objects.get(id=notification_id)
    except Notification.DoesNotExist:
        return {'success': False, 'error': 'Notification not found'}

    notification.status = Notification.Status.SENDING
    notification.save()

    try:
        # Get user's device tokens
        device_tokens = DeviceToken.objects.filter(
            user_id=notification.user_id,
            is_active=True
        )

        if not device_tokens.exists():
            raise ValueError("No active device tokens for user")

        success_count = 0
        failure_count = 0

        for device in device_tokens:
            try:
                result = _send_fcm_push(
                    token=device.token,
                    title=notification.subject,
                    body=notification.body,
                    data=notification.context,
                )
                success_count += 1
            except Exception as e:
                logger.warning(f"Failed to send push to device {device.id}: {e}")
                failure_count += 1
                # Mark token as potentially invalid
                if 'NotRegistered' in str(e) or 'InvalidRegistration' in str(e):
                    device.is_active = False
                    device.save()

        if success_count > 0:
            notification.status = Notification.Status.SENT
            notification.sent_at = timezone.now()
            notification.metadata['push_result'] = {
                'success_count': success_count,
                'failure_count': failure_count
            }
        else:
            notification.status = Notification.Status.FAILED
            notification.failure_reason = "Failed to send to all devices"

        notification.save()

        logger.info(f"Push notification {notification_id}: {success_count} sent, {failure_count} failed")
        return {
            'success': success_count > 0,
            'success_count': success_count,
            'failure_count': failure_count
        }

    except Exception as e:
        logger.error(f"Failed to send push notification {notification_id}: {e}")
        notification.status = Notification.Status.FAILED
        notification.failure_reason = str(e)
        notification.retry_count += 1
        notification.save()

        if notification.retry_count < notification.max_retries:
            raise self.retry(exc=e)

        return {'success': False, 'error': str(e)}


@shared_task
def send_in_app_notification(notification_id: str) -> Dict[str, Any]:
    """
    Mark an in-app notification as delivered.

    In-app notifications are stored and fetched by the client,
    so we just mark them as sent.

    Args:
        notification_id: UUID of the notification

    Returns:
        Dict with result
    """
    from .models import Notification

    try:
        notification = Notification.objects.get(id=notification_id)
        notification.status = Notification.Status.SENT
        notification.sent_at = timezone.now()
        notification.save()

        logger.info(f"In-app notification {notification_id} marked as sent")
        return {'success': True}

    except Notification.DoesNotExist:
        return {'success': False, 'error': 'Notification not found'}


@shared_task
def process_scheduled_notifications():
    """
    Process notifications that are scheduled to be sent.
    Runs periodically via Celery Beat.
    """
    from .models import Notification

    now = timezone.now()
    scheduled = Notification.objects.filter(
        status=Notification.Status.PENDING,
        scheduled_at__lte=now
    )

    count = 0
    for notification in scheduled:
        send_notification.delay(str(notification.id))
        count += 1

    logger.info(f"Queued {count} scheduled notifications")
    return {'queued': count}


@shared_task
def retry_failed_notifications():
    """
    Retry notifications that failed but haven't exceeded max retries.
    Runs periodically via Celery Beat.
    """
    from .models import Notification
    from django.db.models import F

    failed = Notification.objects.filter(
        status=Notification.Status.FAILED,
        retry_count__lt=F('max_retries')
    )

    count = 0
    for notification in failed:
        notification.status = Notification.Status.PENDING
        notification.save()
        send_notification.delay(str(notification.id))
        count += 1

    logger.info(f"Retrying {count} failed notifications")
    return {'retried': count}


# =============================================================================
# Provider-specific helpers (stubs - implement with actual SDK)
# =============================================================================

def _send_twilio_sms(phone_number: str, message: str) -> Dict[str, Any]:
    """
    Send SMS via Twilio.

    TODO: Implement with actual Twilio SDK when ready.
    """
    # from twilio.rest import Client
    # client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
    # message = client.messages.create(
    #     body=message,
    #     from_=settings.TWILIO_PHONE_NUMBER,
    #     to=phone_number
    # )
    # return {'sid': message.sid, 'status': message.status}

    logger.warning(f"Twilio SMS not configured. Would send to {phone_number}: {message[:50]}...")
    return {'status': 'simulated'}


def _send_sns_sms(phone_number: str, message: str) -> Dict[str, Any]:
    """
    Send SMS via AWS SNS.

    TODO: Implement with actual boto3 when ready.
    """
    # import boto3
    # client = boto3.client('sns', region_name=settings.AWS_REGION)
    # response = client.publish(
    #     PhoneNumber=phone_number,
    #     Message=message
    # )
    # return {'message_id': response['MessageId']}

    logger.warning(f"AWS SNS SMS not configured. Would send to {phone_number}: {message[:50]}...")
    return {'status': 'simulated'}


def _send_fcm_push(token: str, title: str, body: str, data: Dict = None) -> Dict[str, Any]:
    """
    Send push notification via Firebase Cloud Messaging.

    TODO: Implement with actual firebase-admin SDK when ready.
    """
    # import firebase_admin
    # from firebase_admin import messaging
    #
    # message = messaging.Message(
    #     notification=messaging.Notification(title=title, body=body),
    #     data=data or {},
    #     token=token,
    # )
    # response = messaging.send(message)
    # return {'message_id': response}

    logger.warning(f"FCM not configured. Would send to token {token[:20]}...: {title}")
    return {'status': 'simulated'}
