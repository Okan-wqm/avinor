# services/flight-service/src/apps/api/serializers/logbook_serializers.py
"""
Logbook Serializers

REST API serializers for pilot logbook operations.
"""

from rest_framework import serializers

from apps.core.models import FlightCrewLog, PilotLogbookSummary


class FlightCrewLogSerializer(serializers.ModelSerializer):
    """Serializer for flight crew log entries."""

    total_landings = serializers.IntegerField(read_only=True)
    total_instrument_time = serializers.DecimalField(
        max_digits=5, decimal_places=2, read_only=True
    )
    is_signed = serializers.BooleanField(read_only=True)
    role_display = serializers.CharField(
        source='get_role_display', read_only=True
    )

    class Meta:
        model = FlightCrewLog
        fields = [
            'id',
            'flight_id',
            'organization_id',
            'user_id',
            'role',
            'role_display',
            'flight_time',
            'time_pic',
            'time_sic',
            'time_dual_received',
            'time_dual_given',
            'time_solo',
            'time_day',
            'time_night',
            'time_ifr',
            'time_actual_instrument',
            'time_simulated_instrument',
            'time_cross_country',
            'total_instrument_time',
            'landings_day',
            'landings_night',
            'full_stop_day',
            'full_stop_night',
            'total_landings',
            'approaches',
            'holds',
            'signature',
            'signed_at',
            'is_signed',
            'remarks',
            'endorsements',
            'training_items',
            'training_grade',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'flight_id',
            'organization_id',
            'user_id',
            'role',
            'created_at',
            'updated_at',
            'signed_at',
        ]


class FlightCrewLogUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating crew log entries."""

    class Meta:
        model = FlightCrewLog
        fields = [
            'remarks',
            'endorsements',
            'training_items',
            'training_grade',
        ]


class LogbookEntrySerializer(serializers.Serializer):
    """Serializer for logbook entries (combined flight + crew log data)."""

    flight_id = serializers.UUIDField()
    date = serializers.DateField()
    aircraft = serializers.CharField()
    aircraft_type = serializers.CharField()
    departure = serializers.CharField()
    arrival = serializers.CharField()
    route = serializers.CharField(allow_null=True)
    role = serializers.CharField()
    flight_time = serializers.DecimalField(max_digits=5, decimal_places=2)
    time_pic = serializers.DecimalField(max_digits=5, decimal_places=2)
    time_sic = serializers.DecimalField(max_digits=5, decimal_places=2)
    time_dual_received = serializers.DecimalField(max_digits=5, decimal_places=2)
    time_dual_given = serializers.DecimalField(max_digits=5, decimal_places=2)
    time_solo = serializers.DecimalField(max_digits=5, decimal_places=2)
    time_day = serializers.DecimalField(max_digits=5, decimal_places=2)
    time_night = serializers.DecimalField(max_digits=5, decimal_places=2)
    time_ifr = serializers.DecimalField(max_digits=5, decimal_places=2)
    time_actual_instrument = serializers.DecimalField(max_digits=5, decimal_places=2)
    time_simulated_instrument = serializers.DecimalField(max_digits=5, decimal_places=2)
    time_cross_country = serializers.DecimalField(max_digits=5, decimal_places=2)
    landings_day = serializers.IntegerField()
    landings_night = serializers.IntegerField()
    approaches = serializers.IntegerField()
    holds = serializers.IntegerField()
    remarks = serializers.CharField(allow_null=True)
    signed = serializers.BooleanField()
    signed_at = serializers.DateTimeField(allow_null=True)


class LogbookSummarySerializer(serializers.ModelSerializer):
    """Serializer for pilot logbook summary."""

    total_landings = serializers.IntegerField(read_only=True)
    total_instrument_time = serializers.DecimalField(
        max_digits=8, decimal_places=2, read_only=True
    )
    is_day_current = serializers.BooleanField(read_only=True)
    is_night_current = serializers.BooleanField(read_only=True)
    is_ifr_current = serializers.BooleanField(read_only=True)

    class Meta:
        model = PilotLogbookSummary
        fields = [
            'id',
            'organization_id',
            'user_id',
            # Totals
            'total_time',
            'total_pic',
            'total_sic',
            'total_dual_received',
            'total_dual_given',
            'total_solo',
            'total_day',
            'total_night',
            'total_ifr',
            'total_actual_instrument',
            'total_simulated_instrument',
            'total_cross_country',
            'total_instrument_time',
            # Landings
            'total_landings_day',
            'total_landings_night',
            'total_full_stop_day',
            'total_full_stop_night',
            'total_landings',
            # IFR
            'total_approaches',
            'total_holds',
            # Counts
            'total_flights',
            # Aircraft category times
            'time_single_engine_land',
            'time_single_engine_sea',
            'time_multi_engine_land',
            'time_multi_engine_sea',
            'time_helicopter',
            'time_glider',
            # Currency
            'landings_last_90_days',
            'night_landings_last_90_days',
            'ifr_approaches_last_6_months',
            'holds_last_6_months',
            'is_day_current',
            'is_night_current',
            'is_ifr_current',
            # Dates
            'last_flight_date',
            'last_currency_check',
            'last_updated',
            'created_at',
        ]
        read_only_fields = fields


class LogbookExportSerializer(serializers.Serializer):
    """Serializer for logbook export request."""

    format = serializers.ChoiceField(
        choices=['json', 'csv', 'pdf'],
        default='json'
    )
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)

    def validate(self, data):
        """Validate date range."""
        if data.get('start_date') and data.get('end_date'):
            if data['end_date'] < data['start_date']:
                raise serializers.ValidationError({
                    'end_date': "End date must be after start date."
                })
        return data


class LogbookExportResponseSerializer(serializers.Serializer):
    """Serializer for logbook export response."""

    pilot_id = serializers.UUIDField()
    organization_id = serializers.UUIDField()
    exported_at = serializers.DateTimeField()
    date_range = serializers.DictField()
    summary = serializers.DictField()
    entries = serializers.ListField(
        child=LogbookEntrySerializer()
    )


class LogbookRemarksSerializer(serializers.Serializer):
    """Serializer for updating logbook remarks."""

    remarks = serializers.CharField(
        max_length=2000,
        allow_blank=True,
        required=True
    )


class LogbookSignatureSerializer(serializers.Serializer):
    """Serializer for signing logbook entries."""

    signature_data = serializers.DictField(
        required=True,
        help_text="Signature data (SVG, base64 image, etc.)"
    )


class LogbookPaginatedSerializer(serializers.Serializer):
    """Serializer for paginated logbook response."""

    entries = serializers.ListField(child=LogbookEntrySerializer())
    total = serializers.IntegerField()
    page = serializers.IntegerField()
    page_size = serializers.IntegerField()
    total_pages = serializers.IntegerField()
    has_next = serializers.BooleanField()
    has_previous = serializers.BooleanField()
