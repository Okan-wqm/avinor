"""
Batch Service.

Business logic for batch notification operations.
"""
import logging
from typing import Optional, List, Dict
from uuid import UUID

from django.db import transaction
from django.db.models import QuerySet
from django.utils import timezone

from ..models import NotificationBatch, Notification
from ..exceptions import BatchNotFound
from ..constants import STATUS_PENDING, BATCH_CHUNK_SIZE

logger = logging.getLogger(__name__)


class BatchService:
    """Service for managing batch notifications."""

    @staticmethod
    def get_by_id(batch_id: UUID, organization_id: UUID) -> NotificationBatch:
        """Get batch by ID."""
        try:
            return NotificationBatch.objects.select_related('template').get(
                id=batch_id,
                organization_id=organization_id
            )
        except NotificationBatch.DoesNotExist:
            raise BatchNotFound()

    @staticmethod
    def get_list(organization_id: UUID) -> QuerySet[NotificationBatch]:
        """Get list of batches for an organization."""
        return NotificationBatch.objects.filter(
            organization_id=organization_id
        ).select_related('template').order_by('-created_at')

    @staticmethod
    @transaction.atomic
    def create(
        organization_id: UUID,
        template_id: UUID,
        created_by_id: UUID,
        name: str,
        recipient_user_ids: List[UUID],
        context: Dict = None,
        description: str = "",
        scheduled_at: Optional[str] = None,
    ) -> NotificationBatch:
        """Create a new batch."""
        batch = NotificationBatch.objects.create(
            organization_id=organization_id,
            template_id=template_id,
            created_by_id=created_by_id,
            name=name,
            description=description,
            recipient_filter={'user_ids': [str(uid) for uid in recipient_user_ids]},
            recipient_count=len(recipient_user_ids),
            context=context or {},
            scheduled_at=scheduled_at,
            status=STATUS_PENDING,
        )

        logger.info(f"Created batch {batch.id} with {len(recipient_user_ids)} recipients")
        return batch

    @staticmethod
    @transaction.atomic
    def process(batch: NotificationBatch) -> Dict:
        """Process a batch, creating individual notifications."""
        from .notification_service import NotificationService

        batch.status = 'processing'
        batch.started_at = timezone.now()
        batch.save()

        user_ids = batch.recipient_filter.get('user_ids', [])
        sent = 0
        failed = 0

        for user_id in user_ids:
            try:
                NotificationService.create_from_template(
                    user_id=UUID(user_id),
                    template_code=batch.template.code,
                    context=batch.context,
                    organization_id=batch.organization_id,
                )
                sent += 1
            except Exception as e:
                logger.error(f"Failed to create notification for {user_id}: {e}")
                failed += 1

        batch.sent_count = sent
        batch.failed_count = failed
        batch.status = 'completed'
        batch.completed_at = timezone.now()
        batch.save()

        logger.info(f"Processed batch {batch.id}: {sent} sent, {failed} failed")
        return {'sent': sent, 'failed': failed}

    @staticmethod
    def get_pending() -> QuerySet[NotificationBatch]:
        """Get pending batches ready to process."""
        now = timezone.now()
        return NotificationBatch.objects.filter(
            status=STATUS_PENDING,
        ).filter(
            scheduled_at__isnull=True
        ).union(
            NotificationBatch.objects.filter(
                status=STATUS_PENDING,
                scheduled_at__lte=now,
            )
        )

    @staticmethod
    @transaction.atomic
    def cancel(batch_id: UUID, organization_id: UUID) -> NotificationBatch:
        """Cancel a pending batch."""
        batch = BatchService.get_by_id(batch_id, organization_id)

        if batch.status != STATUS_PENDING:
            raise ValueError("Only pending batches can be cancelled")

        batch.status = 'cancelled'
        batch.save()

        logger.info(f"Cancelled batch {batch_id}")
        return batch
