# services/organization-service/src/apps/core/models/location.py
"""
Location Model

Represents physical locations/bases for organizations.
Includes airport information, facilities, and operating hours.
"""

import uuid
from django.db import models
from django.core.validators import (
    MinValueValidator,
    MaxValueValidator,
    RegexValidator
)


class Location(models.Model):
    """
    Location model representing a physical base or training site.

    Each organization can have multiple locations (bases, satellite sites,
    training areas, etc.). One location should be marked as primary.
    """

    class LocationType(models.TextChoices):
        BASE = 'base', 'Main Base'
        SATELLITE = 'satellite', 'Satellite Base'
        TRAINING_AREA = 'training_area', 'Training Area'
        SIMULATOR_CENTER = 'simulator_center', 'Simulator Center'

    # Primary Key
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    # Organization Reference
    organization = models.ForeignKey(
        'Organization',
        on_delete=models.CASCADE,
        related_name='locations'
    )

    # Basic Information
    name = models.CharField(max_length=255)
    code = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="Short code for the location"
    )
    description = models.TextField(blank=True, null=True)
    location_type = models.CharField(
        max_length=50,
        choices=LocationType.choices,
        default=LocationType.BASE
    )

    # Airport Information
    airport_icao = models.CharField(
        max_length=4,
        blank=True,
        null=True,
        validators=[RegexValidator(r'^[A-Z]{4}$', 'Must be 4-letter ICAO code')],
        help_text="ICAO airport code"
    )
    airport_iata = models.CharField(
        max_length=3,
        blank=True,
        null=True,
        validators=[RegexValidator(r'^[A-Z]{3}$', 'Must be 3-letter IATA code')],
        help_text="IATA airport code"
    )
    airport_name = models.CharField(max_length=255, blank=True, null=True)

    # Contact Information
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=50, blank=True, null=True)

    # Address
    address_line1 = models.CharField(max_length=255, blank=True, null=True)
    address_line2 = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    state_province = models.CharField(max_length=100, blank=True, null=True)
    postal_code = models.CharField(max_length=20, blank=True, null=True)
    country_code = models.CharField(
        max_length=2,
        blank=True,
        null=True,
        validators=[RegexValidator(r'^[A-Z]{2}$', 'Must be 2-letter country code')]
    )

    # Coordinates
    latitude = models.DecimalField(
        max_digits=10,
        decimal_places=8,
        blank=True,
        null=True,
        validators=[MinValueValidator(-90), MaxValueValidator(90)]
    )
    longitude = models.DecimalField(
        max_digits=11,
        decimal_places=8,
        blank=True,
        null=True,
        validators=[MinValueValidator(-180), MaxValueValidator(180)]
    )
    elevation_ft = models.IntegerField(
        blank=True,
        null=True,
        help_text="Elevation in feet"
    )

    # Operational Status
    is_primary = models.BooleanField(
        default=False,
        help_text="Primary location for the organization"
    )
    is_active = models.BooleanField(default=True)

    # Operating Hours (JSON structure)
    operating_hours = models.JSONField(
        default=dict,
        blank=True,
        help_text="""Operating hours in format:
        {
            "monday": {"open": "08:00", "close": "20:00"},
            "tuesday": {"open": "08:00", "close": "20:00"},
            ...
            "holidays": [{"date": "2024-01-01", "closed": true}]
        }"""
    )

    # Timezone (can differ from organization)
    timezone = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Location timezone (defaults to organization timezone if not set)"
    )

    # Facilities
    facilities = models.JSONField(
        default=list,
        blank=True,
        help_text="List of available facilities: hangar, classroom, briefing_room, etc."
    )

    # Runways
    runways = models.JSONField(
        default=list,
        blank=True,
        help_text="""Runway information:
        [{"designator": "09/27", "length_ft": 3000, "width_ft": 75, "surface": "asphalt"}]"""
    )

    # Radio Frequencies
    frequencies = models.JSONField(
        default=list,
        blank=True,
        help_text="""Radio frequencies:
        [{"type": "tower", "frequency": "118.1", "name": "Tower"}]"""
    )

    # Weather Station
    weather_station_id = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Weather station ID for METAR/TAF"
    )

    # Notes
    notes = models.TextField(
        blank=True,
        null=True,
        help_text="Internal notes"
    )
    pilot_notes = models.TextField(
        blank=True,
        null=True,
        help_text="Notes visible to pilots"
    )

    # Visual
    photo_url = models.URLField(max_length=500, blank=True, null=True)

    # Metadata
    metadata = models.JSONField(default=dict, blank=True)

    # Display
    display_order = models.IntegerField(
        default=0,
        help_text="Order in lists"
    )

    # Audit Fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'locations'
        ordering = ['display_order', 'name']
        constraints = [
            models.UniqueConstraint(
                fields=['organization', 'code'],
                condition=models.Q(code__isnull=False),
                name='unique_org_location_code'
            )
        ]
        indexes = [
            models.Index(fields=['organization']),
            models.Index(fields=['airport_icao']),
            models.Index(
                fields=['organization', 'is_primary'],
                condition=models.Q(is_primary=True),
                name='idx_location_primary'
            ),
            models.Index(
                fields=['organization', 'is_active'],
                condition=models.Q(is_active=True),
                name='idx_location_active'
            ),
        ]

    def __str__(self):
        if self.airport_icao:
            return f"{self.name} ({self.airport_icao})"
        return self.name

    def save(self, *args, **kwargs):
        # Ensure only one primary location per organization
        if self.is_primary:
            Location.objects.filter(
                organization=self.organization,
                is_primary=True
            ).exclude(pk=self.pk).update(is_primary=False)
        super().save(*args, **kwargs)

    @property
    def effective_timezone(self) -> str:
        """Get effective timezone (location or organization default)."""
        return self.timezone or self.organization.timezone

    @property
    def coordinates(self) -> dict:
        """Get coordinates as dict."""
        if self.latitude and self.longitude:
            return {
                'latitude': float(self.latitude),
                'longitude': float(self.longitude),
                'elevation_ft': self.elevation_ft
            }
        return None

    @property
    def full_address(self) -> str:
        """Get full formatted address."""
        parts = filter(None, [
            self.address_line1,
            self.address_line2,
            self.city,
            self.state_province,
            self.postal_code,
            self.country_code
        ])
        return ', '.join(parts)

    def is_open_at(self, datetime_obj) -> bool:
        """Check if location is open at a specific time."""
        if not self.operating_hours:
            return True  # No hours defined means always open

        day_name = datetime_obj.strftime('%A').lower()
        day_hours = self.operating_hours.get(day_name)

        if not day_hours:
            return False  # Day not in operating hours

        if day_hours.get('closed'):
            return False

        # Check holidays
        holidays = self.operating_hours.get('holidays', [])
        date_str = datetime_obj.strftime('%Y-%m-%d')
        for holiday in holidays:
            if holiday.get('date') == date_str and holiday.get('closed'):
                return False

        # Check time
        time_str = datetime_obj.strftime('%H:%M')
        open_time = day_hours.get('open', '00:00')
        close_time = day_hours.get('close', '23:59')

        return open_time <= time_str <= close_time

    def has_facility(self, facility_name: str) -> bool:
        """Check if location has a specific facility."""
        return facility_name.lower() in [f.lower() for f in self.facilities]

    def get_runway(self, designator: str) -> dict:
        """Get runway information by designator."""
        for runway in self.runways:
            if runway.get('designator') == designator:
                return runway
        return None

    def get_frequency(self, freq_type: str) -> str:
        """Get radio frequency by type (tower, ground, etc.)."""
        for freq in self.frequencies:
            if freq.get('type') == freq_type:
                return freq.get('frequency')
        return None
