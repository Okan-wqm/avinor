"""
Aircraft Service Models.
"""
import uuid
from decimal import Decimal
from django.db import models
from django.core.validators import MinValueValidator
from shared.common.mixins import UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin


class AircraftType(UUIDPrimaryKeyMixin, TimestampMixin, models.Model):
    """
    Aircraft type/model definition (e.g., Cessna 172, Piper PA-28).
    """
    class Category(models.TextChoices):
        SEP = 'SEP', 'Single Engine Piston'
        MEP = 'MEP', 'Multi Engine Piston'
        SET = 'SET', 'Single Engine Turbine'
        MET = 'MET', 'Multi Engine Turbine'
        HELICOPTER = 'HEL', 'Helicopter'
        GLIDER = 'GLI', 'Glider'
        BALLOON = 'BAL', 'Balloon'

    manufacturer = models.CharField(max_length=100)
    model = models.CharField(max_length=100)
    icao_designator = models.CharField(max_length=4, blank=True)
    category = models.CharField(max_length=3, choices=Category.choices, default=Category.SEP)

    # Performance specs
    max_takeoff_weight_kg = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    empty_weight_kg = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    fuel_capacity_liters = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    cruise_speed_kts = models.IntegerField(null=True, blank=True)
    max_speed_kts = models.IntegerField(null=True, blank=True)
    stall_speed_kts = models.IntegerField(null=True, blank=True)
    range_nm = models.IntegerField(null=True, blank=True)
    service_ceiling_ft = models.IntegerField(null=True, blank=True)
    rate_of_climb_fpm = models.IntegerField(null=True, blank=True)

    # Engine info
    engine_type = models.CharField(max_length=100, blank=True)
    engine_count = models.IntegerField(default=1)
    engine_power_hp = models.IntegerField(null=True, blank=True)

    # Dimensions
    wingspan_m = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    length_m = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    height_m = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    # Seating
    passenger_capacity = models.IntegerField(default=1)
    crew_required = models.IntegerField(default=1)

    # Training requirements
    requires_type_rating = models.BooleanField(default=False)
    requires_complex_endorsement = models.BooleanField(default=False)
    requires_high_performance_endorsement = models.BooleanField(default=False)

    # Status
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'aircraft_types'
        unique_together = ['manufacturer', 'model']
        ordering = ['manufacturer', 'model']

    def __str__(self):
        return f"{self.manufacturer} {self.model}"


class Aircraft(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, models.Model):
    """
    Individual aircraft in the fleet.
    """
    class Status(models.TextChoices):
        AVAILABLE = 'available', 'Available'
        IN_USE = 'in_use', 'In Use'
        MAINTENANCE = 'maintenance', 'In Maintenance'
        GROUNDED = 'grounded', 'Grounded'
        RESERVED = 'reserved', 'Reserved'

    aircraft_type = models.ForeignKey(
        AircraftType,
        on_delete=models.PROTECT,
        related_name='aircraft'
    )
    organization_id = models.UUIDField()  # Reference to Organization Service

    # Registration
    registration = models.CharField(max_length=10, unique=True)  # e.g., N12345, G-ABCD
    serial_number = models.CharField(max_length=50, blank=True)
    year_manufactured = models.IntegerField(null=True, blank=True)

    # Display
    name = models.CharField(max_length=100, blank=True)  # Nickname
    callsign = models.CharField(max_length=10, blank=True)

    # Current status
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.AVAILABLE)
    home_base_id = models.UUIDField(null=True, blank=True)  # Reference to Location

    # Hours tracking
    total_time_hours = models.DecimalField(max_digits=10, decimal_places=1, default=0)
    engine_hours = models.DecimalField(max_digits=10, decimal_places=1, default=0)
    cycles = models.IntegerField(default=0)  # Landings/takeoffs

    # Hobbs meter
    hobbs_time = models.DecimalField(max_digits=10, decimal_places=1, default=0)
    tach_time = models.DecimalField(max_digits=10, decimal_places=1, default=0)

    # Rates
    hourly_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    block_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Insurance
    insurance_policy_number = models.CharField(max_length=50, blank=True)
    insurance_expiry = models.DateField(null=True, blank=True)
    hull_value = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    # Equipment flags
    has_autopilot = models.BooleanField(default=False)
    has_gps = models.BooleanField(default=True)
    has_ifr_equipment = models.BooleanField(default=False)
    has_ads_b = models.BooleanField(default=False)
    has_tcas = models.BooleanField(default=False)

    # Fuel
    fuel_type = models.CharField(max_length=20, default='100LL')  # 100LL, JetA, etc.
    current_fuel_liters = models.DecimalField(max_digits=8, decimal_places=2, default=0)

    # Photos
    photo_url = models.URLField(blank=True)

    # Notes
    notes = models.TextField(blank=True)
    equipment_list = models.JSONField(default=list, blank=True)

    class Meta:
        db_table = 'aircraft'
        ordering = ['registration']
        indexes = [
            models.Index(fields=['registration']),
            models.Index(fields=['organization_id']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        name_part = f" ({self.name})" if self.name else ""
        return f"{self.registration}{name_part}"


class AircraftDocument(UUIDPrimaryKeyMixin, TimestampMixin, models.Model):
    """
    Documents associated with aircraft (certificates, manuals, etc.).
    """
    class DocumentType(models.TextChoices):
        AIRWORTHINESS = 'airworthiness', 'Certificate of Airworthiness'
        REGISTRATION = 'registration', 'Certificate of Registration'
        INSURANCE = 'insurance', 'Insurance Certificate'
        WEIGHT_BALANCE = 'weight_balance', 'Weight & Balance'
        POH = 'poh', 'Pilot Operating Handbook'
        CHECKLIST = 'checklist', 'Checklist'
        MEL = 'mel', 'Minimum Equipment List'
        MAINTENANCE_LOG = 'maintenance_log', 'Maintenance Log'
        OTHER = 'other', 'Other'

    aircraft = models.ForeignKey(
        Aircraft,
        on_delete=models.CASCADE,
        related_name='documents'
    )
    document_type = models.CharField(max_length=20, choices=DocumentType.choices)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    # File info
    file_url = models.URLField()
    file_name = models.CharField(max_length=255)
    file_size_bytes = models.IntegerField(default=0)
    mime_type = models.CharField(max_length=100, default='application/pdf')

    # Validity
    issue_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    is_current = models.BooleanField(default=True)

    # Versioning
    version = models.CharField(max_length=20, blank=True)

    class Meta:
        db_table = 'aircraft_documents'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.aircraft.registration} - {self.title}"


class Squawk(UUIDPrimaryKeyMixin, TimestampMixin, models.Model):
    """
    Aircraft discrepancies/issues reported by pilots.
    """
    class Severity(models.TextChoices):
        CRITICAL = 'critical', 'Critical - Aircraft Grounded'
        MAJOR = 'major', 'Major - Needs Immediate Attention'
        MINOR = 'minor', 'Minor - Can Continue Operations'
        INFORMATIONAL = 'info', 'Informational'

    class Status(models.TextChoices):
        OPEN = 'open', 'Open'
        IN_PROGRESS = 'in_progress', 'In Progress'
        DEFERRED = 'deferred', 'Deferred'
        RESOLVED = 'resolved', 'Resolved'
        CLOSED = 'closed', 'Closed'

    aircraft = models.ForeignKey(
        Aircraft,
        on_delete=models.CASCADE,
        related_name='squawks'
    )
    reported_by_id = models.UUIDField()  # Reference to User
    flight_id = models.UUIDField(null=True, blank=True)  # Reference to Flight

    # Issue details
    title = models.CharField(max_length=255)
    description = models.TextField()
    severity = models.CharField(max_length=20, choices=Severity.choices, default=Severity.MINOR)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)

    # When discovered
    discovered_at = models.DateTimeField()
    aircraft_hours_at_discovery = models.DecimalField(max_digits=10, decimal_places=1, null=True, blank=True)

    # Resolution
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by_id = models.UUIDField(null=True, blank=True)
    resolution_notes = models.TextField(blank=True)

    # MEL reference if deferred
    mel_reference = models.CharField(max_length=50, blank=True)
    defer_expiry = models.DateField(null=True, blank=True)

    class Meta:
        db_table = 'squawks'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['severity']),
        ]

    def __str__(self):
        return f"{self.aircraft.registration} - {self.title}"


class FuelLog(UUIDPrimaryKeyMixin, TimestampMixin, models.Model):
    """
    Fuel transactions for aircraft.
    """
    class TransactionType(models.TextChoices):
        UPLIFT = 'uplift', 'Fuel Uplift'
        CONSUMPTION = 'consumption', 'Fuel Consumption'
        ADJUSTMENT = 'adjustment', 'Adjustment'

    aircraft = models.ForeignKey(
        Aircraft,
        on_delete=models.CASCADE,
        related_name='fuel_logs'
    )
    flight_id = models.UUIDField(null=True, blank=True)
    recorded_by_id = models.UUIDField()

    transaction_type = models.CharField(max_length=20, choices=TransactionType.choices)
    quantity_liters = models.DecimalField(max_digits=8, decimal_places=2)
    price_per_liter = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    total_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    # Running total after this transaction
    fuel_remaining_liters = models.DecimalField(max_digits=8, decimal_places=2)

    location_id = models.UUIDField(null=True, blank=True)  # Where fueled
    fuel_type = models.CharField(max_length=20, default='100LL')
    receipt_number = models.CharField(max_length=50, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = 'fuel_logs'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.aircraft.registration} - {self.quantity_liters}L {self.transaction_type}"
