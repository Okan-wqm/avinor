# services/certificate-service/src/apps/core/models/rating_revalidation.py
"""
Rating Revalidation Model

EASA FCL.740 - Validity of ratings
EASA FCL.745 - Class rating revalidation requirements

Implements comprehensive rating revalidation tracking per EASA Part-FCL.
"""

import uuid
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional, Dict, Any, List
from dateutil.relativedelta import relativedelta

from django.db import models
from django.contrib.postgres.fields import ArrayField


class RevalidationType(models.TextChoices):
    """Revalidation type choices per FCL.740."""
    PROFICIENCY_CHECK = 'proficiency_check', 'Proficiency Check'
    TRAINING_FLIGHT = 'training_flight', 'Training Flight with Instructor'
    EXPERIENCE_BASED = 'experience_based', 'Experience-Based Revalidation'
    RENEWAL = 'renewal', 'Renewal (after lapse)'
    INITIAL = 'initial', 'Initial Issue'


class RatingCategory(models.TextChoices):
    """Rating category for revalidation rules."""
    # Class Ratings (FCL.740.A)
    SEP_LAND = 'sep_land', 'Single Engine Piston (Land)'
    SEP_SEA = 'sep_sea', 'Single Engine Piston (Sea)'
    MEP_LAND = 'mep_land', 'Multi Engine Piston (Land)'
    MEP_SEA = 'mep_sea', 'Multi Engine Piston (Sea)'
    SET = 'set', 'Single Engine Turbine'
    MET = 'met', 'Multi Engine Turbine'
    # TMG
    TMG = 'tmg', 'Touring Motor Glider'
    # Type Ratings (FCL.740.A)
    TYPE_SP = 'type_sp', 'Type Rating - Single Pilot'
    TYPE_MP = 'type_mp', 'Type Rating - Multi Pilot'
    # Instrument Ratings (FCL.740.B)
    IR_SE = 'ir_se', 'Instrument Rating - Single Engine'
    IR_ME = 'ir_me', 'Instrument Rating - Multi Engine'
    EIR = 'eir', 'En-Route Instrument Rating'
    # Other Ratings
    NIGHT = 'night', 'Night Rating'
    AEROBATIC = 'aerobatic', 'Aerobatic Rating'
    TOWING = 'towing', 'Towing Rating'
    MOUNTAIN = 'mountain', 'Mountain Rating'


class RevalidationStatus(models.TextChoices):
    """Revalidation status choices."""
    VALID = 'valid', 'Valid'
    EXPIRING_SOON = 'expiring_soon', 'Expiring Soon'
    EXPIRED = 'expired', 'Expired'
    LAPSED = 'lapsed', 'Lapsed (requires renewal)'
    PENDING = 'pending', 'Pending Revalidation'


# =============================================================================
# FCL.740/745 Revalidation Requirements Constants
# =============================================================================
class FCL740Requirements:
    """
    EASA FCL.740 Rating Validity Requirements.

    FCL.740.A - Revalidation of class and type ratings:
    (1) Single-pilot class ratings:
        - Within 3 months preceding expiry:
        - Proficiency check OR
        - 12 hours flight time + 1 hour training flight with instructor

    (2) Single-pilot type ratings:
        - Within 3 months preceding expiry:
        - Proficiency check including at least 1 section in aircraft

    (3) Multi-pilot ratings:
        - Within 3 months preceding expiry:
        - Proficiency check

    FCL.740.B - Revalidation of IRs:
    - Within 3 months preceding expiry
    - Pass IR proficiency check
    """

    # Validity Periods (months)
    CLASS_RATING_VALIDITY = 24  # 2 years
    TYPE_RATING_SP_VALIDITY = 12  # 1 year
    TYPE_RATING_MP_VALIDITY = 12  # 1 year
    IR_VALIDITY = 12  # 1 year
    EIR_VALIDITY = 12  # 1 year
    NIGHT_RATING_VALIDITY = None  # No expiry (lifetime)
    MOUNTAIN_RATING_VALIDITY = 24  # 2 years

    # Revalidation Windows (months before expiry)
    REVALIDATION_WINDOW = 3  # Can revalidate within 3 months of expiry

    # FCL.745.A - SEP/MEP Revalidation Requirements
    SEP_MEP_FLIGHT_HOURS = 12  # 12 hours in class
    SEP_MEP_TRAINING_HOURS = 1  # 1 hour with instructor
    SEP_MEP_TAKEOFFS_LANDINGS = 12  # 12 takeoffs and landings

    # IR Revalidation
    IR_FLIGHT_HOURS_RECENT = 10  # Recent IFR experience


class RatingRevalidationRule(models.Model):
    """
    Revalidation rule definition per rating category.

    Defines the requirements for revalidating each type of rating.
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
        help_text='Organization-specific rules (null = global)'
    )

    # Rating Category
    rating_category = models.CharField(
        max_length=50,
        choices=RatingCategory.choices,
        unique=True
    )

    # Regulatory Reference
    regulatory_reference = models.CharField(
        max_length=100,
        help_text='e.g., FCL.740.A(b)(1)'
    )

    # Validity Period
    validity_months = models.PositiveIntegerField(
        help_text='Validity period in months'
    )

    # Revalidation Window
    revalidation_window_months = models.PositiveIntegerField(
        default=3,
        help_text='Months before expiry when revalidation can occur'
    )

    # Requirements
    requires_proficiency_check = models.BooleanField(default=True)
    proficiency_check_can_be_replaced = models.BooleanField(
        default=False,
        help_text='Can experience replace proficiency check'
    )

    # Experience-Based Revalidation (FCL.745.A)
    min_flight_hours = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        blank=True,
        null=True,
        help_text='Minimum flight hours in rating (e.g., 12 for SEP)'
    )
    min_training_hours = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        blank=True,
        null=True,
        help_text='Minimum training hours with instructor (e.g., 1)'
    )
    min_takeoffs_landings = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text='Minimum takeoffs/landings'
    )

    # Renewal Requirements (if lapsed)
    lapse_period_months = models.PositiveIntegerField(
        default=36,
        help_text='Months after expiry before renewal required'
    )
    renewal_requires_training = models.BooleanField(
        default=True,
        help_text='Renewal requires refresher training'
    )
    renewal_training_hours = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        blank=True,
        null=True,
        help_text='Hours of refresher training for renewal'
    )

    # Notes
    description = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

    # Active
    is_active = models.BooleanField(default=True)

    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'rating_revalidation_rules'
        ordering = ['rating_category']

    def __str__(self) -> str:
        return f"{self.get_rating_category_display()} - {self.regulatory_reference}"


class RatingRevalidation(models.Model):
    """
    Individual rating revalidation record.

    Tracks each revalidation event for a pilot's rating.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    organization_id = models.UUIDField(db_index=True)
    user_id = models.UUIDField(db_index=True)

    # Link to Rating
    rating_id = models.UUIDField(db_index=True)
    rating_category = models.CharField(
        max_length=50,
        choices=RatingCategory.choices
    )

    # Revalidation Type
    revalidation_type = models.CharField(
        max_length=50,
        choices=RevalidationType.choices
    )

    # Dates
    revalidation_date = models.DateField()
    previous_expiry_date = models.DateField(
        blank=True,
        null=True,
        help_text='Expiry date before revalidation'
    )
    new_expiry_date = models.DateField(
        help_text='New expiry date after revalidation'
    )

    # Status
    status = models.CharField(
        max_length=20,
        choices=RevalidationStatus.choices,
        default=RevalidationStatus.VALID
    )

    # Examiner/Instructor (for proficiency check)
    examiner_id = models.UUIDField(blank=True, null=True)
    examiner_name = models.CharField(max_length=255, blank=True, null=True)
    examiner_certificate = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text='FE/TRE certificate number'
    )

    # Instructor (for training flight)
    instructor_id = models.UUIDField(blank=True, null=True)
    instructor_name = models.CharField(max_length=255, blank=True, null=True)
    instructor_certificate = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text='FI/CRI certificate number'
    )

    # Training/Experience Details (for FCL.745.A experience-based)
    flight_hours_logged = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        blank=True,
        null=True,
        help_text='Hours flown in rating period'
    )
    training_hours = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True,
        help_text='Hours with instructor'
    )
    takeoffs_landings = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text='Takeoffs/landings in period'
    )

    # Aircraft Used
    aircraft_registration = models.CharField(
        max_length=20,
        blank=True,
        null=True
    )
    aircraft_type = models.CharField(
        max_length=50,
        blank=True,
        null=True
    )
    simulator_used = models.BooleanField(default=False)
    simulator_id = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text='FSTD identifier'
    )

    # Proficiency Check Details
    proficiency_sections = models.JSONField(
        default=list,
        blank=True,
        help_text='Proficiency check sections completed'
    )
    proficiency_result = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        choices=[
            ('pass', 'Pass'),
            ('partial', 'Partial Pass'),
            ('fail', 'Fail'),
        ]
    )

    # Training Flight Details (FCL.745.A(b)(1)(ii))
    training_maneuvers = models.JSONField(
        default=list,
        blank=True,
        help_text='Maneuvers completed during training flight'
    )

    # Documents
    document_url = models.URLField(max_length=500, blank=True, null=True)
    certificate_url = models.URLField(max_length=500, blank=True, null=True)

    # Notes
    notes = models.TextField(blank=True, null=True)
    remarks = models.TextField(blank=True, null=True)

    # Metadata
    metadata = models.JSONField(default=dict, blank=True)

    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.UUIDField(blank=True, null=True)

    class Meta:
        db_table = 'rating_revalidations'
        ordering = ['-revalidation_date']
        indexes = [
            models.Index(fields=['organization_id', 'user_id']),
            models.Index(fields=['rating_id']),
            models.Index(fields=['revalidation_date']),
            models.Index(fields=['new_expiry_date']),
        ]

    def __str__(self) -> str:
        return f"{self.get_rating_category_display()} - {self.revalidation_date}"

    @property
    def is_within_window(self) -> bool:
        """Check if revalidation was within the valid window."""
        if not self.previous_expiry_date:
            return True
        window_start = self.previous_expiry_date - relativedelta(months=3)
        return window_start <= self.revalidation_date <= self.previous_expiry_date

    def get_summary(self) -> Dict[str, Any]:
        """Get revalidation summary."""
        return {
            'id': str(self.id),
            'rating_category': self.rating_category,
            'revalidation_type': self.revalidation_type,
            'revalidation_date': self.revalidation_date.isoformat(),
            'new_expiry_date': self.new_expiry_date.isoformat(),
            'status': self.status,
            'examiner_name': self.examiner_name,
            'instructor_name': self.instructor_name,
            'flight_hours_logged': float(self.flight_hours_logged) if self.flight_hours_logged else None,
            'proficiency_result': self.proficiency_result,
        }


class RatingExperienceLog(models.Model):
    """
    Experience log entry for FCL.745.A experience-based revalidation.

    Tracks flights contributing to experience requirements.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    organization_id = models.UUIDField(db_index=True)
    user_id = models.UUIDField(db_index=True)
    rating_id = models.UUIDField(db_index=True)

    # Flight Reference
    flight_id = models.UUIDField(
        blank=True,
        null=True,
        help_text='Reference to flight log entry'
    )

    # Flight Details
    flight_date = models.DateField()
    aircraft_registration = models.CharField(max_length=20)
    aircraft_type = models.CharField(max_length=50)
    aircraft_class = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text='SEP, MEP, SET, MET, etc.'
    )

    # Time
    flight_time = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text='Total flight time'
    )
    pic_time = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0
    )
    dual_time = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text='Time with instructor'
    )

    # Takeoffs/Landings
    takeoffs = models.PositiveIntegerField(default=0)
    landings = models.PositiveIntegerField(default=0)

    # Route
    departure = models.CharField(max_length=10, blank=True, null=True)
    arrival = models.CharField(max_length=10, blank=True, null=True)

    # Instructor (if dual)
    instructor_id = models.UUIDField(blank=True, null=True)
    instructor_name = models.CharField(max_length=255, blank=True, null=True)

    # Qualifies for revalidation
    counts_for_revalidation = models.BooleanField(
        default=True,
        help_text='Whether this flight counts toward revalidation'
    )

    # Audit
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'rating_experience_logs'
        ordering = ['-flight_date']
        indexes = [
            models.Index(fields=['organization_id', 'user_id', 'rating_id']),
            models.Index(fields=['flight_date']),
        ]

    def __str__(self) -> str:
        return f"{self.flight_date} - {self.aircraft_registration} ({self.flight_time}h)"


# =============================================================================
# Default FCL.740/745 Revalidation Rules
# =============================================================================
DEFAULT_REVALIDATION_RULES = [
    {
        'rating_category': RatingCategory.SEP_LAND,
        'regulatory_reference': 'FCL.740.A(b)(1)',
        'validity_months': 24,
        'requires_proficiency_check': True,
        'proficiency_check_can_be_replaced': True,
        'min_flight_hours': Decimal('12'),
        'min_training_hours': Decimal('1'),
        'min_takeoffs_landings': 12,
        'lapse_period_months': 36,
        'description': 'SEP(Land) class rating - 24 months validity. Revalidation by proficiency check or 12h + 1h training.',
    },
    {
        'rating_category': RatingCategory.SEP_SEA,
        'regulatory_reference': 'FCL.740.A(b)(1)',
        'validity_months': 24,
        'requires_proficiency_check': True,
        'proficiency_check_can_be_replaced': True,
        'min_flight_hours': Decimal('12'),
        'min_training_hours': Decimal('1'),
        'min_takeoffs_landings': 12,
        'lapse_period_months': 36,
        'description': 'SEP(Sea) class rating - 24 months validity.',
    },
    {
        'rating_category': RatingCategory.MEP_LAND,
        'regulatory_reference': 'FCL.740.A(b)(1)',
        'validity_months': 24,
        'requires_proficiency_check': True,
        'proficiency_check_can_be_replaced': True,
        'min_flight_hours': Decimal('12'),
        'min_training_hours': Decimal('1'),
        'min_takeoffs_landings': 12,
        'lapse_period_months': 36,
        'description': 'MEP(Land) class rating - 24 months validity.',
    },
    {
        'rating_category': RatingCategory.TMG,
        'regulatory_reference': 'FCL.740.A(b)(1)',
        'validity_months': 24,
        'requires_proficiency_check': True,
        'proficiency_check_can_be_replaced': True,
        'min_flight_hours': Decimal('12'),
        'min_training_hours': Decimal('1'),
        'min_takeoffs_landings': 12,
        'lapse_period_months': 36,
        'description': 'TMG class rating - 24 months validity.',
    },
    {
        'rating_category': RatingCategory.TYPE_SP,
        'regulatory_reference': 'FCL.740.A(b)(2)',
        'validity_months': 12,
        'requires_proficiency_check': True,
        'proficiency_check_can_be_replaced': False,
        'lapse_period_months': 36,
        'description': 'Single-pilot type rating - 12 months validity. Proficiency check required.',
    },
    {
        'rating_category': RatingCategory.TYPE_MP,
        'regulatory_reference': 'FCL.740.A(b)(3)',
        'validity_months': 12,
        'requires_proficiency_check': True,
        'proficiency_check_can_be_replaced': False,
        'lapse_period_months': 36,
        'description': 'Multi-pilot type rating - 12 months validity. Proficiency check required.',
    },
    {
        'rating_category': RatingCategory.IR_SE,
        'regulatory_reference': 'FCL.740.B',
        'validity_months': 12,
        'requires_proficiency_check': True,
        'proficiency_check_can_be_replaced': False,
        'lapse_period_months': 36,
        'description': 'IR(SE) - 12 months validity. IR proficiency check required.',
    },
    {
        'rating_category': RatingCategory.IR_ME,
        'regulatory_reference': 'FCL.740.B',
        'validity_months': 12,
        'requires_proficiency_check': True,
        'proficiency_check_can_be_replaced': False,
        'lapse_period_months': 36,
        'description': 'IR(ME) - 12 months validity. IR proficiency check required.',
    },
    {
        'rating_category': RatingCategory.EIR,
        'regulatory_reference': 'FCL.740.B',
        'validity_months': 12,
        'requires_proficiency_check': True,
        'proficiency_check_can_be_replaced': False,
        'lapse_period_months': 36,
        'description': 'EIR - 12 months validity.',
    },
    {
        'rating_category': RatingCategory.NIGHT,
        'regulatory_reference': 'FCL.810',
        'validity_months': 0,  # No expiry
        'requires_proficiency_check': False,
        'proficiency_check_can_be_replaced': False,
        'description': 'Night rating - No expiry. Currency requirements per FCL.060.',
    },
    {
        'rating_category': RatingCategory.MOUNTAIN,
        'regulatory_reference': 'FCL.815',
        'validity_months': 24,
        'requires_proficiency_check': True,
        'proficiency_check_can_be_replaced': True,
        'min_flight_hours': Decimal('6'),
        'lapse_period_months': 36,
        'description': 'Mountain rating - 24 months validity.',
    },
    {
        'rating_category': RatingCategory.AEROBATIC,
        'regulatory_reference': 'FCL.800',
        'validity_months': 0,  # No expiry per regulation
        'requires_proficiency_check': False,
        'proficiency_check_can_be_replaced': False,
        'description': 'Aerobatic rating - No expiry. Competency maintenance recommended.',
    },
    {
        'rating_category': RatingCategory.TOWING,
        'regulatory_reference': 'FCL.805',
        'validity_months': 24,
        'requires_proficiency_check': True,
        'proficiency_check_can_be_replaced': True,
        'min_flight_hours': Decimal('5'),
        'lapse_period_months': 36,
        'description': 'Towing rating - 24 months validity.',
    },
]
