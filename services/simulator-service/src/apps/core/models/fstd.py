# services/simulator-service/src/apps/core/models/fstd.py
"""
FSTD (Flight Simulation Training Device) Model

Tracks simulator devices, their qualification, and availability.
Compliant with EASA FSTD qualification standards.
"""

import uuid
from django.db import models
from django.utils import timezone


class FSTDType(models.TextChoices):
    """FSTD Device Types per EASA regulations"""
    FFS = 'FFS', 'Full Flight Simulator'
    FTD = 'FTD', 'Flight Training Device'
    FNPT_I = 'FNPT_I', 'FNPT I'
    FNPT_II = 'FNPT_II', 'FNPT II'
    FNPT_III = 'FNPT_III', 'FNPT III'
    BITD = 'BITD', 'Basic Instrument Training Device'


class QualificationLevel(models.TextChoices):
    """FFS Qualification Levels"""
    LEVEL_A = 'A', 'Level A'
    LEVEL_B = 'B', 'Level B'
    LEVEL_C = 'C', 'Level C'
    LEVEL_D = 'D', 'Level D'
    MCC = 'MCC', 'MCC Qualified'
    GENERIC = 'GEN', 'Generic'


class DeviceStatus(models.TextChoices):
    """Device operational status"""
    ACTIVE = 'active', 'Active'
    MAINTENANCE = 'maintenance', 'Under Maintenance'
    CALIBRATION = 'calibration', 'Under Calibration'
    INACTIVE = 'inactive', 'Inactive'
    DECOMMISSIONED = 'decommissioned', 'Decommissioned'


class FSTDevice(models.Model):
    """
    FSTD/Simulator Device Registration

    Tracks flight simulation training devices including:
    - Full Flight Simulators (FFS) Level A-D
    - Flight Training Devices (FTD)
    - Flight and Navigation Procedures Trainers (FNPT I/II/III)
    - Basic Instrument Training Devices (BITD)
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    organization_id = models.UUIDField(
        db_index=True,
        help_text="Organization that owns/operates this device"
    )

    # Device Identification
    device_id = models.CharField(
        max_length=50,
        unique=True,
        help_text="Unique device identifier (e.g., SIM-001)"
    )
    name = models.CharField(
        max_length=100,
        help_text="Device name (e.g., B737 MAX Full Flight Simulator)"
    )
    manufacturer = models.CharField(
        max_length=100,
        blank=True,
        help_text="Simulator manufacturer (e.g., CAE, L3Harris, FlightSafety)"
    )
    model = models.CharField(
        max_length=100,
        blank=True,
        help_text="Simulator model designation"
    )
    serial_number = models.CharField(
        max_length=100,
        blank=True,
        help_text="Manufacturer serial number"
    )

    # Classification
    fstd_type = models.CharField(
        max_length=20,
        choices=FSTDType.choices,
        db_index=True,
        help_text="FSTD device type classification"
    )
    qualification_level = models.CharField(
        max_length=10,
        choices=QualificationLevel.choices,
        blank=True,
        help_text="Qualification level (for FFS: A, B, C, D)"
    )

    # Aircraft Simulated
    aircraft_type_simulated = models.CharField(
        max_length=50,
        help_text="ICAO aircraft type designator being simulated (e.g., B738, A320)"
    )
    aircraft_variant = models.CharField(
        max_length=100,
        blank=True,
        help_text="Specific variant (e.g., B737-800, A320neo)"
    )
    engine_type = models.CharField(
        max_length=100,
        blank=True,
        help_text="Engine type simulated (e.g., CFM56-7B)"
    )

    # Qualification & Certification
    qualification_certificate_number = models.CharField(
        max_length=100,
        blank=True,
        help_text="Qualification certificate number from authority"
    )
    qualification_authority = models.CharField(
        max_length=50,
        blank=True,
        help_text="Qualifying authority (e.g., EASA, FAA, CAA)"
    )
    qualification_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date of last qualification"
    )
    qualification_expiry = models.DateField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Qualification expiry date"
    )
    next_recurrent_evaluation = models.DateField(
        null=True,
        blank=True,
        help_text="Next scheduled recurrent evaluation date"
    )

    # Location & Availability
    location_id = models.UUIDField(
        null=True,
        blank=True,
        help_text="Location/facility where device is installed"
    )
    location_name = models.CharField(
        max_length=200,
        blank=True,
        help_text="Location name for display"
    )

    # Operational Status
    status = models.CharField(
        max_length=20,
        choices=DeviceStatus.choices,
        default=DeviceStatus.ACTIVE,
        db_index=True
    )
    last_maintenance_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date of last maintenance"
    )
    next_maintenance_date = models.DateField(
        null=True,
        blank=True,
        help_text="Next scheduled maintenance"
    )
    maintenance_notes = models.TextField(
        blank=True,
        help_text="Maintenance status notes"
    )

    # Capabilities
    capabilities = models.JSONField(
        default=list,
        blank=True,
        help_text="List of capabilities (e.g., ['LOFT', 'ZFTT', 'Emergency_Procedures'])"
    )
    motion_system = models.CharField(
        max_length=100,
        blank=True,
        help_text="Motion system specification (e.g., 6-DOF electric)"
    )
    visual_system = models.CharField(
        max_length=100,
        blank=True,
        help_text="Visual system specification (e.g., 200°x40° collimated)"
    )

    # Training Credits (per EASA FCL)
    ir_training_credit_hours = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        null=True,
        blank=True,
        help_text="Maximum hours creditable toward IR training"
    )
    type_rating_credit_hours = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        null=True,
        blank=True,
        help_text="Maximum hours creditable toward type rating"
    )
    zftt_eligible = models.BooleanField(
        default=False,
        help_text="Eligible for Zero Flight Time Training (ZFTT)"
    )

    # Pricing
    hourly_rate = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Standard hourly rate"
    )
    currency = models.CharField(
        max_length=3,
        default='NOK',
        help_text="Pricing currency"
    )
    minimum_booking_hours = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        default=1.0,
        help_text="Minimum booking duration in hours"
    )

    # Scheduling
    operating_hours_start = models.TimeField(
        null=True,
        blank=True,
        help_text="Daily operating hours start"
    )
    operating_hours_end = models.TimeField(
        null=True,
        blank=True,
        help_text="Daily operating hours end"
    )
    timezone = models.CharField(
        max_length=50,
        default='Europe/Oslo',
        help_text="Device timezone"
    )

    # Usage Statistics
    total_hours = models.DecimalField(
        max_digits=10,
        decimal_places=1,
        default=0,
        help_text="Total operating hours"
    )
    total_sessions = models.IntegerField(
        default=0,
        help_text="Total number of sessions"
    )
    hours_since_qualification = models.DecimalField(
        max_digits=10,
        decimal_places=1,
        default=0,
        help_text="Hours since last qualification"
    )

    # Documentation
    qualification_document_url = models.URLField(
        blank=True,
        help_text="URL to qualification certificate document"
    )
    user_manual_url = models.URLField(
        blank=True,
        help_text="URL to user/operator manual"
    )
    photo_url = models.URLField(
        blank=True,
        help_text="Photo of the device"
    )

    # Notes
    notes = models.TextField(
        blank=True,
        help_text="General notes"
    )
    internal_notes = models.TextField(
        blank=True,
        help_text="Internal notes (not visible to trainees)"
    )

    # Metadata
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional metadata"
    )

    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.UUIDField(null=True, blank=True)
    updated_by = models.UUIDField(null=True, blank=True)

    class Meta:
        db_table = 'fstd_devices'
        ordering = ['name']
        verbose_name = 'FSTD Device'
        verbose_name_plural = 'FSTD Devices'
        indexes = [
            models.Index(fields=['organization_id', 'status']),
            models.Index(fields=['fstd_type', 'qualification_level']),
            models.Index(fields=['aircraft_type_simulated']),
            models.Index(fields=['qualification_expiry']),
        ]

    def __str__(self):
        return f"{self.name} ({self.device_id})"

    @property
    def is_qualified(self):
        """Check if device qualification is current"""
        if not self.qualification_expiry:
            return False
        return self.qualification_expiry >= timezone.now().date()

    @property
    def is_available(self):
        """Check if device is available for booking"""
        return self.status == DeviceStatus.ACTIVE and self.is_qualified

    @property
    def days_until_expiry(self):
        """Calculate days until qualification expiry"""
        if not self.qualification_expiry:
            return None
        delta = self.qualification_expiry - timezone.now().date()
        return delta.days

    def update_statistics(self, session_hours: float):
        """Update device statistics after a session"""
        self.total_hours += session_hours
        self.total_sessions += 1
        self.hours_since_qualification += session_hours
        self.save(update_fields=['total_hours', 'total_sessions', 'hours_since_qualification', 'updated_at'])

    def get_available_slots(self, date):
        """Get available time slots for a given date"""
        # Implementation would check bookings and return available slots
        pass

    def get_credit_rules(self):
        """Get training credit rules based on device type and level"""
        credit_rules = {
            'FFS': {
                'D': {'ir_max': 50, 'type_max': None, 'zftt': True},
                'C': {'ir_max': 50, 'type_max': None, 'zftt': True},
                'B': {'ir_max': 40, 'type_max': 21, 'zftt': False},
                'A': {'ir_max': 40, 'type_max': 14, 'zftt': False},
            },
            'FTD': {
                'GEN': {'ir_max': 40, 'type_max': 21, 'zftt': False},
            },
            'FNPT_II': {
                'GEN': {'ir_max': 25, 'type_max': 10, 'zftt': False},
                'MCC': {'ir_max': 25, 'type_max': 10, 'zftt': False},
            },
            'FNPT_I': {
                'GEN': {'ir_max': 10, 'type_max': 0, 'zftt': False},
            },
            'BITD': {
                'GEN': {'ir_max': 10, 'type_max': 0, 'zftt': False},
            },
        }

        fstd_rules = credit_rules.get(self.fstd_type, {})
        return fstd_rules.get(self.qualification_level or 'GEN', {})
