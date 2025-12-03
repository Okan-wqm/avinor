"""Flight Service Serializers."""
from rest_framework import serializers
from .models import Flight, FlightTrack, LogbookEntry, PilotTotals


class FlightSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    flight_type_display = serializers.CharField(source='get_flight_type_display', read_only=True)

    class Meta:
        model = Flight
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class FlightListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Flight
        fields = ['id', 'flight_type', 'status', 'aircraft_id', 'pic_id',
                  'departure_airport', 'arrival_airport', 'actual_departure',
                  'flight_time', 'landings_day', 'landings_night']


class FlightTrackSerializer(serializers.ModelSerializer):
    class Meta:
        model = FlightTrack
        fields = '__all__'


class LogbookEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = LogbookEntry
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class LogbookSummarySerializer(serializers.Serializer):
    """Summary of logbook for a period."""
    total_time = serializers.DecimalField(max_digits=10, decimal_places=2)
    pic_time = serializers.DecimalField(max_digits=10, decimal_places=2)
    dual_received = serializers.DecimalField(max_digits=10, decimal_places=2)
    cross_country = serializers.DecimalField(max_digits=10, decimal_places=2)
    night_time = serializers.DecimalField(max_digits=10, decimal_places=2)
    instrument_time = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_landings = serializers.IntegerField()
    flight_count = serializers.IntegerField()


class PilotTotalsSerializer(serializers.ModelSerializer):
    class Meta:
        model = PilotTotals
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at', 'pilot_id']
