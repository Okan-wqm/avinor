# services/training-service/src/apps/core/api/views/enrollment_views.py
"""
Enrollment Views

API ViewSet for student enrollment endpoints.
"""

import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.core.exceptions import ValidationError

from ...models import StudentEnrollment
from ...services import EnrollmentService
from ..serializers.enrollment_serializers import (
    StudentEnrollmentSerializer,
    StudentEnrollmentCreateSerializer,
    StudentEnrollmentUpdateSerializer,
    StudentEnrollmentDetailSerializer,
    StudentEnrollmentListSerializer,
    EnrollmentActivateSerializer,
    EnrollmentHoldSerializer,
    EnrollmentWithdrawSerializer,
    EnrollmentCompleteSerializer,
    InstructorAssignmentSerializer,
    AddHoursSerializer,
    PaymentRecordSerializer,
    ChargeRecordSerializer,
    StudentEnrollmentsSummarySerializer,
)

logger = logging.getLogger(__name__)


class StudentEnrollmentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for student enrollment CRUD and management.

    Endpoints:
    - GET /enrollments/ - List enrollments
    - POST /enrollments/ - Create enrollment
    - GET /enrollments/{id}/ - Get enrollment details
    - PUT/PATCH /enrollments/{id}/ - Update enrollment
    - POST /enrollments/{id}/activate/ - Activate enrollment
    - POST /enrollments/{id}/hold/ - Put on hold
    - POST /enrollments/{id}/resume/ - Resume from hold
    - POST /enrollments/{id}/withdraw/ - Withdraw
    - POST /enrollments/{id}/complete/ - Mark as completed
    - POST /enrollments/{id}/assign-instructor/ - Assign primary instructor
    - POST /enrollments/{id}/add-secondary-instructor/ - Add secondary instructor
    - POST /enrollments/{id}/remove-secondary-instructor/ - Remove secondary instructor
    - POST /enrollments/{id}/add-hours/ - Add hours manually
    - POST /enrollments/{id}/refresh-progress/ - Refresh progress
    - POST /enrollments/{id}/advance-stage/ - Advance to next stage
    - POST /enrollments/{id}/record-payment/ - Record payment
    - POST /enrollments/{id}/add-charge/ - Add charge
    - GET /enrollments/student-summary/ - Get student summary
    - POST /enrollments/check-expired/ - Check and mark expired enrollments
    """

    permission_classes = [IsAuthenticated]
    lookup_field = 'id'

    def get_queryset(self):
        """Get queryset filtered by organization."""
        organization_id = self.request.headers.get('X-Organization-ID')
        return StudentEnrollment.objects.filter(
            organization_id=organization_id
        ).select_related('program')

    def get_serializer_class(self):
        """Get appropriate serializer based on action."""
        if self.action == 'create':
            return StudentEnrollmentCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return StudentEnrollmentUpdateSerializer
        elif self.action == 'list':
            return StudentEnrollmentListSerializer
        elif self.action == 'retrieve':
            return StudentEnrollmentDetailSerializer
        return StudentEnrollmentSerializer

    def list(self, request):
        """List enrollments with filters."""
        organization_id = request.headers.get('X-Organization-ID')

        student_id = request.query_params.get('student_id')
        program_id = request.query_params.get('program_id')
        instructor_id = request.query_params.get('instructor_id')
        status_filter = request.query_params.get('status')
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))

        enrollments, total = EnrollmentService.list_enrollments(
            organization_id=organization_id,
            student_id=student_id,
            program_id=program_id,
            instructor_id=instructor_id,
            status=status_filter,
            page=page,
            page_size=page_size
        )

        serializer = self.get_serializer(enrollments, many=True)

        return Response({
            'results': serializer.data,
            'total': total,
            'page': page,
            'page_size': page_size,
        })

    def create(self, request):
        """Create a new enrollment."""
        organization_id = request.headers.get('X-Organization-ID')

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            enrollment = EnrollmentService.create_enrollment(
                organization_id=organization_id,
                **serializer.validated_data
            )

            response_serializer = StudentEnrollmentDetailSerializer(enrollment)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)

        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    def update(self, request, id=None):
        """Update an enrollment."""
        organization_id = request.headers.get('X-Organization-ID')

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            enrollment = EnrollmentService.update_enrollment(
                enrollment_id=id,
                organization_id=organization_id,
                **serializer.validated_data
            )

            response_serializer = StudentEnrollmentDetailSerializer(enrollment)
            return Response(response_serializer.data)

        except StudentEnrollment.DoesNotExist:
            return Response(
                {'error': 'Enrollment not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=['post'])
    def activate(self, request, id=None):
        """Activate an enrollment."""
        organization_id = request.headers.get('X-Organization-ID')

        serializer = EnrollmentActivateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            enrollment = EnrollmentService.activate_enrollment(
                enrollment_id=id,
                organization_id=organization_id,
                start_date=serializer.validated_data.get('start_date')
            )

            response_serializer = StudentEnrollmentDetailSerializer(enrollment)
            return Response(response_serializer.data)

        except StudentEnrollment.DoesNotExist:
            return Response(
                {'error': 'Enrollment not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def hold(self, request, id=None):
        """Put enrollment on hold."""
        organization_id = request.headers.get('X-Organization-ID')

        serializer = EnrollmentHoldSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            enrollment = EnrollmentService.put_on_hold(
                enrollment_id=id,
                organization_id=organization_id,
                reason=serializer.validated_data['reason']
            )

            response_serializer = StudentEnrollmentDetailSerializer(enrollment)
            return Response(response_serializer.data)

        except StudentEnrollment.DoesNotExist:
            return Response(
                {'error': 'Enrollment not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def resume(self, request, id=None):
        """Resume enrollment from hold."""
        organization_id = request.headers.get('X-Organization-ID')

        try:
            enrollment = EnrollmentService.resume_enrollment(
                enrollment_id=id,
                organization_id=organization_id
            )

            response_serializer = StudentEnrollmentDetailSerializer(enrollment)
            return Response(response_serializer.data)

        except StudentEnrollment.DoesNotExist:
            return Response(
                {'error': 'Enrollment not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def withdraw(self, request, id=None):
        """Withdraw from enrollment."""
        organization_id = request.headers.get('X-Organization-ID')

        serializer = EnrollmentWithdrawSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            enrollment = EnrollmentService.withdraw_enrollment(
                enrollment_id=id,
                organization_id=organization_id,
                reason=serializer.validated_data['reason']
            )

            response_serializer = StudentEnrollmentDetailSerializer(enrollment)
            return Response(response_serializer.data)

        except StudentEnrollment.DoesNotExist:
            return Response(
                {'error': 'Enrollment not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def complete(self, request, id=None):
        """Mark enrollment as completed."""
        organization_id = request.headers.get('X-Organization-ID')

        serializer = EnrollmentCompleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            enrollment = EnrollmentService.complete_enrollment(
                enrollment_id=id,
                organization_id=organization_id,
                completion_date=serializer.validated_data.get('completion_date')
            )

            response_serializer = StudentEnrollmentDetailSerializer(enrollment)
            return Response(response_serializer.data)

        except StudentEnrollment.DoesNotExist:
            return Response(
                {'error': 'Enrollment not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'], url_path='assign-instructor')
    def assign_instructor(self, request, id=None):
        """Assign primary instructor."""
        organization_id = request.headers.get('X-Organization-ID')

        serializer = InstructorAssignmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            enrollment = EnrollmentService.assign_primary_instructor(
                enrollment_id=id,
                organization_id=organization_id,
                instructor_id=serializer.validated_data['instructor_id']
            )

            response_serializer = StudentEnrollmentDetailSerializer(enrollment)
            return Response(response_serializer.data)

        except StudentEnrollment.DoesNotExist:
            return Response(
                {'error': 'Enrollment not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=['post'], url_path='add-secondary-instructor')
    def add_secondary_instructor(self, request, id=None):
        """Add secondary instructor."""
        organization_id = request.headers.get('X-Organization-ID')

        serializer = InstructorAssignmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            enrollment = EnrollmentService.add_secondary_instructor(
                enrollment_id=id,
                organization_id=organization_id,
                instructor_id=serializer.validated_data['instructor_id']
            )

            response_serializer = StudentEnrollmentDetailSerializer(enrollment)
            return Response(response_serializer.data)

        except StudentEnrollment.DoesNotExist:
            return Response(
                {'error': 'Enrollment not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=['post'], url_path='remove-secondary-instructor')
    def remove_secondary_instructor(self, request, id=None):
        """Remove secondary instructor."""
        organization_id = request.headers.get('X-Organization-ID')

        serializer = InstructorAssignmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            enrollment = EnrollmentService.remove_secondary_instructor(
                enrollment_id=id,
                organization_id=organization_id,
                instructor_id=serializer.validated_data['instructor_id']
            )

            response_serializer = StudentEnrollmentDetailSerializer(enrollment)
            return Response(response_serializer.data)

        except StudentEnrollment.DoesNotExist:
            return Response(
                {'error': 'Enrollment not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=['post'], url_path='add-hours')
    def add_hours(self, request, id=None):
        """Manually add hours."""
        organization_id = request.headers.get('X-Organization-ID')

        serializer = AddHoursSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            enrollment = EnrollmentService.add_hours(
                enrollment_id=id,
                organization_id=organization_id,
                **serializer.validated_data
            )

            response_serializer = StudentEnrollmentDetailSerializer(enrollment)
            return Response(response_serializer.data)

        except StudentEnrollment.DoesNotExist:
            return Response(
                {'error': 'Enrollment not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=['post'], url_path='refresh-progress')
    def refresh_progress(self, request, id=None):
        """Refresh progress from completions."""
        organization_id = request.headers.get('X-Organization-ID')

        try:
            enrollment = EnrollmentService.update_progress(
                enrollment_id=id,
                organization_id=organization_id
            )

            response_serializer = StudentEnrollmentDetailSerializer(enrollment)
            return Response(response_serializer.data)

        except StudentEnrollment.DoesNotExist:
            return Response(
                {'error': 'Enrollment not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=['post'], url_path='advance-stage')
    def advance_stage(self, request, id=None):
        """Advance to next stage."""
        organization_id = request.headers.get('X-Organization-ID')

        try:
            enrollment = EnrollmentService.advance_to_next_stage(
                enrollment_id=id,
                organization_id=organization_id
            )

            response_serializer = StudentEnrollmentDetailSerializer(enrollment)
            return Response(response_serializer.data)

        except StudentEnrollment.DoesNotExist:
            return Response(
                {'error': 'Enrollment not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'], url_path='record-payment')
    def record_payment(self, request, id=None):
        """Record a payment."""
        organization_id = request.headers.get('X-Organization-ID')

        serializer = PaymentRecordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            enrollment = EnrollmentService.record_payment(
                enrollment_id=id,
                organization_id=organization_id,
                **serializer.validated_data
            )

            response_serializer = StudentEnrollmentDetailSerializer(enrollment)
            return Response(response_serializer.data)

        except StudentEnrollment.DoesNotExist:
            return Response(
                {'error': 'Enrollment not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=['post'], url_path='add-charge')
    def add_charge(self, request, id=None):
        """Add a charge."""
        organization_id = request.headers.get('X-Organization-ID')

        serializer = ChargeRecordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            enrollment = EnrollmentService.add_charge(
                enrollment_id=id,
                organization_id=organization_id,
                **serializer.validated_data
            )

            response_serializer = StudentEnrollmentDetailSerializer(enrollment)
            return Response(response_serializer.data)

        except StudentEnrollment.DoesNotExist:
            return Response(
                {'error': 'Enrollment not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['get'], url_path='student-summary')
    def student_summary(self, request):
        """Get enrollments summary for a student."""
        organization_id = request.headers.get('X-Organization-ID')
        student_id = request.query_params.get('student_id')

        if not student_id:
            return Response(
                {'error': 'student_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        summary = EnrollmentService.get_student_enrollments_summary(
            organization_id=organization_id,
            student_id=student_id
        )

        return Response(summary)

    @action(detail=False, methods=['post'], url_path='check-expired')
    def check_expired(self, request):
        """Check and mark expired enrollments."""
        organization_id = request.headers.get('X-Organization-ID')

        expired = EnrollmentService.check_expired_enrollments(
            organization_id=organization_id
        )

        return Response({
            'expired_count': len(expired),
            'expired_enrollments': [e.enrollment_number for e in expired]
        })
