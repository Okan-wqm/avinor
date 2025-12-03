# services/maintenance-service/src/apps/api/views/compliance.py
"""
AD/SB Compliance API Views
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.models import ADSBTracking
from apps.core.services import (
    ComplianceService,
    ComplianceError,
    MaintenanceServiceError,
)
from apps.api.serializers import (
    ADSBTrackingSerializer,
    ADSBTrackingListSerializer,
    ADSBTrackingDetailSerializer,
    ADSBTrackingCreateSerializer,
    ADSBTrackingComplianceSerializer,
)
from apps.api.serializers.compliance import (
    ADSBTrackingUpdateSerializer,
    ADSBNotApplicableSerializer,
)


class ADSBTrackingViewSet(viewsets.ModelViewSet):
    """
    ViewSet for AD/SB Tracking.

    Provides CRUD operations and compliance management actions.
    """

    queryset = ADSBTracking.objects.all()
    serializer_class = ADSBTrackingSerializer

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.service = ComplianceService()

    def get_serializer_class(self):
        if self.action == 'list':
            return ADSBTrackingListSerializer
        elif self.action == 'retrieve':
            return ADSBTrackingDetailSerializer
        elif self.action == 'create':
            return ADSBTrackingCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return ADSBTrackingUpdateSerializer
        return ADSBTrackingSerializer

    def get_queryset(self):
        """Filter by organization and optional parameters."""
        queryset = ADSBTracking.objects.all()

        org_id = self.request.query_params.get('organization_id')
        if org_id:
            queryset = queryset.filter(organization_id=org_id)

        aircraft_id = self.request.query_params.get('aircraft_id')
        if aircraft_id:
            queryset = queryset.filter(aircraft_id=aircraft_id)

        directive_type = self.request.query_params.get('directive_type')
        if directive_type:
            queryset = queryset.filter(directive_type=directive_type)

        compliance_status = self.request.query_params.get('compliance_status')
        if compliance_status:
            queryset = queryset.filter(compliance_status=compliance_status)

        is_applicable = self.request.query_params.get('is_applicable')
        if is_applicable is not None:
            queryset = queryset.filter(is_applicable=is_applicable.lower() == 'true')

        is_recurring = self.request.query_params.get('is_recurring')
        if is_recurring is not None:
            queryset = queryset.filter(is_recurring=is_recurring.lower() == 'true')

        overdue_only = self.request.query_params.get('overdue_only')
        if overdue_only and overdue_only.lower() == 'true':
            queryset = queryset.filter(is_overdue=True)

        search = self.request.query_params.get('search')
        if search:
            from django.db.models import Q
            queryset = queryset.filter(
                Q(directive_number__icontains=search) |
                Q(title__icontains=search)
            )

        return queryset.order_by('-effective_date')

    def create(self, request, *args, **kwargs):
        """Create a new AD/SB tracking record."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            directive = self.service.create_directive(**serializer.validated_data)
            return Response(
                ADSBTrackingDetailSerializer(directive).data,
                status=status.HTTP_201_CREATED
            )
        except MaintenanceServiceError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    def update(self, request, *args, **kwargs):
        """Update an AD/SB tracking record."""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()

        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        try:
            directive = self.service.update_directive(
                instance.id,
                **serializer.validated_data
            )
            return Response(ADSBTrackingDetailSerializer(directive).data)
        except ComplianceError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )

    # ==========================================================================
    # Compliance Actions
    # ==========================================================================

    @action(detail=True, methods=['post'])
    def record_compliance(self, request, pk=None):
        """Record compliance with a directive."""
        serializer = ADSBTrackingComplianceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            directive = self.service.record_compliance(
                directive_id=pk,
                **serializer.validated_data
            )
            return Response({
                'message': 'Compliance recorded successfully',
                'directive': ADSBTrackingDetailSerializer(directive).data,
            })
        except ComplianceError as e:
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
    def mark_not_applicable(self, request, pk=None):
        """Mark a directive as not applicable."""
        serializer = ADSBNotApplicableSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            directive = self.service.mark_not_applicable(
                directive_id=pk,
                reason=serializer.validated_data['reason']
            )
            return Response({
                'message': 'Directive marked as not applicable',
                'directive': ADSBTrackingDetailSerializer(directive).data,
            })
        except ComplianceError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )

    # ==========================================================================
    # Queries
    # ==========================================================================

    @action(detail=False, methods=['get'])
    def pending(self, request):
        """Get all pending directives."""
        org_id = request.query_params.get('organization_id')
        if not org_id:
            return Response(
                {'error': 'organization_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        aircraft_id = request.query_params.get('aircraft_id')

        directives = self.service.get_pending_directives(
            organization_id=org_id,
            aircraft_id=aircraft_id
        )
        return Response(ADSBTrackingListSerializer(directives, many=True).data)

    @action(detail=False, methods=['get'])
    def upcoming(self, request):
        """Get directives coming due."""
        org_id = request.query_params.get('organization_id')
        if not org_id:
            return Response(
                {'error': 'organization_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        aircraft_id = request.query_params.get('aircraft_id')
        days_ahead = int(request.query_params.get('days_ahead', 30))
        hours_ahead = int(request.query_params.get('hours_ahead', 50))

        directives = self.service.get_upcoming_compliance(
            organization_id=org_id,
            aircraft_id=aircraft_id,
            days_ahead=days_ahead,
            hours_ahead=hours_ahead
        )
        return Response(ADSBTrackingListSerializer(directives, many=True).data)

    @action(detail=False, methods=['get'])
    def aircraft_status(self, request):
        """Get compliance status for an aircraft."""
        aircraft_id = request.query_params.get('aircraft_id')
        if not aircraft_id:
            return Response(
                {'error': 'aircraft_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        status_data = self.service.get_aircraft_compliance_status(
            aircraft_id=aircraft_id
        )
        return Response(status_data)

    @action(detail=False, methods=['post'])
    def update_status(self, request):
        """Update compliance status for all directives on an aircraft."""
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
    def statistics(self, request):
        """Get compliance statistics."""
        org_id = request.query_params.get('organization_id')
        if not org_id:
            return Response(
                {'error': 'organization_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        stats = self.service.get_compliance_statistics(organization_id=org_id)
        return Response(stats)

    @action(detail=False, methods=['get'])
    def by_type(self, request):
        """Get directives grouped by type."""
        org_id = request.query_params.get('organization_id')
        if not org_id:
            return Response(
                {'error': 'organization_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        aircraft_id = request.query_params.get('aircraft_id')

        from django.db.models import Count

        queryset = ADSBTracking.objects.filter(
            organization_id=org_id,
            is_applicable=True
        )

        if aircraft_id:
            queryset = queryset.filter(aircraft_id=aircraft_id)

        # Group by type
        by_type = {}
        for directive_type in ['AD', 'SB', 'SL', 'SIL', 'ASB']:
            type_queryset = queryset.filter(directive_type=directive_type)
            by_type[directive_type] = {
                'total': type_queryset.count(),
                'pending': type_queryset.filter(
                    compliance_status=ADSBTracking.ComplianceStatus.PENDING
                ).count(),
                'compliant': type_queryset.filter(
                    compliance_status=ADSBTracking.ComplianceStatus.COMPLIANT
                ).count(),
                'overdue': type_queryset.filter(is_overdue=True).count(),
            }

        return Response(by_type)
