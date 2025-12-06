# services/certificate-service/src/apps/core/api/views/flight_review_views.py
"""
Flight Review API Views
"""

from uuid import UUID
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from ...models import FlightReview, SkillTest
from ...services import FlightReviewService
from ..serializers import (
    FlightReviewSerializer,
    FlightReviewCreateSerializer,
    SkillTestSerializer,
    SkillTestCreateSerializer,
    FlightReviewVerifySerializer,
)


class FlightReviewViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Flight Review management.

    Endpoints:
    - GET /api/v1/flight-reviews/ - List reviews
    - POST /api/v1/flight-reviews/ - Create review
    - GET /api/v1/flight-reviews/{id}/ - Get review
    - POST /api/v1/flight-reviews/{id}/verify/ - Verify review
    - GET /api/v1/flight-reviews/bfr-validity/ - Check BFR validity
    - GET /api/v1/flight-reviews/ipc-validity/ - Check IPC validity
    - GET /api/v1/flight-reviews/expiring/ - Get expiring reviews
    - GET /api/v1/flight-reviews/comprehensive-status/ - Get full status
    """

    queryset = FlightReview.objects.all()
    serializer_class = FlightReviewSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter by organization and user."""
        queryset = super().get_queryset()
        org_id = self.request.headers.get('X-Organization-ID')
        if org_id:
            queryset = queryset.filter(organization_id=org_id)

        user_id = self.request.query_params.get('user_id')
        if user_id:
            queryset = queryset.filter(user_id=user_id)

        review_type = self.request.query_params.get('review_type')
        if review_type:
            queryset = queryset.filter(review_type=review_type)

        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        return queryset.order_by('-review_date')

    def create(self, request, *args, **kwargs):
        """Record a flight review."""
        serializer = FlightReviewCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        org_id = UUID(request.headers.get('X-Organization-ID'))
        user_id = UUID(request.data.get('user_id'))

        result = FlightReviewService.record_flight_review(
            organization_id=org_id,
            user_id=user_id,
            **serializer.validated_data
        )

        return Response(result, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def verify(self, request, pk=None):
        """Verify a flight review."""
        serializer = FlightReviewVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = FlightReviewService.verify_review(
            review_id=UUID(pk),
            verified_by=request.user.id,
            notes=serializer.validated_data.get('notes')
        )

        return Response(result)

    @action(detail=False, methods=['get'], url_path='bfr-validity')
    def bfr_validity(self, request):
        """Check BFR validity for a user."""
        org_id = UUID(request.headers.get('X-Organization-ID'))
        user_id = UUID(request.query_params.get('user_id'))

        result = FlightReviewService.check_bfr_validity(
            organization_id=org_id,
            user_id=user_id
        )

        return Response(result)

    @action(detail=False, methods=['get'], url_path='ipc-validity')
    def ipc_validity(self, request):
        """Check IPC validity for a user."""
        org_id = UUID(request.headers.get('X-Organization-ID'))
        user_id = UUID(request.query_params.get('user_id'))

        result = FlightReviewService.check_ipc_validity(
            organization_id=org_id,
            user_id=user_id
        )

        return Response(result)

    @action(detail=False, methods=['get'])
    def expiring(self, request):
        """Get expiring flight reviews."""
        org_id = request.headers.get('X-Organization-ID')
        days = int(request.query_params.get('days', 90))

        result = FlightReviewService.get_expiring_reviews(
            organization_id=UUID(org_id) if org_id else None,
            days_ahead=days
        )

        return Response(result)

    @action(detail=False, methods=['get'], url_path='comprehensive-status')
    def comprehensive_status(self, request):
        """Get comprehensive review status for a user."""
        org_id = UUID(request.headers.get('X-Organization-ID'))
        user_id = UUID(request.query_params.get('user_id'))

        result = FlightReviewService.get_comprehensive_review_status(
            organization_id=org_id,
            user_id=user_id
        )

        return Response(result)

    @action(detail=False, methods=['get'], url_path='instructor-statistics')
    def instructor_statistics(self, request):
        """Get flight review statistics for an instructor."""
        org_id = UUID(request.headers.get('X-Organization-ID'))
        instructor_id = UUID(request.query_params.get('instructor_id'))

        result = FlightReviewService.get_instructor_statistics(
            organization_id=org_id,
            instructor_id=instructor_id
        )

        return Response(result)


class SkillTestViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Skill Test (Checkride) management.

    Endpoints:
    - GET /api/v1/skill-tests/ - List skill tests
    - POST /api/v1/skill-tests/ - Record skill test
    - GET /api/v1/skill-tests/{id}/ - Get skill test
    """

    queryset = SkillTest.objects.all()
    serializer_class = SkillTestSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter by organization and user."""
        queryset = super().get_queryset()
        org_id = self.request.headers.get('X-Organization-ID')
        if org_id:
            queryset = queryset.filter(organization_id=org_id)

        user_id = self.request.query_params.get('user_id')
        if user_id:
            queryset = queryset.filter(user_id=user_id)

        test_type = self.request.query_params.get('test_type')
        if test_type:
            queryset = queryset.filter(test_type=test_type)

        return queryset.order_by('-test_date')

    def create(self, request, *args, **kwargs):
        """Record a skill test."""
        serializer = SkillTestCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        org_id = UUID(request.headers.get('X-Organization-ID'))
        user_id = UUID(request.data.get('user_id'))

        result = FlightReviewService.record_skill_test(
            organization_id=org_id,
            user_id=user_id,
            **serializer.validated_data
        )

        return Response(result, status=status.HTTP_201_CREATED)
