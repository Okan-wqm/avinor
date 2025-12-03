# services/aircraft-service/src/apps/core/models/propeller.py
"""
Aircraft Propeller Model

Propeller tracking and TBO management.
"""

import uuid
from decimal import Decimal
from datetime import date
from typing import Optional

from django.db import models


class AircraftPropeller(models.Model):
    """
    Aircraft propeller details and time tracking.

    Supports:
    - Multi-propeller aircraft
    - Fixed pitch and constant-speed props
    - TBO monitoring
    - Overhaul history
    """

    class PropellerType(models.TextChoices):
        FIXED = 'fixed', 'Fixed Pitch'
        CONSTANT_SPEED = 'constant_speed', 'Constant Speed'
        FEATHERING = 'feathering', 'Feathering'
        REVERSING = 'reversing', 'Reversing'
        GROUND_ADJUSTABLE = 'ground_adjustable', 'Ground Adjustable'

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    aircraft = models.ForeignKey(
        'Aircraft',
        on_delete=models.CASCADE,
        related_name='propellers'
    )
    engine = models.ForeignKey(
        'AircraftEngine',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='propellers',
        help_text='Associated engine'
    )

    # ==========================================================================
    # Position
    # ==========================================================================

    position = models.IntegerField(
        default=1,
        help_text='Propeller position (matches engine position)'
    )

    # ==========================================================================
    # Propeller Information
    # ==========================================================================

    manufacturer = models.CharField(max_length=100, blank=True, null=True)
    model = models.CharField(max_length=100, blank=True, null=True)
    serial_number = models.CharField(max_length=100, blank=True, null=True)

    # ==========================================================================
    # Type and Specifications
    # ==========================================================================

    propeller_type = models.CharField(
        max_length=50,
        choices=PropellerType.choices,
        default=PropellerType.FIXED
    )
    blade_count = models.IntegerField(
        default=2,
        help_text='Number of propeller blades'
    )
    diameter_inches = models.IntegerField(
        blank=True,
        null=True,
        help_text='Propeller diameter in inches'
    )

    # ==========================================================================
    # Time Tracking
    # ==========================================================================

    total_time_hours = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text='Total propeller time since new'
    )
    tsmoh = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text='Time Since Major Overhaul'
    )

    # ==========================================================================
    # TBO
    # ==========================================================================

    tbo_hours = models.IntegerField(
        blank=True,
        null=True,
        help_text='Manufacturer TBO in hours'
    )
    tbo_years = models.IntegerField(
        blank=True,
        null=True,
        help_text='Calendar TBO in years'
    )

    # ==========================================================================
    # Last Overhaul
    # ==========================================================================

    last_overhaul_date = models.DateField(blank=True, null=True)
    last_overhaul_hours = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True
    )
    last_overhaul_shop = models.CharField(max_length=255, blank=True, null=True)

    # ==========================================================================
    # Notes
    # ==========================================================================

    notes = models.TextField(blank=True, null=True)

    # ==========================================================================
    # Timestamps
    # ==========================================================================

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'aircraft_propellers'
        ordering = ['aircraft', 'position']
        verbose_name = 'Aircraft Propeller'
        verbose_name_plural = 'Aircraft Propellers'
        constraints = [
            models.UniqueConstraint(
                fields=['aircraft', 'position'],
                name='unique_aircraft_prop_position'
            )
        ]

    def __str__(self):
        return f"{self.aircraft.registration} Prop #{self.position}"

    # ==========================================================================
    # Properties
    # ==========================================================================

    @property
    def display_name(self) -> str:
        """Get display name for the propeller."""
        if self.manufacturer and self.model:
            return f"{self.manufacturer} {self.model}"
        return f"Propeller #{self.position}"

    @property
    def hours_until_tbo(self) -> Optional[Decimal]:
        """Calculate hours remaining until TBO."""
        if not self.tbo_hours:
            return None
        return Decimal(str(self.tbo_hours)) - self.tsmoh

    @property
    def tbo_percentage(self) -> Optional[float]:
        """Calculate percentage of TBO used."""
        if not self.tbo_hours or self.tbo_hours == 0:
            return None
        return (float(self.tsmoh) / self.tbo_hours) * 100

    @property
    def is_tbo_exceeded(self) -> bool:
        """Check if propeller has exceeded TBO."""
        if not self.tbo_hours:
            return False
        return self.tsmoh >= Decimal(str(self.tbo_hours))

    @property
    def years_since_overhaul(self) -> Optional[float]:
        """Calculate years since last overhaul."""
        if not self.last_overhaul_date:
            return None
        delta = date.today() - self.last_overhaul_date
        return delta.days / 365.25

    # ==========================================================================
    # Methods
    # ==========================================================================

    def add_hours(self, hours: Decimal) -> None:
        """Add flight hours to propeller."""
        self.total_time_hours += hours
        self.tsmoh += hours
        self.save(update_fields=['total_time_hours', 'tsmoh', 'updated_at'])

    def record_overhaul(
        self,
        overhaul_date: date,
        shop: str = None
    ) -> None:
        """Record a propeller overhaul."""
        self.last_overhaul_date = overhaul_date
        self.last_overhaul_hours = self.total_time_hours
        self.last_overhaul_shop = shop
        self.tsmoh = Decimal('0.00')
        self.save()

    def get_status(self) -> dict:
        """Get propeller status summary."""
        return {
            'position': self.position,
            'display_name': self.display_name,
            'propeller_type': self.propeller_type,
            'blade_count': self.blade_count,
            'total_time': float(self.total_time_hours),
            'tsmoh': float(self.tsmoh),
            'tbo_hours': self.tbo_hours,
            'hours_until_tbo': float(self.hours_until_tbo) if self.hours_until_tbo else None,
            'tbo_percentage': self.tbo_percentage,
            'is_tbo_exceeded': self.is_tbo_exceeded,
        }
