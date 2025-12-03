# services/booking-service/src/apps/api/serializers/waitlist_serializers.py
"""
Waitlist Serializers

Serializers for waitlist management.
"""

from datetime import date, time
from rest_framework import serializers
from django.utils import timezone

from apps.core.models import WaitlistEntry


class WaitlistEntrySerializer(serializers.ModelSerializer):
    """Base waitlist entry serializer."""

    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )
    booking_type_display = serializers.CharField(
        source='get_booking_type_display',
        read_only=True
    )
    is_active = serializers.SerializerMethodField()
    offer_expired = serializers.BooleanField(read_only=True)
    days_waiting = serializers.SerializerMethodField()
    time_remaining = serializers.SerializerMethodField()

    class Meta:
        model = WaitlistEntry
        fields = [
            'id', 'organization_id', 'user_id',
            'user_name', 'user_email',
            'requested_date',
            'preferred_start_time', 'preferred_end_time',
            'duration_minutes', 'booking_type', 'booking_type_display',
            'aircraft_id', 'instructor_id', 'location_id',
            'any_aircraft', 'any_instructor',
            'flexibility_days', 'flexibility_hours',
            'priority', 'notes',
            'status', 'status_display', 'is_active',
            'offered_booking_id', 'offer_expires_at',
            'offer_message', 'offer_expired',
            'accepted_booking_id',
            'days_waiting', 'time_remaining',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'status',
            'offered_booking_id', 'offer_expires_at', 'offer_message',
            'accepted_booking_id',
            'created_at', 'updated_at',
        ]

    def get_is_active(self, obj) -> bool:
        """Check if entry is still active."""
        return obj.status in [
            WaitlistEntry.Status.WAITING,
            WaitlistEntry.Status.OFFERED
        ]

    def get_days_waiting(self, obj) -> int:
        """Get number of days on waitlist."""
        if obj.status == WaitlistEntry.Status.WAITING:
            return (timezone.now().date() - obj.created_at.date()).days
        return 0

    def get_time_remaining(self, obj) -> str | None:
        """Get time remaining for offer response."""
        if obj.status == WaitlistEntry.Status.OFFERED and obj.offer_expires_at:
            remaining = obj.offer_expires_at - timezone.now()
            if remaining.total_seconds() > 0:
                hours = int(remaining.total_seconds() // 3600)
                minutes = int((remaining.total_seconds() % 3600) // 60)
                return f"{hours}h {minutes}m"
            return "Expired"
        return None


class WaitlistEntryListSerializer(WaitlistEntrySerializer):
    """Optimized serializer for waitlist lists."""

    class Meta(WaitlistEntrySerializer.Meta):
        fields = [
            'id', 'user_id', 'user_name',
            'requested_date',
            'preferred_start_time', 'preferred_end_time',
            'booking_type', 'booking_type_display',
            'aircraft_id', 'instructor_id',
            'priority', 'status', 'status_display',
            'is_active', 'days_waiting',
            'offer_expires_at', 'time_remaining',
        ]


class WaitlistEntryDetailSerializer(WaitlistEntrySerializer):
    """Detailed waitlist entry serializer."""

    matching_slots = serializers.SerializerMethodField()
    position = serializers.SerializerMethodField()

    class Meta(WaitlistEntrySerializer.Meta):
        fields = WaitlistEntrySerializer.Meta.fields + [
            'matching_slots', 'position',
            'cancelled_at', 'cancelled_reason',
        ]

    def get_matching_slots(self, obj) -> list:
        """Get available slots matching this request."""
        if obj.status != WaitlistEntry.Status.WAITING:
            return []

        from apps.core.services import AvailabilityService
        availability_service = AvailabilityService()

        try:
            slots = availability_service.get_available_slots(
                organization_id=obj.organization_id,
                target_date=obj.requested_date,
                duration_minutes=obj.duration_minutes or 60,
                aircraft_id=obj.aircraft_id if not obj.any_aircraft else None,
                instructor_id=obj.instructor_id if not obj.any_instructor else None,
                location_id=obj.location_id,
            )
            return slots[:5]  # Return up to 5 matching slots
        except Exception:
            return []

    def get_position(self, obj) -> int | None:
        """Get position in waitlist queue."""
        if obj.status != WaitlistEntry.Status.WAITING:
            return None

        # Count entries with higher priority or earlier creation
        ahead = WaitlistEntry.objects.filter(
            organization_id=obj.organization_id,
            requested_date=obj.requested_date,
            status=WaitlistEntry.Status.WAITING
        ).filter(
            models.Q(priority__gt=obj.priority) |
            models.Q(priority=obj.priority, created_at__lt=obj.created_at)
        ).count()

        return ahead + 1


class WaitlistEntryCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating waitlist entries."""

    check_availability = serializers.BooleanField(
        default=True,
        write_only=True,
        help_text="Check for immediate availability before adding to waitlist"
    )

    class Meta:
        model = WaitlistEntry
        fields = [
            'organization_id', 'user_id',
            'user_name', 'user_email',
            'requested_date',
            'preferred_start_time', 'preferred_end_time',
            'duration_minutes', 'booking_type',
            'aircraft_id', 'instructor_id', 'location_id',
            'any_aircraft', 'any_instructor',
            'flexibility_days', 'flexibility_hours',
            'priority', 'notes',
            'check_availability',
        ]

    def validate(self, attrs):
        """Validate waitlist entry."""
        requested_date = attrs.get('requested_date')

        if requested_date and requested_date < timezone.now().date():
            raise serializers.ValidationError({
                'requested_date': "Requested date cannot be in the past"
            })

        # Validate time range
        start_time = attrs.get('preferred_start_time')
        end_time = attrs.get('preferred_end_time')
        if start_time and end_time and end_time <= start_time:
            raise serializers.ValidationError({
                'preferred_end_time': "End time must be after start time"
            })

        # Validate flexibility
        flexibility_days = attrs.get('flexibility_days', 0)
        if flexibility_days < 0 or flexibility_days > 30:
            raise serializers.ValidationError({
                'flexibility_days': "Flexibility must be 0-30 days"
            })

        # Can't specify both specific resource and any resource
        if attrs.get('aircraft_id') and attrs.get('any_aircraft'):
            raise serializers.ValidationError({
                'any_aircraft': "Cannot specify both aircraft_id and any_aircraft"
            })

        if attrs.get('instructor_id') and attrs.get('any_instructor'):
            raise serializers.ValidationError({
                'any_instructor': "Cannot specify both instructor_id and any_instructor"
            })

        return attrs


class WaitlistEntryUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating waitlist entries."""

    class Meta:
        model = WaitlistEntry
        fields = [
            'requested_date',
            'preferred_start_time', 'preferred_end_time',
            'duration_minutes',
            'aircraft_id', 'instructor_id', 'location_id',
            'any_aircraft', 'any_instructor',
            'flexibility_days', 'flexibility_hours',
            'priority', 'notes',
        ]

    def validate(self, attrs):
        """Validate update data."""
        instance = self.instance

        if instance and instance.status != WaitlistEntry.Status.WAITING:
            raise serializers.ValidationError(
                "Can only update entries in waiting status"
            )

        return attrs


class WaitlistOfferSerializer(serializers.Serializer):
    """Serializer for sending offers to waitlist entries."""

    booking_id = serializers.UUIDField(
        help_text="ID of the booking being offered"
    )
    message = serializers.CharField(
        required=False,
        max_length=500,
        help_text="Message to include with the offer"
    )
    expires_in_hours = serializers.IntegerField(
        min_value=1,
        max_value=48,
        default=4,
        help_text="Hours until offer expires"
    )


class WaitlistOfferResponseSerializer(serializers.Serializer):
    """Serializer for responding to waitlist offers."""

    action = serializers.ChoiceField(
        choices=['accept', 'decline']
    )
    notes = serializers.CharField(
        required=False,
        max_length=500
    )


class WaitlistCancelSerializer(serializers.Serializer):
    """Serializer for cancelling waitlist entries."""

    reason = serializers.CharField(
        required=False,
        max_length=500
    )


class WaitlistStatisticsSerializer(serializers.Serializer):
    """Serializer for waitlist statistics."""

    total = serializers.IntegerField()
    waiting = serializers.IntegerField()
    offered = serializers.IntegerField()
    accepted = serializers.IntegerField()
    declined = serializers.IntegerField()
    expired = serializers.IntegerField()
    fulfilled = serializers.IntegerField()
    cancelled = serializers.IntegerField()
    fulfillment_rate = serializers.FloatField()
    acceptance_rate = serializers.FloatField()
    average_wait_days = serializers.FloatField(required=False)


class WaitlistMatchSerializer(serializers.Serializer):
    """Serializer for waitlist matching results."""

    entry_id = serializers.UUIDField()
    user_id = serializers.UUIDField()
    user_name = serializers.CharField()
    priority = serializers.IntegerField()
    requested_date = serializers.DateField()
    preferred_start_time = serializers.TimeField(allow_null=True)
    preferred_end_time = serializers.TimeField(allow_null=True)
    flexibility_days = serializers.IntegerField()
    match_score = serializers.FloatField(
        help_text="Score indicating how well slot matches request (0-100)"
    )


class WaitlistProcessCancellationSerializer(serializers.Serializer):
    """Serializer for processing cancellation and notifying waitlist."""

    cancelled_booking_id = serializers.UUIDField()
    auto_offer = serializers.BooleanField(
        default=True,
        help_text="Automatically send offer to top waitlist entry"
    )
    notify_all = serializers.BooleanField(
        default=False,
        help_text="Notify all matching waitlist entries"
    )


# Import models at the end to avoid circular imports
from django.db import models
