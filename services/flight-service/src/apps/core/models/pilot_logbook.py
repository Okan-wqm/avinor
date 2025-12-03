# services/flight-service/src/apps/core/models/pilot_logbook.py
"""
Pilot Logbook Summary Model

Aggregated flight time statistics for pilots.
"""

import uuid
from decimal import Decimal
from datetime import date, timedelta
from typing import Dict, Any, List

from django.db import models
from django.db.models import Sum, Count, Q
from django.contrib.postgres.fields import ArrayField
from django.utils import timezone


class PilotLogbookSummary(models.Model):
    """
    Aggregated pilot logbook statistics.

    This model maintains running totals for efficient querying
    and currency calculations. Updated when flights are approved.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    organization_id = models.UUIDField(db_index=True)
    pilot_id = models.UUIDField(db_index=True)

    # ==========================================================================
    # Total Times (decimal hours)
    # ==========================================================================
    total_time = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Total flight time"
    )
    total_pic = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Total PIC time"
    )
    total_sic = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Total SIC time"
    )
    total_dual_received = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Total dual instruction received"
    )
    total_dual_given = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Total dual instruction given"
    )
    total_solo = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Total solo time"
    )

    # ==========================================================================
    # Condition Times
    # ==========================================================================
    total_day = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    total_night = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    total_ifr = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    total_actual_instrument = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    total_simulated_instrument = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    total_cross_country = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )

    # ==========================================================================
    # Landing Counts
    # ==========================================================================
    total_landings = models.PositiveIntegerField(default=0)
    total_landings_day = models.PositiveIntegerField(default=0)
    total_landings_night = models.PositiveIntegerField(default=0)
    total_full_stop_day = models.PositiveIntegerField(default=0)
    total_full_stop_night = models.PositiveIntegerField(default=0)

    # ==========================================================================
    # Approaches
    # ==========================================================================
    total_approaches = models.PositiveIntegerField(default=0)
    total_holds = models.PositiveIntegerField(default=0)

    # ==========================================================================
    # Aircraft Category Times
    # ==========================================================================
    time_single_engine_land = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="ASEL time"
    )
    time_single_engine_sea = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="ASES time"
    )
    time_multi_engine_land = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="AMEL time"
    )
    time_multi_engine_sea = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="AMES time"
    )
    time_complex = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    time_high_performance = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    time_turbine = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    time_tailwheel = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    time_helicopter = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    time_glider = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )

    # ==========================================================================
    # Simulator Time
    # ==========================================================================
    time_ftd = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Flight Training Device time"
    )
    time_ffs = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Full Flight Simulator time"
    )

    # ==========================================================================
    # Last Flight Info
    # ==========================================================================
    last_flight_date = models.DateField(blank=True, null=True)
    last_flight_id = models.UUIDField(blank=True, null=True)

    # ==========================================================================
    # Currency Tracking (Rolling windows)
    # ==========================================================================
    landings_last_90_days = models.PositiveIntegerField(
        default=0,
        help_text="Total landings in last 90 days"
    )
    night_landings_last_90_days = models.PositiveIntegerField(
        default=0,
        help_text="Night landings in last 90 days"
    )
    ifr_approaches_last_6_months = models.PositiveIntegerField(
        default=0,
        help_text="IFR approaches in last 6 months"
    )
    ifr_holds_last_6_months = models.PositiveIntegerField(
        default=0,
        help_text="IFR holds in last 6 months"
    )

    # ==========================================================================
    # Flight Count
    # ==========================================================================
    total_flights = models.PositiveIntegerField(default=0)

    # ==========================================================================
    # Aircraft Type Times
    # ==========================================================================
    aircraft_type_times = models.JSONField(
        default=dict,
        help_text="Time by aircraft type: {'C172': 150.5, 'PA28': 45.0}"
    )

    # ==========================================================================
    # Airports Visited
    # ==========================================================================
    airports_visited = ArrayField(
        models.CharField(max_length=4),
        default=list,
        blank=True
    )
    airports_visited_count = models.PositiveIntegerField(default=0)

    # ==========================================================================
    # Timestamps
    # ==========================================================================
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'pilot_logbook_summary'
        constraints = [
            models.UniqueConstraint(
                fields=['organization_id', 'pilot_id'],
                name='unique_pilot_logbook_summary'
            )
        ]
        indexes = [
            models.Index(fields=['pilot_id']),
            models.Index(fields=['organization_id', 'pilot_id']),
        ]

    def __str__(self):
        return f"Logbook Summary: {self.pilot_id}"

    # ==========================================================================
    # Properties
    # ==========================================================================

    @property
    def total_instrument(self) -> Decimal:
        """Total instrument time (actual + simulated)."""
        return self.total_actual_instrument + self.total_simulated_instrument

    @property
    def total_single_engine(self) -> Decimal:
        """Total single engine time."""
        return self.time_single_engine_land + self.time_single_engine_sea

    @property
    def total_multi_engine(self) -> Decimal:
        """Total multi engine time."""
        return self.time_multi_engine_land + self.time_multi_engine_sea

    @property
    def days_since_last_flight(self) -> int | None:
        """Days since last flight."""
        if self.last_flight_date:
            return (timezone.now().date() - self.last_flight_date).days
        return None

    # ==========================================================================
    # Currency Checks
    # ==========================================================================

    def is_day_current(self) -> bool:
        """Check if pilot is day current (3 landings in 90 days)."""
        return self.landings_last_90_days >= 3

    def is_night_current(self) -> bool:
        """Check if pilot is night current (3 night landings in 90 days)."""
        return self.night_landings_last_90_days >= 3

    def is_ifr_current(self) -> bool:
        """Check if pilot is IFR current (6 approaches + holding in 6 months)."""
        return self.ifr_approaches_last_6_months >= 6

    def get_currency_status(self) -> Dict[str, Any]:
        """Get comprehensive currency status."""
        issues = []
        warnings = []

        # Day currency
        if not self.is_day_current():
            issues.append({
                'type': 'day_currency',
                'message': f'{self.landings_last_90_days}/3 landings in 90 days',
                'severity': 'error'
            })
        elif self.landings_last_90_days < 6:
            warnings.append({
                'type': 'day_currency_warning',
                'message': f'{self.landings_last_90_days} landings in 90 days (minimum 3)',
                'severity': 'warning'
            })

        # Night currency
        if not self.is_night_current():
            issues.append({
                'type': 'night_currency',
                'message': f'{self.night_landings_last_90_days}/3 night landings in 90 days',
                'severity': 'warning'
            })

        # IFR currency
        if not self.is_ifr_current():
            issues.append({
                'type': 'ifr_currency',
                'message': f'{self.ifr_approaches_last_6_months}/6 IFR approaches in 6 months',
                'severity': 'warning'
            })

        # Flight recency
        if self.days_since_last_flight and self.days_since_last_flight > 60:
            warnings.append({
                'type': 'flight_recency',
                'message': f'{self.days_since_last_flight} days since last flight',
                'severity': 'warning'
            })

        return {
            'is_day_current': self.is_day_current(),
            'is_night_current': self.is_night_current(),
            'is_ifr_current': self.is_ifr_current(),
            'issues': issues,
            'warnings': warnings,
            'last_flight': self.last_flight_date.isoformat() if self.last_flight_date else None,
            'days_since_last_flight': self.days_since_last_flight,
        }

    # ==========================================================================
    # Update Methods
    # ==========================================================================

    def add_flight(self, flight, role: str):
        """Add flight data to summary totals."""
        flight_time = flight.flight_time or Decimal('0')

        self.total_time += flight_time
        self.total_flights += 1
        self.last_flight_date = flight.flight_date
        self.last_flight_id = flight.id

        # Role-specific times
        if role == 'pic':
            self.total_pic += flight.time_pic or Decimal('0')
        elif role == 'sic':
            self.total_sic += flight.time_sic or Decimal('0')
        elif role == 'student':
            self.total_dual_received += flight.time_dual_received or Decimal('0')
            self.total_solo += flight.time_solo or Decimal('0')
        elif role == 'instructor':
            self.total_dual_given += flight.time_dual_given or Decimal('0')

        # Condition times
        self.total_day += flight.time_day or Decimal('0')
        self.total_night += flight.time_night or Decimal('0')
        self.total_ifr += flight.time_ifr or Decimal('0')
        self.total_actual_instrument += flight.time_actual_instrument or Decimal('0')
        self.total_simulated_instrument += flight.time_simulated_instrument or Decimal('0')
        self.total_cross_country += flight.time_cross_country or Decimal('0')

        # Landings
        self.total_landings += flight.total_landings
        self.total_landings_day += flight.landings_day
        self.total_landings_night += flight.landings_night
        self.total_full_stop_day += flight.full_stop_day
        self.total_full_stop_night += flight.full_stop_night

        # Approaches
        self.total_approaches += flight.approach_count
        self.total_holds += flight.holds

        # Track airports
        for airport in [flight.departure_airport, flight.arrival_airport]:
            if airport and airport not in self.airports_visited:
                self.airports_visited.append(airport)
        self.airports_visited_count = len(self.airports_visited)

    def recalculate_currency(self, flights_queryset):
        """Recalculate currency values from flight data."""
        today = timezone.now().date()
        ninety_days_ago = today - timedelta(days=90)
        six_months_ago = today - timedelta(days=180)

        # Last 90 days landings
        recent_flights = flights_queryset.filter(
            flight_date__gte=ninety_days_ago
        )

        landing_totals = recent_flights.aggregate(
            total_landings=Sum('landings_day') + Sum('landings_night'),
            night_landings=Sum('landings_night'),
        )

        self.landings_last_90_days = landing_totals['total_landings'] or 0
        self.night_landings_last_90_days = landing_totals['night_landings'] or 0

        # Last 6 months IFR
        ifr_flights = flights_queryset.filter(
            flight_date__gte=six_months_ago
        )

        ifr_totals = ifr_flights.aggregate(
            approaches=Sum('approach_count'),
            holds=Sum('holds'),
        )

        self.ifr_approaches_last_6_months = ifr_totals['approaches'] or 0
        self.ifr_holds_last_6_months = ifr_totals['holds'] or 0

    def recalculate_from_flights(self, flights_queryset):
        """Fully recalculate all totals from flight data."""
        # Reset all totals
        self.total_time = Decimal('0')
        self.total_pic = Decimal('0')
        self.total_sic = Decimal('0')
        self.total_dual_received = Decimal('0')
        self.total_dual_given = Decimal('0')
        self.total_solo = Decimal('0')
        self.total_day = Decimal('0')
        self.total_night = Decimal('0')
        self.total_ifr = Decimal('0')
        self.total_actual_instrument = Decimal('0')
        self.total_simulated_instrument = Decimal('0')
        self.total_cross_country = Decimal('0')
        self.total_landings = 0
        self.total_landings_day = 0
        self.total_landings_night = 0
        self.total_full_stop_day = 0
        self.total_full_stop_night = 0
        self.total_approaches = 0
        self.total_holds = 0
        self.total_flights = 0
        self.airports_visited = []
        self.aircraft_type_times = {}

        # Aggregate from flights
        totals = flights_queryset.aggregate(
            total_time=Sum('flight_time'),
            total_pic=Sum('time_pic'),
            total_sic=Sum('time_sic'),
            total_dual_received=Sum('time_dual_received'),
            total_dual_given=Sum('time_dual_given'),
            total_solo=Sum('time_solo'),
            total_day=Sum('time_day'),
            total_night=Sum('time_night'),
            total_ifr=Sum('time_ifr'),
            total_actual_instrument=Sum('time_actual_instrument'),
            total_simulated_instrument=Sum('time_simulated_instrument'),
            total_cross_country=Sum('time_cross_country'),
            total_landings_day=Sum('landings_day'),
            total_landings_night=Sum('landings_night'),
            total_full_stop_day=Sum('full_stop_day'),
            total_full_stop_night=Sum('full_stop_night'),
            total_approaches=Sum('approach_count'),
            total_holds=Sum('holds'),
            flight_count=Count('id'),
        )

        for field, value in totals.items():
            if hasattr(self, field) and value is not None:
                setattr(self, field, value)

        self.total_landings = (totals['total_landings_day'] or 0) + \
                              (totals['total_landings_night'] or 0)
        self.total_flights = totals['flight_count'] or 0

        # Get last flight
        last_flight = flights_queryset.order_by('-flight_date').first()
        if last_flight:
            self.last_flight_date = last_flight.flight_date
            self.last_flight_id = last_flight.id

        # Recalculate currency
        self.recalculate_currency(flights_queryset)

    @classmethod
    def get_or_create_for_pilot(
        cls,
        organization_id: uuid.UUID,
        pilot_id: uuid.UUID
    ) -> 'PilotLogbookSummary':
        """Get or create a logbook summary for a pilot."""
        summary, created = cls.objects.get_or_create(
            organization_id=organization_id,
            pilot_id=pilot_id,
            defaults={}
        )
        return summary
