# services/certificate-service/src/apps/core/api/serializers/endorsement_serializers.py
"""
Endorsement Serializers

API serializers for endorsement management.
"""

from rest_framework import serializers

from ...models import (
    Endorsement,
    EndorsementType,
    EndorsementStatus,
)


class EndorsementSerializer(serializers.ModelSerializer):
    """Full endorsement serializer."""

    endorsement_type_display = serializers.CharField(
        source='get_endorsement_type_display',
        read_only=True
    )
    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )
    is_valid = serializers.BooleanField(read_only=True)
    is_expired = serializers.BooleanField(read_only=True)
    is_signed = serializers.BooleanField(read_only=True)
    days_until_expiry = serializers.IntegerField(read_only=True)

    class Meta:
        model = Endorsement
        fields = [
            'id',
            'organization_id',
            'student_id',
            'student_name',
            'instructor_id',
            'instructor_name',
            'endorsement_type',
            'endorsement_type_display',
            'endorsement_code',
            'description',
            'endorsement_text',
            'aircraft_type',
            'aircraft_registration',
            'aircraft_icao',
            'airports',
            'area_description',
            'route',
            'issue_date',
            'expiry_date',
            'is_permanent',
            'validity_days',
            'conditions',
            'limitations',
            'weather_minimums',
            'day_night_restriction',
            'instructor_signature',
            'signed_at',
            'instructor_certificate_number',
            'instructor_certificate_expiry',
            'status',
            'status_display',
            'related_flight_id',
            'related_lesson_id',
            'notes',
            'is_valid',
            'is_expired',
            'is_signed',
            'days_until_expiry',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'organization_id',
            'instructor_signature',
            'signed_at',
            'instructor_certificate_number',
            'instructor_certificate_expiry',
            'status',
            'created_at',
            'updated_at',
        ]


class EndorsementCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating endorsements."""

    class Meta:
        model = Endorsement
        fields = [
            'student_id',
            'student_name',
            'instructor_id',
            'instructor_name',
            'endorsement_type',
            'endorsement_code',
            'description',
            'endorsement_text',
            'aircraft_type',
            'aircraft_registration',
            'aircraft_icao',
            'airports',
            'area_description',
            'route',
            'issue_date',
            'expiry_date',
            'is_permanent',
            'validity_days',
            'conditions',
            'limitations',
            'weather_minimums',
            'day_night_restriction',
            'related_flight_id',
            'related_lesson_id',
            'notes',
        ]

    def validate_endorsement_type(self, value):
        """Validate endorsement type."""
        if value not in EndorsementType.values:
            raise serializers.ValidationError(
                f'Invalid endorsement type. Must be one of: {EndorsementType.values}'
            )
        return value

    def validate(self, attrs):
        """Cross-field validation."""
        is_permanent = attrs.get('is_permanent', False)
        validity_days = attrs.get('validity_days')
        expiry_date = attrs.get('expiry_date')

        if not is_permanent and not validity_days and not expiry_date:
            raise serializers.ValidationError(
                'Must specify validity_days or expiry_date for non-permanent endorsements'
            )

        return attrs


class EndorsementListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for endorsement lists."""

    endorsement_type_display = serializers.CharField(
        source='get_endorsement_type_display',
        read_only=True
    )
    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )
    is_valid = serializers.BooleanField(read_only=True)
    is_signed = serializers.BooleanField(read_only=True)
    days_until_expiry = serializers.IntegerField(read_only=True)

    class Meta:
        model = Endorsement
        fields = [
            'id',
            'student_id',
            'student_name',
            'instructor_id',
            'instructor_name',
            'endorsement_type',
            'endorsement_type_display',
            'aircraft_type',
            'issue_date',
            'expiry_date',
            'is_permanent',
            'status',
            'status_display',
            'is_valid',
            'is_signed',
            'days_until_expiry',
        ]


class EndorsementSignSerializer(serializers.Serializer):
    """Serializer for signing an endorsement."""

    signature_data = serializers.DictField(
        help_text='Digital signature data'
    )

    def validate_signature_data(self, value):
        """Validate signature data has required fields."""
        if not value.get('signature'):
            raise serializers.ValidationError(
                'signature_data must include a signature field'
            )
        return value


class SoloEndorsementCreateSerializer(serializers.Serializer):
    """Serializer for creating a solo endorsement."""

    student_id = serializers.UUIDField()
    student_name = serializers.CharField()
    instructor_id = serializers.UUIDField()
    instructor_name = serializers.CharField()
    aircraft_type = serializers.CharField()
    validity_days = serializers.IntegerField(default=90)
    airports = serializers.ListField(
        child=serializers.CharField(),
        required=False
    )
    conditions = serializers.ListField(
        child=serializers.CharField(),
        required=False
    )
    weather_minimums = serializers.DictField(required=False)


class SoloAuthorizationCheckSerializer(serializers.Serializer):
    """Serializer for solo authorization check request."""

    student_id = serializers.UUIDField()
    aircraft_type = serializers.CharField(required=False)


class SoloAuthorizationResponseSerializer(serializers.Serializer):
    """Serializer for solo authorization check response."""

    authorized = serializers.BooleanField()
    message = serializers.CharField()
    endorsement = serializers.DictField(allow_null=True)
    conditions = serializers.ListField(required=False)
    limitations = serializers.CharField(required=False, allow_null=True)
    airports = serializers.ListField(required=False)
