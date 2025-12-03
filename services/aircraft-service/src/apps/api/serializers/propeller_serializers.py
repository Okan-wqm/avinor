# services/aircraft-service/src/apps/api/serializers/propeller_serializers.py
"""
Propeller Serializers

Serializers for aircraft propeller management.
"""

from rest_framework import serializers

from apps.core.models import AircraftPropeller


class AircraftPropellerSerializer(serializers.ModelSerializer):
    """Serializer for propeller details."""

    propeller_type_display = serializers.CharField(
        source='get_propeller_type_display', read_only=True
    )
    hours_until_tbo = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True
    )
    tbo_percentage = serializers.DecimalField(
        max_digits=5, decimal_places=2, read_only=True
    )
    is_tbo_exceeded = serializers.BooleanField(read_only=True)
    status = serializers.SerializerMethodField()

    class Meta:
        model = AircraftPropeller
        fields = [
            'id', 'aircraft', 'position', 'propeller_type', 'propeller_type_display',
            'manufacturer', 'model', 'serial_number', 'blade_count',
            'tsn', 'tso', 'tbo_hours', 'tbo_years', 'last_overhaul_date',
            'hours_until_tbo', 'tbo_percentage', 'is_tbo_exceeded',
            'is_active', 'notes', 'status',
            'install_date', 'install_tsn',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'hours_until_tbo', 'tbo_percentage', 'is_tbo_exceeded',
            'created_at', 'updated_at',
        ]

    def get_status(self, obj):
        return obj.get_status()


class AircraftPropellerCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a propeller."""

    class Meta:
        model = AircraftPropeller
        fields = [
            'position', 'propeller_type', 'manufacturer', 'model',
            'serial_number', 'blade_count',
            'tsn', 'tso', 'tbo_hours', 'tbo_years', 'last_overhaul_date',
            'notes', 'install_date', 'install_tsn',
        ]

    def validate_position(self, value):
        """Validate propeller position."""
        if value < 1 or value > 4:
            raise serializers.ValidationError(
                "Propeller position must be between 1 and 4"
            )
        return value

    def validate_blade_count(self, value):
        """Validate blade count."""
        if value < 2 or value > 6:
            raise serializers.ValidationError(
                "Blade count must be between 2 and 6"
            )
        return value

    def validate(self, attrs):
        """Validate propeller data."""
        tsn = attrs.get('tsn', 0)
        tso = attrs.get('tso', 0)

        if tso > tsn:
            raise serializers.ValidationError({
                'tso': "Time since overhaul cannot exceed total time"
            })

        return attrs
