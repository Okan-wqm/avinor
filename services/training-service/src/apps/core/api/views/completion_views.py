# services/training-service/src/apps/core/api/views/completion_views.py
"""
Completion Views

API ViewSets for lesson completion and exercise grading.
"""

import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.core.exceptions import ValidationError

from ...models import LessonCompletion, ExerciseGrade
from ...services import CompletionService
from ..serializers.completion_serializers import (
    LessonCompletionSerializer,
    LessonCompletionCreateSerializer,
    LessonCompletionUpdateSerializer,
    LessonCompletionDetailSerializer,
    LessonCompletionListSerializer,
    ExerciseGradeSerializer,
    ExerciseGradeCreateSerializer,
    ExerciseGradeListSerializer,
    StartLessonSerializer,
    CompleteLessonSerializer,
    CancelLessonSerializer,
    InstructorSignoffSerializer,
    BulkGradeSerializer,
    CompletionStatisticsSerializer,
)

logger = logging.getLogger(__name__)


class LessonCompletionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for lesson completion CRUD and workflow.

    Endpoints:
    - GET /completions/ - List completions
    - POST /completions/ - Create completion
    - GET /completions/{id}/ - Get completion details
    - PUT/PATCH /completions/{id}/ - Update completion
    - POST /completions/{id}/start/ - Start lesson
    - POST /completions/{id}/complete/ - Complete lesson
    - POST /completions/{id}/cancel/ - Cancel lesson
    - POST /completions/{id}/no-show/ - Mark as no-show
    - POST /completions/{id}/instructor-signoff/ - Instructor sign-off
    - POST /completions/{id}/student-signoff/ - Student sign-off
    - POST /completions/{id}/grade-exercise/ - Grade an exercise
    - POST /completions/{id}/bulk-grade/ - Bulk grade exercises
    - GET /completions/{id}/grades/ - Get exercise grades
    - GET /completions/statistics/ - Get completion statistics
    - GET /completions/lesson-history/ - Get lesson history
    - GET /completions/instructor-performance/ - Get instructor performance
    """

    permission_classes = [IsAuthenticated]
    lookup_field = 'id'

    def get_queryset(self):
        """Get queryset filtered by organization."""
        organization_id = self.request.headers.get('X-Organization-ID')
        return LessonCompletion.objects.filter(
            organization_id=organization_id
        ).select_related('enrollment', 'lesson')

    def get_serializer_class(self):
        """Get appropriate serializer based on action."""
        if self.action == 'create':
            return LessonCompletionCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return LessonCompletionUpdateSerializer
        elif self.action == 'list':
            return LessonCompletionListSerializer
        elif self.action == 'retrieve':
            return LessonCompletionDetailSerializer
        return LessonCompletionSerializer

    def list(self, request):
        """List completions with filters."""
        organization_id = request.headers.get('X-Organization-ID')

        enrollment_id = request.query_params.get('enrollment_id')
        lesson_id = request.query_params.get('lesson_id')
        instructor_id = request.query_params.get('instructor_id')
        status_filter = request.query_params.get('status')
        is_completed = request.query_params.get('is_completed')
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))

        if is_completed is not None:
            is_completed = is_completed.lower() == 'true'

        completions, total = CompletionService.list_completions(
            organization_id=organization_id,
            enrollment_id=enrollment_id,
            lesson_id=lesson_id,
            instructor_id=instructor_id,
            status=status_filter,
            is_completed=is_completed,
            date_from=date_from,
            date_to=date_to,
            page=page,
            page_size=page_size
        )

        serializer = self.get_serializer(completions, many=True)

        return Response({
            'results': serializer.data,
            'total': total,
            'page': page,
            'page_size': page_size,
        })

    def create(self, request):
        """Create a new lesson completion."""
        organization_id = request.headers.get('X-Organization-ID')

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            completion = CompletionService.create_completion(
                organization_id=organization_id,
                **serializer.validated_data
            )

            response_serializer = LessonCompletionDetailSerializer(completion)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)

        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    def update(self, request, id=None):
        """Update a lesson completion."""
        organization_id = request.headers.get('X-Organization-ID')

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            completion = CompletionService.update_completion(
                completion_id=id,
                organization_id=organization_id,
                **serializer.validated_data
            )

            response_serializer = LessonCompletionDetailSerializer(completion)
            return Response(response_serializer.data)

        except LessonCompletion.DoesNotExist:
            return Response(
                {'error': 'Completion not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def start(self, request, id=None):
        """Start a lesson."""
        organization_id = request.headers.get('X-Organization-ID')

        serializer = StartLessonSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            completion = CompletionService.start_lesson(
                completion_id=id,
                organization_id=organization_id,
                instructor_id=serializer.validated_data.get('instructor_id')
            )

            response_serializer = LessonCompletionDetailSerializer(completion)
            return Response(response_serializer.data)

        except LessonCompletion.DoesNotExist:
            return Response(
                {'error': 'Completion not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def complete(self, request, id=None):
        """Complete a lesson."""
        organization_id = request.headers.get('X-Organization-ID')

        serializer = CompleteLessonSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            completion = CompletionService.complete_lesson(
                completion_id=id,
                organization_id=organization_id,
                **serializer.validated_data
            )

            response_serializer = LessonCompletionDetailSerializer(completion)
            return Response(response_serializer.data)

        except LessonCompletion.DoesNotExist:
            return Response(
                {'error': 'Completion not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def cancel(self, request, id=None):
        """Cancel a lesson."""
        organization_id = request.headers.get('X-Organization-ID')
        user_id = request.user.id

        serializer = CancelLessonSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            completion = CompletionService.cancel_lesson(
                completion_id=id,
                organization_id=organization_id,
                reason=serializer.validated_data['reason'],
                cancelled_by=user_id
            )

            response_serializer = LessonCompletionDetailSerializer(completion)
            return Response(response_serializer.data)

        except LessonCompletion.DoesNotExist:
            return Response(
                {'error': 'Completion not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'], url_path='no-show')
    def no_show(self, request, id=None):
        """Mark as no-show."""
        organization_id = request.headers.get('X-Organization-ID')

        try:
            completion = CompletionService.mark_no_show(
                completion_id=id,
                organization_id=organization_id
            )

            response_serializer = LessonCompletionDetailSerializer(completion)
            return Response(response_serializer.data)

        except LessonCompletion.DoesNotExist:
            return Response(
                {'error': 'Completion not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'], url_path='instructor-signoff')
    def instructor_signoff(self, request, id=None):
        """Instructor sign-off."""
        organization_id = request.headers.get('X-Organization-ID')
        instructor_id = request.user.id

        serializer = InstructorSignoffSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            completion = CompletionService.instructor_signoff(
                completion_id=id,
                organization_id=organization_id,
                instructor_id=instructor_id,
                notes=serializer.validated_data.get('notes')
            )

            response_serializer = LessonCompletionDetailSerializer(completion)
            return Response(response_serializer.data)

        except LessonCompletion.DoesNotExist:
            return Response(
                {'error': 'Completion not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'], url_path='student-signoff')
    def student_signoff(self, request, id=None):
        """Student sign-off."""
        organization_id = request.headers.get('X-Organization-ID')
        student_id = request.user.id

        try:
            completion = CompletionService.student_signoff(
                completion_id=id,
                organization_id=organization_id,
                student_id=student_id
            )

            response_serializer = LessonCompletionDetailSerializer(completion)
            return Response(response_serializer.data)

        except LessonCompletion.DoesNotExist:
            return Response(
                {'error': 'Completion not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'], url_path='grade-exercise')
    def grade_exercise(self, request, id=None):
        """Grade an exercise."""
        organization_id = request.headers.get('X-Organization-ID')

        serializer = ExerciseGradeCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            grade = CompletionService.grade_exercise(
                completion_id=id,
                organization_id=organization_id,
                **serializer.validated_data
            )

            response_serializer = ExerciseGradeSerializer(grade)
            return Response(response_serializer.data)

        except LessonCompletion.DoesNotExist:
            return Response(
                {'error': 'Completion not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'], url_path='bulk-grade')
    def bulk_grade(self, request, id=None):
        """Bulk grade exercises."""
        organization_id = request.headers.get('X-Organization-ID')

        serializer = BulkGradeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            grades = CompletionService.bulk_grade_exercises(
                completion_id=id,
                organization_id=organization_id,
                grades=serializer.validated_data['grades']
            )

            response_serializer = ExerciseGradeSerializer(grades, many=True)
            return Response({'grades': response_serializer.data})

        except LessonCompletion.DoesNotExist:
            return Response(
                {'error': 'Completion not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['get'])
    def grades(self, request, id=None):
        """Get exercise grades for a completion."""
        organization_id = request.headers.get('X-Organization-ID')

        try:
            grades = CompletionService.get_exercise_grades(
                completion_id=id,
                organization_id=organization_id
            )

            serializer = ExerciseGradeSerializer(grades, many=True)
            return Response({'grades': serializer.data})

        except LessonCompletion.DoesNotExist:
            return Response(
                {'error': 'Completion not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get completion statistics."""
        organization_id = request.headers.get('X-Organization-ID')

        enrollment_id = request.query_params.get('enrollment_id')
        lesson_id = request.query_params.get('lesson_id')
        instructor_id = request.query_params.get('instructor_id')
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')

        stats = CompletionService.get_completion_statistics(
            organization_id=organization_id,
            enrollment_id=enrollment_id,
            lesson_id=lesson_id,
            instructor_id=instructor_id,
            date_from=date_from,
            date_to=date_to
        )

        return Response(stats)

    @action(detail=False, methods=['get'], url_path='lesson-history')
    def lesson_history(self, request):
        """Get completion history for a lesson."""
        organization_id = request.headers.get('X-Organization-ID')

        enrollment_id = request.query_params.get('enrollment_id')
        lesson_id = request.query_params.get('lesson_id')

        if not enrollment_id or not lesson_id:
            return Response(
                {'error': 'enrollment_id and lesson_id are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        history = CompletionService.get_lesson_history(
            organization_id=organization_id,
            enrollment_id=enrollment_id,
            lesson_id=lesson_id
        )

        return Response({'history': history})

    @action(detail=False, methods=['get'], url_path='instructor-performance')
    def instructor_performance(self, request):
        """Get instructor performance statistics."""
        organization_id = request.headers.get('X-Organization-ID')

        instructor_id = request.query_params.get('instructor_id')
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')

        if not instructor_id:
            return Response(
                {'error': 'instructor_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        performance = CompletionService.get_instructor_performance(
            organization_id=organization_id,
            instructor_id=instructor_id,
            date_from=date_from,
            date_to=date_to
        )

        return Response(performance)


class ExerciseGradeViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for exercise grades (read-only).

    Grading is done through LessonCompletionViewSet.
    """

    permission_classes = [IsAuthenticated]
    lookup_field = 'id'

    def get_queryset(self):
        """Get queryset filtered by organization."""
        organization_id = self.request.headers.get('X-Organization-ID')
        return ExerciseGrade.objects.filter(
            organization_id=organization_id
        ).select_related('completion', 'exercise')

    def get_serializer_class(self):
        """Get appropriate serializer based on action."""
        if self.action == 'list':
            return ExerciseGradeListSerializer
        return ExerciseGradeSerializer

    def list(self, request):
        """List grades for a completion."""
        completion_id = request.query_params.get('completion_id')

        if not completion_id:
            return Response(
                {'error': 'completion_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        queryset = self.get_queryset().filter(completion_id=completion_id)
        serializer = self.get_serializer(queryset, many=True)

        return Response({'grades': serializer.data})
