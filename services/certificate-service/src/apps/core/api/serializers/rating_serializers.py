# services/certificate-service/src/apps/core/api/serializers/rating_serializers.py
"""
Rating Serializers

API serializers for rating/privilege management.
"""

from rest_framework import serializers

from ...models import (
    Rating,
    RatingType,
    RatingStatus,
)


class RatingSerializer(serializers.ModelSerializer):
    """Full rating serializer."""

    rating_type_display = serializers.CharField(
        source='get_rating_type_display',
        read_only=True
    )
    is_valid = serializers.BooleanField(read_only=True)
    is_expired = serializers.BooleanField(read_only=True)
    is_proficiency_due = serializers.BooleanField(read_only=True)
    days_until_expiry = serializers.IntegerField(read_only=True)
    days_until_proficiency = serializers.IntegerField(read_only=True)

    class Meta:
        model = Rating
        fields = [
            'id',
            'organization_id',
            'user_id',
            'certificate_id',
            'rating_type',
            'rating_type_display',
            'rating_code',
            'rating_name',
            'aircraft_type_id',
            'aircraft_icao',
            'aircraft_name',
            'issue_date',
            'expiry_date',
            'last_proficiency_date',
            'next_proficiency_date',
            'validity_period_months',
            'proficiency_check_months',
            'status',
            'restrictions',
            'training_organization',
            'training_completion_date',
            'examiner_id',
            'examiner_name',
            'skill_test_date',
            'operating_minima',
            'pic_hours_on_type',
            'total_hours_on_type',
            'document_url',
            'notes',
            'is_valid',
            'is_expired',
            'is_proficiency_due',
            'days_until_expiry',
            'days_until_proficiency',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'organization_id',
            'created_at',
            'updated_at',
        ]


class RatingCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating ratings."""

    class Meta:
        model = Rating
        fields = [
            'user_id',
            'certificate_id',
            'rating_type',
            'rating_code',
            'rating_name',
            'aircraft_type_id',
            'aircraft_icao',
            'aircraft_name',
            'issue_date',
            'expiry_date',
            'validity_period_months',
            'proficiency_check_months',
            'restrictions',
            'training_organization',
            'training_completion_date',
            'examiner_id',
            'examiner_name',
            'skill_test_date',
            'operating_minima',
            'document_url',
            'notes',
        ]

    def validate_rating_type(self, value):
        """Validate rating type."""
        if value not in RatingType.values:
            raise serializers.ValidationError(
                f'Invalid rating type. Must be one of: {RatingType.values}'
            )
        return value

    def validate(self, attrs):
        """Cross-field validation."""
        rating_type = attrs.get('rating_type')

        # Type rating requires aircraft info
        if rating_type == RatingType.AIRCRAFT_TYPE:
            if not attrs.get('aircraft_icao') and not attrs.get('aircraft_name'):
                raise serializers.ValidationError({
                    'aircraft_icao': 'Aircraft type rating requires aircraft ICAO code or name'
                })

        return attrs


class RatingListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for rating lists."""

    rating_type_display = serializers.CharField(
        source='get_rating_type_display',
        read_only=True
    )
    is_valid = serializers.BooleanField(read_only=True)
    days_until_expiry = serializers.IntegerField(read_only=True)

    class Meta:
        model = Rating
        fields = [
            'id',
            'user_id',
            'rating_type',
            'rating_type_display',
            'rating_name',
            'aircraft_icao',
            'issue_date',
            'expiry_date',
            'next_proficiency_date',
            'status',
            'is_valid',
            'days_until_expiry',
        ]


class ProficiencyCheckSerializer(serializers.Serializer):
    """Serializer for recording a proficiency check."""

    check_date = serializers.DateField()
    examiner_id = serializers.UUIDField()
    examiner_name = serializers.CharField()
    passed = serializers.BooleanField(default=True)
    notes = serializers.CharField(required=False, allow_blank=True)


class RatingRenewSerializer(serializers.Serializer):
    """Serializer for renewing a rating."""

    new_expiry_date = serializers.DateField()
    proficiency_date = serializers.DateField(required=False)


class TypeRatingCheckSerializer(serializers.Serializer):
    """Serializer for type rating check request."""

    user_id = serializers.UUIDField()
    aircraft_icao = serializers.CharField()


class TypeRatingCheckResponseSerializer(serializers.Serializer):
    """Serializer for type rating check response."""

    has_rating = serializers.BooleanField()
    is_valid = serializers.BooleanField(required=False)
    message = serializers.CharField()
    rating = serializers.DictField(allow_null=True)
