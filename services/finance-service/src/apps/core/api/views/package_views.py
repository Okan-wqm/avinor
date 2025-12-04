# services/finance-service/src/apps/core/api/views/package_views.py
"""
Package Views

DRF viewsets for credit package management.
"""

import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from ...models.package import CreditPackage, UserPackage
from ...services.package_service import (
    PackageService,
    PackageServiceError,
    PackageNotFoundError,
    InsufficientCreditsError,
    PackageExpiredError,
)
from ..serializers.package_serializers import (
    CreditPackageSerializer,
    CreditPackageListSerializer,
    CreditPackageDetailSerializer,
    CreditPackageCreateSerializer,
    CreditPackageUpdateSerializer,
    UserPackageSerializer,
    UserPackageListSerializer,
    UserPackageDetailSerializer,
    PurchasePackageSerializer,
    UsePackageCreditSerializer,
    UsePackageHoursSerializer,
    CancelUserPackageSerializer,
    PackageUsageStatsSerializer,
)

logger = logging.getLogger(__name__)


class CreditPackageViewSet(viewsets.ViewSet):
    """
    ViewSet for managing credit packages.

    Provides package CRUD operations.
    """

    permission_classes = [IsAuthenticated]

    def get_organization_id(self, request):
        """Get organization ID from request."""
        return request.headers.get('X-Organization-ID') or request.user.organization_id

    def list(self, request):
        """
        List credit packages with filtering.

        GET /api/v1/finance/packages/
        """
        organization_id = self.get_organization_id(request)

        result = PackageService.list_packages(
            organization_id=organization_id,
            package_type=request.query_params.get('package_type'),
            is_active=request.query_params.get('is_active', True),
            is_available=request.query_params.get('is_available'),
            search=request.query_params.get('search'),
            order_by=request.query_params.get('order_by', '-sort_order'),
            limit=int(request.query_params.get('limit', 50)),
            offset=int(request.query_params.get('offset', 0)),
        )

        return Response(result)

    def retrieve(self, request, pk=None):
        """
        Get package details.

        GET /api/v1/finance/packages/{id}/
        """
        try:
            organization_id = self.get_organization_id(request)
            package = PackageService.get_package(pk, organization_id)
            serializer = CreditPackageDetailSerializer(package)
            return Response(serializer.data)
        except PackageNotFoundError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )

    def create(self, request):
        """
        Create a new package.

        POST /api/v1/finance/packages/
        """
        serializer = CreditPackageCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        organization_id = self.get_organization_id(request)

        try:
            package = PackageService.create_package(
                organization_id=organization_id,
                created_by=request.user.id,
                **serializer.validated_data
            )

            return Response(
                CreditPackageDetailSerializer(package).data,
                status=status.HTTP_201_CREATED
            )
        except PackageServiceError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    def partial_update(self, request, pk=None):
        """
        Update package.

        PATCH /api/v1/finance/packages/{id}/
        """
        serializer = CreditPackageUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        organization_id = self.get_organization_id(request)

        try:
            package = PackageService.update_package(
                package_id=pk,
                organization_id=organization_id,
                updated_by=request.user.id,
                **serializer.validated_data
            )

            return Response(CreditPackageDetailSerializer(package).data)
        except PackageNotFoundError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )
        except PackageServiceError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['get'])
    def available(self, request):
        """
        Get available packages for purchase.

        GET /api/v1/finance/packages/available/
        """
        organization_id = self.get_organization_id(request)

        result = PackageService.list_packages(
            organization_id=organization_id,
            is_available=True,
            order_by='sort_order'
        )

        return Response(result)


class UserPackageViewSet(viewsets.ViewSet):
    """
    ViewSet for managing user packages.

    Provides user package operations including purchase and usage.
    """

    permission_classes = [IsAuthenticated]

    def get_organization_id(self, request):
        """Get organization ID from request."""
        return request.headers.get('X-Organization-ID') or request.user.organization_id

    def list(self, request):
        """
        List user packages.

        GET /api/v1/finance/user-packages/
        """
        organization_id = self.get_organization_id(request)
        user_id = request.query_params.get('user_id')
        include_expired = request.query_params.get('include_expired', 'false').lower() == 'true'

        if not user_id:
            user_id = request.user.id

        packages = PackageService.get_user_packages(
            organization_id=organization_id,
            user_id=user_id,
            status=request.query_params.get('status'),
            include_expired=include_expired
        )

        return Response({
            'packages': UserPackageListSerializer(packages, many=True).data,
            'count': len(packages),
        })

    def retrieve(self, request, pk=None):
        """
        Get user package details.

        GET /api/v1/finance/user-packages/{id}/
        """
        try:
            organization_id = self.get_organization_id(request)
            user_package = PackageService.get_user_package(pk, organization_id)
            serializer = UserPackageDetailSerializer(user_package)
            return Response(serializer.data)
        except PackageNotFoundError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['post'])
    def purchase(self, request):
        """
        Purchase a package.

        POST /api/v1/finance/user-packages/purchase/
        """
        serializer = PurchasePackageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        organization_id = self.get_organization_id(request)

        try:
            user_package = PackageService.purchase_package(
                organization_id=organization_id,
                purchased_by=request.user.id,
                **serializer.validated_data
            )

            return Response(
                UserPackageDetailSerializer(user_package).data,
                status=status.HTTP_201_CREATED
            )
        except PackageNotFoundError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )
        except PackageServiceError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def use_credit(self, request, pk=None):
        """
        Use credit from package.

        POST /api/v1/finance/user-packages/{id}/use_credit/
        """
        serializer = UsePackageCreditSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            result = PackageService.use_package_credit(
                user_package_id=pk,
                used_by=request.user.id,
                **serializer.validated_data
            )

            return Response(result)
        except PackageNotFoundError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )
        except InsufficientCreditsError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except PackageExpiredError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def use_hours(self, request, pk=None):
        """
        Use hours from package.

        POST /api/v1/finance/user-packages/{id}/use_hours/
        """
        serializer = UsePackageHoursSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            result = PackageService.use_package_hours(
                user_package_id=pk,
                used_by=request.user.id,
                **serializer.validated_data
            )

            return Response(result)
        except PackageNotFoundError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )
        except InsufficientCreditsError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except PackageExpiredError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """
        Cancel a user package.

        POST /api/v1/finance/user-packages/{id}/cancel/
        """
        serializer = CancelUserPackageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            user_package = PackageService.cancel_user_package(
                user_package_id=pk,
                cancelled_by=request.user.id,
                **serializer.validated_data
            )

            return Response(UserPackageDetailSerializer(user_package).data)
        except PackageNotFoundError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )
        except PackageServiceError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['get'])
    def usage_stats(self, request, pk=None):
        """
        Get package usage statistics.

        GET /api/v1/finance/user-packages/{id}/usage_stats/
        """
        try:
            stats = PackageService.get_package_usage_stats(pk)
            return Response(stats)
        except PackageNotFoundError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['get'])
    def active(self, request):
        """
        Get active packages for a user.

        GET /api/v1/finance/user-packages/active/?user_id=...
        """
        organization_id = self.get_organization_id(request)
        user_id = request.query_params.get('user_id') or request.user.id
        package_type = request.query_params.get('package_type')

        packages = PackageService.get_active_packages(
            organization_id=organization_id,
            user_id=user_id,
            package_type=package_type
        )

        return Response({
            'packages': UserPackageListSerializer(packages, many=True).data,
            'count': len(packages),
        })

    @action(detail=False, methods=['get'])
    def available_credit(self, request):
        """
        Get available credit for a user.

        GET /api/v1/finance/user-packages/available_credit/?user_id=...
        """
        organization_id = self.get_organization_id(request)
        user_id = request.query_params.get('user_id') or request.user.id
        package_type = request.query_params.get('package_type')

        credit = PackageService.get_available_credit(
            organization_id=organization_id,
            user_id=user_id,
            package_type=package_type
        )

        hours = PackageService.get_available_hours(
            organization_id=organization_id,
            user_id=user_id,
            package_type=package_type
        )

        return Response({
            'user_id': str(user_id),
            'available_credit': float(credit),
            'available_hours': float(hours),
        })
