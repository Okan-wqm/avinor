# services/certificate-service/src/apps/core/models/flight_time_limitations.py
"""
Flight Time Limitations (FTL) Model

Fatigue management and duty time tracking.
Compliant with EASA FTL (ORO.FTL) and FAA 14 CFR 117.
"""

import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Optional, Dict, Any, List

from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.utils import timezone


class FTLStandard(models.TextChoices):
    """FTL regulatory standard choices."""
    EASA_FTL = 'easa_ftl', 'EASA FTL (ORO.FTL)'
    FAA_117 = 'faa_117', 'FAA Part 117'
    FAA_91 = 'faa_91', 'FAA Part 91'
    FAA_135 = 'faa_135', 'FAA Part 135'
    FAA_121 = 'faa_121', 'FAA Part 121'
    CUSTOM = 'custom', 'Custom/Organization Rules'


class DutyType(models.TextChoices):
    """Duty type choices."""
    FLIGHT_DUTY = 'flight_duty', 'Flight Duty Period (FDP)'
    DUTY = 'duty', 'Duty Period'
    REST = 'rest', 'Rest Period'
    STANDBY = 'standby', 'Standby'
    RESERVE = 'reserve', 'Reserve'
    POSITIONING = 'positioning', 'Positioning'
    TRAINING = 'training', 'Training'
    GROUND_DUTY = 'ground_duty', 'Ground Duty'
    SPLIT_DUTY = 'split_duty', 'Split Duty'


class FTLViolationType(models.TextChoices):
    """FTL violation type choices."""
    FDP_EXCEEDED = 'fdp_exceeded', 'Flight Duty Period Exceeded'
    FLIGHT_TIME_EXCEEDED = 'flight_time_exceeded', 'Flight Time Limit Exceeded'
    REST_INSUFFICIENT = 'rest_insufficient', 'Insufficient Rest'
    DUTY_EXCEEDED = 'duty_exceeded', 'Duty Period Exceeded'
    CUMULATIVE_EXCEEDED = 'cumulative_exceeded', 'Cumulative Limit Exceeded'
    WEEKLY_EXCEEDED = 'weekly_exceeded', 'Weekly Limit Exceeded'
    MONTHLY_EXCEEDED = 'monthly_exceeded', 'Monthly Limit Exceeded'
    YEARLY_EXCEEDED = 'yearly_exceeded', 'Yearly Limit Exceeded'


class FTLConfiguration(models.Model):
    """
    FTL Configuration Model.

    Defines the FTL rules for an organization.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    organization_id = models.UUIDField(db_index=True, unique=True)

    # Regulatory Standard
    ftl_standard = models.CharField(
        max_length=20,
        choices=FTLStandard.choices,
        default=FTLStandard.EASA_FTL
    )

    # Flight Time Limits
    max_flight_time_daily = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=Decimal('10.0'),
        help_text='Maximum flight time per day (hours)'
    )
    max_flight_time_7_days = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('60.0'),
        help_text='Maximum flight time in 7 consecutive days'
    )
    max_flight_time_28_days = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('100.0'),
        help_text='Maximum flight time in 28 consecutive days'
    )
    max_flight_time_calendar_year = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal('900.0'),
        help_text='Maximum flight time per calendar year'
    )

    # Flight Duty Period (FDP) Limits
    max_fdp_standard = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=Decimal('13.0'),
        help_text='Maximum FDP with early/late start acclimatized'
    )
    max_fdp_extended = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=Decimal('14.0'),
        help_text='Maximum FDP with extension'
    )
    fdp_extension_allowed = models.BooleanField(
        default=True,
        help_text='Allow FDP extension with augmented crew'
    )
    fdp_extension_requires_augmented = models.BooleanField(
        default=True,
        help_text='Require augmented crew for extension'
    )

    # Duty Period Limits
    max_duty_period = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=Decimal('14.0'),
        help_text='Maximum total duty period (hours)'
    )
    max_duty_7_days = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('60.0'),
        help_text='Maximum duty in 7 consecutive days'
    )
    max_duty_14_days = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('110.0'),
        help_text='Maximum duty in 14 consecutive days'
    )
    max_duty_28_days = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('190.0'),
        help_text='Maximum duty in 28 consecutive days'
    )

    # Rest Requirements
    min_rest_between_duties = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=Decimal('10.0'),
        help_text='Minimum rest between duty periods (hours)'
    )
    min_rest_after_fdp = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=Decimal('12.0'),
        help_text='Minimum rest after FDP (hours)'
    )
    min_weekly_rest = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=Decimal('36.0'),
        help_text='Minimum weekly rest period (hours)'
    )
    days_off_per_7_days = models.IntegerField(
        default=1,
        help_text='Required days off per 7 days'
    )
    days_off_per_14_days = models.IntegerField(
        default=2,
        help_text='Required days off per 14 days'
    )

    # Night Operations
    night_start = models.TimeField(
        default=datetime.strptime('22:00', '%H:%M').time(),
        help_text='Start of night period (local time)'
    )
    night_end = models.TimeField(
        default=datetime.strptime('06:00', '%H:%M').time(),
        help_text='End of night period (local time)'
    )
    fdp_reduction_night = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=Decimal('2.0'),
        help_text='FDP reduction for night operations (hours)'
    )

    # Split Duty
    split_duty_allowed = models.BooleanField(default=True)
    min_split_rest = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=Decimal('3.0'),
        help_text='Minimum split duty rest (hours)'
    )
    fdp_extension_per_split_hour = models.DecimalField(
        max_digits=2,
        decimal_places=1,
        default=Decimal('0.5'),
        help_text='FDP extension per hour of split rest'
    )

    # Standby/Reserve
    standby_counts_as_duty = models.BooleanField(
        default=True,
        help_text='Count standby time as duty'
    )
    airport_standby_max = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=Decimal('6.0'),
        help_text='Maximum airport standby (hours)'
    )

    # Fatigue Risk Management
    frm_enabled = models.BooleanField(
        default=False,
        help_text='Enable Fatigue Risk Management System'
    )
    fatigue_reporting_required = models.BooleanField(default=True)

    # Metadata
    effective_date = models.DateField(default=date.today)
    notes = models.TextField(blank=True, null=True)
    metadata = models.JSONField(default=dict, blank=True)

    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ftl_configurations'
        verbose_name = 'FTL Configuration'
        verbose_name_plural = 'FTL Configurations'

    def __str__(self) -> str:
        return f"FTL Config: {self.get_ftl_standard_display()}"


class DutyPeriod(models.Model):
    """
    Duty Period Model.

    Tracks individual duty periods for FTL compliance.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    organization_id = models.UUIDField(db_index=True)
    user_id = models.UUIDField(db_index=True)

    # Period Details
    duty_type = models.CharField(
        max_length=20,
        choices=DutyType.choices,
        db_index=True
    )
    duty_date = models.DateField(db_index=True)

    # Times (UTC)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(blank=True, null=True)

    # Times (Local)
    start_time_local = models.DateTimeField(blank=True, null=True)
    end_time_local = models.DateTimeField(blank=True, null=True)
    timezone = models.CharField(max_length=50, default='UTC')

    # Duration (calculated)
    duration_hours = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.0')
    )

    # Flight Time (within duty)
    flight_time_hours = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.0')
    )
    sectors = models.IntegerField(
        default=0,
        help_text='Number of flight sectors'
    )

    # Location
    start_location = models.CharField(
        max_length=4,
        blank=True,
        null=True,
        help_text='Start location (ICAO code)'
    )
    end_location = models.CharField(
        max_length=4,
        blank=True,
        null=True,
        help_text='End location (ICAO code)'
    )

    # Status
    is_completed = models.BooleanField(default=False)
    is_planned = models.BooleanField(
        default=False,
        help_text='Is this a planned/future duty?'
    )

    # Augmented Crew
    is_augmented = models.BooleanField(
        default=False,
        help_text='Augmented crew for FDP extension'
    )
    augmentation_type = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text='Type of crew augmentation'
    )

    # Rest Facility
    rest_facility_class = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        help_text='Class of rest facility (1, 2, 3)'
    )

    # Split Duty Rest
    split_rest_start = models.DateTimeField(blank=True, null=True)
    split_rest_end = models.DateTimeField(blank=True, null=True)
    split_rest_hours = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=Decimal('0.0')
    )

    # Related Flights
    flight_ids = ArrayField(
        models.UUIDField(),
        default=list,
        blank=True,
        help_text='Associated flight IDs'
    )

    # Notes
    notes = models.TextField(blank=True, null=True)

    # Metadata
    metadata = models.JSONField(default=dict, blank=True)

    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'duty_periods'
        ordering = ['-start_time']
        indexes = [
            models.Index(fields=['organization_id', 'user_id']),
            models.Index(fields=['duty_date']),
            models.Index(fields=['start_time', 'end_time']),
            models.Index(fields=['duty_type']),
        ]

    def __str__(self) -> str:
        return f"{self.get_duty_type_display()} - {self.duty_date}"

    def save(self, *args, **kwargs):
        """Calculate duration on save."""
        if self.end_time and self.start_time:
            delta = self.end_time - self.start_time
            self.duration_hours = Decimal(str(delta.total_seconds() / 3600)).quantize(Decimal('0.01'))
            self.is_completed = True
        super().save(*args, **kwargs)

    @property
    def is_flight_duty(self) -> bool:
        """Check if this is a flight duty period."""
        return self.duty_type == DutyType.FLIGHT_DUTY

    def get_duty_info(self) -> Dict[str, Any]:
        """Get duty period information."""
        return {
            'duty_id': str(self.id),
            'user_id': str(self.user_id),
            'duty_type': self.duty_type,
            'duty_type_display': self.get_duty_type_display(),
            'duty_date': self.duty_date.isoformat(),
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'duration_hours': float(self.duration_hours),
            'flight_time_hours': float(self.flight_time_hours),
            'sectors': self.sectors,
            'is_completed': self.is_completed,
            'is_augmented': self.is_augmented,
        }


class RestPeriod(models.Model):
    """
    Rest Period Model.

    Tracks rest periods for FTL compliance.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    organization_id = models.UUIDField(db_index=True)
    user_id = models.UUIDField(db_index=True)

    # Period Details
    rest_date = models.DateField(db_index=True)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(blank=True, null=True)

    # Duration
    duration_hours = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.0')
    )

    # Type
    is_reduced_rest = models.BooleanField(default=False)
    is_split_duty_rest = models.BooleanField(default=False)
    is_weekly_rest = models.BooleanField(default=False)

    # Location
    location = models.CharField(
        max_length=4,
        blank=True,
        null=True,
        help_text='Rest location (ICAO code)'
    )
    accommodation_type = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text='Type of accommodation'
    )
    is_suitable_accommodation = models.BooleanField(
        default=True,
        help_text='Whether accommodation meets standards'
    )

    # Linked Duty Periods
    preceding_duty = models.ForeignKey(
        DutyPeriod,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='following_rest'
    )
    following_duty = models.ForeignKey(
        DutyPeriod,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='preceding_rest'
    )

    # Notes
    notes = models.TextField(blank=True, null=True)

    # Metadata
    metadata = models.JSONField(default=dict, blank=True)

    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'rest_periods'
        ordering = ['-start_time']
        indexes = [
            models.Index(fields=['organization_id', 'user_id']),
            models.Index(fields=['rest_date']),
        ]

    def __str__(self) -> str:
        return f"Rest: {self.rest_date} - {self.duration_hours}h"

    def save(self, *args, **kwargs):
        """Calculate duration on save."""
        if self.end_time and self.start_time:
            delta = self.end_time - self.start_time
            self.duration_hours = Decimal(str(delta.total_seconds() / 3600)).quantize(Decimal('0.01'))
        super().save(*args, **kwargs)


class FTLViolation(models.Model):
    """
    FTL Violation Model.

    Records FTL limit violations.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    organization_id = models.UUIDField(db_index=True)
    user_id = models.UUIDField(db_index=True)

    # Violation Details
    violation_type = models.CharField(
        max_length=30,
        choices=FTLViolationType.choices,
        db_index=True
    )
    violation_date = models.DateField(db_index=True)
    detected_at = models.DateTimeField(auto_now_add=True)

    # Limit Information
    limit_name = models.CharField(max_length=100)
    limit_value = models.DecimalField(max_digits=6, decimal_places=2)
    actual_value = models.DecimalField(max_digits=6, decimal_places=2)
    exceeded_by = models.DecimalField(max_digits=5, decimal_places=2)

    # Period
    period_start = models.DateField()
    period_end = models.DateField()

    # Severity
    class Severity(models.TextChoices):
        LOW = 'low', 'Low'
        MEDIUM = 'medium', 'Medium'
        HIGH = 'high', 'High'
        CRITICAL = 'critical', 'Critical'

    severity = models.CharField(
        max_length=10,
        choices=Severity.choices,
        default=Severity.MEDIUM
    )

    # Related Records
    duty_period = models.ForeignKey(
        DutyPeriod,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='violations'
    )
    flight_ids = ArrayField(
        models.UUIDField(),
        default=list,
        blank=True
    )

    # Resolution
    is_resolved = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(blank=True, null=True)
    resolved_by = models.UUIDField(blank=True, null=True)
    resolution_notes = models.TextField(blank=True, null=True)
    commander_discretion = models.BooleanField(
        default=False,
        help_text='Was commander discretion applied?'
    )
    discretion_reason = models.TextField(blank=True, null=True)

    # Reporting
    reported_to_authority = models.BooleanField(default=False)
    authority_report_date = models.DateField(blank=True, null=True)
    authority_reference = models.CharField(max_length=100, blank=True, null=True)

    # Notes
    notes = models.TextField(blank=True, null=True)

    # Metadata
    metadata = models.JSONField(default=dict, blank=True)

    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ftl_violations'
        ordering = ['-violation_date']
        indexes = [
            models.Index(fields=['organization_id', 'user_id']),
            models.Index(fields=['violation_type']),
            models.Index(fields=['violation_date']),
            models.Index(fields=['is_resolved']),
        ]

    def __str__(self) -> str:
        return f"{self.get_violation_type_display()} - {self.violation_date}"

    def resolve(self, resolved_by: uuid.UUID, notes: str = None) -> None:
        """Resolve the violation."""
        self.is_resolved = True
        self.resolved_at = timezone.now()
        self.resolved_by = resolved_by
        if notes:
            self.resolution_notes = notes
        self.save()


class PilotFTLSummary(models.Model):
    """
    Pilot FTL Summary Model.

    Aggregated FTL statistics for quick compliance checking.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    organization_id = models.UUIDField(db_index=True)
    user_id = models.UUIDField(db_index=True)

    # Current Rolling Totals
    flight_time_today = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.0'))
    flight_time_7_days = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.0'))
    flight_time_28_days = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.0'))
    flight_time_calendar_year = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.0'))

    duty_time_7_days = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.0'))
    duty_time_14_days = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.0'))
    duty_time_28_days = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.0'))

    # Last FDP
    last_fdp_end = models.DateTimeField(blank=True, null=True)
    last_fdp_duration = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.0'))

    # Last Rest
    last_rest_start = models.DateTimeField(blank=True, null=True)
    last_rest_end = models.DateTimeField(blank=True, null=True)
    last_rest_duration = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.0'))

    # Days Off
    days_off_last_7 = models.IntegerField(default=0)
    days_off_last_14 = models.IntegerField(default=0)
    last_weekly_rest_date = models.DateField(blank=True, null=True)

    # Availability Status
    class AvailabilityStatus(models.TextChoices):
        AVAILABLE = 'available', 'Available'
        ON_DUTY = 'on_duty', 'On Duty'
        RESTING = 'resting', 'Resting'
        LIMIT_REACHED = 'limit_reached', 'Limit Reached'
        STANDBY = 'standby', 'Standby'

    current_status = models.CharField(
        max_length=20,
        choices=AvailabilityStatus.choices,
        default=AvailabilityStatus.AVAILABLE
    )

    # Next Available
    next_available = models.DateTimeField(blank=True, null=True)

    # Maximum Available FDP
    max_fdp_available = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=Decimal('0.0'),
        help_text='Maximum FDP available for next duty'
    )

    # Compliance Flags
    is_compliant = models.BooleanField(default=True)
    compliance_issues = ArrayField(
        models.CharField(max_length=255),
        default=list,
        blank=True
    )

    # Last Calculation
    last_calculated = models.DateTimeField(auto_now=True)

    # Metadata
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'pilot_ftl_summaries'
        indexes = [
            models.Index(fields=['organization_id', 'user_id']),
            models.Index(fields=['current_status']),
            models.Index(fields=['is_compliant']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['organization_id', 'user_id'],
                name='unique_pilot_ftl_summary'
            )
        ]

    def __str__(self) -> str:
        return f"FTL Summary: {self.user_id}"

    def get_compliance_summary(self) -> Dict[str, Any]:
        """Get FTL compliance summary."""
        return {
            'user_id': str(self.user_id),
            'current_status': self.current_status,
            'is_compliant': self.is_compliant,
            'compliance_issues': self.compliance_issues,
            'flight_time': {
                'today': float(self.flight_time_today),
                '7_days': float(self.flight_time_7_days),
                '28_days': float(self.flight_time_28_days),
                'calendar_year': float(self.flight_time_calendar_year),
            },
            'duty_time': {
                '7_days': float(self.duty_time_7_days),
                '14_days': float(self.duty_time_14_days),
                '28_days': float(self.duty_time_28_days),
            },
            'rest': {
                'last_rest_duration': float(self.last_rest_duration),
                'days_off_last_7': self.days_off_last_7,
                'days_off_last_14': self.days_off_last_14,
            },
            'availability': {
                'max_fdp_available': float(self.max_fdp_available),
                'next_available': self.next_available.isoformat() if self.next_available else None,
            },
            'last_calculated': self.last_calculated.isoformat(),
        }
