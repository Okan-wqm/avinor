"""
Shared API Mixins Module.

Provides standardized mixins for ViewSets and views across all microservices.
"""
import logging
from typing import Dict, Any, Optional, List, Type
from uuid import UUID

from django.db.models import QuerySet
from rest_framework import status
from rest_framework.response import Response
from rest_framework.request import Request

logger = logging.getLogger(__name__)


# =============================================================================
# RESPONSE MIXIN
# =============================================================================

class StandardResponseMixin:
    """
    Mixin that provides standardized API response methods.

    Ensures consistent response format across all services.
    """

    def success_response(
        self,
        data: Any = None,
        message: str = None,
        status_code: int = status.HTTP_200_OK,
        **kwargs
    ) -> Response:
        """
        Return a successful response.

        Args:
            data: Response data
            message: Optional success message
            status_code: HTTP status code
            **kwargs: Additional response fields

        Returns:
            Response object
        """
        response_data = {}

        if message:
            response_data['message'] = message

        if data is not None:
            if isinstance(data, dict) and 'results' in data:
                # Paginated response - merge at top level
                response_data.update(data)
            else:
                response_data['data'] = data

        response_data.update(kwargs)

        return Response(response_data, status=status_code)

    def created_response(
        self,
        data: Any = None,
        message: str = "Created successfully",
        **kwargs
    ) -> Response:
        """Return a 201 Created response."""
        return self.success_response(
            data=data,
            message=message,
            status_code=status.HTTP_201_CREATED,
            **kwargs
        )

    def no_content_response(self) -> Response:
        """Return a 204 No Content response."""
        return Response(status=status.HTTP_204_NO_CONTENT)

    def error_response(
        self,
        code: str,
        message: str,
        details: Dict = None,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        **kwargs
    ) -> Response:
        """
        Return an error response.

        Args:
            code: Error code
            message: Error message
            details: Additional error details
            status_code: HTTP status code
            **kwargs: Additional response fields

        Returns:
            Response object
        """
        error_data = {
            'error': {
                'code': code,
                'message': message,
            }
        }

        if details:
            error_data['error']['details'] = details

        error_data['error'].update(kwargs)

        return Response(error_data, status=status_code)

    def validation_error_response(
        self,
        errors: Dict[str, List[str]],
        message: str = "Validation failed"
    ) -> Response:
        """Return a validation error response."""
        return self.error_response(
            code='VALIDATION_ERROR',
            message=message,
            fields=errors,
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    def not_found_response(
        self,
        resource: str = "Resource",
        identifier: str = None
    ) -> Response:
        """Return a 404 Not Found response."""
        message = f"{resource} not found"
        if identifier:
            message = f"{resource} with id '{identifier}' not found"

        return self.error_response(
            code='NOT_FOUND',
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
        )

    def unauthorized_response(
        self,
        message: str = "Authentication required"
    ) -> Response:
        """Return a 401 Unauthorized response."""
        return self.error_response(
            code='UNAUTHORIZED',
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    def forbidden_response(
        self,
        message: str = "Permission denied"
    ) -> Response:
        """Return a 403 Forbidden response."""
        return self.error_response(
            code='FORBIDDEN',
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
        )

    def conflict_response(
        self,
        message: str = "Resource conflict"
    ) -> Response:
        """Return a 409 Conflict response."""
        return self.error_response(
            code='CONFLICT',
            message=message,
            status_code=status.HTTP_409_CONFLICT,
        )

    def rate_limit_response(
        self,
        message: str = "Rate limit exceeded",
        retry_after: int = None
    ) -> Response:
        """Return a 429 Too Many Requests response."""
        response = self.error_response(
            code='RATE_LIMIT_EXCEEDED',
            message=message,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        )
        if retry_after:
            response['Retry-After'] = str(retry_after)
        return response

    def service_unavailable_response(
        self,
        message: str = "Service temporarily unavailable"
    ) -> Response:
        """Return a 503 Service Unavailable response."""
        return self.error_response(
            code='SERVICE_UNAVAILABLE',
            message=message,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )


# =============================================================================
# ORGANIZATION MIXIN
# =============================================================================

class OrganizationFilterMixin:
    """
    Mixin that filters querysets by organization.

    Requires the view to have get_organization_id() method or
    organization_id in request headers.
    """

    organization_field = 'organization_id'

    def get_organization_id(self) -> Optional[UUID]:
        """
        Get organization ID from request.

        Override this method for custom organization resolution.
        """
        # Try request attribute first (set by authentication)
        if hasattr(self.request, 'organization_id'):
            return self.request.organization_id

        # Try header
        org_id = self.request.headers.get('X-Organization-ID')
        if org_id:
            try:
                return UUID(org_id)
            except (ValueError, TypeError):
                pass

        # Try query parameter (for specific use cases)
        org_id = self.request.query_params.get('organization_id')
        if org_id:
            try:
                return UUID(org_id)
            except (ValueError, TypeError):
                pass

        return None

    def get_queryset(self) -> QuerySet:
        """Filter queryset by organization."""
        queryset = super().get_queryset()
        org_id = self.get_organization_id()

        if org_id:
            filter_kwargs = {self.organization_field: org_id}
            queryset = queryset.filter(**filter_kwargs)

        return queryset

    def perform_create(self, serializer):
        """Set organization on create."""
        org_id = self.get_organization_id()
        if org_id:
            serializer.save(**{self.organization_field: org_id})
        else:
            serializer.save()


# =============================================================================
# AUDIT MIXIN
# =============================================================================

class AuditMixin:
    """
    Mixin that logs API operations for audit purposes.
    """

    audit_actions = True

    def get_audit_user(self) -> Optional[str]:
        """Get user identifier for audit logging."""
        user = getattr(self.request, 'user', None)
        if user and hasattr(user, 'id'):
            return str(user.id)
        return None

    def log_action(
        self,
        action: str,
        resource_type: str,
        resource_id: str = None,
        details: Dict = None
    ):
        """
        Log an audit action.

        Args:
            action: Action type (create, update, delete, view)
            resource_type: Type of resource
            resource_id: Resource identifier
            details: Additional details
        """
        if not self.audit_actions:
            return

        user_id = self.get_audit_user()
        org_id = getattr(self, 'get_organization_id', lambda: None)()

        log_data = {
            'action': action,
            'resource_type': resource_type,
            'resource_id': resource_id,
            'user_id': user_id,
            'organization_id': str(org_id) if org_id else None,
            'ip_address': self.get_client_ip(),
            'user_agent': self.request.META.get('HTTP_USER_AGENT', ''),
        }

        if details:
            log_data['details'] = details

        logger.info(f"Audit: {action} {resource_type}", extra=log_data)

    def get_client_ip(self) -> str:
        """Get client IP address from request."""
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return self.request.META.get('REMOTE_ADDR', '')

    def perform_create(self, serializer):
        """Log create action."""
        instance = serializer.save()
        self.log_action(
            action='create',
            resource_type=instance.__class__.__name__,
            resource_id=str(instance.pk),
        )
        return instance

    def perform_update(self, serializer):
        """Log update action."""
        instance = serializer.save()
        self.log_action(
            action='update',
            resource_type=instance.__class__.__name__,
            resource_id=str(instance.pk),
        )
        return instance

    def perform_destroy(self, instance):
        """Log delete action."""
        resource_type = instance.__class__.__name__
        resource_id = str(instance.pk)
        instance.delete()
        self.log_action(
            action='delete',
            resource_type=resource_type,
            resource_id=resource_id,
        )


# =============================================================================
# SOFT DELETE MIXIN
# =============================================================================

class SoftDeleteMixin:
    """
    Mixin for soft delete functionality.

    Requires model to have 'is_deleted' and 'deleted_at' fields.
    """

    def get_queryset(self) -> QuerySet:
        """Filter out soft-deleted records."""
        queryset = super().get_queryset()
        return queryset.filter(is_deleted=False)

    def perform_destroy(self, instance):
        """Soft delete instead of hard delete."""
        from django.utils import timezone

        instance.is_deleted = True
        instance.deleted_at = timezone.now()
        instance.save(update_fields=['is_deleted', 'deleted_at'])

    def get_queryset_with_deleted(self) -> QuerySet:
        """Get queryset including soft-deleted records."""
        return super().get_queryset()


# =============================================================================
# BULK OPERATIONS MIXIN
# =============================================================================

class BulkOperationsMixin:
    """
    Mixin that provides bulk create, update, and delete operations.
    """

    bulk_create_serializer_class = None
    bulk_update_serializer_class = None
    max_bulk_items = 100

    def bulk_create(self, request: Request) -> Response:
        """
        Create multiple items at once.

        Request body should be a list of items.
        """
        if not isinstance(request.data, list):
            return self.error_response(
                code='INVALID_FORMAT',
                message='Request body must be a list',
            )

        if len(request.data) > self.max_bulk_items:
            return self.error_response(
                code='LIMIT_EXCEEDED',
                message=f'Maximum {self.max_bulk_items} items allowed',
            )

        serializer_class = self.bulk_create_serializer_class or self.get_serializer_class()
        serializer = serializer_class(data=request.data, many=True)

        if not serializer.is_valid():
            return self.validation_error_response(serializer.errors)

        instances = serializer.save()
        output_serializer = serializer_class(instances, many=True)

        return self.created_response(
            data=output_serializer.data,
            message=f'Created {len(instances)} items',
        )

    def bulk_update(self, request: Request) -> Response:
        """
        Update multiple items at once.

        Request body should be a list of items with 'id' field.
        """
        if not isinstance(request.data, list):
            return self.error_response(
                code='INVALID_FORMAT',
                message='Request body must be a list',
            )

        if len(request.data) > self.max_bulk_items:
            return self.error_response(
                code='LIMIT_EXCEEDED',
                message=f'Maximum {self.max_bulk_items} items allowed',
            )

        updated = []
        errors = []

        for item in request.data:
            item_id = item.get('id')
            if not item_id:
                errors.append({'error': 'Missing id field', 'item': item})
                continue

            try:
                instance = self.get_queryset().get(pk=item_id)
                serializer = self.get_serializer(instance, data=item, partial=True)

                if serializer.is_valid():
                    serializer.save()
                    updated.append(serializer.data)
                else:
                    errors.append({'id': item_id, 'errors': serializer.errors})

            except self.get_queryset().model.DoesNotExist:
                errors.append({'id': item_id, 'error': 'Not found'})

        return self.success_response(
            data={'updated': updated, 'errors': errors},
            message=f'Updated {len(updated)} items, {len(errors)} errors',
        )

    def bulk_delete(self, request: Request) -> Response:
        """
        Delete multiple items at once.

        Request body should have 'ids' field with list of IDs.
        """
        ids = request.data.get('ids', [])

        if not isinstance(ids, list):
            return self.error_response(
                code='INVALID_FORMAT',
                message="'ids' must be a list",
            )

        if len(ids) > self.max_bulk_items:
            return self.error_response(
                code='LIMIT_EXCEEDED',
                message=f'Maximum {self.max_bulk_items} items allowed',
            )

        queryset = self.get_queryset().filter(pk__in=ids)
        count = queryset.count()

        # Use soft delete if available
        if hasattr(self, 'perform_destroy'):
            for instance in queryset:
                self.perform_destroy(instance)
        else:
            queryset.delete()

        return self.success_response(
            data={'deleted': count},
            message=f'Deleted {count} items',
        )


# =============================================================================
# SEARCH MIXIN
# =============================================================================

class SearchMixin:
    """
    Mixin that provides search functionality across multiple fields.
    """

    search_fields = []
    search_param = 'q'

    def get_queryset(self) -> QuerySet:
        """Apply search filter if search parameter is present."""
        queryset = super().get_queryset()
        search_term = self.request.query_params.get(self.search_param)

        if search_term and self.search_fields:
            from django.db.models import Q

            query = Q()
            for field in self.search_fields:
                query |= Q(**{f'{field}__icontains': search_term})

            queryset = queryset.filter(query)

        return queryset


# =============================================================================
# EXPORT MIXIN
# =============================================================================

class ExportMixin:
    """
    Mixin that provides data export functionality.
    """

    export_fields = None
    export_filename = 'export'

    def export_csv(self, request: Request) -> Response:
        """Export data as CSV."""
        import csv
        from django.http import HttpResponse

        queryset = self.filter_queryset(self.get_queryset())
        fields = self.export_fields or [f.name for f in queryset.model._meta.fields]

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{self.export_filename}.csv"'

        writer = csv.writer(response)
        writer.writerow(fields)

        for obj in queryset:
            row = [getattr(obj, field, '') for field in fields]
            writer.writerow(row)

        return response

    def export_json(self, request: Request) -> Response:
        """Export data as JSON."""
        import json
        from django.http import HttpResponse

        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)

        response = HttpResponse(
            json.dumps(serializer.data, indent=2, default=str),
            content_type='application/json'
        )
        response['Content-Disposition'] = f'attachment; filename="{self.export_filename}.json"'

        return response
