# services/aircraft-service/src/apps/api/serializers/engine_serializers.py
"""
Engine Serializers

Serializers for aircraft engine management.
"""

from rest_framework import serializers

from apps.core.models import AircraftEngine


class AircraftEngineSerializer(serializers.ModelSerializer):
    """Serializer for engine details."""

    engine_type_display = serializers.CharField(
        source='get_engine_type_display', read_only=True
    )
    hours_until_tbo = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True
    )
    tbo_percentage = serializers.DecimalField(
        max_digits=5, decimal_places=2, read_only=True
    )
    is_tbo_exceeded = serializers.BooleanField(read_only=True)
    is_calendar_tbo_exceeded = serializers.BooleanField(read_only=True)
    status = serializers.SerializerMethodField()

    class Meta:
        model = AircraftEngine
        fields = [
            'id', 'aircraft', 'position', 'engine_type', 'engine_type_display',
            'manufacturer', 'model', 'serial_number',
            'tsn', 'tso', 'tbo_hours', 'tbo_years', 'last_overhaul_date',
            'hours_until_tbo', 'tbo_percentage', 'is_tbo_exceeded',
            'is_calendar_tbo_exceeded',
            'horsepower', 'is_active', 'notes', 'status',
            'install_date', 'install_tsn',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'hours_until_tbo', 'tbo_percentage',
            'is_tbo_exceeded', 'is_calendar_tbo_exceeded',
            'created_at', 'updated_at',
        ]

    def get_status(self, obj):
        return obj.get_status()


class AircraftEngineCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating an engine."""

    class Meta:
        model = AircraftEngine
        fields = [
            'position', 'engine_type', 'manufacturer', 'model', 'serial_number',
            'tsn', 'tso', 'tbo_hours', 'tbo_years', 'last_overhaul_date',
            'horsepower', 'notes', 'install_date', 'install_tsn',
        ]

    def validate_position(self, value):
        """Validate engine position."""
        if value < 1 or value > 4:
            raise serializers.ValidationError(
                "Engine position must be between 1 and 4"
            )
        return value

    def validate(self, attrs):
        """Validate engine data."""
        # TSO should not exceed TSN
        tsn = attrs.get('tsn', 0)
        tso = attrs.get('tso', 0)

        if tso > tsn:
            raise serializers.ValidationError({
                'tso': "Time since overhaul cannot exceed total time"
            })

        return attrs


class AircraftEngineUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating an engine."""

    class Meta:
        model = AircraftEngine
        fields = [
            'engine_type', 'manufacturer', 'model', 'serial_number',
            'tbo_hours', 'tbo_years', 'horsepower', 'notes', 'is_active',
        ]


class EngineOverhaulSerializer(serializers.Serializer):
    """Serializer for recording an engine overhaul."""

    overhaul_date = serializers.DateField(required=True)
    overhaul_type = serializers.ChoiceField(
        choices=['major', 'top'],
        required=True,
        help_text="Type of overhaul: major or top"
    )
    overhaul_shop = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True
    )
    work_order_number = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True
    )
    new_tbo_hours = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        help_text="New TBO hours (if different from previous)"
    )
    notes = serializers.CharField(
        max_length=2000,
        required=False,
        allow_blank=True
    )

    def validate_overhaul_date(self, value):
        from datetime import date
        if value > date.today():
            raise serializers.ValidationError(
                "Overhaul date cannot be in the future"
            )
        return value
