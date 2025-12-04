# services/document-service/src/apps/core/api/views/share_views.py
"""
Share Views
"""

import logging

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny

from django.http import HttpResponse
from django.db.models import Q

from ...models import DocumentShare, ShareAccessLog, Document, DocumentFolder
from ...services import ShareService, StorageService
from ..serializers import (
    ShareSerializer,
    ShareCreateSerializer,
    ShareUpdateSerializer,
    PublicShareSerializer,
)
from ..serializers.share_serializers import (
    ShareDetailSerializer,
    ShareRevokeSerializer,
    ShareAccessLogSerializer,
    PublicShareInfoSerializer,
    BulkShareSerializer,
)


logger = logging.getLogger(__name__)


class ShareViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Document/Folder Shares.

    Endpoints:
    - GET /shares/ - List shares
    - POST /shares/ - Create share
    - GET /shares/{id}/ - Get share details
    - PATCH /shares/{id}/ - Update share
    - DELETE /shares/{id}/ - Revoke share
    - GET /shares/{id}/logs/ - Get access logs
    - POST /shares/bulk/ - Create bulk shares
    """

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter shares by organization."""
        organization_id = self.request.headers.get('X-Organization-ID')
        user_id = self.request.headers.get('X-User-ID')

        if not organization_id:
            return DocumentShare.objects.none()

        queryset = DocumentShare.objects.filter(
            Q(document__organization_id=organization_id) |
            Q(folder__organization_id=organization_id)
        ).select_related('document', 'folder')

        # Filter by what user can see
        view_mode = self.request.query_params.get('mode', 'all')

        if view_mode == 'shared_by_me':
            queryset = queryset.filter(shared_by=user_id)
        elif view_mode == 'shared_with_me':
            user_email = self.request.headers.get('X-User-Email')
            queryset = queryset.filter(
                Q(target_id=user_id) |
                Q(target_email=user_email) |
                Q(target_type='organization')
            )

        # Filter by document/folder
        document_id = self.request.query_params.get('document_id')
        if document_id:
            queryset = queryset.filter(document_id=document_id)

        folder_id = self.request.query_params.get('folder_id')
        if folder_id:
            queryset = queryset.filter(folder_id=folder_id)

        # Filter by active only
        if self.request.query_params.get('active_only') == 'true':
            from django.utils import timezone
            now = timezone.now()
            queryset = queryset.filter(
                Q(expires_at__isnull=True) | Q(expires_at__gt=now),
                revoked_at__isnull=True,
            )

        return queryset.order_by('-created_at')

    def get_serializer_class(self):
        """Return appropriate serializer."""
        if self.action == 'retrieve':
            return ShareDetailSerializer
        elif self.action == 'create':
            return ShareCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return ShareUpdateSerializer
        return ShareSerializer

    def create(self, request, *args, **kwargs):
        """Create a new share."""
        serializer = ShareCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        organization_id = request.headers.get('X-Organization-ID')
        user_id = request.headers.get('X-User-ID')

        try:
            service = ShareService()
            data = serializer.validated_data

            # Get document or folder
            document = None
            folder = None

            if data.get('document_id'):
                document = Document.objects.get(
                    id=data['document_id'],
                    organization_id=organization_id,
                )
            elif data.get('folder_id'):
                folder = DocumentFolder.objects.get(
                    id=data['folder_id'],
                    organization_id=organization_id,
                )

            share = service.create_share(
                document=document,
                folder=folder,
                shared_by=user_id,
                target_type=data['target_type'],
                target_id=data.get('target_id'),
                target_email=data.get('target_email'),
                permission=data.get('permission'),
                expires_at=data.get('expires_at'),
                max_downloads=data.get('max_downloads'),
                max_views=data.get('max_views'),
                password=data.get('password'),
                message=data.get('message'),
                notify_on_access=data.get('notify_on_access', False),
            )

            # Send notification if requested
            if data.get('send_notification', True):
                service.send_share_notification(share)

            return Response(
                ShareDetailSerializer(share).data,
                status=status.HTTP_201_CREATED
            )

        except (Document.DoesNotExist, DocumentFolder.DoesNotExist):
            return Response(
                {'error': 'Document or folder not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Share creation failed: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def update(self, request, *args, **kwargs):
        """Update share settings."""
        share = self.get_object()
        user_id = request.headers.get('X-User-ID')

        # Only sharer can update
        if str(share.shared_by) != str(user_id):
            return Response(
                {'error': 'Only the sharer can modify'},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = ShareUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        try:
            service = ShareService()
            service.update_share(share, **serializer.validated_data)

            return Response(ShareDetailSerializer(share).data)

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def destroy(self, request, *args, **kwargs):
        """Revoke share."""
        share = self.get_object()

        serializer = ShareRevokeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            service = ShareService()
            service.revoke_share(
                share=share,
                reason=serializer.validated_data.get('reason', ''),
            )

            return Response(status=status.HTTP_204_NO_CONTENT)

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'])
    def logs(self, request, pk=None):
        """Get share access logs."""
        share = self.get_object()

        logs = ShareAccessLog.objects.filter(
            share=share
        ).order_by('-accessed_at')[:100]

        return Response(
            ShareAccessLogSerializer(logs, many=True).data
        )

    @action(detail=False, methods=['post'])
    def bulk(self, request):
        """Create bulk shares."""
        serializer = BulkShareSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        organization_id = request.headers.get('X-Organization-ID')
        user_id = request.headers.get('X-User-ID')

        try:
            service = ShareService()
            data = serializer.validated_data

            results = service.create_bulk_shares(
                organization_id=organization_id,
                shared_by=user_id,
                document_ids=data.get('document_ids', []),
                folder_ids=data.get('folder_ids', []),
                target_type=data['target_type'],
                targets=data['targets'],
                permission=data.get('permission'),
                expires_at=data.get('expires_at'),
                message=data.get('message'),
            )

            return Response(results)

        except Exception as e:
            logger.error(f"Bulk share failed: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'], url_path='regenerate-link')
    def regenerate_link(self, request, pk=None):
        """Regenerate share link."""
        share = self.get_object()

        if share.target_type != 'public':
            return Response(
                {'error': 'Only public shares have links'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            service = ShareService()
            new_token = service.regenerate_share_token(share)

            return Response({
                'share_token': new_token,
                'share_url': f"/share/{new_token}",
            })

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PublicShareView(APIView):
    """
    View for accessing public shares.

    Endpoints:
    - GET /share/{token}/ - Get share info
    - POST /share/{token}/ - Access share (with password if required)
    - GET /share/{token}/download/ - Download shared content
    """

    permission_classes = [AllowAny]

    def get(self, request, token):
        """Get public share info."""
        try:
            share = DocumentShare.objects.select_related(
                'document', 'folder'
            ).get(share_token=token)

            # Check if active
            if not share.is_active:
                return Response(
                    {'error': 'This share link has expired or been revoked'},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Return info without content
            return Response(PublicShareInfoSerializer(share).data)

        except DocumentShare.DoesNotExist:
            return Response(
                {'error': 'Share not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    def post(self, request, token):
        """Access share content."""
        serializer = PublicShareSerializer(data={'token': token, **request.data})
        serializer.is_valid(raise_exception=True)

        share = serializer.context['share']

        try:
            service = ShareService()

            # Log access
            service.log_access(
                share=share,
                access_type='view',
                ip_address=self._get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
            )

            # Return content info
            if share.document:
                from ..serializers import DocumentDetailSerializer
                return Response({
                    'type': 'document',
                    'content': DocumentDetailSerializer(share.document).data,
                    'permission': share.permission,
                })
            elif share.folder:
                from ..serializers import FolderDetailSerializer
                return Response({
                    'type': 'folder',
                    'content': FolderDetailSerializer(share.folder).data,
                    'permission': share.permission,
                })

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _get_client_ip(self, request):
        """Extract client IP."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')


class PublicShareDownloadView(APIView):
    """Download from public share."""

    permission_classes = [AllowAny]

    def get(self, request, token):
        """Download shared document."""
        password = request.query_params.get('password')

        serializer = PublicShareSerializer(
            data={'token': token, 'password': password}
        )

        try:
            serializer.is_valid(raise_exception=True)
        except Exception as e:
            return Response(
                {'error': str(e.detail) if hasattr(e, 'detail') else str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

        share = serializer.context['share']

        # Check download permission
        if share.permission not in ['download', 'edit', 'manage']:
            return Response(
                {'error': 'Download not allowed for this share'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Check download limit
        if share.max_downloads and share.download_count >= share.max_downloads:
            return Response(
                {'error': 'Download limit reached'},
                status=status.HTTP_403_FORBIDDEN
            )

        if not share.document:
            return Response(
                {'error': 'Folder download not supported via this endpoint'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Log download
            service = ShareService()
            service.log_access(
                share=share,
                access_type='download',
                ip_address=self._get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
            )

            # Stream file
            storage = StorageService()
            content = storage.download_file(share.document.file_path)

            response = HttpResponse(
                content,
                content_type=share.document.mime_type or 'application/octet-stream'
            )
            response['Content-Disposition'] = (
                f'attachment; filename="{share.document.original_name}"'
            )
            response['Content-Length'] = len(content)

            return response

        except Exception as e:
            logger.error(f"Public download failed: {e}")
            return Response(
                {'error': 'Download failed'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')
