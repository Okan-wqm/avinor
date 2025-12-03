# services/aircraft-service/src/apps/core/models/aircraft_type.py
"""
Aircraft Type Model

Reference data for aircraft types (Cessna 172, Piper PA-28, etc.)
"""

import uuid
from django.db import models


class AircraftType(models.Model):
    """
    Reference table for aircraft types.

    Contains manufacturer-defined specifications and default values
    that can be applied when creating new aircraft.
    """

    class Category(models.TextChoices):
        AIRPLANE = 'airplane', 'Airplane'
        HELICOPTER = 'helicopter', 'Helicopter'
        GLIDER = 'glider', 'Glider'
        BALLOON = 'balloon', 'Balloon'
        POWERED_LIFT = 'powered_lift', 'Powered Lift'

    class AircraftClass(models.TextChoices):
        SINGLE_ENGINE_LAND = 'single_engine_land', 'Single Engine Land'
        SINGLE_ENGINE_SEA = 'single_engine_sea', 'Single Engine Sea'
        MULTI_ENGINE_LAND = 'multi_engine_land', 'Multi Engine Land'
        MULTI_ENGINE_SEA = 'multi_engine_sea', 'Multi Engine Sea'
        HELICOPTER = 'helicopter', 'Helicopter'
        GLIDER = 'glider', 'Glider'

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    # Identification codes
    icao_code = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        help_text='ICAO type designator (e.g., C172, PA28)'
    )
    iata_code = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        help_text='IATA type code'
    )

    # Manufacturer and Model
    manufacturer = models.CharField(max_length=100)
    model = models.CharField(max_length=100)
    variant = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text='Model variant (e.g., 172S, 172SP)'
    )

    # Display names
    display_name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text='Full display name (e.g., Cessna 172 Skyhawk)'
    )
    short_name = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text='Short name for lists (e.g., C172)'
    )

    # Classification
    category = models.CharField(
        max_length=50,
        choices=Category.choices,
        default=Category.AIRPLANE
    )
    aircraft_class = models.CharField(
        max_length=50,
        choices=AircraftClass.choices,
        blank=True,
        null=True
    )

    # Characteristics
    is_complex = models.BooleanField(
        default=False,
        help_text='Retractable gear, constant-speed prop, and flaps'
    )
    is_high_performance = models.BooleanField(
        default=False,
        help_text='More than 200 HP'
    )
    is_multi_engine = models.BooleanField(default=False)
    requires_type_rating = models.BooleanField(
        default=False,
        help_text='Requires specific type rating to fly'
    )

    # Engine info
    engine_count = models.IntegerField(default=1)
    engine_type = models.CharField(
        max_length=50,
        default='piston',
        help_text='piston, turboprop, turbojet, turbofan, electric'
    )

    # Default specifications
    default_seat_count = models.IntegerField(blank=True, null=True)
    default_fuel_capacity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        help_text='Default fuel capacity in liters'
    )
    default_fuel_burn = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        blank=True,
        null=True,
        help_text='Default fuel burn in liters per hour'
    )
    default_cruise_speed = models.IntegerField(
        blank=True,
        null=True,
        help_text='Default cruise speed in knots'
    )

    # Performance specs
    mtow_kg = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        help_text='Maximum Takeoff Weight in kg'
    )
    never_exceed_kts = models.IntegerField(
        blank=True,
        null=True,
        help_text='VNE - Never Exceed Speed in knots'
    )
    stall_speed_kts = models.IntegerField(
        blank=True,
        null=True,
        help_text='VS0 - Stall speed in landing configuration'
    )

    # Visuals
    silhouette_url = models.URLField(
        max_length=500,
        blank=True,
        null=True,
        help_text='URL to aircraft silhouette image'
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'aircraft_types'
        ordering = ['manufacturer', 'model']
        verbose_name = 'Aircraft Type'
        verbose_name_plural = 'Aircraft Types'
        indexes = [
            models.Index(fields=['icao_code']),
            models.Index(fields=['manufacturer', 'model']),
        ]

    def __str__(self):
        if self.display_name:
            return self.display_name
        return f"{self.manufacturer} {self.model}"

    def save(self, *args, **kwargs):
        # Auto-generate display_name if not set
        if not self.display_name:
            self.display_name = f"{self.manufacturer} {self.model}"
            if self.variant:
                self.display_name += f" {self.variant}"

        # Auto-generate short_name if not set
        if not self.short_name:
            self.short_name = self.icao_code or f"{self.manufacturer[:1]}{self.model[:3]}".upper()

        # Set is_multi_engine based on engine_count
        self.is_multi_engine = self.engine_count > 1

        super().save(*args, **kwargs)

    @property
    def full_designation(self) -> str:
        """Get full type designation."""
        parts = [self.manufacturer, self.model]
        if self.variant:
            parts.append(self.variant)
        return ' '.join(parts)
