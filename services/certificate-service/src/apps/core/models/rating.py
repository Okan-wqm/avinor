# services/certificate-service/src/apps/core/models/rating.py
"""
Rating Model

Aircraft type ratings, class ratings, and other pilot ratings/privileges.
"""

import uuid
from datetime import date, timedelta
from typing import Optional, Dict, Any, List

from django.db import models
from django.contrib.postgres.fields import ArrayField


class RatingType(models.TextChoices):
    """Rating type choices."""
    # Type Ratings
    AIRCRAFT_TYPE = 'aircraft_type', 'Aircraft Type Rating'
    # Class Ratings
    CLASS_SEP = 'class_sep', 'Single Engine Piston (SEP)'
    CLASS_MEP = 'class_mep', 'Multi Engine Piston (MEP)'
    CLASS_SET = 'class_set', 'Single Engine Turbine (SET)'
    CLASS_MET = 'class_met', 'Multi Engine Turbine (MET)'
    # Instrument Ratings
    INSTRUMENT = 'instrument', 'Instrument Rating (IR)'
    INSTRUMENT_EIR = 'instrument_eir', 'En-Route Instrument Rating (EIR)'
    # Other Ratings
    INSTRUCTOR = 'instructor', 'Instructor Rating'
    NIGHT = 'night', 'Night Rating'
    AEROBATIC = 'aerobatic', 'Aerobatic Rating'
    TOWING = 'towing', 'Towing Rating'
    MOUNTAIN = 'mountain', 'Mountain Rating'
    SEAPLANE = 'seaplane', 'Seaplane Rating'
    TAILWHEEL = 'tailwheel', 'Tailwheel Endorsement'
    HIGH_PERFORMANCE = 'high_performance', 'High Performance'
    COMPLEX = 'complex', 'Complex Aircraft'
    PRESSURIZED = 'pressurized', 'Pressurized Aircraft'


class RatingStatus(models.TextChoices):
    """Rating status choices."""
    ACTIVE = 'active', 'Active'
    EXPIRED = 'expired', 'Expired'
    SUSPENDED = 'suspended', 'Suspended'
    LAPSED = 'lapsed', 'Lapsed'
    PENDING = 'pending', 'Pending'


class Rating(models.Model):
    """
    Rating/Privilege model.

    Stores type ratings, class ratings, instrument ratings, and other
    pilot ratings/privileges that are attached to a license.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    organization_id = models.UUIDField(db_index=True)
    user_id = models.UUIDField(db_index=True)

    # Link to certificate (optional - some ratings standalone)
    certificate_id = models.UUIDField(
        blank=True,
        null=True,
        db_index=True,
        help_text='Associated pilot license'
    )

    # Rating Type
    rating_type = models.CharField(
        max_length=50,
        choices=RatingType.choices,
        db_index=True
    )
    rating_code = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text='Standard rating code'
    )
    rating_name = models.CharField(
        max_length=255,
        help_text='Full rating name'
    )

    # Aircraft Type (for type ratings)
    aircraft_type_id = models.UUIDField(
        blank=True,
        null=True,
        help_text='Reference to aircraft type'
    )
    aircraft_icao = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        help_text='ICAO aircraft type designator'
    )
    aircraft_name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text='Aircraft type name'
    )

    # Dates
    issue_date = models.DateField()
    expiry_date = models.DateField(blank=True, null=True, db_index=True)
    last_proficiency_date = models.DateField(
        blank=True,
        null=True,
        help_text='Last proficiency check date'
    )
    next_proficiency_date = models.DateField(
        blank=True,
        null=True,
        help_text='Next required proficiency check'
    )

    # Validity Requirements
    validity_period_months = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text='Validity period in months'
    )
    proficiency_check_months = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text='Proficiency check interval in months'
    )

    # Status
    status = models.CharField(
        max_length=20,
        choices=RatingStatus.choices,
        default=RatingStatus.ACTIVE,
        db_index=True
    )

    # Restrictions
    restrictions = ArrayField(
        models.CharField(max_length=255),
        default=list,
        blank=True,
        help_text='Rating restrictions (e.g., SIC only, VFR only)'
    )

    # Training Information
    training_organization = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text='ATO/Training organization'
    )
    training_completion_date = models.DateField(
        blank=True,
        null=True
    )
    examiner_id = models.UUIDField(
        blank=True,
        null=True,
        help_text='Examiner who conducted skill test'
    )
    examiner_name = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )
    skill_test_date = models.DateField(
        blank=True,
        null=True
    )

    # Operating Minima (for IR)
    operating_minima = models.JSONField(
        default=dict,
        blank=True,
        help_text='IFR operating minima if applicable'
    )

    # PIC Hours on Type
    pic_hours_on_type = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0,
        help_text='PIC hours on this aircraft type'
    )
    total_hours_on_type = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0,
        help_text='Total hours on this aircraft type'
    )

    # Document
    document_url = models.URLField(max_length=500, blank=True, null=True)

    # Notes
    notes = models.TextField(blank=True, null=True)

    # Metadata
    metadata = models.JSONField(default=dict, blank=True)

    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.UUIDField(blank=True, null=True)

    class Meta:
        db_table = 'ratings'
        ordering = ['rating_type', 'rating_name']
        indexes = [
            models.Index(fields=['organization_id', 'user_id']),
            models.Index(fields=['rating_type', 'status']),
            models.Index(fields=['aircraft_icao']),
            models.Index(fields=['expiry_date']),
        ]

    def __str__(self) -> str:
        return f"{self.get_rating_type_display()}: {self.rating_name}"

    @property
    def is_valid(self) -> bool:
        """Check if rating is currently valid."""
        if self.status != RatingStatus.ACTIVE:
            return False
        if self.expiry_date and self.expiry_date < date.today():
            return False
        return True

    @property
    def is_expired(self) -> bool:
        """Check if rating is expired."""
        if not self.expiry_date:
            return False
        return self.expiry_date < date.today()

    @property
    def days_until_expiry(self) -> Optional[int]:
        """Calculate days until expiry."""
        if not self.expiry_date:
            return None
        return (self.expiry_date - date.today()).days

    @property
    def is_proficiency_due(self) -> bool:
        """Check if proficiency check is due."""
        if not self.next_proficiency_date:
            return False
        return self.next_proficiency_date <= date.today()

    @property
    def days_until_proficiency(self) -> Optional[int]:
        """Calculate days until proficiency check."""
        if not self.next_proficiency_date:
            return None
        return (self.next_proficiency_date - date.today()).days

    def check_recent_experience(
        self,
        required_flights: int = 1,
        required_hours: float = 0,
        period_days: int = 90
    ) -> Dict[str, Any]:
        """
        Check recent experience requirements for the rating.

        Returns dict with currency status.
        """
        # This would typically call flight service to check recent experience
        # Placeholder implementation
        return {
            'is_current': True,
            'flights_in_period': 0,
            'hours_in_period': 0,
            'period_days': period_days,
            'required_flights': required_flights,
            'required_hours': required_hours,
        }

    def update_status(self) -> None:
        """Update status based on current state."""
        if self.status in [RatingStatus.SUSPENDED]:
            return

        if self.is_expired:
            self.status = RatingStatus.EXPIRED
            self.save(update_fields=['status', 'updated_at'])

    def record_proficiency_check(
        self,
        check_date: date,
        examiner_id: uuid.UUID,
        examiner_name: str,
        passed: bool = True
    ) -> None:
        """Record a proficiency check."""
        if not passed:
            self.status = RatingStatus.SUSPENDED
            self.notes = f"{self.notes or ''}\nFailed proficiency check on {check_date}".strip()
        else:
            self.last_proficiency_date = check_date
            if self.proficiency_check_months:
                self.next_proficiency_date = check_date + timedelta(
                    days=self.proficiency_check_months * 30
                )
            self.status = RatingStatus.ACTIVE

        self.examiner_id = examiner_id
        self.examiner_name = examiner_name
        self.save()

    def renew(
        self,
        new_expiry_date: date,
        proficiency_check_date: Optional[date] = None
    ) -> None:
        """Renew the rating with new expiry date."""
        self.expiry_date = new_expiry_date
        if proficiency_check_date:
            self.last_proficiency_date = proficiency_check_date
            if self.proficiency_check_months:
                self.next_proficiency_date = proficiency_check_date + timedelta(
                    days=self.proficiency_check_months * 30
                )
        self.status = RatingStatus.ACTIVE
        self.save()

    def get_validity_info(self) -> Dict[str, Any]:
        """Get detailed validity information."""
        return {
            'rating_id': str(self.id),
            'rating_type': self.rating_type,
            'rating_name': self.rating_name,
            'aircraft_icao': self.aircraft_icao,
            'status': self.status,
            'is_valid': self.is_valid,
            'is_expired': self.is_expired,
            'expiry_date': self.expiry_date.isoformat() if self.expiry_date else None,
            'days_until_expiry': self.days_until_expiry,
            'is_proficiency_due': self.is_proficiency_due,
            'next_proficiency_date': self.next_proficiency_date.isoformat() if self.next_proficiency_date else None,
            'days_until_proficiency': self.days_until_proficiency,
            'restrictions': self.restrictions,
            'pic_hours_on_type': float(self.pic_hours_on_type),
            'total_hours_on_type': float(self.total_hours_on_type),
        }
