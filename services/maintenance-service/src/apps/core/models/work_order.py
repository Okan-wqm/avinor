# services/maintenance-service/src/apps/core/models/work_order.py
"""
Work Order Model

Manages maintenance work orders and tasks.
"""

import uuid
from datetime import date
from decimal import Decimal
from typing import List, Optional

from django.db import models
from django.utils import timezone
from django.contrib.postgres.fields import ArrayField


class WorkOrder(models.Model):
    """
    Work Order for maintenance activities.

    Tracks scheduled and unscheduled maintenance work.
    """

    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        PLANNED = 'planned', 'Planned'
        APPROVED = 'approved', 'Approved'
        IN_PROGRESS = 'in_progress', 'In Progress'
        ON_HOLD = 'on_hold', 'On Hold'
        COMPLETED = 'completed', 'Completed'
        CANCELLED = 'cancelled', 'Cancelled'

    class Priority(models.TextChoices):
        LOW = 'low', 'Low'
        NORMAL = 'normal', 'Normal'
        HIGH = 'high', 'High'
        URGENT = 'urgent', 'Urgent'
        AOG = 'aog', 'Aircraft On Ground'

    class WorkOrderType(models.TextChoices):
        SCHEDULED = 'scheduled_maintenance', 'Scheduled Maintenance'
        UNSCHEDULED = 'unscheduled_maintenance', 'Unscheduled Maintenance'
        INSPECTION = 'inspection', 'Inspection'
        REPAIR = 'repair', 'Repair'
        MODIFICATION = 'modification', 'Modification'
        AD_COMPLIANCE = 'ad_compliance', 'AD Compliance'
        SB_COMPLIANCE = 'sb_compliance', 'SB Compliance'
        ANNUAL = 'annual', 'Annual Inspection'
        HUNDRED_HOUR = '100_hour', '100 Hour Inspection'
        PROGRESSIVE = 'progressive', 'Progressive Inspection'

    class PartsStatus(models.TextChoices):
        PENDING = 'pending', 'Pending'
        ORDERED = 'ordered', 'Ordered'
        PARTIAL = 'partial', 'Partial'
        COMPLETE = 'complete', 'Complete'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization_id = models.UUIDField(db_index=True)
    aircraft_id = models.UUIDField(db_index=True)

    # ==========================================================================
    # Identification
    # ==========================================================================

    work_order_number = models.CharField(max_length=50, unique=True)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)

    work_order_type = models.CharField(
        max_length=50,
        choices=WorkOrderType.choices
    )
    priority = models.CharField(
        max_length=20,
        choices=Priority.choices,
        default=Priority.NORMAL
    )

    # ==========================================================================
    # Planning
    # ==========================================================================

    scheduled_start = models.DateTimeField(blank=True, null=True)
    scheduled_end = models.DateTimeField(blank=True, null=True)
    actual_start = models.DateTimeField(blank=True, null=True)
    actual_end = models.DateTimeField(blank=True, null=True)

    # ==========================================================================
    # Location
    # ==========================================================================

    location_id = models.UUIDField(blank=True, null=True)
    hangar = models.CharField(max_length=100, blank=True, null=True)

    # ==========================================================================
    # Assignment
    # ==========================================================================

    assigned_to = models.UUIDField(blank=True, null=True)
    assigned_to_name = models.CharField(max_length=255, blank=True, null=True)
    assigned_team = models.CharField(max_length=100, blank=True, null=True)

    # ==========================================================================
    # Related Items
    # ==========================================================================

    maintenance_items = ArrayField(
        models.UUIDField(),
        default=list,
        blank=True,
        help_text='Related maintenance item IDs'
    )
    squawk_ids = ArrayField(
        models.UUIDField(),
        default=list,
        blank=True,
        help_text='Related squawk IDs'
    )

    # ==========================================================================
    # Estimates
    # ==========================================================================

    estimated_hours = models.DecimalField(
        max_digits=6, decimal_places=2, blank=True, null=True
    )
    estimated_cost = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )
    estimated_parts_cost = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )

    # ==========================================================================
    # Actual
    # ==========================================================================

    actual_hours = models.DecimalField(
        max_digits=6, decimal_places=2, blank=True, null=True
    )
    actual_cost = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )
    actual_parts_cost = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )

    # ==========================================================================
    # Parts
    # ==========================================================================

    required_parts = models.JSONField(default=list, blank=True)
    parts_status = models.CharField(
        max_length=20,
        choices=PartsStatus.choices,
        default=PartsStatus.PENDING
    )

    # ==========================================================================
    # Approval
    # ==========================================================================

    requires_approval = models.BooleanField(default=False)
    approved_by = models.UUIDField(blank=True, null=True)
    approved_by_name = models.CharField(max_length=255, blank=True, null=True)
    approved_at = models.DateTimeField(blank=True, null=True)
    approval_notes = models.TextField(blank=True, null=True)

    # ==========================================================================
    # Status
    # ==========================================================================

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT
    )
    on_hold_reason = models.TextField(blank=True, null=True)
    cancellation_reason = models.TextField(blank=True, null=True)

    # ==========================================================================
    # Customer Approval (External maintenance)
    # ==========================================================================

    customer_approved = models.BooleanField(default=False)
    customer_approved_at = models.DateTimeField(blank=True, null=True)
    customer_approval_ref = models.CharField(max_length=100, blank=True, null=True)

    # ==========================================================================
    # Result
    # ==========================================================================

    completion_notes = models.TextField(blank=True, null=True)
    findings = models.TextField(blank=True, null=True)
    recommendations = models.TextField(blank=True, null=True)

    # ==========================================================================
    # Aircraft Hours at completion
    # ==========================================================================

    aircraft_hours_start = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )
    aircraft_hours_end = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )

    # ==========================================================================
    # Documents
    # ==========================================================================

    documents = models.JSONField(default=list, blank=True)

    # ==========================================================================
    # Timestamps
    # ==========================================================================

    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.UUIDField()
    created_by_name = models.CharField(max_length=255, blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    completed_by = models.UUIDField(blank=True, null=True)
    completed_by_name = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        db_table = 'work_orders'
        ordering = ['-created_at']
        verbose_name = 'Work Order'
        verbose_name_plural = 'Work Orders'
        indexes = [
            models.Index(fields=['organization_id']),
            models.Index(fields=['aircraft_id']),
            models.Index(fields=['status']),
            models.Index(fields=['scheduled_start']),
            models.Index(fields=['work_order_number']),
            models.Index(fields=['priority']),
        ]

    def __str__(self):
        return f"{self.work_order_number}: {self.title}"

    def save(self, *args, **kwargs):
        if not self.work_order_number:
            self.work_order_number = self._generate_work_order_number()
        super().save(*args, **kwargs)

    def _generate_work_order_number(self) -> str:
        """Generate unique work order number."""
        year = timezone.now().year
        count = WorkOrder.objects.filter(
            organization_id=self.organization_id,
            created_at__year=year
        ).count() + 1
        return f"WO-{year}-{count:05d}"

    # ==========================================================================
    # Properties
    # ==========================================================================

    @property
    def is_open(self) -> bool:
        return self.status in [
            self.Status.DRAFT,
            self.Status.PLANNED,
            self.Status.APPROVED,
            self.Status.IN_PROGRESS,
            self.Status.ON_HOLD
        ]

    @property
    def is_overdue(self) -> bool:
        if not self.scheduled_end:
            return False
        return self.is_open and self.scheduled_end < timezone.now()

    @property
    def duration_hours(self) -> Optional[Decimal]:
        """Get actual duration in hours."""
        if self.actual_start and self.actual_end:
            delta = self.actual_end - self.actual_start
            return Decimal(delta.total_seconds() / 3600).quantize(Decimal('0.01'))
        return None

    @property
    def total_cost(self) -> Decimal:
        """Calculate total cost."""
        labor = self.actual_cost or Decimal('0')
        parts = self.actual_parts_cost or Decimal('0')
        return labor + parts

    # ==========================================================================
    # Workflow Methods
    # ==========================================================================

    def plan(self, scheduled_start, scheduled_end=None) -> None:
        """Schedule the work order."""
        self.status = self.Status.PLANNED
        self.scheduled_start = scheduled_start
        self.scheduled_end = scheduled_end
        self.save(update_fields=['status', 'scheduled_start', 'scheduled_end', 'updated_at'])

    def approve(self, approved_by: uuid.UUID, approved_by_name: str = None, notes: str = None) -> None:
        """Approve the work order."""
        self.status = self.Status.APPROVED
        self.approved_by = approved_by
        self.approved_by_name = approved_by_name
        self.approved_at = timezone.now()
        self.approval_notes = notes
        self.save(update_fields=[
            'status', 'approved_by', 'approved_by_name', 'approved_at',
            'approval_notes', 'updated_at'
        ])

    def start(self, started_by: uuid.UUID = None, aircraft_hours: Decimal = None) -> None:
        """Start work on the work order."""
        self.status = self.Status.IN_PROGRESS
        self.actual_start = timezone.now()
        if aircraft_hours:
            self.aircraft_hours_start = aircraft_hours
        self.save(update_fields=['status', 'actual_start', 'aircraft_hours_start', 'updated_at'])

    def hold(self, reason: str) -> None:
        """Put work order on hold."""
        self.status = self.Status.ON_HOLD
        self.on_hold_reason = reason
        self.save(update_fields=['status', 'on_hold_reason', 'updated_at'])

    def resume(self) -> None:
        """Resume work order from hold."""
        self.status = self.Status.IN_PROGRESS
        self.on_hold_reason = None
        self.save(update_fields=['status', 'on_hold_reason', 'updated_at'])

    def complete(
        self,
        completed_by: uuid.UUID,
        completed_by_name: str = None,
        notes: str = None,
        findings: str = None,
        aircraft_hours: Decimal = None
    ) -> None:
        """Complete the work order."""
        self.status = self.Status.COMPLETED
        self.completed_at = timezone.now()
        self.actual_end = timezone.now()
        self.completed_by = completed_by
        self.completed_by_name = completed_by_name
        self.completion_notes = notes
        self.findings = findings
        if aircraft_hours:
            self.aircraft_hours_end = aircraft_hours
        self.save()

    def cancel(self, reason: str, cancelled_by: uuid.UUID = None) -> None:
        """Cancel the work order."""
        self.status = self.Status.CANCELLED
        self.cancellation_reason = reason
        self.save(update_fields=['status', 'cancellation_reason', 'updated_at'])

    def add_maintenance_item(self, item_id: uuid.UUID) -> None:
        """Add a maintenance item to this work order."""
        if item_id not in self.maintenance_items:
            self.maintenance_items.append(item_id)
            self.save(update_fields=['maintenance_items', 'updated_at'])

    def add_squawk(self, squawk_id: uuid.UUID) -> None:
        """Add a squawk to this work order."""
        if squawk_id not in self.squawk_ids:
            self.squawk_ids.append(squawk_id)
            self.save(update_fields=['squawk_ids', 'updated_at'])


class WorkOrderTask(models.Model):
    """
    Individual task within a work order.
    """

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        IN_PROGRESS = 'in_progress', 'In Progress'
        COMPLETED = 'completed', 'Completed'
        SKIPPED = 'skipped', 'Skipped'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    work_order = models.ForeignKey(
        WorkOrder,
        on_delete=models.CASCADE,
        related_name='tasks'
    )

    # Task details
    sequence = models.IntegerField(default=0)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    instructions = models.TextField(blank=True, null=True)

    # Related maintenance item
    maintenance_item_id = models.UUIDField(blank=True, null=True)

    # Estimates
    estimated_hours = models.DecimalField(
        max_digits=6, decimal_places=2, blank=True, null=True
    )

    # Actual
    actual_hours = models.DecimalField(
        max_digits=6, decimal_places=2, blank=True, null=True
    )

    # Status
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )

    # Completion
    completed_at = models.DateTimeField(blank=True, null=True)
    completed_by = models.UUIDField(blank=True, null=True)
    completion_notes = models.TextField(blank=True, null=True)

    # Sign-off
    signed_off = models.BooleanField(default=False)
    signed_off_by = models.UUIDField(blank=True, null=True)
    signed_off_at = models.DateTimeField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'work_order_tasks'
        ordering = ['work_order', 'sequence']

    def __str__(self):
        return f"{self.work_order.work_order_number} - {self.sequence}: {self.title}"

    def complete(self, completed_by: uuid.UUID, notes: str = None, hours: Decimal = None) -> None:
        """Mark task as completed."""
        self.status = self.Status.COMPLETED
        self.completed_at = timezone.now()
        self.completed_by = completed_by
        self.completion_notes = notes
        if hours:
            self.actual_hours = hours
        self.save()

    def sign_off(self, signed_by: uuid.UUID) -> None:
        """Sign off on the completed task."""
        self.signed_off = True
        self.signed_off_by = signed_by
        self.signed_off_at = timezone.now()
        self.save(update_fields=['signed_off', 'signed_off_by', 'signed_off_at', 'updated_at'])
