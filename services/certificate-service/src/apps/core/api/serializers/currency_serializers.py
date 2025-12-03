# services/certificate-service/src/apps/core/api/serializers/currency_serializers.py
"""
Currency Serializers

API serializers for currency tracking and requirements.
"""

from rest_framework import serializers

from ...models import (
    CurrencyRequirement,
    UserCurrencyStatus,
    CurrencyType,
    CurrencyStatus,
)


class CurrencyRequirementSerializer(serializers.ModelSerializer):
    """Full currency requirement serializer."""

    currency_type_display = serializers.CharField(
        source='get_currency_type_display',
        read_only=True
    )
    applicable_ratings_list = serializers.ListField(
        source='get_applicable_ratings_list',
        read_only=True
    )

    class Meta:
        model = CurrencyRequirement
        fields = [
            'id',
            'organization_id',
            'currency_type',
            'currency_type_display',
            'name',
            'description',
            'regulatory_reference',
            'authority',
            'required_takeoffs',
            'required_landings',
            'required_night_takeoffs',
            'required_night_landings',
            'required_instrument_approaches',
            'required_holding_procedures',
            'required_intercepting_tracking',
            'required_flight_hours',
            'required_pic_hours',
            'required_dual_hours',
            'required_sim_hours',
            'lookback_days',
            'grace_period_days',
            'applicable_certificate_types',
            'applicable_ratings',
            'applicable_ratings_list',
            'aircraft_category',
            'aircraft_class',
            'aircraft_type_specific',
            'is_active',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'organization_id',
            'created_at',
            'updated_at',
        ]


class CurrencyRequirementCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating currency requirements."""

    class Meta:
        model = CurrencyRequirement
        fields = [
            'currency_type',
            'name',
            'description',
            'regulatory_reference',
            'authority',
            'required_takeoffs',
            'required_landings',
            'required_night_takeoffs',
            'required_night_landings',
            'required_instrument_approaches',
            'required_holding_procedures',
            'required_intercepting_tracking',
            'required_flight_hours',
            'required_pic_hours',
            'required_dual_hours',
            'required_sim_hours',
            'lookback_days',
            'grace_period_days',
            'applicable_certificate_types',
            'applicable_ratings',
            'aircraft_category',
            'aircraft_class',
            'aircraft_type_specific',
            'is_active',
        ]

    def validate_currency_type(self, value):
        """Validate currency type."""
        if value not in CurrencyType.values:
            raise serializers.ValidationError(
                f'Invalid currency type. Must be one of: {CurrencyType.values}'
            )
        return value

    def validate(self, attrs):
        """Cross-field validation."""
        currency_type = attrs.get('currency_type')

        # Validate appropriate fields are set for currency type
        if currency_type == CurrencyType.TAKEOFF_LANDING:
            if not attrs.get('required_takeoffs') and not attrs.get('required_landings'):
                raise serializers.ValidationError({
                    'required_takeoffs': 'Takeoff/landing currency requires takeoff or landing count'
                })

        if currency_type == CurrencyType.NIGHT:
            if not attrs.get('required_night_takeoffs') and not attrs.get('required_night_landings'):
                raise serializers.ValidationError({
                    'required_night_takeoffs': 'Night currency requires night takeoff or landing count'
                })

        if currency_type == CurrencyType.INSTRUMENT:
            has_ifr_req = (
                attrs.get('required_instrument_approaches') or
                attrs.get('required_holding_procedures') or
                attrs.get('required_intercepting_tracking')
            )
            if not has_ifr_req:
                raise serializers.ValidationError({
                    'required_instrument_approaches': 'Instrument currency requires IFR activity requirements'
                })

        return attrs


class CurrencyRequirementListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for currency requirement lists."""

    currency_type_display = serializers.CharField(
        source='get_currency_type_display',
        read_only=True
    )

    class Meta:
        model = CurrencyRequirement
        fields = [
            'id',
            'currency_type',
            'currency_type_display',
            'name',
            'regulatory_reference',
            'authority',
            'lookback_days',
            'is_active',
        ]


class UserCurrencyStatusSerializer(serializers.ModelSerializer):
    """Full user currency status serializer."""

    requirement_name = serializers.CharField(
        source='requirement.name',
        read_only=True
    )
    currency_type = serializers.CharField(
        source='requirement.currency_type',
        read_only=True
    )
    currency_type_display = serializers.CharField(
        source='requirement.get_currency_type_display',
        read_only=True
    )
    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )
    is_current = serializers.BooleanField(read_only=True)
    is_expiring_soon = serializers.BooleanField(read_only=True)
    days_until_expiry = serializers.IntegerField(read_only=True)
    completion_percentage = serializers.IntegerField(read_only=True)
    missing_items = serializers.DictField(read_only=True)

    class Meta:
        model = UserCurrencyStatus
        fields = [
            'id',
            'organization_id',
            'user_id',
            'requirement',
            'requirement_name',
            'currency_type',
            'currency_type_display',
            'aircraft_type_id',
            'aircraft_icao',
            'status',
            'status_display',
            'current_takeoffs',
            'current_landings',
            'current_night_takeoffs',
            'current_night_landings',
            'current_instrument_approaches',
            'current_holding_procedures',
            'current_intercepting_tracking',
            'current_flight_hours',
            'current_pic_hours',
            'current_dual_hours',
            'current_sim_hours',
            'period_start_date',
            'expiry_date',
            'grace_expiry_date',
            'last_activity_date',
            'last_calculated_at',
            'flight_ids',
            'notes',
            'is_current',
            'is_expiring_soon',
            'days_until_expiry',
            'completion_percentage',
            'missing_items',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'organization_id',
            'created_at',
            'updated_at',
        ]


class UserCurrencyStatusListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for user currency status lists."""

    requirement_name = serializers.CharField(
        source='requirement.name',
        read_only=True
    )
    currency_type = serializers.CharField(
        source='requirement.currency_type',
        read_only=True
    )
    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )
    is_current = serializers.BooleanField(read_only=True)
    days_until_expiry = serializers.IntegerField(read_only=True)
    completion_percentage = serializers.IntegerField(read_only=True)

    class Meta:
        model = UserCurrencyStatus
        fields = [
            'id',
            'user_id',
            'requirement',
            'requirement_name',
            'currency_type',
            'aircraft_icao',
            'status',
            'status_display',
            'expiry_date',
            'is_current',
            'days_until_expiry',
            'completion_percentage',
        ]


class CurrencyCheckSerializer(serializers.Serializer):
    """Serializer for currency check request."""

    user_id = serializers.UUIDField()
    currency_type = serializers.ChoiceField(
        choices=CurrencyType.choices,
        required=False
    )
    aircraft_type = serializers.CharField(required=False)


class CurrencyCheckResponseSerializer(serializers.Serializer):
    """Serializer for currency check response."""

    is_current = serializers.BooleanField()
    message = serializers.CharField()
    currency_statuses = serializers.ListField(
        child=serializers.DictField()
    )
    deficiencies = serializers.ListField(
        child=serializers.DictField(),
        required=False
    )


class CurrencyUpdateSerializer(serializers.Serializer):
    """Serializer for updating currency from flight data."""

    user_id = serializers.UUIDField()
    flight_id = serializers.UUIDField()
    flight_date = serializers.DateField()
    aircraft_type = serializers.CharField()
    aircraft_icao = serializers.CharField(required=False)

    # Flight counts
    takeoffs = serializers.IntegerField(default=0)
    landings = serializers.IntegerField(default=0)
    night_takeoffs = serializers.IntegerField(default=0)
    night_landings = serializers.IntegerField(default=0)

    # IFR activities
    instrument_approaches = serializers.IntegerField(default=0)
    holding_procedures = serializers.IntegerField(default=0)
    intercepting_tracking = serializers.IntegerField(default=0)

    # Flight hours
    total_time = serializers.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0
    )
    pic_time = serializers.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0
    )
    dual_time = serializers.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0
    )
    sim_time = serializers.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0
    )


class CurrencyBatchUpdateSerializer(serializers.Serializer):
    """Serializer for batch currency updates."""

    user_id = serializers.UUIDField()
    flights = CurrencyUpdateSerializer(many=True)


class CurrencySummarySerializer(serializers.Serializer):
    """Serializer for user currency summary."""

    user_id = serializers.UUIDField()
    overall_current = serializers.BooleanField()
    total_requirements = serializers.IntegerField()
    current_count = serializers.IntegerField()
    expiring_soon_count = serializers.IntegerField()
    expired_count = serializers.IntegerField()
    currency_statuses = UserCurrencyStatusListSerializer(many=True)
    recommendations = serializers.ListField(
        child=serializers.DictField()
    )


class FlightCurrencyImpactSerializer(serializers.Serializer):
    """Serializer for flight currency impact analysis."""

    flight_id = serializers.UUIDField()
    user_id = serializers.UUIDField()
    affected_currencies = serializers.ListField(
        child=serializers.DictField()
    )
    new_expiry_dates = serializers.DictField()
    requirements_met = serializers.ListField(
        child=serializers.CharField()
    )
    requirements_still_needed = serializers.ListField(
        child=serializers.DictField()
    )
