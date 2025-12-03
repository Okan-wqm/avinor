"""Training Service Views."""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.utils import timezone

from .models import (
    TrainingProgram, Syllabus, Stage, Lesson,
    StudentEnrollment, LessonCompletion, StageCheck
)
from .serializers import (
    TrainingProgramSerializer, TrainingProgramListSerializer,
    SyllabusSerializer, StageSerializer, LessonSerializer,
    StudentEnrollmentSerializer, LessonCompletionSerializer, StageCheckSerializer
)


class TrainingProgramViewSet(viewsets.ModelViewSet):
    queryset = TrainingProgram.objects.filter(is_deleted=False)
    serializer_class = TrainingProgramSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['organization_id', 'program_type', 'is_active']
    search_fields = ['name', 'code', 'description']
    ordering = ['name']

    def get_serializer_class(self):
        if self.action == 'list':
            return TrainingProgramListSerializer
        return TrainingProgramSerializer


class SyllabusViewSet(viewsets.ModelViewSet):
    queryset = Syllabus.objects.all()
    serializer_class = SyllabusSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['program', 'is_active']


class StageViewSet(viewsets.ModelViewSet):
    queryset = Stage.objects.all()
    serializer_class = StageSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['syllabus']
    ordering = ['order']


class LessonViewSet(viewsets.ModelViewSet):
    queryset = Lesson.objects.all()
    serializer_class = LessonSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['stage', 'lesson_type']
    search_fields = ['name', 'code']
    ordering = ['order']


class StudentEnrollmentViewSet(viewsets.ModelViewSet):
    queryset = StudentEnrollment.objects.all()
    serializer_class = StudentEnrollmentSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['student_id', 'instructor_id', 'program', 'status']
    ordering = ['-enrolled_at']

    @action(detail=True, methods=['get'])
    def progress(self, request, pk=None):
        """Get detailed progress for enrollment."""
        enrollment = self.get_object()
        completions = enrollment.completions.all()
        total_lessons = Lesson.objects.filter(stage__syllabus=enrollment.syllabus).count()

        return Response({
            'enrollment': StudentEnrollmentSerializer(enrollment).data,
            'total_lessons': total_lessons,
            'completed_lessons': completions.filter(grade='S').count(),
            'flight_hours': float(enrollment.total_flight_hours),
            'ground_hours': float(enrollment.total_ground_hours),
            'recent_completions': LessonCompletionSerializer(completions[:10], many=True).data
        })

    @action(detail=True, methods=['post'])
    def complete_lesson(self, request, pk=None):
        """Record lesson completion."""
        enrollment = self.get_object()
        data = request.data.copy()
        data['enrollment'] = enrollment.id
        data['instructor_id'] = request.user.id
        data['completed_at'] = timezone.now()

        serializer = LessonCompletionSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        completion = serializer.save()

        # Update enrollment hours
        enrollment.total_flight_hours += completion.flight_time_minutes / 60
        enrollment.total_ground_hours += completion.ground_time_minutes / 60
        enrollment.save()

        return Response(serializer.data, status=status.HTTP_201_CREATED)


class LessonCompletionViewSet(viewsets.ModelViewSet):
    queryset = LessonCompletion.objects.all()
    serializer_class = LessonCompletionSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['enrollment', 'lesson', 'instructor_id', 'grade']
    ordering = ['-completed_at']


class StageCheckViewSet(viewsets.ModelViewSet):
    queryset = StageCheck.objects.all()
    serializer_class = StageCheckSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['enrollment', 'stage', 'examiner_id', 'result']
    ordering = ['-scheduled_at']

    @action(detail=True, methods=['post'])
    def record_result(self, request, pk=None):
        """Record stage check result."""
        check = self.get_object()
        check.completed_at = timezone.now()
        check.result = request.data.get('result')
        check.areas_satisfactory = request.data.get('areas_satisfactory', [])
        check.areas_unsatisfactory = request.data.get('areas_unsatisfactory', [])
        check.examiner_comments = request.data.get('examiner_comments', '')
        check.save()
        return Response(StageCheckSerializer(check).data)
