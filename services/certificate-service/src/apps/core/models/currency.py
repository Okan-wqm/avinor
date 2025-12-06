# services/certificate-service/src/apps/core/models/currency.py
"""
Currency Models

Currency requirements and pilot currency status tracking.
"""

import uuid
from datetime import date, timedelta
from typing import Optional, Dict, Any, List

from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.utils import timezone


class CurrencyStatus(models.TextChoices):
    """Currency status choices."""
    CURRENT = 'current', 'Current'
    WARNING = 'warning', 'Warning (Expiring Soon)'
    EXPIRED = 'expired', 'Expired'
    NOT_CURRENT = 'not_current', 'Not Current'
    GRACE_PERIOD = 'grace_period', 'Grace Period'


class CurrencyType(models.TextChoices):
    """Currency requirement type choices."""
    # Basic Currency
    TAKEOFF_LANDING = 'takeoff_landing', 'Takeoff/Landing Currency'
    NIGHT = 'night', 'Night Currency'
    IFR = 'ifr', 'IFR Currency'
    # Type Specific
    TYPE_SPECIFIC = 'type_specific', 'Type Specific Currency'
    CLASS_SPECIFIC = 'class_specific', 'Class Specific Currency'
    # Instructor
    INSTRUCTOR = 'instructor', 'Instructor Currency'
    # Recency
    FLIGHT_REVIEW = 'flight_review', 'Flight Review'
    INSTRUMENT_PROFICIENCY = 'ipc', 'Instrument Proficiency Check'
    # Special
    TAILWHEEL = 'tailwheel', 'Tailwheel Currency'
    HIGH_ALTITUDE = 'high_altitude', 'High Altitude Currency'
    PASSENGER = 'passenger', 'Passenger Carrying Currency'


class CurrencyRequirement(models.Model):
    """
    Currency Requirement definition.

    Defines regulatory currency requirements that pilots must maintain.
    Based on FAR 61.57, EASA FCL.060, etc.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    organization_id = models.UUIDField(db_index=True)

    # Definition
    name = models.CharField(
        max_length=255,
        help_text='Requirement name'
    )
    code = models.CharField(
        max_length=50,
        help_text='Short code identifier'
    )
    description = models.TextField(
        blank=True,
        null=True
    )

    # Regulatory Reference
    regulatory_reference = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text='FAR 61.57, EASA FCL.060, etc.'
    )
    issuing_authority = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text='FAA, EASA, SHGM, etc.'
    )

    # Requirement Type
    requirement_type = models.CharField(
        max_length=50,
        choices=CurrencyType.choices,
        db_index=True
    )

    # Criteria
    criteria = models.JSONField(
        default=dict,
        help_text='Currency criteria definition'
    )
    # Example criteria:
    # {
    #     "period_days": 90,
    #     "min_takeoffs": 3,
    #     "min_landings": 3,
    #     "full_stop_required": true,
    #     "conditions": ["day"],  # or ["night"]
    #     "aircraft_category": "airplane",
    #     "aircraft_class": "single_engine_land"
    # }

    # Applicability
    applies_to = models.JSONField(
        default=dict,
        blank=True,
        help_text='Who this requirement applies to'
    )
    # Example:
    # {
    #     "license_types": ["PPL", "CPL", "ATPL"],
    #     "operation_types": ["passenger"],
    #     "aircraft_categories": ["airplane"],
    #     "aircraft_classes": ["single_engine_land", "multi_engine_land"]
    # }

    # Grace Period
    grace_period_days = models.PositiveIntegerField(
        default=0,
        help_text='Grace period after expiry'
    )

    # Warning Threshold
    warning_days = models.PositiveIntegerField(
        default=30,
        help_text='Days before expiry to show warning'
    )

    # Active
    is_active = models.BooleanField(default=True)
    is_mandatory = models.BooleanField(
        default=True,
        help_text='Whether this is a mandatory requirement'
    )

    # Priority (for display)
    priority = models.PositiveIntegerField(
        default=100,
        help_text='Display priority (lower = higher priority)'
    )

    # Notes
    notes = models.TextField(blank=True, null=True)

    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'currency_requirements'
        ordering = ['priority', 'name']
        indexes = [
            models.Index(fields=['organization_id', 'requirement_type']),
            models.Index(fields=['is_active']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['organization_id', 'code'],
                name='unique_currency_requirement_code'
            )
        ]

    def __str__(self) -> str:
        return f"{self.code}: {self.name}"

    def get_period_days(self) -> int:
        """Get the currency period in days."""
        return self.criteria.get('period_days', 90)

    def get_min_takeoffs(self) -> int:
        """Get minimum required takeoffs."""
        return self.criteria.get('min_takeoffs', 0)

    def get_min_landings(self) -> int:
        """Get minimum required landings."""
        return self.criteria.get('min_landings', 0)

    def get_min_approaches(self) -> int:
        """Get minimum required approaches (for IFR)."""
        return self.criteria.get('min_approaches', 0)

    def get_min_hours(self) -> float:
        """Get minimum required hours."""
        return self.criteria.get('min_hours', 0)

    def check_currency(
        self,
        activity_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Check if currency requirements are met.

        Args:
            activity_data: Dict containing activity counts
                - takeoffs: int
                - landings: int
                - approaches: int
                - hours: float
                - last_activity_date: date

        Returns:
            Dict with currency status
        """
        is_current = True
        issues = []

        # Check takeoffs
        min_takeoffs = self.get_min_takeoffs()
        actual_takeoffs = activity_data.get('takeoffs', 0)
        if min_takeoffs > 0 and actual_takeoffs < min_takeoffs:
            is_current = False
            issues.append(f'Need {min_takeoffs - actual_takeoffs} more takeoffs')

        # Check landings
        min_landings = self.get_min_landings()
        actual_landings = activity_data.get('landings', 0)
        if min_landings > 0 and actual_landings < min_landings:
            is_current = False
            issues.append(f'Need {min_landings - actual_landings} more landings')

        # Check approaches
        min_approaches = self.get_min_approaches()
        actual_approaches = activity_data.get('approaches', 0)
        if min_approaches > 0 and actual_approaches < min_approaches:
            is_current = False
            issues.append(f'Need {min_approaches - actual_approaches} more approaches')

        # Check hours
        min_hours = self.get_min_hours()
        actual_hours = activity_data.get('hours', 0)
        if min_hours > 0 and actual_hours < min_hours:
            is_current = False
            issues.append(f'Need {min_hours - actual_hours:.1f} more hours')

        return {
            'requirement_id': str(self.id),
            'requirement_code': self.code,
            'requirement_name': self.name,
            'is_current': is_current,
            'issues': issues,
            'criteria': self.criteria,
            'actual': activity_data,
        }


class UserCurrencyStatus(models.Model):
    """
    User Currency Status.

    Tracks a pilot's currency status for each requirement.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    organization_id = models.UUIDField(db_index=True)
    user_id = models.UUIDField(db_index=True)
    requirement = models.ForeignKey(
        CurrencyRequirement,
        on_delete=models.CASCADE,
        related_name='user_statuses'
    )

    # Status
    status = models.CharField(
        max_length=20,
        choices=CurrencyStatus.choices,
        default=CurrencyStatus.NOT_CURRENT,
        db_index=True
    )
    is_current = models.BooleanField(default=False, db_index=True)
    is_warning = models.BooleanField(
        default=False,
        help_text='Currency expiring soon'
    )

    # Current Activity Counts
    current_count = models.JSONField(
        default=dict,
        help_text='Current activity counts within period'
    )
    # Example:
    # {
    #     "takeoffs": 5,
    #     "landings": 5,
    #     "night_landings": 2,
    #     "approaches": 3,
    #     "hours": 12.5
    # }

    # Last Activity
    last_activity_date = models.DateField(
        blank=True,
        null=True
    )
    last_activity_id = models.UUIDField(
        blank=True,
        null=True,
        help_text='Last flight that contributed to currency'
    )

    # Validity
    valid_from = models.DateField(
        blank=True,
        null=True,
        help_text='Currency valid from date'
    )
    valid_until = models.DateField(
        blank=True,
        null=True,
        db_index=True,
        help_text='Currency valid until date'
    )

    # Expiry Warning
    expiry_warning_sent = models.BooleanField(default=False)
    expiry_warning_sent_at = models.DateTimeField(blank=True, null=True)

    # Lost Currency
    currency_lost_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text='When currency was lost'
    )
    currency_lost_notification_sent = models.BooleanField(default=False)

    # Last Check
    last_checked_at = models.DateTimeField(auto_now=True)
    last_calculated_at = models.DateTimeField(blank=True, null=True)

    # Notes
    notes = models.TextField(blank=True, null=True)

    # Metadata
    metadata = models.JSONField(default=dict, blank=True)

    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'user_currency_status'
        ordering = ['requirement__priority', 'requirement__name']
        indexes = [
            models.Index(fields=['organization_id', 'user_id']),
            models.Index(fields=['is_current']),
            models.Index(fields=['valid_until']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['user_id', 'requirement'],
                name='unique_user_currency_requirement'
            )
        ]

    def __str__(self) -> str:
        status = 'Current' if self.is_current else 'Not Current'
        return f"{self.requirement.code} - {status}"

    @property
    def days_until_expiry(self) -> Optional[int]:
        """Calculate days until currency expires."""
        if not self.valid_until:
            return None
        return (self.valid_until - date.today()).days

    @property
    def is_expired(self) -> bool:
        """Check if currency is expired."""
        if not self.valid_until:
            return not self.is_current
        return self.valid_until < date.today()

    @property
    def expiry_status(self) -> str:
        """Get human-readable expiry status."""
        if not self.is_current:
            return 'Not current'

        days = self.days_until_expiry
        if days is None:
            return 'Current (no expiry)'
        elif days < 0:
            return f'Expired {abs(days)} days ago'
        elif days == 0:
            return 'Expires today'
        elif days <= 7:
            return f'Expires in {days} days (critical)'
        elif days <= 30:
            return f'Expires in {days} days (warning)'
        else:
            return f'Current for {days} days'

    def update_currency(
        self,
        activity_data: Dict[str, Any],
        recalculate: bool = True
    ) -> None:
        """
        Update currency status based on new activity.

        Args:
            activity_data: Activity counts and dates
            recalculate: Whether to recalculate currency
        """
        self.current_count = activity_data.get('counts', {})
        self.last_activity_date = activity_data.get('last_date')
        self.last_activity_id = activity_data.get('last_flight_id')

        if recalculate:
            result = self.requirement.check_currency(self.current_count)
            was_current = self.is_current
            self.is_current = result['is_current']

            if self.is_current:
                self.valid_from = activity_data.get('first_date', date.today())
                self.valid_until = date.today() + timedelta(
                    days=self.requirement.get_period_days()
                )
                self.currency_lost_at = None
            elif was_current and not self.is_current:
                self.currency_lost_at = timezone.now()
                self.currency_lost_notification_sent = False

            # Check warning threshold
            warning_days = self.requirement.warning_days
            if self.days_until_expiry and 0 < self.days_until_expiry <= warning_days:
                self.is_warning = True
            else:
                self.is_warning = False

        self.last_calculated_at = timezone.now()
        self.save()

    def get_status_info(self) -> Dict[str, Any]:
        """Get detailed currency status information."""
        return {
            'status_id': str(self.id),
            'requirement_id': str(self.requirement.id),
            'requirement_code': self.requirement.code,
            'requirement_name': self.requirement.name,
            'requirement_type': self.requirement.requirement_type,
            'is_current': self.is_current,
            'is_warning': self.is_warning,
            'is_expired': self.is_expired,
            'valid_from': self.valid_from.isoformat() if self.valid_from else None,
            'valid_until': self.valid_until.isoformat() if self.valid_until else None,
            'days_until_expiry': self.days_until_expiry,
            'expiry_status': self.expiry_status,
            'current_count': self.current_count,
            'last_activity_date': self.last_activity_date.isoformat() if self.last_activity_date else None,
            'criteria': self.requirement.criteria,
            'regulatory_reference': self.requirement.regulatory_reference,
        }


# Default currency requirements data
DEFAULT_CURRENCY_REQUIREMENTS = [
    {
        'code': 'DAY_VFR',
        'name': 'Day VFR Passenger Currency',
        'requirement_type': CurrencyType.TAKEOFF_LANDING,
        'regulatory_reference': 'FAR 61.57(a) / EASA FCL.060(b)',
        'criteria': {
            'period_days': 90,
            'min_takeoffs': 3,
            'min_landings': 3,
            'full_stop_required': False,
            'conditions': ['day'],
        },
        'applies_to': {
            'operation_types': ['passenger'],
        },
        'priority': 10,
    },
    {
        'code': 'NIGHT_VFR',
        'name': 'Night VFR Passenger Currency',
        'requirement_type': CurrencyType.NIGHT,
        'regulatory_reference': 'FAR 61.57(b) / EASA FCL.060(b)',
        'criteria': {
            'period_days': 90,
            'min_takeoffs': 3,
            'min_landings': 3,
            'full_stop_required': True,
            'conditions': ['night'],
            'time_period': 'one_hour_after_sunset_to_one_hour_before_sunrise',
        },
        'applies_to': {
            'operation_types': ['passenger', 'night'],
        },
        'priority': 20,
    },
    {
        'code': 'IFR',
        'name': 'IFR Currency',
        'requirement_type': CurrencyType.IFR,
        'regulatory_reference': 'FAR 61.57(c) / EASA FCL.060(c)',
        'criteria': {
            'period_days': 180,  # 6 months
            'min_approaches': 6,
            'min_holding_procedures': 1,
            'min_intercepting_tracking': 1,
        },
        'applies_to': {
            'operation_types': ['ifr'],
        },
        'priority': 30,
    },
    {
        'code': 'TAILWHEEL',
        'name': 'Tailwheel Currency',
        'requirement_type': CurrencyType.TAILWHEEL,
        'regulatory_reference': 'FAR 61.31(i)',
        'criteria': {
            'period_days': 90,
            'min_takeoffs': 3,
            'min_landings': 3,
            'full_stop_required': True,
            'aircraft_type': 'tailwheel',
        },
        'applies_to': {
            'aircraft_types': ['tailwheel'],
        },
        'priority': 40,
    },
]
