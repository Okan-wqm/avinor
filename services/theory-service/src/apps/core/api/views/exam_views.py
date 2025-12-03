# services/theory-service/src/apps/core/api/views/exam_views.py
"""
Exam Views

ViewSets for exam-related API endpoints.
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from ...models import Exam, ExamAttempt
from ...services import ExamService
from ..serializers import (
    ExamListSerializer,
    ExamDetailSerializer,
    ExamCreateSerializer,
    ExamUpdateSerializer,
    ExamStartSerializer,
    ExamAnswerSerializer,
    ExamFlagSerializer,
    ExamAttemptSerializer,
    ExamResultSerializer,
    SetRandomRulesSerializer,
    AddFixedQuestionsSerializer,
)


class ExamViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing exams.

    Provides CRUD operations plus exam execution actions.
    """

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Get exams filtered by organization."""
        organization_id = self.request.headers.get('X-Organization-ID')

        return ExamService.get_exams(
            organization_id=organization_id,
            course_id=self.request.query_params.get('course_id'),
            exam_type=self.request.query_params.get('exam_type'),
            status=self.request.query_params.get('status'),
            is_published=self.request.query_params.get('is_published'),
        )

    def get_serializer_class(self):
        """Return appropriate serializer class."""
        if self.action == 'list':
            return ExamListSerializer
        elif self.action == 'create':
            return ExamCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return ExamUpdateSerializer
        return ExamDetailSerializer

    def create(self, request, *args, **kwargs):
        """Create a new exam."""
        organization_id = request.headers.get('X-Organization-ID')
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            exam = ExamService.create_exam(
                organization_id=organization_id,
                created_by=str(request.user.id),
                **serializer.validated_data
            )

            return Response(
                ExamDetailSerializer(exam).data,
                status=status.HTTP_201_CREATED
            )
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    def update(self, request, *args, **kwargs):
        """Update an exam."""
        organization_id = request.headers.get('X-Organization-ID')
        serializer = self.get_serializer(data=request.data, partial=kwargs.get('partial', False))
        serializer.is_valid(raise_exception=True)

        try:
            exam = ExamService.update_exam(
                exam_id=kwargs['pk'],
                organization_id=organization_id,
                **serializer.validated_data
            )

            return Response(ExamDetailSerializer(exam).data)
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        """Publish an exam."""
        organization_id = request.headers.get('X-Organization-ID')

        try:
            exam = ExamService.publish_exam(
                exam_id=pk,
                organization_id=organization_id
            )
            return Response(ExamDetailSerializer(exam).data)
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def archive(self, request, pk=None):
        """Archive an exam."""
        organization_id = request.headers.get('X-Organization-ID')

        exam = ExamService.archive_exam(
            exam_id=pk,
            organization_id=organization_id
        )

        return Response(ExamDetailSerializer(exam).data)

    @action(detail=True, methods=['post'], url_path='random-rules')
    def set_random_rules(self, request, pk=None):
        """Set random selection rules for an exam."""
        organization_id = request.headers.get('X-Organization-ID')
        serializer = SetRandomRulesSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            exam = ExamService.set_random_rules(
                exam_id=pk,
                organization_id=organization_id,
                rules=serializer.validated_data['rules']
            )
            return Response(ExamDetailSerializer(exam).data)
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'], url_path='fixed-questions')
    def add_fixed_questions(self, request, pk=None):
        """Add fixed questions to an exam."""
        organization_id = request.headers.get('X-Organization-ID')
        serializer = AddFixedQuestionsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            exam = ExamService.add_fixed_questions(
                exam_id=pk,
                organization_id=organization_id,
                question_ids=[str(q) for q in serializer.validated_data['question_ids']]
            )
            return Response(ExamDetailSerializer(exam).data)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['get'])
    def availability(self, request, pk=None):
        """Check exam availability for current user."""
        organization_id = request.headers.get('X-Organization-ID')

        exam = ExamService.get_exam(pk, organization_id)
        availability = exam.check_availability(str(request.user.id))

        return Response(availability)

    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """Start an exam attempt."""
        organization_id = request.headers.get('X-Organization-ID')
        serializer = ExamStartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            result = ExamService.start_exam(
                exam_id=pk,
                user_id=str(request.user.id),
                organization_id=organization_id,
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                enrollment_id=serializer.validated_data.get('enrollment_id')
            )
            return Response(result)
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['get'])
    def statistics(self, request, pk=None):
        """Get exam statistics."""
        organization_id = request.headers.get('X-Organization-ID')

        stats = ExamService.get_exam_statistics(
            exam_id=pk,
            organization_id=organization_id
        )

        return Response(stats)


class ExamAttemptViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for exam attempts.

    Handles answer submission and exam completion.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = ExamAttemptSerializer

    def get_queryset(self):
        """Get user's exam attempts."""
        organization_id = self.request.headers.get('X-Organization-ID')

        return ExamService.get_user_attempts(
            user_id=str(self.request.user.id),
            organization_id=organization_id,
            exam_id=self.request.query_params.get('exam_id'),
            status=self.request.query_params.get('status'),
        )

    @action(detail=True, methods=['post'])
    def answer(self, request, pk=None):
        """Submit an answer for a question."""
        serializer = ExamAnswerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            result = ExamService.save_answer(
                attempt_id=pk,
                user_id=str(request.user.id),
                **serializer.validated_data
            )
            return Response(result)
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def flag(self, request, pk=None):
        """Flag a question for review."""
        serializer = ExamFlagSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            result = ExamService.flag_question(
                attempt_id=pk,
                user_id=str(request.user.id),
                **serializer.validated_data
            )
            return Response(result)
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def pause(self, request, pk=None):
        """Pause the exam attempt."""
        try:
            result = ExamService.pause_exam(
                attempt_id=pk,
                user_id=str(request.user.id)
            )
            return Response(result)
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def resume(self, request, pk=None):
        """Resume the exam attempt."""
        try:
            result = ExamService.resume_exam(
                attempt_id=pk,
                user_id=str(request.user.id)
            )
            return Response(result)
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        """Submit the exam for grading."""
        try:
            result = ExamService.submit_exam(
                attempt_id=pk,
                user_id=str(request.user.id)
            )
            return Response(result)
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['get'])
    def results(self, request, pk=None):
        """Get exam results."""
        include_answers = request.query_params.get('include_answers', 'false').lower() == 'true'

        try:
            result = ExamService.get_attempt_results(
                attempt_id=pk,
                user_id=str(request.user.id),
                include_answers=include_answers
            )
            return Response(result)
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get user's exam statistics."""
        organization_id = request.headers.get('X-Organization-ID')

        stats = ExamService.get_user_statistics(
            user_id=str(request.user.id),
            organization_id=organization_id
        )

        return Response(stats)
