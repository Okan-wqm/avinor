# services/certificate-service/src/apps/core/api/serializers/validity_serializers.py
"""
Validity Check Serializers

API serializers for comprehensive validity checking.
"""

from rest_framework import serializers


class ValidityCheckSerializer(serializers.Serializer):
    """Serializer for validity check request."""

    user_id = serializers.UUIDField()
    operation_type = serializers.ChoiceField(
        choices=[
            ('vfr_day', 'VFR Day'),
            ('vfr_night', 'VFR Night'),
            ('ifr', 'IFR'),
            ('solo', 'Solo'),
            ('dual', 'Dual'),
            ('pic', 'Pilot in Command'),
            ('instructor', 'Instructor'),
            ('examiner', 'Examiner'),
        ],
        required=False
    )
    aircraft_type = serializers.CharField(required=False)
    aircraft_icao = serializers.CharField(required=False)
    check_currency = serializers.BooleanField(default=True)
    check_medical = serializers.BooleanField(default=True)
    check_ratings = serializers.BooleanField(default=True)
    check_endorsements = serializers.BooleanField(default=True)


class ValidityCheckResponseSerializer(serializers.Serializer):
    """Serializer for validity check response."""

    is_valid = serializers.BooleanField()
    message = serializers.CharField()
    checked_at = serializers.DateTimeField()

    # Individual validity results
    certificate_valid = serializers.BooleanField()
    certificate_message = serializers.CharField(allow_null=True)

    medical_valid = serializers.BooleanField()
    medical_message = serializers.CharField(allow_null=True)
    medical_expiry = serializers.DateField(allow_null=True)

    ratings_valid = serializers.BooleanField()
    ratings_message = serializers.CharField(allow_null=True)
    missing_ratings = serializers.ListField(
        child=serializers.CharField(),
        required=False
    )

    currency_valid = serializers.BooleanField()
    currency_message = serializers.CharField(allow_null=True)
    currency_deficiencies = serializers.ListField(
        child=serializers.DictField(),
        required=False
    )

    endorsements_valid = serializers.BooleanField()
    endorsements_message = serializers.CharField(allow_null=True)

    # Warnings and recommendations
    warnings = serializers.ListField(
        child=serializers.CharField(),
        required=False
    )
    recommendations = serializers.ListField(
        child=serializers.CharField(),
        required=False
    )


class UserSummarySerializer(serializers.Serializer):
    """Comprehensive user certification summary serializer."""

    user_id = serializers.UUIDField()
    summary_date = serializers.DateTimeField()

    # Overall status
    overall_valid = serializers.BooleanField()
    overall_message = serializers.CharField()

    # Certificates section
    certificates = serializers.DictField(
        child=serializers.DictField()
    )
    active_certificate_count = serializers.IntegerField()
    expiring_certificates = serializers.ListField(
        child=serializers.DictField()
    )

    # Medical section
    medical = serializers.DictField(allow_null=True)
    medical_status = serializers.CharField()
    medical_days_remaining = serializers.IntegerField(allow_null=True)

    # Ratings section
    ratings = serializers.ListField(
        child=serializers.DictField()
    )
    active_rating_count = serializers.IntegerField()
    expiring_ratings = serializers.ListField(
        child=serializers.DictField()
    )

    # Endorsements section
    endorsements = serializers.ListField(
        child=serializers.DictField()
    )
    active_endorsement_count = serializers.IntegerField()
    pending_endorsements = serializers.ListField(
        child=serializers.DictField()
    )

    # Currency section
    currency_statuses = serializers.ListField(
        child=serializers.DictField()
    )
    overall_currency = serializers.BooleanField()
    currency_deficiencies = serializers.ListField(
        child=serializers.DictField()
    )

    # Action items
    action_required = serializers.ListField(
        child=serializers.DictField()
    )
    upcoming_expirations = serializers.ListField(
        child=serializers.DictField()
    )


class FlightValidityCheckSerializer(serializers.Serializer):
    """Serializer for pre-flight validity check."""

    user_id = serializers.UUIDField()
    flight_date = serializers.DateField()
    flight_type = serializers.ChoiceField(
        choices=[
            ('vfr_day', 'VFR Day'),
            ('vfr_night', 'VFR Night'),
            ('ifr', 'IFR'),
            ('training', 'Training'),
            ('solo', 'Solo'),
            ('checkride', 'Check Ride'),
        ]
    )
    aircraft_type = serializers.CharField()
    aircraft_icao = serializers.CharField(required=False)
    role = serializers.ChoiceField(
        choices=[
            ('pic', 'Pilot in Command'),
            ('sic', 'Second in Command'),
            ('student', 'Student Pilot'),
            ('instructor', 'Instructor'),
            ('examiner', 'Examiner'),
        ]
    )
    is_night = serializers.BooleanField(default=False)
    is_cross_country = serializers.BooleanField(default=False)
    carrying_passengers = serializers.BooleanField(default=False)


class FlightValidityResponseSerializer(serializers.Serializer):
    """Serializer for pre-flight validity check response."""

    authorized = serializers.BooleanField()
    authorization_message = serializers.CharField()
    flight_date = serializers.DateField()
    checked_at = serializers.DateTimeField()

    # Detailed results
    pilot_status = serializers.DictField()
    aircraft_authorization = serializers.DictField()
    operational_limitations = serializers.ListField(
        child=serializers.CharField()
    )
    weather_limitations = serializers.ListField(
        child=serializers.CharField()
    )

    # Blocking issues (must be resolved)
    blocking_issues = serializers.ListField(
        child=serializers.DictField()
    )

    # Warnings (may proceed with caution)
    warnings = serializers.ListField(
        child=serializers.DictField()
    )

    # Required endorsements
    required_endorsements = serializers.ListField(
        child=serializers.CharField()
    )
    has_required_endorsements = serializers.BooleanField()


class ExpirationAlertSerializer(serializers.Serializer):
    """Serializer for expiration alerts."""

    alert_type = serializers.ChoiceField(
        choices=[
            ('certificate', 'Certificate'),
            ('medical', 'Medical'),
            ('rating', 'Rating'),
            ('endorsement', 'Endorsement'),
            ('currency', 'Currency'),
        ]
    )
    item_id = serializers.UUIDField()
    item_name = serializers.CharField()
    expiry_date = serializers.DateField()
    days_remaining = serializers.IntegerField()
    severity = serializers.ChoiceField(
        choices=[
            ('info', 'Info'),
            ('warning', 'Warning'),
            ('critical', 'Critical'),
            ('expired', 'Expired'),
        ]
    )
    message = serializers.CharField()
    action_required = serializers.CharField()


class OrganizationComplianceSerializer(serializers.Serializer):
    """Serializer for organization-wide compliance summary."""

    organization_id = serializers.UUIDField()
    report_date = serializers.DateTimeField()

    # Overall statistics
    total_pilots = serializers.IntegerField()
    fully_compliant = serializers.IntegerField()
    partially_compliant = serializers.IntegerField()
    non_compliant = serializers.IntegerField()
    compliance_percentage = serializers.FloatField()

    # Breakdown by issue type
    medical_issues = serializers.ListField(
        child=serializers.DictField()
    )
    certificate_issues = serializers.ListField(
        child=serializers.DictField()
    )
    rating_issues = serializers.ListField(
        child=serializers.DictField()
    )
    currency_issues = serializers.ListField(
        child=serializers.DictField()
    )

    # Upcoming expirations
    expiring_this_week = serializers.IntegerField()
    expiring_this_month = serializers.IntegerField()
    expiring_next_month = serializers.IntegerField()

    # Detailed expiration list
    upcoming_expirations = serializers.ListField(
        child=serializers.DictField()
    )


class StudentProgressSerializer(serializers.Serializer):
    """Serializer for student pilot progress summary."""

    student_id = serializers.UUIDField()
    student_name = serializers.CharField()
    report_date = serializers.DateTimeField()

    # Certificate status
    student_certificate = serializers.DictField(allow_null=True)
    medical_status = serializers.DictField(allow_null=True)

    # Endorsements
    endorsements_received = serializers.ListField(
        child=serializers.DictField()
    )
    endorsements_pending = serializers.ListField(
        child=serializers.DictField()
    )

    # Solo authorization
    solo_authorized = serializers.BooleanField()
    solo_endorsement = serializers.DictField(allow_null=True)
    solo_limitations = serializers.ListField(
        child=serializers.CharField()
    )

    # Training progress
    checkride_eligible = serializers.BooleanField()
    checkride_requirements_met = serializers.DictField()
    checkride_requirements_missing = serializers.ListField(
        child=serializers.CharField()
    )


class InstructorValiditySerializer(serializers.Serializer):
    """Serializer for instructor validity check."""

    instructor_id = serializers.UUIDField()
    check_date = serializers.DateTimeField()

    # Basic validity
    is_valid = serializers.BooleanField()
    message = serializers.CharField()

    # Certificate status
    instructor_certificate = serializers.DictField(allow_null=True)
    certificate_valid = serializers.BooleanField()
    certificate_expiry = serializers.DateField(allow_null=True)

    # Medical status
    medical = serializers.DictField(allow_null=True)
    medical_valid = serializers.BooleanField()
    medical_expiry = serializers.DateField(allow_null=True)

    # Flight Review / BFR
    flight_review_current = serializers.BooleanField()
    flight_review_expiry = serializers.DateField(allow_null=True)

    # Currency
    currency_current = serializers.BooleanField()
    currency_details = serializers.ListField(
        child=serializers.DictField()
    )

    # Authorized activities
    authorized_instruction = serializers.ListField(
        child=serializers.CharField()
    )
    limitations = serializers.ListField(
        child=serializers.CharField()
    )
