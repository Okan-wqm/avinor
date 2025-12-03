# services/flight-service/src/apps/core/models/flight_crew_log.py
"""
Flight Crew Log Model

Individual logbook entries for each crew member on a flight.
"""

import uuid
from decimal import Decimal
from typing import Dict, Any

from django.db import models
from django.utils import timezone


class FlightCrewLog(models.Model):
    """
    Individual crew member's log entry for a flight.

    Each person on a flight (PIC, SIC, instructor, student, examiner)
    gets their own log entry with their specific times and roles.
    """

    class Role(models.TextChoices):
        PIC = 'pic', 'Pilot in Command'
        SIC = 'sic', 'Second in Command'
        INSTRUCTOR = 'instructor', 'Flight Instructor'
        STUDENT = 'student', 'Student Pilot'
        EXAMINER = 'examiner', 'Designated Examiner'
        SAFETY_PILOT = 'safety_pilot', 'Safety Pilot'
        OBSERVER = 'observer', 'Observer'

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    flight_id = models.UUIDField(db_index=True)
    organization_id = models.UUIDField(db_index=True)

    # ==========================================================================
    # User and Role
    # ==========================================================================
    user_id = models.UUIDField(db_index=True)
    role = models.CharField(
        max_length=50,
        choices=Role.choices
    )

    # ==========================================================================
    # Times for this person (decimal hours)
    # ==========================================================================
    flight_time = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Total flight time for this crew member"
    )
    time_pic = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00')
    )
    time_sic = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00')
    )
    time_dual_received = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00')
    )
    time_dual_given = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00')
    )
    time_solo = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00')
    )

    # ==========================================================================
    # Condition Times
    # ==========================================================================
    time_day = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00')
    )
    time_night = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00')
    )
    time_ifr = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00')
    )
    time_actual_instrument = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00')
    )
    time_simulated_instrument = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00')
    )
    time_cross_country = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00')
    )

    # ==========================================================================
    # Landings
    # ==========================================================================
    landings_day = models.PositiveIntegerField(default=0)
    landings_night = models.PositiveIntegerField(default=0)
    full_stop_day = models.PositiveIntegerField(default=0)
    full_stop_night = models.PositiveIntegerField(default=0)

    # ==========================================================================
    # Approaches
    # ==========================================================================
    approaches = models.PositiveIntegerField(
        default=0,
        help_text="Number of approaches for this crew member"
    )
    holds = models.PositiveIntegerField(default=0)

    # ==========================================================================
    # Signature
    # ==========================================================================
    signature = models.JSONField(
        blank=True,
        null=True,
        help_text="Signature data for this crew member"
    )
    signed_at = models.DateTimeField(blank=True, null=True)

    # ==========================================================================
    # Remarks
    # ==========================================================================
    remarks = models.TextField(
        blank=True,
        null=True,
        help_text="Personal remarks for this crew member"
    )

    # ==========================================================================
    # Endorsements (for students)
    # ==========================================================================
    endorsements = models.JSONField(
        default=list,
        help_text="Endorsements given/received during this flight"
    )

    # ==========================================================================
    # Training Items (for students)
    # ==========================================================================
    training_items = models.JSONField(
        default=list,
        help_text="Training items completed during this flight"
    )
    training_grade = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="Overall training grade if applicable"
    )

    # ==========================================================================
    # Timestamps
    # ==========================================================================
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'flight_crew_log'
        ordering = ['flight_id', 'role']
        indexes = [
            models.Index(fields=['flight_id']),
            models.Index(fields=['user_id', 'created_at']),
            models.Index(fields=['organization_id', 'user_id']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['flight_id', 'user_id', 'role'],
                name='unique_crew_log_per_flight'
            )
        ]

    def __str__(self):
        return f"{self.role} log for flight {self.flight_id}"

    # ==========================================================================
    # Properties
    # ==========================================================================

    @property
    def total_landings(self) -> int:
        """Total landings for this crew member."""
        return self.landings_day + self.landings_night

    @property
    def total_instrument_time(self) -> Decimal:
        """Total instrument time."""
        return self.time_actual_instrument + self.time_simulated_instrument

    @property
    def is_signed(self) -> bool:
        """Check if entry is signed."""
        return self.signed_at is not None

    # ==========================================================================
    # Methods
    # ==========================================================================

    def sign(self, signature_data: dict):
        """Sign this crew log entry."""
        self.signature = {
            'data': signature_data,
            'timestamp': timezone.now().isoformat(),
        }
        self.signed_at = timezone.now()
        self.save()

    def to_logbook_entry(self, flight_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert to logbook entry format."""
        return {
            'flight_id': str(self.flight_id),
            'date': flight_data.get('flight_date'),
            'aircraft': flight_data.get('aircraft_registration'),
            'aircraft_type': flight_data.get('aircraft_type'),
            'departure': flight_data.get('departure_airport'),
            'arrival': flight_data.get('arrival_airport'),
            'route': flight_data.get('route'),
            'role': self.role,
            'flight_time': float(self.flight_time) if self.flight_time else 0,
            'time_pic': float(self.time_pic),
            'time_sic': float(self.time_sic),
            'time_dual_received': float(self.time_dual_received),
            'time_dual_given': float(self.time_dual_given),
            'time_solo': float(self.time_solo),
            'time_day': float(self.time_day),
            'time_night': float(self.time_night),
            'time_ifr': float(self.time_ifr),
            'time_actual_instrument': float(self.time_actual_instrument),
            'time_simulated_instrument': float(self.time_simulated_instrument),
            'time_cross_country': float(self.time_cross_country),
            'landings_day': self.landings_day,
            'landings_night': self.landings_night,
            'approaches': self.approaches,
            'holds': self.holds,
            'remarks': self.remarks,
            'signed': self.is_signed,
            'signed_at': self.signed_at.isoformat() if self.signed_at else None,
        }

    @classmethod
    def create_from_flight(
        cls,
        flight,
        user_id: uuid.UUID,
        role: str,
        **kwargs
    ) -> 'FlightCrewLog':
        """Create a crew log entry from a flight."""
        return cls.objects.create(
            flight_id=flight.id,
            organization_id=flight.organization_id,
            user_id=user_id,
            role=role,
            flight_time=flight.flight_time,
            time_day=flight.time_day,
            time_night=flight.time_night,
            time_ifr=flight.time_ifr,
            time_actual_instrument=flight.time_actual_instrument,
            time_simulated_instrument=flight.time_simulated_instrument,
            time_cross_country=flight.time_cross_country,
            landings_day=flight.landings_day if role in ['pic', 'student'] else 0,
            landings_night=flight.landings_night if role in ['pic', 'student'] else 0,
            full_stop_day=flight.full_stop_day if role in ['pic', 'student'] else 0,
            full_stop_night=flight.full_stop_night if role in ['pic', 'student'] else 0,
            approaches=flight.approach_count if role in ['pic', 'student', 'sic'] else 0,
            holds=flight.holds if role in ['pic', 'student', 'sic'] else 0,
            **kwargs
        )
