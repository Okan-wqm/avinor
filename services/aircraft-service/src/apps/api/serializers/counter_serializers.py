# services/aircraft-service/src/apps/api/serializers/counter_serializers.py
"""
Counter Serializers

Serializers for aircraft counter and time tracking.
"""

from decimal import Decimal
from rest_framework import serializers

from apps.core.models import AircraftTimeLog


class CounterSerializer(serializers.Serializer):
    """Serializer for counter values."""

    aircraft_id = serializers.UUIDField()
    registration = serializers.CharField()

    # Primary counters
    hobbs_time = serializers.FloatField()
    tach_time = serializers.FloatField()
    total_time_hours = serializers.FloatField()
    total_landings = serializers.IntegerField()
    total_cycles = serializers.IntegerField()

    # Billing
    billing_time_source = serializers.CharField()

    # Engines
    engines = serializers.ListField(child=serializers.DictField())

    # Timestamps
    last_hobbs_update = serializers.DateTimeField(allow_null=True)
    updated_at = serializers.DateTimeField()


class CounterUpdateSerializer(serializers.Serializer):
    """Serializer for updating counters from a flight."""

    flight_id = serializers.UUIDField(required=True)
    hobbs_time = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=True,
        help_text="Hobbs time to add (hours)"
    )
    tach_time = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False, allow_null=True,
        help_text="Tach time to add (hours)"
    )
    landings = serializers.IntegerField(
        required=False, default=0,
        help_text="Number of landings"
    )
    cycles = serializers.IntegerField(
        required=False, default=0,
        help_text="Number of cycles"
    )
    flight_date = serializers.DateField(required=False)
    engine_times = serializers.DictField(
        child=serializers.DecimalField(max_digits=10, decimal_places=2),
        required=False,
        help_text="Engine-specific times: {1: 1.5, 2: 1.5}"
    )
    notes = serializers.CharField(
        max_length=1000, required=False, allow_blank=True
    )

    def validate_hobbs_time(self, value):
        if value < 0:
            raise serializers.ValidationError("Hobbs time cannot be negative")
        if value > 24:
            raise serializers.ValidationError("Hobbs time seems too high (>24 hours)")
        return value

    def validate_tach_time(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError("Tach time cannot be negative")
        return value

    def validate_landings(self, value):
        if value < 0:
            raise serializers.ValidationError("Landings cannot be negative")
        if value > 100:
            raise serializers.ValidationError("Landings seem too high (>100)")
        return value


class CounterAdjustmentSerializer(serializers.Serializer):
    """Serializer for manual counter adjustment."""

    field = serializers.ChoiceField(
        choices=[
            ('hobbs_time', 'Hobbs Time'),
            ('tach_time', 'Tach Time'),
            ('total_time_hours', 'Total Time'),
            ('total_landings', 'Total Landings'),
            ('total_cycles', 'Total Cycles'),
        ],
        required=True
    )
    new_value = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=True,
        help_text="New value for the counter"
    )
    reason = serializers.CharField(
        min_length=10, max_length=1000, required=True,
        help_text="Reason for the adjustment"
    )

    def validate_new_value(self, value):
        if value < 0:
            raise serializers.ValidationError("Counter value cannot be negative")
        return value

    def validate_reason(self, value):
        if len(value.strip()) < 10:
            raise serializers.ValidationError(
                "Adjustment reason must be at least 10 characters"
            )
        return value.strip()


class TimeLogSerializer(serializers.ModelSerializer):
    """Serializer for time log entries."""

    source_type_display = serializers.CharField(
        source='get_source_type_display', read_only=True
    )

    class Meta:
        model = AircraftTimeLog
        fields = [
            'id', 'aircraft',
            'source_type', 'source_type_display',
            'source_id', 'source_reference',
            'log_date',

            # Hobbs
            'hobbs_before', 'hobbs_after', 'hobbs_change',

            # Tach
            'tach_before', 'tach_after', 'tach_change',

            # Total time
            'total_time_before', 'total_time_after', 'total_time_change',

            # Landings/Cycles
            'landings_before', 'landings_after', 'landings_change',
            'cycles_before', 'cycles_after', 'cycles_change',

            # Engine times
            'engine_times',

            # Notes
            'notes', 'adjustment_reason',

            # Audit
            'created_at', 'created_by', 'created_by_name',
        ]
        read_only_fields = ['id', 'created_at']


class UtilizationStatsSerializer(serializers.Serializer):
    """Serializer for utilization statistics."""

    period = serializers.DictField()
    totals = serializers.DictField()
    averages = serializers.DictField()
    ranges = serializers.DictField()


class PeriodSummarySerializer(serializers.Serializer):
    """Serializer for period summary."""

    hobbs = serializers.FloatField()
    tach = serializers.FloatField()
    total_time = serializers.FloatField()
    landings = serializers.IntegerField()
    cycles = serializers.IntegerField()
    flight_count = serializers.IntegerField()
    period = serializers.DictField()


class BulkImportSerializer(serializers.Serializer):
    """Serializer for bulk counter import."""

    hobbs_time = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False
    )
    tach_time = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False
    )
    total_time_hours = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False
    )
    total_landings = serializers.IntegerField(required=False)
    total_cycles = serializers.IntegerField(required=False)
    import_date = serializers.DateField(required=False)
    notes = serializers.CharField(max_length=1000, required=False, allow_blank=True)

    def validate(self, attrs):
        if not any(k in attrs for k in ['hobbs_time', 'tach_time', 'total_time_hours',
                                          'total_landings', 'total_cycles']):
            raise serializers.ValidationError(
                "At least one counter value must be provided"
            )
        return attrs
