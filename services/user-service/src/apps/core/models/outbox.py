# services/user-service/src/apps/core/models/outbox.py
"""
Event Outbox Model

Implements the transactional outbox pattern for reliable event publishing.
Failed events are stored here for later retry.
"""

import uuid
from django.db import models


class EventOutbox(models.Model):
    """
    Stores events that failed to publish for later retry.

    This implements the transactional outbox pattern to ensure
    events are eventually published even if the message broker
    is temporarily unavailable.
    """

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        PROCESSING = 'processing', 'Processing'
        COMPLETED = 'completed', 'Completed'
        FAILED = 'failed', 'Failed'
        DEAD_LETTER = 'dead_letter', 'Dead Letter'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event_id = models.CharField(max_length=100, unique=True)
    event_type = models.CharField(max_length=100, db_index=True)
    topic = models.CharField(max_length=100)
    payload = models.JSONField()
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True
    )
    retry_count = models.IntegerField(default=0)
    max_retries = models.IntegerField(default=5)
    error = models.TextField(blank=True, null=True)
    last_error = models.TextField(blank=True, null=True)
    next_retry_at = models.DateTimeField(blank=True, null=True, db_index=True)
    processed_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'event_outbox'
        ordering = ['created_at']
        indexes = [
            models.Index(
                fields=['status', 'next_retry_at'],
                name='idx_outbox_retry'
            ),
            models.Index(
                fields=['event_type', 'created_at'],
                name='idx_outbox_type_created'
            ),
        ]

    def __str__(self):
        return f"{self.event_type} - {self.status}"

    def mark_processing(self):
        """Mark event as being processed."""
        self.status = self.Status.PROCESSING
        self.save(update_fields=['status', 'updated_at'])

    def mark_completed(self):
        """Mark event as successfully processed."""
        from django.utils import timezone
        self.status = self.Status.COMPLETED
        self.processed_at = timezone.now()
        self.save(update_fields=['status', 'processed_at', 'updated_at'])

    def mark_failed(self, error: str):
        """Mark event as failed and schedule retry."""
        from django.utils import timezone
        from datetime import timedelta

        self.retry_count += 1
        self.last_error = error

        if self.retry_count >= self.max_retries:
            self.status = self.Status.DEAD_LETTER
        else:
            self.status = self.Status.PENDING
            # Exponential backoff: 1min, 2min, 4min, 8min, 16min
            delay = timedelta(minutes=2 ** self.retry_count)
            self.next_retry_at = timezone.now() + delay

        self.save(update_fields=[
            'status', 'retry_count', 'last_error', 'next_retry_at', 'updated_at'
        ])

    @classmethod
    def get_pending_events(cls, limit: int = 100):
        """Get events ready for retry."""
        from django.utils import timezone
        from django.db.models import Q

        return cls.objects.filter(
            status=cls.Status.PENDING
        ).filter(
            Q(next_retry_at__isnull=True) | Q(next_retry_at__lte=timezone.now())
        ).order_by('created_at')[:limit]
