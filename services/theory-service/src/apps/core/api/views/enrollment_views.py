# services/theory-service/src/apps/core/api/views/enrollment_views.py
"""
Enrollment Views

ViewSets for enrollment-related API endpoints.
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from ...models import CourseEnrollment, ModuleProgress
from ...services import EnrollmentService
from ..serializers import (
    EnrollmentListSerializer,
    EnrollmentDetailSerializer,
    EnrollmentCreateSerializer,
    ModuleProgressSerializer,
    ModuleActivitySerializer,
    QuizResultSerializer,
    ReviewSerializer,
    SuspendEnrollmentSerializer,
    ReactivateEnrollmentSerializer,
)


class EnrollmentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing course enrollments.

    Provides enrollment CRUD and progress tracking.
    """

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Get enrollments filtered by organization and user."""
        organization_id = self.request.headers.get('X-Organization-ID')
        user_id = self.request.query_params.get('user_id')

        # Regular users can only see their own enrollments
        if not user_id:
            user_id = str(self.request.user.id)

        return EnrollmentService.get_enrollments(
            organization_id=organization_id,
            user_id=user_id,
            course_id=self.request.query_params.get('course_id'),
            status=self.request.query_params.get('status'),
        )

    def get_serializer_class(self):
        """Return appropriate serializer class."""
        if self.action == 'list':
            return EnrollmentListSerializer
        elif self.action == 'create':
            return EnrollmentCreateSerializer
        return EnrollmentDetailSerializer

    def create(self, request, *args, **kwargs):
        """Enroll in a course."""
        organization_id = request.headers.get('X-Organization-ID')
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            enrollment = EnrollmentService.enroll_user(
                organization_id=organization_id,
                user_id=str(request.user.id),
                course_id=str(serializer.validated_data['course_id']),
                expires_in_days=serializer.validated_data.get('expires_in_days')
            )

            return Response(
                EnrollmentDetailSerializer(enrollment).data,
                status=status.HTTP_201_CREATED
            )
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """Start the course."""
        try:
            enrollment = EnrollmentService.start_course(
                enrollment_id=pk,
                user_id=str(request.user.id)
            )
            return Response(EnrollmentDetailSerializer(enrollment).data)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['get'])
    def progress(self, request, pk=None):
        """Get detailed progress for an enrollment."""
        try:
            progress = EnrollmentService.get_enrollment_progress(
                enrollment_id=pk,
                user_id=str(request.user.id)
            )
            return Response(progress)
        except CourseEnrollment.DoesNotExist:
            return Response(
                {'error': 'Enrollment not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=['post'])
    def suspend(self, request, pk=None):
        """Suspend an enrollment (admin)."""
        organization_id = request.headers.get('X-Organization-ID')
        serializer = SuspendEnrollmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            enrollment = EnrollmentService.suspend_enrollment(
                enrollment_id=pk,
                organization_id=organization_id,
                reason=serializer.validated_data.get('reason', '')
            )
            return Response(EnrollmentDetailSerializer(enrollment).data)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def reactivate(self, request, pk=None):
        """Reactivate a suspended enrollment (admin)."""
        organization_id = request.headers.get('X-Organization-ID')
        serializer = ReactivateEnrollmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            enrollment = EnrollmentService.reactivate_enrollment(
                enrollment_id=pk,
                organization_id=organization_id,
                extend_days=serializer.validated_data.get('extend_days')
            )
            return Response(EnrollmentDetailSerializer(enrollment).data)
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def review(self, request, pk=None):
        """Submit a course review."""
        serializer = ReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            enrollment = EnrollmentService.submit_review(
                enrollment_id=pk,
                user_id=str(request.user.id),
                **serializer.validated_data
            )
            return Response(EnrollmentDetailSerializer(enrollment).data)
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['get'], url_path='my-courses')
    def my_courses(self, request):
        """Get current user's enrolled courses grouped by status."""
        organization_id = request.headers.get('X-Organization-ID')
        user_id = str(request.user.id)

        enrollments = EnrollmentService.get_enrollments(
            organization_id=organization_id,
            user_id=user_id
        )

        in_progress = [e for e in enrollments if e.status in ['enrolled', 'in_progress']]
        completed = [e for e in enrollments if e.status == 'completed']
        expired = [e for e in enrollments if e.status == 'expired']

        return Response({
            'in_progress': EnrollmentListSerializer(in_progress, many=True).data,
            'completed': EnrollmentListSerializer(completed, many=True).data,
            'expired': EnrollmentListSerializer(expired, many=True).data
        })


class ModuleProgressViewSet(viewsets.ModelViewSet):
    """
    ViewSet for module progress tracking.

    Nested under enrollments.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = ModuleProgressSerializer

    def get_queryset(self):
        """Get module progress for an enrollment."""
        enrollment_id = self.kwargs.get('enrollment_pk')

        return ModuleProgress.objects.filter(
            enrollment_id=enrollment_id,
            enrollment__user_id=self.request.user.id
        ).select_related('module').order_by('module__sort_order')

    @action(detail=True, methods=['post'])
    def activity(self, request, enrollment_pk=None, pk=None):
        """Record module activity."""
        serializer = ModuleActivitySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            progress = EnrollmentService.record_module_activity(
                enrollment_id=enrollment_pk,
                module_id=pk,
                user_id=str(request.user.id),
                **serializer.validated_data
            )
            return Response(ModuleProgressSerializer(progress).data)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def complete(self, request, enrollment_pk=None, pk=None):
        """Mark module as completed."""
        try:
            progress = EnrollmentService.complete_module(
                enrollment_id=enrollment_pk,
                module_id=pk,
                user_id=str(request.user.id)
            )
            return Response(ModuleProgressSerializer(progress).data)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'], url_path='quiz-result')
    def quiz_result(self, request, enrollment_pk=None, pk=None):
        """Record quiz result for module."""
        serializer = QuizResultSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            progress = EnrollmentService.record_quiz_result(
                enrollment_id=enrollment_pk,
                module_id=pk,
                user_id=str(request.user.id),
                **serializer.validated_data
            )
            return Response(ModuleProgressSerializer(progress).data)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def bookmark(self, request, enrollment_pk=None, pk=None):
        """Bookmark/unbookmark a module."""
        bookmarked = request.data.get('bookmarked', True)

        progress = ModuleProgress.objects.get(
            enrollment_id=enrollment_pk,
            module_id=pk,
            enrollment__user_id=request.user.id
        )

        progress.bookmarked = bookmarked
        progress.save()

        return Response(ModuleProgressSerializer(progress).data)

    @action(detail=True, methods=['post'])
    def notes(self, request, enrollment_pk=None, pk=None):
        """Save notes for a module."""
        notes = request.data.get('notes', '')

        progress = ModuleProgress.objects.get(
            enrollment_id=enrollment_pk,
            module_id=pk,
            enrollment__user_id=request.user.id
        )

        progress.notes = notes
        progress.save()

        return Response(ModuleProgressSerializer(progress).data)
