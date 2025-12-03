# services/aircraft-service/src/apps/api/views/aircraft_views.py
"""
Aircraft Views

ViewSets for aircraft CRUD and management operations.
"""

import logging
from datetime import datetime

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters import rest_framework as filters
from django.db.models import Q

from apps.core.models import Aircraft, AircraftType, AircraftEngine, AircraftPropeller
from apps.core.services import (
    AircraftService,
    AircraftNotFoundError,
    AircraftValidationError,
    AircraftConflictError,
)
from apps.api.serializers import (
    AircraftTypeSerializer,
    AircraftListSerializer,
    AircraftDetailSerializer,
    AircraftCreateSerializer,
    AircraftUpdateSerializer,
    AircraftStatusSerializer,
    AircraftAvailabilitySerializer,
    GroundAircraftSerializer,
    AircraftEngineSerializer,
    AircraftEngineCreateSerializer,
    AircraftEngineUpdateSerializer,
    EngineOverhaulSerializer,
    AircraftPropellerSerializer,
    AircraftPropellerCreateSerializer,
)

logger = logging.getLogger(__name__)


class AircraftTypeFilter(filters.FilterSet):
    """Filter for aircraft types."""

    manufacturer = filters.CharFilter(lookup_expr='icontains')
    model = filters.CharFilter(lookup_expr='icontains')
    category = filters.ChoiceFilter(choices=AircraftType.Category.choices)
    is_complex = filters.BooleanFilter()
    is_high_performance = filters.BooleanFilter()
    requires_type_rating = filters.BooleanFilter()

    class Meta:
        model = AircraftType
        fields = ['manufacturer', 'model', 'category', 'is_complex',
                  'is_high_performance', 'requires_type_rating']


class AircraftTypeViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for aircraft types (reference data).

    list: Get all aircraft types
    retrieve: Get aircraft type details
    """

    queryset = AircraftType.objects.filter(is_active=True)
    serializer_class = AircraftTypeSerializer
    permission_classes = [IsAuthenticated]
    filterset_class = AircraftTypeFilter
    search_fields = ['manufacturer', 'model', 'common_name', 'icao_code']
    ordering_fields = ['manufacturer', 'model', 'created_at']
    ordering = ['manufacturer', 'model']


class AircraftFilter(filters.FilterSet):
    """Filter for aircraft."""

    status = filters.ChoiceFilter(choices=Aircraft.Status.choices)
    operational_status = filters.ChoiceFilter(choices=Aircraft.OperationalStatus.choices)
    category = filters.ChoiceFilter(choices=Aircraft.Category.choices)
    home_base_id = filters.UUIDFilter()
    current_location_id = filters.UUIDFilter()
    is_airworthy = filters.BooleanFilter()
    is_complex = filters.BooleanFilter()
    is_high_performance = filters.BooleanFilter()
    is_ifr_certified = filters.BooleanFilter()
    has_open_squawks = filters.BooleanFilter()
    has_grounding_squawks = filters.BooleanFilter()
    registration = filters.CharFilter(lookup_expr='icontains')
    aircraft_type = filters.UUIDFilter()

    # Available filter
    available = filters.BooleanFilter(method='filter_available')

    class Meta:
        model = Aircraft
        fields = [
            'status', 'operational_status', 'category',
            'home_base_id', 'current_location_id',
            'is_airworthy', 'is_complex', 'is_high_performance',
            'is_ifr_certified', 'has_open_squawks', 'has_grounding_squawks',
            'registration', 'aircraft_type',
        ]

    def filter_available(self, queryset, name, value):
        if value:
            return queryset.filter(
                status=Aircraft.Status.ACTIVE,
                is_airworthy=True,
                has_grounding_squawks=False
            )
        return queryset


class AircraftViewSet(viewsets.ModelViewSet):
    """
    ViewSet for aircraft management.

    list: Get all aircraft for organization
    retrieve: Get aircraft details
    create: Create new aircraft
    update: Update aircraft
    partial_update: Partial update aircraft
    destroy: Soft delete aircraft

    Custom actions:
    - status: Get aircraft status with warnings
    - ground: Ground the aircraft
    - unground: Remove grounding
    - availability: Check availability for time period
    - engines: Manage engines
    - propellers: Manage propellers
    """

    permission_classes = [IsAuthenticated]
    filterset_class = AircraftFilter
    search_fields = ['registration', 'serial_number', 'notes']
    ordering_fields = ['registration', 'total_time_hours', 'created_at', 'updated_at']
    ordering = ['registration']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.aircraft_service = AircraftService()

    def get_queryset(self):
        """Get aircraft for the current organization."""
        organization_id = self.request.headers.get('X-Organization-ID')
        if not organization_id:
            return Aircraft.objects.none()

        return Aircraft.objects.filter(
            organization_id=organization_id,
            deleted_at__isnull=True
        ).select_related('aircraft_type')

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return AircraftListSerializer
        elif self.action == 'create':
            return AircraftCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return AircraftUpdateSerializer
        return AircraftDetailSerializer

    def perform_create(self, serializer):
        """Create aircraft with organization context."""
        organization_id = self.request.headers.get('X-Organization-ID')
        user_id = self.request.headers.get('X-User-ID')

        try:
            aircraft = self.aircraft_service.create_aircraft(
                organization_id=organization_id,
                created_by=user_id,
                **serializer.validated_data
            )
            serializer.instance = aircraft
        except AircraftConflictError as e:
            raise serializers.ValidationError({'registration': str(e)})
        except AircraftValidationError as e:
            raise serializers.ValidationError(str(e))

    def perform_destroy(self, instance):
        """Soft delete the aircraft."""
        user_id = self.request.headers.get('X-User-ID')
        try:
            self.aircraft_service.delete_aircraft(
                aircraft_id=instance.id,
                deleted_by=user_id
            )
        except AircraftNotFoundError:
            pass

    # ==========================================================================
    # Status Actions
    # ==========================================================================

    @action(detail=True, methods=['get'])
    def status(self, request, pk=None):
        """Get detailed aircraft status with warnings and blockers."""
        try:
            status_data = self.aircraft_service.get_aircraft_status(pk)
            return Response(status_data)
        except AircraftNotFoundError:
            return Response(
                {'error': 'Aircraft not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=['post'])
    def ground(self, request, pk=None):
        """Ground the aircraft."""
        serializer = GroundAircraftSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user_id = request.headers.get('X-User-ID')

        try:
            aircraft = self.aircraft_service.ground_aircraft(
                aircraft_id=pk,
                reason=serializer.validated_data['reason'],
                grounded_by=user_id
            )
            return Response(AircraftDetailSerializer(aircraft).data)
        except AircraftNotFoundError:
            return Response(
                {'error': 'Aircraft not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=['post'])
    def unground(self, request, pk=None):
        """Remove grounding from aircraft."""
        try:
            aircraft = self.aircraft_service.unground_aircraft(pk)
            return Response(AircraftDetailSerializer(aircraft).data)
        except AircraftNotFoundError:
            return Response(
                {'error': 'Aircraft not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    # ==========================================================================
    # Availability
    # ==========================================================================

    @action(detail=True, methods=['get'])
    def availability(self, request, pk=None):
        """Check aircraft availability for a time period."""
        serializer = AircraftAvailabilitySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        try:
            availability = self.aircraft_service.check_availability(
                aircraft_id=pk,
                start_time=serializer.validated_data['start'],
                end_time=serializer.validated_data['end']
            )
            return Response(availability)
        except AircraftNotFoundError:
            return Response(
                {'error': 'Aircraft not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    # ==========================================================================
    # Engine Management
    # ==========================================================================

    @action(detail=True, methods=['get', 'post'])
    def engines(self, request, pk=None):
        """List or add engines."""
        aircraft = self.get_object()

        if request.method == 'GET':
            engines = aircraft.engines.filter(is_active=True).order_by('position')
            serializer = AircraftEngineSerializer(engines, many=True)
            return Response(serializer.data)

        # POST - Add engine
        serializer = AircraftEngineCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            engine = self.aircraft_service.add_engine(
                aircraft_id=pk,
                **serializer.validated_data
            )
            return Response(
                AircraftEngineSerializer(engine).data,
                status=status.HTTP_201_CREATED
            )
        except AircraftNotFoundError:
            return Response(
                {'error': 'Aircraft not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=['get', 'put', 'delete'], url_path='engines/(?P<engine_id>[^/.]+)')
    def engine_detail(self, request, pk=None, engine_id=None):
        """Get, update, or delete a specific engine."""
        aircraft = self.get_object()

        try:
            engine = aircraft.engines.get(id=engine_id)
        except AircraftEngine.DoesNotExist:
            return Response(
                {'error': 'Engine not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        if request.method == 'GET':
            return Response(AircraftEngineSerializer(engine).data)

        elif request.method == 'PUT':
            serializer = AircraftEngineUpdateSerializer(
                engine, data=request.data, partial=True
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(AircraftEngineSerializer(engine).data)

        elif request.method == 'DELETE':
            engine.is_active = False
            engine.save(update_fields=['is_active', 'updated_at'])
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'], url_path='engines/(?P<engine_id>[^/.]+)/overhaul')
    def engine_overhaul(self, request, pk=None, engine_id=None):
        """Record an engine overhaul."""
        aircraft = self.get_object()

        try:
            engine = aircraft.engines.get(id=engine_id)
        except AircraftEngine.DoesNotExist:
            return Response(
                {'error': 'Engine not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = EngineOverhaulSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        engine.record_overhaul(
            overhaul_date=serializer.validated_data['overhaul_date'],
            overhaul_type=serializer.validated_data['overhaul_type'],
            new_tbo=serializer.validated_data.get('new_tbo_hours')
        )

        return Response(AircraftEngineSerializer(engine).data)

    # ==========================================================================
    # Propeller Management
    # ==========================================================================

    @action(detail=True, methods=['get', 'post'])
    def propellers(self, request, pk=None):
        """List or add propellers."""
        aircraft = self.get_object()

        if request.method == 'GET':
            propellers = aircraft.propellers.filter(is_active=True).order_by('position')
            serializer = AircraftPropellerSerializer(propellers, many=True)
            return Response(serializer.data)

        # POST - Add propeller
        serializer = AircraftPropellerCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            propeller = self.aircraft_service.add_propeller(
                aircraft_id=pk,
                **serializer.validated_data
            )
            return Response(
                AircraftPropellerSerializer(propeller).data,
                status=status.HTTP_201_CREATED
            )
        except AircraftNotFoundError:
            return Response(
                {'error': 'Aircraft not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=['get', 'delete'], url_path='propellers/(?P<propeller_id>[^/.]+)')
    def propeller_detail(self, request, pk=None, propeller_id=None):
        """Get or delete a specific propeller."""
        aircraft = self.get_object()

        try:
            propeller = aircraft.propellers.get(id=propeller_id)
        except AircraftPropeller.DoesNotExist:
            return Response(
                {'error': 'Propeller not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        if request.method == 'GET':
            return Response(AircraftPropellerSerializer(propeller).data)

        elif request.method == 'DELETE':
            propeller.is_active = False
            propeller.save(update_fields=['is_active', 'updated_at'])
            return Response(status=status.HTTP_204_NO_CONTENT)
