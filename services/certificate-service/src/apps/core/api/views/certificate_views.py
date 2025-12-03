# services/certificate-service/src/apps/core/api/views/certificate_views.py
"""
Certificate ViewSet

API endpoints for certificate/license management.
"""

import logging
from uuid import UUID

from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from ...models import Certificate, CertificateStatus
from ...services import CertificateService
from ..serializers import (
    CertificateSerializer,
    CertificateCreateSerializer,
    CertificateUpdateSerializer,
    CertificateListSerializer,
    CertificateVerifySerializer,
    CertificateSuspendSerializer,
    CertificateRevokeSerializer,
    CertificateRenewSerializer,
    ExpiringCertificateSerializer,
)

logger = logging.getLogger(__name__)


class CertificateViewSet(viewsets.ModelViewSet):
    """
    ViewSet for certificate management.

    Provides CRUD operations and specialized actions for:
    - Pilot licenses (PPL, CPL, ATPL)
    - Instructor certificates (CFI, CFII)
    - Other aviation certificates

    Endpoints:
    - GET /certificates/ - List certificates
    - POST /certificates/ - Create certificate
    - GET /certificates/{id}/ - Retrieve certificate
    - PUT /certificates/{id}/ - Update certificate
    - DELETE /certificates/{id}/ - Delete certificate
    - POST /certificates/{id}/verify/ - Verify certificate
    - POST /certificates/{id}/suspend/ - Suspend certificate
    - POST /certificates/{id}/revoke/ - Revoke certificate
    - POST /certificates/{id}/reinstate/ - Reinstate certificate
    - POST /certificates/{id}/renew/ - Renew certificate
    - GET /certificates/user/{user_id}/ - Get user certificates
    - GET /certificates/expiring/ - Get expiring certificates
    - GET /certificates/statistics/ - Get statistics
    """

    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = [
        'user_id',
        'certificate_type',
        'certificate_subtype',
        'issuing_authority',
        'status',
        'verified',
    ]
    search_fields = [
        'certificate_number',
        'reference_number',
        'notes',
    ]
    ordering_fields = [
        'issue_date',
        'expiry_date',
        'created_at',
        'certificate_type',
    ]
    ordering = ['-created_at']

    def get_queryset(self):
        """Filter by organization."""
        organization_id = self.request.headers.get('X-Organization-ID')
        queryset = Certificate.objects.all()

        if organization_id:
            queryset = queryset.filter(organization_id=organization_id)

        return queryset

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'create':
            return CertificateCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return CertificateUpdateSerializer
        elif self.action == 'list':
            return CertificateListSerializer
        elif self.action == 'verify':
            return CertificateVerifySerializer
        elif self.action == 'suspend':
            return CertificateSuspendSerializer
        elif self.action == 'revoke':
            return CertificateRevokeSerializer
        elif self.action == 'renew':
            return CertificateRenewSerializer
        return CertificateSerializer

    def perform_create(self, serializer):
        """Create certificate with organization context."""
        organization_id = self.request.headers.get('X-Organization-ID')
        user_id = self.request.user.id

        service = CertificateService()
        certificate = service.create_certificate(
            organization_id=UUID(organization_id) if organization_id else None,
            created_by=user_id,
            **serializer.validated_data
        )

        serializer.instance = certificate

    def perform_update(self, serializer):
        """Update certificate."""
        serializer.save()
        logger.info(f"Certificate {serializer.instance.id} updated")

    def perform_destroy(self, instance):
        """Soft delete or archive certificate."""
        instance.status = CertificateStatus.EXPIRED
        instance.save(update_fields=['status', 'updated_at'])
        logger.info(f"Certificate {instance.id} archived")

    @action(detail=True, methods=['post'])
    def verify(self, request, pk=None):
        """
        Verify a certificate.

        POST /certificates/{id}/verify/
        """
        certificate = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = CertificateService()
        verified_cert = service.verify_certificate(
            certificate_id=certificate.id,
            verified_by=request.user.id,
            verification_method=serializer.validated_data['verification_method'],
            notes=serializer.validated_data.get('notes', '')
        )

        return Response(
            CertificateSerializer(verified_cert).data,
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['post'])
    def suspend(self, request, pk=None):
        """
        Suspend a certificate.

        POST /certificates/{id}/suspend/
        """
        certificate = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = CertificateService()
        suspended_cert = service.suspend_certificate(
            certificate_id=certificate.id,
            reason=serializer.validated_data['reason'],
            suspended_by=request.user.id
        )

        return Response(
            CertificateSerializer(suspended_cert).data,
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['post'])
    def revoke(self, request, pk=None):
        """
        Revoke a certificate.

        POST /certificates/{id}/revoke/
        """
        certificate = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = CertificateService()
        revoked_cert = service.revoke_certificate(
            certificate_id=certificate.id,
            reason=serializer.validated_data['reason'],
            revoked_by=request.user.id
        )

        return Response(
            CertificateSerializer(revoked_cert).data,
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['post'])
    def reinstate(self, request, pk=None):
        """
        Reinstate a suspended certificate.

        POST /certificates/{id}/reinstate/
        """
        certificate = self.get_object()

        service = CertificateService()
        reinstated_cert = service.reinstate_certificate(
            certificate_id=certificate.id,
            reinstated_by=request.user.id
        )

        return Response(
            CertificateSerializer(reinstated_cert).data,
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['post'])
    def renew(self, request, pk=None):
        """
        Renew a certificate.

        POST /certificates/{id}/renew/
        """
        certificate = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = CertificateService()
        renewed_cert = service.renew_certificate(
            certificate_id=certificate.id,
            new_expiry_date=serializer.validated_data['new_expiry_date'],
            new_certificate_number=serializer.validated_data.get('new_certificate_number'),
            renewed_by=request.user.id
        )

        return Response(
            CertificateSerializer(renewed_cert).data,
            status=status.HTTP_200_OK
        )

    @action(detail=False, methods=['get'], url_path='user/(?P<user_id>[^/.]+)')
    def user_certificates(self, request, user_id=None):
        """
        Get all certificates for a user.

        GET /certificates/user/{user_id}/
        """
        service = CertificateService()
        certificates = service.get_user_certificates(
            user_id=UUID(user_id),
            include_expired=request.query_params.get('include_expired', 'false').lower() == 'true'
        )

        serializer = CertificateListSerializer(certificates, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def expiring(self, request):
        """
        Get certificates expiring soon.

        GET /certificates/expiring/?days=30
        """
        organization_id = request.headers.get('X-Organization-ID')
        days = int(request.query_params.get('days', 30))

        service = CertificateService()
        expiring = service.get_expiring_certificates(
            organization_id=UUID(organization_id) if organization_id else None,
            days_ahead=days
        )

        serializer = ExpiringCertificateSerializer(expiring, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """
        Get certificate statistics for organization.

        GET /certificates/statistics/
        """
        organization_id = request.headers.get('X-Organization-ID')

        service = CertificateService()
        stats = service.get_certificate_statistics(
            organization_id=UUID(organization_id) if organization_id else None
        )

        return Response(stats)

    @action(detail=False, methods=['get'], url_path='check/(?P<user_id>[^/.]+)')
    def check_validity(self, request, user_id=None):
        """
        Check if user has valid certificate of specified type.

        GET /certificates/check/{user_id}/?type=pilot_license
        """
        certificate_type = request.query_params.get('type')

        service = CertificateService()
        result = service.check_certificate_validity(
            user_id=UUID(user_id),
            certificate_type=certificate_type
        )

        return Response(result)
