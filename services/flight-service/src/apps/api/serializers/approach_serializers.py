# services/flight-service/src/apps/api/serializers/approach_serializers.py
"""
Approach and Hold Serializers

REST API serializers for approach and holding pattern records.
"""

from rest_framework import serializers

from apps.core.models import Approach, Hold


class ApproachSerializer(serializers.ModelSerializer):
    """Serializer for approach records."""

    display_name = serializers.CharField(read_only=True)
    counts_for_currency = serializers.BooleanField(read_only=True)
    approach_type_display = serializers.CharField(
        source='get_approach_type_display', read_only=True
    )
    result_display = serializers.CharField(
        source='get_result_display', read_only=True
    )

    class Meta:
        model = Approach
        fields = [
            'id',
            'flight_id',
            'organization_id',
            'approach_type',
            'approach_type_display',
            'airport_icao',
            'runway',
            'result',
            'result_display',
            'in_imc',
            'to_minimums',
            'lowest_altitude',
            'coupled',
            'hand_flown',
            'flight_director',
            'under_hood',
            'safety_pilot_id',
            'sequence_number',
            'notes',
            'executed_at',
            'display_name',
            'counts_for_currency',
            'created_at',
        ]
        read_only_fields = [
            'id',
            'flight_id',
            'organization_id',
            'sequence_number',
            'created_at',
        ]


class ApproachCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating approach records."""

    class Meta:
        model = Approach
        fields = [
            'approach_type',
            'airport_icao',
            'runway',
            'result',
            'in_imc',
            'to_minimums',
            'lowest_altitude',
            'coupled',
            'hand_flown',
            'flight_director',
            'under_hood',
            'safety_pilot_id',
            'notes',
            'executed_at',
        ]

    def validate_airport_icao(self, value):
        """Validate ICAO code format."""
        if value:
            value = value.upper()
            if len(value) != 4:
                raise serializers.ValidationError(
                    "ICAO code must be exactly 4 characters."
                )
        return value

    def validate_runway(self, value):
        """Validate runway designator."""
        if value:
            value = value.upper()
            # Basic validation for runway format (e.g., 05, 27L, 09R, 18C)
            import re
            if not re.match(r'^[0-3][0-9][LRC]?$', value):
                raise serializers.ValidationError(
                    "Invalid runway designator format."
                )
        return value

    def validate(self, data):
        """Cross-field validation."""
        # If under_hood, safety_pilot should be provided
        if data.get('under_hood') and not data.get('safety_pilot_id'):
            raise serializers.ValidationError({
                'safety_pilot_id': "Safety pilot is required when under hood."
            })

        # Coupled and hand_flown are mutually exclusive (mostly)
        if data.get('coupled') and data.get('hand_flown'):
            # This is technically possible (hand flying after disconnect)
            # but typically one or the other
            pass

        return data


class ApproachBulkCreateSerializer(serializers.Serializer):
    """Serializer for bulk approach creation."""

    approaches = serializers.ListField(
        child=ApproachCreateSerializer(),
        min_length=1,
        max_length=20
    )


class HoldSerializer(serializers.ModelSerializer):
    """Serializer for holding pattern records."""

    class Meta:
        model = Hold
        fields = [
            'id',
            'flight_id',
            'organization_id',
            'fix_name',
            'fix_type',
            'entry_type',
            'turns',
            'altitude',
            'duration_minutes',
            'published',
            'in_imc',
            'notes',
            'executed_at',
            'created_at',
        ]
        read_only_fields = [
            'id',
            'flight_id',
            'organization_id',
            'created_at',
        ]


class HoldCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating holding pattern records."""

    class Meta:
        model = Hold
        fields = [
            'fix_name',
            'fix_type',
            'entry_type',
            'turns',
            'altitude',
            'duration_minutes',
            'published',
            'in_imc',
            'notes',
            'executed_at',
        ]

    def validate_fix_name(self, value):
        """Validate fix name."""
        if value:
            value = value.upper()
        return value

    def validate_entry_type(self, value):
        """Validate entry type."""
        if value:
            valid_entries = ['direct', 'teardrop', 'parallel']
            if value.lower() not in valid_entries:
                raise serializers.ValidationError(
                    f"Entry type must be one of: {', '.join(valid_entries)}"
                )
            return value.lower()
        return value

    def validate_turns(self, value):
        """Validate turn count."""
        if value is not None and value < 1:
            raise serializers.ValidationError(
                "Turns must be at least 1."
            )
        return value


class ApproachStatisticsSerializer(serializers.Serializer):
    """Serializer for approach statistics."""

    total_approaches = serializers.IntegerField()
    imc_approaches = serializers.IntegerField()
    to_minimums = serializers.IntegerField()
    by_type = serializers.ListField(
        child=serializers.DictField()
    )
    by_airport = serializers.ListField(
        child=serializers.DictField()
    )
