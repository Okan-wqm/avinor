# services/maintenance-service/src/apps/api/views/work_order.py
"""
Work Order API Views
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.models import WorkOrder, WorkOrderTask
from apps.core.services import (
    WorkOrderService,
    WorkOrderNotFoundError,
    WorkOrderStateError,
    MaintenanceServiceError,
)
from apps.api.serializers import (
    WorkOrderSerializer,
    WorkOrderListSerializer,
    WorkOrderDetailSerializer,
    WorkOrderCreateSerializer,
    WorkOrderUpdateSerializer,
    WorkOrderTaskSerializer,
    WorkOrderTaskCreateSerializer,
    WorkOrderTaskCompleteSerializer,
)
from apps.api.serializers.work_order import (
    WorkOrderPlanSerializer,
    WorkOrderApproveSerializer,
    WorkOrderStartSerializer,
    WorkOrderCompleteSerializer,
    WorkOrderHoldSerializer,
    WorkOrderCancelSerializer,
)


class WorkOrderViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Work Orders.

    Provides CRUD operations and workflow actions.
    """

    queryset = WorkOrder.objects.all()
    serializer_class = WorkOrderSerializer

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.service = WorkOrderService()

    def get_serializer_class(self):
        if self.action == 'list':
            return WorkOrderListSerializer
        elif self.action == 'retrieve':
            return WorkOrderDetailSerializer
        elif self.action == 'create':
            return WorkOrderCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return WorkOrderUpdateSerializer
        return WorkOrderSerializer

    def get_queryset(self):
        """Filter by organization and optional parameters."""
        queryset = WorkOrder.objects.prefetch_related('tasks').all()

        org_id = self.request.query_params.get('organization_id')
        if org_id:
            queryset = queryset.filter(organization_id=org_id)

        aircraft_id = self.request.query_params.get('aircraft_id')
        if aircraft_id:
            queryset = queryset.filter(aircraft_id=aircraft_id)

        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        priority = self.request.query_params.get('priority')
        if priority:
            queryset = queryset.filter(priority=priority)

        work_order_type = self.request.query_params.get('work_order_type')
        if work_order_type:
            queryset = queryset.filter(work_order_type=work_order_type)

        assigned_to = self.request.query_params.get('assigned_to')
        if assigned_to:
            queryset = queryset.filter(assigned_to=assigned_to)

        is_open = self.request.query_params.get('is_open')
        if is_open is not None:
            is_open = is_open.lower() == 'true'
            if is_open:
                queryset = queryset.filter(
                    status__in=[
                        WorkOrder.Status.DRAFT,
                        WorkOrder.Status.PLANNED,
                        WorkOrder.Status.APPROVED,
                        WorkOrder.Status.IN_PROGRESS,
                        WorkOrder.Status.ON_HOLD
                    ]
                )
            else:
                queryset = queryset.filter(
                    status__in=[WorkOrder.Status.COMPLETED, WorkOrder.Status.CANCELLED]
                )

        return queryset.order_by('-created_at')

    def create(self, request, *args, **kwargs):
        """Create a new work order."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        maintenance_item_ids = data.pop('maintenance_item_ids', [])

        try:
            work_order = self.service.create_work_order(
                maintenance_item_ids=maintenance_item_ids,
                **data
            )
            return Response(
                WorkOrderDetailSerializer(work_order).data,
                status=status.HTTP_201_CREATED
            )
        except MaintenanceServiceError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    def update(self, request, *args, **kwargs):
        """Update a work order."""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()

        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        try:
            work_order = self.service.update_work_order(
                instance.id,
                **serializer.validated_data
            )
            return Response(WorkOrderDetailSerializer(work_order).data)
        except WorkOrderStateError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except WorkOrderNotFoundError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )

    # ==========================================================================
    # Workflow Actions
    # ==========================================================================

    @action(detail=True, methods=['post'])
    def plan(self, request, pk=None):
        """Schedule the work order."""
        serializer = WorkOrderPlanSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            work_order = self.service.plan(
                work_order_id=pk,
                **serializer.validated_data
            )
            return Response(WorkOrderDetailSerializer(work_order).data)
        except WorkOrderStateError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except WorkOrderNotFoundError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve the work order."""
        serializer = WorkOrderApproveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            work_order = self.service.approve(
                work_order_id=pk,
                **serializer.validated_data
            )
            return Response(WorkOrderDetailSerializer(work_order).data)
        except WorkOrderStateError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except WorkOrderNotFoundError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """Start work on the work order."""
        serializer = WorkOrderStartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            work_order = self.service.start(
                work_order_id=pk,
                **serializer.validated_data
            )
            return Response(WorkOrderDetailSerializer(work_order).data)
        except WorkOrderStateError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except WorkOrderNotFoundError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=['post'])
    def hold(self, request, pk=None):
        """Put work order on hold."""
        serializer = WorkOrderHoldSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            work_order = self.service.hold(
                work_order_id=pk,
                reason=serializer.validated_data['reason']
            )
            return Response(WorkOrderDetailSerializer(work_order).data)
        except WorkOrderStateError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except WorkOrderNotFoundError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=['post'])
    def resume(self, request, pk=None):
        """Resume work order from hold."""
        try:
            work_order = self.service.resume(work_order_id=pk)
            return Response(WorkOrderDetailSerializer(work_order).data)
        except WorkOrderStateError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except WorkOrderNotFoundError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Complete the work order."""
        serializer = WorkOrderCompleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            work_order = self.service.complete(
                work_order_id=pk,
                **serializer.validated_data
            )
            return Response(WorkOrderDetailSerializer(work_order).data)
        except WorkOrderStateError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except WorkOrderNotFoundError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel the work order."""
        serializer = WorkOrderCancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            work_order = self.service.cancel(
                work_order_id=pk,
                **serializer.validated_data
            )
            return Response(WorkOrderDetailSerializer(work_order).data)
        except WorkOrderStateError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except WorkOrderNotFoundError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )

    # ==========================================================================
    # Task Management
    # ==========================================================================

    @action(detail=True, methods=['post'])
    def add_task(self, request, pk=None):
        """Add a task to the work order."""
        serializer = WorkOrderTaskCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            task = self.service.add_task(
                work_order_id=pk,
                **serializer.validated_data
            )
            return Response(
                WorkOrderTaskSerializer(task).data,
                status=status.HTTP_201_CREATED
            )
        except WorkOrderNotFoundError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=['get'])
    def tasks(self, request, pk=None):
        """Get all tasks for a work order."""
        try:
            work_order = self.service.get_work_order(pk)
            tasks = work_order.tasks.all().order_by('sequence')
            return Response(WorkOrderTaskSerializer(tasks, many=True).data)
        except WorkOrderNotFoundError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )

    # ==========================================================================
    # Statistics
    # ==========================================================================

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get work order statistics."""
        org_id = request.query_params.get('organization_id')
        if not org_id:
            return Response(
                {'error': 'organization_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        aircraft_id = request.query_params.get('aircraft_id')

        stats = self.service.get_statistics(
            organization_id=org_id,
            aircraft_id=aircraft_id
        )
        return Response(stats)


class WorkOrderTaskViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Work Order Tasks.
    """

    queryset = WorkOrderTask.objects.all()
    serializer_class = WorkOrderTaskSerializer

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.service = WorkOrderService()

    def get_queryset(self):
        """Filter by work order if provided."""
        queryset = WorkOrderTask.objects.select_related('work_order').all()

        work_order_id = self.request.query_params.get('work_order_id')
        if work_order_id:
            queryset = queryset.filter(work_order_id=work_order_id)

        return queryset.order_by('work_order_id', 'sequence')

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Complete a task."""
        serializer = WorkOrderTaskCompleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            task = self.service.complete_task(
                task_id=pk,
                **serializer.validated_data
            )
            return Response(WorkOrderTaskSerializer(task).data)
        except WorkOrderNotFoundError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=['post'])
    def sign_off(self, request, pk=None):
        """Sign off on a completed task."""
        signed_by = request.data.get('signed_by')
        if not signed_by:
            return Response(
                {'error': 'signed_by is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            task = self.service.sign_off_task(task_id=pk, signed_by=signed_by)
            return Response(WorkOrderTaskSerializer(task).data)
        except WorkOrderNotFoundError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )
        except WorkOrderStateError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
