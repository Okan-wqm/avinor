# services/aircraft-service/src/apps/core/models/aircraft.py
"""
Aircraft Model

Core model for aircraft fleet management.
"""

import uuid
from decimal import Decimal
from datetime import date
from typing import Optional, Dict, Any

from django.db import models
from django.utils import timezone


class Aircraft(models.Model):
    """
    Aircraft model representing individual aircraft in the fleet.

    Supports:
    - Multi-tenant isolation via organization_id
    - Comprehensive technical specifications
    - Counter/time tracking (hobbs, tach, total time)
    - Operational status management
    - Squawk tracking integration
    - Pricing configuration
    - Document references
    """

    # ==========================================================================
    # Enums
    # ==========================================================================

    class Category(models.TextChoices):
        AIRPLANE = 'airplane', 'Airplane'
        HELICOPTER = 'helicopter', 'Helicopter'
        GLIDER = 'glider', 'Glider'
        BALLOON = 'balloon', 'Balloon'
        POWERED_LIFT = 'powered_lift', 'Powered Lift'

    class Status(models.TextChoices):
        ACTIVE = 'active', 'Active'
        MAINTENANCE = 'maintenance', 'In Maintenance'
        GROUNDED = 'grounded', 'Grounded'
        SOLD = 'sold', 'Sold'
        RETIRED = 'retired', 'Retired'
        STORAGE = 'storage', 'In Storage'

    class OperationalStatus(models.TextChoices):
        AVAILABLE = 'available', 'Available'
        IN_USE = 'in_use', 'In Use'
        RESERVED = 'reserved', 'Reserved'
        UNAVAILABLE = 'unavailable', 'Unavailable'

    class EngineType(models.TextChoices):
        PISTON = 'piston', 'Piston'
        TURBOPROP = 'turboprop', 'Turboprop'
        TURBOJET = 'turbojet', 'Turbojet'
        TURBOFAN = 'turbofan', 'Turbofan'
        ELECTRIC = 'electric', 'Electric'

    class FuelType(models.TextChoices):
        AVGAS_100LL = 'avgas_100ll', 'AVGAS 100LL'
        AVGAS_100 = 'avgas_100', 'AVGAS 100'
        JET_A = 'jet_a', 'Jet A'
        JET_A1 = 'jet_a1', 'Jet A-1'
        MOGAS = 'mogas', 'MOGAS'

    class BillingTimeSource(models.TextChoices):
        HOBBS = 'hobbs', 'Hobbs Time'
        TACH = 'tach', 'Tach Time'
        BLOCK = 'block', 'Block Time'
        AIRBORNE = 'airborne', 'Airborne Time'

    class AirworthinessCertType(models.TextChoices):
        STANDARD = 'standard', 'Standard'
        RESTRICTED = 'restricted', 'Restricted'
        EXPERIMENTAL = 'experimental', 'Experimental'
        SPECIAL = 'special', 'Special'

    # ==========================================================================
    # Primary Key and Multi-Tenant
    # ==========================================================================

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    organization_id = models.UUIDField(
        db_index=True,
        help_text='Organization that owns this aircraft'
    )

    # ==========================================================================
    # Identification
    # ==========================================================================

    registration = models.CharField(
        max_length=20,
        help_text='Aircraft registration (e.g., TC-ABC, N12345)'
    )
    serial_number = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text='Manufacturer serial number'
    )

    # ==========================================================================
    # Type Information
    # ==========================================================================

    aircraft_type = models.ForeignKey(
        'AircraftType',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='aircraft'
    )
    manufacturer = models.CharField(max_length=100, blank=True, null=True)
    model = models.CharField(max_length=100, blank=True, null=True)
    variant = models.CharField(max_length=100, blank=True, null=True)
    year_manufactured = models.IntegerField(blank=True, null=True)

    # ==========================================================================
    # Classification
    # ==========================================================================

    category = models.CharField(
        max_length=50,
        choices=Category.choices,
        default=Category.AIRPLANE
    )
    aircraft_class = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text='single_engine_land, multi_engine_land, etc.'
    )

    # ==========================================================================
    # Aircraft Characteristics
    # ==========================================================================

    is_complex = models.BooleanField(
        default=False,
        help_text='Has retractable gear, constant-speed prop, and flaps'
    )
    is_high_performance = models.BooleanField(
        default=False,
        help_text='Engine produces more than 200 HP'
    )
    is_tailwheel = models.BooleanField(default=False)
    is_pressurized = models.BooleanField(default=False)
    is_turbine = models.BooleanField(default=False)
    is_jet = models.BooleanField(default=False)
    is_aerobatic = models.BooleanField(default=False)

    # ==========================================================================
    # Engine Information
    # ==========================================================================

    engine_count = models.IntegerField(default=1)
    engine_type = models.CharField(
        max_length=50,
        choices=EngineType.choices,
        default=EngineType.PISTON
    )
    engine_manufacturer = models.CharField(max_length=100, blank=True, null=True)
    engine_model = models.CharField(max_length=100, blank=True, null=True)
    engine_power_hp = models.IntegerField(blank=True, null=True)

    # ==========================================================================
    # Technical Specifications
    # ==========================================================================

    mtow_kg = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        help_text='Maximum Takeoff Weight in kg'
    )
    empty_weight_kg = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True
    )
    useful_load_kg = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True
    )
    max_fuel_kg = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True
    )
    fuel_capacity_liters = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True
    )
    fuel_type = models.CharField(
        max_length=50,
        choices=FuelType.choices,
        default=FuelType.AVGAS_100LL
    )
    oil_capacity_liters = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True
    )

    # ==========================================================================
    # Capacity
    # ==========================================================================

    seat_count = models.IntegerField(default=4)
    passenger_count = models.IntegerField(
        default=3,
        help_text='Maximum passengers (excluding pilot)'
    )
    baggage_capacity_kg = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True
    )

    # ==========================================================================
    # Performance
    # ==========================================================================

    cruise_speed_kts = models.IntegerField(blank=True, null=True)
    max_speed_kts = models.IntegerField(blank=True, null=True)
    never_exceed_kts = models.IntegerField(
        blank=True,
        null=True,
        help_text='VNE'
    )
    stall_speed_kts = models.IntegerField(
        blank=True,
        null=True,
        help_text='VS0 in landing configuration'
    )
    best_climb_kts = models.IntegerField(
        blank=True,
        null=True,
        help_text='VY'
    )
    best_glide_kts = models.IntegerField(blank=True, null=True)
    range_nm = models.IntegerField(blank=True, null=True)
    endurance_hours = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        blank=True,
        null=True
    )
    service_ceiling_ft = models.IntegerField(blank=True, null=True)
    rate_of_climb_fpm = models.IntegerField(blank=True, null=True)
    fuel_consumption_lph = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        blank=True,
        null=True,
        help_text='Liters per hour at cruise'
    )

    # ==========================================================================
    # Avionics
    # ==========================================================================

    avionics_type = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text='steam_gauges, glass_cockpit, g1000, g3x, avidyne'
    )
    gps_type = models.CharField(max_length=100, blank=True, null=True)
    autopilot_type = models.CharField(max_length=100, blank=True, null=True)
    ifr_certified = models.BooleanField(default=False)
    ifr_equipped = models.BooleanField(default=False)
    gps_equipped = models.BooleanField(default=False)
    autopilot_equipped = models.BooleanField(default=False)
    adsb_out = models.BooleanField(default=False)
    adsb_in = models.BooleanField(default=False)

    # ==========================================================================
    # Location
    # ==========================================================================

    home_base_id = models.UUIDField(
        blank=True,
        null=True,
        help_text='Reference to location in organization-service'
    )
    current_location_id = models.UUIDField(blank=True, null=True)
    current_airport_icao = models.CharField(max_length=4, blank=True, null=True)
    last_known_position = models.JSONField(
        default=dict,
        blank=True,
        help_text='{"latitude": 41.123, "longitude": 29.456, "updated_at": "..."}'
    )

    # ==========================================================================
    # Counters (Current Values)
    # ==========================================================================

    total_time_hours = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text='Total airframe time'
    )
    total_landings = models.IntegerField(default=0)
    total_cycles = models.IntegerField(default=0)

    # Hobbs & Tach
    hobbs_time = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    tach_time = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    hobbs_offset = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text='Offset to apply to hobbs readings'
    )

    # ==========================================================================
    # Operational Status
    # ==========================================================================

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE
    )
    operational_status = models.CharField(
        max_length=20,
        choices=OperationalStatus.choices,
        default=OperationalStatus.AVAILABLE
    )
    is_airworthy = models.BooleanField(default=True)
    grounded_reason = models.TextField(blank=True, null=True)
    grounded_at = models.DateTimeField(blank=True, null=True)
    grounded_by = models.UUIDField(blank=True, null=True)

    # ==========================================================================
    # Airworthiness Certificates
    # ==========================================================================

    airworthiness_cert_type = models.CharField(
        max_length=50,
        choices=AirworthinessCertType.choices,
        blank=True,
        null=True
    )
    airworthiness_cert_date = models.DateField(blank=True, null=True)
    arc_expiry_date = models.DateField(
        blank=True,
        null=True,
        help_text='Airworthiness Review Certificate expiry'
    )

    # ==========================================================================
    # Squawk Tracking
    # ==========================================================================

    has_open_squawks = models.BooleanField(default=False)
    has_grounding_squawks = models.BooleanField(default=False)
    open_squawk_count = models.IntegerField(default=0)

    # ==========================================================================
    # Pricing
    # ==========================================================================

    hourly_rate_dry = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        help_text='Hourly rate without fuel'
    )
    hourly_rate_wet = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        help_text='Hourly rate including fuel'
    )
    block_rate = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True
    )
    daily_rate = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True
    )
    daily_minimum_hours = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True,
        help_text='Minimum billable hours per day'
    )
    billing_time_source = models.CharField(
        max_length=20,
        choices=BillingTimeSource.choices,
        default=BillingTimeSource.HOBBS
    )

    # ==========================================================================
    # Insurance
    # ==========================================================================

    insurance_policy_number = models.CharField(max_length=100, blank=True, null=True)
    insurance_provider = models.CharField(max_length=255, blank=True, null=True)
    insurance_expiry_date = models.DateField(blank=True, null=True)
    hull_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        blank=True,
        null=True
    )
    liability_coverage = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        blank=True,
        null=True
    )

    # ==========================================================================
    # Tracking
    # ==========================================================================

    tracking_device_id = models.CharField(max_length=100, blank=True, null=True)
    tracking_provider = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text='spidertracks, flightradar24, adsb'
    )

    # ==========================================================================
    # Document URLs
    # ==========================================================================

    registration_doc_url = models.URLField(max_length=500, blank=True, null=True)
    airworthiness_cert_url = models.URLField(max_length=500, blank=True, null=True)
    insurance_cert_url = models.URLField(max_length=500, blank=True, null=True)
    weight_balance_url = models.URLField(max_length=500, blank=True, null=True)
    poh_url = models.URLField(max_length=500, blank=True, null=True)
    checklist_url = models.URLField(max_length=500, blank=True, null=True)

    # ==========================================================================
    # Visuals
    # ==========================================================================

    photo_url = models.URLField(max_length=500, blank=True, null=True)
    thumbnail_url = models.URLField(max_length=500, blank=True, null=True)
    gallery = models.JSONField(default=list, blank=True)

    # ==========================================================================
    # Notes
    # ==========================================================================

    notes = models.TextField(
        blank=True,
        null=True,
        help_text='General notes'
    )
    pilot_notes = models.TextField(
        blank=True,
        null=True,
        help_text='Notes visible to pilots'
    )
    internal_notes = models.TextField(
        blank=True,
        null=True,
        help_text='Internal/admin notes only'
    )

    # ==========================================================================
    # Metadata
    # ==========================================================================

    metadata = models.JSONField(default=dict, blank=True)
    display_order = models.IntegerField(default=0)

    # ==========================================================================
    # Audit Fields
    # ==========================================================================

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.UUIDField(blank=True, null=True)
    updated_by = models.UUIDField(blank=True, null=True)
    deleted_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = 'aircraft'
        ordering = ['display_order', 'registration']
        verbose_name = 'Aircraft'
        verbose_name_plural = 'Aircraft'
        constraints = [
            models.UniqueConstraint(
                fields=['organization_id', 'registration'],
                condition=models.Q(deleted_at__isnull=True),
                name='unique_org_registration'
            )
        ]
        indexes = [
            models.Index(fields=['organization_id']),
            models.Index(fields=['registration']),
            models.Index(fields=['status']),
            models.Index(fields=['aircraft_type']),
            models.Index(fields=['home_base_id']),
            models.Index(fields=['current_location_id']),
            models.Index(fields=['is_airworthy']),
            models.Index(fields=['has_open_squawks']),
        ]

    def __str__(self):
        model_info = self.model or 'Unknown'
        return f"{self.registration} ({model_info})"

    # ==========================================================================
    # Properties
    # ==========================================================================

    @property
    def display_name(self) -> str:
        """Get formatted display name."""
        if self.model:
            return f"{self.registration} - {self.model}"
        return self.registration

    @property
    def is_available(self) -> bool:
        """Check if aircraft is available for booking."""
        return (
            self.status == self.Status.ACTIVE and
            self.operational_status == self.OperationalStatus.AVAILABLE and
            self.is_airworthy and
            not self.has_grounding_squawks
        )

    @property
    def is_multi_engine(self) -> bool:
        """Check if aircraft is multi-engine."""
        return self.engine_count > 1

    @property
    def arc_days_remaining(self) -> Optional[int]:
        """Days until ARC expires."""
        if not self.arc_expiry_date:
            return None
        delta = self.arc_expiry_date - date.today()
        return delta.days

    @property
    def insurance_days_remaining(self) -> Optional[int]:
        """Days until insurance expires."""
        if not self.insurance_expiry_date:
            return None
        delta = self.insurance_expiry_date - date.today()
        return delta.days

    @property
    def is_arc_expired(self) -> bool:
        """Check if ARC is expired."""
        if not self.arc_expiry_date:
            return False
        return self.arc_expiry_date < date.today()

    @property
    def is_insurance_expired(self) -> bool:
        """Check if insurance is expired."""
        if not self.insurance_expiry_date:
            return False
        return self.insurance_expiry_date < date.today()

    # ==========================================================================
    # Methods
    # ==========================================================================

    def ground(self, reason: str, grounded_by: uuid.UUID) -> None:
        """Ground the aircraft."""
        self.is_airworthy = False
        self.grounded_reason = reason
        self.grounded_at = timezone.now()
        self.grounded_by = grounded_by
        self.status = self.Status.GROUNDED
        self.operational_status = self.OperationalStatus.UNAVAILABLE
        self.save(update_fields=[
            'is_airworthy', 'grounded_reason', 'grounded_at',
            'grounded_by', 'status', 'operational_status', 'updated_at'
        ])

    def unground(self) -> None:
        """Remove ground status."""
        self.is_airworthy = True
        self.grounded_reason = None
        self.grounded_at = None
        self.grounded_by = None
        self.status = self.Status.ACTIVE
        self.operational_status = self.OperationalStatus.AVAILABLE
        self.save(update_fields=[
            'is_airworthy', 'grounded_reason', 'grounded_at',
            'grounded_by', 'status', 'operational_status', 'updated_at'
        ])

    def update_counters(
        self,
        hobbs_change: Decimal = Decimal('0'),
        tach_change: Decimal = Decimal('0'),
        landings: int = 0,
        cycles: int = 0
    ) -> None:
        """Update aircraft counters."""
        if hobbs_change:
            self.hobbs_time += hobbs_change
            self.total_time_hours += hobbs_change
        if tach_change:
            self.tach_time += tach_change
        self.total_landings += landings
        self.total_cycles += cycles
        self.save(update_fields=[
            'hobbs_time', 'tach_time', 'total_time_hours',
            'total_landings', 'total_cycles', 'updated_at'
        ])

    def update_squawk_status(self) -> None:
        """Update squawk tracking fields based on current squawks."""
        from apps.core.models import AircraftSquawk

        open_squawks = AircraftSquawk.objects.filter(
            aircraft=self,
            status__in=[
                AircraftSquawk.Status.OPEN,
                AircraftSquawk.Status.IN_PROGRESS,
                AircraftSquawk.Status.DEFERRED
            ]
        )

        self.open_squawk_count = open_squawks.count()
        self.has_open_squawks = self.open_squawk_count > 0
        self.has_grounding_squawks = open_squawks.filter(is_grounding=True).exists()

        # Auto-ground if grounding squawk exists
        if self.has_grounding_squawks and self.is_airworthy:
            self.is_airworthy = False
            self.status = self.Status.GROUNDED
            self.operational_status = self.OperationalStatus.UNAVAILABLE

        self.save(update_fields=[
            'open_squawk_count', 'has_open_squawks', 'has_grounding_squawks',
            'is_airworthy', 'status', 'operational_status', 'updated_at'
        ])

    def soft_delete(self) -> None:
        """Soft delete the aircraft."""
        self.deleted_at = timezone.now()
        self.status = self.Status.RETIRED
        self.save(update_fields=['deleted_at', 'status', 'updated_at'])

    def get_billing_rate(self, rate_type: str = 'wet') -> Optional[Decimal]:
        """Get applicable hourly rate."""
        if rate_type == 'dry':
            return self.hourly_rate_dry
        elif rate_type == 'wet':
            return self.hourly_rate_wet
        elif rate_type == 'block':
            return self.block_rate
        elif rate_type == 'daily':
            return self.daily_rate
        return self.hourly_rate_wet

    def to_summary_dict(self) -> Dict[str, Any]:
        """Return summary dictionary for API responses."""
        return {
            'id': str(self.id),
            'registration': self.registration,
            'model': self.model,
            'manufacturer': self.manufacturer,
            'category': self.category,
            'status': self.status,
            'operational_status': self.operational_status,
            'is_airworthy': self.is_airworthy,
            'is_available': self.is_available,
            'total_time_hours': float(self.total_time_hours),
            'photo_url': self.photo_url,
        }
