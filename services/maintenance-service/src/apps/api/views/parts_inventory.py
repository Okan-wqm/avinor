# services/maintenance-service/src/apps/api/views/parts_inventory.py
"""
Parts Inventory API Views
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.models import PartsInventory, PartTransaction
from apps.core.services import (
    PartsService,
    PartNotFoundError,
    InsufficientInventoryError,
    MaintenanceServiceError,
)
from apps.api.serializers import (
    PartsInventorySerializer,
    PartsInventoryListSerializer,
    PartsInventoryDetailSerializer,
    PartsInventoryCreateSerializer,
    PartsInventoryUpdateSerializer,
    PartTransactionSerializer,
    PartReceiveSerializer,
    PartIssueSerializer,
)
from apps.api.serializers.parts_inventory import (
    PartAdjustSerializer,
    PartReturnSerializer,
    PartReserveSerializer,
)


class PartsInventoryViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Parts Inventory.

    Provides CRUD operations and inventory management actions.
    """

    queryset = PartsInventory.objects.all()
    serializer_class = PartsInventorySerializer

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.service = PartsService()

    def get_serializer_class(self):
        if self.action == 'list':
            return PartsInventoryListSerializer
        elif self.action == 'retrieve':
            return PartsInventoryDetailSerializer
        elif self.action == 'create':
            return PartsInventoryCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return PartsInventoryUpdateSerializer
        return PartsInventorySerializer

    def get_queryset(self):
        """Filter by organization and optional parameters."""
        queryset = PartsInventory.objects.all()

        org_id = self.request.query_params.get('organization_id')
        if org_id:
            queryset = queryset.filter(organization_id=org_id)

        location_id = self.request.query_params.get('location_id')
        if location_id:
            queryset = queryset.filter(location_id=location_id)

        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category=category)

        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        low_stock = self.request.query_params.get('low_stock')
        if low_stock and low_stock.lower() == 'true':
            from django.db.models import F
            queryset = queryset.filter(quantity_available__lte=F('minimum_quantity'))

        search = self.request.query_params.get('search')
        if search:
            from django.db.models import Q
            queryset = queryset.filter(
                Q(part_number__icontains=search) |
                Q(description__icontains=search) |
                Q(manufacturer__icontains=search)
            )

        return queryset.order_by('part_number')

    def create(self, request, *args, **kwargs):
        """Create a new part in inventory."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            part = self.service.create_part(**serializer.validated_data)
            return Response(
                PartsInventoryDetailSerializer(part).data,
                status=status.HTTP_201_CREATED
            )
        except MaintenanceServiceError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    def update(self, request, *args, **kwargs):
        """Update a part."""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()

        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        try:
            part = self.service.update_part(instance.id, **serializer.validated_data)
            return Response(PartsInventoryDetailSerializer(part).data)
        except PartNotFoundError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )

    # ==========================================================================
    # Stock Operations
    # ==========================================================================

    @action(detail=True, methods=['post'])
    def receive(self, request, pk=None):
        """Receive parts into inventory."""
        serializer = PartReceiveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            transaction = self.service.receive_parts(
                part_id=pk,
                **serializer.validated_data
            )
            return Response({
                'message': 'Parts received successfully',
                'transaction': PartTransactionSerializer(transaction).data,
            })
        except PartNotFoundError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=['post'])
    def issue(self, request, pk=None):
        """Issue parts from inventory."""
        serializer = PartIssueSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            transaction = self.service.issue_parts(
                part_id=pk,
                **serializer.validated_data
            )
            return Response({
                'message': 'Parts issued successfully',
                'transaction': PartTransactionSerializer(transaction).data,
            })
        except PartNotFoundError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )
        except InsufficientInventoryError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def adjust(self, request, pk=None):
        """Adjust inventory count."""
        serializer = PartAdjustSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            transaction = self.service.adjust_inventory(
                part_id=pk,
                **serializer.validated_data
            )
            return Response({
                'message': 'Inventory adjusted successfully',
                'transaction': PartTransactionSerializer(transaction).data,
            })
        except PartNotFoundError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=['post'])
    def return_parts(self, request, pk=None):
        """Return parts to inventory."""
        serializer = PartReturnSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            transaction = self.service.return_parts(
                part_id=pk,
                **serializer.validated_data
            )
            return Response({
                'message': 'Parts returned successfully',
                'transaction': PartTransactionSerializer(transaction).data,
            })
        except PartNotFoundError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=['post'])
    def reserve(self, request, pk=None):
        """Reserve parts for a work order."""
        serializer = PartReserveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            part = self.service.reserve_parts(
                part_id=pk,
                **serializer.validated_data
            )
            return Response({
                'message': 'Parts reserved successfully',
                'part': PartsInventorySerializer(part).data,
            })
        except PartNotFoundError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )
        except InsufficientInventoryError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def release_reservation(self, request, pk=None):
        """Release reserved parts."""
        quantity = request.data.get('quantity')
        if not quantity:
            return Response(
                {'error': 'quantity is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            part = self.service.release_reservation(
                part_id=pk,
                quantity=int(quantity)
            )
            return Response({
                'message': 'Reservation released successfully',
                'part': PartsInventorySerializer(part).data,
            })
        except PartNotFoundError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )

    # ==========================================================================
    # Queries
    # ==========================================================================

    @action(detail=True, methods=['get'])
    def transactions(self, request, pk=None):
        """Get transaction history for a part."""
        limit = int(request.query_params.get('limit', 50))

        try:
            transactions = self.service.get_part_transactions(
                part_id=pk,
                limit=limit
            )
            return Response(PartTransactionSerializer(transactions, many=True).data)
        except PartNotFoundError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['get'])
    def low_stock(self, request):
        """Get parts with low stock."""
        org_id = request.query_params.get('organization_id')
        if not org_id:
            return Response(
                {'error': 'organization_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        location_id = request.query_params.get('location_id')

        parts = self.service.get_low_stock_parts(
            organization_id=org_id,
            location_id=location_id
        )
        return Response(PartsInventoryListSerializer(parts, many=True).data)

    @action(detail=False, methods=['get'])
    def search(self, request):
        """Search parts by number, description, or manufacturer."""
        org_id = request.query_params.get('organization_id')
        query = request.query_params.get('q')

        if not org_id or not query:
            return Response(
                {'error': 'organization_id and q (query) are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        parts = self.service.search_parts(
            organization_id=org_id,
            query=query
        )
        return Response(PartsInventoryListSerializer(parts, many=True).data)

    @action(detail=False, methods=['get'])
    def by_part_number(self, request):
        """Get part by part number."""
        org_id = request.query_params.get('organization_id')
        part_number = request.query_params.get('part_number')
        location_id = request.query_params.get('location_id')

        if not org_id or not part_number:
            return Response(
                {'error': 'organization_id and part_number are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            part = self.service.get_by_part_number(
                organization_id=org_id,
                part_number=part_number,
                location_id=location_id
            )
            return Response(PartsInventoryDetailSerializer(part).data)
        except PartNotFoundError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['get'])
    def work_order_parts(self, request):
        """Get all parts used in a work order."""
        work_order_id = request.query_params.get('work_order_id')
        if not work_order_id:
            return Response(
                {'error': 'work_order_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        transactions = self.service.get_work_order_parts(work_order_id=work_order_id)
        return Response(PartTransactionSerializer(transactions, many=True).data)

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get inventory statistics."""
        org_id = request.query_params.get('organization_id')
        if not org_id:
            return Response(
                {'error': 'organization_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        location_id = request.query_params.get('location_id')

        stats = self.service.get_inventory_statistics(
            organization_id=org_id,
            location_id=location_id
        )
        return Response(stats)


class PartTransactionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for Part Transactions (read-only).

    Provides listing and retrieving of transaction history.
    """

    queryset = PartTransaction.objects.all()
    serializer_class = PartTransactionSerializer

    def get_queryset(self):
        """Filter by various parameters."""
        queryset = PartTransaction.objects.select_related('part').all()

        org_id = self.request.query_params.get('organization_id')
        if org_id:
            queryset = queryset.filter(organization_id=org_id)

        part_id = self.request.query_params.get('part_id')
        if part_id:
            queryset = queryset.filter(part_id=part_id)

        work_order_id = self.request.query_params.get('work_order_id')
        if work_order_id:
            queryset = queryset.filter(work_order_id=work_order_id)

        transaction_type = self.request.query_params.get('transaction_type')
        if transaction_type:
            queryset = queryset.filter(transaction_type=transaction_type)

        start_date = self.request.query_params.get('start_date')
        if start_date:
            queryset = queryset.filter(performed_at__date__gte=start_date)

        end_date = self.request.query_params.get('end_date')
        if end_date:
            queryset = queryset.filter(performed_at__date__lte=end_date)

        return queryset.order_by('-performed_at')
