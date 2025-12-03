"""Flight Service Models - Flight records and logbook."""
import uuid
from decimal import Decimal
from django.db import models
from shared.common.mixins import UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin


class Flight(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, models.Model):
    """Individual flight record."""

    class FlightType(models.TextChoices):
        TRAINING = 'training', 'Training'
        SOLO = 'solo', 'Solo'
        CHECK_RIDE = 'check_ride', 'Check Ride'
        CROSS_COUNTRY = 'cross_country', 'Cross Country'
        NIGHT = 'night', 'Night'
        INSTRUMENT = 'instrument', 'Instrument'
        PROFICIENCY = 'proficiency', 'Proficiency'
        FERRY = 'ferry', 'Ferry'
        OTHER = 'other', 'Other'

    class Status(models.TextChoices):
        PLANNED = 'planned', 'Planned'
        PREFLIGHT = 'preflight', 'Pre-Flight'
        IN_PROGRESS = 'in_progress', 'In Progress'
        COMPLETED = 'completed', 'Completed'
        CANCELLED = 'cancelled', 'Cancelled'

    # References
    organization_id = models.UUIDField()
    booking_id = models.UUIDField(null=True, blank=True)
    aircraft_id = models.UUIDField()
    pic_id = models.UUIDField()  # Pilot in Command
    sic_id = models.UUIDField(null=True, blank=True)  # Second in Command
    instructor_id = models.UUIDField(null=True, blank=True)

    # Flight details
    flight_type = models.CharField(max_length=20, choices=FlightType.choices, default=FlightType.TRAINING)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PLANNED)

    # Times (UTC)
    scheduled_departure = models.DateTimeField(null=True, blank=True)
    scheduled_arrival = models.DateTimeField(null=True, blank=True)
    actual_departure = models.DateTimeField(null=True, blank=True)
    actual_arrival = models.DateTimeField(null=True, blank=True)

    # Route
    departure_airport = models.CharField(max_length=4)  # ICAO
    arrival_airport = models.CharField(max_length=4)
    route = models.TextField(blank=True)
    remarks = models.TextField(blank=True)

    # Flight times (decimal hours)
    block_time = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    flight_time = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    hobbs_start = models.DecimalField(max_digits=10, decimal_places=1, null=True, blank=True)
    hobbs_end = models.DecimalField(max_digits=10, decimal_places=1, null=True, blank=True)
    tach_start = models.DecimalField(max_digits=10, decimal_places=1, null=True, blank=True)
    tach_end = models.DecimalField(max_digits=10, decimal_places=1, null=True, blank=True)

    # Logged times (for pilot logbook)
    time_pic = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    time_sic = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    time_dual_received = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    time_dual_given = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    time_solo = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    time_cross_country = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    time_night = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    time_actual_instrument = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    time_simulated_instrument = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    time_simulator = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    # Landings
    landings_day = models.IntegerField(default=0)
    landings_night = models.IntegerField(default=0)
    landings_full_stop = models.IntegerField(default=0)

    # Approaches
    approaches = models.JSONField(default=list, blank=True)  # List of approach types

    # Weather
    weather_conditions = models.CharField(max_length=10, blank=True)  # VFR, MVFR, IFR, LIFR
    weather_briefing_obtained = models.BooleanField(default=False)

    # Fuel
    fuel_added_liters = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    fuel_used_liters = models.DecimalField(max_digits=8, decimal_places=2, default=0)

    # Distance
    distance_nm = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)

    # Signatures
    pic_signature = models.TextField(blank=True)
    pic_signed_at = models.DateTimeField(null=True, blank=True)
    instructor_signature = models.TextField(blank=True)
    instructor_signed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'flights'
        ordering = ['-actual_departure', '-scheduled_departure']
        indexes = [
            models.Index(fields=['pic_id', '-actual_departure']),
            models.Index(fields=['aircraft_id', '-actual_departure']),
            models.Index(fields=['organization_id', '-actual_departure']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.departure_airport}-{self.arrival_airport} ({self.actual_departure or self.scheduled_departure})"


class FlightTrack(UUIDPrimaryKeyMixin, TimestampMixin, models.Model):
    """GPS track points for a flight."""

    flight = models.ForeignKey(Flight, on_delete=models.CASCADE, related_name='track_points')

    timestamp = models.DateTimeField()
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    altitude_ft = models.IntegerField(null=True, blank=True)
    ground_speed_kts = models.IntegerField(null=True, blank=True)
    heading = models.IntegerField(null=True, blank=True)  # Degrees

    class Meta:
        db_table = 'flight_tracks'
        ordering = ['timestamp']


class LogbookEntry(UUIDPrimaryKeyMixin, TimestampMixin, models.Model):
    """Pilot logbook entry (may reference multiple flights or manual entry)."""

    pilot_id = models.UUIDField()
    flight = models.ForeignKey(Flight, on_delete=models.SET_NULL, null=True, blank=True, related_name='logbook_entries')

    # Date and aircraft
    date = models.DateField()
    aircraft_registration = models.CharField(max_length=10)
    aircraft_type = models.CharField(max_length=50)

    # Route
    departure = models.CharField(max_length=4)
    arrival = models.CharField(max_length=4)
    route = models.TextField(blank=True)

    # Times
    total_time = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    pic_time = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    sic_time = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    dual_received = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    dual_given = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    solo_time = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    cross_country = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    night_time = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    actual_instrument = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    simulated_instrument = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    simulator_time = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    # Landings
    day_landings = models.IntegerField(default=0)
    night_landings = models.IntegerField(default=0)

    # Approaches and holds
    instrument_approaches = models.IntegerField(default=0)
    holds = models.IntegerField(default=0)

    # Instructor info
    instructor_name = models.CharField(max_length=255, blank=True)
    instructor_certificate_number = models.CharField(max_length=50, blank=True)

    # Remarks
    remarks = models.TextField(blank=True)

    # Verification
    is_verified = models.BooleanField(default=False)
    verified_by_id = models.UUIDField(null=True, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'logbook_entries'
        ordering = ['-date']
        indexes = [
            models.Index(fields=['pilot_id', '-date']),
        ]


class PilotTotals(UUIDPrimaryKeyMixin, TimestampMixin, models.Model):
    """Cached pilot total times for quick access."""

    pilot_id = models.UUIDField(unique=True)

    total_time = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    pic_time = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    sic_time = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    dual_received = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    dual_given = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    solo_time = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    cross_country = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    night_time = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    actual_instrument = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    simulated_instrument = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    simulator_time = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    total_landings = models.IntegerField(default=0)
    day_landings = models.IntegerField(default=0)
    night_landings = models.IntegerField(default=0)

    total_flights = models.IntegerField(default=0)
    last_flight_date = models.DateField(null=True, blank=True)

    # Last 90 days for currency
    last_90_days_landings = models.IntegerField(default=0)
    last_90_days_night_landings = models.IntegerField(default=0)
    last_90_days_instrument_approaches = models.IntegerField(default=0)

    class Meta:
        db_table = 'pilot_totals'
