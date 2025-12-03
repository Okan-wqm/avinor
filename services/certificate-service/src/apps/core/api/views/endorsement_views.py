# services/certificate-service/src/apps/core/api/views/endorsement_views.py
"""
Endorsement ViewSet

API endpoints for endorsement management.
"""

import logging
from uuid import UUID

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from ...models import Endorsement, EndorsementStatus
from ...services import EndorsementService
from ..serializers import (
    EndorsementSerializer,
    EndorsementCreateSerializer,
    EndorsementListSerializer,
    EndorsementSignSerializer,
    SoloEndorsementCreateSerializer,
    SoloAuthorizationCheckSerializer,
    SoloAuthorizationResponseSerializer,
)

logger = logging.getLogger(__name__)


class EndorsementViewSet(viewsets.ModelViewSet):
    """
    ViewSet for endorsement management.

    Provides CRUD operations and specialized actions for:
    - Solo endorsements
    - Cross-country endorsements
    - Pre-solo ground training
    - Aircraft type endorsements
    - Knowledge test sign-offs

    Endpoints:
    - GET /endorsements/ - List endorsements
    - POST /endorsements/ - Create endorsement
    - GET /endorsements/{id}/ - Retrieve endorsement
    - PUT /endorsements/{id}/ - Update endorsement
    - DELETE /endorsements/{id}/ - Delete endorsement
    - POST /endorsements/{id}/sign/ - Sign endorsement
    - GET /endorsements/student/{student_id}/ - Get student endorsements
    - GET /endorsements/instructor/{instructor_id}/ - Get instructor's given endorsements
    - POST /endorsements/solo/ - Create solo endorsement
    - POST /endorsements/check-solo/ - Check solo authorization
    """

    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = [
        'student_id',
        'instructor_id',
        'endorsement_type',
        'status',
        'aircraft_type',
        'is_permanent',
    ]
    search_fields = [
        'endorsement_code',
        'description',
        'student_name',
        'instructor_name',
        'notes',
    ]
    ordering_fields = [
        'issue_date',
        'expiry_date',
        'endorsement_type',
        'created_at',
    ]
    ordering = ['-created_at']

    def get_queryset(self):
        """Filter by organization."""
        organization_id = self.request.headers.get('X-Organization-ID')
        queryset = Endorsement.objects.all()

        if organization_id:
            queryset = queryset.filter(organization_id=organization_id)

        return queryset

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'create':
            return EndorsementCreateSerializer
        elif self.action == 'list':
            return EndorsementListSerializer
        elif self.action == 'sign':
            return EndorsementSignSerializer
        elif self.action == 'create_solo':
            return SoloEndorsementCreateSerializer
        elif self.action == 'check_solo':
            return SoloAuthorizationCheckSerializer
        return EndorsementSerializer

    def perform_create(self, serializer):
        """Create endorsement with organization context."""
        organization_id = self.request.headers.get('X-Organization-ID')

        service = EndorsementService()
        endorsement = service.create_endorsement(
            organization_id=UUID(organization_id) if organization_id else None,
            **serializer.validated_data
        )

        serializer.instance = endorsement

    def perform_destroy(self, instance):
        """Soft delete endorsement."""
        if instance.is_signed:
            # Cannot delete signed endorsements
            raise ValueError("Cannot delete signed endorsements")

        instance.status = EndorsementStatus.CANCELLED
        instance.save(update_fields=['status', 'updated_at'])
        logger.info(f"Endorsement {instance.id} cancelled")

    @action(detail=True, methods=['post'])
    def sign(self, request, pk=None):
        """
        Sign an endorsement.

        POST /endorsements/{id}/sign/
        """
        endorsement = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Verify instructor is signing their own endorsement
        instructor_id = request.user.id
        if str(endorsement.instructor_id) != str(instructor_id):
            return Response(
                {'detail': 'Only the issuing instructor can sign this endorsement'},
                status=status.HTTP_403_FORBIDDEN
            )

        service = EndorsementService()
        signed_endorsement = service.sign_endorsement(
            endorsement_id=endorsement.id,
            instructor_id=instructor_id,
            signature_data=serializer.validated_data['signature_data']
        )

        return Response(
            EndorsementSerializer(signed_endorsement).data,
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['post'])
    def revoke(self, request, pk=None):
        """
        Revoke an endorsement.

        POST /endorsements/{id}/revoke/
        """
        endorsement = self.get_object()
        reason = request.data.get('reason', '')

        service = EndorsementService()
        revoked_endorsement = service.revoke_endorsement(
            endorsement_id=endorsement.id,
            reason=reason,
            revoked_by=request.user.id
        )

        return Response(
            EndorsementSerializer(revoked_endorsement).data,
            status=status.HTTP_200_OK
        )

    @action(detail=False, methods=['get'], url_path='student/(?P<student_id>[^/.]+)')
    def student_endorsements(self, request, student_id=None):
        """
        Get all endorsements for a student.

        GET /endorsements/student/{student_id}/
        """
        include_expired = request.query_params.get('include_expired', 'false').lower() == 'true'
        endorsement_type = request.query_params.get('type')

        service = EndorsementService()
        endorsements = service.get_student_endorsements(
            student_id=UUID(student_id),
            include_expired=include_expired,
            endorsement_type=endorsement_type
        )

        serializer = EndorsementListSerializer(endorsements, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='instructor/(?P<instructor_id>[^/.]+)')
    def instructor_endorsements(self, request, instructor_id=None):
        """
        Get all endorsements given by an instructor.

        GET /endorsements/instructor/{instructor_id}/
        """
        include_expired = request.query_params.get('include_expired', 'false').lower() == 'true'

        service = EndorsementService()
        endorsements = service.get_instructor_endorsements(
            instructor_id=UUID(instructor_id),
            include_expired=include_expired
        )

        serializer = EndorsementListSerializer(endorsements, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def solo(self, request):
        """
        Create a solo endorsement.

        POST /endorsements/solo/
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        organization_id = request.headers.get('X-Organization-ID')

        service = EndorsementService()
        endorsement = service.create_solo_endorsement(
            organization_id=UUID(organization_id) if organization_id else None,
            **serializer.validated_data
        )

        return Response(
            EndorsementSerializer(endorsement).data,
            status=status.HTTP_201_CREATED
        )

    @action(detail=False, methods=['post'], url_path='check-solo')
    def check_solo(self, request):
        """
        Check if a student has valid solo authorization.

        POST /endorsements/check-solo/
        {
            "student_id": "uuid",
            "aircraft_type": "C172" (optional)
        }
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = EndorsementService()
        result = service.check_solo_authorization(
            student_id=serializer.validated_data['student_id'],
            aircraft_type=serializer.validated_data.get('aircraft_type')
        )

        response_serializer = SoloAuthorizationResponseSerializer(data=result)
        response_serializer.is_valid(raise_exception=True)

        return Response(response_serializer.data)

    @action(detail=False, methods=['get'])
    def expiring(self, request):
        """
        Get endorsements expiring soon.

        GET /endorsements/expiring/?days=30
        """
        organization_id = request.headers.get('X-Organization-ID')
        days = int(request.query_params.get('days', 30))

        service = EndorsementService()
        expiring = service.get_expiring_endorsements(
            organization_id=UUID(organization_id) if organization_id else None,
            days_ahead=days
        )

        serializer = EndorsementListSerializer(expiring, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def pending(self, request):
        """
        Get pending (unsigned) endorsements.

        GET /endorsements/pending/
        """
        organization_id = request.headers.get('X-Organization-ID')
        instructor_id = request.query_params.get('instructor_id')

        queryset = self.get_queryset().filter(status=EndorsementStatus.PENDING)

        if instructor_id:
            queryset = queryset.filter(instructor_id=instructor_id)

        serializer = EndorsementListSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """
        Get endorsement statistics for organization.

        GET /endorsements/statistics/
        """
        organization_id = request.headers.get('X-Organization-ID')

        service = EndorsementService()
        stats = service.get_endorsement_statistics(
            organization_id=UUID(organization_id) if organization_id else None
        )

        return Response(stats)

    @action(detail=False, methods=['get'], url_path='types')
    def endorsement_types(self, request):
        """
        Get available endorsement types.

        GET /endorsements/types/
        """
        from ...models import EndorsementType

        types = [
            {
                'value': choice[0],
                'label': choice[1]
            }
            for choice in EndorsementType.choices
        ]

        return Response(types)

    @action(detail=False, methods=['get'], url_path='templates')
    def endorsement_templates(self, request):
        """
        Get endorsement templates for common endorsements.

        GET /endorsements/templates/
        """
        from ...models import EndorsementType

        templates = {
            EndorsementType.SOLO: {
                'code': '61.87(n)',
                'description': 'Solo flight endorsement',
                'endorsement_text': (
                    'I certify that [Student Name] has received the training '
                    'required by 14 CFR 61.87 and has demonstrated proficiency '
                    'in the make and model aircraft to be flown solo.'
                ),
                'validity_days': 90,
            },
            EndorsementType.SOLO_CROSS_COUNTRY: {
                'code': '61.93(c)(1)',
                'description': 'Solo cross-country flight endorsement',
                'endorsement_text': (
                    'I certify that [Student Name] has received solo cross-country '
                    'training required by 14 CFR 61.93 and is proficient to make '
                    'solo cross-country flights in a [Aircraft Type].'
                ),
                'validity_days': 90,
            },
            EndorsementType.KNOWLEDGE_TEST: {
                'code': '61.35(a)(1)',
                'description': 'Knowledge test endorsement',
                'endorsement_text': (
                    'I certify that [Student Name] has received the training '
                    'required by 14 CFR Part 61 and is prepared for the '
                    '[Certificate Type] knowledge test.'
                ),
                'is_permanent': True,
            },
            EndorsementType.PRACTICAL_TEST: {
                'code': '61.39(a)',
                'description': 'Practical test endorsement',
                'endorsement_text': (
                    'I certify that [Student Name] has received training '
                    'in preparation for the [Certificate Type] practical test '
                    'and is prepared for that test.'
                ),
                'is_permanent': True,
            },
        }

        return Response(templates)
