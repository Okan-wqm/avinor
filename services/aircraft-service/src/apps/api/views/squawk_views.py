# services/aircraft-service/src/apps/api/views/squawk_views.py
"""
Squawk Views

ViewSet for aircraft squawk/discrepancy management.
"""

import logging
import uuid

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters import rest_framework as filters

from apps.core.models import Aircraft, AircraftSquawk
from apps.core.services import SquawkService, SquawkError, AircraftNotFoundError
from apps.api.serializers import (
    SquawkListSerializer,
    SquawkDetailSerializer,
    SquawkCreateSerializer,
    SquawkUpdateSerializer,
    SquawkResolveSerializer,
    SquawkDeferSerializer,
    SquawkStatisticsSerializer,
)

logger = logging.getLogger(__name__)


class SquawkFilter(filters.FilterSet):
    """Filter for squawks."""

    status = filters.ChoiceFilter(choices=AircraftSquawk.Status.choices)
    severity = filters.ChoiceFilter(choices=AircraftSquawk.Severity.choices)
    priority = filters.ChoiceFilter(choices=AircraftSquawk.Priority.choices)
    category = filters.ChoiceFilter(choices=AircraftSquawk.Category.choices)
    is_grounding = filters.BooleanFilter()
    is_mel_item = filters.BooleanFilter()
    mel_category = filters.ChoiceFilter(choices=AircraftSquawk.MELCategory.choices)
    reported_by = filters.UUIDFilter()

    # Open squawks
    is_open = filters.BooleanFilter(method='filter_is_open')

    # Date filters
    reported_after = filters.DateFilter(field_name='reported_at', lookup_expr='date__gte')
    reported_before = filters.DateFilter(field_name='reported_at', lookup_expr='date__lte')

    class Meta:
        model = AircraftSquawk
        fields = [
            'status', 'severity', 'priority', 'category',
            'is_grounding', 'is_mel_item', 'mel_category', 'reported_by',
        ]

    def filter_is_open(self, queryset, name, value):
        if value:
            return queryset.filter(
                status__in=[
                    AircraftSquawk.Status.OPEN,
                    AircraftSquawk.Status.IN_PROGRESS,
                    AircraftSquawk.Status.DEFERRED
                ]
            )
        return queryset.exclude(
            status__in=[
                AircraftSquawk.Status.OPEN,
                AircraftSquawk.Status.IN_PROGRESS,
                AircraftSquawk.Status.DEFERRED
            ]
        )


class SquawkViewSet(viewsets.ModelViewSet):
    """
    ViewSet for squawk management.

    This viewset can be used in two contexts:
    1. Nested under aircraft: /aircraft/{aircraft_id}/squawks/
    2. Organization-wide: /squawks/

    Custom actions:
    - resolve: Resolve a squawk
    - defer: Defer a squawk
    - close: Close a resolved squawk
    - cancel: Cancel a squawk
    - start_work: Start work on a squawk
    - statistics: Get squawk statistics
    - add_photo: Add a photo to a squawk
    - overdue: Get overdue deferrals
    """

    permission_classes = [IsAuthenticated]
    filterset_class = SquawkFilter
    search_fields = ['squawk_number', 'title', 'description']
    ordering_fields = ['reported_at', 'severity', 'priority', 'status', 'created_at']
    ordering = ['-reported_at']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.squawk_service = SquawkService()

    def get_queryset(self):
        """Get squawks based on context."""
        organization_id = self.request.headers.get('X-Organization-ID')
        if not organization_id:
            return AircraftSquawk.objects.none()

        queryset = AircraftSquawk.objects.filter(
            organization_id=organization_id
        ).select_related('aircraft')

        # If nested under aircraft
        aircraft_pk = self.kwargs.get('aircraft_pk')
        if aircraft_pk:
            queryset = queryset.filter(aircraft_id=aircraft_pk)

        return queryset

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return SquawkListSerializer
        elif self.action == 'create':
            return SquawkCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return SquawkUpdateSerializer
        return SquawkDetailSerializer

    def perform_create(self, serializer):
        """Create squawk with context."""
        organization_id = self.request.headers.get('X-Organization-ID')
        user_id = self.request.headers.get('X-User-ID')
        user_name = self.request.headers.get('X-User-Name', '')

        # Get aircraft from URL or request
        aircraft_pk = self.kwargs.get('aircraft_pk')
        if not aircraft_pk:
            aircraft_pk = self.request.data.get('aircraft_id')

        if not aircraft_pk:
            raise serializers.ValidationError({'aircraft_id': 'Aircraft ID is required'})

        try:
            squawk = self.squawk_service.create_squawk(
                aircraft_id=aircraft_pk,
                organization_id=organization_id,
                reported_by=user_id,
                reported_by_name=user_name,
                **serializer.validated_data
            )
            serializer.instance = squawk
        except AircraftNotFoundError:
            raise serializers.ValidationError({'aircraft_id': 'Aircraft not found'})
        except SquawkError as e:
            raise serializers.ValidationError(str(e))

    # ==========================================================================
    # Workflow Actions
    # ==========================================================================

    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None, aircraft_pk=None):
        """Resolve a squawk."""
        serializer = SquawkResolveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user_id = request.headers.get('X-User-ID')
        user_name = request.headers.get('X-User-Name', '')

        try:
            squawk = self.squawk_service.resolve_squawk(
                squawk_id=pk,
                resolution=serializer.validated_data['resolution'],
                resolved_by=user_id,
                resolved_by_name=user_name,
                corrective_action=serializer.validated_data.get('corrective_action'),
                parts_used=serializer.validated_data.get('parts_used', []),
                labor_hours=serializer.validated_data.get('labor_hours'),
                work_order_number=serializer.validated_data.get('work_order_number'),
            )
            return Response(SquawkDetailSerializer(squawk).data)
        except SquawkError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def close(self, request, pk=None, aircraft_pk=None):
        """Close a resolved squawk."""
        user_id = request.headers.get('X-User-ID')
        user_name = request.headers.get('X-User-Name', '')
        notes = request.data.get('notes', '')

        try:
            squawk = self.squawk_service.close_squawk(
                squawk_id=pk,
                closed_by=user_id,
                closed_by_name=user_name,
                notes=notes
            )
            return Response(SquawkDetailSerializer(squawk).data)
        except SquawkError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None, aircraft_pk=None):
        """Cancel a squawk."""
        reason = request.data.get('reason', '')
        if len(reason) < 10:
            return Response(
                {'error': 'Cancellation reason must be at least 10 characters'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            squawk = self.squawk_service.cancel_squawk(
                squawk_id=pk,
                reason=reason
            )
            return Response(SquawkDetailSerializer(squawk).data)
        except SquawkError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def defer(self, request, pk=None, aircraft_pk=None):
        """Defer a squawk under MEL/CDL."""
        serializer = SquawkDeferSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user_id = request.headers.get('X-User-ID')

        try:
            squawk = self.squawk_service.defer_squawk(
                squawk_id=pk,
                mel_category=serializer.validated_data['mel_category'],
                mel_reference=serializer.validated_data.get('mel_reference'),
                operational_restrictions=serializer.validated_data.get('operational_restrictions'),
                deferred_by=user_id,
            )
            return Response(SquawkDetailSerializer(squawk).data)
        except SquawkError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def start_work(self, request, pk=None, aircraft_pk=None):
        """Mark work as started on a squawk."""
        user_id = request.headers.get('X-User-ID')
        user_name = request.headers.get('X-User-Name', '')
        work_order_id = request.data.get('work_order_id')
        work_order_number = request.data.get('work_order_number')

        try:
            squawk = self.squawk_service.start_work(
                squawk_id=pk,
                started_by=user_id,
                started_by_name=user_name,
                work_order_id=work_order_id,
                work_order_number=work_order_number,
            )
            return Response(SquawkDetailSerializer(squawk).data)
        except SquawkError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    # ==========================================================================
    # Attachments
    # ==========================================================================

    @action(detail=True, methods=['post'])
    def add_photo(self, request, pk=None, aircraft_pk=None):
        """Add a photo to a squawk."""
        photo_url = request.data.get('photo_url')
        caption = request.data.get('caption', '')

        if not photo_url:
            return Response(
                {'error': 'photo_url is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user_id = request.headers.get('X-User-ID')

        try:
            squawk = self.squawk_service.add_photo(
                squawk_id=pk,
                photo_url=photo_url,
                caption=caption,
                uploaded_by=user_id,
            )
            return Response({'photos': squawk.photos})
        except SquawkError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def add_document(self, request, pk=None, aircraft_pk=None):
        """Add a document to a squawk."""
        document_url = request.data.get('document_url')
        document_name = request.data.get('document_name', '')
        document_type = request.data.get('document_type', 'other')

        if not document_url:
            return Response(
                {'error': 'document_url is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user_id = request.headers.get('X-User-ID')

        try:
            squawk = self.squawk_service.add_document(
                squawk_id=pk,
                document_url=document_url,
                document_name=document_name,
                document_type=document_type,
                uploaded_by=user_id,
            )
            return Response({'documents': squawk.documents})
        except SquawkError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    # ==========================================================================
    # Statistics
    # ==========================================================================

    @action(detail=False, methods=['get'])
    def statistics(self, request, aircraft_pk=None):
        """Get squawk statistics."""
        organization_id = request.headers.get('X-Organization-ID')

        stats = self.squawk_service.get_statistics(
            organization_id=organization_id,
            aircraft_id=aircraft_pk
        )

        serializer = SquawkStatisticsSerializer(stats)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def overdue(self, request, aircraft_pk=None):
        """Get overdue deferred squawks."""
        organization_id = request.headers.get('X-Organization-ID')

        squawks = self.squawk_service.get_overdue_deferrals(
            organization_id=organization_id
        )

        serializer = SquawkListSerializer(squawks, many=True)
        return Response(serializer.data)
