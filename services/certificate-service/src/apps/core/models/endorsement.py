# services/certificate-service/src/apps/core/models/endorsement.py
"""
Endorsement Model

Instructor endorsements and sign-offs for students.
"""

import uuid
from datetime import date, timedelta
from typing import Optional, Dict, Any, List

from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.utils import timezone


class EndorsementType(models.TextChoices):
    """Endorsement type choices."""
    # Student Endorsements
    SOLO_FLIGHT = 'solo_flight', 'Solo Flight'
    SOLO_CROSS_COUNTRY = 'solo_cross_country', 'Solo Cross Country'
    SOLO_NIGHT = 'solo_night', 'Solo Night Flight'
    # Checkride
    CHECKRIDE_RECOMMENDATION = 'checkride_recommendation', 'Checkride Recommendation'
    KNOWLEDGE_TEST = 'knowledge_test', 'Knowledge Test Endorsement'
    PRACTICAL_TEST = 'practical_test', 'Practical Test Endorsement'
    # Aircraft
    COMPLEX_AIRCRAFT = 'complex_aircraft', 'Complex Aircraft'
    HIGH_PERFORMANCE = 'high_performance', 'High Performance Aircraft'
    TAILWHEEL = 'tailwheel', 'Tailwheel Aircraft'
    PRESSURIZED = 'pressurized', 'Pressurized Aircraft'
    HIGH_ALTITUDE = 'high_altitude', 'High Altitude Operations'
    # Flight Conditions
    NIGHT_FLIGHT = 'night_flight', 'Night Flight'
    INSTRUMENT_FLIGHT = 'instrument_flight', 'Instrument Flight'
    IFR_CROSS_COUNTRY = 'ifr_cross_country', 'IFR Cross Country'
    # Other
    FLIGHT_REVIEW = 'flight_review', 'Flight Review'
    INSTRUMENT_PROFICIENCY = 'instrument_proficiency', 'Instrument Proficiency Check'
    TYPE_CHECKOUT = 'type_checkout', 'Aircraft Type Checkout'
    MOUNTAIN_FLYING = 'mountain_flying', 'Mountain Flying'
    AEROBATIC = 'aerobatic', 'Aerobatic Operations'


class EndorsementStatus(models.TextChoices):
    """Endorsement status choices."""
    ACTIVE = 'active', 'Active'
    EXPIRED = 'expired', 'Expired'
    REVOKED = 'revoked', 'Revoked'
    SUPERSEDED = 'superseded', 'Superseded'
    PENDING = 'pending', 'Pending Signature'


class Endorsement(models.Model):
    """
    Endorsement model.

    Stores instructor endorsements/sign-offs for students.
    Includes solo endorsements, checkride recommendations, and aircraft endorsements.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    organization_id = models.UUIDField(db_index=True)

    # Parties
    student_id = models.UUIDField(
        db_index=True,
        help_text='Student/pilot receiving endorsement'
    )
    student_name = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )
    instructor_id = models.UUIDField(
        db_index=True,
        help_text='Instructor giving endorsement'
    )
    instructor_name = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    # Endorsement Type
    endorsement_type = models.CharField(
        max_length=100,
        choices=EndorsementType.choices,
        db_index=True
    )
    endorsement_code = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text='FAA/EASA endorsement reference code'
    )

    # Description
    description = models.TextField(
        blank=True,
        null=True,
        help_text='Endorsement description/text'
    )
    endorsement_text = models.TextField(
        blank=True,
        null=True,
        help_text='Full regulatory endorsement wording'
    )

    # Scope
    aircraft_type = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text='Aircraft type/make-model'
    )
    aircraft_registration = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text='Specific aircraft registration'
    )
    aircraft_icao = models.CharField(
        max_length=10,
        blank=True,
        null=True
    )
    airports = ArrayField(
        models.CharField(max_length=10),
        default=list,
        blank=True,
        help_text='Authorized airports (for solo endorsements)'
    )
    area_description = models.TextField(
        blank=True,
        null=True,
        help_text='Geographic area description'
    )
    route = models.TextField(
        blank=True,
        null=True,
        help_text='Authorized route (for cross-country)'
    )

    # Validity
    issue_date = models.DateField()
    expiry_date = models.DateField(
        blank=True,
        null=True,
        db_index=True
    )
    is_permanent = models.BooleanField(
        default=False,
        help_text='Permanent endorsement (no expiry)'
    )
    validity_days = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text='Validity period in days (e.g., 90 for solo)'
    )

    # Conditions and Limitations
    conditions = ArrayField(
        models.CharField(max_length=255),
        default=list,
        blank=True,
        help_text='Conditions for endorsement'
    )
    limitations = models.TextField(
        blank=True,
        null=True,
        help_text='Specific limitations'
    )
    weather_minimums = models.JSONField(
        default=dict,
        blank=True,
        help_text='Weather minimums (visibility, ceiling, etc.)'
    )
    day_night_restriction = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        choices=[
            ('day_only', 'Day Only'),
            ('night_only', 'Night Only'),
            ('day_night', 'Day and Night'),
        ]
    )

    # Instructor Signature
    instructor_signature = models.JSONField(
        blank=True,
        null=True,
        help_text='Digital signature data'
    )
    signed_at = models.DateTimeField(
        blank=True,
        null=True
    )
    instructor_certificate_number = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text='CFI certificate number'
    )
    instructor_certificate_expiry = models.DateField(
        blank=True,
        null=True,
        help_text='CFI certificate expiry date'
    )

    # Status
    status = models.CharField(
        max_length=20,
        choices=EndorsementStatus.choices,
        default=EndorsementStatus.PENDING,
        db_index=True
    )

    # Related Records
    related_flight_id = models.UUIDField(
        blank=True,
        null=True,
        help_text='Related training flight'
    )
    related_lesson_id = models.UUIDField(
        blank=True,
        null=True,
        help_text='Related training lesson'
    )
    superseded_by_id = models.UUIDField(
        blank=True,
        null=True,
        help_text='Newer endorsement that supersedes this one'
    )

    # Notes
    notes = models.TextField(blank=True, null=True)

    # Metadata
    metadata = models.JSONField(default=dict, blank=True)

    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'endorsements'
        ordering = ['-issue_date']
        indexes = [
            models.Index(fields=['organization_id', 'student_id']),
            models.Index(fields=['organization_id', 'instructor_id']),
            models.Index(fields=['endorsement_type', 'status']),
            models.Index(fields=['expiry_date']),
        ]

    def __str__(self) -> str:
        return f"{self.get_endorsement_type_display()} - {self.student_name or self.student_id}"

    @property
    def is_valid(self) -> bool:
        """Check if endorsement is currently valid."""
        if self.status != EndorsementStatus.ACTIVE:
            return False
        if self.is_permanent:
            return True
        if self.expiry_date:
            return self.expiry_date >= date.today()
        return True

    @property
    def is_expired(self) -> bool:
        """Check if endorsement is expired."""
        if self.is_permanent:
            return False
        if not self.expiry_date:
            return False
        return self.expiry_date < date.today()

    @property
    def days_until_expiry(self) -> Optional[int]:
        """Calculate days until expiry."""
        if self.is_permanent or not self.expiry_date:
            return None
        return (self.expiry_date - date.today()).days

    @property
    def is_signed(self) -> bool:
        """Check if endorsement is signed."""
        return self.signed_at is not None

    def sign(
        self,
        instructor_id: uuid.UUID,
        signature_data: Dict[str, Any],
        certificate_number: str,
        certificate_expiry: date
    ) -> None:
        """Sign the endorsement."""
        if str(self.instructor_id) != str(instructor_id):
            raise ValueError('Only the assigned instructor can sign')

        self.instructor_signature = signature_data
        self.signed_at = timezone.now()
        self.instructor_certificate_number = certificate_number
        self.instructor_certificate_expiry = certificate_expiry
        self.status = EndorsementStatus.ACTIVE

        # Calculate expiry if validity days set
        if self.validity_days and not self.is_permanent:
            self.expiry_date = self.issue_date + timedelta(days=self.validity_days)

        self.save()

    def revoke(self, reason: str) -> None:
        """Revoke the endorsement."""
        self.status = EndorsementStatus.REVOKED
        self.notes = f"{self.notes or ''}\nRevoked: {reason}".strip()
        self.save()

    def supersede(self, new_endorsement_id: uuid.UUID) -> None:
        """Mark as superseded by newer endorsement."""
        self.status = EndorsementStatus.SUPERSEDED
        self.superseded_by_id = new_endorsement_id
        self.save()

    def update_status(self) -> None:
        """Update status based on current state."""
        if self.status in [EndorsementStatus.REVOKED, EndorsementStatus.SUPERSEDED]:
            return

        if self.is_expired:
            self.status = EndorsementStatus.EXPIRED
            self.save(update_fields=['status', 'updated_at'])

    def get_validity_info(self) -> Dict[str, Any]:
        """Get detailed validity information."""
        return {
            'endorsement_id': str(self.id),
            'endorsement_type': self.endorsement_type,
            'status': self.status,
            'is_valid': self.is_valid,
            'is_signed': self.is_signed,
            'is_permanent': self.is_permanent,
            'is_expired': self.is_expired,
            'issue_date': self.issue_date.isoformat(),
            'expiry_date': self.expiry_date.isoformat() if self.expiry_date else None,
            'days_until_expiry': self.days_until_expiry,
            'aircraft_type': self.aircraft_type,
            'aircraft_registration': self.aircraft_registration,
            'airports': self.airports,
            'conditions': self.conditions,
            'limitations': self.limitations,
            'instructor_name': self.instructor_name,
            'instructor_certificate_number': self.instructor_certificate_number,
        }

    @classmethod
    def get_required_endorsements_for_solo(cls) -> List[str]:
        """Get list of endorsement types required for solo flight."""
        return [
            EndorsementType.SOLO_FLIGHT,
        ]

    @classmethod
    def get_required_endorsements_for_checkride(cls, license_type: str) -> List[str]:
        """Get list of endorsement types required for checkride."""
        return [
            EndorsementType.KNOWLEDGE_TEST,
            EndorsementType.PRACTICAL_TEST,
            EndorsementType.CHECKRIDE_RECOMMENDATION,
        ]

    @classmethod
    def generate_endorsement_text(
        cls,
        endorsement_type: str,
        student_name: str,
        **kwargs
    ) -> str:
        """Generate standard endorsement text based on type."""
        templates = {
            EndorsementType.SOLO_FLIGHT: (
                f"I certify that {student_name} has received the training required by "
                f"14 CFR 61.87 and has been found proficient to make solo flights in a "
                f"{{aircraft_type}}. This endorsement is valid for {{validity_days}} days."
            ),
            EndorsementType.SOLO_CROSS_COUNTRY: (
                f"I certify that {student_name} has received solo cross-country training "
                f"as required by 14 CFR 61.93 and is competent to make solo cross-country "
                f"flights. Route: {{route}}"
            ),
            EndorsementType.CHECKRIDE_RECOMMENDATION: (
                f"I certify that {student_name} has received and logged the required "
                f"training time and is prepared for the {{license_type}} practical test."
            ),
            EndorsementType.FLIGHT_REVIEW: (
                f"I certify that {student_name} has satisfactorily completed a flight "
                f"review of 14 CFR 61.56(a) on {{date}}."
            ),
        }

        template = templates.get(endorsement_type, '')
        return template.format(**kwargs) if template else ''
