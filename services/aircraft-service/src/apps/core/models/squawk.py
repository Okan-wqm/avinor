# services/aircraft-service/src/apps/core/models/squawk.py
"""
Aircraft Squawk Model

Discrepancy/defect reporting and tracking system.
"""

import uuid
from decimal import Decimal
from datetime import date, timedelta
from typing import Optional

from django.db import models
from django.utils import timezone


class AircraftSquawk(models.Model):
    """
    Aircraft squawk (discrepancy/defect) model.

    Supports:
    - Pilot-reported discrepancies
    - Severity levels (minor to AOG)
    - MEL/CDL items
    - Deferral management
    - Resolution tracking
    - Work order integration
    """

    # ==========================================================================
    # Enums
    # ==========================================================================

    class Category(models.TextChoices):
        ENGINE = 'engine', 'Engine'
        AIRFRAME = 'airframe', 'Airframe'
        AVIONICS = 'avionics', 'Avionics'
        INSTRUMENTS = 'instruments', 'Instruments'
        ELECTRICAL = 'electrical', 'Electrical'
        LANDING_GEAR = 'landing_gear', 'Landing Gear'
        FLIGHT_CONTROLS = 'flight_controls', 'Flight Controls'
        FUEL = 'fuel', 'Fuel System'
        HYDRAULIC = 'hydraulic', 'Hydraulic'
        PROPELLER = 'propeller', 'Propeller'
        INTERIOR = 'interior', 'Interior'
        EXTERIOR = 'exterior', 'Exterior'
        OTHER = 'other', 'Other'

    class Severity(models.TextChoices):
        MINOR = 'minor', 'Minor'
        MAJOR = 'major', 'Major'
        GROUNDING = 'grounding', 'Grounding'
        AOG = 'aog', 'Aircraft on Ground'

    class Priority(models.TextChoices):
        LOW = 'low', 'Low'
        NORMAL = 'normal', 'Normal'
        HIGH = 'high', 'High'
        URGENT = 'urgent', 'Urgent'

    class Status(models.TextChoices):
        OPEN = 'open', 'Open'
        IN_PROGRESS = 'in_progress', 'In Progress'
        DEFERRED = 'deferred', 'Deferred'
        RESOLVED = 'resolved', 'Resolved'
        CLOSED = 'closed', 'Closed'
        CANCELLED = 'cancelled', 'Cancelled'

    class MELCategory(models.TextChoices):
        A = 'A', 'Category A - No time limit'
        B = 'B', 'Category B - 3 days'
        C = 'C', 'Category C - 10 days'
        D = 'D', 'Category D - 120 days'

    # ==========================================================================
    # Primary Key and Relationships
    # ==========================================================================

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    organization_id = models.UUIDField(db_index=True)
    aircraft = models.ForeignKey(
        'Aircraft',
        on_delete=models.CASCADE,
        related_name='squawks'
    )

    # ==========================================================================
    # Reporter Information
    # ==========================================================================

    reported_by = models.UUIDField(
        help_text='User ID who reported the squawk'
    )
    reported_by_name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text='Name of reporter for display'
    )
    reported_at = models.DateTimeField(default=timezone.now)
    flight_id = models.UUIDField(
        blank=True,
        null=True,
        help_text='Associated flight where issue was discovered'
    )

    # ==========================================================================
    # Squawk Details
    # ==========================================================================

    squawk_number = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text='Auto-generated squawk number (e.g., SQ-2024-0001)'
    )
    title = models.CharField(max_length=255)
    description = models.TextField()

    # ==========================================================================
    # Categorization
    # ==========================================================================

    category = models.CharField(
        max_length=50,
        choices=Category.choices,
        default=Category.OTHER
    )
    ata_chapter = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        help_text='ATA 100 chapter code'
    )
    system = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text='Specific system affected'
    )
    component = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text='Specific component affected'
    )

    # ==========================================================================
    # Severity and Priority
    # ==========================================================================

    severity = models.CharField(
        max_length=20,
        choices=Severity.choices,
        default=Severity.MINOR
    )
    priority = models.CharField(
        max_length=20,
        choices=Priority.choices,
        default=Priority.NORMAL
    )

    # ==========================================================================
    # Flight Impact
    # ==========================================================================

    is_grounding = models.BooleanField(
        default=False,
        help_text='Squawk prevents aircraft from flying'
    )
    is_mel_item = models.BooleanField(
        default=False,
        help_text='Item is covered under MEL'
    )
    mel_category = models.CharField(
        max_length=1,
        choices=MELCategory.choices,
        blank=True,
        null=True
    )
    mel_reference = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text='MEL item reference number'
    )

    # CDL/NEF
    is_cdl_item = models.BooleanField(
        default=False,
        help_text='Configuration Deviation List item'
    )
    cdl_reference = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    # ==========================================================================
    # Deferral
    # ==========================================================================

    is_deferred = models.BooleanField(default=False)
    deferred_until = models.DateField(
        blank=True,
        null=True,
        help_text='Deferred until this date'
    )
    deferred_until_hours = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        help_text='Deferred until this aircraft hour'
    )
    deferred_until_cycles = models.IntegerField(
        blank=True,
        null=True,
        help_text='Deferred until this cycle count'
    )
    deferral_reason = models.TextField(blank=True, null=True)
    deferral_approved_by = models.UUIDField(blank=True, null=True)
    deferral_approved_at = models.DateTimeField(blank=True, null=True)

    # ==========================================================================
    # Status
    # ==========================================================================

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OPEN
    )

    # ==========================================================================
    # Resolution
    # ==========================================================================

    resolution = models.TextField(
        blank=True,
        null=True,
        help_text='Description of how the squawk was resolved'
    )
    resolution_action = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text='repair, replace, adjust, defer, etc.'
    )
    resolved_by = models.UUIDField(blank=True, null=True)
    resolved_by_name = models.CharField(max_length=255, blank=True, null=True)
    resolved_at = models.DateTimeField(blank=True, null=True)
    parts_used = models.JSONField(
        default=list,
        blank=True,
        help_text='Parts used in repair'
    )

    # ==========================================================================
    # Work Order Integration
    # ==========================================================================

    work_order_id = models.UUIDField(
        blank=True,
        null=True,
        help_text='Reference to maintenance work order'
    )
    work_order_number = models.CharField(max_length=50, blank=True, null=True)

    # ==========================================================================
    # Cost Tracking
    # ==========================================================================

    estimated_hours = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        blank=True,
        null=True,
        help_text='Estimated labor hours'
    )
    estimated_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True
    )
    actual_hours = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        blank=True,
        null=True,
        help_text='Actual labor hours'
    )
    actual_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True
    )

    # ==========================================================================
    # Attachments
    # ==========================================================================

    photos = models.JSONField(
        default=list,
        blank=True,
        help_text='List of photo URLs'
    )
    documents = models.JSONField(
        default=list,
        blank=True,
        help_text='List of document URLs'
    )

    # ==========================================================================
    # Aircraft State at Reporting
    # ==========================================================================

    aircraft_hours_at = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        help_text='Aircraft total time when squawk was reported'
    )
    aircraft_cycles_at = models.IntegerField(
        blank=True,
        null=True,
        help_text='Aircraft cycles when squawk was reported'
    )

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
        db_table = 'aircraft_squawks'
        ordering = ['-reported_at']
        verbose_name = 'Aircraft Squawk'
        verbose_name_plural = 'Aircraft Squawks'
        indexes = [
            models.Index(fields=['organization_id']),
            models.Index(fields=['aircraft', 'status']),
            models.Index(fields=['status']),
            models.Index(fields=['is_grounding']),
            models.Index(fields=['severity']),
        ]

    def __str__(self):
        return f"{self.squawk_number or 'SQ'}: {self.title}"

    # ==========================================================================
    # Save Override
    # ==========================================================================

    def save(self, *args, **kwargs):
        # Auto-generate squawk number
        if not self.squawk_number:
            year = timezone.now().year
            count = AircraftSquawk.objects.filter(
                organization_id=self.organization_id,
                created_at__year=year
            ).count() + 1
            self.squawk_number = f"SQ-{year}-{count:04d}"

        # Auto-set is_grounding based on severity
        if self.severity in [self.Severity.GROUNDING, self.Severity.AOG]:
            self.is_grounding = True

        # Set aircraft state if not provided
        if not self.aircraft_hours_at and hasattr(self, 'aircraft'):
            self.aircraft_hours_at = self.aircraft.total_time_hours
            self.aircraft_cycles_at = self.aircraft.total_cycles

        super().save(*args, **kwargs)

        # Update aircraft squawk status
        if hasattr(self, 'aircraft'):
            self.aircraft.update_squawk_status()

    # ==========================================================================
    # Properties
    # ==========================================================================

    @property
    def is_open(self) -> bool:
        """Check if squawk is in an open state."""
        return self.status in [
            self.Status.OPEN,
            self.Status.IN_PROGRESS,
            self.Status.DEFERRED
        ]

    @property
    def days_open(self) -> int:
        """Calculate days since squawk was reported."""
        delta = timezone.now() - self.reported_at
        return delta.days

    @property
    def is_overdue(self) -> bool:
        """Check if deferred squawk is overdue."""
        if not self.is_deferred:
            return False

        if self.deferred_until and self.deferred_until < date.today():
            return True

        if self.deferred_until_hours and hasattr(self, 'aircraft'):
            if self.aircraft.total_time_hours > self.deferred_until_hours:
                return True

        if self.deferred_until_cycles and hasattr(self, 'aircraft'):
            if self.aircraft.total_cycles > self.deferred_until_cycles:
                return True

        return False

    @property
    def mel_time_limit_days(self) -> Optional[int]:
        """Get MEL category time limit in days."""
        if not self.is_mel_item or not self.mel_category:
            return None

        limits = {
            'A': None,  # No limit
            'B': 3,
            'C': 10,
            'D': 120,
        }
        return limits.get(self.mel_category)

    @property
    def mel_expiry_date(self) -> Optional[date]:
        """Calculate MEL expiry date."""
        limit_days = self.mel_time_limit_days
        if limit_days is None:
            return None
        return self.reported_at.date() + timedelta(days=limit_days)

    # ==========================================================================
    # Methods
    # ==========================================================================

    def resolve(
        self,
        resolution: str,
        resolved_by: uuid.UUID,
        resolved_by_name: str = None,
        resolution_action: str = None,
        parts_used: list = None
    ) -> None:
        """Mark squawk as resolved."""
        self.status = self.Status.RESOLVED
        self.resolution = resolution
        self.resolution_action = resolution_action
        self.resolved_by = resolved_by
        self.resolved_by_name = resolved_by_name
        self.resolved_at = timezone.now()
        if parts_used:
            self.parts_used = parts_used
        self.save()

    def close(self) -> None:
        """Close a resolved squawk."""
        if self.status != self.Status.RESOLVED:
            raise ValueError("Only resolved squawks can be closed")
        self.status = self.Status.CLOSED
        self.save()

    def cancel(self, reason: str = None) -> None:
        """Cancel a squawk."""
        self.status = self.Status.CANCELLED
        if reason:
            self.resolution = f"Cancelled: {reason}"
        self.save()

    def defer(
        self,
        reason: str,
        approved_by: uuid.UUID,
        until_date: date = None,
        until_hours: Decimal = None,
        until_cycles: int = None
    ) -> None:
        """Defer a squawk."""
        if self.is_grounding:
            raise ValueError("Grounding squawks cannot be deferred")

        self.status = self.Status.DEFERRED
        self.is_deferred = True
        self.deferral_reason = reason
        self.deferral_approved_by = approved_by
        self.deferral_approved_at = timezone.now()
        self.deferred_until = until_date
        self.deferred_until_hours = until_hours
        self.deferred_until_cycles = until_cycles
        self.save()

    def start_work(self) -> None:
        """Mark squawk as in progress."""
        self.status = self.Status.IN_PROGRESS
        self.save()

    def add_photo(self, photo_url: str) -> None:
        """Add a photo to the squawk."""
        if not isinstance(self.photos, list):
            self.photos = []
        self.photos.append({
            'url': photo_url,
            'added_at': timezone.now().isoformat()
        })
        self.save(update_fields=['photos', 'updated_at'])

    def add_document(self, document_url: str, title: str = None) -> None:
        """Add a document to the squawk."""
        if not isinstance(self.documents, list):
            self.documents = []
        self.documents.append({
            'url': document_url,
            'title': title,
            'added_at': timezone.now().isoformat()
        })
        self.save(update_fields=['documents', 'updated_at'])

    @classmethod
    def generate_squawk_number(cls, organization_id: uuid.UUID) -> str:
        """Generate unique squawk number."""
        year = timezone.now().year
        count = cls.objects.filter(
            organization_id=organization_id,
            created_at__year=year
        ).count() + 1
        return f"SQ-{year}-{count:04d}"
