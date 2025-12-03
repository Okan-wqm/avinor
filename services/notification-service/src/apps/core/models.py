"""Notification Service Models."""
import uuid
from django.db import models
from shared.common.mixins import UUIDPrimaryKeyMixin, TimestampMixin


class NotificationTemplate(UUIDPrimaryKeyMixin, TimestampMixin, models.Model):
    """Email/SMS notification templates."""

    class TemplateType(models.TextChoices):
        EMAIL = 'email', 'Email'
        SMS = 'sms', 'SMS'
        PUSH = 'push', 'Push Notification'
        IN_APP = 'in_app', 'In-App'

    organization_id = models.UUIDField(null=True, blank=True)  # Null for system templates

    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50, unique=True)
    template_type = models.CharField(max_length=10, choices=TemplateType.choices, default=TemplateType.EMAIL)
    description = models.TextField(blank=True)

    # Email specifics
    subject = models.CharField(max_length=255, blank=True)
    body_html = models.TextField(blank=True)
    body_text = models.TextField(blank=True)

    # Variables
    variables = models.JSONField(default=list, blank=True)  # List of available variables

    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'notification_templates'
        ordering = ['name']


class Notification(UUIDPrimaryKeyMixin, TimestampMixin, models.Model):
    """Individual notification record."""

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        SENT = 'sent', 'Sent'
        DELIVERED = 'delivered', 'Delivered'
        READ = 'read', 'Read'
        FAILED = 'failed', 'Failed'

    class Channel(models.TextChoices):
        EMAIL = 'email', 'Email'
        SMS = 'sms', 'SMS'
        PUSH = 'push', 'Push Notification'
        IN_APP = 'in_app', 'In-App'

    class Priority(models.TextChoices):
        LOW = 'low', 'Low'
        NORMAL = 'normal', 'Normal'
        HIGH = 'high', 'High'
        URGENT = 'urgent', 'Urgent'

    user_id = models.UUIDField()
    organization_id = models.UUIDField(null=True, blank=True)
    template = models.ForeignKey(NotificationTemplate, on_delete=models.SET_NULL, null=True, blank=True)

    channel = models.CharField(max_length=10, choices=Channel.choices, default=Channel.EMAIL)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    priority = models.CharField(max_length=10, choices=Priority.choices, default=Priority.NORMAL)

    # Content
    subject = models.CharField(max_length=255, blank=True)
    body = models.TextField()
    body_html = models.TextField(blank=True)

    # Recipient info
    recipient_email = models.EmailField(blank=True)
    recipient_phone = models.CharField(max_length=20, blank=True)

    # Metadata
    context = models.JSONField(default=dict, blank=True)  # Template variables
    metadata = models.JSONField(default=dict, blank=True)  # Additional data

    # Tracking
    scheduled_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)
    failure_reason = models.TextField(blank=True)

    # Retry
    retry_count = models.IntegerField(default=0)
    max_retries = models.IntegerField(default=3)
    next_retry_at = models.DateTimeField(null=True, blank=True)

    # External references
    external_id = models.CharField(max_length=255, blank=True)  # Provider message ID

    class Meta:
        db_table = 'notifications'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user_id', '-created_at']),
            models.Index(fields=['status']),
            models.Index(fields=['channel']),
            models.Index(fields=['scheduled_at']),
        ]


class NotificationPreference(UUIDPrimaryKeyMixin, TimestampMixin, models.Model):
    """User notification preferences."""

    user_id = models.UUIDField()

    # Channel preferences
    email_enabled = models.BooleanField(default=True)
    sms_enabled = models.BooleanField(default=False)
    push_enabled = models.BooleanField(default=True)
    in_app_enabled = models.BooleanField(default=True)

    # Category preferences (JSON for flexibility)
    category_preferences = models.JSONField(default=dict, blank=True)
    # e.g., {'booking_reminders': True, 'marketing': False}

    # Quiet hours
    quiet_hours_enabled = models.BooleanField(default=False)
    quiet_hours_start = models.TimeField(null=True, blank=True)
    quiet_hours_end = models.TimeField(null=True, blank=True)
    timezone = models.CharField(max_length=50, default='UTC')

    class Meta:
        db_table = 'notification_preferences'
        unique_together = ['user_id']


class DeviceToken(UUIDPrimaryKeyMixin, TimestampMixin, models.Model):
    """Push notification device tokens."""

    class Platform(models.TextChoices):
        IOS = 'ios', 'iOS'
        ANDROID = 'android', 'Android'
        WEB = 'web', 'Web'

    user_id = models.UUIDField()
    token = models.TextField()
    platform = models.CharField(max_length=10, choices=Platform.choices)
    device_name = models.CharField(max_length=255, blank=True)

    is_active = models.BooleanField(default=True)
    last_used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'device_tokens'
        unique_together = ['user_id', 'token']
        indexes = [
            models.Index(fields=['user_id', 'is_active']),
        ]


class NotificationBatch(UUIDPrimaryKeyMixin, TimestampMixin, models.Model):
    """Batch notification job."""

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        PROCESSING = 'processing', 'Processing'
        COMPLETED = 'completed', 'Completed'
        FAILED = 'failed', 'Failed'

    organization_id = models.UUIDField()
    template = models.ForeignKey(NotificationTemplate, on_delete=models.PROTECT)
    created_by_id = models.UUIDField()

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    scheduled_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # Recipients
    recipient_filter = models.JSONField(default=dict, blank=True)  # Filter criteria
    recipient_count = models.IntegerField(default=0)

    # Progress
    sent_count = models.IntegerField(default=0)
    failed_count = models.IntegerField(default=0)

    # Context
    context = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'notification_batches'
        ordering = ['-created_at']
