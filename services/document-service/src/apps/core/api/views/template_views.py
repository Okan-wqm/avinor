# services/document-service/src/apps/core/api/views/template_views.py
"""
Template Views
"""

import logging

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from django.http import HttpResponse
from django.db.models import Q

from ...models import DocumentTemplate
from ...services import TemplateService, PDFService
from ..serializers import (
    TemplateSerializer,
    TemplateListSerializer,
    TemplateDetailSerializer,
    TemplateCreateSerializer,
    TemplateGenerateSerializer,
)
from ..serializers.template_serializers import (
    TemplateUpdateSerializer,
    TemplatePreviewSerializer,
    TemplateCloneSerializer,
)


logger = logging.getLogger(__name__)


class TemplateViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Document Templates.

    Endpoints:
    - GET /templates/ - List templates
    - POST /templates/ - Create template
    - GET /templates/{id}/ - Get template details
    - PATCH /templates/{id}/ - Update template
    - DELETE /templates/{id}/ - Delete template
    - POST /templates/{id}/generate/ - Generate document from template
    - POST /templates/{id}/preview/ - Preview template
    - POST /templates/{id}/clone/ - Clone template
    """

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter templates by organization and system templates."""
        organization_id = self.request.headers.get('X-Organization-ID')

        if not organization_id:
            return DocumentTemplate.objects.none()

        # Include org templates and system templates
        queryset = DocumentTemplate.objects.filter(
            Q(organization_id=organization_id) | Q(is_system=True),
            is_active=True,
        )

        # Filter by type
        template_type = self.request.query_params.get('type')
        if template_type:
            queryset = queryset.filter(template_type=template_type)

        # Filter by category
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category=category)

        return queryset.order_by('-is_system', 'name')

    def get_serializer_class(self):
        """Return appropriate serializer."""
        if self.action == 'list':
            return TemplateListSerializer
        elif self.action == 'retrieve':
            return TemplateDetailSerializer
        elif self.action == 'create':
            return TemplateCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return TemplateUpdateSerializer
        return TemplateSerializer

    def get_serializer_context(self):
        """Add organization to context."""
        context = super().get_serializer_context()
        context['organization_id'] = self.request.headers.get('X-Organization-ID')
        return context

    def create(self, request, *args, **kwargs):
        """Create a new template."""
        serializer = TemplateCreateSerializer(
            data=request.data,
            context=self.get_serializer_context()
        )
        serializer.is_valid(raise_exception=True)

        organization_id = request.headers.get('X-Organization-ID')
        user_id = request.headers.get('X-User-ID')

        try:
            service = TemplateService()
            template = service.create_template(
                organization_id=organization_id,
                created_by=user_id,
                **serializer.validated_data
            )

            return Response(
                TemplateDetailSerializer(template).data,
                status=status.HTTP_201_CREATED
            )

        except Exception as e:
            logger.error(f"Template creation failed: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def destroy(self, request, *args, **kwargs):
        """Soft delete template."""
        template = self.get_object()

        if template.is_system:
            return Response(
                {'error': 'Cannot delete system templates'},
                status=status.HTTP_400_BAD_REQUEST
            )

        template.is_active = False
        template.save(update_fields=['is_active'])

        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'])
    def generate(self, request, pk=None):
        """Generate document from template."""
        template = self.get_object()

        serializer = TemplateGenerateSerializer(
            data={**request.data, 'template_id': pk},
            context=self.get_serializer_context()
        )
        serializer.is_valid(raise_exception=True)

        organization_id = request.headers.get('X-Organization-ID')
        user_id = request.headers.get('X-User-ID')

        try:
            service = TemplateService()
            data = serializer.validated_data

            result = service.generate_document(
                template_id=str(template.id),
                variables=data['variables'],
                organization_id=organization_id,
                user_id=user_id,
            )

            # If save_as_document, return document info
            if data.get('save_as_document'):
                from ...services import DocumentService
                doc_service = DocumentService()

                filename = data.get('output_filename', template.name)
                if not filename.endswith('.pdf'):
                    filename += '.pdf'

                document = doc_service.upload_document(
                    organization_id=organization_id,
                    owner_id=user_id,
                    file_content=result,
                    filename=filename,
                    document_type=data.get('document_type', template.template_type),
                    folder_id=data.get('folder_id'),
                    title=filename.rsplit('.', 1)[0],
                    uploaded_by=user_id,
                    metadata={'generated_from_template': str(template.id)},
                )

                from ..serializers import DocumentDetailSerializer
                return Response(
                    DocumentDetailSerializer(document).data,
                    status=status.HTTP_201_CREATED
                )

            # Return PDF content
            filename = data.get('output_filename', template.name)
            if not filename.endswith('.pdf'):
                filename += '.pdf'

            response = HttpResponse(
                result,
                content_type='application/pdf'
            )
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            response['Content-Length'] = len(result)

            # Update usage count
            template.usage_count += 1
            template.save(update_fields=['usage_count'])

            return response

        except Exception as e:
            logger.error(f"Document generation failed: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def preview(self, request, pk=None):
        """Preview template with sample data."""
        template = self.get_object()

        serializer = TemplatePreviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            pdf_service = PDFService()
            data = serializer.validated_data

            # Use provided content or template content
            content = data.get('content') or template.content
            css = data.get('css_styles') or template.css_styles
            variables = data.get('variables', {})

            # Render template with variables
            from jinja2 import Template
            rendered = Template(content).render(**variables)

            # Generate PDF
            pdf_content = pdf_service.generate_pdf_from_html(
                html_content=rendered,
                css_content=css,
            )

            response = HttpResponse(
                pdf_content,
                content_type='application/pdf'
            )
            response['Content-Disposition'] = 'inline; filename="preview.pdf"'

            return response

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def clone(self, request, pk=None):
        """Clone a template."""
        template = self.get_object()

        serializer = TemplateCloneSerializer(
            data=request.data,
            context=self.get_serializer_context()
        )
        serializer.is_valid(raise_exception=True)

        organization_id = request.headers.get('X-Organization-ID')
        user_id = request.headers.get('X-User-ID')

        try:
            # Create clone
            clone = DocumentTemplate.objects.create(
                organization_id=organization_id,
                name=serializer.validated_data['name'],
                description=serializer.validated_data.get(
                    'description',
                    template.description
                ),
                template_type=template.template_type,
                output_format=template.output_format,
                content=template.content,
                header_content=template.header_content,
                footer_content=template.footer_content,
                css_styles=template.css_styles,
                category=template.category,
                tags=template.tags,
                variable_definitions=template.variable_definitions,
                page_size=template.page_size,
                page_orientation=template.page_orientation,
                margin_top=template.margin_top,
                margin_bottom=template.margin_bottom,
                margin_left=template.margin_left,
                margin_right=template.margin_right,
                signature_fields=template.signature_fields,
                created_by=user_id,
                is_system=False,
            )

            return Response(
                TemplateDetailSerializer(clone).data,
                status=status.HTTP_201_CREATED
            )

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'])
    def variables(self, request, pk=None):
        """Get template variable definitions."""
        template = self.get_object()

        return Response({
            'variables': template.variable_definitions,
            'signature_fields': template.signature_fields,
        })

    @action(detail=False, methods=['get'])
    def categories(self, request):
        """Get available template categories."""
        organization_id = request.headers.get('X-Organization-ID')

        categories = DocumentTemplate.objects.filter(
            Q(organization_id=organization_id) | Q(is_system=True),
            is_active=True,
            category__isnull=False,
        ).values_list('category', flat=True).distinct()

        return Response(list(categories))
