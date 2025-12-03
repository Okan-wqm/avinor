# services/booking-service/src/apps/api/serializers/rule_serializers.py
"""
Booking Rule Serializers

Serializers for booking rules and validation.
"""

from decimal import Decimal
from rest_framework import serializers

from apps.core.models import BookingRule


class BookingRuleSerializer(serializers.ModelSerializer):
    """Base booking rule serializer."""

    rule_type_display = serializers.CharField(
        source='get_rule_type_display',
        read_only=True
    )
    target_type_display = serializers.CharField(
        source='get_target_type_display',
        read_only=True
    )
    is_effective = serializers.SerializerMethodField()
    constraint_summary = serializers.SerializerMethodField()

    class Meta:
        model = BookingRule
        fields = [
            'id', 'organization_id',
            'rule_type', 'rule_type_display',
            'target_type', 'target_type_display',
            'target_id',
            'name', 'description',
            'priority', 'is_active', 'is_effective',
            # Time constraints
            'min_booking_duration', 'max_booking_duration',
            'min_notice_hours', 'max_advance_days',
            # Quantity constraints
            'max_daily_hours', 'max_weekly_hours',
            'max_daily_bookings', 'max_concurrent_bookings',
            # Operating hours
            'operating_hours',
            # Buffer rules
            'required_buffer_minutes',
            'preflight_minutes', 'postflight_minutes',
            # Authorization
            'who_can_book', 'requires_approval_from',
            'required_qualifications', 'required_currency',
            # Financial
            'require_positive_balance', 'minimum_balance',
            'require_prepayment', 'prepayment_percentage',
            # Cancellation
            'free_cancellation_hours',
            'late_cancellation_fee_percent',
            'no_show_fee_percent',
            # Validity
            'effective_from', 'effective_to',
            # Summary
            'constraint_summary',
            # Metadata
            'created_by', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_is_effective(self, obj) -> bool:
        """Check if rule is currently in effect."""
        return obj.is_effective

    def get_constraint_summary(self, obj) -> dict:
        """Get a summary of active constraints."""
        summary = {}

        if obj.min_booking_duration or obj.max_booking_duration:
            summary['duration'] = {
                'min': obj.min_booking_duration,
                'max': obj.max_booking_duration,
            }

        if obj.min_notice_hours:
            summary['notice_hours'] = obj.min_notice_hours

        if obj.max_advance_days:
            summary['advance_days'] = obj.max_advance_days

        if obj.max_daily_hours or obj.max_weekly_hours:
            summary['hours_limit'] = {
                'daily': float(obj.max_daily_hours) if obj.max_daily_hours else None,
                'weekly': float(obj.max_weekly_hours) if obj.max_weekly_hours else None,
            }

        if obj.free_cancellation_hours is not None:
            summary['cancellation'] = {
                'free_hours': obj.free_cancellation_hours,
                'late_fee_percent': float(obj.late_cancellation_fee_percent) if obj.late_cancellation_fee_percent else None,
                'no_show_fee_percent': float(obj.no_show_fee_percent) if obj.no_show_fee_percent else None,
            }

        return summary


class BookingRuleListSerializer(BookingRuleSerializer):
    """Optimized serializer for rule lists."""

    class Meta(BookingRuleSerializer.Meta):
        fields = [
            'id', 'name', 'description',
            'rule_type', 'rule_type_display',
            'target_type', 'target_id',
            'priority', 'is_active', 'is_effective',
            'effective_from', 'effective_to',
        ]


class BookingRuleDetailSerializer(BookingRuleSerializer):
    """Detailed rule serializer with affected resources."""

    affected_count = serializers.SerializerMethodField()

    class Meta(BookingRuleSerializer.Meta):
        fields = BookingRuleSerializer.Meta.fields + ['affected_count']

    def get_affected_count(self, obj) -> dict:
        """Get count of resources affected by this rule."""
        # This would typically query actual resource counts
        return {
            'estimated': True,
            'message': "Rule applies based on target type and scope"
        }


class BookingRuleCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating booking rules."""

    class Meta:
        model = BookingRule
        fields = [
            'organization_id',
            'rule_type', 'target_type', 'target_id',
            'name', 'description', 'priority',
            'min_booking_duration', 'max_booking_duration',
            'min_notice_hours', 'max_advance_days',
            'max_daily_hours', 'max_weekly_hours',
            'max_daily_bookings', 'max_concurrent_bookings',
            'operating_hours',
            'required_buffer_minutes',
            'preflight_minutes', 'postflight_minutes',
            'who_can_book', 'requires_approval_from',
            'required_qualifications', 'required_currency',
            'require_positive_balance', 'minimum_balance',
            'require_prepayment', 'prepayment_percentage',
            'free_cancellation_hours',
            'late_cancellation_fee_percent', 'no_show_fee_percent',
            'effective_from', 'effective_to',
        ]

    def validate(self, attrs):
        """Validate rule configuration."""
        # Duration validation
        min_duration = attrs.get('min_booking_duration')
        max_duration = attrs.get('max_booking_duration')
        if min_duration and max_duration and min_duration > max_duration:
            raise serializers.ValidationError({
                'max_booking_duration': "Max duration must be >= min duration"
            })

        # Percentage validations
        late_fee = attrs.get('late_cancellation_fee_percent')
        if late_fee and (late_fee < 0 or late_fee > 100):
            raise serializers.ValidationError({
                'late_cancellation_fee_percent': "Must be between 0 and 100"
            })

        no_show_fee = attrs.get('no_show_fee_percent')
        if no_show_fee and (no_show_fee < 0 or no_show_fee > 100):
            raise serializers.ValidationError({
                'no_show_fee_percent': "Must be between 0 and 100"
            })

        prepayment = attrs.get('prepayment_percentage')
        if prepayment and (prepayment < 0 or prepayment > 100):
            raise serializers.ValidationError({
                'prepayment_percentage': "Must be between 0 and 100"
            })

        # Effective dates validation
        effective_from = attrs.get('effective_from')
        effective_to = attrs.get('effective_to')
        if effective_from and effective_to and effective_to < effective_from:
            raise serializers.ValidationError({
                'effective_to': "End date must be after start date"
            })

        # Operating hours validation
        operating_hours = attrs.get('operating_hours')
        if operating_hours:
            self._validate_operating_hours(operating_hours)

        return attrs

    def _validate_operating_hours(self, hours: dict):
        """Validate operating hours format."""
        valid_days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']

        for day, times in hours.items():
            if day not in valid_days:
                raise serializers.ValidationError({
                    'operating_hours': f"Invalid day: {day}"
                })

            if isinstance(times, dict):
                if 'open' not in times or 'close' not in times:
                    raise serializers.ValidationError({
                        'operating_hours': f"Missing open/close times for {day}"
                    })


class BookingRuleUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating booking rules."""

    class Meta:
        model = BookingRule
        fields = [
            'name', 'description', 'priority', 'is_active',
            'min_booking_duration', 'max_booking_duration',
            'min_notice_hours', 'max_advance_days',
            'max_daily_hours', 'max_weekly_hours',
            'max_daily_bookings', 'max_concurrent_bookings',
            'operating_hours',
            'required_buffer_minutes',
            'preflight_minutes', 'postflight_minutes',
            'who_can_book', 'requires_approval_from',
            'required_qualifications', 'required_currency',
            'require_positive_balance', 'minimum_balance',
            'require_prepayment', 'prepayment_percentage',
            'free_cancellation_hours',
            'late_cancellation_fee_percent', 'no_show_fee_percent',
            'effective_from', 'effective_to',
        ]


class RuleValidationRequestSerializer(serializers.Serializer):
    """Serializer for rule validation requests."""

    organization_id = serializers.UUIDField()
    scheduled_start = serializers.DateTimeField()
    scheduled_end = serializers.DateTimeField()
    user_id = serializers.UUIDField()
    aircraft_id = serializers.UUIDField(required=False, allow_null=True)
    instructor_id = serializers.UUIDField(required=False, allow_null=True)
    student_id = serializers.UUIDField(required=False, allow_null=True)
    location_id = serializers.UUIDField(required=False, allow_null=True)
    booking_type = serializers.CharField(required=False)


class RuleValidationResultSerializer(serializers.Serializer):
    """Serializer for rule validation results."""

    valid = serializers.BooleanField()
    errors = serializers.ListField(
        child=serializers.CharField()
    )
    warnings = serializers.ListField(
        child=serializers.CharField()
    )
    rules_applied = serializers.ListField(
        child=serializers.CharField()
    )
    requires_approval = serializers.BooleanField(default=False)
    approval_required_from = serializers.ListField(
        child=serializers.CharField(),
        required=False
    )


class MergedRulesSerializer(serializers.Serializer):
    """Serializer for merged/effective rules."""

    # Time constraints
    min_booking_duration = serializers.IntegerField(allow_null=True)
    max_booking_duration = serializers.IntegerField(allow_null=True)
    min_notice_hours = serializers.IntegerField(allow_null=True)
    max_advance_days = serializers.IntegerField(allow_null=True)

    # Quantity constraints
    max_daily_hours = serializers.DecimalField(
        max_digits=5, decimal_places=1, allow_null=True
    )
    max_weekly_hours = serializers.DecimalField(
        max_digits=5, decimal_places=1, allow_null=True
    )
    max_daily_bookings = serializers.IntegerField(allow_null=True)
    max_concurrent_bookings = serializers.IntegerField(allow_null=True)

    # Buffer rules
    required_buffer_minutes = serializers.IntegerField(allow_null=True)
    preflight_minutes = serializers.IntegerField(allow_null=True)
    postflight_minutes = serializers.IntegerField(allow_null=True)

    # Financial
    require_positive_balance = serializers.BooleanField(default=False)
    minimum_balance = serializers.DecimalField(
        max_digits=10, decimal_places=2, allow_null=True
    )
    require_prepayment = serializers.BooleanField(default=False)
    prepayment_percentage = serializers.DecimalField(
        max_digits=5, decimal_places=2, allow_null=True
    )

    # Cancellation
    free_cancellation_hours = serializers.IntegerField(allow_null=True)
    late_cancellation_fee_percent = serializers.DecimalField(
        max_digits=5, decimal_places=2, allow_null=True
    )
    no_show_fee_percent = serializers.DecimalField(
        max_digits=5, decimal_places=2, allow_null=True
    )

    # Authorization
    requires_approval_from = serializers.ListField(
        child=serializers.CharField(),
        required=False
    )


class CancellationFeeRequestSerializer(serializers.Serializer):
    """Serializer for cancellation fee calculation requests."""

    organization_id = serializers.UUIDField()
    hours_until_start = serializers.FloatField()
    estimated_cost = serializers.DecimalField(
        max_digits=10,
        decimal_places=2
    )
    aircraft_id = serializers.UUIDField(required=False, allow_null=True)


class CancellationFeeSerializer(serializers.Serializer):
    """Serializer for cancellation fee results."""

    fee = serializers.DecimalField(
        max_digits=10,
        decimal_places=2
    )
    fee_percent = serializers.DecimalField(
        max_digits=5,
        decimal_places=2
    )
    is_free = serializers.BooleanField()
    is_late = serializers.BooleanField()
    currency = serializers.CharField(default='NOK')
    message = serializers.CharField(required=False)
