# services/certificate-service/src/apps/core/api/views/language_proficiency_views.py
"""
Language Proficiency API Views
"""

from uuid import UUID
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from ...models import LanguageProficiency, LanguageTestHistory
from ...services import LanguageProficiencyService
from ..serializers import (
    LanguageProficiencySerializer,
    LanguageProficiencyCreateSerializer,
    LanguageTestHistorySerializer,
    LanguageProficiencyVerifySerializer,
)


class LanguageProficiencyViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Language Proficiency management.

    Endpoints:
    - GET /api/v1/language-proficiency/ - List proficiencies
    - POST /api/v1/language-proficiency/ - Record test result
    - GET /api/v1/language-proficiency/{id}/ - Get proficiency
    - POST /api/v1/language-proficiency/{id}/verify/ - Verify proficiency
    - GET /api/v1/language-proficiency/check-validity/ - Check validity
    - GET /api/v1/language-proficiency/expiring/ - Get expiring
    - GET /api/v1/language-proficiency/test-history/ - Get test history
    """

    queryset = LanguageProficiency.objects.all()
    serializer_class = LanguageProficiencySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter by organization."""
        queryset = super().get_queryset()
        org_id = self.request.headers.get('X-Organization-ID')
        if org_id:
            queryset = queryset.filter(organization_id=org_id)

        user_id = self.request.query_params.get('user_id')
        if user_id:
            queryset = queryset.filter(user_id=user_id)

        language = self.request.query_params.get('language')
        if language:
            queryset = queryset.filter(language=language)

        return queryset.order_by('-test_date')

    def create(self, request, *args, **kwargs):
        """Record a language proficiency test result."""
        serializer = LanguageProficiencyCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        org_id = UUID(request.headers.get('X-Organization-ID'))
        user_id = UUID(request.data.get('user_id'))

        result = LanguageProficiencyService.record_test_result(
            organization_id=org_id,
            user_id=user_id,
            **serializer.validated_data
        )

        return Response(result, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def verify(self, request, pk=None):
        """Verify a language proficiency record."""
        serializer = LanguageProficiencyVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = LanguageProficiencyService.verify_proficiency(
            proficiency_id=UUID(pk),
            verified_by=request.user.id,
            notes=serializer.validated_data.get('notes')
        )

        return Response(result)

    @action(detail=False, methods=['get'])
    def check_validity(self, request):
        """Check language proficiency validity for a user."""
        org_id = UUID(request.headers.get('X-Organization-ID'))
        user_id = UUID(request.query_params.get('user_id'))
        language = request.query_params.get('language', 'en')
        min_level = int(request.query_params.get('min_level', 4))

        result = LanguageProficiencyService.check_proficiency_validity(
            organization_id=org_id,
            user_id=user_id,
            language=language,
            min_level=min_level
        )

        return Response(result)

    @action(detail=False, methods=['get'])
    def expiring(self, request):
        """Get expiring language proficiencies."""
        org_id = request.headers.get('X-Organization-ID')
        days = int(request.query_params.get('days', 180))

        result = LanguageProficiencyService.get_expiring_proficiencies(
            organization_id=UUID(org_id) if org_id else None,
            days_ahead=days
        )

        return Response(result)

    @action(detail=False, methods=['get'])
    def test_history(self, request):
        """Get language test history for a user."""
        org_id = UUID(request.headers.get('X-Organization-ID'))
        user_id = UUID(request.query_params.get('user_id'))
        language = request.query_params.get('language')
        limit = int(request.query_params.get('limit', 10))

        result = LanguageProficiencyService.get_test_history(
            organization_id=org_id,
            user_id=user_id,
            language=language,
            limit=limit
        )

        return Response(result)

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get language proficiency statistics for organization."""
        org_id = UUID(request.headers.get('X-Organization-ID'))

        result = LanguageProficiencyService.get_organization_statistics(
            organization_id=org_id
        )

        return Response(result)

    @action(detail=False, methods=['get'])
    def english(self, request):
        """Get English language proficiency for a user."""
        org_id = UUID(request.headers.get('X-Organization-ID'))
        user_id = UUID(request.query_params.get('user_id'))

        result = LanguageProficiencyService.get_english_proficiency(
            organization_id=org_id,
            user_id=user_id
        )

        if result:
            return Response(result)
        return Response(
            {'error': 'No valid English proficiency found'},
            status=status.HTTP_404_NOT_FOUND
        )
