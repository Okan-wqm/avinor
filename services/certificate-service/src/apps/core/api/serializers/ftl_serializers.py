# services/certificate-service/src/apps/core/api/serializers/ftl_serializers.py
"""
Flight Time Limitations (FTL) API Serializers
"""

from rest_framework import serializers
from ...models import (
    FTLConfiguration,
    DutyPeriod,
    DutyType,
    RestPeriod,
    FTLViolation,
    FTLViolationType,
    PilotFTLSummary,
    FTLStandard,
)


class FTLConfigurationSerializer(serializers.ModelSerializer):
    """Serializer for FTL Configuration."""

    ftl_standard_display = serializers.CharField(
        source='get_ftl_standard_display',
        read_only=True
    )

    class Meta:
        model = FTLConfiguration
        fields = [
            'id',
            'organization_id',
            'ftl_standard',
            'ftl_standard_display',
            # Flight time limits
            'max_flight_time_daily',
            'max_flight_time_7_days',
            'max_flight_time_28_days',
            'max_flight_time_calendar_year',
            # FDP limits
            'max_fdp_standard',
            'max_fdp_extended',
            'fdp_extension_allowed',
            'fdp_extension_requires_augmented',
            # Duty limits
            'max_duty_period',
            'max_duty_7_days',
            'max_duty_14_days',
            'max_duty_28_days',
            # Rest requirements
            'min_rest_between_duties',
            'min_rest_after_fdp',
            'min_weekly_rest',
            'days_off_per_7_days',
            'days_off_per_14_days',
            # Night operations
            'night_start',
            'night_end',
            'fdp_reduction_night',
            # Split duty
            'split_duty_allowed',
            'min_split_rest',
            'fdp_extension_per_split_hour',
            # Standby
            'standby_counts_as_duty',
            'airport_standby_max',
            # FRM
            'frm_enabled',
            'fatigue_reporting_required',
            # Meta
            'effective_date',
            'notes',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'organization_id', 'created_at', 'updated_at']


class DutyPeriodSerializer(serializers.ModelSerializer):
    """Serializer for Duty Period."""

    duty_type_display = serializers.CharField(
        source='get_duty_type_display',
        read_only=True
    )
    is_flight_duty = serializers.BooleanField(read_only=True)

    class Meta:
        model = DutyPeriod
        fields = [
            'id',
            'organization_id',
            'user_id',
            'duty_type',
            'duty_type_display',
            'duty_date',
            'start_time',
            'end_time',
            'start_time_local',
            'end_time_local',
            'timezone',
            'duration_hours',
            'flight_time_hours',
            'sectors',
            'start_location',
            'end_location',
            'is_completed',
            'is_planned',
            'is_augmented',
            'augmentation_type',
            'rest_facility_class',
            'split_rest_start',
            'split_rest_end',
            'split_rest_hours',
            'flight_ids',
            'is_flight_duty',
            'notes',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'duration_hours',
            'is_completed',
            'created_at',
            'updated_at',
        ]


class DutyPeriodStartSerializer(serializers.Serializer):
    """Serializer for starting a duty period."""

    duty_type = serializers.ChoiceField(choices=DutyType.choices)
    start_time = serializers.DateTimeField()
    start_location = serializers.CharField(max_length=4, required=False, allow_blank=True)
    is_planned = serializers.BooleanField(default=False)
    is_augmented = serializers.BooleanField(default=False)
    timezone_name = serializers.CharField(max_length=50, default='UTC')


class DutyPeriodEndSerializer(serializers.Serializer):
    """Serializer for ending a duty period."""

    end_time = serializers.DateTimeField()
    end_location = serializers.CharField(max_length=4, required=False, allow_blank=True)
    flight_time_hours = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        required=False
    )
    sectors = serializers.IntegerField(min_value=0, required=False)
    flight_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        default=list
    )
    notes = serializers.CharField(required=False, allow_blank=True)


class RestPeriodSerializer(serializers.ModelSerializer):
    """Serializer for Rest Period."""

    class Meta:
        model = RestPeriod
        fields = [
            'id',
            'organization_id',
            'user_id',
            'rest_date',
            'start_time',
            'end_time',
            'duration_hours',
            'is_reduced_rest',
            'is_split_duty_rest',
            'is_weekly_rest',
            'location',
            'accommodation_type',
            'is_suitable_accommodation',
            'preceding_duty',
            'following_duty',
            'notes',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'duration_hours',
            'created_at',
            'updated_at',
        ]


class RestPeriodCreateSerializer(serializers.Serializer):
    """Serializer for creating a rest period."""

    start_time = serializers.DateTimeField()
    end_time = serializers.DateTimeField(required=False, allow_null=True)
    location = serializers.CharField(max_length=4, required=False, allow_blank=True)
    accommodation_type = serializers.CharField(max_length=50, required=False, allow_blank=True)
    is_suitable_accommodation = serializers.BooleanField(default=True)
    is_reduced_rest = serializers.BooleanField(default=False)
    is_weekly_rest = serializers.BooleanField(default=False)
    preceding_duty_id = serializers.UUIDField(required=False, allow_null=True)


class FTLViolationSerializer(serializers.ModelSerializer):
    """Serializer for FTL Violation."""

    violation_type_display = serializers.CharField(
        source='get_violation_type_display',
        read_only=True
    )
    severity_display = serializers.CharField(
        source='get_severity_display',
        read_only=True
    )

    class Meta:
        model = FTLViolation
        fields = [
            'id',
            'organization_id',
            'user_id',
            'violation_type',
            'violation_type_display',
            'violation_date',
            'detected_at',
            'limit_name',
            'limit_value',
            'actual_value',
            'exceeded_by',
            'period_start',
            'period_end',
            'severity',
            'severity_display',
            'duty_period',
            'flight_ids',
            'is_resolved',
            'resolved_at',
            'resolved_by',
            'resolution_notes',
            'commander_discretion',
            'discretion_reason',
            'reported_to_authority',
            'authority_report_date',
            'authority_reference',
            'notes',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'detected_at',
            'created_at',
            'updated_at',
        ]


class FTLViolationResolveSerializer(serializers.Serializer):
    """Serializer for resolving an FTL violation."""

    resolution_notes = serializers.CharField(required=False, allow_blank=True)
    commander_discretion = serializers.BooleanField(default=False)
    discretion_reason = serializers.CharField(required=False, allow_blank=True)


class PilotFTLSummarySerializer(serializers.ModelSerializer):
    """Serializer for Pilot FTL Summary."""

    current_status_display = serializers.CharField(
        source='get_current_status_display',
        read_only=True
    )

    class Meta:
        model = PilotFTLSummary
        fields = [
            'id',
            'organization_id',
            'user_id',
            'flight_time_today',
            'flight_time_7_days',
            'flight_time_28_days',
            'flight_time_calendar_year',
            'duty_time_7_days',
            'duty_time_14_days',
            'duty_time_28_days',
            'last_fdp_end',
            'last_fdp_duration',
            'last_rest_start',
            'last_rest_end',
            'last_rest_duration',
            'days_off_last_7',
            'days_off_last_14',
            'last_weekly_rest_date',
            'current_status',
            'current_status_display',
            'next_available',
            'max_fdp_available',
            'is_compliant',
            'compliance_issues',
            'last_calculated',
        ]
        read_only_fields = fields


class FTLComplianceCheckSerializer(serializers.Serializer):
    """Serializer for FTL compliance check response."""

    user_id = serializers.UUIDField()
    is_compliant = serializers.BooleanField()
    flight_time = serializers.DictField()
    duty_time = serializers.DictField()
    limits = serializers.DictField()
    issues = serializers.ListField(child=serializers.DictField())
    warnings = serializers.ListField(child=serializers.DictField())
    checked_at = serializers.DateTimeField()


class FTLPlanValidationSerializer(serializers.Serializer):
    """Serializer for validating planned duty."""

    start_time = serializers.DateTimeField()
    estimated_duration_hours = serializers.DecimalField(max_digits=4, decimal_places=2)
    estimated_flight_time_hours = serializers.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=0
    )
    is_augmented = serializers.BooleanField(default=False)


class FTLPlanValidationResponseSerializer(serializers.Serializer):
    """Serializer for plan validation response."""

    is_valid = serializers.BooleanField()
    can_schedule = serializers.BooleanField()
    max_fdp_available = serializers.FloatField()
    issues = serializers.ListField(child=serializers.DictField())
    warnings = serializers.ListField(child=serializers.DictField())
