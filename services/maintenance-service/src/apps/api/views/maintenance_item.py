# services/maintenance-service/src/apps/api/views/maintenance_item.py
"""
Maintenance Item API Views
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.models import MaintenanceItem
from apps.core.services import (
    MaintenanceService,
    MaintenanceItemNotFoundError,
    MaintenanceServiceError,
)
from apps.api.serializers import (
    MaintenanceItemSerializer,
    MaintenanceItemListSerializer,
    MaintenanceItemDetailSerializer,
    MaintenanceItemCreateSerializer,
    MaintenanceItemUpdateSerializer,
    MaintenanceItemComplianceSerializer,
)
from apps.api.serializers.maintenance_item import (
    MaintenanceItemDeferSerializer,
    MaintenanceStatusSerializer,
)


class MaintenanceItemViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Maintenance Items.

    Provides CRUD operations and maintenance-specific actions.
    """

    queryset = MaintenanceItem.objects.all()
    serializer_class = MaintenanceItemSerializer

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.service = MaintenanceService()

    def get_serializer_class(self):
        if self.action == 'list':
            return MaintenanceItemListSerializer
        elif self.action == 'retrieve':
            return MaintenanceItemDetailSerializer
        elif self.action == 'create':
            return MaintenanceItemCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return MaintenanceItemUpdateSerializer
        return MaintenanceItemSerializer

    def get_queryset(self):
        """Filter by organization and optional parameters."""
        queryset = MaintenanceItem.objects.all()

        # Filter by organization (required)
        org_id = self.request.query_params.get('organization_id')
        if org_id:
            queryset = queryset.filter(organization_id=org_id)

        # Optional filters
        aircraft_id = self.request.query_params.get('aircraft_id')
        if aircraft_id:
            queryset = queryset.filter(aircraft_id=aircraft_id)

        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category=category)

        compliance_status = self.request.query_params.get('compliance_status')
        if compliance_status:
            queryset = queryset.filter(compliance_status=compliance_status)

        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        is_mandatory = self.request.query_params.get('is_mandatory')
        if is_mandatory is not None:
            queryset = queryset.filter(is_mandatory=is_mandatory.lower() == 'true')

        search = self.request.query_params.get('search')
        if search:
            from django.db.models import Q
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(code__icontains=search) |
                Q(description__icontains=search)
            )

        return queryset.order_by('next_due_hours', 'next_due_date')

    def create(self, request, *args, **kwargs):
        """Create a new maintenance item."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            item = self.service.create_item(**serializer.validated_data)
            return Response(
                MaintenanceItemDetailSerializer(item).data,
                status=status.HTTP_201_CREATED
            )
        except MaintenanceServiceError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    def update(self, request, *args, **kwargs):
        """Update a maintenance item."""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()

        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        try:
            item = self.service.update_item(instance.id, **serializer.validated_data)
            return Response(MaintenanceItemDetailSerializer(item).data)
        except MaintenanceItemNotFoundError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=['post'])
    def record_compliance(self, request, pk=None):
        """Record compliance for a maintenance item."""
        serializer = MaintenanceItemComplianceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            log = self.service.record_compliance(
                item_id=pk,
                **serializer.validated_data
            )
            return Response({
                'message': 'Compliance recorded successfully',
                'log_id': str(log.id),
                'log_number': log.log_number,
            })
        except MaintenanceItemNotFoundError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )
        except MaintenanceServiceError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def defer(self, request, pk=None):
        """Defer maintenance item."""
        serializer = MaintenanceItemDeferSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            item = self.service.get_item(pk)
            item.defer(
                new_due_date=serializer.validated_data.get('deferred_to_date'),
                new_due_hours=serializer.validated_data.get('deferred_to_hours'),
                reason=serializer.validated_data['reason'],
                approved_by=serializer.validated_data.get('approved_by')
            )
            return Response(MaintenanceItemDetailSerializer(item).data)
        except MaintenanceItemNotFoundError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['get'])
    def aircraft_status(self, request):
        """Get maintenance status for an aircraft."""
        aircraft_id = request.query_params.get('aircraft_id')
        if not aircraft_id:
            return Response(
                {'error': 'aircraft_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        current_hours = request.query_params.get('current_hours')
        if current_hours:
            from decimal import Decimal
            current_hours = Decimal(current_hours)

        result = self.service.get_aircraft_maintenance_status(
            aircraft_id=aircraft_id,
            current_hours=current_hours
        )
        return Response(result)

    @action(detail=False, methods=['get'])
    def upcoming(self, request):
        """Get upcoming maintenance items."""
        aircraft_id = request.query_params.get('aircraft_id')
        if not aircraft_id:
            return Response(
                {'error': 'aircraft_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        hours_ahead = int(request.query_params.get('hours_ahead', 50))
        days_ahead = int(request.query_params.get('days_ahead', 90))

        items = self.service.get_upcoming_maintenance(
            aircraft_id=aircraft_id,
            hours_ahead=hours_ahead,
            days_ahead=days_ahead
        )
        return Response(items)

    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        """Get dashboard statistics."""
        org_id = request.query_params.get('organization_id')
        if not org_id:
            return Response(
                {'error': 'organization_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        stats = self.service.get_dashboard_stats(organization_id=org_id)
        return Response(stats)

    @action(detail=False, methods=['post'])
    def update_compliance_status(self, request):
        """Update compliance status for all items on an aircraft."""
        aircraft_id = request.data.get('aircraft_id')
        current_hours = request.data.get('current_hours')
        current_cycles = request.data.get('current_cycles')

        if not aircraft_id or current_hours is None:
            return Response(
                {'error': 'aircraft_id and current_hours are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        from decimal import Decimal
        counts = self.service.update_compliance_status(
            aircraft_id=aircraft_id,
            current_hours=Decimal(str(current_hours)),
            current_cycles=current_cycles
        )
        return Response(counts)

    @action(detail=False, methods=['get'])
    def templates(self, request):
        """Get maintenance item templates."""
        org_id = request.query_params.get('organization_id')
        if not org_id:
            return Response(
                {'error': 'organization_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        templates = MaintenanceItem.objects.filter(
            organization_id=org_id,
            is_template=True,
            status=MaintenanceItem.Status.ACTIVE
        )
        return Response(MaintenanceItemListSerializer(templates, many=True).data)

    @action(detail=True, methods=['post'])
    def apply_template(self, request, pk=None):
        """Apply a template to an aircraft."""
        aircraft_id = request.data.get('aircraft_id')
        initial_hours = request.data.get('initial_hours')
        initial_date = request.data.get('initial_date')

        if not aircraft_id:
            return Response(
                {'error': 'aircraft_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            from decimal import Decimal
            from datetime import datetime

            item = self.service.create_from_template(
                template_id=pk,
                aircraft_id=aircraft_id,
                initial_hours=Decimal(str(initial_hours)) if initial_hours else None,
                initial_date=datetime.strptime(initial_date, '%Y-%m-%d').date() if initial_date else None
            )
            return Response(
                MaintenanceItemDetailSerializer(item).data,
                status=status.HTTP_201_CREATED
            )
        except MaintenanceServiceError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
