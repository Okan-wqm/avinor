# services/booking-service/src/apps/api/serializers/recurring_serializers.py
"""
Recurring Pattern Serializers

Serializers for recurring booking patterns.
"""

from datetime import date, time
from rest_framework import serializers
from django.utils import timezone

from apps.core.models import RecurringPattern


class RecurringPatternSerializer(serializers.ModelSerializer):
    """Base recurring pattern serializer."""

    frequency_display = serializers.CharField(
        source='get_frequency_display',
        read_only=True
    )
    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )
    days_of_week_display = serializers.SerializerMethodField()
    remaining_occurrences = serializers.SerializerMethodField()
    is_active = serializers.BooleanField(read_only=True)

    class Meta:
        model = RecurringPattern
        fields = [
            'id', 'organization_id', 'location_id',
            'name', 'description',
            'frequency', 'frequency_display',
            'interval', 'days_of_week', 'days_of_week_display',
            'day_of_month', 'week_of_month',
            'start_date', 'end_date', 'max_occurrences',
            'start_time', 'end_time', 'duration_minutes',
            'booking_type', 'training_type',
            'aircraft_id', 'instructor_id', 'student_id',
            'preflight_minutes', 'postflight_minutes',
            'route', 'notes',
            'status', 'status_display', 'is_active',
            'occurrences_created', 'remaining_occurrences',
            'exception_dates', 'modified_dates',
            'created_by', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'occurrences_created',
            'created_at', 'updated_at',
        ]

    def get_days_of_week_display(self, obj) -> list:
        """Get human-readable day names."""
        if not obj.days_of_week:
            return []

        day_names = [
            'Sunday', 'Monday', 'Tuesday', 'Wednesday',
            'Thursday', 'Friday', 'Saturday'
        ]
        return [day_names[d] for d in obj.days_of_week if 0 <= d <= 6]

    def get_remaining_occurrences(self, obj) -> int | None:
        """Get remaining occurrences if max is set."""
        if obj.max_occurrences:
            return max(0, obj.max_occurrences - obj.occurrences_created)
        return None


class RecurringPatternListSerializer(RecurringPatternSerializer):
    """Optimized serializer for listing recurring patterns."""

    class Meta(RecurringPatternSerializer.Meta):
        fields = [
            'id', 'name', 'frequency', 'frequency_display',
            'start_date', 'end_date', 'start_time', 'end_time',
            'booking_type', 'aircraft_id', 'instructor_id', 'student_id',
            'status', 'status_display', 'is_active',
            'occurrences_created', 'remaining_occurrences',
        ]


class RecurringPatternDetailSerializer(RecurringPatternSerializer):
    """Detailed serializer with upcoming occurrences."""

    upcoming_occurrences = serializers.SerializerMethodField()
    booking_count = serializers.SerializerMethodField()

    class Meta(RecurringPatternSerializer.Meta):
        fields = RecurringPatternSerializer.Meta.fields + [
            'upcoming_occurrences', 'booking_count',
        ]

    def get_upcoming_occurrences(self, obj) -> list:
        """Get next 10 upcoming occurrence dates."""
        if not obj.is_active:
            return []

        occurrences = obj.get_next_occurrences(10)
        return [occ.isoformat() for occ in occurrences]

    def get_booking_count(self, obj) -> int:
        """Get count of bookings created from this pattern."""
        return obj.bookings.count()


class RecurringPatternCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating recurring patterns."""

    generate_bookings = serializers.BooleanField(
        default=True,
        write_only=True,
        help_text="Generate bookings immediately after creation"
    )
    generate_until = serializers.DateField(
        required=False,
        write_only=True,
        help_text="Generate bookings until this date"
    )

    class Meta:
        model = RecurringPattern
        fields = [
            'organization_id', 'location_id',
            'name', 'description',
            'frequency', 'interval', 'days_of_week',
            'day_of_month', 'week_of_month',
            'start_date', 'end_date', 'max_occurrences',
            'start_time', 'end_time', 'duration_minutes',
            'booking_type', 'training_type',
            'aircraft_id', 'instructor_id', 'student_id',
            'preflight_minutes', 'postflight_minutes',
            'route', 'notes',
            'generate_bookings', 'generate_until',
        ]

    def validate(self, attrs):
        """Validate pattern configuration."""
        frequency = attrs.get('frequency')
        days_of_week = attrs.get('days_of_week')
        day_of_month = attrs.get('day_of_month')
        start_date = attrs.get('start_date')
        end_date = attrs.get('end_date')
        start_time = attrs.get('start_time')
        end_time = attrs.get('end_time')

        # Weekly frequency requires days_of_week
        if frequency in [RecurringPattern.Frequency.WEEKLY, RecurringPattern.Frequency.BIWEEKLY]:
            if not days_of_week:
                raise serializers.ValidationError({
                    'days_of_week': "Days of week required for weekly/biweekly patterns"
                })
            # Validate day values
            for day in days_of_week:
                if not 0 <= day <= 6:
                    raise serializers.ValidationError({
                        'days_of_week': "Day values must be 0-6 (Sunday-Saturday)"
                    })

        # Monthly frequency requires day_of_month or week_of_month
        if frequency == RecurringPattern.Frequency.MONTHLY:
            if not day_of_month and not attrs.get('week_of_month'):
                raise serializers.ValidationError({
                    'day_of_month': "Day of month or week of month required for monthly patterns"
                })

        # Date validation
        if start_date and end_date and end_date < start_date:
            raise serializers.ValidationError({
                'end_date': "End date must be after start date"
            })

        if start_date and start_date < timezone.now().date():
            raise serializers.ValidationError({
                'start_date': "Start date cannot be in the past"
            })

        # Time validation
        if start_time and end_time and end_time <= start_time:
            raise serializers.ValidationError({
                'end_time': "End time must be after start time"
            })

        return attrs


class RecurringPatternUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating recurring patterns."""

    apply_to_future = serializers.BooleanField(
        default=False,
        write_only=True,
        help_text="Apply changes to future bookings"
    )

    class Meta:
        model = RecurringPattern
        fields = [
            'name', 'description',
            'end_date', 'max_occurrences',
            'start_time', 'end_time', 'duration_minutes',
            'aircraft_id', 'instructor_id',
            'preflight_minutes', 'postflight_minutes',
            'route', 'notes',
            'apply_to_future',
        ]

    def validate(self, attrs):
        """Validate update data."""
        instance = self.instance

        if instance and instance.status not in [
            RecurringPattern.Status.ACTIVE,
            RecurringPattern.Status.PAUSED
        ]:
            raise serializers.ValidationError(
                "Cannot modify completed or cancelled patterns"
            )

        return attrs


class RecurringPatternOccurrenceSerializer(serializers.Serializer):
    """Serializer for occurrence data."""

    date = serializers.DateField()
    start_time = serializers.TimeField()
    end_time = serializers.TimeField()
    status = serializers.ChoiceField(
        choices=['scheduled', 'exception', 'modified', 'past']
    )
    booking_id = serializers.UUIDField(required=False, allow_null=True)
    booking_number = serializers.CharField(required=False, allow_null=True)
    modification = serializers.DictField(required=False)


class RecurringPatternExceptionSerializer(serializers.Serializer):
    """Serializer for adding exceptions to patterns."""

    date = serializers.DateField()
    reason = serializers.CharField(
        required=False,
        max_length=500
    )
    cancel_booking = serializers.BooleanField(
        default=True,
        help_text="Cancel the booking for this date if it exists"
    )

    def validate_date(self, value):
        """Validate exception date."""
        pattern = self.context.get('pattern')

        if pattern:
            if pattern.start_date and value < pattern.start_date:
                raise serializers.ValidationError(
                    "Exception date cannot be before pattern start date"
                )
            if pattern.end_date and value > pattern.end_date:
                raise serializers.ValidationError(
                    "Exception date cannot be after pattern end date"
                )
            if value in (pattern.exception_dates or []):
                raise serializers.ValidationError(
                    "This date is already marked as an exception"
                )

        return value


class RecurringPatternModificationSerializer(serializers.Serializer):
    """Serializer for modifying specific occurrences."""

    date = serializers.DateField()
    new_start_time = serializers.TimeField(required=False)
    new_end_time = serializers.TimeField(required=False)
    new_aircraft_id = serializers.UUIDField(required=False, allow_null=True)
    new_instructor_id = serializers.UUIDField(required=False, allow_null=True)
    reason = serializers.CharField(
        required=False,
        max_length=500
    )
    update_booking = serializers.BooleanField(
        default=True,
        help_text="Update the booking for this date if it exists"
    )
