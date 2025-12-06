# services/certificate-service/src/apps/core/api/serializers/flight_review_serializers.py
"""
Flight Review API Serializers
"""

from rest_framework import serializers
from ...models import (
    FlightReview,
    FlightReviewType,
    FlightReviewResult,
    FlightReviewStatus,
    SkillTest,
)


class FlightReviewSerializer(serializers.ModelSerializer):
    """Serializer for FlightReview model."""

    review_type_display = serializers.CharField(
        source='get_review_type_display',
        read_only=True
    )
    result_display = serializers.CharField(
        source='get_result_display',
        read_only=True
    )
    is_valid = serializers.BooleanField(read_only=True)
    is_expired = serializers.BooleanField(read_only=True)
    is_expiring_soon = serializers.BooleanField(read_only=True)
    days_until_expiry = serializers.IntegerField(read_only=True)
    total_time_hours = serializers.FloatField(read_only=True)

    class Meta:
        model = FlightReview
        fields = [
            'id',
            'organization_id',
            'user_id',
            'review_type',
            'review_type_display',
            'rating_id',
            'certificate_id',
            'aircraft_type',
            'aircraft_icao',
            'review_date',
            'completion_date',
            'expiry_date',
            'result',
            'result_display',
            'status',
            'instructor_id',
            'instructor_name',
            'instructor_certificate_number',
            'ground_time_hours',
            'flight_time_hours',
            'simulator_time_hours',
            'total_time_hours',
            'aircraft_registration',
            'aircraft_id',
            'topics_covered',
            'maneuvers_performed',
            'areas_satisfactory',
            'areas_for_improvement',
            'unsatisfactory_items',
            'instructor_comments',
            'recommendations',
            'regulatory_reference',
            'logbook_entry_text',
            'document_url',
            'verified',
            'verified_at',
            'is_valid',
            'is_expired',
            'is_expiring_soon',
            'days_until_expiry',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'expiry_date',
            'logbook_entry_text',
            'verified',
            'verified_at',
            'created_at',
            'updated_at',
        ]


class FlightReviewCreateSerializer(serializers.Serializer):
    """Serializer for creating a flight review."""

    review_type = serializers.ChoiceField(choices=FlightReviewType.choices)
    review_date = serializers.DateField()
    instructor_id = serializers.UUIDField()
    instructor_name = serializers.CharField(max_length=255)
    instructor_certificate_number = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True
    )

    result = serializers.ChoiceField(
        choices=FlightReviewResult.choices,
        default=FlightReviewResult.PASSED
    )

    # Training time
    ground_time_hours = serializers.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=1.0
    )
    flight_time_hours = serializers.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=1.0
    )
    simulator_time_hours = serializers.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=0.0
    )

    # Aircraft
    aircraft_type = serializers.CharField(max_length=50, required=False, allow_blank=True)
    aircraft_icao = serializers.CharField(max_length=4, required=False, allow_blank=True)
    aircraft_registration = serializers.CharField(max_length=20, required=False, allow_blank=True)
    aircraft_id = serializers.UUIDField(required=False, allow_null=True)

    # References
    rating_id = serializers.UUIDField(required=False, allow_null=True)
    certificate_id = serializers.UUIDField(required=False, allow_null=True)
    flight_id = serializers.UUIDField(required=False, allow_null=True)

    # Topics and maneuvers
    topics_covered = serializers.ListField(
        child=serializers.CharField(max_length=255),
        required=False,
        default=list
    )
    maneuvers_performed = serializers.ListField(
        child=serializers.CharField(max_length=255),
        required=False,
        default=list
    )
    areas_satisfactory = serializers.ListField(
        child=serializers.CharField(max_length=255),
        required=False,
        default=list
    )
    areas_for_improvement = serializers.ListField(
        child=serializers.CharField(max_length=255),
        required=False,
        default=list
    )
    unsatisfactory_items = serializers.ListField(
        child=serializers.CharField(max_length=255),
        required=False,
        default=list
    )

    # Comments
    instructor_comments = serializers.CharField(required=False, allow_blank=True)
    recommendations = serializers.CharField(required=False, allow_blank=True)
    regulatory_reference = serializers.CharField(max_length=100, required=False, allow_blank=True)

    # Document
    document_url = serializers.URLField(required=False, allow_blank=True)


class SkillTestSerializer(serializers.ModelSerializer):
    """Serializer for SkillTest model."""

    test_type_display = serializers.CharField(
        source='get_test_type_display',
        read_only=True
    )
    result_display = serializers.CharField(
        source='get_result_display',
        read_only=True
    )
    is_passed = serializers.BooleanField(read_only=True)

    class Meta:
        model = SkillTest
        fields = [
            'id',
            'organization_id',
            'user_id',
            'test_type',
            'test_type_display',
            'test_date',
            'result',
            'result_display',
            'is_passed',
            'examiner_id',
            'examiner_name',
            'examiner_number',
            'examiner_authority',
            'aircraft_type',
            'aircraft_icao',
            'aircraft_registration',
            'is_simulator',
            'simulator_level',
            'oral_time_hours',
            'flight_time_hours',
            'test_sections',
            'failed_sections',
            'application_number',
            'iacra_number',
            'certificate_issued',
            'certificate_id',
            'rating_id',
            'temporary_certificate_number',
            'examiner_comments',
            'retest_requirements',
            'document_url',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class SkillTestCreateSerializer(serializers.Serializer):
    """Serializer for creating a skill test record."""

    test_type = serializers.ChoiceField(choices=SkillTest.TestType.choices)
    test_date = serializers.DateField()
    result = serializers.ChoiceField(choices=SkillTest.TestResult.choices)

    # Examiner
    examiner_id = serializers.UUIDField()
    examiner_name = serializers.CharField(max_length=255)
    examiner_number = serializers.CharField(max_length=100)
    examiner_authority = serializers.CharField(max_length=50, required=False, allow_blank=True)

    # Aircraft
    aircraft_type = serializers.CharField(max_length=50)
    aircraft_icao = serializers.CharField(max_length=4, required=False, allow_blank=True)
    aircraft_registration = serializers.CharField(max_length=20, required=False, allow_blank=True)
    is_simulator = serializers.BooleanField(default=False)
    simulator_level = serializers.CharField(max_length=20, required=False, allow_blank=True)

    # Time
    oral_time_hours = serializers.DecimalField(max_digits=4, decimal_places=2, default=0)
    flight_time_hours = serializers.DecimalField(max_digits=4, decimal_places=2, default=0)

    # Test details
    test_sections = serializers.DictField(required=False, default=dict)
    failed_sections = serializers.ListField(
        child=serializers.CharField(max_length=255),
        required=False,
        default=list
    )

    # Application
    application_number = serializers.CharField(max_length=100, required=False, allow_blank=True)
    iacra_number = serializers.CharField(max_length=100, required=False, allow_blank=True)

    # Comments
    examiner_comments = serializers.CharField(required=False, allow_blank=True)
    retest_requirements = serializers.CharField(required=False, allow_blank=True)

    # Document
    document_url = serializers.URLField(required=False, allow_blank=True)


class FlightReviewValiditySerializer(serializers.Serializer):
    """Serializer for flight review validity check."""

    is_valid = serializers.BooleanField()
    error_code = serializers.CharField(required=False, allow_null=True)
    message = serializers.CharField(required=False, allow_null=True)
    warning = serializers.CharField(required=False, allow_null=True)
    bfr = FlightReviewSerializer(required=False, allow_null=True)


class FlightReviewVerifySerializer(serializers.Serializer):
    """Serializer for verifying flight review."""

    notes = serializers.CharField(required=False, allow_blank=True)
