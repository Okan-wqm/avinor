# services/flight-service/src/apps/api/serializers/flight_serializers.py
"""
Flight Serializers

REST API serializers for Flight model operations.
"""

from decimal import Decimal
from rest_framework import serializers

from apps.core.models import Flight, Approach, Hold


class FlightListSerializer(serializers.ModelSerializer):
    """Serializer for flight list view (minimal fields)."""

    total_landings = serializers.IntegerField(read_only=True)
    is_signed = serializers.BooleanField(read_only=True)
    flight_type_display = serializers.CharField(
        source='get_flight_type_display', read_only=True
    )
    flight_status_display = serializers.CharField(
        source='get_flight_status_display', read_only=True
    )

    class Meta:
        model = Flight
        fields = [
            'id',
            'flight_date',
            'aircraft_id',
            'aircraft_registration',
            'aircraft_type',
            'departure_airport',
            'arrival_airport',
            'flight_type',
            'flight_type_display',
            'flight_rules',
            'flight_time',
            'block_time',
            'total_landings',
            'flight_status',
            'flight_status_display',
            'pic_id',
            'sic_id',
            'instructor_id',
            'student_id',
            'is_signed',
            'created_at',
        ]
        read_only_fields = fields


class FlightDetailSerializer(serializers.ModelSerializer):
    """Serializer for flight detail view (all fields)."""

    total_landings = serializers.IntegerField(read_only=True)
    total_full_stops = serializers.IntegerField(read_only=True)
    total_instrument_time = serializers.DecimalField(
        max_digits=5, decimal_places=2, read_only=True
    )
    is_signed = serializers.BooleanField(read_only=True)
    is_approved = serializers.BooleanField(read_only=True)
    is_training_flight = serializers.BooleanField(read_only=True)
    display_route = serializers.CharField(read_only=True)

    # Related data counts
    approach_count = serializers.IntegerField(read_only=True)
    holds = serializers.IntegerField(read_only=True)

    # Display names
    flight_type_display = serializers.CharField(
        source='get_flight_type_display', read_only=True
    )
    flight_rules_display = serializers.CharField(
        source='get_flight_rules_display', read_only=True
    )
    flight_category_display = serializers.CharField(
        source='get_flight_category_display', read_only=True
    )
    flight_status_display = serializers.CharField(
        source='get_flight_status_display', read_only=True
    )
    billing_status_display = serializers.CharField(
        source='get_billing_status_display', read_only=True
    )

    class Meta:
        model = Flight
        fields = '__all__'
        read_only_fields = [
            'id',
            'organization_id',
            'created_by',
            'created_at',
            'updated_at',
            'flight_time',
            'block_time',
            'submitted_at',
            'submitted_by',
            'approved_at',
            'approved_by',
            'rejected_at',
            'rejected_by',
            'cancelled_at',
            'cancelled_by',
            'pic_signed_at',
            'instructor_signed_at',
            'student_signed_at',
        ]


class FlightCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new flights."""

    approaches = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        write_only=True
    )
    holds = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        write_only=True
    )
    fuel_records = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        write_only=True
    )

    class Meta:
        model = Flight
        fields = [
            # Core fields
            'flight_date',
            'aircraft_id',
            'aircraft_registration',
            'aircraft_type',
            'departure_airport',
            'arrival_airport',
            'via_airports',
            'route',
            # Type and rules
            'flight_type',
            'flight_rules',
            'flight_category',
            'training_type',
            # Crew
            'pic_id',
            'sic_id',
            'instructor_id',
            'student_id',
            'examiner_id',
            'crew_members',
            'passengers',
            # Times
            'block_off',
            'takeoff_time',
            'landing_time',
            'block_on',
            'hobbs_start',
            'hobbs_end',
            'tach_start',
            'tach_end',
            # Time splits
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
            # Landings
            'landings_day',
            'landings_night',
            'full_stop_day',
            'full_stop_night',
            # Conditions
            'weather_conditions',
            'weather_remarks',
            # Remarks
            'remarks',
            'instructor_comments',
            # Related data
            'approaches',
            'holds',
            'fuel_records',
            # Booking reference
            'booking_id',
        ]

    def validate_flight_date(self, value):
        """Validate flight date is not in the future."""
        from datetime import date
        if value > date.today():
            raise serializers.ValidationError(
                "Flight date cannot be in the future."
            )
        return value

    def validate(self, data):
        """Cross-field validation."""
        # Validate times
        if data.get('block_off') and data.get('block_on'):
            if data['block_on'] <= data['block_off']:
                raise serializers.ValidationError({
                    'block_on': "Block on must be after block off."
                })

        if data.get('takeoff_time') and data.get('landing_time'):
            if data['landing_time'] <= data['takeoff_time']:
                raise serializers.ValidationError({
                    'landing_time': "Landing time must be after takeoff time."
                })

        # Validate hobbs
        if data.get('hobbs_start') and data.get('hobbs_end'):
            if data['hobbs_end'] < data['hobbs_start']:
                raise serializers.ValidationError({
                    'hobbs_end': "Hobbs end must be greater than or equal to start."
                })

        # Validate tach
        if data.get('tach_start') and data.get('tach_end'):
            if data['tach_end'] < data['tach_start']:
                raise serializers.ValidationError({
                    'tach_end': "Tach end must be greater than or equal to start."
                })

        # Validate crew
        if not data.get('pic_id') and not data.get('student_id'):
            raise serializers.ValidationError(
                "Either PIC or student is required."
            )

        # Validate training flight has instructor
        if data.get('flight_type') == Flight.FlightType.TRAINING:
            if not data.get('instructor_id') and not data.get('student_id'):
                raise serializers.ValidationError({
                    'instructor_id': "Training flights require an instructor or student."
                })

        return data


class FlightUpdateSerializer(FlightCreateSerializer):
    """Serializer for updating existing flights."""

    class Meta(FlightCreateSerializer.Meta):
        # All fields optional for partial updates
        extra_kwargs = {
            field: {'required': False}
            for field in FlightCreateSerializer.Meta.fields
        }

    def validate(self, data):
        """Validate update is allowed."""
        instance = self.instance
        if instance and instance.flight_status not in [
            Flight.Status.DRAFT, Flight.Status.REJECTED
        ]:
            raise serializers.ValidationError(
                "Only draft or rejected flights can be edited."
            )
        return super().validate(data)


class FlightSubmitSerializer(serializers.Serializer):
    """Serializer for flight submission."""

    class Meta:
        fields = []

    def validate(self, data):
        """Validate flight can be submitted."""
        instance = self.instance
        if instance:
            errors = []

            if not instance.aircraft_id:
                errors.append("Aircraft is required.")

            if not instance.departure_airport:
                errors.append("Departure airport is required.")

            if not instance.pic_id and not instance.student_id:
                errors.append("PIC or student is required.")

            if not instance.block_off or not instance.block_on:
                errors.append("Block times are required.")

            if errors:
                raise serializers.ValidationError(errors)

        return data


class FlightApproveSerializer(serializers.Serializer):
    """Serializer for flight approval."""

    remarks = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=500
    )


class FlightRejectSerializer(serializers.Serializer):
    """Serializer for flight rejection."""

    reason = serializers.CharField(
        required=True,
        max_length=500,
        help_text="Reason for rejection"
    )


class FlightSignatureSerializer(serializers.Serializer):
    """Serializer for flight signatures."""

    signature_data = serializers.DictField(
        required=True,
        help_text="Signature data (SVG, base64 image, etc.)"
    )
    role = serializers.ChoiceField(
        choices=['pic', 'instructor', 'student'],
        required=True
    )
    endorsements = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        help_text="Endorsements (for instructor signatures)"
    )


class FlightCancelSerializer(serializers.Serializer):
    """Serializer for flight cancellation."""

    reason = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=500,
        help_text="Cancellation reason"
    )


class FlightSquawkSerializer(serializers.Serializer):
    """Serializer for adding squawks to flights."""

    squawk_id = serializers.UUIDField(
        required=True,
        help_text="Squawk/discrepancy ID"
    )


class FlightBulkActionSerializer(serializers.Serializer):
    """Serializer for bulk flight actions."""

    flight_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=True,
        min_length=1,
        max_length=100
    )
    action = serializers.ChoiceField(
        choices=['submit', 'approve', 'reject', 'cancel'],
        required=True
    )
    reason = serializers.CharField(
        required=False,
        max_length=500
    )

    def validate(self, data):
        """Validate bulk action data."""
        if data['action'] == 'reject' and not data.get('reason'):
            raise serializers.ValidationError({
                'reason': "Reason is required for rejection."
            })
        return data


class FlightFilterSerializer(serializers.Serializer):
    """Serializer for flight list filters."""

    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)
    status = serializers.ListField(
        child=serializers.ChoiceField(choices=Flight.Status.choices),
        required=False
    )
    aircraft_id = serializers.UUIDField(required=False)
    pilot_id = serializers.UUIDField(required=False)
    flight_type = serializers.ChoiceField(
        choices=Flight.FlightType.choices,
        required=False
    )
    flight_rules = serializers.ChoiceField(
        choices=Flight.FlightRules.choices,
        required=False
    )
    departure_airport = serializers.CharField(max_length=4, required=False)
    arrival_airport = serializers.CharField(max_length=4, required=False)
    booking_id = serializers.UUIDField(required=False)
    billing_status = serializers.ChoiceField(
        choices=Flight.BillingStatus.choices,
        required=False
    )
    search = serializers.CharField(max_length=100, required=False)

    def validate(self, data):
        """Validate date range."""
        if data.get('start_date') and data.get('end_date'):
            if data['end_date'] < data['start_date']:
                raise serializers.ValidationError({
                    'end_date': "End date must be after start date."
                })
        return data
