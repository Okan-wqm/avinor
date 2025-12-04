# services/document-service/src/apps/core/api/views/folder_views.py
"""
Folder Views
"""

import logging

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from ...models import DocumentFolder, Document
from ...services import FolderService
from ..serializers import (
    FolderSerializer,
    FolderListSerializer,
    FolderDetailSerializer,
    FolderCreateSerializer,
    FolderMoveSerializer,
    FolderTreeSerializer,
)
from ..serializers.folder_serializers import FolderUpdateSerializer


logger = logging.getLogger(__name__)


class FolderViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Folder CRUD operations.

    Endpoints:
    - GET /folders/ - List folders
    - POST /folders/ - Create folder
    - GET /folders/{id}/ - Get folder details
    - PATCH /folders/{id}/ - Update folder
    - DELETE /folders/{id}/ - Delete folder
    - GET /folders/tree/ - Get folder tree
    - POST /folders/{id}/move/ - Move folder
    - GET /folders/{id}/contents/ - Get folder contents
    """

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter folders by organization."""
        organization_id = self.request.headers.get('X-Organization-ID')

        if not organization_id:
            return DocumentFolder.objects.none()

        queryset = DocumentFolder.objects.filter(
            organization_id=organization_id,
        )

        # Filter by parent
        parent_id = self.request.query_params.get('parent_id')
        if parent_id:
            if parent_id == 'root':
                queryset = queryset.filter(parent_folder_id__isnull=True)
            else:
                queryset = queryset.filter(parent_folder_id=parent_id)

        return queryset.order_by('name')

    def get_serializer_class(self):
        """Return appropriate serializer."""
        if self.action == 'list':
            return FolderListSerializer
        elif self.action == 'retrieve':
            return FolderDetailSerializer
        elif self.action == 'create':
            return FolderCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return FolderUpdateSerializer
        return FolderSerializer

    def get_serializer_context(self):
        """Add organization to context."""
        context = super().get_serializer_context()
        context['organization_id'] = self.request.headers.get('X-Organization-ID')
        return context

    def create(self, request, *args, **kwargs):
        """Create a new folder."""
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
            service = FolderService()
            folder = service.create_folder(
                organization_id=organization_id,
                owner_id=user_id,
                name=serializer.validated_data['name'],
                parent_folder_id=serializer.validated_data.get('parent_folder_id'),
                description=serializer.validated_data.get('description'),
                access_level=serializer.validated_data.get('access_level'),
                color=serializer.validated_data.get('color'),
                icon=serializer.validated_data.get('icon'),
                metadata=serializer.validated_data.get('metadata', {}),
            )

            return Response(
                FolderDetailSerializer(folder).data,
                status=status.HTTP_201_CREATED
            )

        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Folder creation failed: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def destroy(self, request, *args, **kwargs):
        """Delete folder (and optionally contents)."""
        folder = self.get_object()

        if folder.is_system:
            return Response(
                {'error': 'Cannot delete system folders'},
                status=status.HTTP_400_BAD_REQUEST
            )

        recursive = request.query_params.get('recursive') == 'true'
        user_id = request.headers.get('X-User-ID')

        try:
            service = FolderService()
            service.delete_folder(
                folder_id=str(folder.id),
                user_id=user_id,
                recursive=recursive,
            )

            return Response(status=status.HTTP_204_NO_CONTENT)

        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['get'])
    def tree(self, request):
        """Get full folder tree."""
        organization_id = request.headers.get('X-Organization-ID')

        if not organization_id:
            return Response(
                {'error': 'Organization header required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            service = FolderService()
            tree = service.get_folder_tree(organization_id)

            return Response(tree)

        except Exception as e:
            logger.error(f"Folder tree failed: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def move(self, request, pk=None):
        """Move folder to new parent."""
        folder = self.get_object()

        serializer = FolderMoveSerializer(
            data=request.data,
            context={
                'folder': folder,
                'organization_id': request.headers.get('X-Organization-ID'),
            }
        )
        serializer.is_valid(raise_exception=True)

        try:
            target_folder_id = serializer.validated_data.get('target_folder_id')

            if target_folder_id:
                target = DocumentFolder.objects.get(id=target_folder_id)
                folder.move_to(target)
            else:
                # Move to root
                folder.parent_folder_id = None
                folder.depth = 0
                folder.path = f"/{folder.name}"
                folder.save()

            return Response(FolderDetailSerializer(folder).data)

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'])
    def contents(self, request, pk=None):
        """Get folder contents (documents and subfolders)."""
        folder = self.get_object()

        # Get subfolders
        subfolders = folder.subfolders.all().order_by('name')

        # Get documents
        from ...models import DocumentStatus
        documents = Document.objects.filter(
            folder=folder,
        ).exclude(
            status=DocumentStatus.DELETED
        ).filter(
            is_latest_version=True
        ).order_by('-created_at')

        # Apply sorting
        sort_by = request.query_params.get('sort', 'name')
        sort_dir = request.query_params.get('dir', 'asc')

        if sort_by == 'name':
            documents = documents.order_by(
                'title' if sort_dir == 'asc' else '-title'
            )
        elif sort_by == 'date':
            documents = documents.order_by(
                'created_at' if sort_dir == 'asc' else '-created_at'
            )
        elif sort_by == 'size':
            documents = documents.order_by(
                'file_size' if sort_dir == 'asc' else '-file_size'
            )

        # Paginate
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 50))
        start = (page - 1) * page_size
        end = start + page_size

        total_documents = documents.count()
        documents = documents[start:end]

        from ..serializers import DocumentListSerializer

        return Response({
            'folder': FolderSerializer(folder).data,
            'subfolders': FolderListSerializer(subfolders, many=True).data,
            'documents': DocumentListSerializer(documents, many=True).data,
            'total_documents': total_documents,
            'page': page,
            'page_size': page_size,
        })

    @action(detail=True, methods=['get'])
    def breadcrumb(self, request, pk=None):
        """Get folder breadcrumb path."""
        folder = self.get_object()
        ancestors = folder.get_ancestors()

        return Response({
            'path': [
                {'id': str(a.id), 'name': a.name}
                for a in ancestors
            ] + [{'id': str(folder.id), 'name': folder.name}]
        })

    @action(detail=True, methods=['post'])
    def recalculate(self, request, pk=None):
        """Recalculate folder statistics."""
        folder = self.get_object()
        folder.recalculate_statistics()

        return Response(FolderDetailSerializer(folder).data)

    @action(detail=False, methods=['post'], url_path='create-path')
    def create_path(self, request):
        """Create folder path (create all folders in path)."""
        path = request.data.get('path', '')
        organization_id = request.headers.get('X-Organization-ID')
        user_id = request.headers.get('X-User-ID')

        if not path:
            return Response(
                {'error': 'Path required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            service = FolderService()
            folder = service.ensure_folder_path(
                organization_id=organization_id,
                path=path,
                owner_id=user_id,
            )

            return Response(
                FolderDetailSerializer(folder).data,
                status=status.HTTP_201_CREATED
            )

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
