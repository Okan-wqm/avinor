# services/flight-service/src/apps/core/models/flight.py
"""
Flight Model

Core model for flight records / logbook entries.
"""

import uuid
from decimal import Decimal
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any

from django.db import models
from django.db.models import Q, Sum, Count
from django.contrib.postgres.fields import ArrayField
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator


class Flight(models.Model):
    """
    Flight record model for pilot logbook.

    Tracks all aspects of a flight including:
    - Times (block, flight, hobbs, tach)
    - Landings and approaches
    - Pilot function times (PIC, SIC, dual, solo)
    - Weather conditions
    - Training information
    - Billing and charges
    """

    class FlightType(models.TextChoices):
        TRAINING = 'training', 'Training'
        SOLO = 'solo', 'Solo'
        RENTAL = 'rental', 'Rental'
        CHARTER = 'charter', 'Charter'
        CHECK_RIDE = 'check_ride', 'Check Ride'
        PROFICIENCY = 'proficiency', 'Proficiency'
        FERRY = 'ferry', 'Ferry'
        MAINTENANCE = 'maintenance', 'Maintenance'

    class FlightRules(models.TextChoices):
        VFR = 'VFR', 'VFR'
        IFR = 'IFR', 'IFR'
        SVFR = 'SVFR', 'Special VFR'

    class FlightCategory(models.TextChoices):
        LOCAL = 'local', 'Local'
        CROSS_COUNTRY = 'cross_country', 'Cross Country'
        NIGHT = 'night', 'Night'
        INSTRUMENT = 'instrument', 'Instrument'

    class TrainingType(models.TextChoices):
        DUAL = 'dual', 'Dual Instruction'
        SOLO = 'solo', 'Solo'
        SUPERVISED_SOLO = 'supervised_solo', 'Supervised Solo'
        STAGE_CHECK = 'stage_check', 'Stage Check'
        CHECK_RIDE = 'check_ride', 'Check Ride'

    class WeatherConditions(models.TextChoices):
        VMC = 'VMC', 'Visual Meteorological Conditions'
        IMC = 'IMC', 'Instrument Meteorological Conditions'

    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        SUBMITTED = 'submitted', 'Submitted'
        PENDING_REVIEW = 'pending_review', 'Pending Review'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'
        CANCELLED = 'cancelled', 'Cancelled'

    class BillingStatus(models.TextChoices):
        PENDING = 'pending', 'Pending'
        CALCULATED = 'calculated', 'Calculated'
        INVOICED = 'invoiced', 'Invoiced'
        PAID = 'paid', 'Paid'
        WAIVED = 'waived', 'Waived'

    # ==========================================================================
    # Primary Keys and Relations
    # ==========================================================================
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    organization_id = models.UUIDField(db_index=True)
    booking_id = models.UUIDField(blank=True, null=True, db_index=True)
    aircraft_id = models.UUIDField(db_index=True)

    # ==========================================================================
    # Personnel
    # ==========================================================================
    pic_id = models.UUIDField(
        db_index=True,
        help_text="Pilot in Command"
    )
    sic_id = models.UUIDField(
        blank=True,
        null=True,
        help_text="Second in Command"
    )
    instructor_id = models.UUIDField(
        blank=True,
        null=True,
        db_index=True,
        help_text="Flight Instructor"
    )
    student_id = models.UUIDField(
        blank=True,
        null=True,
        db_index=True,
        help_text="Student Pilot"
    )
    examiner_id = models.UUIDField(
        blank=True,
        null=True,
        help_text="Designated Examiner for check rides"
    )

    # Additional crew/passengers
    crew_members = models.JSONField(
        default=list,
        help_text="Additional crew members"
    )
    passengers = models.JSONField(
        default=list,
        help_text="Passenger list"
    )
    pax_count = models.PositiveIntegerField(default=0)

    # ==========================================================================
    # Flight Date and Route
    # ==========================================================================
    flight_date = models.DateField(db_index=True)

    departure_airport = models.CharField(
        max_length=4,
        help_text="ICAO code"
    )
    arrival_airport = models.CharField(
        max_length=4,
        help_text="ICAO code"
    )
    route = models.TextField(
        blank=True,
        null=True,
        help_text="Route description"
    )
    waypoints = models.JSONField(
        default=list,
        help_text="Route waypoints with details"
    )
    via_airports = ArrayField(
        models.CharField(max_length=4),
        default=list,
        blank=True,
        help_text="Intermediate stops"
    )

    # ==========================================================================
    # Times
    # ==========================================================================
    block_off = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Engine start / parking brake release"
    )
    takeoff_time = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Wheels up"
    )
    landing_time = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Wheels down"
    )
    block_on = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Engine shutdown / parking brake set"
    )

    # Calculated durations (in decimal hours)
    block_time = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Block to block time in hours"
    )
    flight_time = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Total flight time in hours"
    )
    air_time = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Takeoff to landing time"
    )

    # ==========================================================================
    # Hobbs and Tach
    # ==========================================================================
    hobbs_start = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True
    )
    hobbs_end = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True
    )
    hobbs_time = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True
    )
    tach_start = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True
    )
    tach_end = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True
    )
    tach_time = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True
    )

    # ==========================================================================
    # Landings
    # ==========================================================================
    landings_day = models.PositiveIntegerField(default=0)
    landings_night = models.PositiveIntegerField(default=0)
    full_stop_day = models.PositiveIntegerField(default=0)
    full_stop_night = models.PositiveIntegerField(default=0)
    touch_and_go = models.PositiveIntegerField(default=0)

    # ==========================================================================
    # Flight Time Categories (decimal hours)
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
        default=Decimal('0.00'),
        help_text="IFR flight time"
    )
    time_actual_instrument = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Actual IMC time"
    )
    time_simulated_instrument = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Hood/foggles time"
    )
    time_cross_country = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00')
    )

    # ==========================================================================
    # Pilot Function Time (decimal hours)
    # ==========================================================================
    time_pic = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Pilot in Command time"
    )
    time_sic = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Second in Command time"
    )
    time_dual_received = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Dual instruction received"
    )
    time_dual_given = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Dual instruction given"
    )
    time_solo = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00')
    )
    time_simulated_flight = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="FTD/FSTD time"
    )

    # ==========================================================================
    # Approaches and Holds
    # ==========================================================================
    approaches = models.JSONField(
        default=list,
        help_text="Approach details: [{type, airport, runway, count}]"
    )
    approach_count = models.PositiveIntegerField(default=0)
    holds = models.PositiveIntegerField(default=0)

    # ==========================================================================
    # Distance
    # ==========================================================================
    distance_nm = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Distance in nautical miles"
    )

    # ==========================================================================
    # Fuel and Oil
    # ==========================================================================
    fuel_start_liters = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        blank=True,
        null=True
    )
    fuel_end_liters = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        blank=True,
        null=True
    )
    fuel_used_liters = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        blank=True,
        null=True
    )
    fuel_added_liters = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        blank=True,
        null=True
    )
    fuel_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True
    )
    oil_added_liters = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True
    )

    # ==========================================================================
    # Flight Type and Classification
    # ==========================================================================
    flight_type = models.CharField(
        max_length=50,
        choices=FlightType.choices,
        default=FlightType.TRAINING
    )
    flight_rules = models.CharField(
        max_length=10,
        choices=FlightRules.choices,
        default=FlightRules.VFR
    )
    flight_category = models.CharField(
        max_length=50,
        choices=FlightCategory.choices,
        blank=True,
        null=True
    )

    # ==========================================================================
    # Training
    # ==========================================================================
    training_type = models.CharField(
        max_length=50,
        choices=TrainingType.choices,
        blank=True,
        null=True
    )
    lesson_id = models.UUIDField(blank=True, null=True)
    exercises_completed = models.JSONField(
        default=list,
        help_text="List of completed exercise IDs"
    )
    lesson_completed = models.BooleanField(default=False)

    # ==========================================================================
    # Weather
    # ==========================================================================
    weather_conditions = models.CharField(
        max_length=20,
        choices=WeatherConditions.choices,
        blank=True,
        null=True
    )
    weather_briefing = models.TextField(blank=True, null=True)
    metar_departure = models.TextField(blank=True, null=True)
    metar_arrival = models.TextField(blank=True, null=True)

    # ==========================================================================
    # Risk Assessment
    # ==========================================================================
    risk_assessment = models.JSONField(
        default=dict,
        blank=True
    )
    risk_score = models.PositiveIntegerField(
        blank=True,
        null=True,
        validators=[MaxValueValidator(100)]
    )

    # ==========================================================================
    # Status and Approval
    # ==========================================================================
    flight_status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT
    )
    approval_status = models.CharField(
        max_length=20,
        default='pending'
    )
    approved_by = models.UUIDField(blank=True, null=True)
    approved_at = models.DateTimeField(blank=True, null=True)
    rejection_reason = models.TextField(blank=True, null=True)

    # ==========================================================================
    # Signatures
    # ==========================================================================
    pic_signature = models.JSONField(
        blank=True,
        null=True,
        help_text="PIC signature data"
    )
    pic_signed_at = models.DateTimeField(blank=True, null=True)
    instructor_signature = models.JSONField(
        blank=True,
        null=True,
        help_text="Instructor signature data"
    )
    instructor_signed_at = models.DateTimeField(blank=True, null=True)
    student_signature = models.JSONField(
        blank=True,
        null=True,
        help_text="Student signature data"
    )
    student_signed_at = models.DateTimeField(blank=True, null=True)

    # ==========================================================================
    # Billing
    # ==========================================================================
    is_billed = models.BooleanField(default=False)
    billing_status = models.CharField(
        max_length=20,
        choices=BillingStatus.choices,
        default=BillingStatus.PENDING
    )
    aircraft_charge = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True
    )
    instructor_charge = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True
    )
    fuel_charge = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True
    )
    other_charges = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True
    )
    total_charge = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True
    )
    transaction_id = models.UUIDField(blank=True, null=True)

    # ==========================================================================
    # Squawks / Discrepancies
    # ==========================================================================
    has_squawks = models.BooleanField(default=False)
    squawk_ids = ArrayField(
        models.UUIDField(),
        default=list,
        blank=True
    )

    # ==========================================================================
    # Documents
    # ==========================================================================
    documents = models.JSONField(
        default=list,
        help_text="Attached documents"
    )
    track_file_url = models.URLField(
        max_length=500,
        blank=True,
        null=True,
        help_text="GPS track file"
    )

    # ==========================================================================
    # Notes and Remarks
    # ==========================================================================
    pilot_remarks = models.TextField(
        blank=True,
        null=True,
        help_text="Pilot's remarks"
    )
    instructor_remarks = models.TextField(
        blank=True,
        null=True,
        help_text="Instructor's remarks/comments"
    )
    internal_notes = models.TextField(
        blank=True,
        null=True,
        help_text="Internal administrative notes"
    )

    # ==========================================================================
    # Metadata
    # ==========================================================================
    metadata = models.JSONField(default=dict, blank=True)

    # ==========================================================================
    # Audit
    # ==========================================================================
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.UUIDField()
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.UUIDField(blank=True, null=True)

    class Meta:
        db_table = 'flights'
        ordering = ['-flight_date', '-block_off']
        indexes = [
            models.Index(fields=['organization_id']),
            models.Index(fields=['flight_date']),
            models.Index(fields=['aircraft_id', 'flight_date']),
            models.Index(fields=['pic_id', 'flight_date']),
            models.Index(fields=['instructor_id', 'flight_date']),
            models.Index(fields=['student_id', 'flight_date']),
            models.Index(fields=['booking_id']),
            models.Index(fields=['flight_status']),
            models.Index(fields=['billing_status']),
        ]

    def __str__(self):
        return f"{self.flight_date} {self.departure_airport}-{self.arrival_airport}"

    # ==========================================================================
    # Properties
    # ==========================================================================

    @property
    def total_landings(self) -> int:
        """Total landings (day + night)."""
        return self.landings_day + self.landings_night

    @property
    def total_instrument_time(self) -> Decimal:
        """Total instrument time (actual + simulated)."""
        return (self.time_actual_instrument or Decimal('0')) + \
               (self.time_simulated_instrument or Decimal('0'))

    @property
    def duration_display(self) -> str:
        """Display flight time as HH:MM."""
        if self.flight_time:
            hours = int(self.flight_time)
            minutes = int((self.flight_time - hours) * 60)
            return f"{hours}:{minutes:02d}"
        return "0:00"

    @property
    def is_cross_country(self) -> bool:
        """Check if flight qualifies as cross-country."""
        return self.departure_airport != self.arrival_airport or \
               (self.distance_nm and self.distance_nm >= Decimal('50'))

    @property
    def can_edit(self) -> bool:
        """Check if flight can be edited."""
        return self.flight_status in [
            self.Status.DRAFT,
            self.Status.REJECTED
        ]

    @property
    def can_submit(self) -> bool:
        """Check if flight can be submitted for approval."""
        return self.flight_status == self.Status.DRAFT

    @property
    def can_approve(self) -> bool:
        """Check if flight can be approved."""
        return self.flight_status in [
            self.Status.SUBMITTED,
            self.Status.PENDING_REVIEW
        ]

    @property
    def requires_instructor_signature(self) -> bool:
        """Check if instructor signature is required."""
        return self.instructor_id is not None and \
               self.flight_type in [self.FlightType.TRAINING, self.FlightType.CHECK_RIDE]

    @property
    def all_signatures_complete(self) -> bool:
        """Check if all required signatures are complete."""
        if not self.pic_signed_at:
            return False
        if self.requires_instructor_signature and not self.instructor_signed_at:
            return False
        if self.student_id and not self.student_signed_at:
            return False
        return True

    # ==========================================================================
    # Methods
    # ==========================================================================

    def calculate_times(self):
        """Calculate all time values from timestamps."""
        # Block time
        if self.block_off and self.block_on:
            diff = (self.block_on - self.block_off).total_seconds() / 3600
            self.block_time = Decimal(str(round(diff, 2)))

        # Air time (wheels up to wheels down)
        if self.takeoff_time and self.landing_time:
            diff = (self.landing_time - self.takeoff_time).total_seconds() / 3600
            self.air_time = Decimal(str(round(diff, 2)))

        # Flight time (use air time or block time)
        if self.air_time:
            self.flight_time = self.air_time
        elif self.block_time:
            self.flight_time = self.block_time

        # Hobbs time
        if self.hobbs_start is not None and self.hobbs_end is not None:
            self.hobbs_time = self.hobbs_end - self.hobbs_start

        # Tach time
        if self.tach_start is not None and self.tach_end is not None:
            self.tach_time = self.tach_end - self.tach_start

        # Calculate approach count
        if self.approaches:
            self.approach_count = sum(
                a.get('count', 1) for a in self.approaches
            )

    def calculate_fuel_used(self):
        """Calculate fuel used from start/end readings."""
        if self.fuel_start_liters is not None and self.fuel_end_liters is not None:
            self.fuel_used_liters = self.fuel_start_liters - self.fuel_end_liters + \
                                    (self.fuel_added_liters or Decimal('0'))

    def validate_times(self) -> List[str]:
        """Validate flight times for consistency."""
        errors = []

        if self.block_off and self.block_on and self.block_on <= self.block_off:
            errors.append("Block on time must be after block off time")

        if self.takeoff_time and self.landing_time and self.landing_time <= self.takeoff_time:
            errors.append("Landing time must be after takeoff time")

        if self.block_off and self.takeoff_time and self.takeoff_time < self.block_off:
            errors.append("Takeoff time cannot be before block off time")

        if self.landing_time and self.block_on and self.landing_time > self.block_on:
            errors.append("Landing time cannot be after block on time")

        if self.hobbs_start is not None and self.hobbs_end is not None:
            if self.hobbs_end < self.hobbs_start:
                errors.append("Hobbs end must be greater than hobbs start")

        return errors

    def submit(self):
        """Submit flight for approval."""
        if not self.can_submit:
            raise ValueError("Flight cannot be submitted in current status")

        self.calculate_times()
        self.calculate_fuel_used()

        errors = self.validate_times()
        if errors:
            raise ValueError(f"Validation errors: {', '.join(errors)}")

        self.flight_status = self.Status.SUBMITTED
        self.save()

    def approve(self, approver_id: uuid.UUID):
        """Approve the flight."""
        if not self.can_approve:
            raise ValueError("Flight cannot be approved in current status")

        self.flight_status = self.Status.APPROVED
        self.approval_status = 'approved'
        self.approved_by = approver_id
        self.approved_at = timezone.now()
        self.save()

    def reject(self, reason: str):
        """Reject the flight."""
        if not self.can_approve:
            raise ValueError("Flight cannot be rejected in current status")

        self.flight_status = self.Status.REJECTED
        self.approval_status = 'rejected'
        self.rejection_reason = reason
        self.save()

    def sign(self, role: str, signature_data: dict, signer_id: uuid.UUID):
        """Sign the flight record."""
        signature = {
            'data': signature_data,
            'signer_id': str(signer_id),
            'timestamp': timezone.now().isoformat(),
        }

        if role == 'pic':
            self.pic_signature = signature
            self.pic_signed_at = timezone.now()
        elif role == 'instructor':
            self.instructor_signature = signature
            self.instructor_signed_at = timezone.now()
        elif role == 'student':
            self.student_signature = signature
            self.student_signed_at = timezone.now()
        else:
            raise ValueError(f"Invalid signature role: {role}")

        self.save()

    def add_squawk(self, squawk_id: uuid.UUID):
        """Add a squawk/discrepancy to this flight."""
        if squawk_id not in self.squawk_ids:
            self.squawk_ids.append(squawk_id)
            self.has_squawks = True
            self.save()

    def cancel(self, reason: str = None):
        """Cancel the flight."""
        if self.flight_status == self.Status.APPROVED:
            raise ValueError("Cannot cancel an approved flight")

        self.flight_status = self.Status.CANCELLED
        if reason:
            self.internal_notes = f"Cancelled: {reason}"
        self.save()

    # ==========================================================================
    # Class Methods
    # ==========================================================================

    @classmethod
    def get_pilot_flights(
        cls,
        organization_id: uuid.UUID,
        pilot_id: uuid.UUID,
        start_date: date = None,
        end_date: date = None,
        approved_only: bool = True
    ):
        """Get flights for a specific pilot."""
        queryset = cls.objects.filter(
            organization_id=organization_id
        ).filter(
            Q(pic_id=pilot_id) |
            Q(sic_id=pilot_id) |
            Q(student_id=pilot_id) |
            Q(instructor_id=pilot_id)
        )

        if approved_only:
            queryset = queryset.filter(flight_status=cls.Status.APPROVED)

        if start_date:
            queryset = queryset.filter(flight_date__gte=start_date)

        if end_date:
            queryset = queryset.filter(flight_date__lte=end_date)

        return queryset.order_by('-flight_date', '-block_off')

    @classmethod
    def get_aircraft_flights(
        cls,
        organization_id: uuid.UUID,
        aircraft_id: uuid.UUID,
        start_date: date = None,
        end_date: date = None
    ):
        """Get flights for a specific aircraft."""
        queryset = cls.objects.filter(
            organization_id=organization_id,
            aircraft_id=aircraft_id,
            flight_status=cls.Status.APPROVED
        )

        if start_date:
            queryset = queryset.filter(flight_date__gte=start_date)

        if end_date:
            queryset = queryset.filter(flight_date__lte=end_date)

        return queryset.order_by('-flight_date')

    @classmethod
    def get_pending_approval(cls, organization_id: uuid.UUID):
        """Get flights pending approval."""
        return cls.objects.filter(
            organization_id=organization_id,
            flight_status__in=[cls.Status.SUBMITTED, cls.Status.PENDING_REVIEW]
        ).order_by('-created_at')

    @classmethod
    def calculate_totals(
        cls,
        organization_id: uuid.UUID,
        pilot_id: uuid.UUID,
        start_date: date = None,
        end_date: date = None
    ) -> Dict[str, Any]:
        """Calculate total times for a pilot."""
        queryset = cls.objects.filter(
            organization_id=organization_id,
            flight_status=cls.Status.APPROVED
        ).filter(
            Q(pic_id=pilot_id) |
            Q(sic_id=pilot_id) |
            Q(student_id=pilot_id)
        )

        if start_date:
            queryset = queryset.filter(flight_date__gte=start_date)

        if end_date:
            queryset = queryset.filter(flight_date__lte=end_date)

        totals = queryset.aggregate(
            total_flight_time=Sum('flight_time'),
            total_pic=Sum('time_pic'),
            total_sic=Sum('time_sic'),
            total_dual_received=Sum('time_dual_received'),
            total_dual_given=Sum('time_dual_given'),
            total_solo=Sum('time_solo'),
            total_day=Sum('time_day'),
            total_night=Sum('time_night'),
            total_ifr=Sum('time_ifr'),
            total_cross_country=Sum('time_cross_country'),
            total_landings_day=Sum('landings_day'),
            total_landings_night=Sum('landings_night'),
            total_approaches=Sum('approach_count'),
            flight_count=Count('id'),
        )

        # Replace None with 0
        return {
            k: v or (0 if 'count' in k or 'landings' in k or 'approaches' in k else Decimal('0'))
            for k, v in totals.items()
        }
