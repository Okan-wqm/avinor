# services/maintenance-service/src/apps/core/models/maintenance_log.py
"""
Maintenance Log Model

Records of completed maintenance work.
"""

import uuid
from decimal import Decimal
from datetime import date

from django.db import models
from django.utils import timezone


class MaintenanceLog(models.Model):
    """
    Maintenance log entry.

    Records all maintenance work performed on aircraft.
    """

    class Category(models.TextChoices):
        INSPECTION = 'inspection', 'Inspection'
        SERVICE = 'service', 'Service'
        REPAIR = 'repair', 'Repair'
        OVERHAUL = 'overhaul', 'Overhaul'
        MODIFICATION = 'modification', 'Modification'
        AD_COMPLIANCE = 'ad_compliance', 'AD Compliance'
        SB_COMPLIANCE = 'sb_compliance', 'SB Compliance'
        COMPONENT_CHANGE = 'component_change', 'Component Change'

    class MaintenanceType(models.TextChoices):
        SCHEDULED = 'scheduled', 'Scheduled'
        UNSCHEDULED = 'unscheduled', 'Unscheduled'
        AD_COMPLIANCE = 'ad_compliance', 'AD Compliance'
        SB_COMPLIANCE = 'sb_compliance', 'SB Compliance'
        INSPECTION = 'inspection', 'Inspection'
        CORRECTIVE = 'corrective', 'Corrective'

    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        PENDING_APPROVAL = 'pending_approval', 'Pending Approval'
        COMPLETED = 'completed', 'Completed'
        REJECTED = 'rejected', 'Rejected'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization_id = models.UUIDField(db_index=True)
    aircraft_id = models.UUIDField(db_index=True)

    # Related records
    maintenance_item_id = models.UUIDField(blank=True, null=True, db_index=True)
    work_order_id = models.UUIDField(blank=True, null=True, db_index=True)
    squawk_id = models.UUIDField(blank=True, null=True)

    # ==========================================================================
    # Identification
    # ==========================================================================

    log_number = models.CharField(max_length=50, blank=True, null=True)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    work_performed = models.TextField()

    # ==========================================================================
    # Category
    # ==========================================================================

    category = models.CharField(max_length=50, choices=Category.choices)
    maintenance_type = models.CharField(
        max_length=50,
        choices=MaintenanceType.choices,
        blank=True,
        null=True
    )
    ata_chapter = models.CharField(max_length=10, blank=True, null=True)

    # ==========================================================================
    # Date/Time
    # ==========================================================================

    performed_date = models.DateField()
    started_at = models.DateTimeField(blank=True, null=True)
    completed_at = models.DateTimeField(blank=True, null=True)

    # ==========================================================================
    # Aircraft Hours (At time of maintenance)
    # ==========================================================================

    aircraft_hours = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )
    aircraft_cycles = models.IntegerField(blank=True, null=True)
    engine_hours = models.JSONField(
        default=dict, blank=True,
        help_text='Engine hours: {"1": 1234.5, "2": 1234.5}'
    )

    # ==========================================================================
    # Performer
    # ==========================================================================

    performed_by = models.CharField(max_length=255)
    performed_by_id = models.UUIDField(blank=True, null=True)
    technician_license = models.CharField(max_length=100, blank=True, null=True)
    organization_name = models.CharField(max_length=255, blank=True, null=True)
    organization_approval = models.CharField(
        max_length=100, blank=True, null=True,
        help_text='Part-145 approval number'
    )

    # ==========================================================================
    # Certification / Sign-off
    # ==========================================================================

    certified_by = models.CharField(max_length=255, blank=True, null=True)
    certified_by_id = models.UUIDField(blank=True, null=True)
    certification_type = models.CharField(
        max_length=50, blank=True, null=True,
        help_text='CRS - Certificate of Release to Service'
    )
    certification_date = models.DateTimeField(blank=True, null=True)
    certification_reference = models.CharField(max_length=100, blank=True, null=True)

    # ==========================================================================
    # Digital Signature
    # ==========================================================================

    signature_data = models.JSONField(default=dict, blank=True)
    signed_at = models.DateTimeField(blank=True, null=True)
    signed_by_user_id = models.UUIDField(blank=True, null=True)

    # ==========================================================================
    # Parts
    # ==========================================================================

    parts_used = models.JSONField(
        default=list, blank=True,
        help_text='[{"part_number": "xxx", "description": "xxx", "serial_number": "xxx", "quantity": 1, "unit_cost": 100.00, "condition": "new"}]'
    )
    parts_removed = models.JSONField(default=list, blank=True)

    # ==========================================================================
    # Costs
    # ==========================================================================

    labor_hours = models.DecimalField(
        max_digits=6, decimal_places=2, blank=True, null=True
    )
    labor_rate = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )
    labor_cost = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )
    parts_cost = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )
    other_cost = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )
    total_cost = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )

    # ==========================================================================
    # Next Due (Sets next maintenance due)
    # ==========================================================================

    sets_next_due = models.BooleanField(default=True)
    next_due_date = models.DateField(blank=True, null=True)
    next_due_hours = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )
    next_due_cycles = models.IntegerField(blank=True, null=True)

    # ==========================================================================
    # Documents
    # ==========================================================================

    documents = models.JSONField(default=list, blank=True)
    photos = models.JSONField(default=list, blank=True)

    # ==========================================================================
    # Notes
    # ==========================================================================

    notes = models.TextField(blank=True, null=True)
    internal_notes = models.TextField(blank=True, null=True)
    findings = models.TextField(blank=True, null=True, help_text='Issues found during maintenance')

    # ==========================================================================
    # Status
    # ==========================================================================

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.COMPLETED
    )

    # ==========================================================================
    # Timestamps
    # ==========================================================================

    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.UUIDField()
    created_by_name = models.CharField(max_length=255, blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)
    approved_at = models.DateTimeField(blank=True, null=True)
    approved_by = models.UUIDField(blank=True, null=True)
    approved_by_name = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        db_table = 'maintenance_logs'
        ordering = ['-performed_date', '-created_at']
        verbose_name = 'Maintenance Log'
        verbose_name_plural = 'Maintenance Logs'
        indexes = [
            models.Index(fields=['organization_id']),
            models.Index(fields=['aircraft_id']),
            models.Index(fields=['maintenance_item_id']),
            models.Index(fields=['-performed_date']),
            models.Index(fields=['work_order_id']),
        ]

    def __str__(self):
        return f"{self.log_number or 'LOG'}: {self.title}"

    def save(self, *args, **kwargs):
        if not self.log_number:
            self.log_number = self._generate_log_number()
        self._calculate_total_cost()
        super().save(*args, **kwargs)

    def _generate_log_number(self) -> str:
        """Generate log number."""
        year = timezone.now().year
        count = MaintenanceLog.objects.filter(
            organization_id=self.organization_id,
            created_at__year=year
        ).count() + 1
        return f"ML-{year}-{count:05d}"

    def _calculate_total_cost(self) -> None:
        """Calculate total cost from components."""
        labor = self.labor_cost or Decimal('0')
        parts = self.parts_cost or Decimal('0')
        other = self.other_cost or Decimal('0')
        self.total_cost = labor + parts + other

    # ==========================================================================
    # Methods
    # ==========================================================================

    def approve(self, approved_by: uuid.UUID, approved_by_name: str = None) -> None:
        """Approve the maintenance log."""
        self.status = self.Status.COMPLETED
        self.approved_at = timezone.now()
        self.approved_by = approved_by
        self.approved_by_name = approved_by_name
        self.save(update_fields=[
            'status', 'approved_at', 'approved_by', 'approved_by_name', 'updated_at'
        ])

    def reject(self, reason: str) -> None:
        """Reject the maintenance log."""
        self.status = self.Status.REJECTED
        self.internal_notes = f"Rejected: {reason}\n{self.internal_notes or ''}"
        self.save(update_fields=['status', 'internal_notes', 'updated_at'])

    def add_part_used(
        self,
        part_number: str,
        description: str,
        quantity: int = 1,
        serial_number: str = None,
        unit_cost: Decimal = None,
        condition: str = 'new'
    ) -> None:
        """Add a part used in this maintenance."""
        part = {
            'part_number': part_number,
            'description': description,
            'quantity': quantity,
            'condition': condition,
        }
        if serial_number:
            part['serial_number'] = serial_number
        if unit_cost:
            part['unit_cost'] = float(unit_cost)

        self.parts_used.append(part)

        # Update parts cost
        if unit_cost:
            current = self.parts_cost or Decimal('0')
            self.parts_cost = current + (unit_cost * quantity)

        self.save(update_fields=['parts_used', 'parts_cost', 'updated_at'])

    def add_part_removed(
        self,
        part_number: str,
        description: str,
        serial_number: str = None,
        reason: str = None
    ) -> None:
        """Add a part removed during maintenance."""
        part = {
            'part_number': part_number,
            'description': description,
            'removed_at': timezone.now().isoformat(),
        }
        if serial_number:
            part['serial_number'] = serial_number
        if reason:
            part['reason'] = reason

        self.parts_removed.append(part)
        self.save(update_fields=['parts_removed', 'updated_at'])

    def sign(self, user_id: uuid.UUID, signature_data: dict = None) -> None:
        """Digitally sign the maintenance log."""
        self.signed_at = timezone.now()
        self.signed_by_user_id = user_id
        if signature_data:
            self.signature_data = signature_data
        self.save(update_fields=['signed_at', 'signed_by_user_id', 'signature_data', 'updated_at'])

    @classmethod
    def get_aircraft_history(
        cls,
        aircraft_id: uuid.UUID,
        start_date: date = None,
        end_date: date = None,
        category: str = None,
        limit: int = 100
    ):
        """Get maintenance history for an aircraft."""
        queryset = cls.objects.filter(
            aircraft_id=aircraft_id,
            status=cls.Status.COMPLETED
        )

        if start_date:
            queryset = queryset.filter(performed_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(performed_date__lte=end_date)
        if category:
            queryset = queryset.filter(category=category)

        return queryset.order_by('-performed_date')[:limit]
