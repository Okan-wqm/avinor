"""
Report Template Service.

Business logic for managing report templates.
"""
import logging
from typing import Optional, List
from uuid import UUID
from django.db import transaction
from django.db.models import QuerySet

from ..models import ReportTemplate
from ..exceptions import (
    ReportTemplateNotFound,
    DuplicateTemplateError,
    PermissionDenied,
)
from ..validators import (
    validate_data_source,
    validate_columns,
    validate_query_config,
    validate_visualization_config,
)

logger = logging.getLogger(__name__)


class ReportTemplateService:
    """Service for managing report templates."""

    @staticmethod
    def get_by_id(template_id: UUID, organization_id: UUID) -> ReportTemplate:
        """
        Get a report template by ID.

        Args:
            template_id: Template UUID
            organization_id: Organization UUID for access control

        Returns:
            ReportTemplate instance

        Raises:
            ReportTemplateNotFound: If template doesn't exist
        """
        try:
            return ReportTemplate.objects.get(
                id=template_id,
                organization_id=organization_id,
                is_active=True
            )
        except ReportTemplate.DoesNotExist:
            raise ReportTemplateNotFound(
                detail=f"Template with ID {template_id} not found."
            )

    @staticmethod
    def get_list(
        organization_id: UUID,
        report_type: Optional[str] = None,
        is_public: Optional[bool] = None,
        created_by_id: Optional[UUID] = None,
    ) -> QuerySet[ReportTemplate]:
        """
        Get list of report templates with filters.

        Args:
            organization_id: Organization UUID
            report_type: Filter by report type
            is_public: Filter by public status
            created_by_id: Filter by creator

        Returns:
            QuerySet of ReportTemplate
        """
        queryset = ReportTemplate.objects.filter(
            organization_id=organization_id,
            is_active=True
        )

        if report_type:
            queryset = queryset.filter(report_type=report_type)

        if is_public is not None:
            queryset = queryset.filter(is_public=is_public)

        if created_by_id:
            queryset = queryset.filter(created_by_id=created_by_id)

        return queryset.order_by('name')

    @staticmethod
    @transaction.atomic
    def create(
        organization_id: UUID,
        created_by_id: UUID,
        name: str,
        report_type: str,
        data_source: str,
        columns: List[dict],
        description: str = "",
        query_config: Optional[dict] = None,
        chart_type: str = "",
        visualization_config: Optional[dict] = None,
        grouping: Optional[List] = None,
        sorting: Optional[List] = None,
        is_public: bool = False,
        allowed_roles: Optional[List] = None,
    ) -> ReportTemplate:
        """
        Create a new report template.

        Args:
            organization_id: Organization UUID
            created_by_id: User UUID who created
            name: Template name
            report_type: Type of report
            data_source: Service to query for data
            columns: Column definitions
            description: Template description
            query_config: Query configuration
            chart_type: Visualization chart type
            visualization_config: Visualization settings
            grouping: Grouping configuration
            sorting: Sorting configuration
            is_public: Whether template is public
            allowed_roles: Roles allowed to use template

        Returns:
            Created ReportTemplate

        Raises:
            DuplicateTemplateError: If name exists
            ValidationError: If validation fails
        """
        # Validate inputs
        validate_data_source(data_source)
        validate_columns(columns)
        if query_config:
            validate_query_config(query_config)
        if visualization_config and chart_type:
            validate_visualization_config(visualization_config, chart_type)

        # Check for duplicate name
        if ReportTemplate.objects.filter(
            organization_id=organization_id,
            name=name,
            is_active=True
        ).exists():
            raise DuplicateTemplateError(
                detail=f"Template with name '{name}' already exists."
            )

        template = ReportTemplate.objects.create(
            organization_id=organization_id,
            created_by_id=created_by_id,
            name=name,
            description=description,
            report_type=report_type,
            data_source=data_source,
            query_config=query_config or {},
            chart_type=chart_type,
            visualization_config=visualization_config or {},
            columns=columns,
            grouping=grouping or [],
            sorting=sorting or [],
            is_public=is_public,
            allowed_roles=allowed_roles or [],
        )

        logger.info(
            f"Created report template: {template.id}",
            extra={
                'template_id': str(template.id),
                'organization_id': str(organization_id),
                'report_type': report_type,
            }
        )

        return template

    @staticmethod
    @transaction.atomic
    def update(
        template_id: UUID,
        organization_id: UUID,
        user_id: UUID,
        **updates
    ) -> ReportTemplate:
        """
        Update a report template.

        Args:
            template_id: Template UUID
            organization_id: Organization UUID
            user_id: User performing update
            **updates: Fields to update

        Returns:
            Updated ReportTemplate

        Raises:
            ReportTemplateNotFound: If template doesn't exist
            PermissionDenied: If user cannot edit
        """
        template = ReportTemplateService.get_by_id(template_id, organization_id)

        # Check permissions (only creator or admin can edit)
        if template.created_by_id != user_id:
            raise PermissionDenied(
                detail="Only the template creator can edit this template."
            )

        # Validate updates
        if 'data_source' in updates:
            validate_data_source(updates['data_source'])
        if 'columns' in updates:
            validate_columns(updates['columns'])
        if 'query_config' in updates:
            validate_query_config(updates['query_config'])

        # Apply updates
        allowed_fields = [
            'name', 'description', 'data_source', 'query_config',
            'chart_type', 'visualization_config', 'columns',
            'grouping', 'sorting', 'is_public', 'allowed_roles'
        ]

        for field, value in updates.items():
            if field in allowed_fields:
                setattr(template, field, value)

        template.save()

        logger.info(
            f"Updated report template: {template.id}",
            extra={
                'template_id': str(template.id),
                'updated_fields': list(updates.keys()),
            }
        )

        return template

    @staticmethod
    @transaction.atomic
    def delete(
        template_id: UUID,
        organization_id: UUID,
        user_id: UUID
    ) -> None:
        """
        Soft delete a report template.

        Args:
            template_id: Template UUID
            organization_id: Organization UUID
            user_id: User performing delete

        Raises:
            ReportTemplateNotFound: If template doesn't exist
            PermissionDenied: If user cannot delete
        """
        template = ReportTemplateService.get_by_id(template_id, organization_id)

        # Check permissions
        if template.created_by_id != user_id:
            raise PermissionDenied(
                detail="Only the template creator can delete this template."
            )

        template.is_active = False
        template.save()

        logger.info(
            f"Deleted report template: {template.id}",
            extra={'template_id': str(template.id)}
        )

    @staticmethod
    def clone(
        template_id: UUID,
        organization_id: UUID,
        user_id: UUID,
        new_name: str
    ) -> ReportTemplate:
        """
        Clone an existing template.

        Args:
            template_id: Source template UUID
            organization_id: Organization UUID
            user_id: User creating clone
            new_name: Name for cloned template

        Returns:
            Cloned ReportTemplate
        """
        source = ReportTemplateService.get_by_id(template_id, organization_id)

        return ReportTemplateService.create(
            organization_id=organization_id,
            created_by_id=user_id,
            name=new_name,
            description=f"Cloned from: {source.name}",
            report_type=source.report_type,
            data_source=source.data_source,
            query_config=source.query_config,
            chart_type=source.chart_type,
            visualization_config=source.visualization_config,
            columns=source.columns,
            grouping=source.grouping,
            sorting=source.sorting,
            is_public=False,  # Clones are private by default
            allowed_roles=source.allowed_roles,
        )
