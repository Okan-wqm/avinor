"""
Dashboard Service.

Business logic for managing dashboards.
"""
import logging
from typing import Optional, List
from uuid import UUID

from django.db import transaction
from django.db.models import QuerySet, Prefetch

from ..models import Dashboard, Widget
from ..exceptions import DashboardNotFound, PermissionDenied

logger = logging.getLogger(__name__)


class DashboardService:
    """Service for managing dashboards."""

    @staticmethod
    def get_by_id(dashboard_id: UUID, organization_id: UUID) -> Dashboard:
        """Get a dashboard by ID with widgets."""
        try:
            return Dashboard.objects.prefetch_related(
                Prefetch('widgets', queryset=Widget.objects.order_by('position_y', 'position_x'))
            ).get(
                id=dashboard_id,
                organization_id=organization_id,
                is_active=True
            )
        except Dashboard.DoesNotExist:
            raise DashboardNotFound(detail=f"Dashboard with ID {dashboard_id} not found.")

    @staticmethod
    def get_list(
        organization_id: UUID,
        owner_id: Optional[UUID] = None,
        is_public: Optional[bool] = None,
    ) -> QuerySet[Dashboard]:
        """Get list of dashboards."""
        queryset = Dashboard.objects.filter(
            organization_id=organization_id,
            is_active=True
        )

        if owner_id:
            queryset = queryset.filter(owner_id=owner_id)

        if is_public is not None:
            queryset = queryset.filter(is_public=is_public)

        return queryset.order_by('-is_default', 'name')

    @staticmethod
    def get_default(organization_id: UUID, user_id: UUID) -> Optional[Dashboard]:
        """Get the default dashboard for a user."""
        # First try user's own default
        dashboard = Dashboard.objects.filter(
            organization_id=organization_id,
            owner_id=user_id,
            is_default=True,
            is_active=True
        ).first()

        if not dashboard:
            # Fall back to organization's public default
            dashboard = Dashboard.objects.filter(
                organization_id=organization_id,
                is_public=True,
                is_default=True,
                is_active=True
            ).first()

        return dashboard

    @staticmethod
    @transaction.atomic
    def create(
        organization_id: UUID,
        owner_id: UUID,
        name: str,
        description: str = "",
        layout_config: Optional[dict] = None,
        is_public: bool = False,
        is_default: bool = False,
        allowed_roles: Optional[List] = None,
    ) -> Dashboard:
        """Create a new dashboard."""
        # If setting as default, unset other defaults
        if is_default:
            Dashboard.objects.filter(
                organization_id=organization_id,
                owner_id=owner_id,
                is_default=True
            ).update(is_default=False)

        dashboard = Dashboard.objects.create(
            organization_id=organization_id,
            owner_id=owner_id,
            name=name,
            description=description,
            layout_config=layout_config or {},
            is_public=is_public,
            is_default=is_default,
            allowed_roles=allowed_roles or [],
        )

        logger.info(
            f"Created dashboard: {dashboard.id}",
            extra={'dashboard_id': str(dashboard.id), 'organization_id': str(organization_id)}
        )

        return dashboard

    @staticmethod
    @transaction.atomic
    def update(
        dashboard_id: UUID,
        organization_id: UUID,
        user_id: UUID,
        **updates
    ) -> Dashboard:
        """Update a dashboard."""
        dashboard = DashboardService.get_by_id(dashboard_id, organization_id)

        if dashboard.owner_id != user_id:
            raise PermissionDenied(detail="Only the dashboard owner can edit it.")

        # Handle is_default specially
        if updates.get('is_default'):
            Dashboard.objects.filter(
                organization_id=organization_id,
                owner_id=user_id,
                is_default=True
            ).exclude(id=dashboard_id).update(is_default=False)

        allowed_fields = ['name', 'description', 'layout_config', 'is_public', 'is_default', 'allowed_roles']

        for field, value in updates.items():
            if field in allowed_fields:
                setattr(dashboard, field, value)

        dashboard.save()

        logger.info(f"Updated dashboard: {dashboard.id}")
        return dashboard

    @staticmethod
    @transaction.atomic
    def delete(dashboard_id: UUID, organization_id: UUID, user_id: UUID) -> None:
        """Soft delete a dashboard."""
        dashboard = DashboardService.get_by_id(dashboard_id, organization_id)

        if dashboard.owner_id != user_id:
            raise PermissionDenied(detail="Only the dashboard owner can delete it.")

        dashboard.is_active = False
        dashboard.save()

        logger.info(f"Deleted dashboard: {dashboard_id}")

    @staticmethod
    @transaction.atomic
    def clone(
        dashboard_id: UUID,
        organization_id: UUID,
        user_id: UUID,
        new_name: str
    ) -> Dashboard:
        """Clone a dashboard with all its widgets."""
        source = DashboardService.get_by_id(dashboard_id, organization_id)

        # Create new dashboard
        new_dashboard = Dashboard.objects.create(
            organization_id=organization_id,
            owner_id=user_id,
            name=new_name,
            description=f"Cloned from: {source.name}",
            layout_config=source.layout_config,
            is_public=False,
            is_default=False,
            allowed_roles=source.allowed_roles,
        )

        # Clone widgets
        for widget in source.widgets.all():
            Widget.objects.create(
                dashboard=new_dashboard,
                title=widget.title,
                widget_type=widget.widget_type,
                data_source=widget.data_source,
                query_config=widget.query_config,
                visualization_config=widget.visualization_config,
                position_x=widget.position_x,
                position_y=widget.position_y,
                width=widget.width,
                height=widget.height,
                auto_refresh=widget.auto_refresh,
                refresh_interval_seconds=widget.refresh_interval_seconds,
                cache_duration_seconds=widget.cache_duration_seconds,
            )

        logger.info(f"Cloned dashboard {source.id} to {new_dashboard.id}")
        return new_dashboard
