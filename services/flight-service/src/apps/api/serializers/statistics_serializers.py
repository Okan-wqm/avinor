# services/flight-service/src/apps/api/serializers/statistics_serializers.py
"""
Statistics Serializers

REST API serializers for flight statistics and currency operations.
"""

from rest_framework import serializers


class TimeStatisticsSerializer(serializers.Serializer):
    """Serializer for time statistics."""

    total_time = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_pic = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_sic = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_dual_received = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_dual_given = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_solo = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_day = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_night = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_ifr = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_instrument = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_cross_country = serializers.DecimalField(max_digits=10, decimal_places=2)


class PilotStatisticsSerializer(serializers.Serializer):
    """Serializer for pilot statistics response."""

    user_id = serializers.UUIDField()
    period = serializers.DictField()
    summary = serializers.DictField()
    by_flight_type = serializers.ListField(
        child=serializers.DictField()
    )
    by_flight_rules = serializers.ListField(
        child=serializers.DictField()
    )
    by_aircraft = serializers.ListField(
        child=serializers.DictField()
    )
    top_departure_airports = serializers.ListField(
        child=serializers.DictField()
    )
    top_arrival_airports = serializers.ListField(
        child=serializers.DictField()
    )
    monthly_trend = serializers.ListField(
        child=serializers.DictField()
    )


class AircraftStatisticsSerializer(serializers.Serializer):
    """Serializer for aircraft statistics response."""

    aircraft_id = serializers.UUIDField()
    period = serializers.DictField()
    summary = serializers.DictField()
    by_flight_type = serializers.ListField(
        child=serializers.DictField()
    )
    by_pilot = serializers.ListField(
        child=serializers.DictField()
    )
    top_routes = serializers.ListField(
        child=serializers.DictField()
    )
    monthly_utilization = serializers.ListField(
        child=serializers.DictField()
    )
    last_flight = serializers.DictField(allow_null=True)


class OrganizationStatisticsSerializer(serializers.Serializer):
    """Serializer for organization statistics response."""

    organization_id = serializers.UUIDField()
    period = serializers.DictField()
    summary = serializers.DictField()
    by_flight_type = serializers.ListField(
        child=serializers.DictField()
    )
    by_aircraft = serializers.ListField(
        child=serializers.DictField()
    )
    by_pilot = serializers.ListField(
        child=serializers.DictField()
    )
    by_instructor = serializers.ListField(
        child=serializers.DictField()
    )
    top_routes = serializers.ListField(
        child=serializers.DictField()
    )
    monthly_trend = serializers.ListField(
        child=serializers.DictField()
    )


class TrainingStatisticsSerializer(serializers.Serializer):
    """Serializer for training statistics response."""

    organization_id = serializers.UUIDField()
    period = serializers.DictField()
    summary = serializers.DictField()
    by_training_type = serializers.ListField(
        child=serializers.DictField()
    )
    by_instructor = serializers.ListField(
        child=serializers.DictField()
    )
    by_student = serializers.ListField(
        child=serializers.DictField()
    )


class DashboardStatisticsSerializer(serializers.Serializer):
    """Serializer for dashboard statistics response."""

    organization_id = serializers.UUIDField()
    user_id = serializers.UUIDField(allow_null=True)
    generated_at = serializers.DateTimeField()
    last_30_days = serializers.DictField()
    last_7_days = serializers.DictField()
    pending = serializers.DictField()
    recent_flights = serializers.ListField(
        child=serializers.DictField()
    )


class CurrencyItemSerializer(serializers.Serializer):
    """Serializer for individual currency item."""

    type = serializers.CharField()
    status = serializers.CharField()
    current = serializers.IntegerField()
    required = serializers.IntegerField()
    period_days = serializers.IntegerField()
    expires_on = serializers.DateField(allow_null=True)
    days_remaining = serializers.IntegerField(allow_null=True)
    description = serializers.CharField(allow_null=True)


class CurrencyStatusSerializer(serializers.Serializer):
    """Serializer for pilot currency status response."""

    user_id = serializers.UUIDField()
    checked_at = serializers.DateTimeField()
    overall_status = serializers.CharField()
    currencies = serializers.ListField(
        child=CurrencyItemSerializer()
    )
    expired_count = serializers.IntegerField()
    expiring_soon_count = serializers.IntegerField()
    current_count = serializers.IntegerField()


class CurrencyValidationSerializer(serializers.Serializer):
    """Serializer for pre-flight currency validation response."""

    user_id = serializers.UUIDField()
    is_valid = serializers.BooleanField()
    warnings = serializers.ListField(
        child=serializers.CharField()
    )
    errors = serializers.ListField(
        child=serializers.CharField()
    )
    currency_checks = serializers.ListField(
        child=serializers.DictField()
    )


class CurrencyValidationRequestSerializer(serializers.Serializer):
    """Serializer for pre-flight currency validation request."""

    flight_type = serializers.CharField(required=True)
    flight_rules = serializers.ChoiceField(
        choices=['VFR', 'IFR', 'SVFR'],
        required=True
    )
    has_passengers = serializers.BooleanField(default=False)
    is_night = serializers.BooleanField(default=False)


class PeriodComparisonSerializer(serializers.Serializer):
    """Serializer for period comparison response."""

    organization_id = serializers.UUIDField()
    user_id = serializers.UUIDField(allow_null=True)
    period_1 = serializers.DictField()
    period_2 = serializers.DictField()
    changes = serializers.DictField()


class PeriodComparisonRequestSerializer(serializers.Serializer):
    """Serializer for period comparison request."""

    period_1_start = serializers.DateField(required=True)
    period_1_end = serializers.DateField(required=True)
    period_2_start = serializers.DateField(required=True)
    period_2_end = serializers.DateField(required=True)
    user_id = serializers.UUIDField(required=False)

    def validate(self, data):
        """Validate date ranges."""
        if data['period_1_end'] < data['period_1_start']:
            raise serializers.ValidationError({
                'period_1_end': "Period 1 end must be after start."
            })
        if data['period_2_end'] < data['period_2_start']:
            raise serializers.ValidationError({
                'period_2_end': "Period 2 end must be after start."
            })
        return data


class StatisticsFilterSerializer(serializers.Serializer):
    """Serializer for statistics filter parameters."""

    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)
    user_id = serializers.UUIDField(required=False)
    aircraft_id = serializers.UUIDField(required=False)
    flight_type = serializers.CharField(required=False)

    def validate(self, data):
        """Validate date range."""
        if data.get('start_date') and data.get('end_date'):
            if data['end_date'] < data['start_date']:
                raise serializers.ValidationError({
                    'end_date': "End date must be after start date."
                })
        return data
