# services/certificate-service/src/apps/core/api/views/currency_views.py
"""
Currency ViewSets

API endpoints for currency tracking and requirements.
"""

import logging
from uuid import UUID

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from ...models import CurrencyRequirement, UserCurrencyStatus, CurrencyStatus
from ...services import CurrencyService
from ..serializers import (
    CurrencyRequirementSerializer,
    CurrencyRequirementCreateSerializer,
    CurrencyRequirementListSerializer,
    UserCurrencyStatusSerializer,
    UserCurrencyStatusListSerializer,
    CurrencyCheckSerializer,
    CurrencyCheckResponseSerializer,
    CurrencyUpdateSerializer,
    CurrencyBatchUpdateSerializer,
    CurrencySummarySerializer,
)

logger = logging.getLogger(__name__)


class CurrencyRequirementViewSet(viewsets.ModelViewSet):
    """
    ViewSet for currency requirement management.

    Provides CRUD operations for:
    - FAR 61.57 requirements
    - EASA FCL.060 requirements
    - Custom organization requirements

    Endpoints:
    - GET /currency/requirements/ - List requirements
    - POST /currency/requirements/ - Create requirement
    - GET /currency/requirements/{id}/ - Retrieve requirement
    - PUT /currency/requirements/{id}/ - Update requirement
    - DELETE /currency/requirements/{id}/ - Delete requirement
    - GET /currency/requirements/defaults/ - Get default FAA requirements
    """

    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = [
        'currency_type',
        'authority',
        'is_active',
        'aircraft_category',
        'aircraft_class',
    ]
    search_fields = [
        'name',
        'description',
        'regulatory_reference',
    ]
    ordering_fields = ['name', 'currency_type', 'created_at']
    ordering = ['name']

    def get_queryset(self):
        """Filter by organization."""
        organization_id = self.request.headers.get('X-Organization-ID')
        queryset = CurrencyRequirement.objects.filter(is_active=True)

        if organization_id:
            queryset = queryset.filter(organization_id=organization_id)

        return queryset

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'create':
            return CurrencyRequirementCreateSerializer
        elif self.action == 'list':
            return CurrencyRequirementListSerializer
        return CurrencyRequirementSerializer

    def perform_create(self, serializer):
        """Create currency requirement with organization context."""
        organization_id = self.request.headers.get('X-Organization-ID')

        service = CurrencyService()
        requirement = service.create_requirement(
            organization_id=UUID(organization_id) if organization_id else None,
            **serializer.validated_data
        )

        serializer.instance = requirement

    def perform_destroy(self, instance):
        """Soft delete currency requirement."""
        instance.is_active = False
        instance.save(update_fields=['is_active', 'updated_at'])
        logger.info(f"Currency requirement {instance.id} deactivated")

    @action(detail=False, methods=['get'])
    def defaults(self, request):
        """
        Get default FAA currency requirements.

        GET /currency/requirements/defaults/
        """
        defaults = CurrencyRequirement.get_default_requirements()
        return Response(defaults)

    @action(detail=False, methods=['post'], url_path='initialize')
    def initialize_defaults(self, request):
        """
        Initialize default currency requirements for organization.

        POST /currency/requirements/initialize/
        """
        organization_id = request.headers.get('X-Organization-ID')

        if not organization_id:
            return Response(
                {'detail': 'Organization ID required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        service = CurrencyService()
        requirements = service.initialize_default_requirements(
            organization_id=UUID(organization_id)
        )

        serializer = CurrencyRequirementListSerializer(requirements, many=True)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class UserCurrencyViewSet(viewsets.ModelViewSet):
    """
    ViewSet for user currency status management.

    Provides operations for:
    - Viewing currency status
    - Updating currency from flights
    - Checking currency compliance

    Endpoints:
    - GET /currency/status/ - List user currency statuses
    - GET /currency/status/{id}/ - Retrieve specific status
    - GET /currency/status/user/{user_id}/ - Get user's currency
    - POST /currency/status/check/ - Check currency
    - POST /currency/status/update-from-flight/ - Update from flight
    - POST /currency/status/batch-update/ - Batch update
    - GET /currency/status/user/{user_id}/summary/ - Get summary
    """

    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = [
        'user_id',
        'requirement',
        'status',
        'aircraft_icao',
    ]
    ordering_fields = ['expiry_date', 'status', 'last_calculated_at']
    ordering = ['expiry_date']

    def get_queryset(self):
        """Filter by organization."""
        organization_id = self.request.headers.get('X-Organization-ID')
        queryset = UserCurrencyStatus.objects.select_related('requirement')

        if organization_id:
            queryset = queryset.filter(organization_id=organization_id)

        return queryset

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return UserCurrencyStatusListSerializer
        elif self.action == 'check':
            return CurrencyCheckSerializer
        elif self.action == 'update_from_flight':
            return CurrencyUpdateSerializer
        elif self.action == 'batch_update':
            return CurrencyBatchUpdateSerializer
        return UserCurrencyStatusSerializer

    @action(detail=False, methods=['get'], url_path='user/(?P<user_id>[^/.]+)')
    def user_currency(self, request, user_id=None):
        """
        Get all currency statuses for a user.

        GET /currency/status/user/{user_id}/
        """
        service = CurrencyService()
        statuses = service.get_user_currency_status(user_id=UUID(user_id))

        serializer = UserCurrencyStatusListSerializer(statuses, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='user/(?P<user_id>[^/.]+)/summary')
    def user_summary(self, request, user_id=None):
        """
        Get currency summary for a user.

        GET /currency/status/user/{user_id}/summary/
        """
        service = CurrencyService()
        summary = service.get_currency_summary(user_id=UUID(user_id))

        return Response(summary)

    @action(detail=False, methods=['post'])
    def check(self, request):
        """
        Check currency status for a user.

        POST /currency/status/check/
        {
            "user_id": "uuid",
            "currency_type": "takeoff_landing" (optional),
            "aircraft_type": "C172" (optional)
        }
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = CurrencyService()
        result = service.check_currency(
            user_id=serializer.validated_data['user_id'],
            currency_type=serializer.validated_data.get('currency_type'),
            aircraft_type=serializer.validated_data.get('aircraft_type')
        )

        response_serializer = CurrencyCheckResponseSerializer(data=result)
        response_serializer.is_valid(raise_exception=True)

        return Response(response_serializer.data)

    @action(detail=False, methods=['post'], url_path='update-from-flight')
    def update_from_flight(self, request):
        """
        Update currency from a flight.

        POST /currency/status/update-from-flight/
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        organization_id = request.headers.get('X-Organization-ID')

        service = CurrencyService()
        updated_statuses = service.update_currency_from_flight(
            organization_id=UUID(organization_id) if organization_id else None,
            **serializer.validated_data
        )

        return Response(
            UserCurrencyStatusListSerializer(updated_statuses, many=True).data,
            status=status.HTTP_200_OK
        )

    @action(detail=False, methods=['post'], url_path='batch-update')
    def batch_update(self, request):
        """
        Batch update currency from multiple flights.

        POST /currency/status/batch-update/
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        organization_id = request.headers.get('X-Organization-ID')

        service = CurrencyService()
        result = service.batch_update_currency(
            organization_id=UUID(organization_id) if organization_id else None,
            user_id=serializer.validated_data['user_id'],
            flights=serializer.validated_data['flights']
        )

        return Response(result)

    @action(detail=False, methods=['post'], url_path='recalculate/(?P<user_id>[^/.]+)')
    def recalculate(self, request, user_id=None):
        """
        Recalculate all currency for a user.

        POST /currency/status/recalculate/{user_id}/
        """
        service = CurrencyService()
        result = service.recalculate_user_currency(user_id=UUID(user_id))

        return Response(result)

    @action(detail=False, methods=['get'])
    def expiring(self, request):
        """
        Get currencies expiring soon.

        GET /currency/status/expiring/?days=30
        """
        organization_id = request.headers.get('X-Organization-ID')
        days = int(request.query_params.get('days', 30))

        service = CurrencyService()
        expiring = service.get_expiring_currency(
            organization_id=UUID(organization_id) if organization_id else None,
            days_ahead=days
        )

        serializer = UserCurrencyStatusListSerializer(expiring, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def expired(self, request):
        """
        Get expired currencies.

        GET /currency/status/expired/
        """
        organization_id = request.headers.get('X-Organization-ID')

        queryset = self.get_queryset().filter(status=CurrencyStatus.EXPIRED)

        serializer = UserCurrencyStatusListSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """
        Get currency statistics for organization.

        GET /currency/status/statistics/
        """
        organization_id = request.headers.get('X-Organization-ID')

        service = CurrencyService()
        stats = service.get_currency_statistics(
            organization_id=UUID(organization_id) if organization_id else None
        )

        return Response(stats)

    @action(detail=False, methods=['get'], url_path='deficiencies/(?P<user_id>[^/.]+)')
    def user_deficiencies(self, request, user_id=None):
        """
        Get currency deficiencies for a user.

        GET /currency/status/deficiencies/{user_id}/
        """
        service = CurrencyService()
        deficiencies = service.get_currency_deficiencies(user_id=UUID(user_id))

        return Response(deficiencies)

    @action(detail=False, methods=['get'], url_path='recommendations/(?P<user_id>[^/.]+)')
    def user_recommendations(self, request, user_id=None):
        """
        Get currency maintenance recommendations for a user.

        GET /currency/status/recommendations/{user_id}/
        """
        service = CurrencyService()
        recommendations = service.get_currency_recommendations(user_id=UUID(user_id))

        return Response(recommendations)
