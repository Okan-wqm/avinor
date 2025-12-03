# services/training-service/src/apps/core/api/serializers/stage_check_serializers.py
"""
Stage Check Serializers

Serializers for stage check API endpoints.
"""

from rest_framework import serializers
from decimal import Decimal

from ...models import StageCheck


class OralTopicSerializer(serializers.Serializer):
    """Serializer for oral examination topic."""

    topic = serializers.CharField()
    grade = serializers.FloatField()
    notes = serializers.CharField(required=False, allow_null=True)


class FlightManeuverSerializer(serializers.Serializer):
    """Serializer for flight maneuver."""

    maneuver = serializers.CharField()
    grade = serializers.FloatField()
    tolerances = serializers.DictField(required=False, allow_null=True)
    notes = serializers.CharField(required=False, allow_null=True)


class StageCheckSerializer(serializers.ModelSerializer):
    """Base serializer for stage checks."""

    stage_name = serializers.CharField(read_only=True)
    is_final_attempt = serializers.BooleanField(read_only=True)
    can_retry = serializers.BooleanField(read_only=True)
    total_check_time = serializers.DecimalField(
        max_digits=5, decimal_places=2, read_only=True
    )
    duration_minutes = serializers.IntegerField(read_only=True)
    enrollment_info = serializers.SerializerMethodField()

    class Meta:
        model = StageCheck
        fields = [
            'id', 'organization_id', 'enrollment', 'enrollment_info',
            'stage_id', 'stage_name', 'examiner_id',
            'recommending_instructor_id',
            'check_type', 'check_number',
            'scheduled_date', 'scheduled_time', 'location',
            'actual_date', 'actual_start_time', 'actual_end_time',
            'aircraft_id', 'flight_record_id',
            'flight_time', 'ground_time', 'total_check_time',
            'weather_conditions',
            'status', 'result', 'is_passed',
            'oral_grade', 'flight_grade', 'overall_grade', 'min_passing_grade',
            'attempt_number', 'max_attempts', 'previous_attempt_id',
            'is_final_attempt', 'can_retry',
            'prerequisites_verified', 'prerequisites_verification_date',
            'prerequisites_notes',
            'oral_topics', 'oral_duration_minutes',
            'flight_maneuvers', 'flight_areas', 'special_emphasis_areas',
            'examiner_comments', 'areas_of_concern', 'recommendations',
            'additional_training_required',
            'disapproval_reasons', 'recheck_items',
            'remedial_training_completed', 'remedial_training_date',
            'remedial_training_hours',
            'examiner_signoff', 'examiner_signoff_date',
            'student_signoff', 'student_signoff_date',
            'form_number', 'document_url',
            'cancellation_reason', 'cancelled_by_id', 'cancelled_at',
            'metadata', 'notes', 'duration_minutes',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'organization_id', 'check_number',
            'attempt_number', 'previous_attempt_id',
            'is_passed', 'prerequisites_verified',
            'prerequisites_verification_date',
            'examiner_signoff', 'examiner_signoff_date',
            'student_signoff', 'student_signoff_date',
            'cancelled_at',
            'created_at', 'updated_at',
        ]

    def get_enrollment_info(self, obj):
        """Get enrollment info."""
        return {
            'id': str(obj.enrollment.id),
            'enrollment_number': obj.enrollment.enrollment_number,
            'student_id': str(obj.enrollment.student_id),
            'program_code': obj.enrollment.program.code,
        }


class StageCheckCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating stage checks."""

    class Meta:
        model = StageCheck
        fields = [
            'enrollment', 'stage_id', 'check_type',
            'scheduled_date', 'scheduled_time', 'location',
            'examiner_id', 'recommending_instructor_id',
            'min_passing_grade', 'max_attempts',
            'metadata', 'notes',
        ]

    def validate(self, data):
        """Validate stage check data."""
        enrollment = data.get('enrollment')
        stage_id = data.get('stage_id')

        # Verify stage exists in program
        stage = enrollment.program.get_stage(str(stage_id))
        if not stage:
            raise serializers.ValidationError(
                f"Stage {stage_id} not found in program"
            )

        # Check for existing active stage check
        existing = StageCheck.objects.filter(
            enrollment=enrollment,
            stage_id=stage_id,
            status__in=['scheduled', 'in_progress']
        ).first()

        if existing:
            raise serializers.ValidationError(
                f"Stage check already {existing.status} for this stage"
            )

        return data


class StageCheckUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating stage checks."""

    class Meta:
        model = StageCheck
        fields = [
            'scheduled_date', 'scheduled_time', 'location',
            'examiner_id', 'aircraft_id',
            'weather_conditions',
            'examiner_comments', 'recommendations',
            'form_number', 'document_url',
            'metadata', 'notes',
        ]


class StageCheckDetailSerializer(StageCheckSerializer):
    """Detailed serializer for stage checks."""

    summary = serializers.SerializerMethodField()

    class Meta(StageCheckSerializer.Meta):
        fields = StageCheckSerializer.Meta.fields + ['summary']

    def get_summary(self, obj):
        """Get stage check summary."""
        return obj.get_summary()


class StageCheckListSerializer(serializers.ModelSerializer):
    """Serializer for listing stage checks."""

    stage_name = serializers.CharField(read_only=True)
    enrollment_number = serializers.CharField(
        source='enrollment.enrollment_number', read_only=True
    )

    class Meta:
        model = StageCheck
        fields = [
            'id', 'check_number', 'enrollment', 'enrollment_number',
            'stage_id', 'stage_name', 'check_type',
            'scheduled_date', 'actual_date',
            'status', 'result', 'is_passed',
            'overall_grade', 'attempt_number', 'examiner_id',
        ]


class ScheduleStageCheckSerializer(serializers.Serializer):
    """Serializer for scheduling a stage check."""

    scheduled_date = serializers.DateField()
    scheduled_time = serializers.TimeField(required=False, allow_null=True)
    examiner_id = serializers.UUIDField(required=False, allow_null=True)
    location = serializers.CharField(required=False, allow_null=True)


class StageCheckResultSerializer(serializers.Serializer):
    """Serializer for stage check result."""

    result = serializers.ChoiceField(choices=['pass', 'fail'])
    overall_grade = serializers.DecimalField(
        max_digits=5, decimal_places=2, required=False, allow_null=True
    )
    oral_grade = serializers.DecimalField(
        max_digits=5, decimal_places=2, required=False, allow_null=True
    )
    flight_grade = serializers.DecimalField(
        max_digits=5, decimal_places=2, required=False, allow_null=True
    )
    examiner_comments = serializers.CharField(required=False, allow_null=True)
    recommendations = serializers.CharField(required=False, allow_null=True)


class PassStageCheckSerializer(serializers.Serializer):
    """Serializer for passing a stage check."""

    overall_grade = serializers.DecimalField(
        max_digits=5, decimal_places=2, required=False, allow_null=True
    )
    oral_grade = serializers.DecimalField(
        max_digits=5, decimal_places=2, required=False, allow_null=True
    )
    flight_grade = serializers.DecimalField(
        max_digits=5, decimal_places=2, required=False, allow_null=True
    )
    examiner_comments = serializers.CharField(required=False, allow_null=True)
    recommendations = serializers.CharField(required=False, allow_null=True)


class FailStageCheckSerializer(serializers.Serializer):
    """Serializer for failing a stage check."""

    disapproval_reasons = serializers.ListField(
        child=serializers.CharField(), required=False, allow_null=True
    )
    recheck_items = serializers.ListField(
        child=serializers.CharField(), required=False, allow_null=True
    )
    additional_training = serializers.ListField(
        child=serializers.CharField(), required=False, allow_null=True
    )
    examiner_comments = serializers.CharField(required=False, allow_null=True)
    oral_grade = serializers.DecimalField(
        max_digits=5, decimal_places=2, required=False, allow_null=True
    )
    flight_grade = serializers.DecimalField(
        max_digits=5, decimal_places=2, required=False, allow_null=True
    )


class DeferStageCheckSerializer(serializers.Serializer):
    """Serializer for deferring a stage check."""

    reason = serializers.CharField()


class CancelStageCheckSerializer(serializers.Serializer):
    """Serializer for cancelling a stage check."""

    reason = serializers.CharField()


class RemedialTrainingSerializer(serializers.Serializer):
    """Serializer for recording remedial training."""

    training_date = serializers.DateField()
    hours = serializers.DecimalField(max_digits=5, decimal_places=2)


class CreateRecheckSerializer(serializers.Serializer):
    """Serializer for creating a recheck."""

    scheduled_date = serializers.DateField(required=False, allow_null=True)
    examiner_id = serializers.UUIDField(required=False, allow_null=True)


class VerifyPrerequisitesSerializer(serializers.Serializer):
    """Serializer for verifying prerequisites."""

    notes = serializers.CharField(required=False, allow_null=True)


class StageCheckStatisticsSerializer(serializers.Serializer):
    """Serializer for stage check statistics."""

    total = serializers.IntegerField()
    completed = serializers.IntegerField()
    passed = serializers.IntegerField()
    failed = serializers.IntegerField()
    cancelled = serializers.IntegerField()
    deferred = serializers.IntegerField()
    pass_rate = serializers.FloatField()
    first_attempt_pass_rate = serializers.FloatField()
    average_grades = serializers.DictField()
