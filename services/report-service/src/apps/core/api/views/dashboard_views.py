"""
Dashboard Views.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Count

from ...services import DashboardService, WidgetService
from ..serializers import (
    DashboardSerializer,
    DashboardCreateSerializer,
    DashboardUpdateSerializer,
    DashboardListSerializer,
)


class DashboardViewSet(viewsets.ViewSet):
    """ViewSet for managing dashboards."""
    permission_classes = [IsAuthenticated]

    def list(self, request):
        """List dashboards."""
        organization_id = request.headers.get('X-Organization-ID')
        is_public = request.query_params.get('is_public')

        if is_public is not None:
            is_public = is_public.lower() == 'true'

        dashboards = DashboardService.get_list(
            organization_id=organization_id,
            is_public=is_public,
        ).annotate(widget_count=Count('widgets'))

        serializer = DashboardListSerializer(dashboards, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        """Get a specific dashboard with widgets."""
        organization_id = request.headers.get('X-Organization-ID')
        dashboard = DashboardService.get_by_id(pk, organization_id)
        serializer = DashboardSerializer(dashboard)
        return Response(serializer.data)

    def create(self, request):
        """Create a new dashboard."""
        serializer = DashboardCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        organization_id = request.headers.get('X-Organization-ID')
        user_id = request.user.id

        dashboard = DashboardService.create(
            organization_id=organization_id,
            owner_id=user_id,
            **serializer.validated_data
        )

        return Response(DashboardSerializer(dashboard).data, status=status.HTTP_201_CREATED)

    def update(self, request, pk=None):
        """Update a dashboard."""
        serializer = DashboardUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        organization_id = request.headers.get('X-Organization-ID')
        user_id = request.user.id

        dashboard = DashboardService.update(
            dashboard_id=pk,
            organization_id=organization_id,
            user_id=user_id,
            **serializer.validated_data
        )

        return Response(DashboardSerializer(dashboard).data)

    def destroy(self, request, pk=None):
        """Delete a dashboard."""
        organization_id = request.headers.get('X-Organization-ID')
        user_id = request.user.id

        DashboardService.delete(pk, organization_id, user_id)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'])
    def clone(self, request, pk=None):
        """Clone a dashboard."""
        organization_id = request.headers.get('X-Organization-ID')
        user_id = request.user.id
        new_name = request.data.get('name', 'Cloned Dashboard')

        dashboard = DashboardService.clone(
            dashboard_id=pk,
            organization_id=organization_id,
            user_id=user_id,
            new_name=new_name
        )

        return Response(DashboardSerializer(dashboard).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'])
    def default(self, request):
        """Get the default dashboard for the user."""
        organization_id = request.headers.get('X-Organization-ID')
        user_id = request.user.id

        dashboard = DashboardService.get_default(organization_id, user_id)

        if dashboard:
            return Response(DashboardSerializer(dashboard).data)
        return Response({'detail': 'No default dashboard found'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['post'])
    def refresh_all(self, request, pk=None):
        """Refresh all widgets on the dashboard."""
        organization_id = request.headers.get('X-Organization-ID')
        results = WidgetService.refresh_all_widgets(pk, organization_id)
        return Response(results)
