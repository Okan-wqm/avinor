# services/certificate-service/src/apps/core/api/views/rating_views.py
"""
Rating ViewSet

API endpoints for rating/privilege management.
"""

import logging
from uuid import UUID

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from ...models import Rating, RatingStatus
from ...services import RatingService
from ..serializers import (
    RatingSerializer,
    RatingCreateSerializer,
    RatingListSerializer,
    ProficiencyCheckSerializer,
    RatingRenewSerializer,
    TypeRatingCheckSerializer,
    TypeRatingCheckResponseSerializer,
)

logger = logging.getLogger(__name__)


class RatingViewSet(viewsets.ModelViewSet):
    """
    ViewSet for rating/privilege management.

    Provides CRUD operations and specialized actions for:
    - Type ratings (aircraft specific)
    - Instrument ratings (IFR)
    - Night ratings
    - Class ratings
    - Instructor ratings

    Endpoints:
    - GET /ratings/ - List ratings
    - POST /ratings/ - Create rating
    - GET /ratings/{id}/ - Retrieve rating
    - PUT /ratings/{id}/ - Update rating
    - DELETE /ratings/{id}/ - Delete rating
    - GET /ratings/user/{user_id}/ - Get user ratings
    - POST /ratings/{id}/proficiency-check/ - Record proficiency check
    - POST /ratings/{id}/renew/ - Renew rating
    - POST /ratings/check-type-rating/ - Check type rating
    - GET /ratings/expiring/ - Get expiring ratings
    - GET /ratings/proficiency-due/ - Get ratings with proficiency due
    """

    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = [
        'user_id',
        'certificate_id',
        'rating_type',
        'status',
        'aircraft_icao',
    ]
    search_fields = [
        'rating_code',
        'rating_name',
        'aircraft_name',
        'notes',
    ]
    ordering_fields = [
        'issue_date',
        'expiry_date',
        'next_proficiency_date',
        'rating_type',
        'created_at',
    ]
    ordering = ['-created_at']

    def get_queryset(self):
        """Filter by organization."""
        organization_id = self.request.headers.get('X-Organization-ID')
        queryset = Rating.objects.all()

        if organization_id:
            queryset = queryset.filter(organization_id=organization_id)

        return queryset

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'create':
            return RatingCreateSerializer
        elif self.action == 'list':
            return RatingListSerializer
        elif self.action == 'proficiency_check':
            return ProficiencyCheckSerializer
        elif self.action == 'renew':
            return RatingRenewSerializer
        elif self.action == 'check_type_rating':
            return TypeRatingCheckSerializer
        return RatingSerializer

    def perform_create(self, serializer):
        """Create rating with organization context."""
        organization_id = self.request.headers.get('X-Organization-ID')

        service = RatingService()
        rating = service.create_rating(
            organization_id=UUID(organization_id) if organization_id else None,
            **serializer.validated_data
        )

        serializer.instance = rating

    def perform_destroy(self, instance):
        """Soft delete rating."""
        instance.status = RatingStatus.EXPIRED
        instance.save(update_fields=['status', 'updated_at'])
        logger.info(f"Rating {instance.id} archived")

    @action(detail=False, methods=['get'], url_path='user/(?P<user_id>[^/.]+)')
    def user_ratings(self, request, user_id=None):
        """
        Get all ratings for a user.

        GET /ratings/user/{user_id}/
        """
        include_expired = request.query_params.get('include_expired', 'false').lower() == 'true'

        service = RatingService()
        ratings = service.get_user_ratings(
            user_id=UUID(user_id),
            include_expired=include_expired
        )

        serializer = RatingListSerializer(ratings, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='proficiency-check')
    def proficiency_check(self, request, pk=None):
        """
        Record a proficiency check for a rating.

        POST /ratings/{id}/proficiency-check/
        """
        rating = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = RatingService()
        updated_rating = service.record_proficiency_check(
            rating_id=rating.id,
            check_date=serializer.validated_data['check_date'],
            examiner_id=serializer.validated_data['examiner_id'],
            examiner_name=serializer.validated_data['examiner_name'],
            passed=serializer.validated_data.get('passed', True),
            notes=serializer.validated_data.get('notes', '')
        )

        return Response(
            RatingSerializer(updated_rating).data,
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['post'])
    def renew(self, request, pk=None):
        """
        Renew a rating.

        POST /ratings/{id}/renew/
        """
        rating = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = RatingService()
        renewed_rating = service.renew_rating(
            rating_id=rating.id,
            new_expiry_date=serializer.validated_data['new_expiry_date'],
            proficiency_date=serializer.validated_data.get('proficiency_date')
        )

        return Response(
            RatingSerializer(renewed_rating).data,
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['post'])
    def suspend(self, request, pk=None):
        """
        Suspend a rating.

        POST /ratings/{id}/suspend/
        """
        rating = self.get_object()
        reason = request.data.get('reason', '')

        service = RatingService()
        suspended_rating = service.suspend_rating(
            rating_id=rating.id,
            reason=reason
        )

        return Response(
            RatingSerializer(suspended_rating).data,
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['post'])
    def reinstate(self, request, pk=None):
        """
        Reinstate a suspended rating.

        POST /ratings/{id}/reinstate/
        """
        rating = self.get_object()

        service = RatingService()
        reinstated_rating = service.reinstate_rating(rating_id=rating.id)

        return Response(
            RatingSerializer(reinstated_rating).data,
            status=status.HTTP_200_OK
        )

    @action(detail=False, methods=['post'], url_path='check-type-rating')
    def check_type_rating(self, request):
        """
        Check if a user has a valid type rating for an aircraft.

        POST /ratings/check-type-rating/
        {
            "user_id": "uuid",
            "aircraft_icao": "C172"
        }
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = RatingService()
        result = service.check_type_rating(
            user_id=serializer.validated_data['user_id'],
            aircraft_icao=serializer.validated_data['aircraft_icao']
        )

        response_serializer = TypeRatingCheckResponseSerializer(data=result)
        response_serializer.is_valid(raise_exception=True)

        return Response(response_serializer.data)

    @action(detail=False, methods=['get'])
    def expiring(self, request):
        """
        Get ratings expiring soon.

        GET /ratings/expiring/?days=30
        """
        organization_id = request.headers.get('X-Organization-ID')
        days = int(request.query_params.get('days', 30))

        service = RatingService()
        expiring = service.get_expiring_ratings(
            organization_id=UUID(organization_id) if organization_id else None,
            days_ahead=days
        )

        serializer = RatingListSerializer(expiring, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='proficiency-due')
    def proficiency_due(self, request):
        """
        Get ratings with proficiency check due.

        GET /ratings/proficiency-due/?days=30
        """
        organization_id = request.headers.get('X-Organization-ID')
        days = int(request.query_params.get('days', 30))

        service = RatingService()
        due = service.get_proficiency_due(
            organization_id=UUID(organization_id) if organization_id else None,
            days_ahead=days
        )

        serializer = RatingListSerializer(due, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """
        Get rating statistics for organization.

        GET /ratings/statistics/
        """
        organization_id = request.headers.get('X-Organization-ID')

        service = RatingService()
        stats = service.get_rating_statistics(
            organization_id=UUID(organization_id) if organization_id else None
        )

        return Response(stats)

    @action(detail=False, methods=['get'], url_path='aircraft/(?P<aircraft_icao>[^/.]+)')
    def by_aircraft(self, request, aircraft_icao=None):
        """
        Get all ratings for a specific aircraft type.

        GET /ratings/aircraft/{aircraft_icao}/
        """
        organization_id = request.headers.get('X-Organization-ID')

        queryset = self.get_queryset().filter(
            aircraft_icao__iexact=aircraft_icao,
            status=RatingStatus.ACTIVE
        )

        if organization_id:
            queryset = queryset.filter(organization_id=organization_id)

        serializer = RatingListSerializer(queryset, many=True)
        return Response(serializer.data)
