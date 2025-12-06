"""
Widget Service.

Business logic for managing dashboard widgets.
"""
import logging
from typing import Optional, Dict, Any
from uuid import UUID
from datetime import timedelta

from django.db import transaction
from django.db.models import QuerySet
from django.utils import timezone

from ..models import Widget, Dashboard
from ..exceptions import WidgetNotFound, WidgetRefreshFailed, PermissionDenied
from ..validators import (
    validate_data_source,
    validate_widget_position,
    validate_refresh_interval,
    validate_query_config,
)
from .data_fetcher_service import DataFetcherService
from .dashboard_service import DashboardService

logger = logging.getLogger(__name__)


class WidgetService:
    """Service for managing dashboard widgets."""

    @staticmethod
    def get_by_id(widget_id: UUID, organization_id: UUID) -> Widget:
        """Get a widget by ID."""
        try:
            return Widget.objects.select_related('dashboard').get(
                id=widget_id,
                dashboard__organization_id=organization_id
            )
        except Widget.DoesNotExist:
            raise WidgetNotFound(detail=f"Widget with ID {widget_id} not found.")

    @staticmethod
    def get_list_by_dashboard(dashboard_id: UUID) -> QuerySet[Widget]:
        """Get all widgets for a dashboard."""
        return Widget.objects.filter(
            dashboard_id=dashboard_id
        ).order_by('position_y', 'position_x')

    @staticmethod
    @transaction.atomic
    def create(
        dashboard_id: UUID,
        organization_id: UUID,
        user_id: UUID,
        title: str,
        widget_type: str,
        data_source: str,
        query_config: Dict[str, Any],
        visualization_config: Optional[Dict] = None,
        position_x: int = 0,
        position_y: int = 0,
        width: int = 4,
        height: int = 3,
        auto_refresh: bool = False,
        refresh_interval_seconds: int = 300,
        cache_duration_seconds: int = 60,
    ) -> Widget:
        """Create a new widget."""
        # Verify dashboard access
        dashboard = DashboardService.get_by_id(dashboard_id, organization_id)

        if dashboard.owner_id != user_id:
            raise PermissionDenied(detail="Only the dashboard owner can add widgets.")

        # Validate inputs
        validate_data_source(data_source)
        validate_query_config(query_config)
        validate_widget_position(position_x, position_y, width, height)
        if auto_refresh:
            validate_refresh_interval(refresh_interval_seconds)

        widget = Widget.objects.create(
            dashboard=dashboard,
            title=title,
            widget_type=widget_type,
            data_source=data_source,
            query_config=query_config,
            visualization_config=visualization_config or {},
            position_x=position_x,
            position_y=position_y,
            width=width,
            height=height,
            auto_refresh=auto_refresh,
            refresh_interval_seconds=refresh_interval_seconds,
            cache_duration_seconds=cache_duration_seconds,
        )

        logger.info(
            f"Created widget: {widget.id}",
            extra={'widget_id': str(widget.id), 'dashboard_id': str(dashboard_id)}
        )

        return widget

    @staticmethod
    @transaction.atomic
    def update(
        widget_id: UUID,
        organization_id: UUID,
        user_id: UUID,
        **updates
    ) -> Widget:
        """Update a widget."""
        widget = WidgetService.get_by_id(widget_id, organization_id)

        if widget.dashboard.owner_id != user_id:
            raise PermissionDenied(detail="Only the dashboard owner can edit widgets.")

        # Validate updates
        if 'data_source' in updates:
            validate_data_source(updates['data_source'])
        if 'query_config' in updates:
            validate_query_config(updates['query_config'])
        if any(k in updates for k in ['position_x', 'position_y', 'width', 'height']):
            validate_widget_position(
                updates.get('position_x', widget.position_x),
                updates.get('position_y', widget.position_y),
                updates.get('width', widget.width),
                updates.get('height', widget.height),
            )

        allowed_fields = [
            'title', 'widget_type', 'data_source', 'query_config',
            'visualization_config', 'position_x', 'position_y', 'width', 'height',
            'auto_refresh', 'refresh_interval_seconds', 'cache_duration_seconds'
        ]

        for field, value in updates.items():
            if field in allowed_fields:
                setattr(widget, field, value)

        # Clear cache when config changes
        if any(k in updates for k in ['data_source', 'query_config']):
            widget.cached_data = {}
            widget.last_cached_at = None

        widget.save()

        logger.info(f"Updated widget: {widget.id}")
        return widget

    @staticmethod
    @transaction.atomic
    def delete(widget_id: UUID, organization_id: UUID, user_id: UUID) -> None:
        """Delete a widget."""
        widget = WidgetService.get_by_id(widget_id, organization_id)

        if widget.dashboard.owner_id != user_id:
            raise PermissionDenied(detail="Only the dashboard owner can delete widgets.")

        widget.delete()
        logger.info(f"Deleted widget: {widget_id}")

    @staticmethod
    def get_data(widget_id: UUID, organization_id: UUID, force_refresh: bool = False) -> Dict:
        """
        Get widget data, using cache if available.

        Args:
            widget_id: Widget UUID
            organization_id: Organization UUID
            force_refresh: Force data refresh ignoring cache

        Returns:
            Widget data dictionary
        """
        widget = WidgetService.get_by_id(widget_id, organization_id)

        # Check cache
        if not force_refresh and widget.cached_data and widget.last_cached_at:
            cache_expires = widget.last_cached_at + timedelta(seconds=widget.cache_duration_seconds)
            if timezone.now() < cache_expires:
                return {
                    'data': widget.cached_data,
                    'cached': True,
                    'cached_at': widget.last_cached_at.isoformat(),
                }

        # Fetch fresh data
        try:
            data = DataFetcherService.fetch_data(
                data_source=widget.data_source,
                query_config=widget.query_config,
                parameters={},
                organization_id=widget.dashboard.organization_id,
            )

            # Update cache
            widget.cached_data = data
            widget.last_cached_at = timezone.now()
            widget.save(update_fields=['cached_data', 'last_cached_at'])

            return {
                'data': data,
                'cached': False,
                'cached_at': widget.last_cached_at.isoformat(),
            }

        except Exception as e:
            logger.error(f"Widget data fetch failed: {widget_id}", exc_info=True)
            raise WidgetRefreshFailed(detail=str(e))

    @staticmethod
    def refresh_all_widgets(dashboard_id: UUID, organization_id: UUID) -> Dict[str, Any]:
        """Refresh all widgets on a dashboard."""
        widgets = WidgetService.get_list_by_dashboard(dashboard_id)
        results = {}

        for widget in widgets:
            try:
                results[str(widget.id)] = WidgetService.get_data(
                    widget.id,
                    organization_id,
                    force_refresh=True
                )
            except Exception as e:
                results[str(widget.id)] = {'error': str(e)}

        return results

    @staticmethod
    @transaction.atomic
    def reorder_widgets(
        dashboard_id: UUID,
        organization_id: UUID,
        user_id: UUID,
        positions: list
    ) -> None:
        """
        Reorder widgets on a dashboard.

        Args:
            dashboard_id: Dashboard UUID
            organization_id: Organization UUID
            user_id: User performing action
            positions: List of {'widget_id': UUID, 'x': int, 'y': int, 'width': int, 'height': int}
        """
        dashboard = DashboardService.get_by_id(dashboard_id, organization_id)

        if dashboard.owner_id != user_id:
            raise PermissionDenied(detail="Only the dashboard owner can reorder widgets.")

        for pos in positions:
            widget_id = pos.get('widget_id')
            Widget.objects.filter(
                id=widget_id,
                dashboard_id=dashboard_id
            ).update(
                position_x=pos.get('x', 0),
                position_y=pos.get('y', 0),
                width=pos.get('width', 4),
                height=pos.get('height', 3),
            )

        logger.info(f"Reordered widgets on dashboard: {dashboard_id}")
