# shared/common/mixins.py
"""
Reusable Mixins for Models and Views
"""

import uuid
from django.db import models
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from typing import Any, Dict, List, Optional


# =============================================================================
# MODEL MIXINS
# =============================================================================

class UUIDPrimaryKeyMixin(models.Model):
    """
    Mixin that provides UUID as primary key instead of auto-increment integer.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Unique identifier for this record"
    )

    class Meta:
        abstract = True


class TimestampMixin(models.Model):
    """
    Mixin that provides created_at and updated_at timestamp fields.
    """

    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text="When this record was created"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="When this record was last updated"
    )

    class Meta:
        abstract = True


class SoftDeleteMixin(models.Model):
    """
    Mixin that provides soft delete functionality.
    Records are marked as deleted instead of being removed from database.
    """

    is_deleted = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Whether this record has been soft-deleted"
    )
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this record was deleted"
    )
    deleted_by = models.UUIDField(
        null=True,
        blank=True,
        help_text="User who deleted this record"
    )

    class Meta:
        abstract = True

    def soft_delete(self, deleted_by: uuid.UUID = None):
        """Mark record as deleted"""
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.deleted_by = deleted_by
        self.save(update_fields=['is_deleted', 'deleted_at', 'deleted_by'])

    def restore(self):
        """Restore a soft-deleted record"""
        self.is_deleted = False
        self.deleted_at = None
        self.deleted_by = None
        self.save(update_fields=['is_deleted', 'deleted_at', 'deleted_by'])


class AuditMixin(models.Model):
    """
    Mixin that tracks who created and last modified a record.
    """

    created_by = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="User who created this record"
    )
    updated_by = models.UUIDField(
        null=True,
        blank=True,
        help_text="User who last updated this record"
    )

    class Meta:
        abstract = True


class OrganizationMixin(models.Model):
    """
    Mixin for multi-tenant models that belong to an organization.
    """

    organization_id = models.UUIDField(
        db_index=True,
        help_text="Organization this record belongs to"
    )

    class Meta:
        abstract = True


class SlugMixin(models.Model):
    """
    Mixin that provides a URL-friendly slug field.
    """

    slug = models.SlugField(
        max_length=255,
        unique=True,
        db_index=True,
        help_text="URL-friendly identifier"
    )

    class Meta:
        abstract = True


class OrderableMixin(models.Model):
    """
    Mixin for models that can be ordered/sorted.
    """

    display_order = models.PositiveIntegerField(
        default=0,
        db_index=True,
        help_text="Order for display purposes"
    )

    class Meta:
        abstract = True
        ordering = ['display_order']


class VersionedMixin(models.Model):
    """
    Mixin for optimistic locking using version number.
    """

    version = models.PositiveIntegerField(
        default=1,
        help_text="Version number for optimistic locking"
    )

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if self.pk:
            self.version += 1
        super().save(*args, **kwargs)


class ActiveMixin(models.Model):
    """
    Mixin for models that can be activated/deactivated.
    """

    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Whether this record is active"
    )

    class Meta:
        abstract = True


class MetadataMixin(models.Model):
    """
    Mixin for storing arbitrary metadata as JSON.
    """

    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional metadata as JSON"
    )

    class Meta:
        abstract = True

    def get_meta(self, key: str, default: Any = None) -> Any:
        """Get a metadata value"""
        return self.metadata.get(key, default)

    def set_meta(self, key: str, value: Any):
        """Set a metadata value"""
        self.metadata[key] = value
        self.save(update_fields=['metadata'])


class BaseModel(
    UUIDPrimaryKeyMixin,
    TimestampMixin,
    SoftDeleteMixin,
    AuditMixin,
    OrganizationMixin
):
    """
    Combined base model with all common fields.
    Use this as the base for most models in the system.
    """

    class Meta:
        abstract = True


# =============================================================================
# VIEW MIXINS
# =============================================================================

class MultiSerializerMixin:
    """
    Mixin that allows different serializers for different actions.
    """

    serializer_classes: Dict[str, Any] = {}

    def get_serializer_class(self):
        action = getattr(self, 'action', None)
        return self.serializer_classes.get(action, self.serializer_class)


class BulkCreateMixin:
    """
    Mixin that allows bulk creation of resources.
    """

    def create(self, request, *args, **kwargs):
        bulk = isinstance(request.data, list)

        if bulk:
            serializer = self.get_serializer(data=request.data, many=True)
        else:
            serializer = self.get_serializer(data=request.data)

        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        headers = self.get_success_headers(serializer.data)
        return Response(
            {
                'success': True,
                'data': serializer.data,
                'message': f'Successfully created {len(serializer.data) if bulk else 1} record(s)'
            },
            status=status.HTTP_201_CREATED,
            headers=headers
        )


class BulkUpdateMixin:
    """
    Mixin that allows bulk update of resources.
    """

    def bulk_update(self, request, *args, **kwargs):
        if not isinstance(request.data, list):
            return Response(
                {'success': False, 'error': {'message': 'Expected a list of items'}},
                status=status.HTTP_400_BAD_REQUEST
            )

        updated = []
        errors = []

        for item in request.data:
            pk = item.get('id')
            if not pk:
                errors.append({'error': 'Missing id field'})
                continue

            try:
                instance = self.get_queryset().get(pk=pk)
                serializer = self.get_serializer(instance, data=item, partial=True)
                serializer.is_valid(raise_exception=True)
                serializer.save()
                updated.append(serializer.data)
            except Exception as e:
                errors.append({'id': pk, 'error': str(e)})

        return Response({
            'success': len(errors) == 0,
            'updated': updated,
            'errors': errors
        })


class BulkDeleteMixin:
    """
    Mixin that allows bulk deletion of resources.
    """

    def bulk_delete(self, request, *args, **kwargs):
        ids = request.data.get('ids', [])

        if not ids:
            return Response(
                {'success': False, 'error': {'message': 'No ids provided'}},
                status=status.HTTP_400_BAD_REQUEST
            )

        queryset = self.get_queryset().filter(id__in=ids)
        count = queryset.count()

        # Soft delete if model supports it
        if hasattr(queryset.model, 'soft_delete'):
            for obj in queryset:
                obj.soft_delete(deleted_by=getattr(request.user, 'id', None))
        else:
            queryset.delete()

        return Response({
            'success': True,
            'message': f'Successfully deleted {count} record(s)'
        })


class ActionLogMixin:
    """
    Mixin that logs actions performed on resources.
    """

    def perform_create(self, serializer):
        instance = serializer.save()
        self.log_action('create', instance)

    def perform_update(self, serializer):
        instance = serializer.save()
        self.log_action('update', instance)

    def perform_destroy(self, instance):
        self.log_action('delete', instance)
        instance.delete()

    def log_action(self, action: str, instance):
        """Override this method to implement actual logging"""
        import logging
        logger = logging.getLogger(__name__)
        logger.info(
            f"Action: {action} on {instance.__class__.__name__}",
            extra={
                'action': action,
                'model': instance.__class__.__name__,
                'instance_id': str(instance.pk),
                'user_id': str(getattr(self.request.user, 'id', None)),
            }
        )


class OrganizationFilterMixin:
    """
    Mixin that automatically filters queryset by organization.
    """

    def get_queryset(self):
        queryset = super().get_queryset()

        # Get organization from user or header
        org_id = getattr(self.request.user, 'organization_id', None)
        if not org_id:
            org_id = self.request.headers.get('X-Organization-ID')

        if org_id and hasattr(queryset.model, 'organization_id'):
            queryset = queryset.filter(organization_id=org_id)

        return queryset


class SoftDeleteFilterMixin:
    """
    Mixin that automatically filters out soft-deleted records.
    """

    include_deleted_param = 'include_deleted'

    def get_queryset(self):
        queryset = super().get_queryset()

        if hasattr(queryset.model, 'is_deleted'):
            include_deleted = self.request.query_params.get(
                self.include_deleted_param, 'false'
            ).lower() == 'true'

            if not include_deleted:
                queryset = queryset.filter(is_deleted=False)

        return queryset


class StandardResponseMixin:
    """
    Mixin that wraps all responses in a standard format.
    """

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        return response  # Pagination already wraps in standard format

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response({
            'success': True,
            'data': serializer.data
        })

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(
            {
                'success': True,
                'data': serializer.data,
                'message': 'Resource created successfully'
            },
            status=status.HTTP_201_CREATED,
            headers=headers
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response({
            'success': True,
            'data': serializer.data,
            'message': 'Resource updated successfully'
        })

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response({
            'success': True,
            'message': 'Resource deleted successfully'
        }, status=status.HTTP_200_OK)
