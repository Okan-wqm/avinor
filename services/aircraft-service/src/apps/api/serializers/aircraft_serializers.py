# services/aircraft-service/src/apps/api/serializers/aircraft_serializers.py
"""
Aircraft Serializers

Serializers for aircraft CRUD and status operations.
"""

import re
from rest_framework import serializers

from apps.core.models import Aircraft, AircraftType


class AircraftTypeSerializer(serializers.ModelSerializer):
    """Serializer for aircraft types (reference data)."""

    category_display = serializers.CharField(source='get_category_display', read_only=True)
    class_display = serializers.CharField(source='get_class_type_display', read_only=True)

    class Meta:
        model = AircraftType
        fields = [
            'id', 'icao_code', 'iata_code', 'manufacturer', 'model',
            'variant', 'common_name', 'category', 'category_display',
            'class_type', 'class_display', 'engine_count', 'engine_type',
            'default_cruise_speed_kts', 'default_fuel_consumption_gph',
            'default_fuel_capacity_gal', 'default_useful_load_lbs',
            'default_seat_count', 'is_complex', 'is_high_performance',
            'is_tailwheel', 'is_pressurized', 'requires_type_rating',
            'is_active',
        ]
        read_only_fields = ['id']


class AircraftListSerializer(serializers.ModelSerializer):
    """Serializer for aircraft list view."""

    status_display = serializers.CharField(source='get_status_display', read_only=True)
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    aircraft_type_name = serializers.SerializerMethodField()

    class Meta:
        model = Aircraft
        fields = [
            'id', 'registration', 'serial_number', 'aircraft_type',
            'aircraft_type_name', 'category', 'category_display',
            'year_manufactured', 'status', 'status_display',
            'is_airworthy', 'is_available', 'home_base_id',
            'current_location_id', 'total_time_hours', 'open_squawk_count',
            'has_grounding_squawks', 'image_url', 'updated_at',
        ]

    def get_aircraft_type_name(self, obj):
        if obj.aircraft_type:
            return obj.aircraft_type.display_name
        return None


class AircraftDetailSerializer(serializers.ModelSerializer):
    """Serializer for aircraft detail view."""

    status_display = serializers.CharField(source='get_status_display', read_only=True)
    operational_status_display = serializers.CharField(
        source='get_operational_status_display', read_only=True
    )
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    engine_type_display = serializers.CharField(source='get_engine_type_display', read_only=True)
    fuel_type_display = serializers.CharField(source='get_fuel_type_display', read_only=True)
    aircraft_type_data = AircraftTypeSerializer(source='aircraft_type', read_only=True)
    display_name = serializers.CharField(read_only=True)
    is_available = serializers.BooleanField(read_only=True)
    is_multi_engine = serializers.BooleanField(read_only=True)
    arc_days_remaining = serializers.IntegerField(read_only=True)
    insurance_days_remaining = serializers.IntegerField(read_only=True)

    class Meta:
        model = Aircraft
        fields = [
            # Identification
            'id', 'organization_id', 'registration', 'serial_number',
            'aircraft_type', 'aircraft_type_data', 'display_name',

            # Classification
            'category', 'category_display', 'class_type', 'year_manufactured',

            # Technical
            'engine_type', 'engine_type_display', 'engine_count',
            'fuel_type', 'fuel_type_display', 'is_multi_engine',
            'is_complex', 'is_high_performance', 'is_tailwheel', 'is_ifr_certified',

            # Specifications
            'max_gross_weight_lbs', 'empty_weight_lbs', 'useful_load_lbs',
            'fuel_capacity_gal', 'usable_fuel_gal', 'oil_capacity_qts',
            'max_passengers', 'cruise_speed_kts', 'fuel_burn_gph',

            # Counters
            'hobbs_time', 'tach_time', 'total_time_hours',
            'total_landings', 'total_cycles', 'billing_time_source',
            'last_hobbs_update',

            # Status
            'status', 'status_display', 'operational_status',
            'operational_status_display', 'is_airworthy', 'is_available',
            'is_grounded', 'grounded_at', 'grounded_by', 'grounded_reason',

            # Certificates
            'airworthiness_cert_type', 'airworthiness_cert_date',
            'arc_expiry_date', 'arc_days_remaining',
            'registration_expiry_date', 'insurance_expiry_date',
            'insurance_days_remaining', 'insurance_provider', 'insurance_policy_number',

            # Location
            'home_base_id', 'current_location_id',

            # Squawk Status
            'open_squawk_count', 'has_open_squawks', 'has_grounding_squawks',

            # Billing
            'hourly_rate', 'block_rate', 'daily_rate',

            # Display
            'image_url', 'color_scheme', 'notes',

            # Timestamps
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'organization_id', 'display_name', 'is_available',
            'is_multi_engine', 'arc_days_remaining', 'insurance_days_remaining',
            'open_squawk_count', 'has_open_squawks', 'has_grounding_squawks',
            'is_grounded', 'grounded_at', 'grounded_by', 'grounded_reason',
            'created_at', 'updated_at',
        ]


class AircraftCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating aircraft."""

    class Meta:
        model = Aircraft
        fields = [
            'registration', 'serial_number', 'aircraft_type',
            'category', 'class_type', 'year_manufactured',
            'engine_type', 'engine_count', 'fuel_type',
            'is_complex', 'is_high_performance', 'is_tailwheel', 'is_ifr_certified',
            'max_gross_weight_lbs', 'empty_weight_lbs', 'useful_load_lbs',
            'fuel_capacity_gal', 'usable_fuel_gal', 'oil_capacity_qts',
            'max_passengers', 'cruise_speed_kts', 'fuel_burn_gph',
            'hobbs_time', 'tach_time', 'total_time_hours',
            'total_landings', 'total_cycles', 'billing_time_source',
            'airworthiness_cert_type', 'airworthiness_cert_date',
            'arc_expiry_date', 'registration_expiry_date',
            'insurance_expiry_date', 'insurance_provider', 'insurance_policy_number',
            'home_base_id', 'current_location_id',
            'hourly_rate', 'block_rate', 'daily_rate',
            'image_url', 'color_scheme', 'notes',
        ]

    def validate_registration(self, value):
        """Validate aircraft registration format."""
        value = value.upper().strip()

        # Common registration patterns
        patterns = [
            r'^N\d{1,5}[A-Z]{0,2}$',      # USA (N12345, N123AB)
            r'^G-[A-Z]{4}$',               # UK (G-ABCD)
            r'^TC-[A-Z]{3}$',              # Turkey (TC-ABC)
            r'^D-[A-Z]{4}$',               # Germany (D-ABCD)
            r'^F-[A-Z]{4}$',               # France (F-ABCD)
            r'^OE-[A-Z]{3}$',              # Austria (OE-ABC)
            r'^PH-[A-Z]{3}$',              # Netherlands (PH-ABC)
            r'^SE-[A-Z]{3}$',              # Sweden (SE-ABC)
            r'^LN-[A-Z]{3}$',              # Norway (LN-ABC)
            r'^OY-[A-Z]{3}$',              # Denmark (OY-ABC)
            r'^HB-[A-Z]{3}$',              # Switzerland (HB-ABC)
            r'^I-[A-Z]{4}$',               # Italy (I-ABCD)
            r'^EC-[A-Z]{3}$',              # Spain (EC-ABC)
            r'^C-[A-Z]{4}$',               # Canada (C-GABC)
            r'^VH-[A-Z]{3}$',              # Australia (VH-ABC)
            r'^ZK-[A-Z]{3}$',              # New Zealand (ZK-ABC)
            r'^[A-Z]{2}-[A-Z0-9]{3,4}$',   # Generic international
        ]

        is_valid = any(re.match(pattern, value) for pattern in patterns)

        if not is_valid and len(value) < 3:
            raise serializers.ValidationError(
                "Registration must be at least 3 characters"
            )

        return value

    def validate(self, attrs):
        """Validate the complete aircraft data."""
        # Ensure useful_load = max_gross_weight - empty_weight if both provided
        if 'max_gross_weight_lbs' in attrs and 'empty_weight_lbs' in attrs:
            if 'useful_load_lbs' not in attrs:
                attrs['useful_load_lbs'] = (
                    attrs['max_gross_weight_lbs'] - attrs['empty_weight_lbs']
                )

        # Ensure usable_fuel <= fuel_capacity
        if 'usable_fuel_gal' in attrs and 'fuel_capacity_gal' in attrs:
            if attrs['usable_fuel_gal'] > attrs['fuel_capacity_gal']:
                raise serializers.ValidationError({
                    'usable_fuel_gal': "Usable fuel cannot exceed fuel capacity"
                })

        return attrs


class AircraftUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating aircraft."""

    class Meta:
        model = Aircraft
        fields = [
            'serial_number', 'aircraft_type',
            'category', 'class_type', 'year_manufactured',
            'engine_type', 'engine_count', 'fuel_type',
            'is_complex', 'is_high_performance', 'is_tailwheel', 'is_ifr_certified',
            'max_gross_weight_lbs', 'empty_weight_lbs', 'useful_load_lbs',
            'fuel_capacity_gal', 'usable_fuel_gal', 'oil_capacity_qts',
            'max_passengers', 'cruise_speed_kts', 'fuel_burn_gph',
            'billing_time_source',
            'airworthiness_cert_type', 'airworthiness_cert_date',
            'arc_expiry_date', 'registration_expiry_date',
            'insurance_expiry_date', 'insurance_provider', 'insurance_policy_number',
            'home_base_id', 'current_location_id',
            'hourly_rate', 'block_rate', 'daily_rate',
            'image_url', 'color_scheme', 'notes',
            'operational_status',
        ]

    def validate(self, attrs):
        """Validate update data."""
        instance = self.instance

        # Check weight calculations if updating weights
        max_gross = attrs.get('max_gross_weight_lbs', instance.max_gross_weight_lbs)
        empty = attrs.get('empty_weight_lbs', instance.empty_weight_lbs)

        if max_gross and empty and empty >= max_gross:
            raise serializers.ValidationError({
                'empty_weight_lbs': "Empty weight must be less than max gross weight"
            })

        return attrs


class AircraftStatusSerializer(serializers.Serializer):
    """Serializer for aircraft status response."""

    aircraft_id = serializers.UUIDField()
    registration = serializers.CharField()
    status = serializers.CharField()
    operational_status = serializers.CharField()
    is_airworthy = serializers.BooleanField()
    is_available = serializers.BooleanField()
    is_grounded = serializers.BooleanField()
    grounded_reason = serializers.CharField(allow_null=True)

    # Counters
    hobbs_time = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_time_hours = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_landings = serializers.IntegerField()

    # Warnings and blockers
    warnings = serializers.ListField(child=serializers.DictField())
    blockers = serializers.ListField(child=serializers.DictField())

    # Squawk summary
    squawk_summary = serializers.DictField()

    # Certificate status
    certificates = serializers.DictField()


class AircraftAvailabilitySerializer(serializers.Serializer):
    """Serializer for availability check request."""

    start = serializers.DateTimeField(required=True)
    end = serializers.DateTimeField(required=True)

    def validate(self, attrs):
        if attrs['start'] >= attrs['end']:
            raise serializers.ValidationError({
                'end': "End time must be after start time"
            })
        return attrs


class GroundAircraftSerializer(serializers.Serializer):
    """Serializer for grounding an aircraft."""

    reason = serializers.CharField(
        required=True,
        min_length=10,
        max_length=1000,
        help_text="Reason for grounding the aircraft"
    )

    def validate_reason(self, value):
        if len(value.strip()) < 10:
            raise serializers.ValidationError(
                "Grounding reason must be at least 10 characters"
            )
        return value.strip()
