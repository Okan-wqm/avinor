"""Training Service Serializers."""
from rest_framework import serializers
from .models import (
    TrainingProgram, Syllabus, Stage, Lesson,
    StudentEnrollment, LessonCompletion, StageCheck
)


class LessonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lesson
        fields = '__all__'


class StageSerializer(serializers.ModelSerializer):
    lessons = LessonSerializer(many=True, read_only=True)
    lesson_count = serializers.SerializerMethodField()

    class Meta:
        model = Stage
        fields = '__all__'

    def get_lesson_count(self, obj):
        return obj.lessons.count()


class SyllabusSerializer(serializers.ModelSerializer):
    stages = StageSerializer(many=True, read_only=True)

    class Meta:
        model = Syllabus
        fields = '__all__'


class TrainingProgramSerializer(serializers.ModelSerializer):
    syllabi = SyllabusSerializer(many=True, read_only=True)

    class Meta:
        model = TrainingProgram
        fields = '__all__'


class TrainingProgramListSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrainingProgram
        fields = ['id', 'name', 'code', 'program_type', 'min_flight_hours', 'estimated_cost', 'is_active']


class StudentEnrollmentSerializer(serializers.ModelSerializer):
    program_name = serializers.CharField(source='program.name', read_only=True)
    progress_percentage = serializers.SerializerMethodField()

    class Meta:
        model = StudentEnrollment
        fields = '__all__'

    def get_progress_percentage(self, obj):
        total_lessons = Lesson.objects.filter(stage__syllabus=obj.syllabus).count()
        completed = obj.completions.filter(grade='S').count()
        return round((completed / total_lessons * 100) if total_lessons > 0 else 0, 1)


class LessonCompletionSerializer(serializers.ModelSerializer):
    lesson_name = serializers.CharField(source='lesson.name', read_only=True)

    class Meta:
        model = LessonCompletion
        fields = '__all__'


class StageCheckSerializer(serializers.ModelSerializer):
    stage_name = serializers.CharField(source='stage.name', read_only=True)

    class Meta:
        model = StageCheck
        fields = '__all__'
