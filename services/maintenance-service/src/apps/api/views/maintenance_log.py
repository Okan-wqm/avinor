# services/maintenance-service/src/apps/api/views/maintenance_log.py
"""
Maintenance Log API Views
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone

from apps.core.models import MaintenanceLog
from apps.core.services import MaintenanceService, MaintenanceServiceError
from apps.api.serializers import (
    MaintenanceLogSerializer,
    MaintenanceLogListSerializer,
    MaintenanceLogDetailSerializer,
    MaintenanceLogCreateSerializer,
)
from apps.api.serializers.maintenance_log import MaintenanceLogApproveSerializer


class MaintenanceLogViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Maintenance Logs.

    Provides CRUD operations and log-specific actions.
    """

    queryset = MaintenanceLog.objects.all()
    serializer_class = MaintenanceLogSerializer

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.service = MaintenanceService()

    def get_serializer_class(self):
        if self.action == 'list':
            return MaintenanceLogListSerializer
        elif self.action == 'retrieve':
            return MaintenanceLogDetailSerializer
        elif self.action == 'create':
            return MaintenanceLogCreateSerializer
        return MaintenanceLogSerializer

    def get_queryset(self):
        """Filter by organization and optional parameters."""
        queryset = MaintenanceLog.objects.all()

        org_id = self.request.query_params.get('organization_id')
        if org_id:
            queryset = queryset.filter(organization_id=org_id)

        aircraft_id = self.request.query_params.get('aircraft_id')
        if aircraft_id:
            queryset = queryset.filter(aircraft_id=aircraft_id)

        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category=category)

        start_date = self.request.query_params.get('start_date')
        if start_date:
            queryset = queryset.filter(performed_date__gte=start_date)

        end_date = self.request.query_params.get('end_date')
        if end_date:
            queryset = queryset.filter(performed_date__lte=end_date)

        work_order_id = self.request.query_params.get('work_order_id')
        if work_order_id:
            queryset = queryset.filter(work_order_id=work_order_id)

        maintenance_item_id = self.request.query_params.get('maintenance_item_id')
        if maintenance_item_id:
            queryset = queryset.filter(maintenance_item_id=maintenance_item_id)

        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        return queryset.order_by('-performed_date')

    def create(self, request, *args, **kwargs):
        """Create a new maintenance log."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            log = MaintenanceLog.objects.create(**serializer.validated_data)
            return Response(
                MaintenanceLogDetailSerializer(log).data,
                status=status.HTTP_201_CREATED
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve a maintenance log."""
        serializer = MaintenanceLogApproveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            log = self.service.get_log(pk)

            log.approved_by = serializer.validated_data['approved_by']
            log.approved_by_id = serializer.validated_data['approved_by_id']
            log.approved_at = timezone.now()
            log.status = MaintenanceLog.Status.APPROVED

            if serializer.validated_data.get('signature_data'):
                log.signature_data = serializer.validated_data['signature_data']

            if serializer.validated_data.get('notes'):
                if log.notes:
                    log.notes += f"\n\nApproval Notes: {serializer.validated_data['notes']}"
                else:
                    log.notes = f"Approval Notes: {serializer.validated_data['notes']}"

            log.save()

            return Response(MaintenanceLogDetailSerializer(log).data)
        except MaintenanceServiceError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['get'])
    def aircraft_history(self, request):
        """Get maintenance history for an aircraft."""
        aircraft_id = request.query_params.get('aircraft_id')
        if not aircraft_id:
            return Response(
                {'error': 'aircraft_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        limit = int(request.query_params.get('limit', 100))

        history = self.service.get_aircraft_history(
            aircraft_id=aircraft_id,
            limit=limit
        )
        return Response(history)

    @action(detail=False, methods=['get'])
    def by_work_order(self, request):
        """Get logs for a specific work order."""
        work_order_id = request.query_params.get('work_order_id')
        if not work_order_id:
            return Response(
                {'error': 'work_order_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        logs = MaintenanceLog.objects.filter(
            work_order_id=work_order_id
        ).order_by('-performed_date')

        return Response(MaintenanceLogListSerializer(logs, many=True).data)

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get maintenance log summary statistics."""
        org_id = request.query_params.get('organization_id')
        if not org_id:
            return Response(
                {'error': 'organization_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        aircraft_id = request.query_params.get('aircraft_id')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        queryset = MaintenanceLog.objects.filter(organization_id=org_id)

        if aircraft_id:
            queryset = queryset.filter(aircraft_id=aircraft_id)
        if start_date:
            queryset = queryset.filter(performed_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(performed_date__lte=end_date)

        from django.db.models import Sum, Count, Avg

        stats = queryset.aggregate(
            total_logs=Count('id'),
            total_labor_hours=Sum('labor_hours'),
            total_labor_cost=Sum('labor_cost'),
            total_parts_cost=Sum('parts_cost'),
            total_cost=Sum('total_cost'),
            avg_cost=Avg('total_cost'),
        )

        # By category
        by_category = queryset.values('category').annotate(
            count=Count('id'),
            total_cost=Sum('total_cost')
        )

        return Response({
            'total_logs': stats['total_logs'] or 0,
            'total_labor_hours': float(stats['total_labor_hours'] or 0),
            'total_labor_cost': float(stats['total_labor_cost'] or 0),
            'total_parts_cost': float(stats['total_parts_cost'] or 0),
            'total_cost': float(stats['total_cost'] or 0),
            'average_cost': float(stats['avg_cost'] or 0),
            'by_category': {
                item['category']: {
                    'count': item['count'],
                    'total_cost': float(item['total_cost'] or 0)
                }
                for item in by_category
            }
        })
