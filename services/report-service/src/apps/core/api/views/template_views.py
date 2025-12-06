"""
Report Template Views.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Count

from ...services import ReportTemplateService
from ..serializers import (
    ReportTemplateSerializer,
    ReportTemplateCreateSerializer,
    ReportTemplateUpdateSerializer,
    ReportTemplateListSerializer,
)


class ReportTemplateViewSet(viewsets.ViewSet):
    """ViewSet for managing report templates."""
    permission_classes = [IsAuthenticated]

    def list(self, request):
        """List report templates."""
        organization_id = request.headers.get('X-Organization-ID')
        report_type = request.query_params.get('report_type')
        is_public = request.query_params.get('is_public')

        if is_public is not None:
            is_public = is_public.lower() == 'true'

        templates = ReportTemplateService.get_list(
            organization_id=organization_id,
            report_type=report_type,
            is_public=is_public,
        ).annotate(report_count=Count('reports'))

        serializer = ReportTemplateListSerializer(templates, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        """Get a specific template."""
        organization_id = request.headers.get('X-Organization-ID')
        template = ReportTemplateService.get_by_id(pk, organization_id)
        serializer = ReportTemplateSerializer(template)
        return Response(serializer.data)

    def create(self, request):
        """Create a new template."""
        serializer = ReportTemplateCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        organization_id = request.headers.get('X-Organization-ID')
        user_id = request.user.id

        template = ReportTemplateService.create(
            organization_id=organization_id,
            created_by_id=user_id,
            **serializer.validated_data
        )

        return Response(
            ReportTemplateSerializer(template).data,
            status=status.HTTP_201_CREATED
        )

    def update(self, request, pk=None):
        """Update a template."""
        serializer = ReportTemplateUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        organization_id = request.headers.get('X-Organization-ID')
        user_id = request.user.id

        template = ReportTemplateService.update(
            template_id=pk,
            organization_id=organization_id,
            user_id=user_id,
            **serializer.validated_data
        )

        return Response(ReportTemplateSerializer(template).data)

    def destroy(self, request, pk=None):
        """Delete a template."""
        organization_id = request.headers.get('X-Organization-ID')
        user_id = request.user.id

        ReportTemplateService.delete(pk, organization_id, user_id)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'])
    def clone(self, request, pk=None):
        """Clone a template."""
        organization_id = request.headers.get('X-Organization-ID')
        user_id = request.user.id
        new_name = request.data.get('name', 'Cloned Template')

        template = ReportTemplateService.clone(
            template_id=pk,
            organization_id=organization_id,
            user_id=user_id,
            new_name=new_name
        )

        return Response(
            ReportTemplateSerializer(template).data,
            status=status.HTTP_201_CREATED
        )
