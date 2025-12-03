# services/maintenance-service/src/apps/core/models/ad_sb_tracking.py
"""
AD/SB Tracking Model

Tracks Airworthiness Directives and Service Bulletins compliance.
"""

import uuid
from datetime import date
from decimal import Decimal

from django.db import models


class ADSBTracking(models.Model):
    """
    Airworthiness Directive / Service Bulletin tracking.

    Tracks compliance status for ADs, SBs, SLs, and SILs.
    """

    class DirectiveType(models.TextChoices):
        AD = 'AD', 'Airworthiness Directive'
        SB = 'SB', 'Service Bulletin'
        SL = 'SL', 'Service Letter'
        SIL = 'SIL', 'Service Information Letter'
        ASB = 'ASB', 'Alert Service Bulletin'

    class IssuingAuthority(models.TextChoices):
        FAA = 'FAA', 'FAA'
        EASA = 'EASA', 'EASA'
        TCCA = 'TCCA', 'Transport Canada'
        MANUFACTURER = 'manufacturer', 'Manufacturer'
        SHGM = 'SHGM', 'SHGM'
        OTHER = 'other', 'Other'

    class ComplianceStatus(models.TextChoices):
        PENDING = 'pending', 'Pending'
        COMPLIANT = 'compliant', 'Compliant'
        NON_COMPLIANT = 'non_compliant', 'Non-Compliant'
        NOT_APPLICABLE = 'not_applicable', 'Not Applicable'
        DEFERRED = 'deferred', 'Deferred'
        TERMINATED = 'terminated', 'Terminated'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization_id = models.UUIDField(db_index=True)
    aircraft_id = models.UUIDField(db_index=True)

    # ==========================================================================
    # Directive Type
    # ==========================================================================

    directive_type = models.CharField(
        max_length=10,
        choices=DirectiveType.choices
    )

    # ==========================================================================
    # Identification
    # ==========================================================================

    directive_number = models.CharField(max_length=100, db_index=True)
    revision = models.CharField(max_length=20, blank=True, null=True)
    title = models.CharField(max_length=500)
    description = models.TextField(blank=True, null=True)

    # ==========================================================================
    # Issuing Authority
    # ==========================================================================

    issuing_authority = models.CharField(
        max_length=50,
        choices=IssuingAuthority.choices,
        blank=True,
        null=True
    )
    issue_date = models.DateField(blank=True, null=True)
    effective_date = models.DateField(blank=True, null=True)

    # ==========================================================================
    # Applicability
    # ==========================================================================

    applicability = models.TextField(blank=True, null=True)
    affected_serial_numbers = models.TextField(blank=True, null=True)
    is_applicable = models.BooleanField(default=True)
    not_applicable_reason = models.TextField(blank=True, null=True)

    # ==========================================================================
    # Compliance Requirements
    # ==========================================================================

    compliance_required = models.BooleanField(default=True)
    compliance_method = models.TextField(blank=True, null=True)
    compliance_instructions = models.TextField(blank=True, null=True)

    # ==========================================================================
    # Terminating Action
    # ==========================================================================

    is_terminating = models.BooleanField(
        default=False,
        help_text='If true, compliance terminates the requirement'
    )
    terminating_action = models.TextField(blank=True, null=True)
    is_terminated = models.BooleanField(default=False)
    terminated_date = models.DateField(blank=True, null=True)

    # ==========================================================================
    # Initial Compliance
    # ==========================================================================

    initial_compliance_date = models.DateField(blank=True, null=True)
    initial_compliance_hours = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )
    initial_compliance_cycles = models.IntegerField(blank=True, null=True)

    # ==========================================================================
    # Recurring Intervals
    # ==========================================================================

    is_recurring = models.BooleanField(default=False)
    recurring_interval_days = models.IntegerField(blank=True, null=True)
    recurring_interval_hours = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )
    recurring_interval_cycles = models.IntegerField(blank=True, null=True)

    # ==========================================================================
    # Current Compliance Status
    # ==========================================================================

    compliance_status = models.CharField(
        max_length=20,
        choices=ComplianceStatus.choices,
        default=ComplianceStatus.PENDING
    )

    last_compliance_date = models.DateField(blank=True, null=True)
    last_compliance_hours = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )
    last_compliance_cycles = models.IntegerField(blank=True, null=True)
    last_compliance_notes = models.TextField(blank=True, null=True)

    next_compliance_date = models.DateField(blank=True, null=True)
    next_compliance_hours = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )
    next_compliance_cycles = models.IntegerField(blank=True, null=True)

    # ==========================================================================
    # Remaining
    # ==========================================================================

    remaining_hours = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )
    remaining_days = models.IntegerField(blank=True, null=True)
    remaining_cycles = models.IntegerField(blank=True, null=True)

    # ==========================================================================
    # Related Records
    # ==========================================================================

    maintenance_item_id = models.UUIDField(blank=True, null=True)
    work_order_id = models.UUIDField(blank=True, null=True)

    # ==========================================================================
    # Documentation
    # ==========================================================================

    directive_document_url = models.URLField(max_length=500, blank=True, null=True)
    compliance_document_url = models.URLField(max_length=500, blank=True, null=True)

    # ==========================================================================
    # Notes
    # ==========================================================================

    notes = models.TextField(blank=True, null=True)

    # ==========================================================================
    # Timestamps
    # ==========================================================================

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ad_sb_tracking'
        ordering = ['-effective_date']
        verbose_name = 'AD/SB Tracking'
        verbose_name_plural = 'AD/SB Tracking'
        indexes = [
            models.Index(fields=['organization_id']),
            models.Index(fields=['aircraft_id']),
            models.Index(fields=['compliance_status']),
            models.Index(fields=['directive_type']),
            models.Index(fields=['directive_number']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['aircraft_id', 'directive_number', 'revision'],
                name='unique_aircraft_directive'
            )
        ]

    def __str__(self):
        return f"{self.directive_type} {self.directive_number}: {self.title[:50]}"

    # ==========================================================================
    # Properties
    # ==========================================================================

    @property
    def is_overdue(self) -> bool:
        if not self.compliance_required or not self.is_applicable:
            return False
        if self.compliance_status == self.ComplianceStatus.COMPLIANT and not self.is_recurring:
            return False

        if self.remaining_hours is not None and self.remaining_hours <= 0:
            return True
        if self.remaining_days is not None and self.remaining_days < 0:
            return True
        if self.remaining_cycles is not None and self.remaining_cycles <= 0:
            return True
        return False

    @property
    def is_due_soon(self) -> bool:
        """Check if due within warning thresholds."""
        if not self.compliance_required or not self.is_applicable:
            return False

        if self.remaining_hours is not None and self.remaining_hours <= Decimal('10'):
            return True
        if self.remaining_days is not None and self.remaining_days <= 30:
            return True
        return False

    # ==========================================================================
    # Methods
    # ==========================================================================

    def calculate_remaining(
        self,
        current_hours: Decimal = None,
        current_cycles: int = None
    ) -> None:
        """Calculate remaining time/cycles until compliance due."""
        if self.next_compliance_hours and current_hours is not None:
            self.remaining_hours = self.next_compliance_hours - current_hours

        if self.next_compliance_date:
            self.remaining_days = (self.next_compliance_date - date.today()).days

        if self.next_compliance_cycles and current_cycles is not None:
            self.remaining_cycles = self.next_compliance_cycles - current_cycles

        self.save(update_fields=[
            'remaining_hours', 'remaining_days', 'remaining_cycles', 'updated_at'
        ])

    def record_compliance(
        self,
        compliance_date: date,
        compliance_hours: Decimal = None,
        compliance_cycles: int = None,
        notes: str = None,
        work_order_id: uuid.UUID = None
    ) -> None:
        """Record compliance with this directive."""
        self.last_compliance_date = compliance_date
        self.last_compliance_hours = compliance_hours
        self.last_compliance_cycles = compliance_cycles
        self.last_compliance_notes = notes
        if work_order_id:
            self.work_order_id = work_order_id

        # Update status
        if self.is_terminating:
            self.compliance_status = self.ComplianceStatus.TERMINATED
            self.is_terminated = True
            self.terminated_date = compliance_date
        else:
            self.compliance_status = self.ComplianceStatus.COMPLIANT

        # Calculate next due if recurring
        if self.is_recurring and not self.is_terminating:
            self._calculate_next_due(compliance_date, compliance_hours, compliance_cycles)

        self.save()

    def _calculate_next_due(
        self,
        done_date: date,
        done_hours: Decimal = None,
        done_cycles: int = None
    ) -> None:
        """Calculate next compliance due."""
        from datetime import timedelta

        if self.recurring_interval_hours and done_hours:
            self.next_compliance_hours = done_hours + self.recurring_interval_hours

        if self.recurring_interval_cycles and done_cycles:
            self.next_compliance_cycles = done_cycles + self.recurring_interval_cycles

        if self.recurring_interval_days:
            self.next_compliance_date = done_date + timedelta(days=self.recurring_interval_days)

    def mark_not_applicable(self, reason: str) -> None:
        """Mark this directive as not applicable."""
        self.is_applicable = False
        self.not_applicable_reason = reason
        self.compliance_status = self.ComplianceStatus.NOT_APPLICABLE
        self.save(update_fields=[
            'is_applicable', 'not_applicable_reason', 'compliance_status', 'updated_at'
        ])

    @classmethod
    def get_pending_directives(
        cls,
        organization_id: uuid.UUID,
        aircraft_id: uuid.UUID = None
    ):
        """Get all pending and non-compliant directives."""
        queryset = cls.objects.filter(
            organization_id=organization_id,
            is_applicable=True,
            compliance_required=True,
            compliance_status__in=[
                cls.ComplianceStatus.PENDING,
                cls.ComplianceStatus.NON_COMPLIANT
            ]
        )
        if aircraft_id:
            queryset = queryset.filter(aircraft_id=aircraft_id)
        return queryset.order_by('effective_date')

    @classmethod
    def get_recurring_due(
        cls,
        organization_id: uuid.UUID,
        aircraft_id: uuid.UUID = None,
        days_ahead: int = 30,
        hours_ahead: int = 50
    ):
        """Get recurring directives coming due."""
        from django.db.models import Q

        queryset = cls.objects.filter(
            organization_id=organization_id,
            is_applicable=True,
            is_recurring=True,
            compliance_status=cls.ComplianceStatus.COMPLIANT
        ).filter(
            Q(remaining_hours__lte=hours_ahead) |
            Q(remaining_days__lte=days_ahead)
        )

        if aircraft_id:
            queryset = queryset.filter(aircraft_id=aircraft_id)

        return queryset.order_by('remaining_hours', 'remaining_days')
