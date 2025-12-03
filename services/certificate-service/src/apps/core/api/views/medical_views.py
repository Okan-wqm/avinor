# services/certificate-service/src/apps/core/api/views/medical_views.py
"""
Medical Certificate ViewSet

API endpoints for medical certificate management.
"""

import logging
from uuid import UUID

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from ...models import MedicalCertificate, MedicalStatus
from ...services import MedicalService
from ..serializers import (
    MedicalCertificateSerializer,
    MedicalCertificateCreateSerializer,
    MedicalCertificateListSerializer,
    MedicalValidityCheckSerializer,
    MedicalValidityResponseSerializer,
)

logger = logging.getLogger(__name__)


class MedicalCertificateViewSet(viewsets.ModelViewSet):
    """
    ViewSet for medical certificate management.

    Provides CRUD operations and specialized actions for:
    - Class 1, 2, 3 medical certificates
    - LAPL medical certificates
    - Validity tracking based on pilot age

    Endpoints:
    - GET /medicals/ - List medical certificates
    - POST /medicals/ - Create medical certificate
    - GET /medicals/{id}/ - Retrieve medical certificate
    - PUT /medicals/{id}/ - Update medical certificate
    - DELETE /medicals/{id}/ - Delete medical certificate
    - GET /medicals/user/{user_id}/ - Get user's medical
    - GET /medicals/user/{user_id}/history/ - Get medical history
    - POST /medicals/check-validity/ - Check medical validity
    - GET /medicals/expiring/ - Get expiring medicals
    - GET /medicals/statistics/ - Get statistics
    """

    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = [
        'user_id',
        'medical_class',
        'status',
        'issuing_authority',
        'issuing_country',
    ]
    search_fields = [
        'certificate_number',
        'ame_name',
        'ame_license_number',
        'notes',
    ]
    ordering_fields = [
        'examination_date',
        'issue_date',
        'expiry_date',
        'medical_class',
        'created_at',
    ]
    ordering = ['-created_at']

    def get_queryset(self):
        """Filter by organization."""
        organization_id = self.request.headers.get('X-Organization-ID')
        queryset = MedicalCertificate.objects.all()

        if organization_id:
            queryset = queryset.filter(organization_id=organization_id)

        return queryset

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'create':
            return MedicalCertificateCreateSerializer
        elif self.action == 'list':
            return MedicalCertificateListSerializer
        elif self.action == 'check_validity':
            return MedicalValidityCheckSerializer
        return MedicalCertificateSerializer

    def perform_create(self, serializer):
        """Create medical certificate with organization context."""
        organization_id = self.request.headers.get('X-Organization-ID')

        service = MedicalService()
        medical = service.create_medical(
            organization_id=UUID(organization_id) if organization_id else None,
            **serializer.validated_data
        )

        serializer.instance = medical

    def perform_destroy(self, instance):
        """Soft delete medical certificate."""
        instance.status = MedicalStatus.EXPIRED
        instance.save(update_fields=['status', 'updated_at'])
        logger.info(f"Medical certificate {instance.id} archived")

    @action(detail=False, methods=['get'], url_path='user/(?P<user_id>[^/.]+)')
    def user_medical(self, request, user_id=None):
        """
        Get current valid medical for a user.

        GET /medicals/user/{user_id}/
        """
        service = MedicalService()
        medical = service.get_current_medical(user_id=UUID(user_id))

        if medical:
            serializer = MedicalCertificateSerializer(medical)
            return Response(serializer.data)
        else:
            return Response(
                {'detail': 'No valid medical certificate found'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['get'], url_path='user/(?P<user_id>[^/.]+)/history')
    def user_medical_history(self, request, user_id=None):
        """
        Get medical certificate history for a user.

        GET /medicals/user/{user_id}/history/
        """
        service = MedicalService()
        medicals = service.get_medical_history(user_id=UUID(user_id))

        serializer = MedicalCertificateListSerializer(medicals, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'], url_path='check-validity')
    def check_validity(self, request):
        """
        Check medical validity for a user.

        POST /medicals/check-validity/
        {
            "user_id": "uuid",
            "required_class": "class_1" (optional)
        }
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = MedicalService()
        result = service.check_medical_validity(
            user_id=serializer.validated_data['user_id'],
            required_class=serializer.validated_data.get('required_class')
        )

        response_serializer = MedicalValidityResponseSerializer(data=result)
        response_serializer.is_valid(raise_exception=True)

        return Response(response_serializer.data)

    @action(detail=False, methods=['get'])
    def expiring(self, request):
        """
        Get medical certificates expiring soon.

        GET /medicals/expiring/?days=30
        """
        organization_id = request.headers.get('X-Organization-ID')
        days = int(request.query_params.get('days', 30))

        service = MedicalService()
        expiring = service.get_expiring_medicals(
            organization_id=UUID(organization_id) if organization_id else None,
            days_ahead=days
        )

        serializer = MedicalCertificateListSerializer(expiring, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """
        Get medical certificate statistics for organization.

        GET /medicals/statistics/
        """
        organization_id = request.headers.get('X-Organization-ID')

        service = MedicalService()
        stats = service.get_medical_statistics(
            organization_id=UUID(organization_id) if organization_id else None
        )

        return Response(stats)

    @action(detail=True, methods=['post'])
    def renew(self, request, pk=None):
        """
        Renew a medical certificate with new examination.

        POST /medicals/{id}/renew/
        """
        current_medical = self.get_object()

        service = MedicalService()
        new_medical = service.renew_medical(
            current_medical_id=current_medical.id,
            new_data=request.data
        )

        serializer = MedicalCertificateSerializer(new_medical)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def suspend(self, request, pk=None):
        """
        Suspend a medical certificate.

        POST /medicals/{id}/suspend/
        """
        medical = self.get_object()
        reason = request.data.get('reason', '')

        service = MedicalService()
        suspended_medical = service.suspend_medical(
            medical_id=medical.id,
            reason=reason
        )

        serializer = MedicalCertificateSerializer(suspended_medical)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='privileges/(?P<user_id>[^/.]+)')
    def user_privileges(self, request, user_id=None):
        """
        Get medical-based privileges for a user.

        GET /medicals/privileges/{user_id}/
        """
        service = MedicalService()
        medical = service.get_current_medical(user_id=UUID(user_id))

        if not medical:
            return Response({
                'user_id': user_id,
                'has_valid_medical': False,
                'privileges': [],
                'message': 'No valid medical certificate found'
            })

        return Response({
            'user_id': user_id,
            'has_valid_medical': medical.is_valid,
            'medical_class': medical.medical_class,
            'expiry_date': medical.expiry_date,
            'days_until_expiry': medical.days_until_expiry,
            'privileges': medical.get_applicable_privileges(),
            'limitations': medical.limitations or [],
            'limitation_codes': medical.limitation_codes or []
        })
