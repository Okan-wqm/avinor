# services/aircraft-service/src/apps/api/views/document_views.py
"""
Document Views

ViewSet for aircraft document management.
"""

import logging

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters import rest_framework as filters

from apps.core.models import Aircraft, AircraftDocument
from apps.core.services import DocumentService, DocumentError, AircraftNotFoundError
from apps.api.serializers import (
    DocumentListSerializer,
    DocumentDetailSerializer,
    DocumentCreateSerializer,
    DocumentUpdateSerializer,
    DocumentComplianceSerializer,
)

logger = logging.getLogger(__name__)


class DocumentFilter(filters.FilterSet):
    """Filter for documents."""

    document_type = filters.ChoiceFilter(choices=AircraftDocument.DocumentType.choices)
    file_type = filters.ChoiceFilter(choices=AircraftDocument.FileType.choices)
    is_current = filters.BooleanFilter()
    is_required = filters.BooleanFilter()
    is_public = filters.BooleanFilter()
    is_expired = filters.BooleanFilter(method='filter_is_expired')
    expiring_within = filters.NumberFilter(method='filter_expiring_within')

    class Meta:
        model = AircraftDocument
        fields = [
            'document_type', 'file_type', 'is_current', 'is_required', 'is_public',
        ]

    def filter_is_expired(self, queryset, name, value):
        from datetime import date
        if value:
            return queryset.filter(
                expiry_date__isnull=False,
                expiry_date__lt=date.today()
            )
        return queryset.filter(
            models.Q(expiry_date__isnull=True) |
            models.Q(expiry_date__gte=date.today())
        )

    def filter_expiring_within(self, queryset, name, value):
        from datetime import date, timedelta
        future_date = date.today() + timedelta(days=value)
        return queryset.filter(
            expiry_date__isnull=False,
            expiry_date__gte=date.today(),
            expiry_date__lte=future_date
        )


class DocumentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for document management.

    Nested under aircraft: /aircraft/{aircraft_id}/documents/

    Custom actions:
    - compliance: Check document compliance
    - expiring: Get expiring documents
    - expired: Get expired documents
    - history: Get version history
    """

    permission_classes = [IsAuthenticated]
    filterset_class = DocumentFilter
    search_fields = ['title', 'document_number', 'issuing_authority']
    ordering_fields = ['document_type', 'expiry_date', 'created_at']
    ordering = ['document_type', '-created_at']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.document_service = DocumentService()

    def get_queryset(self):
        """Get documents for the aircraft."""
        aircraft_pk = self.kwargs.get('aircraft_pk')
        if not aircraft_pk:
            return AircraftDocument.objects.none()

        return AircraftDocument.objects.filter(
            aircraft_id=aircraft_pk
        ).select_related('aircraft')

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return DocumentListSerializer
        elif self.action == 'create':
            return DocumentCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return DocumentUpdateSerializer
        return DocumentDetailSerializer

    def perform_create(self, serializer):
        """Create document with context."""
        organization_id = self.request.headers.get('X-Organization-ID')
        user_id = self.request.headers.get('X-User-ID')
        aircraft_pk = self.kwargs.get('aircraft_pk')

        try:
            document = self.document_service.add_document(
                aircraft_id=aircraft_pk,
                organization_id=organization_id,
                created_by=user_id,
                **serializer.validated_data
            )
            serializer.instance = document
        except AircraftNotFoundError:
            raise serializers.ValidationError({'aircraft_id': 'Aircraft not found'})
        except DocumentError as e:
            raise serializers.ValidationError(str(e))

    def perform_update(self, serializer):
        """Update document."""
        user_id = self.request.headers.get('X-User-ID')

        try:
            document = self.document_service.update_document(
                document_id=serializer.instance.id,
                updated_by=user_id,
                **serializer.validated_data
            )
            serializer.instance = document
        except DocumentError as e:
            raise serializers.ValidationError(str(e))

    def perform_destroy(self, instance):
        """Delete document."""
        try:
            self.document_service.delete_document(instance.id)
        except DocumentError:
            pass

    # ==========================================================================
    # Compliance Actions
    # ==========================================================================

    @action(detail=False, methods=['get'])
    def compliance(self, request, aircraft_pk=None):
        """Check document compliance for the aircraft."""
        try:
            compliance = self.document_service.check_compliance(aircraft_pk)
            serializer = DocumentComplianceSerializer(compliance)
            return Response(serializer.data)
        except AircraftNotFoundError:
            return Response(
                {'error': 'Aircraft not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['get'])
    def expiring(self, request, aircraft_pk=None):
        """Get documents expiring soon."""
        days = int(request.query_params.get('days', 30))

        documents = self.document_service.get_expiring_documents(
            aircraft_id=aircraft_pk,
            days_ahead=days
        )

        return Response(documents)

    @action(detail=False, methods=['get'])
    def expired(self, request, aircraft_pk=None):
        """Get expired documents."""
        documents = self.document_service.get_expired_documents(
            aircraft_id=aircraft_pk
        )

        return Response(documents)

    @action(detail=False, methods=['get'], url_path='history/(?P<document_type>[^/.]+)')
    def history(self, request, aircraft_pk=None, document_type=None):
        """Get version history for a document type."""
        history = self.document_service.get_document_history(
            aircraft_id=aircraft_pk,
            document_type=document_type
        )

        return Response(history)


class OrganizationDocumentViewSet(viewsets.ViewSet):
    """
    ViewSet for organization-wide document queries.

    Non-nested: /documents/
    """

    permission_classes = [IsAuthenticated]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.document_service = DocumentService()

    @action(detail=False, methods=['get'])
    def expiring(self, request):
        """Get all expiring documents in the organization."""
        organization_id = request.headers.get('X-Organization-ID')
        days = int(request.query_params.get('days', 30))

        documents = self.document_service.get_expiring_documents(
            organization_id=organization_id,
            days_ahead=days
        )

        return Response(documents)

    @action(detail=False, methods=['get'])
    def expired(self, request):
        """Get all expired documents in the organization."""
        organization_id = request.headers.get('X-Organization-ID')

        documents = self.document_service.get_expired_documents(
            organization_id=organization_id
        )

        return Response(documents)

    @action(detail=False, methods=['get'])
    def compliance_summary(self, request):
        """Get compliance summary for the organization."""
        organization_id = request.headers.get('X-Organization-ID')

        summary = self.document_service.get_compliance_summary(
            organization_id=organization_id
        )

        return Response(summary)

    @action(detail=False, methods=['get'])
    def reminders(self, request):
        """Get documents needing reminders."""
        organization_id = request.headers.get('X-Organization-ID')

        result = self.document_service.check_all_reminders(
            organization_id=organization_id
        )

        return Response(result)

    @action(detail=False, methods=['post'], url_path='reminders/(?P<document_id>[^/.]+)/mark-sent')
    def mark_reminder_sent(self, request, document_id=None):
        """Mark a document reminder as sent."""
        try:
            self.document_service.mark_reminder_sent(document_id)
            return Response({'status': 'success'})
        except DocumentError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
