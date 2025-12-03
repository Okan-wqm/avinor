"""Booking Service Serializers."""
from rest_framework import serializers
from .models import Booking, BookingResource, Schedule, WaitlistEntry


class BookingResourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = BookingResource
        fields = '__all__'


class BookingSerializer(serializers.ModelSerializer):
    resources = BookingResourceSerializer(many=True, read_only=True)
    duration_hours = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Booking
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class BookingListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Booking
        fields = ['id', 'booking_type', 'status', 'aircraft_id', 'pilot_id',
                  'instructor_id', 'start_time', 'end_time', 'title']


class BookingCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Booking
        fields = ['organization_id', 'aircraft_id', 'pilot_id', 'instructor_id',
                  'booking_type', 'start_time', 'end_time', 'title', 'description',
                  'departure_airport', 'destination_airport', 'route', 'lesson_id', 'notes']

    def validate(self, data):
        if data['end_time'] <= data['start_time']:
            raise serializers.ValidationError("End time must be after start time")
        return data


class ScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Schedule
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class WaitlistEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = WaitlistEntry
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']
