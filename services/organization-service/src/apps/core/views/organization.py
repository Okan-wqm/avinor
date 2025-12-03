# services/organization-service/src/apps/core/views/organization.py
"""
Organization ViewSets

REST API endpoints for organization management.
"""

import logging
from typing import Any

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction

from apps.core.models import Organization, OrganizationSetting
from apps.core.serializers import (
    OrganizationSerializer,
    OrganizationListSerializer,
    OrganizationCreateSerializer,
    OrganizationUpdateSerializer,
    OrganizationBrandingSerializer,
    OrganizationSettingsSerializer,
    OrganizationSettingSerializer,
    OrganizationUsageSerializer,
)
from apps.core.services import (
    OrganizationService,
    OrganizationError,
)

logger = logging.getLogger(__name__)


class OrganizationViewSet(viewsets.ViewSet):
    """
    ViewSet for Organization CRUD and management operations.

    Endpoints:
    - GET /organizations/ - List organizations (admin only)
    - POST /organizations/ - Create organization
    - GET /organizations/{id}/ - Get organization details
    - PUT /organizations/{id}/ - Update organization
    - DELETE /organizations/{id}/ - Soft delete organization
    - PUT /organizations/{id}/branding/ - Update branding
    - GET /organizations/{id}/usage/ - Get usage statistics
    - POST /organizations/{id}/custom-domain/ - Setup custom domain
    - POST /organizations/{id}/verify-domain/ - Verify custom domain
    - POST /organizations/{id}/activate/ - Activate organization
    - POST /organizations/{id}/suspend/ - Suspend organization
    """

    permission_classes = [IsAuthenticated]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.organization_service = OrganizationService()

    def list(self, request: Request) -> Response:
        """List all organizations (admin only)."""
        # In production, add admin permission check
        queryset = Organization.objects.filter(
            deleted_at__isnull=True
        ).select_related('subscription_plan').order_by('-created_at')

        # Filter by status if provided
        status_filter = request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        # Filter by subscription status
        subscription_status = request.query_params.get('subscription_status')
        if subscription_status:
            queryset = queryset.filter(subscription_status=subscription_status)

        # Filter by organization type
        org_type = request.query_params.get('organization_type')
        if org_type:
            queryset = queryset.filter(organization_type=org_type)

        # Search by name
        search = request.query_params.get('search')
        if search:
            queryset = queryset.filter(name__icontains=search)

        serializer = OrganizationListSerializer(queryset, many=True)
        return Response({
            'status': 'success',
            'data': serializer.data,
            'count': queryset.count(),
        })

    def create(self, request: Request) -> Response:
        """Create a new organization."""
        serializer = OrganizationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            with transaction.atomic():
                organization = self.organization_service.create_organization(
                    created_by_user_id=request.user.id,
                    **serializer.validated_data
                )

            output_serializer = OrganizationSerializer(organization)
            return Response({
                'status': 'success',
                'message': 'Organization created successfully',
                'data': output_serializer.data,
            }, status=status.HTTP_201_CREATED)

        except OrganizationError as e:
            logger.warning(f"Organization creation failed: {e}")
            return Response({
                'status': 'error',
                'message': str(e),
                'code': 'ORGANIZATION_ERROR',
            }, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request: Request, pk: str = None) -> Response:
        """Get organization details."""
        try:
            organization = self.organization_service.get_organization(pk)
            if not organization:
                return Response({
                    'status': 'error',
                    'message': 'Organization not found',
                    'code': 'NOT_FOUND',
                }, status=status.HTTP_404_NOT_FOUND)

            serializer = OrganizationSerializer(organization)
            return Response({
                'status': 'success',
                'data': serializer.data,
            })

        except OrganizationError as e:
            return Response({
                'status': 'error',
                'message': str(e),
                'code': 'ORGANIZATION_ERROR',
            }, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request: Request, pk: str = None) -> Response:
        """Update organization."""
        serializer = OrganizationUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            with transaction.atomic():
                organization = self.organization_service.update_organization(
                    organization_id=pk,
                    updated_by_user_id=request.user.id,
                    **serializer.validated_data
                )

            output_serializer = OrganizationSerializer(organization)
            return Response({
                'status': 'success',
                'message': 'Organization updated successfully',
                'data': output_serializer.data,
            })

        except OrganizationError as e:
            logger.warning(f"Organization update failed: {e}")
            return Response({
                'status': 'error',
                'message': str(e),
                'code': 'ORGANIZATION_ERROR',
            }, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request: Request, pk: str = None) -> Response:
        """Soft delete organization."""
        try:
            with transaction.atomic():
                self.organization_service.delete_organization(
                    organization_id=pk,
                    deleted_by_user_id=request.user.id
                )

            return Response({
                'status': 'success',
                'message': 'Organization deleted successfully',
            })

        except OrganizationError as e:
            logger.warning(f"Organization deletion failed: {e}")
            return Response({
                'status': 'error',
                'message': str(e),
                'code': 'ORGANIZATION_ERROR',
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['put'], url_path='branding')
    def update_branding(self, request: Request, pk: str = None) -> Response:
        """Update organization branding (logos, colors)."""
        serializer = OrganizationBrandingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            with transaction.atomic():
                organization = self.organization_service.update_branding(
                    organization_id=pk,
                    updated_by_user_id=request.user.id,
                    **serializer.validated_data
                )

            output_serializer = OrganizationSerializer(organization)
            return Response({
                'status': 'success',
                'message': 'Branding updated successfully',
                'data': output_serializer.data,
            })

        except OrganizationError as e:
            return Response({
                'status': 'error',
                'message': str(e),
                'code': 'ORGANIZATION_ERROR',
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'], url_path='usage')
    def get_usage(self, request: Request, pk: str = None) -> Response:
        """Get organization usage statistics."""
        try:
            usage = self.organization_service.get_usage_statistics(pk)

            serializer = OrganizationUsageSerializer(data=usage)
            serializer.is_valid()

            return Response({
                'status': 'success',
                'data': usage,
            })

        except OrganizationError as e:
            return Response({
                'status': 'error',
                'message': str(e),
                'code': 'ORGANIZATION_ERROR',
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='custom-domain')
    def setup_custom_domain(self, request: Request, pk: str = None) -> Response:
        """Setup custom domain for white-label."""
        domain = request.data.get('domain')
        if not domain:
            return Response({
                'status': 'error',
                'message': 'Domain is required',
                'code': 'VALIDATION_ERROR',
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                result = self.organization_service.setup_custom_domain(
                    organization_id=pk,
                    domain=domain
                )

            return Response({
                'status': 'success',
                'message': 'Custom domain configured. Please add DNS records.',
                'data': result,
            })

        except OrganizationError as e:
            return Response({
                'status': 'error',
                'message': str(e),
                'code': 'ORGANIZATION_ERROR',
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='verify-domain')
    def verify_custom_domain(self, request: Request, pk: str = None) -> Response:
        """Verify custom domain DNS records."""
        try:
            with transaction.atomic():
                result = self.organization_service.verify_custom_domain(pk)

            if result.get('verified'):
                return Response({
                    'status': 'success',
                    'message': 'Domain verified successfully',
                    'data': result,
                })
            else:
                return Response({
                    'status': 'error',
                    'message': 'Domain verification failed',
                    'data': result,
                    'code': 'VERIFICATION_FAILED',
                }, status=status.HTTP_400_BAD_REQUEST)

        except OrganizationError as e:
            return Response({
                'status': 'error',
                'message': str(e),
                'code': 'ORGANIZATION_ERROR',
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='activate')
    def activate(self, request: Request, pk: str = None) -> Response:
        """Activate organization."""
        try:
            organization = Organization.objects.get(
                id=pk,
                deleted_at__isnull=True
            )
            organization.status = Organization.Status.ACTIVE
            organization.save(update_fields=['status', 'updated_at'])

            self.organization_service._invalidate_cache(pk)

            serializer = OrganizationSerializer(organization)
            return Response({
                'status': 'success',
                'message': 'Organization activated successfully',
                'data': serializer.data,
            })

        except Organization.DoesNotExist:
            return Response({
                'status': 'error',
                'message': 'Organization not found',
                'code': 'NOT_FOUND',
            }, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['post'], url_path='suspend')
    def suspend(self, request: Request, pk: str = None) -> Response:
        """Suspend organization."""
        reason = request.data.get('reason', '')

        try:
            organization = Organization.objects.get(
                id=pk,
                deleted_at__isnull=True
            )
            organization.status = Organization.Status.SUSPENDED
            organization.save(update_fields=['status', 'updated_at'])

            self.organization_service._invalidate_cache(pk)

            logger.info(f"Organization {pk} suspended. Reason: {reason}")

            serializer = OrganizationSerializer(organization)
            return Response({
                'status': 'success',
                'message': 'Organization suspended successfully',
                'data': serializer.data,
            })

        except Organization.DoesNotExist:
            return Response({
                'status': 'error',
                'message': 'Organization not found',
                'code': 'NOT_FOUND',
            }, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['get'], url_path='by-slug/(?P<slug>[^/.]+)')
    def get_by_slug(self, request: Request, pk: str = None, slug: str = None) -> Response:
        """Get organization by slug."""
        try:
            organization = self.organization_service.get_organization_by_slug(slug)
            if not organization:
                return Response({
                    'status': 'error',
                    'message': 'Organization not found',
                    'code': 'NOT_FOUND',
                }, status=status.HTTP_404_NOT_FOUND)

            serializer = OrganizationSerializer(organization)
            return Response({
                'status': 'success',
                'data': serializer.data,
            })

        except OrganizationError as e:
            return Response({
                'status': 'error',
                'message': str(e),
                'code': 'ORGANIZATION_ERROR',
            }, status=status.HTTP_400_BAD_REQUEST)


class OrganizationSettingsViewSet(viewsets.ViewSet):
    """
    ViewSet for Organization Settings management.

    Endpoints:
    - GET /organizations/{org_id}/settings/ - List all settings
    - GET /organizations/{org_id}/settings/{category}/ - Get settings by category
    - PUT /organizations/{org_id}/settings/ - Update settings
    - DELETE /organizations/{org_id}/settings/{key}/ - Delete setting
    """

    permission_classes = [IsAuthenticated]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.organization_service = OrganizationService()

    def list(self, request: Request, organization_pk: str = None) -> Response:
        """List all settings for organization."""
        try:
            # Verify organization exists
            organization = self.organization_service.get_organization(organization_pk)
            if not organization:
                return Response({
                    'status': 'error',
                    'message': 'Organization not found',
                    'code': 'NOT_FOUND',
                }, status=status.HTTP_404_NOT_FOUND)

            settings = OrganizationSetting.objects.filter(
                organization_id=organization_pk
            ).order_by('category', 'key')

            # Group by category
            category_filter = request.query_params.get('category')
            if category_filter:
                settings = settings.filter(category=category_filter)

            serializer = OrganizationSettingSerializer(settings, many=True)

            # Group settings by category for response
            grouped_settings = {}
            for setting in serializer.data:
                category = setting['category']
                if category not in grouped_settings:
                    grouped_settings[category] = []
                grouped_settings[category].append(setting)

            return Response({
                'status': 'success',
                'data': grouped_settings,
                'count': settings.count(),
            })

        except OrganizationError as e:
            return Response({
                'status': 'error',
                'message': str(e),
                'code': 'ORGANIZATION_ERROR',
            }, status=status.HTTP_400_BAD_REQUEST)

    def create(self, request: Request, organization_pk: str = None) -> Response:
        """Create or update a setting."""
        serializer = OrganizationSettingsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            with transaction.atomic():
                setting = self.organization_service.update_settings(
                    organization_id=organization_pk,
                    settings=[serializer.validated_data],
                    updated_by_user_id=request.user.id
                )

            return Response({
                'status': 'success',
                'message': 'Setting saved successfully',
                'data': setting,
            }, status=status.HTTP_201_CREATED)

        except OrganizationError as e:
            return Response({
                'status': 'error',
                'message': str(e),
                'code': 'ORGANIZATION_ERROR',
            }, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request: Request, organization_pk: str = None, pk: str = None) -> Response:
        """Update multiple settings."""
        settings_data = request.data.get('settings', [])
        if not settings_data:
            return Response({
                'status': 'error',
                'message': 'Settings array is required',
                'code': 'VALIDATION_ERROR',
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                result = self.organization_service.update_settings(
                    organization_id=organization_pk,
                    settings=settings_data,
                    updated_by_user_id=request.user.id
                )

            return Response({
                'status': 'success',
                'message': 'Settings updated successfully',
                'data': result,
            })

        except OrganizationError as e:
            return Response({
                'status': 'error',
                'message': str(e),
                'code': 'ORGANIZATION_ERROR',
            }, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request: Request, organization_pk: str = None, pk: str = None) -> Response:
        """Delete a setting by key."""
        try:
            category = request.query_params.get('category')
            if not category:
                return Response({
                    'status': 'error',
                    'message': 'Category query parameter is required',
                    'code': 'VALIDATION_ERROR',
                }, status=status.HTTP_400_BAD_REQUEST)

            deleted = OrganizationSetting.objects.filter(
                organization_id=organization_pk,
                category=category,
                key=pk
            ).delete()

            if deleted[0] == 0:
                return Response({
                    'status': 'error',
                    'message': 'Setting not found',
                    'code': 'NOT_FOUND',
                }, status=status.HTTP_404_NOT_FOUND)

            return Response({
                'status': 'success',
                'message': 'Setting deleted successfully',
            })

        except Exception as e:
            logger.error(f"Error deleting setting: {e}")
            return Response({
                'status': 'error',
                'message': 'Failed to delete setting',
                'code': 'INTERNAL_ERROR',
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
