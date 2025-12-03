# services/training-service/src/apps/core/api/serializers/completion_serializers.py
"""
Completion Serializers

Serializers for lesson completion and exercise grading API endpoints.
"""

from rest_framework import serializers
from decimal import Decimal

from ...models import LessonCompletion, ExerciseGrade


class ExerciseGradeSerializer(serializers.ModelSerializer):
    """Serializer for exercise grades."""

    exercise_info = serializers.SerializerMethodField()
    is_within_tolerances = serializers.BooleanField(read_only=True)
    demonstration_success_rate = serializers.FloatField(read_only=True)

    class Meta:
        model = ExerciseGrade
        fields = [
            'id', 'organization_id', 'completion', 'exercise', 'exercise_info',
            'grade', 'competency_grade', 'letter_grade', 'is_passed',
            'weight', 'demonstrations', 'successful_demonstrations',
            'performance_notes', 'deviations', 'competency_scores',
            'is_within_tolerances', 'demonstration_success_rate',
            'graded_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'organization_id', 'is_passed',
            'graded_at', 'updated_at',
        ]

    def get_exercise_info(self, obj):
        """Get exercise info."""
        return {
            'id': str(obj.exercise.id),
            'code': obj.exercise.code,
            'name': obj.exercise.name,
            'is_required': obj.exercise.is_required,
            'is_critical': obj.exercise.is_critical,
        }


class ExerciseGradeCreateSerializer(serializers.Serializer):
    """Serializer for creating/updating exercise grades."""

    exercise_id = serializers.UUIDField()
    grade = serializers.DecimalField(
        max_digits=5, decimal_places=2, required=False, allow_null=True
    )
    competency_grade = serializers.CharField(
        max_length=1, required=False, allow_null=True
    )
    demonstrations = serializers.IntegerField(required=False, default=1)
    successful_demonstrations = serializers.IntegerField(required=False, default=0)
    performance_notes = serializers.CharField(required=False, allow_null=True)
    deviations = serializers.DictField(required=False, allow_null=True)
    competency_scores = serializers.DictField(required=False, allow_null=True)


class ExerciseGradeListSerializer(serializers.ModelSerializer):
    """Serializer for listing exercise grades."""

    exercise_code = serializers.CharField(source='exercise.code', read_only=True)
    exercise_name = serializers.CharField(source='exercise.name', read_only=True)

    class Meta:
        model = ExerciseGrade
        fields = [
            'id', 'exercise', 'exercise_code', 'exercise_name',
            'grade', 'competency_grade', 'is_passed',
        ]


class LessonCompletionSerializer(serializers.ModelSerializer):
    """Base serializer for lesson completions."""

    lesson_info = serializers.SerializerMethodField()
    exercise_grades = ExerciseGradeListSerializer(many=True, read_only=True)
    total_time = serializers.DecimalField(
        max_digits=5, decimal_places=2, read_only=True
    )
    total_landings = serializers.IntegerField(read_only=True)
    is_passed = serializers.BooleanField(read_only=True)
    exercise_grades_summary = serializers.DictField(read_only=True)

    class Meta:
        model = LessonCompletion
        fields = [
            'id', 'organization_id', 'enrollment', 'lesson', 'lesson_info',
            'instructor_id', 'flight_record_id', 'aircraft_id', 'booking_id',
            'scheduled_date', 'scheduled_start_time', 'scheduled_end_time',
            'actual_date', 'actual_start_time', 'actual_end_time',
            'flight_time', 'ground_time', 'simulator_time', 'briefing_time',
            'dual_time', 'solo_time', 'pic_time', 'cross_country_time',
            'night_time', 'instrument_time', 'instrument_actual',
            'instrument_simulated',
            'landings_day', 'landings_night', 'total_landings',
            'status', 'is_completed', 'completion_date', 'result',
            'grade', 'grade_letter', 'attempt_number', 'is_repeat',
            'previous_attempt_id',
            'instructor_signoff', 'instructor_signoff_date',
            'instructor_signoff_notes',
            'student_signoff', 'student_signoff_date',
            'instructor_comments', 'student_notes',
            'areas_of_improvement', 'strengths',
            'weather_conditions',
            'cancellation_reason', 'cancelled_by_id', 'cancelled_at',
            'metadata',
            'exercise_grades', 'total_time', 'is_passed',
            'exercise_grades_summary',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'organization_id', 'attempt_number', 'is_repeat',
            'is_completed', 'completion_date',
            'instructor_signoff', 'instructor_signoff_date',
            'student_signoff', 'student_signoff_date',
            'cancelled_at',
            'created_at', 'updated_at',
        ]

    def get_lesson_info(self, obj):
        """Get lesson info."""
        return {
            'id': str(obj.lesson.id),
            'code': obj.lesson.code,
            'name': obj.lesson.name,
            'lesson_type': obj.lesson.lesson_type,
            'min_grade_to_pass': obj.lesson.min_grade_to_pass,
        }


class LessonCompletionCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating lesson completions."""

    class Meta:
        model = LessonCompletion
        fields = [
            'enrollment', 'lesson', 'instructor_id',
            'scheduled_date', 'scheduled_start_time', 'scheduled_end_time',
            'aircraft_id', 'booking_id',
            'metadata',
        ]

    def validate(self, data):
        """Validate completion data."""
        enrollment = data.get('enrollment')
        lesson = data.get('lesson')

        # Verify lesson belongs to enrollment's program
        if lesson.program_id != enrollment.program_id:
            raise serializers.ValidationError(
                "Lesson does not belong to enrollment's program"
            )

        # Check for existing in-progress completion
        existing = LessonCompletion.objects.filter(
            enrollment=enrollment,
            lesson=lesson,
            status__in=['scheduled', 'in_progress']
        ).first()

        if existing:
            raise serializers.ValidationError(
                f"Lesson already has a {existing.status} completion record"
            )

        return data


class LessonCompletionUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating lesson completions."""

    class Meta:
        model = LessonCompletion
        fields = [
            'instructor_id', 'flight_record_id', 'aircraft_id',
            'scheduled_date', 'scheduled_start_time', 'scheduled_end_time',
            'actual_date', 'actual_start_time', 'actual_end_time',
            'flight_time', 'ground_time', 'simulator_time', 'briefing_time',
            'dual_time', 'solo_time', 'pic_time', 'cross_country_time',
            'night_time', 'instrument_time', 'instrument_actual',
            'instrument_simulated',
            'landings_day', 'landings_night',
            'instructor_comments', 'student_notes',
            'areas_of_improvement', 'strengths',
            'weather_conditions', 'metadata',
        ]


class LessonCompletionDetailSerializer(LessonCompletionSerializer):
    """Detailed serializer for lesson completions."""

    exercise_grades = ExerciseGradeSerializer(many=True, read_only=True)
    enrollment_info = serializers.SerializerMethodField()

    class Meta(LessonCompletionSerializer.Meta):
        fields = LessonCompletionSerializer.Meta.fields + ['enrollment_info']

    def get_enrollment_info(self, obj):
        """Get enrollment info."""
        return {
            'id': str(obj.enrollment.id),
            'enrollment_number': obj.enrollment.enrollment_number,
            'student_id': str(obj.enrollment.student_id),
            'program_code': obj.enrollment.program.code,
        }


class LessonCompletionListSerializer(serializers.ModelSerializer):
    """Serializer for listing lesson completions."""

    lesson_code = serializers.CharField(source='lesson.code', read_only=True)
    lesson_name = serializers.CharField(source='lesson.name', read_only=True)
    lesson_type = serializers.CharField(source='lesson.lesson_type', read_only=True)
    total_time = serializers.DecimalField(
        max_digits=5, decimal_places=2, read_only=True
    )

    class Meta:
        model = LessonCompletion
        fields = [
            'id', 'lesson', 'lesson_code', 'lesson_name', 'lesson_type',
            'instructor_id', 'scheduled_date', 'actual_date',
            'status', 'is_completed', 'result', 'grade',
            'total_time', 'attempt_number',
        ]


class StartLessonSerializer(serializers.Serializer):
    """Serializer for starting a lesson."""

    instructor_id = serializers.UUIDField(required=False, allow_null=True)


class CompleteLessonSerializer(serializers.Serializer):
    """Serializer for completing a lesson."""

    grade = serializers.DecimalField(
        max_digits=5, decimal_places=2, required=False, allow_null=True
    )
    result = serializers.ChoiceField(
        choices=LessonCompletion.CompletionResult.choices,
        required=False, allow_null=True
    )
    instructor_comments = serializers.CharField(required=False, allow_null=True)
    flight_time = serializers.DecimalField(
        max_digits=5, decimal_places=2, required=False, allow_null=True
    )
    ground_time = serializers.DecimalField(
        max_digits=5, decimal_places=2, required=False, allow_null=True
    )
    simulator_time = serializers.DecimalField(
        max_digits=5, decimal_places=2, required=False, allow_null=True
    )
    dual_time = serializers.DecimalField(
        max_digits=5, decimal_places=2, required=False, allow_null=True
    )
    solo_time = serializers.DecimalField(
        max_digits=5, decimal_places=2, required=False, allow_null=True
    )
    pic_time = serializers.DecimalField(
        max_digits=5, decimal_places=2, required=False, allow_null=True
    )
    cross_country_time = serializers.DecimalField(
        max_digits=5, decimal_places=2, required=False, allow_null=True
    )
    night_time = serializers.DecimalField(
        max_digits=5, decimal_places=2, required=False, allow_null=True
    )
    instrument_time = serializers.DecimalField(
        max_digits=5, decimal_places=2, required=False, allow_null=True
    )
    landings_day = serializers.IntegerField(required=False, default=0)
    landings_night = serializers.IntegerField(required=False, default=0)


class CancelLessonSerializer(serializers.Serializer):
    """Serializer for cancelling a lesson."""

    reason = serializers.CharField()


class InstructorSignoffSerializer(serializers.Serializer):
    """Serializer for instructor sign-off."""

    notes = serializers.CharField(required=False, allow_null=True)


class BulkGradeSerializer(serializers.Serializer):
    """Serializer for bulk grading exercises."""

    grades = ExerciseGradeCreateSerializer(many=True)


class CompletionStatisticsSerializer(serializers.Serializer):
    """Serializer for completion statistics."""

    total_records = serializers.IntegerField()
    completed = serializers.IntegerField()
    cancelled = serializers.IntegerField()
    no_show = serializers.IntegerField()
    results = serializers.DictField()
    average_grade = serializers.FloatField()
    hours = serializers.DictField()


class LessonHistorySerializer(serializers.Serializer):
    """Serializer for lesson completion history."""

    completions = serializers.ListField(child=serializers.DictField())


class InstructorPerformanceSerializer(serializers.Serializer):
    """Serializer for instructor performance statistics."""

    instructor_id = serializers.UUIDField()
    total_lessons_taught = serializers.IntegerField()
    completed_lessons = serializers.IntegerField()
    average_student_grade = serializers.FloatField()
    hours = serializers.DictField()
    unique_students = serializers.IntegerField()
    lessons_by_type = serializers.DictField()
