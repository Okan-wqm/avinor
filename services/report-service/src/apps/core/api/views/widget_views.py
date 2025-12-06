"""
Widget Views.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from ...services import WidgetService
from ..serializers import (
    WidgetSerializer,
    WidgetCreateSerializer,
    WidgetUpdateSerializer,
    WidgetDataSerializer,
)


class WidgetViewSet(viewsets.ViewSet):
    """ViewSet for managing widgets."""
    permission_classes = [IsAuthenticated]

    def list(self, request):
        """List widgets for a dashboard."""
        dashboard_id = request.query_params.get('dashboard_id')
        if not dashboard_id:
            return Response(
                {'detail': 'dashboard_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        widgets = WidgetService.get_list_by_dashboard(dashboard_id)
        serializer = WidgetSerializer(widgets, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        """Get a specific widget."""
        organization_id = request.headers.get('X-Organization-ID')
        widget = WidgetService.get_by_id(pk, organization_id)
        serializer = WidgetSerializer(widget)
        return Response(serializer.data)

    def create(self, request):
        """Create a new widget."""
        serializer = WidgetCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        organization_id = request.headers.get('X-Organization-ID')
        user_id = request.user.id

        widget = WidgetService.create(
            organization_id=organization_id,
            user_id=user_id,
            **serializer.validated_data
        )

        return Response(WidgetSerializer(widget).data, status=status.HTTP_201_CREATED)

    def update(self, request, pk=None):
        """Update a widget."""
        serializer = WidgetUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        organization_id = request.headers.get('X-Organization-ID')
        user_id = request.user.id

        widget = WidgetService.update(
            widget_id=pk,
            organization_id=organization_id,
            user_id=user_id,
            **serializer.validated_data
        )

        return Response(WidgetSerializer(widget).data)

    def destroy(self, request, pk=None):
        """Delete a widget."""
        organization_id = request.headers.get('X-Organization-ID')
        user_id = request.user.id

        WidgetService.delete(pk, organization_id, user_id)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['get'])
    def data(self, request, pk=None):
        """Get widget data."""
        organization_id = request.headers.get('X-Organization-ID')
        force_refresh = request.query_params.get('refresh', 'false').lower() == 'true'

        data = WidgetService.get_data(pk, organization_id, force_refresh)
        serializer = WidgetDataSerializer(data)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def refresh(self, request, pk=None):
        """Force refresh widget data."""
        organization_id = request.headers.get('X-Organization-ID')
        data = WidgetService.get_data(pk, organization_id, force_refresh=True)
        serializer = WidgetDataSerializer(data)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def reorder(self, request):
        """Reorder widgets on a dashboard."""
        dashboard_id = request.data.get('dashboard_id')
        positions = request.data.get('positions', [])

        if not dashboard_id:
            return Response(
                {'detail': 'dashboard_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        organization_id = request.headers.get('X-Organization-ID')
        user_id = request.user.id

        WidgetService.reorder_widgets(dashboard_id, organization_id, user_id, positions)
        return Response({'status': 'success'})
