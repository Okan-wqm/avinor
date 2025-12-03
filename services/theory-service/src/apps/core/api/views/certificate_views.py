# services/theory-service/src/apps/core/api/views/certificate_views.py
"""
Certificate Views

ViewSets for certificate-related API endpoints.
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny

from ...models import Certificate
from ...services import CertificateService
from ..serializers import (
    CertificateListSerializer,
    CertificateDetailSerializer,
    CertificateGenerateSerializer,
    CertificateRevokeSerializer,
    CertificateVerifySerializer,
    CertificateUpdateDocumentSerializer,
)


class CertificateViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for managing certificates.

    Provides read access plus generate, issue, revoke actions.
    """

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Get certificates filtered by organization."""
        organization_id = self.request.headers.get('X-Organization-ID')
        user_id = self.request.query_params.get('user_id')

        # Regular users can only see their own certificates
        if not user_id:
            user_id = str(self.request.user.id)

        return CertificateService.get_certificates(
            organization_id=organization_id,
            user_id=user_id,
            course_id=self.request.query_params.get('course_id'),
            status=self.request.query_params.get('status'),
        )

    def get_serializer_class(self):
        """Return appropriate serializer class."""
        if self.action == 'list':
            return CertificateListSerializer
        return CertificateDetailSerializer

    @action(detail=False, methods=['post'])
    def generate(self, request):
        """Generate a certificate for a completed enrollment."""
        organization_id = request.headers.get('X-Organization-ID')
        serializer = CertificateGenerateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            certificate = CertificateService.generate_certificate(
                organization_id=organization_id,
                issued_by=str(request.user.id),
                **serializer.validated_data
            )

            return Response(
                CertificateDetailSerializer(certificate).data,
                status=status.HTTP_201_CREATED
            )
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def issue(self, request, pk=None):
        """Issue a generated certificate."""
        organization_id = request.headers.get('X-Organization-ID')

        try:
            certificate = CertificateService.issue_certificate(
                certificate_id=pk,
                organization_id=organization_id,
                issued_by=str(request.user.id)
            )
            return Response(CertificateDetailSerializer(certificate).data)
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def revoke(self, request, pk=None):
        """Revoke a certificate."""
        organization_id = request.headers.get('X-Organization-ID')
        serializer = CertificateRevokeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            certificate = CertificateService.revoke_certificate(
                certificate_id=pk,
                organization_id=organization_id,
                reason=serializer.validated_data['reason'],
                revoked_by=str(request.user.id)
            )
            return Response(CertificateDetailSerializer(certificate).data)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def verify(self, request):
        """Verify a certificate (public endpoint)."""
        serializer = CertificateVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = CertificateService.verify_certificate(
            verification_code=serializer.validated_data.get('verification_code'),
            certificate_number=serializer.validated_data.get('certificate_number')
        )

        return Response(result)

    @action(detail=True, methods=['post'], url_path='update-document')
    def update_document(self, request, pk=None):
        """Update certificate document URLs."""
        organization_id = request.headers.get('X-Organization-ID')
        serializer = CertificateUpdateDocumentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        certificate = CertificateService.update_certificate_document(
            certificate_id=pk,
            organization_id=organization_id,
            **serializer.validated_data
        )

        return Response(CertificateDetailSerializer(certificate).data)

    @action(detail=True, methods=['post'], url_path='make-public')
    def make_public(self, request, pk=None):
        """Make certificate publicly shareable."""
        try:
            certificate = CertificateService.make_public(
                certificate_id=pk,
                user_id=str(request.user.id)
            )
            return Response(CertificateDetailSerializer(certificate).data)
        except Certificate.DoesNotExist:
            return Response(
                {'error': 'Certificate not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=['post'], url_path='make-private')
    def make_private(self, request, pk=None):
        """Make certificate private."""
        try:
            certificate = CertificateService.make_private(
                certificate_id=pk,
                user_id=str(request.user.id)
            )
            return Response(CertificateDetailSerializer(certificate).data)
        except Certificate.DoesNotExist:
            return Response(
                {'error': 'Certificate not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=['post'], url_path='linkedin-share')
    def linkedin_share(self, request, pk=None):
        """Record LinkedIn share and get LinkedIn data."""
        try:
            certificate = CertificateService.record_linkedin_share(
                certificate_id=pk,
                user_id=str(request.user.id)
            )

            # Get certificate for LinkedIn data
            cert = CertificateService.get_certificate(pk, user_id=str(request.user.id))

            return Response({
                'certificate': CertificateDetailSerializer(certificate).data,
                'linkedin_data': cert.get_linkedin_data()
            })
        except Certificate.DoesNotExist:
            return Response(
                {'error': 'Certificate not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=['get'], permission_classes=[AllowAny])
    def public(self, request, pk=None):
        """Get public certificate data."""
        try:
            data = CertificateService.get_public_certificate(certificate_id=pk)
            return Response(data)
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_403_FORBIDDEN
            )
        except Certificate.DoesNotExist:
            return Response(
                {'error': 'Certificate not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=['post'])
    def download(self, request, pk=None):
        """Record download and return PDF URL."""
        try:
            certificate = CertificateService.get_certificate(
                certificate_id=pk,
                user_id=str(request.user.id)
            )
            certificate.record_download()

            return Response({
                'pdf_url': certificate.pdf_url,
                'certificate_number': certificate.certificate_number
            })
        except Certificate.DoesNotExist:
            return Response(
                {'error': 'Certificate not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['get'], url_path='my-certificates')
    def my_certificates(self, request):
        """Get current user's certificates."""
        organization_id = request.headers.get('X-Organization-ID')

        certificates = CertificateService.get_user_certificates(
            user_id=str(request.user.id),
            organization_id=organization_id
        )

        return Response(certificates)

    @action(detail=False, methods=['get'])
    def expiring(self, request):
        """Get certificates expiring soon (admin)."""
        organization_id = request.headers.get('X-Organization-ID')
        days = int(request.query_params.get('days', 30))

        certificates = CertificateService.check_expiring_certificates(
            organization_id=organization_id,
            days_before=days
        )

        return Response(CertificateListSerializer(certificates, many=True).data)
