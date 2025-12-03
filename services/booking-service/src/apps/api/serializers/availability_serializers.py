# services/booking-service/src/apps/api/serializers/availability_serializers.py
"""
Availability Serializers

Serializers for availability and operating hours management.
"""

from datetime import date, time, datetime
from rest_framework import serializers
from django.utils import timezone

from apps.core.models import Availability
from apps.core.models.availability import OperatingHours


class AvailabilitySerializer(serializers.ModelSerializer):
    """Base availability serializer."""

    availability_type_display = serializers.CharField(
        source='get_availability_type_display',
        read_only=True
    )
    resource_type_display = serializers.CharField(
        source='get_resource_type_display',
        read_only=True
    )
    duration_hours = serializers.SerializerMethodField()
    is_current = serializers.SerializerMethodField()

    class Meta:
        model = Availability
        fields = [
            'id', 'organization_id',
            'resource_type', 'resource_type_display',
            'resource_id',
            'availability_type', 'availability_type_display',
            'start_datetime', 'end_datetime',
            'duration_hours', 'is_current',
            'reason', 'notes',
            'is_recurring', 'recurrence_rule',
            'max_bookings', 'current_bookings',
            'booking_types_allowed',
            'created_by', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'current_bookings',
            'created_at', 'updated_at',
        ]

    def get_duration_hours(self, obj) -> float:
        """Get duration in hours."""
        if obj.start_datetime and obj.end_datetime:
            delta = obj.end_datetime - obj.start_datetime
            return round(delta.total_seconds() / 3600, 1)
        return 0

    def get_is_current(self, obj) -> bool:
        """Check if availability is currently active."""
        now = timezone.now()
        return obj.start_datetime <= now <= obj.end_datetime


class AvailabilityListSerializer(AvailabilitySerializer):
    """Optimized serializer for availability lists."""

    class Meta(AvailabilitySerializer.Meta):
        fields = [
            'id', 'resource_type', 'resource_id',
            'availability_type', 'availability_type_display',
            'start_datetime', 'end_datetime',
            'duration_hours', 'is_current',
            'reason',
        ]


class AvailabilityDetailSerializer(AvailabilitySerializer):
    """Detailed availability serializer."""

    affected_bookings = serializers.SerializerMethodField()

    class Meta(AvailabilitySerializer.Meta):
        fields = AvailabilitySerializer.Meta.fields + [
            'affected_bookings',
        ]

    def get_affected_bookings(self, obj) -> list:
        """Get bookings affected by this availability block."""
        if obj.availability_type != Availability.AvailabilityType.UNAVAILABLE:
            return []

        from apps.core.models import Booking

        filters = {
            'organization_id': obj.organization_id,
            'scheduled_start__lt': obj.end_datetime,
            'scheduled_end__gt': obj.start_datetime,
        }

        if obj.resource_type == 'aircraft':
            filters['aircraft_id'] = obj.resource_id
        elif obj.resource_type == 'instructor':
            filters['instructor_id'] = obj.resource_id

        bookings = Booking.objects.filter(**filters).exclude(
            status__in=[Booking.Status.CANCELLED, Booking.Status.DRAFT]
        )

        return [
            {
                'id': str(b.id),
                'booking_number': b.booking_number,
                'scheduled_start': b.scheduled_start.isoformat(),
                'scheduled_end': b.scheduled_end.isoformat(),
                'status': b.status,
            }
            for b in bookings[:20]
        ]


class AvailabilityCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating availability entries."""

    notify_affected = serializers.BooleanField(
        default=True,
        write_only=True,
        help_text="Notify users with affected bookings"
    )

    class Meta:
        model = Availability
        fields = [
            'organization_id',
            'resource_type', 'resource_id',
            'availability_type',
            'start_datetime', 'end_datetime',
            'reason', 'notes',
            'is_recurring', 'recurrence_rule',
            'max_bookings', 'booking_types_allowed',
            'notify_affected',
        ]

    def validate(self, attrs):
        """Validate availability data."""
        start = attrs.get('start_datetime')
        end = attrs.get('end_datetime')

        if start and end:
            if end <= start:
                raise serializers.ValidationError({
                    'end_datetime': "End time must be after start time"
                })

            # Don't allow very long unavailability blocks without confirmation
            duration_days = (end - start).days
            if duration_days > 30 and attrs.get('availability_type') == Availability.AvailabilityType.UNAVAILABLE:
                if not self.context.get('confirm_long_block'):
                    raise serializers.ValidationError({
                        'end_datetime': f"Unavailability block of {duration_days} days is very long. "
                                       "Confirm this is intentional."
                    })

        # Validate resource type
        resource_type = attrs.get('resource_type')
        if resource_type not in ['aircraft', 'instructor', 'location', 'student']:
            raise serializers.ValidationError({
                'resource_type': "Invalid resource type"
            })

        return attrs


class AvailabilityUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating availability entries."""

    class Meta:
        model = Availability
        fields = [
            'availability_type',
            'start_datetime', 'end_datetime',
            'reason', 'notes',
            'max_bookings', 'booking_types_allowed',
        ]

    def validate(self, attrs):
        """Validate update data."""
        instance = self.instance
        start = attrs.get('start_datetime', instance.start_datetime if instance else None)
        end = attrs.get('end_datetime', instance.end_datetime if instance else None)

        if start and end and end <= start:
            raise serializers.ValidationError({
                'end_datetime': "End time must be after start time"
            })

        return attrs


class OperatingHoursSerializer(serializers.ModelSerializer):
    """Serializer for operating hours."""

    day_name = serializers.SerializerMethodField()
    is_open = serializers.SerializerMethodField()
    duration_hours = serializers.SerializerMethodField()

    class Meta:
        model = OperatingHours
        fields = [
            'id', 'organization_id', 'location_id',
            'day_of_week', 'day_name',
            'open_time', 'close_time',
            'is_open', 'duration_hours',
            'effective_from', 'effective_to',
            'is_active',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_day_name(self, obj) -> str:
        """Get day of week name."""
        days = [
            'Sunday', 'Monday', 'Tuesday', 'Wednesday',
            'Thursday', 'Friday', 'Saturday'
        ]
        return days[obj.day_of_week] if 0 <= obj.day_of_week <= 6 else 'Unknown'

    def get_is_open(self, obj) -> bool:
        """Check if location is open on this day."""
        return obj.is_active and obj.open_time is not None

    def get_duration_hours(self, obj) -> float:
        """Get operating hours duration."""
        if obj.open_time and obj.close_time:
            open_dt = datetime.combine(date.today(), obj.open_time)
            close_dt = datetime.combine(date.today(), obj.close_time)
            delta = close_dt - open_dt
            return round(delta.total_seconds() / 3600, 1)
        return 0


class OperatingHoursCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating operating hours."""

    class Meta:
        model = OperatingHours
        fields = [
            'organization_id', 'location_id',
            'day_of_week',
            'open_time', 'close_time',
            'effective_from', 'effective_to',
            'is_active',
        ]

    def validate(self, attrs):
        """Validate operating hours."""
        day_of_week = attrs.get('day_of_week')
        open_time = attrs.get('open_time')
        close_time = attrs.get('close_time')

        if day_of_week is not None and not 0 <= day_of_week <= 6:
            raise serializers.ValidationError({
                'day_of_week': "Day must be 0-6 (Sunday-Saturday)"
            })

        if open_time and close_time and close_time <= open_time:
            raise serializers.ValidationError({
                'close_time': "Close time must be after open time"
            })

        effective_from = attrs.get('effective_from')
        effective_to = attrs.get('effective_to')
        if effective_from and effective_to and effective_to < effective_from:
            raise serializers.ValidationError({
                'effective_to': "Effective end date must be after start date"
            })

        return attrs


class WeeklyScheduleSerializer(serializers.Serializer):
    """Serializer for weekly schedule data."""

    sunday = serializers.DictField(required=False)
    monday = serializers.DictField(required=False)
    tuesday = serializers.DictField(required=False)
    wednesday = serializers.DictField(required=False)
    thursday = serializers.DictField(required=False)
    friday = serializers.DictField(required=False)
    saturday = serializers.DictField(required=False)


class AvailableSlotSerializer(serializers.Serializer):
    """Serializer for available time slots."""

    start = serializers.DateTimeField()
    end = serializers.DateTimeField()
    duration_minutes = serializers.IntegerField()
    available = serializers.BooleanField(default=True)
    aircraft_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False
    )
    instructor_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False
    )


class AvailableSlotsRequestSerializer(serializers.Serializer):
    """Serializer for available slots request."""

    target_date = serializers.DateField()
    duration_minutes = serializers.IntegerField(
        min_value=15,
        max_value=480
    )
    aircraft_id = serializers.UUIDField(required=False, allow_null=True)
    instructor_id = serializers.UUIDField(required=False, allow_null=True)
    location_id = serializers.UUIDField(required=False, allow_null=True)
    booking_type = serializers.CharField(required=False)
    slot_interval = serializers.IntegerField(
        min_value=15,
        max_value=60,
        default=30
    )


class ResourceScheduleSerializer(serializers.Serializer):
    """Serializer for resource daily schedule."""

    date = serializers.DateField()
    resource_type = serializers.CharField()
    resource_id = serializers.UUIDField()
    bookings = serializers.ListField(child=serializers.DictField())
    availability = serializers.ListField(child=serializers.DictField())
    operating_hours = serializers.DictField(required=False)


class ResourceAvailabilityCheckSerializer(serializers.Serializer):
    """Serializer for checking resource availability."""

    resource_type = serializers.ChoiceField(
        choices=['aircraft', 'instructor', 'location']
    )
    resource_id = serializers.UUIDField()
    start = serializers.DateTimeField()
    end = serializers.DateTimeField()
    booking_type = serializers.CharField(required=False)


class ResourceAvailabilityResultSerializer(serializers.Serializer):
    """Serializer for availability check results."""

    available = serializers.BooleanField()
    reasons = serializers.ListField(
        child=serializers.CharField()
    )
    conflicts = serializers.ListField(
        child=serializers.DictField()
    )
    alternatives = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        help_text="Alternative available time slots"
    )
