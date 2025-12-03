# services/organization-service/src/apps/core/serializers/location.py
"""
Location Serializers

Serializers for location management API endpoints.
"""

from rest_framework import serializers
from apps.core.models import Location


class LocationSerializer(serializers.ModelSerializer):
    """Full location serializer with all details."""

    organization_name = serializers.CharField(
        source='organization.name',
        read_only=True
    )
    effective_timezone = serializers.CharField(read_only=True)
    coordinates = serializers.DictField(read_only=True)
    full_address = serializers.CharField(read_only=True)

    class Meta:
        model = Location
        fields = [
            'id',
            'organization',
            'organization_name',
            'name',
            'code',
            'description',
            'location_type',
            'airport_icao',
            'airport_iata',
            'airport_name',
            'email',
            'phone',
            'address_line1',
            'address_line2',
            'city',
            'state_province',
            'postal_code',
            'country_code',
            'latitude',
            'longitude',
            'elevation_ft',
            'coordinates',
            'full_address',
            'is_primary',
            'is_active',
            'operating_hours',
            'timezone',
            'effective_timezone',
            'facilities',
            'runways',
            'frequencies',
            'weather_station_id',
            'notes',
            'pilot_notes',
            'photo_url',
            'metadata',
            'display_order',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'organization', 'created_at', 'updated_at']


class LocationListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for location lists."""

    class Meta:
        model = Location
        fields = [
            'id',
            'name',
            'code',
            'location_type',
            'airport_icao',
            'city',
            'country_code',
            'is_primary',
            'is_active',
            'display_order',
        ]


class LocationCreateSerializer(serializers.Serializer):
    """Serializer for creating locations."""

    name = serializers.CharField(max_length=255)
    code = serializers.CharField(max_length=20, required=False, allow_blank=True)
    description = serializers.CharField(required=False, allow_blank=True)
    location_type = serializers.ChoiceField(
        choices=Location.LocationType.choices,
        default='base'
    )
    airport_icao = serializers.RegexField(
        regex=r'^[A-Z]{4}$',
        required=False,
        allow_blank=True,
        error_messages={'invalid': 'Must be 4 uppercase letters'}
    )
    airport_iata = serializers.RegexField(
        regex=r'^[A-Z]{3}$',
        required=False,
        allow_blank=True,
        error_messages={'invalid': 'Must be 3 uppercase letters'}
    )
    airport_name = serializers.CharField(max_length=255, required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    phone = serializers.CharField(max_length=50, required=False, allow_blank=True)
    address_line1 = serializers.CharField(max_length=255, required=False, allow_blank=True)
    address_line2 = serializers.CharField(max_length=255, required=False, allow_blank=True)
    city = serializers.CharField(max_length=100, required=False, allow_blank=True)
    state_province = serializers.CharField(max_length=100, required=False, allow_blank=True)
    postal_code = serializers.CharField(max_length=20, required=False, allow_blank=True)
    country_code = serializers.CharField(max_length=2, required=False, allow_blank=True)
    latitude = serializers.DecimalField(
        max_digits=10, decimal_places=8, required=False, allow_null=True
    )
    longitude = serializers.DecimalField(
        max_digits=11, decimal_places=8, required=False, allow_null=True
    )
    elevation_ft = serializers.IntegerField(required=False, allow_null=True)
    is_primary = serializers.BooleanField(default=False)
    timezone = serializers.CharField(max_length=50, required=False, allow_blank=True)
    operating_hours = serializers.JSONField(required=False, default=dict)
    facilities = serializers.ListField(
        child=serializers.CharField(max_length=50),
        required=False,
        default=list
    )
    weather_station_id = serializers.CharField(max_length=50, required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)
    pilot_notes = serializers.CharField(required=False, allow_blank=True)
    photo_url = serializers.URLField(max_length=500, required=False, allow_blank=True)

    def validate_airport_icao(self, value):
        if value:
            return value.upper()
        return value

    def validate_airport_iata(self, value):
        if value:
            return value.upper()
        return value

    def validate_country_code(self, value):
        if value:
            return value.upper()
        return value


class LocationUpdateSerializer(serializers.Serializer):
    """Serializer for updating locations."""

    name = serializers.CharField(max_length=255, required=False)
    code = serializers.CharField(max_length=20, required=False, allow_blank=True)
    description = serializers.CharField(required=False, allow_blank=True)
    location_type = serializers.ChoiceField(
        choices=Location.LocationType.choices,
        required=False
    )
    airport_icao = serializers.RegexField(
        regex=r'^[A-Z]{4}$',
        required=False,
        allow_blank=True,
        error_messages={'invalid': 'Must be 4 uppercase letters'}
    )
    airport_iata = serializers.RegexField(
        regex=r'^[A-Z]{3}$',
        required=False,
        allow_blank=True,
        error_messages={'invalid': 'Must be 3 uppercase letters'}
    )
    airport_name = serializers.CharField(max_length=255, required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    phone = serializers.CharField(max_length=50, required=False, allow_blank=True)
    address_line1 = serializers.CharField(max_length=255, required=False, allow_blank=True)
    address_line2 = serializers.CharField(max_length=255, required=False, allow_blank=True)
    city = serializers.CharField(max_length=100, required=False, allow_blank=True)
    state_province = serializers.CharField(max_length=100, required=False, allow_blank=True)
    postal_code = serializers.CharField(max_length=20, required=False, allow_blank=True)
    country_code = serializers.CharField(max_length=2, required=False, allow_blank=True)
    latitude = serializers.DecimalField(
        max_digits=10, decimal_places=8, required=False, allow_null=True
    )
    longitude = serializers.DecimalField(
        max_digits=11, decimal_places=8, required=False, allow_null=True
    )
    elevation_ft = serializers.IntegerField(required=False, allow_null=True)
    is_active = serializers.BooleanField(required=False)
    timezone = serializers.CharField(max_length=50, required=False, allow_blank=True)
    operating_hours = serializers.JSONField(required=False)
    facilities = serializers.ListField(
        child=serializers.CharField(max_length=50),
        required=False
    )
    runways = serializers.JSONField(required=False)
    frequencies = serializers.JSONField(required=False)
    weather_station_id = serializers.CharField(max_length=50, required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)
    pilot_notes = serializers.CharField(required=False, allow_blank=True)
    photo_url = serializers.URLField(max_length=500, required=False, allow_blank=True)
    metadata = serializers.JSONField(required=False)
    display_order = serializers.IntegerField(required=False)


class LocationOperatingHoursSerializer(serializers.Serializer):
    """Serializer for operating hours."""

    monday = serializers.DictField(required=False)
    tuesday = serializers.DictField(required=False)
    wednesday = serializers.DictField(required=False)
    thursday = serializers.DictField(required=False)
    friday = serializers.DictField(required=False)
    saturday = serializers.DictField(required=False)
    sunday = serializers.DictField(required=False)
    holidays = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        default=list
    )


class LocationWeatherSerializer(serializers.Serializer):
    """Serializer for weather information."""

    icao = serializers.CharField(read_only=True)
    metar = serializers.CharField(read_only=True, allow_null=True)
    taf = serializers.CharField(read_only=True, allow_null=True)
    fetched_at = serializers.DateTimeField(read_only=True)
    source = serializers.CharField(read_only=True)
