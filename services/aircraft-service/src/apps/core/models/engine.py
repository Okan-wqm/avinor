# services/aircraft-service/src/apps/core/models/engine.py
"""
Aircraft Engine Model

Detailed engine tracking for multi-engine aircraft and TBO management.
"""

import uuid
from decimal import Decimal
from datetime import date
from typing import Optional

from django.db import models


class AircraftEngine(models.Model):
    """
    Aircraft engine details and time tracking.

    Supports:
    - Multi-engine aircraft (position tracking)
    - TBO (Time Between Overhaul) monitoring
    - Overhaul history tracking
    - Individual engine hour logging
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    aircraft = models.ForeignKey(
        'Aircraft',
        on_delete=models.CASCADE,
        related_name='engines'
    )

    # ==========================================================================
    # Position
    # ==========================================================================

    position = models.IntegerField(
        default=1,
        help_text='Engine position (1 for single, 1-4 for multi-engine)'
    )
    position_name = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text='Position name: Left, Right, Center, etc.'
    )

    # ==========================================================================
    # Engine Information
    # ==========================================================================

    manufacturer = models.CharField(max_length=100, blank=True, null=True)
    model = models.CharField(max_length=100, blank=True, null=True)
    serial_number = models.CharField(max_length=100, blank=True, null=True)

    # ==========================================================================
    # Specifications
    # ==========================================================================

    power_hp = models.IntegerField(
        blank=True,
        null=True,
        help_text='Rated horsepower'
    )
    displacement = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text='Engine displacement (e.g., 360 cubic inches)'
    )
    cylinders = models.IntegerField(blank=True, null=True)

    # ==========================================================================
    # Time Tracking
    # ==========================================================================

    total_time_hours = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text='Total engine time since new'
    )
    tsmoh = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text='Time Since Major Overhaul'
    )
    tsoh = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text='Time Since Overhaul (any overhaul)'
    )
    tso = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text='Time Since New or Overhaul'
    )

    # ==========================================================================
    # TBO (Time Between Overhaul)
    # ==========================================================================

    tbo_hours = models.IntegerField(
        blank=True,
        null=True,
        help_text='Manufacturer recommended TBO in hours'
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
        null=True,
        help_text='Engine hours at last overhaul'
    )
    last_overhaul_shop = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text='Shop that performed the overhaul'
    )
    last_overhaul_type = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text='major, top, field'
    )

    # ==========================================================================
    # Installation
    # ==========================================================================

    install_date = models.DateField(
        blank=True,
        null=True,
        help_text='Date engine was installed on this aircraft'
    )
    install_hours = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        help_text='Engine hours when installed'
    )
    install_airframe_hours = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        help_text='Airframe hours when engine was installed'
    )

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
        db_table = 'aircraft_engines'
        ordering = ['aircraft', 'position']
        verbose_name = 'Aircraft Engine'
        verbose_name_plural = 'Aircraft Engines'
        constraints = [
            models.UniqueConstraint(
                fields=['aircraft', 'position'],
                name='unique_aircraft_engine_position'
            )
        ]

    def __str__(self):
        return f"{self.aircraft.registration} Engine #{self.position}"

    # ==========================================================================
    # Properties
    # ==========================================================================

    @property
    def display_name(self) -> str:
        """Get display name for the engine."""
        if self.manufacturer and self.model:
            return f"{self.manufacturer} {self.model}"
        return f"Engine #{self.position}"

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
        """Check if engine has exceeded TBO hours."""
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

    @property
    def is_calendar_tbo_exceeded(self) -> bool:
        """Check if calendar TBO is exceeded."""
        if not self.tbo_years or not self.last_overhaul_date:
            return False
        years = self.years_since_overhaul
        return years is not None and years >= self.tbo_years

    # ==========================================================================
    # Methods
    # ==========================================================================

    def add_hours(self, hours: Decimal) -> None:
        """Add flight hours to engine."""
        self.total_time_hours += hours
        self.tsmoh += hours
        self.tsoh += hours
        self.tso += hours
        self.save(update_fields=[
            'total_time_hours', 'tsmoh', 'tsoh', 'tso', 'updated_at'
        ])

    def record_overhaul(
        self,
        overhaul_date: date,
        overhaul_type: str = 'major',
        shop: str = None
    ) -> None:
        """Record an engine overhaul."""
        self.last_overhaul_date = overhaul_date
        self.last_overhaul_hours = self.total_time_hours
        self.last_overhaul_type = overhaul_type
        self.last_overhaul_shop = shop

        if overhaul_type == 'major':
            self.tsmoh = Decimal('0.00')
        self.tsoh = Decimal('0.00')
        self.tso = Decimal('0.00')

        self.save()

    def get_status(self) -> dict:
        """Get engine status summary."""
        return {
            'position': self.position,
            'position_name': self.position_name,
            'display_name': self.display_name,
            'total_time': float(self.total_time_hours),
            'tsmoh': float(self.tsmoh),
            'tbo_hours': self.tbo_hours,
            'hours_until_tbo': float(self.hours_until_tbo) if self.hours_until_tbo else None,
            'tbo_percentage': self.tbo_percentage,
            'is_tbo_exceeded': self.is_tbo_exceeded,
            'is_calendar_tbo_exceeded': self.is_calendar_tbo_exceeded,
            'last_overhaul_date': self.last_overhaul_date.isoformat() if self.last_overhaul_date else None,
        }
