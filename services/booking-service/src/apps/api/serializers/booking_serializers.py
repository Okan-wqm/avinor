# services/booking-service/src/apps/api/serializers/booking_serializers.py
"""
Booking Serializers

Comprehensive serializers for booking operations.
"""

from datetime import datetime, timedelta
from decimal import Decimal
from rest_framework import serializers
from django.utils import timezone

from apps.core.models import Booking


class BookingSerializer(serializers.ModelSerializer):
    """Base booking serializer."""

    booking_type_display = serializers.CharField(
        source='get_booking_type_display',
        read_only=True
    )
    training_type_display = serializers.CharField(
        source='get_training_type_display',
        read_only=True
    )
    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )
    payment_status_display = serializers.CharField(
        source='get_payment_status_display',
        read_only=True
    )
    duration_minutes = serializers.SerializerMethodField()
    block_duration_minutes = serializers.SerializerMethodField()
    hours_until_start = serializers.FloatField(read_only=True)
    can_cancel = serializers.BooleanField(read_only=True)
    can_check_in = serializers.BooleanField(read_only=True)
    can_dispatch = serializers.BooleanField(read_only=True)

    class Meta:
        model = Booking
        fields = [
            'id', 'organization_id', 'location_id', 'booking_number',
            'booking_type', 'booking_type_display',
            'training_type', 'training_type_display',
            'status', 'status_display',
            'aircraft_id', 'instructor_id', 'student_id', 'pilot_id',
            'scheduled_start', 'scheduled_end', 'scheduled_duration',
            'block_start', 'block_end',
            'preflight_minutes', 'postflight_minutes',
            'duration_minutes', 'block_duration_minutes',
            'actual_start', 'actual_end', 'actual_duration',
            'hobbs_start', 'hobbs_end', 'tach_start', 'tach_end',
            'route', 'remarks', 'internal_notes',
            'estimated_cost', 'actual_cost',
            'payment_status', 'payment_status_display',
            'payment_collected', 'invoice_id',
            'recurring_pattern_id', 'parent_booking_id',
            'hours_until_start', 'can_cancel', 'can_check_in', 'can_dispatch',
            'created_by', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'booking_number', 'block_start', 'block_end',
            'actual_start', 'actual_end', 'actual_duration',
            'created_at', 'updated_at',
        ]

    def get_duration_minutes(self, obj) -> int:
        """Get scheduled duration in minutes."""
        if obj.scheduled_start and obj.scheduled_end:
            return int((obj.scheduled_end - obj.scheduled_start).total_seconds() / 60)
        return obj.scheduled_duration or 0

    def get_block_duration_minutes(self, obj) -> int:
        """Get block duration including pre/post flight."""
        if obj.block_start and obj.block_end:
            return int((obj.block_end - obj.block_start).total_seconds() / 60)
        return 0


class BookingListSerializer(BookingSerializer):
    """Optimized serializer for booking lists."""

    class Meta(BookingSerializer.Meta):
        fields = [
            'id', 'booking_number', 'booking_type', 'booking_type_display',
            'status', 'status_display',
            'aircraft_id', 'instructor_id', 'student_id',
            'scheduled_start', 'scheduled_end', 'duration_minutes',
            'block_start', 'block_end',
            'location_id', 'route',
            'estimated_cost', 'payment_status',
            'can_cancel', 'can_check_in',
        ]


class BookingDetailSerializer(BookingSerializer):
    """Detailed serializer with all booking information."""

    conflicts = serializers.SerializerMethodField()
    status_history = serializers.SerializerMethodField()

    class Meta(BookingSerializer.Meta):
        fields = BookingSerializer.Meta.fields + [
            'conflicts', 'status_history',
            'cancelled_at', 'cancelled_by', 'cancellation_type', 'cancellation_reason',
            'no_show_at', 'no_show_fee',
        ]

    def get_conflicts(self, obj) -> list:
        """Get any conflicting bookings."""
        if obj.status in [Booking.Status.CANCELLED, Booking.Status.DRAFT]:
            return []

        conflicts = Booking.get_conflicts(
            obj.organization_id,
            obj.scheduled_start,
            obj.scheduled_end,
            aircraft_id=obj.aircraft_id,
            instructor_id=obj.instructor_id,
            exclude_booking_id=obj.id
        )

        return [
            {
                'id': str(c.id),
                'booking_number': c.booking_number,
                'scheduled_start': c.scheduled_start.isoformat(),
                'scheduled_end': c.scheduled_end.isoformat(),
                'conflict_type': self._get_conflict_type(obj, c),
            }
            for c in conflicts
        ]

    def _get_conflict_type(self, booking, conflict) -> str:
        """Determine the type of conflict."""
        types = []
        if booking.aircraft_id and booking.aircraft_id == conflict.aircraft_id:
            types.append('aircraft')
        if booking.instructor_id and booking.instructor_id == conflict.instructor_id:
            types.append('instructor')
        if booking.student_id and booking.student_id == conflict.student_id:
            types.append('student')
        return ','.join(types) if types else 'unknown'

    def get_status_history(self, obj) -> list:
        """Get booking status change history from metadata."""
        return obj.metadata.get('status_history', []) if obj.metadata else []


class BookingCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new bookings."""

    validate_only = serializers.BooleanField(
        default=False,
        write_only=True,
        help_text="If true, only validate without creating"
    )
    skip_conflict_check = serializers.BooleanField(
        default=False,
        write_only=True,
        help_text="Skip conflict validation (admin only)"
    )
    skip_rule_check = serializers.BooleanField(
        default=False,
        write_only=True,
        help_text="Skip rule validation (admin only)"
    )

    class Meta:
        model = Booking
        fields = [
            'organization_id', 'location_id',
            'booking_type', 'training_type',
            'aircraft_id', 'instructor_id', 'student_id', 'pilot_id',
            'scheduled_start', 'scheduled_end',
            'preflight_minutes', 'postflight_minutes',
            'route', 'remarks', 'internal_notes',
            'recurring_pattern_id', 'parent_booking_id',
            'validate_only', 'skip_conflict_check', 'skip_rule_check',
        ]

    def validate(self, attrs):
        """Validate booking data."""
        scheduled_start = attrs.get('scheduled_start')
        scheduled_end = attrs.get('scheduled_end')

        if scheduled_start and scheduled_end:
            if scheduled_end <= scheduled_start:
                raise serializers.ValidationError({
                    'scheduled_end': "End time must be after start time"
                })

            duration = (scheduled_end - scheduled_start).total_seconds() / 60
            if duration < 15:
                raise serializers.ValidationError({
                    'scheduled_end': "Minimum booking duration is 15 minutes"
                })
            if duration > 480:
                raise serializers.ValidationError({
                    'scheduled_end': "Maximum booking duration is 8 hours"
                })

        # Validate booking type requirements
        booking_type = attrs.get('booking_type')
        if booking_type in [Booking.BookingType.TRAINING, Booking.BookingType.CHECK_RIDE]:
            if not attrs.get('instructor_id'):
                raise serializers.ValidationError({
                    'instructor_id': f"Instructor required for {booking_type} bookings"
                })
            if not attrs.get('student_id'):
                raise serializers.ValidationError({
                    'student_id': f"Student required for {booking_type} bookings"
                })

        if booking_type == Booking.BookingType.RENTAL:
            if not attrs.get('pilot_id') and not attrs.get('student_id'):
                raise serializers.ValidationError({
                    'pilot_id': "Pilot or student required for rental bookings"
                })

        return attrs


class BookingUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating existing bookings."""

    class Meta:
        model = Booking
        fields = [
            'scheduled_start', 'scheduled_end',
            'aircraft_id', 'instructor_id',
            'preflight_minutes', 'postflight_minutes',
            'route', 'remarks', 'internal_notes',
        ]

    def validate(self, attrs):
        """Validate update data."""
        instance = self.instance

        if instance and instance.status not in [
            Booking.Status.DRAFT,
            Booking.Status.PENDING_APPROVAL,
            Booking.Status.SCHEDULED
        ]:
            raise serializers.ValidationError(
                "Cannot modify booking in current status"
            )

        scheduled_start = attrs.get('scheduled_start', instance.scheduled_start if instance else None)
        scheduled_end = attrs.get('scheduled_end', instance.scheduled_end if instance else None)

        if scheduled_start and scheduled_end and scheduled_end <= scheduled_start:
            raise serializers.ValidationError({
                'scheduled_end': "End time must be after start time"
            })

        return attrs


class BookingStatusUpdateSerializer(serializers.Serializer):
    """Base serializer for status updates."""

    notes = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=1000
    )


class BookingCancelSerializer(BookingStatusUpdateSerializer):
    """Serializer for booking cancellation."""

    cancellation_type = serializers.ChoiceField(
        choices=Booking.CancellationType.choices,
        default=Booking.CancellationType.USER
    )
    reason = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=500
    )
    waive_fee = serializers.BooleanField(
        default=False,
        help_text="Waive cancellation fee (admin only)"
    )

    def validate(self, attrs):
        """Validate cancellation request."""
        booking = self.context.get('booking')

        if booking and not booking.can_cancel:
            raise serializers.ValidationError(
                "This booking cannot be cancelled in its current state"
            )

        return attrs


class BookingCheckInSerializer(BookingStatusUpdateSerializer):
    """Serializer for check-in action."""

    hobbs_reading = serializers.DecimalField(
        max_digits=10,
        decimal_places=1,
        required=False,
        allow_null=True
    )
    tach_reading = serializers.DecimalField(
        max_digits=10,
        decimal_places=1,
        required=False,
        allow_null=True
    )

    def validate(self, attrs):
        """Validate check-in data."""
        booking = self.context.get('booking')

        if booking and not booking.can_check_in:
            raise serializers.ValidationError(
                "This booking cannot be checked in yet"
            )

        return attrs


class BookingDispatchSerializer(BookingStatusUpdateSerializer):
    """Serializer for dispatch action."""

    hobbs_out = serializers.DecimalField(
        max_digits=10,
        decimal_places=1,
        required=True
    )
    tach_out = serializers.DecimalField(
        max_digits=10,
        decimal_places=1,
        required=False,
        allow_null=True
    )
    fuel_quantity = serializers.DecimalField(
        max_digits=6,
        decimal_places=1,
        required=False,
        allow_null=True,
        help_text="Fuel quantity in gallons"
    )
    departure_fuel = serializers.DecimalField(
        max_digits=6,
        decimal_places=1,
        required=False,
        allow_null=True
    )

    def validate(self, attrs):
        """Validate dispatch data."""
        booking = self.context.get('booking')

        if booking and not booking.can_dispatch:
            raise serializers.ValidationError(
                "This booking cannot be dispatched"
            )

        return attrs


class BookingCompleteSerializer(BookingStatusUpdateSerializer):
    """Serializer for completing a booking."""

    hobbs_in = serializers.DecimalField(
        max_digits=10,
        decimal_places=1,
        required=True
    )
    tach_in = serializers.DecimalField(
        max_digits=10,
        decimal_places=1,
        required=False,
        allow_null=True
    )
    landings_day = serializers.IntegerField(
        min_value=0,
        default=0
    )
    landings_night = serializers.IntegerField(
        min_value=0,
        default=0
    )
    flight_time = serializers.DecimalField(
        max_digits=5,
        decimal_places=1,
        required=False,
        allow_null=True,
        help_text="Total flight time in hours"
    )
    fuel_added = serializers.DecimalField(
        max_digits=6,
        decimal_places=1,
        required=False,
        allow_null=True,
        help_text="Fuel added in gallons"
    )
    squawks = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=2000,
        help_text="Aircraft discrepancies noted"
    )

    def validate(self, attrs):
        """Validate completion data."""
        booking = self.context.get('booking')

        if booking and booking.status != Booking.Status.IN_PROGRESS:
            raise serializers.ValidationError(
                "Only in-progress bookings can be completed"
            )

        hobbs_in = attrs.get('hobbs_in')
        if booking and booking.hobbs_start and hobbs_in:
            if hobbs_in < booking.hobbs_start:
                raise serializers.ValidationError({
                    'hobbs_in': "Hobbs in cannot be less than hobbs out"
                })

        return attrs


class BookingConflictSerializer(serializers.Serializer):
    """Serializer for conflict check results."""

    has_conflicts = serializers.BooleanField()
    conflicts = serializers.ListField(
        child=serializers.DictField()
    )
    aircraft_conflicts = serializers.ListField(
        child=serializers.DictField(),
        required=False
    )
    instructor_conflicts = serializers.ListField(
        child=serializers.DictField(),
        required=False
    )
    student_conflicts = serializers.ListField(
        child=serializers.DictField(),
        required=False
    )


class BookingCalendarSerializer(serializers.Serializer):
    """Serializer for calendar view data."""

    date = serializers.DateField()
    bookings = BookingListSerializer(many=True)
    slots_available = serializers.IntegerField()
    total_scheduled_hours = serializers.DecimalField(
        max_digits=5,
        decimal_places=1
    )


class BookingCostEstimateSerializer(serializers.Serializer):
    """Serializer for booking cost estimates."""

    organization_id = serializers.UUIDField()
    aircraft_id = serializers.UUIDField(required=False, allow_null=True)
    duration_minutes = serializers.IntegerField(min_value=15)
    booking_type = serializers.ChoiceField(
        choices=Booking.BookingType.choices
    )
    include_instructor = serializers.BooleanField(default=False)
    include_fuel_surcharge = serializers.BooleanField(default=True)


class BookingCostEstimateResultSerializer(serializers.Serializer):
    """Serializer for cost estimate results."""

    aircraft_rate = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        allow_null=True
    )
    instructor_rate = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        allow_null=True
    )
    aircraft_cost = serializers.DecimalField(
        max_digits=10,
        decimal_places=2
    )
    instructor_cost = serializers.DecimalField(
        max_digits=10,
        decimal_places=2
    )
    fuel_surcharge = serializers.DecimalField(
        max_digits=10,
        decimal_places=2
    )
    subtotal = serializers.DecimalField(
        max_digits=10,
        decimal_places=2
    )
    tax = serializers.DecimalField(
        max_digits=10,
        decimal_places=2
    )
    total = serializers.DecimalField(
        max_digits=10,
        decimal_places=2
    )
    currency = serializers.CharField(default='NOK')
