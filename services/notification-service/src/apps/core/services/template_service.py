"""
Template Service.

Business logic for managing notification templates.
"""
import re
import logging
from typing import Optional, Dict, Any
from uuid import UUID

from django.db import transaction
from django.db.models import QuerySet

from ..models import NotificationTemplate
from ..exceptions import TemplateNotFound, InvalidTemplate

logger = logging.getLogger(__name__)


class TemplateService:
    """Service for managing notification templates."""

    @staticmethod
    def get_by_id(template_id: UUID) -> NotificationTemplate:
        """Get template by ID."""
        try:
            return NotificationTemplate.objects.get(id=template_id, is_active=True)
        except NotificationTemplate.DoesNotExist:
            raise TemplateNotFound()

    @staticmethod
    def get_by_code(code: str) -> NotificationTemplate:
        """Get template by code."""
        try:
            return NotificationTemplate.objects.get(code=code, is_active=True)
        except NotificationTemplate.DoesNotExist:
            raise TemplateNotFound(detail=f"Template with code '{code}' not found")

    @staticmethod
    def get_list(
        organization_id: Optional[UUID] = None,
        template_type: Optional[str] = None,
    ) -> QuerySet[NotificationTemplate]:
        """Get list of templates."""
        queryset = NotificationTemplate.objects.filter(is_active=True)

        if organization_id:
            # Include org-specific and system templates
            queryset = queryset.filter(
                organization_id__in=[organization_id, None]
            )
        else:
            queryset = queryset.filter(organization_id__isnull=True)

        if template_type:
            queryset = queryset.filter(template_type=template_type)

        return queryset.order_by('name')

    @staticmethod
    @transaction.atomic
    def create(
        code: str,
        name: str,
        template_type: str,
        subject: str = "",
        body_html: str = "",
        body_text: str = "",
        organization_id: Optional[UUID] = None,
        description: str = "",
        variables: Optional[list] = None,
    ) -> NotificationTemplate:
        """Create a new template."""
        # Check for duplicate code
        if NotificationTemplate.objects.filter(code=code).exists():
            raise InvalidTemplate(detail=f"Template with code '{code}' already exists")

        template = NotificationTemplate.objects.create(
            organization_id=organization_id,
            code=code,
            name=name,
            template_type=template_type,
            description=description,
            subject=subject,
            body_html=body_html,
            body_text=body_text,
            variables=variables or [],
        )

        logger.info(f"Created template: {template.id} ({code})")
        return template

    @staticmethod
    @transaction.atomic
    def update(template_id: UUID, **updates) -> NotificationTemplate:
        """Update a template."""
        template = TemplateService.get_by_id(template_id)

        allowed_fields = [
            'name', 'description', 'subject', 'body_html',
            'body_text', 'variables', 'is_active'
        ]

        for field, value in updates.items():
            if field in allowed_fields:
                setattr(template, field, value)

        template.save()
        logger.info(f"Updated template: {template.id}")
        return template

    @staticmethod
    @transaction.atomic
    def delete(template_id: UUID) -> None:
        """Soft delete a template."""
        template = TemplateService.get_by_id(template_id)
        template.is_active = False
        template.save()
        logger.info(f"Deleted template: {template_id}")

    @staticmethod
    def render_template(template_string: str, context: Dict[str, Any]) -> str:
        """
        Render a template string with context variables.

        Uses {{variable_name}} syntax.
        """
        if not template_string:
            return ""

        def replace_var(match):
            var_name = match.group(1).strip()
            return str(context.get(var_name, f'{{{{{var_name}}}}}'))

        pattern = r'\{\{\s*(\w+)\s*\}\}'
        return re.sub(pattern, replace_var, template_string)

    @staticmethod
    def validate_template(body_html: str, body_text: str, variables: list) -> bool:
        """Validate template content."""
        # Extract variables from template
        pattern = r'\{\{\s*(\w+)\s*\}\}'
        used_vars = set()

        for content in [body_html, body_text]:
            matches = re.findall(pattern, content)
            used_vars.update(matches)

        # Check all used variables are declared
        declared_vars = set(variables)
        undefined = used_vars - declared_vars

        if undefined:
            raise InvalidTemplate(
                detail=f"Undefined variables in template: {', '.join(undefined)}"
            )

        return True
