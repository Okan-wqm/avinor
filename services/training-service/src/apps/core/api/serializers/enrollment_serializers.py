# services/training-service/src/apps/core/api/serializers/enrollment_serializers.py
"""
Enrollment Serializers

Serializers for student enrollment API endpoints.
"""

from rest_framework import serializers
from decimal import Decimal

from ...models import StudentEnrollment, TrainingProgram


class EnrollmentHoursSerializer(serializers.Serializer):
    """Serializer for enrollment hours."""

    flight = serializers.DecimalField(max_digits=6, decimal_places=2)
    ground = serializers.DecimalField(max_digits=6, decimal_places=2)
    simulator = serializers.DecimalField(max_digits=6, decimal_places=2)
    total = serializers.DecimalField(max_digits=6, decimal_places=2, read_only=True)
    dual = serializers.DecimalField(max_digits=6, decimal_places=2)
    solo = serializers.DecimalField(max_digits=6, decimal_places=2)
    pic = serializers.DecimalField(max_digits=6, decimal_places=2)
    cross_country = serializers.DecimalField(max_digits=6, decimal_places=2)
    night = serializers.DecimalField(max_digits=6, decimal_places=2)
    instrument = serializers.DecimalField(max_digits=6, decimal_places=2)


class EnrollmentProgressSerializer(serializers.Serializer):
    """Serializer for enrollment progress."""

    lessons_completed = serializers.IntegerField()
    lessons_total = serializers.IntegerField()
    completion_percentage = serializers.DecimalField(max_digits=5, decimal_places=2)
    progress_status = serializers.CharField()


class StudentEnrollmentSerializer(serializers.ModelSerializer):
    """Base serializer for student enrollments."""

    program_info = serializers.SerializerMethodField()
    hours = serializers.SerializerMethodField()
    progress = serializers.SerializerMethodField()
    is_active = serializers.BooleanField(read_only=True)
    is_completed = serializers.BooleanField(read_only=True)
    days_enrolled = serializers.IntegerField(read_only=True)
    days_remaining = serializers.IntegerField(read_only=True)
    current_stage_name = serializers.CharField(read_only=True)
    total_training_hours = serializers.DecimalField(
        max_digits=6, decimal_places=2, read_only=True
    )

    class Meta:
        model = StudentEnrollment
        fields = [
            'id', 'organization_id', 'student_id', 'program', 'program_info',
            'primary_instructor_id', 'secondary_instructor_ids',
            'enrollment_number', 'enrollment_date', 'start_date',
            'expected_completion', 'actual_completion', 'expiry_date',
            'status', 'hold_reason', 'hold_date',
            'withdrawal_reason', 'withdrawal_date',
            'current_stage_id', 'current_stage_name', 'current_lesson_id',
            'total_flight_hours', 'total_ground_hours', 'total_simulator_hours',
            'dual_hours', 'solo_hours', 'pic_hours',
            'cross_country_hours', 'night_hours', 'instrument_hours',
            'lessons_completed', 'lessons_total', 'completion_percentage',
            'exercises_completed', 'exercises_total',
            'average_grade', 'stage_checks_passed', 'stage_checks_failed',
            'total_paid', 'total_charges', 'balance', 'currency',
            'notes', 'instructor_notes', 'metadata', 'training_records_url',
            'hours', 'progress', 'is_active', 'is_completed',
            'days_enrolled', 'days_remaining', 'total_training_hours',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'organization_id', 'enrollment_number',
            'lessons_completed', 'lessons_total', 'completion_percentage',
            'exercises_completed', 'exercises_total', 'average_grade',
            'stage_checks_passed', 'stage_checks_failed',
            'created_at', 'updated_at',
        ]

    def get_program_info(self, obj):
        """Get program info."""
        return {
            'id': str(obj.program.id),
            'code': obj.program.code,
            'name': obj.program.name,
            'program_type': obj.program.program_type,
        }

    def get_hours(self, obj):
        """Get hours breakdown."""
        return {
            'flight': float(obj.total_flight_hours),
            'ground': float(obj.total_ground_hours),
            'simulator': float(obj.total_simulator_hours),
            'total': float(obj.total_training_hours),
            'dual': float(obj.dual_hours),
            'solo': float(obj.solo_hours),
            'pic': float(obj.pic_hours),
            'cross_country': float(obj.cross_country_hours),
            'night': float(obj.night_hours),
            'instrument': float(obj.instrument_hours),
        }

    def get_progress(self, obj):
        """Get progress info."""
        return {
            'lessons_completed': obj.lessons_completed,
            'lessons_total': obj.lessons_total,
            'completion_percentage': float(obj.completion_percentage),
            'status': obj.progress_status,
        }


class StudentEnrollmentCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating student enrollments."""

    class Meta:
        model = StudentEnrollment
        fields = [
            'student_id', 'program', 'enrollment_date',
            'primary_instructor_id', 'secondary_instructor_ids',
            'expected_completion', 'notes', 'metadata',
        ]

    def validate(self, data):
        """Validate enrollment data."""
        student_id = data.get('student_id')
        program = data.get('program')

        # Check for existing active enrollment
        if StudentEnrollment.objects.filter(
            student_id=student_id,
            program=program,
            status__in=['pending', 'active', 'on_hold']
        ).exists():
            raise serializers.ValidationError(
                "Student is already enrolled in this program"
            )

        return data

    def validate_program(self, value):
        """Validate program is published."""
        if not value.is_published:
            raise serializers.ValidationError(
                "Cannot enroll in unpublished program"
            )
        return value


class StudentEnrollmentUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating student enrollments."""

    class Meta:
        model = StudentEnrollment
        fields = [
            'primary_instructor_id', 'secondary_instructor_ids',
            'expected_completion', 'notes', 'instructor_notes',
            'metadata', 'training_records_url',
        ]


class StudentEnrollmentDetailSerializer(StudentEnrollmentSerializer):
    """Detailed serializer for student enrollments."""

    hour_requirements = serializers.SerializerMethodField()
    progress_summary = serializers.SerializerMethodField()

    class Meta(StudentEnrollmentSerializer.Meta):
        fields = StudentEnrollmentSerializer.Meta.fields + [
            'hour_requirements', 'progress_summary',
        ]

    def get_hour_requirements(self, obj):
        """Get hour requirements check."""
        return obj.check_hour_requirements()

    def get_progress_summary(self, obj):
        """Get progress summary."""
        return obj.get_progress_summary()


class StudentEnrollmentListSerializer(serializers.ModelSerializer):
    """Serializer for listing student enrollments."""

    program_code = serializers.CharField(source='program.code', read_only=True)
    program_name = serializers.CharField(source='program.name', read_only=True)
    progress_percentage = serializers.DecimalField(
        source='completion_percentage',
        max_digits=5, decimal_places=2, read_only=True
    )
    total_hours = serializers.DecimalField(
        source='total_training_hours',
        max_digits=6, decimal_places=2, read_only=True
    )

    class Meta:
        model = StudentEnrollment
        fields = [
            'id', 'enrollment_number', 'student_id',
            'program', 'program_code', 'program_name',
            'status', 'enrollment_date', 'start_date',
            'progress_percentage', 'total_hours',
            'primary_instructor_id',
        ]


class EnrollmentStatusChangeSerializer(serializers.Serializer):
    """Serializer for enrollment status changes."""

    reason = serializers.CharField(required=False, allow_null=True)


class EnrollmentActivateSerializer(serializers.Serializer):
    """Serializer for activating enrollment."""

    start_date = serializers.DateField(required=False, allow_null=True)


class EnrollmentHoldSerializer(serializers.Serializer):
    """Serializer for putting enrollment on hold."""

    reason = serializers.CharField()


class EnrollmentWithdrawSerializer(serializers.Serializer):
    """Serializer for withdrawing enrollment."""

    reason = serializers.CharField()


class EnrollmentCompleteSerializer(serializers.Serializer):
    """Serializer for completing enrollment."""

    completion_date = serializers.DateField(required=False, allow_null=True)


class InstructorAssignmentSerializer(serializers.Serializer):
    """Serializer for instructor assignment."""

    instructor_id = serializers.UUIDField()


class AddHoursSerializer(serializers.Serializer):
    """Serializer for manually adding hours."""

    flight_hours = serializers.DecimalField(
        max_digits=5, decimal_places=2, required=False, allow_null=True
    )
    ground_hours = serializers.DecimalField(
        max_digits=5, decimal_places=2, required=False, allow_null=True
    )
    simulator_hours = serializers.DecimalField(
        max_digits=5, decimal_places=2, required=False, allow_null=True
    )
    dual_hours = serializers.DecimalField(
        max_digits=5, decimal_places=2, required=False, allow_null=True
    )
    solo_hours = serializers.DecimalField(
        max_digits=5, decimal_places=2, required=False, allow_null=True
    )
    pic_hours = serializers.DecimalField(
        max_digits=5, decimal_places=2, required=False, allow_null=True
    )
    cross_country_hours = serializers.DecimalField(
        max_digits=5, decimal_places=2, required=False, allow_null=True
    )
    night_hours = serializers.DecimalField(
        max_digits=5, decimal_places=2, required=False, allow_null=True
    )
    instrument_hours = serializers.DecimalField(
        max_digits=5, decimal_places=2, required=False, allow_null=True
    )


class PaymentRecordSerializer(serializers.Serializer):
    """Serializer for recording payment."""

    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    payment_reference = serializers.CharField(required=False, allow_null=True)


class ChargeRecordSerializer(serializers.Serializer):
    """Serializer for recording charge."""

    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    description = serializers.CharField(required=False, allow_null=True)


class StudentEnrollmentsSummarySerializer(serializers.Serializer):
    """Serializer for student enrollments summary."""

    student_id = serializers.UUIDField()
    enrollments = serializers.DictField()
    total_hours = serializers.DictField()
    programs = serializers.ListField(child=serializers.DictField())
