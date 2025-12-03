# services/training-service/src/apps/core/api/views/progress_views.py
"""
Progress Views

API ViewSet for student progress tracking and reporting.
"""

import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from ...models import StudentEnrollment
from ...services import ProgressService

logger = logging.getLogger(__name__)


class ProgressViewSet(viewsets.ViewSet):
    """
    ViewSet for student progress tracking and reporting.

    Endpoints:
    - GET /progress/{enrollment_id}/ - Get student progress summary
    - GET /progress/{enrollment_id}/lessons/ - Get lesson progress
    - GET /progress/{enrollment_id}/next-lessons/ - Get next available lessons
    - GET /progress/{enrollment_id}/hours/ - Get hour breakdown
    - GET /progress/{enrollment_id}/performance/ - Get performance analytics
    - GET /progress/{enrollment_id}/comparison/ - Compare to program average
    - GET /progress/{enrollment_id}/report/ - Generate full progress report
    """

    permission_classes = [IsAuthenticated]

    def retrieve(self, request, pk=None):
        """Get student progress summary."""
        organization_id = request.headers.get('X-Organization-ID')

        try:
            progress = ProgressService.get_student_progress(
                enrollment_id=pk,
                organization_id=organization_id
            )

            return Response(progress)

        except StudentEnrollment.DoesNotExist:
            return Response(
                {'error': 'Enrollment not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=['get'])
    def lessons(self, request, pk=None):
        """Get detailed lesson progress."""
        organization_id = request.headers.get('X-Organization-ID')

        try:
            lesson_progress = ProgressService.get_lesson_progress(
                enrollment_id=pk,
                organization_id=organization_id
            )

            return Response({'lessons': lesson_progress})

        except StudentEnrollment.DoesNotExist:
            return Response(
                {'error': 'Enrollment not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=['get'], url_path='next-lessons')
    def next_lessons(self, request, pk=None):
        """Get next available lessons."""
        organization_id = request.headers.get('X-Organization-ID')
        limit = int(request.query_params.get('limit', 5))

        try:
            next_lessons = ProgressService.get_next_lessons(
                enrollment_id=pk,
                organization_id=organization_id,
                limit=limit
            )

            return Response({'next_lessons': next_lessons})

        except StudentEnrollment.DoesNotExist:
            return Response(
                {'error': 'Enrollment not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=['get'])
    def hours(self, request, pk=None):
        """Get hour breakdown."""
        organization_id = request.headers.get('X-Organization-ID')

        try:
            hour_breakdown = ProgressService.get_hour_breakdown(
                enrollment_id=pk,
                organization_id=organization_id
            )

            return Response(hour_breakdown)

        except StudentEnrollment.DoesNotExist:
            return Response(
                {'error': 'Enrollment not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=['get'])
    def performance(self, request, pk=None):
        """Get performance analytics."""
        organization_id = request.headers.get('X-Organization-ID')

        try:
            performance = ProgressService.get_performance_analytics(
                enrollment_id=pk,
                organization_id=organization_id
            )

            return Response(performance)

        except StudentEnrollment.DoesNotExist:
            return Response(
                {'error': 'Enrollment not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=['get'])
    def comparison(self, request, pk=None):
        """Compare to program average."""
        organization_id = request.headers.get('X-Organization-ID')

        try:
            comparison = ProgressService.compare_to_program_average(
                enrollment_id=pk,
                organization_id=organization_id
            )

            return Response(comparison)

        except StudentEnrollment.DoesNotExist:
            return Response(
                {'error': 'Enrollment not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=['get'])
    def report(self, request, pk=None):
        """Generate full progress report."""
        organization_id = request.headers.get('X-Organization-ID')

        try:
            report = ProgressService.generate_progress_report(
                enrollment_id=pk,
                organization_id=organization_id
            )

            return Response(report)

        except StudentEnrollment.DoesNotExist:
            return Response(
                {'error': 'Enrollment not found'},
                status=status.HTTP_404_NOT_FOUND
            )
