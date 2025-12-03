# services/training-service/src/apps/core/api/serializers/syllabus_serializers.py
"""
Syllabus Serializers

Serializers for syllabus lesson and exercise API endpoints.
"""

from rest_framework import serializers
from decimal import Decimal

from ...models import SyllabusLesson, Exercise


class ExerciseSerializer(serializers.ModelSerializer):
    """Serializer for exercises."""

    class Meta:
        model = Exercise
        fields = [
            'id', 'organization_id', 'lesson', 'code', 'name',
            'description', 'sort_order', 'ato_reference',
            'competency_elements', 'grading_scale', 'tolerances',
            'standards', 'min_demonstrations', 'min_grade',
            'resources', 'is_required', 'is_critical',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'organization_id', 'created_at', 'updated_at']


class ExerciseCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating exercises."""

    class Meta:
        model = Exercise
        fields = [
            'code', 'name', 'description', 'ato_reference',
            'competency_elements', 'grading_scale', 'tolerances',
            'standards', 'min_demonstrations', 'min_grade',
            'resources', 'is_required', 'is_critical',
        ]


class ExerciseListSerializer(serializers.ModelSerializer):
    """Serializer for listing exercises."""

    class Meta:
        model = Exercise
        fields = [
            'id', 'code', 'name', 'sort_order', 'grading_scale',
            'is_required', 'is_critical',
        ]


class SyllabusLessonSerializer(serializers.ModelSerializer):
    """Base serializer for syllabus lessons."""

    exercises = ExerciseListSerializer(many=True, read_only=True)
    exercise_count = serializers.IntegerField(source='exercise_count', read_only=True)
    total_duration = serializers.DecimalField(
        max_digits=4, decimal_places=2, read_only=True
    )
    is_flight_lesson = serializers.BooleanField(read_only=True)
    is_ground_lesson = serializers.BooleanField(read_only=True)
    is_evaluation = serializers.BooleanField(read_only=True)
    stage_name = serializers.SerializerMethodField()

    class Meta:
        model = SyllabusLesson
        fields = [
            'id', 'organization_id', 'program', 'stage_id', 'parent_lesson',
            'code', 'name', 'description', 'objective', 'lesson_type',
            'sort_order', 'duration_hours', 'ground_hours', 'flight_hours',
            'simulator_hours', 'briefing_hours',
            'required_aircraft_type', 'required_aircraft_category',
            'required_conditions', 'required_equipment',
            'prerequisite_lessons', 'prerequisite_hours', 'prerequisite_conditions',
            'content', 'completion_standards', 'resources', 'references',
            'grading_criteria', 'min_grade_to_pass', 'max_attempts',
            'completion_criteria', 'requires_instructor_signoff',
            'requires_student_signoff',
            'ato_reference', 'regulatory_reference',
            'instructor_notes', 'common_errors',
            'status', 'metadata', 'tags',
            'exercises', 'exercise_count', 'total_duration',
            'is_flight_lesson', 'is_ground_lesson', 'is_evaluation',
            'stage_name', 'has_prerequisites',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'organization_id', 'created_at', 'updated_at']

    def get_stage_name(self, obj):
        """Get stage name."""
        return obj.get_stage_name()


class SyllabusLessonCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating syllabus lessons."""

    class Meta:
        model = SyllabusLesson
        fields = [
            'program', 'stage_id', 'parent_lesson',
            'code', 'name', 'description', 'objective', 'lesson_type',
            'duration_hours', 'ground_hours', 'flight_hours',
            'simulator_hours', 'briefing_hours',
            'required_aircraft_type', 'required_aircraft_category',
            'required_conditions', 'required_equipment',
            'prerequisite_lessons', 'prerequisite_hours', 'prerequisite_conditions',
            'content', 'completion_standards', 'resources', 'references',
            'grading_criteria', 'min_grade_to_pass', 'max_attempts',
            'completion_criteria', 'requires_instructor_signoff',
            'requires_student_signoff',
            'ato_reference', 'regulatory_reference',
            'instructor_notes', 'common_errors',
            'status', 'metadata', 'tags',
        ]

    def validate_code(self, value):
        """Validate code uniqueness within program."""
        program_id = self.initial_data.get('program')
        if SyllabusLesson.objects.filter(
            program_id=program_id,
            code=value
        ).exists():
            raise serializers.ValidationError(
                f"Lesson with code '{value}' already exists in this program"
            )
        return value


class SyllabusLessonUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating syllabus lessons."""

    class Meta:
        model = SyllabusLesson
        fields = [
            'stage_id', 'parent_lesson',
            'name', 'description', 'objective',
            'duration_hours', 'ground_hours', 'flight_hours',
            'simulator_hours', 'briefing_hours',
            'required_aircraft_type', 'required_aircraft_category',
            'required_conditions', 'required_equipment',
            'prerequisite_lessons', 'prerequisite_hours', 'prerequisite_conditions',
            'content', 'completion_standards', 'resources', 'references',
            'grading_criteria', 'min_grade_to_pass', 'max_attempts',
            'completion_criteria', 'requires_instructor_signoff',
            'requires_student_signoff',
            'ato_reference', 'regulatory_reference',
            'instructor_notes', 'common_errors',
            'status', 'metadata', 'tags',
        ]


class SyllabusLessonDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for syllabus lessons."""

    exercises = ExerciseSerializer(many=True, read_only=True)
    program_info = serializers.SerializerMethodField()
    stage_name = serializers.SerializerMethodField()
    total_duration = serializers.DecimalField(
        max_digits=4, decimal_places=2, read_only=True
    )
    is_flight_lesson = serializers.BooleanField(read_only=True)
    is_ground_lesson = serializers.BooleanField(read_only=True)
    is_evaluation = serializers.BooleanField(read_only=True)

    class Meta:
        model = SyllabusLesson
        fields = [
            'id', 'organization_id', 'program', 'program_info',
            'stage_id', 'stage_name', 'parent_lesson',
            'code', 'name', 'description', 'objective', 'lesson_type',
            'sort_order', 'duration_hours', 'ground_hours', 'flight_hours',
            'simulator_hours', 'briefing_hours',
            'required_aircraft_type', 'required_aircraft_category',
            'required_conditions', 'required_equipment',
            'prerequisite_lessons', 'prerequisite_hours', 'prerequisite_conditions',
            'content', 'completion_standards', 'resources', 'references',
            'grading_criteria', 'min_grade_to_pass', 'max_attempts',
            'completion_criteria', 'requires_instructor_signoff',
            'requires_student_signoff',
            'ato_reference', 'regulatory_reference',
            'instructor_notes', 'common_errors',
            'status', 'metadata', 'tags',
            'exercises', 'total_duration',
            'is_flight_lesson', 'is_ground_lesson', 'is_evaluation',
            'has_prerequisites',
            'created_at', 'updated_at',
        ]

    def get_program_info(self, obj):
        """Get program info."""
        return {
            'id': str(obj.program.id),
            'code': obj.program.code,
            'name': obj.program.name,
        }

    def get_stage_name(self, obj):
        """Get stage name."""
        return obj.get_stage_name()


class SyllabusLessonListSerializer(serializers.ModelSerializer):
    """Serializer for listing syllabus lessons."""

    stage_name = serializers.SerializerMethodField()
    total_duration = serializers.DecimalField(
        max_digits=4, decimal_places=2, read_only=True
    )
    exercise_count = serializers.IntegerField(source='exercise_count', read_only=True)

    class Meta:
        model = SyllabusLesson
        fields = [
            'id', 'code', 'name', 'lesson_type', 'stage_id', 'stage_name',
            'sort_order', 'total_duration', 'exercise_count', 'status',
            'min_grade_to_pass',
        ]

    def get_stage_name(self, obj):
        """Get stage name."""
        return obj.get_stage_name()


class ProgramSyllabusSerializer(serializers.Serializer):
    """Serializer for complete program syllabus structure."""

    program = serializers.DictField()
    stages = serializers.ListField(child=serializers.DictField())
    unassigned_lessons = serializers.ListField(child=serializers.DictField())
    statistics = serializers.DictField()


class LessonReorderSerializer(serializers.Serializer):
    """Serializer for reordering lessons."""

    lesson_order = serializers.ListField(
        child=serializers.UUIDField(),
        help_text="List of lesson IDs in desired order"
    )
    stage_id = serializers.UUIDField(required=False, allow_null=True)


class ExerciseReorderSerializer(serializers.Serializer):
    """Serializer for reordering exercises."""

    exercise_order = serializers.ListField(
        child=serializers.UUIDField(),
        help_text="List of exercise IDs in desired order"
    )


class PrerequisiteSerializer(serializers.Serializer):
    """Serializer for adding/removing prerequisites."""

    prerequisite_lesson_id = serializers.UUIDField()


class LessonCloneSerializer(serializers.Serializer):
    """Serializer for cloning a lesson."""

    new_code = serializers.CharField(max_length=50)
    new_name = serializers.CharField(max_length=255, required=False, allow_null=True)
    target_program_id = serializers.UUIDField(required=False, allow_null=True)
    include_exercises = serializers.BooleanField(default=True)
