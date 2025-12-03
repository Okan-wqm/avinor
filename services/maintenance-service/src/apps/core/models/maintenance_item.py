# services/maintenance-service/src/apps/core/models/maintenance_item.py
"""
Maintenance Item Model

Defines maintenance requirements, intervals, and tracking.
"""

import uuid
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional, Dict, Any

from django.db import models
from django.utils import timezone


class MaintenanceItem(models.Model):
    """
    Maintenance item/requirement definition.

    Tracks recurring inspections, services, overhauls, ADs, SBs, and life-limited parts.
    """

    class Category(models.TextChoices):
        INSPECTION = 'inspection', 'Inspection'
        SERVICE = 'service', 'Service'
        OVERHAUL = 'overhaul', 'Overhaul'
        REPLACEMENT = 'replacement', 'Replacement'
        AD = 'ad', 'Airworthiness Directive'
        SB = 'sb', 'Service Bulletin'
        LIFE_LIMITED = 'life_limited', 'Life Limited Part'
        CALIBRATION = 'calibration', 'Calibration'
        OPERATIONAL_CHECK = 'operational_check', 'Operational Check'

    class ItemType(models.TextChoices):
        RECURRING = 'recurring', 'Recurring'
        ONE_TIME = 'one_time', 'One Time'
        ON_CONDITION = 'on_condition', 'On Condition'

    class ComponentType(models.TextChoices):
        AIRFRAME = 'airframe', 'Airframe'
        ENGINE = 'engine', 'Engine'
        PROPELLER = 'propeller', 'Propeller'
        AVIONICS = 'avionics', 'Avionics'
        LANDING_GEAR = 'landing_gear', 'Landing Gear'
        INSTRUMENTS = 'instruments', 'Instruments'
        FUEL_SYSTEM = 'fuel_system', 'Fuel System'
        HYDRAULICS = 'hydraulics', 'Hydraulics'
        ELECTRICAL = 'electrical', 'Electrical'
        OTHER = 'other', 'Other'

    class ComplianceStatus(models.TextChoices):
        COMPLIANT = 'compliant', 'Compliant'
        DUE_SOON = 'due_soon', 'Due Soon'
        DUE = 'due', 'Due'
        OVERDUE = 'overdue', 'Overdue'
        DEFERRED = 'deferred', 'Deferred'
        NOT_APPLICABLE = 'not_applicable', 'Not Applicable'

    class Status(models.TextChoices):
        ACTIVE = 'active', 'Active'
        INACTIVE = 'inactive', 'Inactive'
        COMPLETED = 'completed', 'Completed'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization_id = models.UUIDField(db_index=True)
    aircraft_id = models.UUIDField(db_index=True, blank=True, null=True)  # NULL = template

    # ==========================================================================
    # Identification
    # ==========================================================================

    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50, blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    category = models.CharField(max_length=50, choices=Category.choices)
    item_type = models.CharField(
        max_length=50,
        choices=ItemType.choices,
        default=ItemType.RECURRING
    )
    ata_chapter = models.CharField(max_length=10, blank=True, null=True)

    # ==========================================================================
    # Component (Optional)
    # ==========================================================================

    component_type = models.CharField(
        max_length=50,
        choices=ComponentType.choices,
        blank=True,
        null=True
    )
    component_id = models.UUIDField(blank=True, null=True)  # engine_id or propeller_id

    # ==========================================================================
    # Regulatory
    # ==========================================================================

    is_mandatory = models.BooleanField(default=True)
    regulatory_reference = models.CharField(max_length=255, blank=True, null=True)
    ad_number = models.CharField(max_length=100, blank=True, null=True)
    sb_number = models.CharField(max_length=100, blank=True, null=True)

    # ==========================================================================
    # Intervals
    # ==========================================================================

    interval_hours = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True,
        help_text='Interval in flight hours'
    )
    interval_cycles = models.IntegerField(blank=True, null=True)
    interval_days = models.IntegerField(blank=True, null=True)
    interval_months = models.IntegerField(blank=True, null=True)
    interval_calendar_months = models.IntegerField(blank=True, null=True)

    # ==========================================================================
    # Life Limits
    # ==========================================================================

    life_limit_hours = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )
    life_limit_cycles = models.IntegerField(blank=True, null=True)
    life_limit_months = models.IntegerField(blank=True, null=True)

    # ==========================================================================
    # Tolerance
    # ==========================================================================

    tolerance_hours = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )
    tolerance_days = models.IntegerField(blank=True, null=True)
    tolerance_percent = models.DecimalField(
        max_digits=5, decimal_places=2, blank=True, null=True
    )

    # ==========================================================================
    # Warning Thresholds
    # ==========================================================================

    warning_hours = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal('10.00')
    )
    warning_days = models.IntegerField(default=30)
    critical_hours = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal('5.00')
    )
    critical_days = models.IntegerField(default=7)

    # ==========================================================================
    # Last Done
    # ==========================================================================

    last_done_date = models.DateField(blank=True, null=True)
    last_done_hours = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )
    last_done_cycles = models.IntegerField(blank=True, null=True)
    last_done_by = models.CharField(max_length=255, blank=True, null=True)
    last_done_notes = models.TextField(blank=True, null=True)
    last_work_order_id = models.UUIDField(blank=True, null=True)

    # ==========================================================================
    # Next Due
    # ==========================================================================

    next_due_date = models.DateField(blank=True, null=True)
    next_due_hours = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )
    next_due_cycles = models.IntegerField(blank=True, null=True)

    # ==========================================================================
    # Remaining (Calculated)
    # ==========================================================================

    remaining_hours = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )
    remaining_days = models.IntegerField(blank=True, null=True)
    remaining_cycles = models.IntegerField(blank=True, null=True)
    remaining_percent = models.DecimalField(
        max_digits=5, decimal_places=2, blank=True, null=True
    )

    # ==========================================================================
    # Status
    # ==========================================================================

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE
    )
    compliance_status = models.CharField(
        max_length=20,
        choices=ComplianceStatus.choices,
        default=ComplianceStatus.COMPLIANT
    )

    # ==========================================================================
    # Estimates
    # ==========================================================================

    estimated_labor_hours = models.DecimalField(
        max_digits=6, decimal_places=2, blank=True, null=True
    )
    estimated_cost = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )
    estimated_downtime_hours = models.IntegerField(blank=True, null=True)

    # ==========================================================================
    # Documentation
    # ==========================================================================

    documentation_url = models.URLField(max_length=500, blank=True, null=True)
    compliance_doc_url = models.URLField(max_length=500, blank=True, null=True)

    # ==========================================================================
    # Notes
    # ==========================================================================

    notes = models.TextField(blank=True, null=True)
    internal_notes = models.TextField(blank=True, null=True)

    # ==========================================================================
    # Metadata
    # ==========================================================================

    metadata = models.JSONField(default=dict, blank=True)

    # ==========================================================================
    # Timestamps
    # ==========================================================================

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'maintenance_items'
        ordering = ['next_due_hours', 'next_due_date']
        verbose_name = 'Maintenance Item'
        verbose_name_plural = 'Maintenance Items'
        indexes = [
            models.Index(fields=['organization_id']),
            models.Index(fields=['aircraft_id']),
            models.Index(fields=['status']),
            models.Index(fields=['compliance_status']),
            models.Index(fields=['next_due_date', 'next_due_hours']),
            models.Index(fields=['category']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['aircraft_id', 'code'],
                condition=models.Q(code__isnull=False),
                name='unique_aircraft_maintenance_code'
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.code or '-'})"

    # ==========================================================================
    # Properties
    # ==========================================================================

    @property
    def is_template(self) -> bool:
        """Check if this is a template (no aircraft assigned)."""
        return self.aircraft_id is None

    @property
    def is_overdue(self) -> bool:
        return self.compliance_status == self.ComplianceStatus.OVERDUE

    @property
    def is_due(self) -> bool:
        return self.compliance_status in [
            self.ComplianceStatus.DUE,
            self.ComplianceStatus.OVERDUE
        ]

    @property
    def due_type(self) -> Optional[str]:
        """Get which limit type is driving the due status."""
        if self.remaining_hours is not None and self.remaining_hours <= 0:
            return 'hours'
        if self.remaining_days is not None and self.remaining_days <= 0:
            return 'calendar'
        if self.remaining_cycles is not None and self.remaining_cycles <= 0:
            return 'cycles'
        return None

    # ==========================================================================
    # Methods
    # ==========================================================================

    def calculate_remaining(
        self,
        current_hours: Decimal = None,
        current_cycles: int = None
    ) -> None:
        """
        Calculate remaining time/cycles until due.

        Updates remaining_hours, remaining_days, remaining_cycles, and compliance_status.
        """
        # Hours remaining
        if self.next_due_hours and current_hours is not None:
            self.remaining_hours = self.next_due_hours - current_hours
            if self.interval_hours:
                self.remaining_percent = (
                    self.remaining_hours / self.interval_hours * 100
                )

        # Days remaining
        if self.next_due_date:
            self.remaining_days = (self.next_due_date - date.today()).days

        # Cycles remaining
        if self.next_due_cycles and current_cycles is not None:
            self.remaining_cycles = self.next_due_cycles - current_cycles

        self._update_compliance_status()
        self.save(update_fields=[
            'remaining_hours', 'remaining_days', 'remaining_cycles',
            'remaining_percent', 'compliance_status', 'updated_at'
        ])

    def _update_compliance_status(self) -> None:
        """Update compliance status based on remaining values."""
        is_overdue = False
        is_due = False
        is_due_soon = False

        # Check hours
        if self.remaining_hours is not None:
            if self.remaining_hours <= 0:
                is_overdue = True
            elif self.remaining_hours <= self.critical_hours:
                is_due = True
            elif self.remaining_hours <= self.warning_hours:
                is_due_soon = True

        # Check days
        if self.remaining_days is not None:
            if self.remaining_days < 0:
                is_overdue = True
            elif self.remaining_days <= self.critical_days:
                is_due = True
            elif self.remaining_days <= self.warning_days:
                is_due_soon = True

        # Check cycles
        if self.remaining_cycles is not None and self.remaining_cycles <= 0:
            is_overdue = True

        # Set status (most severe wins)
        if is_overdue:
            self.compliance_status = self.ComplianceStatus.OVERDUE
        elif is_due:
            self.compliance_status = self.ComplianceStatus.DUE
        elif is_due_soon:
            self.compliance_status = self.ComplianceStatus.DUE_SOON
        else:
            self.compliance_status = self.ComplianceStatus.COMPLIANT

    def record_compliance(
        self,
        done_date: date,
        done_hours: Decimal = None,
        done_cycles: int = None,
        done_by: str = None,
        notes: str = None,
        work_order_id: uuid.UUID = None
    ) -> None:
        """Record that maintenance was performed."""
        self.last_done_date = done_date
        self.last_done_hours = done_hours
        self.last_done_cycles = done_cycles
        self.last_done_by = done_by
        self.last_done_notes = notes
        self.last_work_order_id = work_order_id

        # Calculate next due
        self._calculate_next_due(done_date, done_hours, done_cycles)

        # Recalculate remaining
        if done_hours:
            self.calculate_remaining(current_hours=done_hours, current_cycles=done_cycles)
        else:
            self.calculate_remaining()

    def _calculate_next_due(
        self,
        done_date: date,
        done_hours: Decimal = None,
        done_cycles: int = None
    ) -> None:
        """Calculate next due dates/hours based on intervals."""
        # Hours-based interval
        if self.interval_hours and done_hours:
            self.next_due_hours = done_hours + self.interval_hours

        # Cycles-based interval
        if self.interval_cycles and done_cycles:
            self.next_due_cycles = done_cycles + self.interval_cycles

        # Calendar-based interval
        if self.interval_days:
            self.next_due_date = done_date + timedelta(days=self.interval_days)
        elif self.interval_months:
            from dateutil.relativedelta import relativedelta
            self.next_due_date = done_date + relativedelta(months=self.interval_months)
        elif self.interval_calendar_months:
            from dateutil.relativedelta import relativedelta
            self.next_due_date = done_date + relativedelta(months=self.interval_calendar_months)

    def defer(self, reason: str, deferred_by: uuid.UUID) -> None:
        """Defer this maintenance item."""
        self.compliance_status = self.ComplianceStatus.DEFERRED
        self.internal_notes = f"Deferred: {reason}\n{self.internal_notes or ''}"
        self.save(update_fields=['compliance_status', 'internal_notes', 'updated_at'])

    @classmethod
    def create_from_template(
        cls,
        template: 'MaintenanceItem',
        aircraft_id: uuid.UUID,
        initial_hours: Decimal = None,
        initial_date: date = None
    ) -> 'MaintenanceItem':
        """Create a maintenance item for an aircraft from a template."""
        item = cls(
            organization_id=template.organization_id,
            aircraft_id=aircraft_id,
            name=template.name,
            code=template.code,
            description=template.description,
            category=template.category,
            item_type=template.item_type,
            ata_chapter=template.ata_chapter,
            component_type=template.component_type,
            is_mandatory=template.is_mandatory,
            regulatory_reference=template.regulatory_reference,
            interval_hours=template.interval_hours,
            interval_cycles=template.interval_cycles,
            interval_days=template.interval_days,
            interval_months=template.interval_months,
            warning_hours=template.warning_hours,
            warning_days=template.warning_days,
            critical_hours=template.critical_hours,
            critical_days=template.critical_days,
            estimated_labor_hours=template.estimated_labor_hours,
            estimated_cost=template.estimated_cost,
            documentation_url=template.documentation_url,
            notes=template.notes,
        )

        # Set initial compliance
        if initial_date:
            item.last_done_date = initial_date
        if initial_hours:
            item.last_done_hours = initial_hours

        item._calculate_next_due(
            initial_date or date.today(),
            initial_hours,
            None
        )
        item.save()
        return item

    @classmethod
    def get_due_items(
        cls,
        organization_id: uuid.UUID,
        aircraft_id: uuid.UUID = None
    ):
        """Get all due and overdue maintenance items."""
        queryset = cls.objects.filter(
            organization_id=organization_id,
            status=cls.Status.ACTIVE,
            compliance_status__in=[
                cls.ComplianceStatus.DUE,
                cls.ComplianceStatus.OVERDUE
            ]
        )
        if aircraft_id:
            queryset = queryset.filter(aircraft_id=aircraft_id)
        return queryset.order_by('compliance_status', 'remaining_hours')

    @classmethod
    def get_upcoming(
        cls,
        organization_id: uuid.UUID,
        aircraft_id: uuid.UUID = None,
        hours_ahead: int = 50,
        days_ahead: int = 90
    ):
        """Get upcoming maintenance items."""
        queryset = cls.objects.filter(
            organization_id=organization_id,
            status=cls.Status.ACTIVE
        ).exclude(
            compliance_status=cls.ComplianceStatus.OVERDUE
        )

        if aircraft_id:
            queryset = queryset.filter(aircraft_id=aircraft_id)

        # Filter by remaining hours or days
        from django.db.models import Q
        queryset = queryset.filter(
            Q(remaining_hours__lte=hours_ahead) |
            Q(remaining_days__lte=days_ahead)
        )

        return queryset.order_by('remaining_hours', 'remaining_days')
