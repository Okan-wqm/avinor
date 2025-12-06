# services/certificate-service/src/apps/core/models/experience_crediting.py
"""
Experience Crediting Model

EASA FCL.035 - Crediting of Flight Time
Comprehensive experience crediting per EASA Part-FCL.
"""

import uuid
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional, Dict, Any, List
from dateutil.relativedelta import relativedelta

from django.db import models
from django.contrib.postgres.fields import ArrayField


class CreditingType(models.TextChoices):
    """Types of experience crediting per FCL.035."""
    # FCL.035 - Crediting of flight time
    FLIGHT_TIME = 'flight_time', 'Flight Time Credit'

    # License upgrades
    PPL_TO_CPL = 'ppl_to_cpl', 'PPL to CPL Credit'
    CPL_TO_ATPL = 'cpl_to_atpl', 'CPL to ATPL Credit'
    LAPL_TO_PPL = 'lapl_to_ppl', 'LAPL to PPL Credit'

    # Category/Class
    SINGLE_TO_MULTI = 'single_to_multi', 'Single to Multi-Engine'
    LAND_TO_SEA = 'land_to_sea', 'Land to Sea'
    AIRPLANE_TO_HELICOPTER = 'airplane_heli', 'Airplane to Helicopter'

    # Ratings
    CLASS_RATING_CREDIT = 'class_rating', 'Class Rating Credit'
    TYPE_RATING_CREDIT = 'type_rating', 'Type Rating Credit'
    IR_CREDIT = 'ir_credit', 'Instrument Rating Credit'

    # Military
    MILITARY_CREDIT = 'military', 'Military Service Credit'

    # Simulator
    FSTD_CREDIT = 'fstd', 'FSTD Credit'


class CreditingStatus(models.TextChoices):
    """Experience crediting application status."""
    PENDING = 'pending', 'Pending Review'
    APPROVED = 'approved', 'Approved'
    PARTIALLY_APPROVED = 'partial', 'Partially Approved'
    DENIED = 'denied', 'Denied'
    EXPIRED = 'expired', 'Expired'


# =============================================================================
# FCL.035 Credit Rules
# =============================================================================
class FCL035CreditRules:
    """
    EASA FCL.035 Crediting rules.

    Flight time as PIC, co-pilot, or under instruction counts.
    Specific credit rules apply for different license/rating applications.
    """

    # General credit limits
    MAX_FSTD_CREDIT_PERCENTAGE = 50  # Maximum simulator credit

    # PPL to CPL (FCL.315)
    PPL_TO_CPL_XC_CREDIT = True  # XC time creditable
    PPL_TO_CPL_INSTRUMENT_CREDIT = 30  # Max IR time credited

    # CPL to ATPL
    CPL_PIC_HOURS_REQUIRED = 1500  # For ATPL
    CPL_COPILOT_CREDIT = 0.5  # 50% credit for copilot

    # LAPL to PPL
    LAPL_TO_PPL_FULL_CREDIT = True  # Full credit for LAPL hours

    # Multi-engine credit
    SE_TO_ME_CREDIT_PERCENTAGE = 100  # SE hours count for ME

    # Airplane to Helicopter
    AIRPLANE_TO_HELI_CREDIT_PERCENTAGE = 10  # 10% of airplane time

    # IR Credits
    IR_SE_TO_ME_CREDIT = True  # SE IR counts for ME IR
    IR_ME_TO_SE_CREDIT = True  # ME IR counts for SE IR

    # Military credit
    MILITARY_MAX_CREDIT_PERCENTAGE = 100


class ExperienceCredit(models.Model):
    """
    Experience crediting application/record per FCL.035.

    Tracks credit applications for license/rating requirements.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    organization_id = models.UUIDField(db_index=True)
    user_id = models.UUIDField(db_index=True)

    # Credit Application
    credit_type = models.CharField(
        max_length=50,
        choices=CreditingType.choices
    )
    status = models.CharField(
        max_length=20,
        choices=CreditingStatus.choices,
        default=CreditingStatus.PENDING
    )

    # Regulatory Reference
    regulatory_reference = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text='FCL reference (e.g., FCL.035, FCL.315)'
    )

    # What is being applied for
    target_license = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text='License being applied for'
    )
    target_rating = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text='Rating being applied for'
    )

    # Source Experience
    source_category = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text='Source aircraft category (e.g., airplane, helicopter)'
    )
    source_class = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text='Source class (e.g., SEP, MEP)'
    )
    source_type = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text='Source aircraft type'
    )

    # Hours Claimed
    total_hours_claimed = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        help_text='Total hours claimed for credit'
    )
    pic_hours_claimed = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        default=0
    )
    copilot_hours_claimed = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        default=0
    )
    dual_hours_claimed = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        default=0
    )
    instrument_hours_claimed = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        default=0
    )
    night_hours_claimed = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        default=0
    )
    xc_hours_claimed = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        default=0,
        help_text='Cross-country hours'
    )
    simulator_hours_claimed = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        default=0
    )

    # Credit Percentage Applied
    credit_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('100.00'),
        help_text='Percentage of claimed hours credited'
    )

    # Hours Credited (after application of rules)
    total_hours_credited = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        blank=True,
        null=True,
        help_text='Hours actually credited'
    )
    pic_hours_credited = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        default=0
    )
    copilot_hours_credited = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        default=0
    )
    dual_hours_credited = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        default=0
    )
    instrument_hours_credited = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        default=0
    )

    # Supporting Documentation
    logbook_verified = models.BooleanField(
        default=False,
        help_text='Logbook entries verified'
    )
    license_verified = models.BooleanField(
        default=False,
        help_text='Source license verified'
    )
    documentation_urls = ArrayField(
        models.URLField(max_length=500),
        default=list,
        blank=True
    )

    # Military Specific
    is_military_credit = models.BooleanField(default=False)
    military_service_branch = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )
    military_aircraft_types = ArrayField(
        models.CharField(max_length=50),
        default=list,
        blank=True
    )
    military_qualification = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    # Dates
    application_date = models.DateField(auto_now_add=True)
    review_date = models.DateField(blank=True, null=True)
    approval_date = models.DateField(blank=True, null=True)
    expiry_date = models.DateField(
        blank=True,
        null=True,
        help_text='Credit validity expiry'
    )

    # Reviewer
    reviewed_by = models.UUIDField(blank=True, null=True)
    reviewer_name = models.CharField(max_length=255, blank=True, null=True)
    reviewer_notes = models.TextField(blank=True, null=True)

    # Denial Reason
    denial_reason = models.TextField(blank=True, null=True)

    # Notes
    notes = models.TextField(blank=True, null=True)

    # Metadata
    metadata = models.JSONField(default=dict, blank=True)

    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.UUIDField(blank=True, null=True)

    class Meta:
        db_table = 'experience_credits'
        ordering = ['-application_date']
        indexes = [
            models.Index(fields=['organization_id', 'user_id']),
            models.Index(fields=['credit_type']),
            models.Index(fields=['status']),
            models.Index(fields=['target_license']),
        ]

    def __str__(self) -> str:
        return f"{self.get_credit_type_display()} - {self.total_hours_credited}h"

    @property
    def is_valid(self) -> bool:
        """Check if credit is still valid."""
        if self.status != CreditingStatus.APPROVED:
            return False
        if self.expiry_date and self.expiry_date < date.today():
            return False
        return True

    def calculate_credit(self) -> None:
        """Calculate credited hours based on rules."""
        percentage = self.credit_percentage / Decimal('100')

        self.total_hours_credited = self.total_hours_claimed * percentage
        self.pic_hours_credited = self.pic_hours_claimed * percentage
        self.copilot_hours_credited = self.copilot_hours_claimed * Decimal('0.5')  # 50% for copilot
        self.dual_hours_credited = self.dual_hours_claimed * percentage
        self.instrument_hours_credited = self.instrument_hours_claimed * percentage

    def get_summary(self) -> Dict[str, Any]:
        """Get credit summary."""
        return {
            'credit_id': str(self.id),
            'credit_type': self.credit_type,
            'status': self.status,
            'target_license': self.target_license,
            'target_rating': self.target_rating,
            'hours_claimed': float(self.total_hours_claimed),
            'hours_credited': float(self.total_hours_credited or 0),
            'credit_percentage': float(self.credit_percentage),
            'is_valid': self.is_valid,
            'application_date': self.application_date.isoformat() if self.application_date else None,
            'approval_date': self.approval_date.isoformat() if self.approval_date else None,
            'expiry_date': self.expiry_date.isoformat() if self.expiry_date else None,
        }


class ExperienceRequirement(models.Model):
    """
    Experience requirements for licenses and ratings.

    Defines the minimum experience needed per FCL.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    organization_id = models.UUIDField(
        db_index=True,
        blank=True,
        null=True,
        help_text='Organization-specific (null = global)'
    )

    # Requirement For
    license_type = models.CharField(
        max_length=50,
        help_text='License type (PPL, CPL, ATPL)'
    )
    rating_type = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text='Rating type if applicable'
    )

    # Regulatory Reference
    regulatory_reference = models.CharField(
        max_length=100,
        help_text='FCL reference'
    )

    # Total Time Requirements
    total_hours_required = models.DecimalField(
        max_digits=6,
        decimal_places=1
    )
    pic_hours_required = models.DecimalField(
        max_digits=6,
        decimal_places=1,
        default=0
    )
    dual_hours_required = models.DecimalField(
        max_digits=6,
        decimal_places=1,
        default=0
    )

    # Specific Requirements
    xc_hours_required = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        default=0,
        help_text='Cross-country hours'
    )
    xc_pic_hours_required = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        default=0
    )
    night_hours_required = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        default=0
    )
    instrument_hours_required = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        default=0
    )
    multi_engine_hours = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        default=0
    )

    # Training Requirements
    training_hours_required = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        default=0,
        help_text='Minimum training with ATO'
    )

    # FSTD Allowance
    max_fstd_hours = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        default=0,
        help_text='Maximum FSTD hours creditable'
    )

    # Long XC Requirement
    long_xc_required = models.BooleanField(default=False)
    long_xc_distance_nm = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text='Minimum XC distance in NM'
    )
    long_xc_full_stop_landings = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text='Full stop landings at different aerodromes'
    )

    # Solo Requirements
    solo_hours_required = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        default=0
    )
    solo_xc_hours_required = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        default=0
    )

    # Description
    description = models.TextField(blank=True, null=True)

    # Active
    is_active = models.BooleanField(default=True)

    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'experience_requirements'
        ordering = ['license_type', 'rating_type']
        unique_together = [['organization_id', 'license_type', 'rating_type']]

    def __str__(self) -> str:
        if self.rating_type:
            return f"{self.license_type} - {self.rating_type}"
        return self.license_type


class PilotExperienceLog(models.Model):
    """
    Aggregated pilot experience for requirement tracking.

    Summarizes pilot's total experience by category.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    organization_id = models.UUIDField(db_index=True)
    user_id = models.UUIDField(db_index=True, unique=True)

    # Total Experience
    total_flight_time = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0
    )
    total_pic_time = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0
    )
    total_copilot_time = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0
    )
    total_dual_time = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0
    )
    total_instructor_time = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0
    )

    # By Condition
    total_night_time = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        default=0
    )
    total_instrument_time = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        default=0
    )
    actual_instrument_time = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        default=0
    )
    simulated_instrument_time = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        default=0
    )

    # Cross Country
    total_xc_time = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        default=0
    )
    xc_pic_time = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        default=0
    )

    # By Category
    airplane_time = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0
    )
    helicopter_time = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0
    )
    glider_time = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        default=0
    )
    balloon_time = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        default=0
    )

    # By Class (Airplane)
    sep_time = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        default=0,
        help_text='Single Engine Piston'
    )
    mep_time = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        default=0,
        help_text='Multi Engine Piston'
    )
    set_time = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        default=0,
        help_text='Single Engine Turbine'
    )
    met_time = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        default=0,
        help_text='Multi Engine Turbine'
    )

    # Simulator
    fstd_time = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        default=0,
        help_text='Flight Simulator Training Device'
    )
    fnpt_time = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        default=0,
        help_text='Flight Navigation Procedures Trainer'
    )

    # Takeoffs/Landings
    total_takeoffs = models.PositiveIntegerField(default=0)
    total_landings = models.PositiveIntegerField(default=0)
    night_landings = models.PositiveIntegerField(default=0)

    # Type Experience (JSON for flexibility)
    type_experience = models.JSONField(
        default=dict,
        blank=True,
        help_text='Hours by aircraft type'
    )

    # Last Updated From
    last_flight_date = models.DateField(blank=True, null=True)
    last_sync_date = models.DateTimeField(blank=True, null=True)

    # Metadata
    metadata = models.JSONField(default=dict, blank=True)

    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'pilot_experience_logs'
        indexes = [
            models.Index(fields=['organization_id', 'user_id']),
        ]

    def __str__(self) -> str:
        return f"Experience Log - {self.total_flight_time}h total"

    def check_requirements(
        self,
        requirement: ExperienceRequirement
    ) -> Dict[str, Any]:
        """Check if pilot meets experience requirements."""
        checks = {}

        # Total hours
        checks['total_hours'] = {
            'required': float(requirement.total_hours_required),
            'logged': float(self.total_flight_time),
            'met': self.total_flight_time >= requirement.total_hours_required,
        }

        # PIC hours
        if requirement.pic_hours_required > 0:
            checks['pic_hours'] = {
                'required': float(requirement.pic_hours_required),
                'logged': float(self.total_pic_time),
                'met': self.total_pic_time >= requirement.pic_hours_required,
            }

        # XC hours
        if requirement.xc_hours_required > 0:
            checks['xc_hours'] = {
                'required': float(requirement.xc_hours_required),
                'logged': float(self.total_xc_time),
                'met': self.total_xc_time >= requirement.xc_hours_required,
            }

        # Night hours
        if requirement.night_hours_required > 0:
            checks['night_hours'] = {
                'required': float(requirement.night_hours_required),
                'logged': float(self.total_night_time),
                'met': self.total_night_time >= requirement.night_hours_required,
            }

        # Instrument hours
        if requirement.instrument_hours_required > 0:
            checks['instrument_hours'] = {
                'required': float(requirement.instrument_hours_required),
                'logged': float(self.total_instrument_time),
                'met': self.total_instrument_time >= requirement.instrument_hours_required,
            }

        # Calculate overall
        all_met = all(c['met'] for c in checks.values())

        return {
            'license_type': requirement.license_type,
            'rating_type': requirement.rating_type,
            'all_requirements_met': all_met,
            'checks': checks,
        }

    def get_summary(self) -> Dict[str, Any]:
        """Get experience summary."""
        return {
            'user_id': str(self.user_id),
            'total_time': float(self.total_flight_time),
            'pic_time': float(self.total_pic_time),
            'copilot_time': float(self.total_copilot_time),
            'dual_time': float(self.total_dual_time),
            'instructor_time': float(self.total_instructor_time),
            'night_time': float(self.total_night_time),
            'instrument_time': float(self.total_instrument_time),
            'xc_time': float(self.total_xc_time),
            'by_category': {
                'airplane': float(self.airplane_time),
                'helicopter': float(self.helicopter_time),
                'glider': float(self.glider_time),
            },
            'by_class': {
                'sep': float(self.sep_time),
                'mep': float(self.mep_time),
                'set': float(self.set_time),
                'met': float(self.met_time),
            },
            'simulator': float(self.fstd_time),
            'takeoffs': self.total_takeoffs,
            'landings': self.total_landings,
            'last_flight_date': (
                self.last_flight_date.isoformat()
                if self.last_flight_date else None
            ),
        }


# Default Experience Requirements per FCL
DEFAULT_EXPERIENCE_REQUIREMENTS = [
    {
        'license_type': 'PPL(A)',
        'regulatory_reference': 'FCL.210',
        'total_hours_required': Decimal('45'),
        'dual_hours_required': Decimal('25'),
        'solo_hours_required': Decimal('10'),
        'solo_xc_hours_required': Decimal('5'),
        'xc_hours_required': Decimal('5'),
        'long_xc_required': True,
        'long_xc_distance_nm': 150,
        'long_xc_full_stop_landings': 2,
        'description': 'PPL(A) minimum experience per FCL.210',
    },
    {
        'license_type': 'CPL(A)',
        'regulatory_reference': 'FCL.315',
        'total_hours_required': Decimal('200'),
        'pic_hours_required': Decimal('100'),
        'xc_hours_required': Decimal('20'),
        'xc_pic_hours_required': Decimal('10'),
        'instrument_hours_required': Decimal('10'),
        'night_hours_required': Decimal('5'),
        'long_xc_required': True,
        'long_xc_distance_nm': 300,
        'long_xc_full_stop_landings': 2,
        'description': 'CPL(A) minimum experience per FCL.315',
    },
    {
        'license_type': 'ATPL(A)',
        'regulatory_reference': 'FCL.510',
        'total_hours_required': Decimal('1500'),
        'pic_hours_required': Decimal('500'),
        'xc_hours_required': Decimal('200'),
        'night_hours_required': Decimal('100'),
        'instrument_hours_required': Decimal('75'),
        'multi_engine_hours': Decimal('500'),
        'description': 'ATPL(A) minimum experience per FCL.510',
    },
    {
        'license_type': 'IR(A)',
        'rating_type': 'IR',
        'regulatory_reference': 'FCL.610',
        'total_hours_required': Decimal('50'),
        'xc_pic_hours_required': Decimal('50'),
        'instrument_hours_required': Decimal('40'),
        'max_fstd_hours': Decimal('15'),
        'description': 'IR experience requirements per FCL.610',
    },
    {
        'license_type': 'LAPL(A)',
        'regulatory_reference': 'FCL.110.A',
        'total_hours_required': Decimal('30'),
        'dual_hours_required': Decimal('15'),
        'solo_hours_required': Decimal('6'),
        'solo_xc_hours_required': Decimal('3'),
        'long_xc_required': True,
        'long_xc_distance_nm': 80,
        'long_xc_full_stop_landings': 1,
        'description': 'LAPL(A) minimum experience per FCL.110.A',
    },
]
