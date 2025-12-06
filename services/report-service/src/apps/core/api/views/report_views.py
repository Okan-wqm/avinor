"""
Report Views.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from ...services import ReportService
from ..serializers import ReportSerializer, ReportCreateSerializer, ReportListSerializer


class ReportViewSet(viewsets.ViewSet):
    """ViewSet for managing reports."""
    permission_classes = [IsAuthenticated]

    def list(self, request):
        """List reports."""
        organization_id = request.headers.get('X-Organization-ID')
        template_id = request.query_params.get('template_id')
        report_status = request.query_params.get('status')

        reports = ReportService.get_list(
            organization_id=organization_id,
            template_id=template_id,
            status=report_status,
        )

        serializer = ReportListSerializer(reports, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        """Get a specific report."""
        organization_id = request.headers.get('X-Organization-ID')
        report = ReportService.get_by_id(pk, organization_id)
        serializer = ReportSerializer(report)
        return Response(serializer.data)

    def create(self, request):
        """Generate a new report."""
        serializer = ReportCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        organization_id = request.headers.get('X-Organization-ID')
        user_id = request.user.id

        report = ReportService.generate(
            template_id=serializer.validated_data['template_id'],
            organization_id=organization_id,
            generated_by_id=user_id,
            parameters=serializer.validated_data.get('parameters', {}),
            title=serializer.validated_data.get('title'),
            description=serializer.validated_data.get('description', ''),
            output_format=serializer.validated_data.get('output_format', 'pdf'),
        )

        return Response(ReportSerializer(report).data, status=status.HTTP_201_CREATED)

    def destroy(self, request, pk=None):
        """Delete a report."""
        organization_id = request.headers.get('X-Organization-ID')
        ReportService.delete(pk, organization_id)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'])
    def regenerate(self, request, pk=None):
        """Regenerate a report."""
        organization_id = request.headers.get('X-Organization-ID')
        user_id = request.user.id

        report = ReportService.regenerate(pk, organization_id, user_id)
        return Response(ReportSerializer(report).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'])
    def cleanup(self, request):
        """Clean up expired reports."""
        count = ReportService.cleanup_expired()
        return Response({'deleted_count': count})
