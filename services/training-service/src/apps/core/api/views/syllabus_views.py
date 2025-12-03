# services/training-service/src/apps/core/api/views/syllabus_views.py
"""
Syllabus Views

API ViewSets for syllabus lessons and exercises.
"""

import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.core.exceptions import ValidationError

from ...models import SyllabusLesson, Exercise
from ...services import SyllabusService
from ..serializers.syllabus_serializers import (
    SyllabusLessonSerializer,
    SyllabusLessonCreateSerializer,
    SyllabusLessonUpdateSerializer,
    SyllabusLessonDetailSerializer,
    SyllabusLessonListSerializer,
    ExerciseSerializer,
    ExerciseCreateSerializer,
    ExerciseListSerializer,
    LessonReorderSerializer,
    ExerciseReorderSerializer,
    PrerequisiteSerializer,
    LessonCloneSerializer,
    ProgramSyllabusSerializer,
)

logger = logging.getLogger(__name__)


class SyllabusLessonViewSet(viewsets.ModelViewSet):
    """
    ViewSet for syllabus lesson CRUD and management.

    Endpoints:
    - GET /lessons/ - List lessons
    - POST /lessons/ - Create lesson
    - GET /lessons/{id}/ - Get lesson details
    - PUT/PATCH /lessons/{id}/ - Update lesson
    - DELETE /lessons/{id}/ - Delete lesson
    - POST /lessons/reorder/ - Reorder lessons
    - POST /lessons/{id}/move-to-stage/ - Move lesson to stage
    - POST /lessons/{id}/prerequisites/add/ - Add prerequisite
    - POST /lessons/{id}/prerequisites/remove/ - Remove prerequisite
    - POST /lessons/{id}/clone/ - Clone lesson
    - GET /lessons/available/ - Get available lessons for enrollment
    """

    permission_classes = [IsAuthenticated]
    lookup_field = 'id'

    def get_queryset(self):
        """Get queryset filtered by organization."""
        organization_id = self.request.headers.get('X-Organization-ID')
        return SyllabusLesson.objects.filter(
            organization_id=organization_id
        ).select_related('program').prefetch_related('exercises')

    def get_serializer_class(self):
        """Get appropriate serializer based on action."""
        if self.action == 'create':
            return SyllabusLessonCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return SyllabusLessonUpdateSerializer
        elif self.action == 'list':
            return SyllabusLessonListSerializer
        elif self.action == 'retrieve':
            return SyllabusLessonDetailSerializer
        return SyllabusLessonSerializer

    def get_serializer_context(self):
        """Add organization_id to serializer context."""
        context = super().get_serializer_context()
        context['organization_id'] = self.request.headers.get('X-Organization-ID')
        return context

    def list(self, request):
        """List lessons with filters."""
        organization_id = request.headers.get('X-Organization-ID')

        program_id = request.query_params.get('program_id')
        stage_id = request.query_params.get('stage_id')
        lesson_type = request.query_params.get('lesson_type')
        status_filter = request.query_params.get('status')
        search = request.query_params.get('search')
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 50))

        lessons, total = SyllabusService.list_lessons(
            organization_id=organization_id,
            program_id=program_id,
            stage_id=stage_id,
            lesson_type=lesson_type,
            status=status_filter,
            search=search,
            page=page,
            page_size=page_size
        )

        serializer = self.get_serializer(lessons, many=True)

        return Response({
            'results': serializer.data,
            'total': total,
            'page': page,
            'page_size': page_size,
        })

    def create(self, request):
        """Create a new lesson."""
        organization_id = request.headers.get('X-Organization-ID')

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            lesson = SyllabusService.create_lesson(
                organization_id=organization_id,
                **serializer.validated_data
            )

            response_serializer = SyllabusLessonDetailSerializer(lesson)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)

        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    def update(self, request, id=None):
        """Update a lesson."""
        organization_id = request.headers.get('X-Organization-ID')

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            lesson = SyllabusService.update_lesson(
                lesson_id=id,
                organization_id=organization_id,
                **serializer.validated_data
            )

            response_serializer = SyllabusLessonDetailSerializer(lesson)
            return Response(response_serializer.data)

        except SyllabusLesson.DoesNotExist:
            return Response(
                {'error': 'Lesson not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    def destroy(self, request, id=None):
        """Delete a lesson."""
        organization_id = request.headers.get('X-Organization-ID')
        force = request.query_params.get('force', 'false').lower() == 'true'

        try:
            SyllabusService.delete_lesson(
                lesson_id=id,
                organization_id=organization_id,
                force=force
            )
            return Response(status=status.HTTP_204_NO_CONTENT)

        except SyllabusLesson.DoesNotExist:
            return Response(
                {'error': 'Lesson not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['post'])
    def reorder(self, request):
        """Reorder lessons."""
        organization_id = request.headers.get('X-Organization-ID')

        serializer = LessonReorderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        program_id = request.data.get('program_id')
        if not program_id:
            return Response(
                {'error': 'program_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            lessons = SyllabusService.reorder_lessons(
                organization_id=organization_id,
                program_id=program_id,
                lesson_order=serializer.validated_data['lesson_order'],
                stage_id=serializer.validated_data.get('stage_id')
            )

            response_serializer = SyllabusLessonListSerializer(lessons, many=True)
            return Response({'lessons': response_serializer.data})

        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'], url_path='move-to-stage')
    def move_to_stage(self, request, id=None):
        """Move lesson to a different stage."""
        organization_id = request.headers.get('X-Organization-ID')
        new_stage_id = request.data.get('stage_id')

        try:
            lesson = SyllabusService.move_lesson_to_stage(
                lesson_id=id,
                organization_id=organization_id,
                new_stage_id=new_stage_id
            )

            serializer = SyllabusLessonDetailSerializer(lesson)
            return Response(serializer.data)

        except SyllabusLesson.DoesNotExist:
            return Response(
                {'error': 'Lesson not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'], url_path='prerequisites/add')
    def add_prerequisite(self, request, id=None):
        """Add a prerequisite lesson."""
        organization_id = request.headers.get('X-Organization-ID')

        serializer = PrerequisiteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            lesson = SyllabusService.add_prerequisite(
                lesson_id=id,
                organization_id=organization_id,
                prerequisite_lesson_id=serializer.validated_data['prerequisite_lesson_id']
            )

            response_serializer = SyllabusLessonDetailSerializer(lesson)
            return Response(response_serializer.data)

        except SyllabusLesson.DoesNotExist:
            return Response(
                {'error': 'Lesson not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'], url_path='prerequisites/remove')
    def remove_prerequisite(self, request, id=None):
        """Remove a prerequisite lesson."""
        organization_id = request.headers.get('X-Organization-ID')

        serializer = PrerequisiteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            lesson = SyllabusService.remove_prerequisite(
                lesson_id=id,
                organization_id=organization_id,
                prerequisite_lesson_id=serializer.validated_data['prerequisite_lesson_id']
            )

            response_serializer = SyllabusLessonDetailSerializer(lesson)
            return Response(response_serializer.data)

        except SyllabusLesson.DoesNotExist:
            return Response(
                {'error': 'Lesson not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=['post'])
    def clone(self, request, id=None):
        """Clone a lesson."""
        organization_id = request.headers.get('X-Organization-ID')

        serializer = LessonCloneSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            new_lesson = SyllabusService.clone_lesson(
                lesson_id=id,
                organization_id=organization_id,
                **serializer.validated_data
            )

            response_serializer = SyllabusLessonDetailSerializer(new_lesson)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)

        except SyllabusLesson.DoesNotExist:
            return Response(
                {'error': 'Lesson not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['get'])
    def available(self, request):
        """Get available lessons for an enrollment."""
        organization_id = request.headers.get('X-Organization-ID')
        enrollment_id = request.query_params.get('enrollment_id')

        if not enrollment_id:
            return Response(
                {'error': 'enrollment_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            lessons = SyllabusService.get_available_lessons(
                enrollment_id=enrollment_id,
                organization_id=organization_id
            )

            serializer = SyllabusLessonListSerializer(lessons, many=True)
            return Response({'lessons': serializer.data})

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class ExerciseViewSet(viewsets.ModelViewSet):
    """
    ViewSet for exercise CRUD.

    Endpoints:
    - GET /exercises/ - List exercises
    - POST /exercises/ - Create exercise
    - GET /exercises/{id}/ - Get exercise details
    - PUT/PATCH /exercises/{id}/ - Update exercise
    - DELETE /exercises/{id}/ - Delete exercise
    - POST /exercises/reorder/ - Reorder exercises
    """

    permission_classes = [IsAuthenticated]
    lookup_field = 'id'

    def get_queryset(self):
        """Get queryset filtered by organization."""
        organization_id = self.request.headers.get('X-Organization-ID')
        return Exercise.objects.filter(
            organization_id=organization_id
        ).select_related('lesson')

    def get_serializer_class(self):
        """Get appropriate serializer based on action."""
        if self.action == 'create':
            return ExerciseCreateSerializer
        elif self.action == 'list':
            return ExerciseListSerializer
        return ExerciseSerializer

    def list(self, request):
        """List exercises for a lesson."""
        organization_id = request.headers.get('X-Organization-ID')
        lesson_id = request.query_params.get('lesson_id')

        if not lesson_id:
            return Response(
                {'error': 'lesson_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        exercises = SyllabusService.list_exercises(
            organization_id=organization_id,
            lesson_id=lesson_id
        )

        serializer = self.get_serializer(exercises, many=True)
        return Response({'exercises': serializer.data})

    def create(self, request):
        """Create a new exercise."""
        organization_id = request.headers.get('X-Organization-ID')
        lesson_id = request.data.get('lesson_id')

        if not lesson_id:
            return Response(
                {'error': 'lesson_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            exercise = SyllabusService.create_exercise(
                organization_id=organization_id,
                lesson_id=lesson_id,
                **serializer.validated_data
            )

            response_serializer = ExerciseSerializer(exercise)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)

        except SyllabusLesson.DoesNotExist:
            return Response(
                {'error': 'Lesson not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    def update(self, request, id=None):
        """Update an exercise."""
        organization_id = request.headers.get('X-Organization-ID')

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            exercise = SyllabusService.update_exercise(
                exercise_id=id,
                organization_id=organization_id,
                **serializer.validated_data
            )

            response_serializer = ExerciseSerializer(exercise)
            return Response(response_serializer.data)

        except Exercise.DoesNotExist:
            return Response(
                {'error': 'Exercise not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    def destroy(self, request, id=None):
        """Delete an exercise."""
        organization_id = request.headers.get('X-Organization-ID')

        try:
            SyllabusService.delete_exercise(
                exercise_id=id,
                organization_id=organization_id
            )
            return Response(status=status.HTTP_204_NO_CONTENT)

        except Exercise.DoesNotExist:
            return Response(
                {'error': 'Exercise not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['post'])
    def reorder(self, request):
        """Reorder exercises in a lesson."""
        organization_id = request.headers.get('X-Organization-ID')
        lesson_id = request.data.get('lesson_id')

        if not lesson_id:
            return Response(
                {'error': 'lesson_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = ExerciseReorderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        exercises = SyllabusService.reorder_exercises(
            organization_id=organization_id,
            lesson_id=lesson_id,
            exercise_order=serializer.validated_data['exercise_order']
        )

        response_serializer = ExerciseListSerializer(exercises, many=True)
        return Response({'exercises': response_serializer.data})
