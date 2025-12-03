# services/flight-service/src/apps/api/serializers/fuel_serializers.py
"""
Fuel and Oil Record Serializers

REST API serializers for fuel and oil record operations.
"""

from decimal import Decimal
from rest_framework import serializers

from apps.core.models import FuelRecord, OilRecord


class FuelRecordSerializer(serializers.ModelSerializer):
    """Serializer for fuel records."""

    total_tank_reading = serializers.DecimalField(
        max_digits=8, decimal_places=2, read_only=True
    )
    record_type_display = serializers.CharField(
        source='get_record_type_display', read_only=True
    )
    fuel_type_display = serializers.CharField(
        source='get_fuel_type_display', read_only=True
    )

    class Meta:
        model = FuelRecord
        fields = [
            'id',
            'flight_id',
            'organization_id',
            'aircraft_id',
            'record_type',
            'record_type_display',
            'recorded_at',
            'fuel_type',
            'fuel_type_display',
            'quantity_liters',
            'quantity_gallons',
            'left_tank_liters',
            'right_tank_liters',
            'aux_tank_liters',
            'total_tank_reading',
            'price_per_liter',
            'total_cost',
            'currency',
            'location_icao',
            'fbo_name',
            'receipt_number',
            'receipt_image_url',
            'notes',
            'created_at',
            'created_by',
        ]
        read_only_fields = [
            'id',
            'flight_id',
            'organization_id',
            'aircraft_id',
            'quantity_gallons',
            'total_cost',
            'created_at',
            'created_by',
        ]


class FuelRecordCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating fuel records."""

    class Meta:
        model = FuelRecord
        fields = [
            'record_type',
            'recorded_at',
            'fuel_type',
            'quantity_liters',
            'left_tank_liters',
            'right_tank_liters',
            'aux_tank_liters',
            'price_per_liter',
            'currency',
            'location_icao',
            'fbo_name',
            'receipt_number',
            'receipt_image_url',
            'notes',
        ]

    def validate_quantity_liters(self, value):
        """Validate quantity is positive."""
        if value is not None and value <= 0:
            raise serializers.ValidationError(
                "Quantity must be greater than zero."
            )
        return value

    def validate_price_per_liter(self, value):
        """Validate price is non-negative."""
        if value is not None and value < 0:
            raise serializers.ValidationError(
                "Price cannot be negative."
            )
        return value

    def validate_location_icao(self, value):
        """Validate ICAO code format."""
        if value:
            value = value.upper()
            if len(value) != 4:
                raise serializers.ValidationError(
                    "ICAO code must be exactly 4 characters."
                )
        return value

    def validate(self, data):
        """Cross-field validation."""
        # If tank readings provided, validate they're reasonable
        tank_fields = ['left_tank_liters', 'right_tank_liters', 'aux_tank_liters']
        total_from_tanks = Decimal('0')

        for field in tank_fields:
            value = data.get(field)
            if value is not None:
                if value < 0:
                    raise serializers.ValidationError({
                        field: f"{field} cannot be negative."
                    })
                total_from_tanks += value

        # For preflight/postflight, quantity should match tank total if provided
        if data.get('record_type') in ['preflight', 'postflight']:
            if total_from_tanks > 0 and data.get('quantity_liters'):
                if abs(total_from_tanks - data['quantity_liters']) > Decimal('1'):
                    raise serializers.ValidationError({
                        'quantity_liters': (
                            "Quantity should match sum of tank readings "
                            f"({total_from_tanks}L) for {data['record_type']} records."
                        )
                    })

        return data


class FuelRecordUpdateSerializer(FuelRecordCreateSerializer):
    """Serializer for updating fuel records."""

    class Meta(FuelRecordCreateSerializer.Meta):
        extra_kwargs = {
            field: {'required': False}
            for field in FuelRecordCreateSerializer.Meta.fields
        }


class OilRecordSerializer(serializers.ModelSerializer):
    """Serializer for oil records."""

    class Meta:
        model = OilRecord
        fields = [
            'id',
            'flight_id',
            'organization_id',
            'aircraft_id',
            'oil_type',
            'quantity_liters',
            'quantity_quarts',
            'oil_level_after',
            'cost',
            'recorded_at',
            'notes',
            'created_at',
            'created_by',
        ]
        read_only_fields = [
            'id',
            'flight_id',
            'organization_id',
            'aircraft_id',
            'quantity_quarts',
            'created_at',
            'created_by',
        ]


class OilRecordCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating oil records."""

    class Meta:
        model = OilRecord
        fields = [
            'oil_type',
            'quantity_liters',
            'oil_level_after',
            'cost',
            'recorded_at',
            'notes',
        ]

    def validate_quantity_liters(self, value):
        """Validate quantity is positive."""
        if value is not None and value <= 0:
            raise serializers.ValidationError(
                "Quantity must be greater than zero."
            )
        return value

    def validate_cost(self, value):
        """Validate cost is non-negative."""
        if value is not None and value < 0:
            raise serializers.ValidationError(
                "Cost cannot be negative."
            )
        return value


class FuelStatisticsSerializer(serializers.Serializer):
    """Serializer for fuel statistics."""

    aircraft_id = serializers.UUIDField()
    period = serializers.DictField()
    summary = serializers.DictField()
    by_location = serializers.ListField(
        child=serializers.DictField()
    )
    by_fuel_type = serializers.ListField(
        child=serializers.DictField()
    )
    monthly_trend = serializers.ListField(
        child=serializers.DictField()
    )
