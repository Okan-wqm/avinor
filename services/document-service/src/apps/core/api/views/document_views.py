# services/document-service/src/apps/core/api/views/document_views.py
"""
Document Views
"""

import logging

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.permissions import IsAuthenticated

from django.http import HttpResponse, StreamingHttpResponse
from django.shortcuts import get_object_or_404

from ...models import Document, DocumentStatus, DocumentFolder
from ...services import DocumentService, StorageService
from ...tasks import process_document
from ..serializers import (
    DocumentSerializer,
    DocumentListSerializer,
    DocumentDetailSerializer,
    DocumentUploadSerializer,
    DocumentUpdateSerializer,
    DocumentVersionSerializer,
    DocumentSearchSerializer,
)


logger = logging.getLogger(__name__)


class DocumentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Document CRUD operations.

    Endpoints:
    - GET /documents/ - List documents
    - POST /documents/ - Upload document
    - GET /documents/{id}/ - Get document details
    - PATCH /documents/{id}/ - Update document
    - DELETE /documents/{id}/ - Delete document
    - GET /documents/{id}/download/ - Download document
    - GET /documents/{id}/preview/ - Get preview URL
    - POST /documents/{id}/versions/ - Create new version
    - GET /documents/{id}/versions/ - List versions
    - POST /documents/search/ - Search documents
    - POST /documents/bulk-action/ - Bulk operations
    """

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_queryset(self):
        """Filter documents by organization."""
        organization_id = self.request.headers.get('X-Organization-ID')

        if not organization_id:
            return Document.objects.none()

        queryset = Document.objects.filter(
            organization_id=organization_id,
        ).exclude(
            status=DocumentStatus.DELETED
        ).select_related('folder')

        # Apply filters from query params
        folder_id = self.request.query_params.get('folder_id')
        if folder_id:
            queryset = queryset.filter(folder_id=folder_id)

        document_type = self.request.query_params.get('document_type')
        if document_type:
            queryset = queryset.filter(document_type=document_type)

        owner_id = self.request.query_params.get('owner_id')
        if owner_id:
            queryset = queryset.filter(owner_id=owner_id)

        # Only latest versions by default
        if self.request.query_params.get('all_versions') != 'true':
            queryset = queryset.filter(is_latest_version=True)

        return queryset.order_by('-created_at')

    def get_serializer_class(self):
        """Return appropriate serializer."""
        if self.action == 'list':
            return DocumentListSerializer
        elif self.action == 'retrieve':
            return DocumentDetailSerializer
        elif self.action == 'create':
            return DocumentUploadSerializer
        elif self.action in ['update', 'partial_update']:
            return DocumentUpdateSerializer
        return DocumentSerializer

    def create(self, request, *args, **kwargs):
        """Upload a new document."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        organization_id = request.headers.get('X-Organization-ID')
        user_id = request.headers.get('X-User-ID')

        if not organization_id or not user_id:
            return Response(
                {'error': 'Organization and user headers required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            service = DocumentService()
            file_obj = serializer.validated_data['file']

            document = service.upload_document(
                organization_id=organization_id,
                owner_id=user_id,
                file_content=file_obj.read(),
                filename=file_obj.name,
                document_type=serializer.validated_data['document_type'],
                folder_id=serializer.validated_data.get('folder_id'),
                title=serializer.validated_data.get('title'),
                description=serializer.validated_data.get('description'),
                access_level=serializer.validated_data.get('access_level'),
                expiry_date=serializer.validated_data.get('expiry_date'),
                related_entity_type=serializer.validated_data.get('related_entity_type'),
                related_entity_id=serializer.validated_data.get('related_entity_id'),
                tags=serializer.validated_data.get('tags', []),
                metadata=serializer.validated_data.get('metadata', {}),
                uploaded_by=user_id,
            )

            # Trigger async processing
            process_document.delay(str(document.id))

            return Response(
                DocumentDetailSerializer(document).data,
                status=status.HTTP_201_CREATED
            )

        except Exception as e:
            logger.error(f"Document upload failed: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def retrieve(self, request, *args, **kwargs):
        """Get document details and record view."""
        instance = self.get_object()
        user_id = request.headers.get('X-User-ID')

        # Record view
        if user_id:
            instance.record_view(user_id)

        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        """Soft delete document."""
        instance = self.get_object()
        user_id = request.headers.get('X-User-ID')

        instance.soft_delete(user_id)

        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """Download document file."""
        document = self.get_object()
        user_id = request.headers.get('X-User-ID')

        # Record download
        document.record_download(user_id)

        # Check if redirect to presigned URL
        if request.query_params.get('redirect') == 'true':
            service = DocumentService()
            url = service.get_download_url(str(document.id), user_id)
            return Response({'url': url})

        # Stream file content
        try:
            storage = StorageService()
            content = storage.download_file(document.file_path)

            response = HttpResponse(
                content,
                content_type=document.mime_type or 'application/octet-stream'
            )
            response['Content-Disposition'] = (
                f'attachment; filename="{document.original_name}"'
            )
            response['Content-Length'] = len(content)

            return response

        except Exception as e:
            logger.error(f"Document download failed: {e}")
            return Response(
                {'error': 'Download failed'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'])
    def preview(self, request, pk=None):
        """Get preview URL or content."""
        document = self.get_object()

        # Check if preview exists
        if not document.preview_path and not document.thumbnail_path:
            return Response(
                {'error': 'No preview available'},
                status=status.HTTP_404_NOT_FOUND
            )

        preview_type = request.query_params.get('type', 'preview')
        path = document.preview_path if preview_type == 'preview' else document.thumbnail_path

        if not path:
            path = document.thumbnail_path or document.preview_path

        try:
            storage = StorageService()
            url = storage.get_presigned_url(path, expires_in=3600)

            return Response({
                'url': url,
                'type': preview_type,
                'page_count': document.page_count,
            })

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get', 'post'], url_path='versions')
    def versions(self, request, pk=None):
        """List or create document versions."""
        document = self.get_object()

        if request.method == 'GET':
            # List all versions
            versions = Document.objects.filter(
                organization_id=document.organization_id,
                parent_document_id=document.parent_document_id or document.id,
            ).order_by('-version')

            # Include original if this is a version
            if document.parent_document_id:
                versions = versions | Document.objects.filter(
                    id=document.parent_document_id
                )

            serializer = DocumentListSerializer(versions, many=True)
            return Response(serializer.data)

        else:
            # Create new version
            serializer = DocumentVersionSerializer(
                data=request.data,
                context={'document': document}
            )
            serializer.is_valid(raise_exception=True)

            user_id = request.headers.get('X-User-ID')

            try:
                service = DocumentService()
                file_obj = serializer.validated_data['file']

                new_version = service.create_new_version(
                    document_id=str(document.id),
                    user_id=user_id,
                    file_content=file_obj.read(),
                    filename=file_obj.name,
                )

                # Trigger processing
                process_document.delay(str(new_version.id))

                return Response(
                    DocumentDetailSerializer(new_version).data,
                    status=status.HTTP_201_CREATED
                )

            except Exception as e:
                return Response(
                    {'error': str(e)},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

    @action(detail=False, methods=['post'])
    def search(self, request):
        """Search documents."""
        serializer = DocumentSearchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        organization_id = request.headers.get('X-Organization-ID')
        user_id = request.headers.get('X-User-ID')

        if not organization_id:
            return Response(
                {'error': 'Organization header required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            service = DocumentService()
            data = serializer.validated_data

            results = service.search_documents(
                organization_id=organization_id,
                user_id=user_id,
                query=data.get('query'),
                document_type=data.get('document_type'),
                folder_id=data.get('folder_id'),
                include_subfolders=data.get('include_subfolders', False),
                owner_id=data.get('owner_id'),
                tags=data.get('tags'),
                expiring_within_days=data.get('expiring_within_days'),
            )

            # Apply ordering
            order_by = data.get('order_by', '-created_at')
            results = results.order_by(order_by)

            # Paginate
            page = data.get('page', 1)
            page_size = data.get('page_size', 20)
            start = (page - 1) * page_size
            end = start + page_size

            total = results.count()
            results = results[start:end]

            return Response({
                'results': DocumentListSerializer(results, many=True).data,
                'total': total,
                'page': page,
                'page_size': page_size,
                'total_pages': (total + page_size - 1) // page_size,
            })

        except Exception as e:
            logger.error(f"Search failed: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'], url_path='bulk-action')
    def bulk_action(self, request):
        """Perform bulk operations on documents."""
        from ..serializers.document_serializers import DocumentBulkActionSerializer

        serializer = DocumentBulkActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        organization_id = request.headers.get('X-Organization-ID')
        user_id = request.headers.get('X-User-ID')

        data = serializer.validated_data
        document_ids = data['document_ids']
        action_type = data['action']

        # Get documents
        documents = Document.objects.filter(
            id__in=document_ids,
            organization_id=organization_id,
        )

        results = {'success': 0, 'failed': 0, 'errors': []}

        for doc in documents:
            try:
                if action_type == 'delete':
                    doc.soft_delete(user_id)
                elif action_type == 'archive':
                    doc.archive()
                elif action_type == 'restore':
                    doc.restore()
                elif action_type == 'move':
                    doc.folder_id = data.get('target_folder_id')
                    doc.save(update_fields=['folder_id'])

                results['success'] += 1

            except Exception as e:
                results['failed'] += 1
                results['errors'].append({
                    'document_id': str(doc.id),
                    'error': str(e)
                })

        return Response(results)

    @action(detail=True, methods=['post'])
    def restore(self, request, pk=None):
        """Restore deleted document."""
        # Include deleted in lookup
        document = get_object_or_404(
            Document.objects.filter(
                organization_id=request.headers.get('X-Organization-ID')
            ),
            pk=pk
        )

        if document.status != DocumentStatus.DELETED:
            return Response(
                {'error': 'Document is not deleted'},
                status=status.HTTP_400_BAD_REQUEST
            )

        document.restore()

        return Response(DocumentDetailSerializer(document).data)

    @action(detail=True, methods=['post'])
    def archive(self, request, pk=None):
        """Archive document."""
        document = self.get_object()
        document.archive()

        return Response(DocumentDetailSerializer(document).data)

    @action(detail=True, methods=['get'])
    def ocr(self, request, pk=None):
        """Get OCR text from document."""
        document = self.get_object()

        if not document.ocr_completed:
            return Response(
                {'error': 'OCR not completed'},
                status=status.HTTP_404_NOT_FOUND
            )

        return Response({
            'text': document.ocr_text,
            'language': document.ocr_language,
            'confidence': document.ocr_confidence,
        })

    @action(detail=True, methods=['post'], url_path='reprocess')
    def reprocess(self, request, pk=None):
        """Trigger reprocessing of document."""
        document = self.get_object()

        process_document.delay(str(document.id))

        return Response({'message': 'Processing started'})
