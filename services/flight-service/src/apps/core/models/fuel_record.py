# services/flight-service/src/apps/core/models/fuel_record.py
"""
Fuel Record Model

Detailed fuel tracking for flights.
"""

import uuid
from decimal import Decimal
from typing import Dict, Any

from django.db import models
from django.utils import timezone


class FuelRecord(models.Model):
    """
    Detailed fuel record for a flight.

    Tracks fuel quantities, costs, and locations for accurate
    fuel management and cost allocation.
    """

    class FuelType(models.TextChoices):
        AVGAS_100LL = '100LL', '100LL Avgas'
        AVGAS_UL94 = 'UL94', 'UL94 Unleaded'
        JET_A = 'JET_A', 'Jet A'
        JET_A1 = 'JET_A1', 'Jet A-1'
        MOGAS = 'MOGAS', 'Mogas'

    class RecordType(models.TextChoices):
        PREFLIGHT = 'preflight', 'Pre-flight Reading'
        POSTFLIGHT = 'postflight', 'Post-flight Reading'
        UPLIFT = 'uplift', 'Fuel Uplift'
        DEFUEL = 'defuel', 'Defuel'

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    flight_id = models.UUIDField(db_index=True)
    organization_id = models.UUIDField(db_index=True)
    aircraft_id = models.UUIDField(db_index=True)

    # ==========================================================================
    # Record Type and Timing
    # ==========================================================================
    record_type = models.CharField(
        max_length=20,
        choices=RecordType.choices
    )
    recorded_at = models.DateTimeField(default=timezone.now)

    # ==========================================================================
    # Fuel Details
    # ==========================================================================
    fuel_type = models.CharField(
        max_length=20,
        choices=FuelType.choices,
        default=FuelType.AVGAS_100LL
    )

    # Quantities in liters
    quantity_liters = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        help_text="Quantity in liters"
    )
    quantity_gallons = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Quantity in US gallons"
    )

    # Tank readings
    left_tank_liters = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        blank=True,
        null=True
    )
    right_tank_liters = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        blank=True,
        null=True
    )
    aux_tank_liters = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        blank=True,
        null=True
    )

    # ==========================================================================
    # Cost Information
    # ==========================================================================
    price_per_liter = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        blank=True,
        null=True
    )
    total_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True
    )
    currency = models.CharField(
        max_length=3,
        default='NOK'
    )

    # ==========================================================================
    # Location
    # ==========================================================================
    location_icao = models.CharField(
        max_length=4,
        blank=True,
        null=True,
        help_text="Airport ICAO code"
    )
    fbo_name = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text="FBO/Fuel provider name"
    )

    # ==========================================================================
    # Receipt Information
    # ==========================================================================
    receipt_number = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )
    receipt_image_url = models.URLField(
        max_length=500,
        blank=True,
        null=True
    )

    # ==========================================================================
    # Notes
    # ==========================================================================
    notes = models.TextField(blank=True, null=True)

    # ==========================================================================
    # Audit
    # ==========================================================================
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.UUIDField()

    class Meta:
        db_table = 'fuel_records'
        ordering = ['-recorded_at']
        indexes = [
            models.Index(fields=['flight_id']),
            models.Index(fields=['aircraft_id', 'recorded_at']),
        ]

    def __str__(self):
        return f"{self.record_type} - {self.quantity_liters}L at {self.recorded_at}"

    def save(self, *args, **kwargs):
        # Calculate gallons if not provided
        if self.quantity_liters and not self.quantity_gallons:
            self.quantity_gallons = self.quantity_liters * Decimal('0.264172')

        # Calculate total cost if not provided
        if self.quantity_liters and self.price_per_liter and not self.total_cost:
            self.total_cost = self.quantity_liters * self.price_per_liter

        super().save(*args, **kwargs)

    @property
    def total_tank_reading(self) -> Decimal:
        """Total fuel from all tanks."""
        total = Decimal('0')
        if self.left_tank_liters:
            total += self.left_tank_liters
        if self.right_tank_liters:
            total += self.right_tank_liters
        if self.aux_tank_liters:
            total += self.aux_tank_liters
        return total


class OilRecord(models.Model):
    """Oil addition record for a flight."""

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    flight_id = models.UUIDField(db_index=True)
    organization_id = models.UUIDField()
    aircraft_id = models.UUIDField()

    # ==========================================================================
    # Oil Details
    # ==========================================================================
    oil_type = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Oil type/grade"
    )
    quantity_liters = models.DecimalField(
        max_digits=5,
        decimal_places=2
    )
    quantity_quarts = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True
    )

    # Reading after addition
    oil_level_after = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Oil level after addition (quarts)"
    )

    # ==========================================================================
    # Cost
    # ==========================================================================
    cost = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        blank=True,
        null=True
    )

    # ==========================================================================
    # Timing
    # ==========================================================================
    recorded_at = models.DateTimeField(default=timezone.now)

    notes = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.UUIDField()

    class Meta:
        db_table = 'oil_records'
        ordering = ['-recorded_at']

    def save(self, *args, **kwargs):
        if self.quantity_liters and not self.quantity_quarts:
            self.quantity_quarts = self.quantity_liters * Decimal('1.05669')
        super().save(*args, **kwargs)
