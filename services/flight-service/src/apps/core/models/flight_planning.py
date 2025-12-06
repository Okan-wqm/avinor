# services/flight-service/src/apps/core/models/flight_planning.py
"""
Flight Planning Models

Comprehensive flight planning system including:
- Weather briefing (METAR, TAF, SIGMET, AIRMET)
- NOTAM management
- Route planning
- Fuel planning
- Weight & Balance integration
- Risk assessment

Reference: ICAO Annex 3 - Meteorological Service for International Air Navigation
Reference: ICAO Doc 8126 - Aeronautical Information Services Manual
"""

import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal
from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone


class WeatherBriefing(models.Model):
    """
    Weather briefing for flight planning.

    Consolidates weather information from multiple sources:
    - METAR (current conditions)
    - TAF (forecast)
    - SIGMET/AIRMET (significant weather)
    - Pilot reports (PIREPs)
    - Winds aloft
    """

    class BriefingType(models.TextChoices):
        STANDARD = 'standard', 'Standard Briefing'
        ABBREVIATED = 'abbreviated', 'Abbreviated Briefing'
        OUTLOOK = 'outlook', 'Outlook Briefing'
        INFLIGHT = 'inflight', 'Inflight Update'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization_id = models.UUIDField(db_index=True)
    pilot_id = models.UUIDField(db_index=True)

    # Briefing Details
    briefing_type = models.CharField(
        max_length=20,
        choices=BriefingType.choices,
        default=BriefingType.STANDARD
    )
    briefing_time = models.DateTimeField(default=timezone.now)

    # Route Information
    departure_airport = models.CharField(
        max_length=4,
        help_text="ICAO code"
    )
    destination_airport = models.CharField(
        max_length=4,
        help_text="ICAO code"
    )
    alternate_airports = ArrayField(
        models.CharField(max_length=4),
        default=list
    )
    route_waypoints = ArrayField(
        models.CharField(max_length=10),
        default=list,
        help_text="Waypoints/VORs along route"
    )

    # Planned Times
    proposed_departure_time = models.DateTimeField()
    estimated_flight_time = models.DurationField(blank=True, null=True)

    # METAR Data
    departure_metar = models.JSONField(
        default=dict,
        help_text="Decoded METAR for departure"
    )
    destination_metar = models.JSONField(
        default=dict,
        help_text="Decoded METAR for destination"
    )
    alternate_metars = models.JSONField(
        default=list,
        help_text="METARs for alternate airports"
    )
    enroute_metars = models.JSONField(
        default=list,
        help_text="METARs for enroute airports"
    )

    # TAF Data
    departure_taf = models.JSONField(
        default=dict,
        help_text="Decoded TAF for departure"
    )
    destination_taf = models.JSONField(
        default=dict,
        help_text="Decoded TAF for destination"
    )
    alternate_tafs = models.JSONField(
        default=list,
        help_text="TAFs for alternate airports"
    )

    # SIGMET/AIRMET
    sigmets = models.JSONField(
        default=list,
        help_text="Active SIGMETs along route"
    )
    airmets = models.JSONField(
        default=list,
        help_text="Active AIRMETs along route"
    )

    # Winds Aloft
    winds_aloft = models.JSONField(
        default=dict,
        help_text="Winds at various altitudes"
    )

    # PIREPs
    pireps = models.JSONField(
        default=list,
        help_text="Pilot reports along route"
    )

    # Radar/Satellite
    radar_summary = models.JSONField(
        default=dict,
        help_text="Radar imagery summary"
    )

    # Weather Synopsis
    synopsis = models.TextField(
        blank=True, null=True,
        help_text="Overall weather synopsis"
    )
    hazards_summary = models.TextField(
        blank=True, null=True,
        help_text="Summary of weather hazards"
    )

    # Weather Minimums Check
    departure_vfr_ok = models.BooleanField(
        blank=True, null=True,
        help_text="Departure meets VFR minimums"
    )
    departure_ifr_ok = models.BooleanField(
        blank=True, null=True,
        help_text="Departure meets IFR minimums"
    )
    destination_vfr_ok = models.BooleanField(
        blank=True, null=True
    )
    destination_ifr_ok = models.BooleanField(
        blank=True, null=True
    )

    # Risk Assessment
    weather_risk_level = models.CharField(
        max_length=10,
        choices=[
            ('low', 'Low'),
            ('moderate', 'Moderate'),
            ('high', 'High'),
            ('extreme', 'Extreme'),
        ],
        blank=True,
        null=True
    )
    weather_go_no_go = models.CharField(
        max_length=10,
        choices=[
            ('go', 'Go'),
            ('marginal', 'Marginal'),
            ('no_go', 'No-Go'),
        ],
        blank=True,
        null=True
    )

    # Source Information
    data_sources = ArrayField(
        models.CharField(max_length=50),
        default=list,
        help_text="Weather data sources used"
    )
    data_timestamp = models.DateTimeField(
        blank=True, null=True,
        help_text="When weather data was retrieved"
    )

    # Pilot Acknowledgment
    acknowledged = models.BooleanField(default=False)
    acknowledged_at = models.DateTimeField(blank=True, null=True)

    # Linked to flight plan
    flight_plan_id = models.UUIDField(blank=True, null=True)

    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'weather_briefings'
        ordering = ['-briefing_time']
        indexes = [
            models.Index(fields=['organization_id', 'pilot_id']),
            models.Index(fields=['departure_airport']),
            models.Index(fields=['destination_airport']),
            models.Index(fields=['proposed_departure_time']),
        ]

    def __str__(self):
        return f"Weather Briefing: {self.departure_airport}-{self.destination_airport} ({self.briefing_time})"


class NOTAMBriefing(models.Model):
    """
    NOTAM (Notice to Air Missions) briefing for flight planning.

    Consolidates NOTAMs relevant to the planned flight:
    - Departure airport NOTAMs
    - Destination airport NOTAMs
    - Enroute NOTAMs
    - FDC NOTAMs (regulatory)
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization_id = models.UUIDField(db_index=True)
    pilot_id = models.UUIDField(db_index=True)

    # Route Information
    departure_airport = models.CharField(max_length=4)
    destination_airport = models.CharField(max_length=4)
    alternate_airports = ArrayField(
        models.CharField(max_length=4),
        default=list
    )
    route_string = models.CharField(
        max_length=500,
        blank=True, null=True,
        help_text="Route string for enroute NOTAMs"
    )

    # Planned Time
    proposed_departure_time = models.DateTimeField()

    # NOTAM Data
    departure_notams = models.JSONField(
        default=list,
        help_text="NOTAMs for departure airport"
    )
    destination_notams = models.JSONField(
        default=list,
        help_text="NOTAMs for destination airport"
    )
    alternate_notams = models.JSONField(
        default=list,
        help_text="NOTAMs for alternate airports"
    )
    enroute_notams = models.JSONField(
        default=list,
        help_text="Enroute NOTAMs"
    )
    fdc_notams = models.JSONField(
        default=list,
        help_text="FDC/regulatory NOTAMs"
    )
    tfr_notams = models.JSONField(
        default=list,
        help_text="TFR (Temporary Flight Restriction) NOTAMs"
    )

    # Summary
    critical_notams = models.JSONField(
        default=list,
        help_text="NOTAMs flagged as critical"
    )
    notam_summary = models.TextField(
        blank=True, null=True,
        help_text="Summary of significant NOTAMs"
    )

    # Counts
    total_notams_count = models.IntegerField(default=0)
    critical_count = models.IntegerField(default=0)

    # Acknowledgment
    acknowledged = models.BooleanField(default=False)
    acknowledged_at = models.DateTimeField(blank=True, null=True)

    # Data Source
    data_timestamp = models.DateTimeField(blank=True, null=True)
    source = models.CharField(max_length=50, blank=True, null=True)

    # Linked to flight plan
    flight_plan_id = models.UUIDField(blank=True, null=True)

    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'notam_briefings'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organization_id', 'pilot_id']),
            models.Index(fields=['departure_airport']),
            models.Index(fields=['proposed_departure_time']),
        ]

    def __str__(self):
        return f"NOTAM Briefing: {self.departure_airport}-{self.destination_airport}"


class FlightPlan(models.Model):
    """
    Flight planning document.

    Comprehensive flight plan including:
    - Route planning
    - Fuel calculations
    - Performance data
    - Weight & Balance reference
    - Weather reference
    - NOTAM reference
    """

    class PlanType(models.TextChoices):
        VFR = 'vfr', 'VFR'
        IFR = 'ifr', 'IFR'
        SVFR = 'svfr', 'Special VFR'
        DVFR = 'dvfr', 'Defense VFR'
        COMPOSITE = 'composite', 'Composite VFR/IFR'

    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        COMPLETE = 'complete', 'Complete'
        FILED = 'filed', 'Filed with ATC'
        ACTIVE = 'active', 'Active'
        CLOSED = 'closed', 'Closed'
        CANCELLED = 'cancelled', 'Cancelled'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization_id = models.UUIDField(db_index=True)
    pilot_id = models.UUIDField(db_index=True)

    # Plan Identification
    plan_number = models.CharField(max_length=50, db_index=True)
    plan_type = models.CharField(
        max_length=20,
        choices=PlanType.choices,
        default=PlanType.VFR
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT
    )

    # Aircraft
    aircraft_id = models.UUIDField()
    aircraft_registration = models.CharField(max_length=20)
    aircraft_type = models.CharField(max_length=20)
    aircraft_equipment = models.CharField(
        max_length=50,
        blank=True, null=True,
        help_text="ICAO equipment codes"
    )

    # Crew
    pic_name = models.CharField(max_length=255)
    sic_name = models.CharField(max_length=255, blank=True, null=True)
    passengers_count = models.IntegerField(default=0)

    # Route
    departure_airport = models.CharField(max_length=4)
    destination_airport = models.CharField(max_length=4)
    alternate_airport = models.CharField(max_length=4, blank=True, null=True)
    alternate_airport_2 = models.CharField(max_length=4, blank=True, null=True)

    # Route Details
    route_string = models.TextField(
        blank=True, null=True,
        help_text="Full route string"
    )
    waypoints = models.JSONField(
        default=list,
        help_text="Detailed waypoint information"
    )

    # Altitude
    cruising_altitude = models.IntegerField(
        help_text="Feet MSL"
    )
    cruise_altitude_alternate = models.IntegerField(
        blank=True, null=True,
        help_text="If different for part of route"
    )

    # Timing
    proposed_departure_date = models.DateField()
    proposed_departure_time = models.TimeField()
    estimated_time_enroute = models.DurationField()
    estimated_arrival_time = models.TimeField(blank=True, null=True)

    # Speeds
    true_airspeed_kts = models.IntegerField()
    ground_speed_kts = models.IntegerField(blank=True, null=True)

    # Distances
    total_distance_nm = models.DecimalField(
        max_digits=8,
        decimal_places=2
    )

    # Fuel Planning
    fuel_endurance = models.DurationField(
        help_text="Total fuel endurance"
    )
    fuel_required_gal = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        help_text="Total fuel required"
    )
    fuel_on_board_gal = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        help_text="Fuel on board at departure"
    )
    fuel_reserve_gal = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        blank=True, null=True
    )
    fuel_to_destination_gal = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        blank=True, null=True
    )
    fuel_to_alternate_gal = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        blank=True, null=True
    )

    # Weight & Balance
    takeoff_weight_lbs = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        blank=True, null=True
    )
    landing_weight_lbs = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        blank=True, null=True
    )
    center_of_gravity = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        blank=True, null=True,
        help_text="CG in inches aft of datum"
    )
    within_weight_limits = models.BooleanField(blank=True, null=True)
    within_cg_limits = models.BooleanField(blank=True, null=True)
    weight_balance_document_id = models.UUIDField(blank=True, null=True)

    # Performance
    takeoff_distance_ft = models.IntegerField(blank=True, null=True)
    landing_distance_ft = models.IntegerField(blank=True, null=True)
    climb_rate_fpm = models.IntegerField(blank=True, null=True)
    performance_document_id = models.UUIDField(blank=True, null=True)

    # Weather Reference
    weather_briefing = models.ForeignKey(
        WeatherBriefing,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='flight_plans'
    )

    # NOTAM Reference
    notam_briefing = models.ForeignKey(
        NOTAMBriefing,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='flight_plans'
    )

    # Risk Assessment
    risk_score = models.IntegerField(
        blank=True, null=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    risk_factors = models.JSONField(
        default=list,
        help_text="Identified risk factors"
    )
    mitigations = models.JSONField(
        default=list,
        help_text="Risk mitigations applied"
    )
    go_no_go_decision = models.CharField(
        max_length=10,
        choices=[
            ('go', 'Go'),
            ('marginal', 'Marginal - Proceed with caution'),
            ('no_go', 'No-Go'),
        ],
        blank=True,
        null=True
    )

    # Remarks
    remarks = models.TextField(blank=True, null=True)
    special_handling = models.TextField(blank=True, null=True)

    # Filing
    filed_at = models.DateTimeField(blank=True, null=True)
    filing_reference = models.CharField(
        max_length=50,
        blank=True, null=True,
        help_text="ATC filing reference"
    )

    # Closure
    actual_departure_time = models.DateTimeField(blank=True, null=True)
    actual_arrival_time = models.DateTimeField(blank=True, null=True)
    closed_at = models.DateTimeField(blank=True, null=True)

    # Documents
    attachments = models.JSONField(default=list)

    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.UUIDField(blank=True, null=True)

    class Meta:
        db_table = 'flight_plans'
        ordering = ['-proposed_departure_date', '-proposed_departure_time']
        indexes = [
            models.Index(fields=['organization_id', 'status']),
            models.Index(fields=['pilot_id']),
            models.Index(fields=['aircraft_id']),
            models.Index(fields=['departure_airport']),
            models.Index(fields=['destination_airport']),
            models.Index(fields=['proposed_departure_date']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['organization_id', 'plan_number'],
                name='unique_flight_plan_number'
            )
        ]

    def __str__(self):
        return f"{self.plan_number}: {self.departure_airport}-{self.destination_airport}"


class FlightPlanWaypoint(models.Model):
    """
    Individual waypoint in a flight plan route.
    """

    class WaypointType(models.TextChoices):
        AIRPORT = 'airport', 'Airport'
        VOR = 'vor', 'VOR'
        NDB = 'ndb', 'NDB'
        INTERSECTION = 'intersection', 'Intersection'
        GPS = 'gps', 'GPS Waypoint'
        USER = 'user', 'User Defined'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    flight_plan = models.ForeignKey(
        FlightPlan,
        on_delete=models.CASCADE,
        related_name='route_waypoints'
    )

    # Sequence
    sequence = models.IntegerField()

    # Waypoint Identification
    identifier = models.CharField(max_length=10)
    name = models.CharField(max_length=100, blank=True, null=True)
    waypoint_type = models.CharField(
        max_length=20,
        choices=WaypointType.choices
    )

    # Position
    latitude = models.DecimalField(
        max_digits=10,
        decimal_places=7
    )
    longitude = models.DecimalField(
        max_digits=11,
        decimal_places=7
    )

    # Altitude
    altitude_ft = models.IntegerField(
        blank=True, null=True,
        help_text="Target altitude at waypoint"
    )
    altitude_restriction = models.CharField(
        max_length=10,
        choices=[
            ('at', 'At'),
            ('at_or_above', 'At or Above'),
            ('at_or_below', 'At or Below'),
            ('between', 'Between'),
        ],
        blank=True,
        null=True
    )

    # Leg to this waypoint
    magnetic_course = models.IntegerField(
        blank=True, null=True,
        validators=[MinValueValidator(0), MaxValueValidator(360)]
    )
    distance_nm = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        blank=True, null=True
    )
    leg_time = models.DurationField(blank=True, null=True)

    # Cumulative
    cumulative_distance_nm = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        blank=True, null=True
    )
    cumulative_time = models.DurationField(blank=True, null=True)
    estimated_time_over = models.TimeField(blank=True, null=True)

    # Wind
    wind_direction = models.IntegerField(blank=True, null=True)
    wind_speed_kts = models.IntegerField(blank=True, null=True)
    ground_speed_kts = models.IntegerField(blank=True, null=True)

    # Fuel
    fuel_remaining_gal = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        blank=True, null=True
    )

    # Notes
    notes = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'flight_plan_waypoints'
        ordering = ['flight_plan', 'sequence']
        indexes = [
            models.Index(fields=['flight_plan', 'sequence']),
        ]

    def __str__(self):
        return f"{self.sequence}. {self.identifier}"


class FlightRiskAssessment(models.Model):
    """
    Pre-flight risk assessment tool (PAVE, IMSAFE, etc).

    Standardized risk assessment for go/no-go decision.
    """

    class AssessmentType(models.TextChoices):
        PAVE = 'pave', 'PAVE (Pilot, Aircraft, enVironment, External)'
        IMSAFE = 'imsafe', 'IMSAFE (Illness, Medication, Stress, Alcohol, Fatigue, Emotion)'
        FRAT = 'frat', 'Flight Risk Assessment Tool'
        CUSTOM = 'custom', 'Custom Assessment'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization_id = models.UUIDField(db_index=True)
    pilot_id = models.UUIDField(db_index=True)

    # Assessment Type
    assessment_type = models.CharField(
        max_length=20,
        choices=AssessmentType.choices,
        default=AssessmentType.FRAT
    )
    assessment_date = models.DateField(default=date.today)

    # Linked Flight
    flight_plan = models.ForeignKey(
        FlightPlan,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='risk_assessments'
    )
    flight_id = models.UUIDField(
        blank=True, null=True,
        help_text="Linked flight record"
    )

    # Assessment Data
    assessment_data = models.JSONField(
        help_text="Full assessment responses"
    )

    # Scores by Category (for FRAT)
    pilot_score = models.IntegerField(
        default=0,
        help_text="Pilot-related risk score"
    )
    aircraft_score = models.IntegerField(
        default=0,
        help_text="Aircraft-related risk score"
    )
    environment_score = models.IntegerField(
        default=0,
        help_text="Environment-related risk score"
    )
    operation_score = models.IntegerField(
        default=0,
        help_text="Operation-related risk score"
    )

    # Total Score
    total_score = models.IntegerField(default=0)
    max_possible_score = models.IntegerField(default=100)

    # Risk Level
    risk_level = models.CharField(
        max_length=20,
        choices=[
            ('low', 'Low Risk'),
            ('moderate', 'Moderate Risk'),
            ('elevated', 'Elevated Risk'),
            ('high', 'High Risk'),
        ]
    )

    # Thresholds
    moderate_threshold = models.IntegerField(default=20)
    elevated_threshold = models.IntegerField(default=35)
    high_threshold = models.IntegerField(default=50)

    # Mitigations
    mitigations_required = models.BooleanField(default=False)
    mitigations_applied = models.JSONField(default=list)
    mitigations_notes = models.TextField(blank=True, null=True)

    # Decision
    go_decision = models.CharField(
        max_length=10,
        choices=[
            ('go', 'Go'),
            ('go_mitigated', 'Go with Mitigations'),
            ('no_go', 'No-Go'),
        ]
    )
    decision_notes = models.TextField(blank=True, null=True)

    # Instructor Review (for students)
    requires_instructor_review = models.BooleanField(default=False)
    reviewed_by_id = models.UUIDField(blank=True, null=True)
    reviewed_at = models.DateTimeField(blank=True, null=True)
    review_notes = models.TextField(blank=True, null=True)
    instructor_approved = models.BooleanField(blank=True, null=True)

    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'flight_risk_assessments'
        ordering = ['-assessment_date']
        indexes = [
            models.Index(fields=['organization_id', 'pilot_id']),
            models.Index(fields=['assessment_date']),
            models.Index(fields=['risk_level']),
        ]

    def __str__(self):
        return f"Risk Assessment: {self.risk_level} ({self.total_score})"

    def calculate_risk_level(self):
        """Calculate risk level based on total score and thresholds."""
        if self.total_score >= self.high_threshold:
            return 'high'
        elif self.total_score >= self.elevated_threshold:
            return 'elevated'
        elif self.total_score >= self.moderate_threshold:
            return 'moderate'
        return 'low'


class WeatherMinima(models.Model):
    """
    Personal and regulatory weather minimums.

    Defines weather limits for different certificate levels
    and personal minimums that may be more conservative.
    """

    class CertificateLevel(models.TextChoices):
        STUDENT = 'student', 'Student Pilot'
        PPL = 'ppl', 'Private Pilot'
        CPL = 'cpl', 'Commercial Pilot'
        ATP = 'atp', 'Airline Transport Pilot'
        CFI = 'cfi', 'Flight Instructor'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization_id = models.UUIDField(db_index=True)

    # Applicability
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    certificate_level = models.CharField(
        max_length=20,
        choices=CertificateLevel.choices,
        blank=True, null=True
    )
    is_default = models.BooleanField(
        default=False,
        help_text="Default minimums for certificate level"
    )

    # VFR Minimums
    vfr_visibility_sm = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        help_text="Minimum visibility in statute miles"
    )
    vfr_ceiling_ft = models.IntegerField(
        help_text="Minimum ceiling in feet AGL"
    )
    vfr_cloud_distance_horizontal_nm = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        default=Decimal('1.0'),
        help_text="Minimum horizontal cloud distance NM"
    )
    vfr_cloud_distance_vertical_ft = models.IntegerField(
        default=500,
        help_text="Minimum vertical cloud distance feet"
    )

    # Night VFR Minimums
    night_vfr_visibility_sm = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        blank=True, null=True
    )
    night_vfr_ceiling_ft = models.IntegerField(blank=True, null=True)

    # IFR Minimums (if applicable)
    ifr_visibility_sm = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        blank=True, null=True
    )
    ifr_ceiling_ft = models.IntegerField(blank=True, null=True)

    # Wind Limits
    max_crosswind_kts = models.IntegerField(
        blank=True, null=True,
        help_text="Maximum demonstrated crosswind"
    )
    max_headwind_kts = models.IntegerField(blank=True, null=True)
    max_tailwind_kts = models.IntegerField(blank=True, null=True)
    max_gust_kts = models.IntegerField(blank=True, null=True)

    # Runway Limits
    min_runway_length_ft = models.IntegerField(blank=True, null=True)
    min_runway_width_ft = models.IntegerField(blank=True, null=True)
    surface_types_allowed = ArrayField(
        models.CharField(max_length=20),
        default=list,
        help_text="Allowed runway surfaces"
    )

    # Special Conditions
    mountain_flying_allowed = models.BooleanField(default=False)
    over_water_allowed = models.BooleanField(default=False)
    night_allowed = models.BooleanField(default=True)

    # Active Status
    is_active = models.BooleanField(default=True)

    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'weather_minima'
        ordering = ['certificate_level', 'name']
        indexes = [
            models.Index(fields=['organization_id', 'is_active']),
            models.Index(fields=['certificate_level']),
        ]

    def __str__(self):
        return f"{self.name} ({self.certificate_level})"


class PersonalMinima(models.Model):
    """
    Individual pilot's personal weather minimums.

    Personal minimums should be more conservative than
    regulatory minimums, especially for less experienced pilots.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization_id = models.UUIDField(db_index=True)
    pilot_id = models.UUIDField(db_index=True, unique=True)

    # Base Minimums Reference
    base_minima = models.ForeignKey(
        WeatherMinima,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Regulatory/organizational base minimums"
    )

    # Personal VFR Minimums
    vfr_visibility_sm = models.DecimalField(
        max_digits=4,
        decimal_places=1
    )
    vfr_ceiling_ft = models.IntegerField()

    # Personal Night VFR Minimums
    night_vfr_visibility_sm = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        blank=True, null=True
    )
    night_vfr_ceiling_ft = models.IntegerField(blank=True, null=True)

    # Personal Wind Limits
    max_crosswind_kts = models.IntegerField(blank=True, null=True)
    max_gust_kts = models.IntegerField(blank=True, null=True)

    # Currency-Based Adjustments
    currency_recency_days = models.IntegerField(
        default=30,
        help_text="Days since last flight to consider current"
    )
    minimums_increase_if_not_current = models.JSONField(
        default=dict,
        help_text="How much to increase minimums if not current"
    )

    # Special Conditions
    comfort_with_mountain = models.IntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="1=Not comfortable, 5=Very comfortable"
    )
    comfort_with_night = models.IntegerField(
        default=3,
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    comfort_with_imc = models.IntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )

    # Notes
    notes = models.TextField(blank=True, null=True)

    # Last Review
    last_reviewed = models.DateField(blank=True, null=True)
    reviewed_with_instructor_id = models.UUIDField(blank=True, null=True)

    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'personal_minima'
        indexes = [
            models.Index(fields=['organization_id', 'pilot_id']),
        ]

    def __str__(self):
        return f"Personal Minima: {self.pilot_id}"


class SavedRoute(models.Model):
    """
    Saved/favorite routes for quick flight planning.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization_id = models.UUIDField(db_index=True)
    pilot_id = models.UUIDField(
        blank=True, null=True,
        help_text="If null, available to all org pilots"
    )

    # Route Identification
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    is_favorite = models.BooleanField(default=False)

    # Route Details
    departure_airport = models.CharField(max_length=4)
    destination_airport = models.CharField(max_length=4)
    alternate_airport = models.CharField(max_length=4, blank=True, null=True)

    route_string = models.TextField(blank=True, null=True)
    waypoints = models.JSONField(default=list)

    # Typical Values
    typical_altitude = models.IntegerField(blank=True, null=True)
    typical_airspeed_kts = models.IntegerField(blank=True, null=True)
    estimated_time = models.DurationField(blank=True, null=True)
    distance_nm = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        blank=True, null=True
    )

    # Categorization
    tags = ArrayField(
        models.CharField(max_length=50),
        default=list
    )
    route_type = models.CharField(
        max_length=20,
        choices=[
            ('training', 'Training Route'),
            ('cross_country', 'Cross Country'),
            ('scenic', 'Scenic'),
            ('practice_area', 'Practice Area'),
            ('local', 'Local'),
        ],
        blank=True,
        null=True
    )

    # Usage Count
    usage_count = models.IntegerField(default=0)
    last_used = models.DateTimeField(blank=True, null=True)

    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'saved_routes'
        ordering = ['-is_favorite', '-usage_count']
        indexes = [
            models.Index(fields=['organization_id', 'pilot_id']),
            models.Index(fields=['departure_airport', 'destination_airport']),
        ]

    def __str__(self):
        return f"{self.name}: {self.departure_airport}-{self.destination_airport}"
