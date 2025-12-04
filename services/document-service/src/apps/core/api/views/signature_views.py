# services/document-service/src/apps/core/api/views/signature_views.py
"""
Signature Views
"""

import logging

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from ...models import DocumentSignature, SignatureRequest, Document
from ...services import SignatureService
from ...tasks import send_signature_request_email
from ..serializers import (
    SignatureSerializer,
    SignatureRequestSerializer,
    SignatureRequestCreateSerializer,
    SignatureVerifySerializer,
)
from ..serializers.signature_serializers import (
    SignatureDetailSerializer,
    SignatureCreateSerializer,
    SignatureRequestUpdateSerializer,
    SignatureRevokeSerializer,
    SignatureVerificationResultSerializer,
)


logger = logging.getLogger(__name__)


class SignatureViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Document Signatures.

    Endpoints:
    - GET /signatures/ - List signatures
    - POST /signatures/ - Create signature
    - GET /signatures/{id}/ - Get signature details
    - POST /signatures/{id}/revoke/ - Revoke signature
    - POST /signatures/verify/ - Verify signature
    """

    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'post', 'head', 'options']

    def get_queryset(self):
        """Filter signatures by organization."""
        organization_id = self.request.headers.get('X-Organization-ID')

        if not organization_id:
            return DocumentSignature.objects.none()

        queryset = DocumentSignature.objects.filter(
            document__organization_id=organization_id,
        ).select_related('document')

        # Filter by document
        document_id = self.request.query_params.get('document_id')
        if document_id:
            queryset = queryset.filter(document_id=document_id)

        # Filter by signer
        signer_id = self.request.query_params.get('signer_id')
        if signer_id:
            queryset = queryset.filter(signer_id=signer_id)

        return queryset.order_by('-signed_at')

    def get_serializer_class(self):
        """Return appropriate serializer."""
        if self.action == 'retrieve':
            return SignatureDetailSerializer
        elif self.action == 'create':
            return SignatureCreateSerializer
        return SignatureSerializer

    def create(self, request, *args, **kwargs):
        """Create a new signature."""
        serializer = SignatureCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user_id = request.headers.get('X-User-ID')
        organization_id = request.headers.get('X-Organization-ID')

        if not user_id:
            return Response(
                {'error': 'User header required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            service = SignatureService()
            data = serializer.validated_data

            # Get document
            document = Document.objects.get(
                id=data['document_id'],
                organization_id=organization_id,
            )

            signature = service.sign_document(
                document=document,
                signer_id=user_id,
                signer_name=request.headers.get('X-User-Name', 'Unknown'),
                signer_email=request.headers.get('X-User-Email', ''),
                signature_type=data.get('signature_type'),
                signature_data=data.get('signature_data'),
                signer_title=data.get('signer_title'),
                reason=data.get('reason'),
                location=data.get('location'),
                page_number=data.get('page_number'),
                position_x=data.get('position_x'),
                position_y=data.get('position_y'),
                width=data.get('width'),
                height=data.get('height'),
                ip_address=self._get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
            )

            return Response(
                SignatureDetailSerializer(signature).data,
                status=status.HTTP_201_CREATED
            )

        except Document.DoesNotExist:
            return Response(
                {'error': 'Document not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Signature creation failed: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def revoke(self, request, pk=None):
        """Revoke a signature."""
        signature = self.get_object()

        serializer = SignatureRevokeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user_id = request.headers.get('X-User-ID')

        try:
            service = SignatureService()
            service.revoke_signature(
                signature=signature,
                revoked_by=user_id,
                reason=serializer.validated_data['reason'],
            )

            return Response(SignatureDetailSerializer(signature).data)

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'])
    def verify(self, request):
        """Verify a signature."""
        serializer = SignatureVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            service = SignatureService()
            data = serializer.validated_data

            # Find signature
            signature = None

            if data.get('signature_id'):
                signature = DocumentSignature.objects.get(id=data['signature_id'])
            elif data.get('verification_token'):
                signature = DocumentSignature.objects.get(
                    verification_token=data['verification_token']
                )
            elif data.get('document_id'):
                # Get all signatures for document
                signatures = DocumentSignature.objects.filter(
                    document_id=data['document_id']
                )
                results = []
                for sig in signatures:
                    result = service.verify_signature(sig)
                    results.append({
                        'signature_id': str(sig.id),
                        'is_valid': result['is_valid'],
                        'signer_name': sig.signer_name,
                        'signed_at': sig.signed_at,
                        'status': sig.status,
                    })
                return Response({'signatures': results})

            if not signature:
                return Response(
                    {'error': 'Signature not found'},
                    status=status.HTTP_404_NOT_FOUND
                )

            result = service.verify_signature(signature)

            return Response(SignatureVerificationResultSerializer(result).data)

        except DocumentSignature.DoesNotExist:
            return Response(
                {'error': 'Signature not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _get_client_ip(self, request):
        """Extract client IP from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')


class SignatureRequestViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Signature Requests.

    Endpoints:
    - GET /signature-requests/ - List requests
    - POST /signature-requests/ - Create request
    - GET /signature-requests/{id}/ - Get request details
    - POST /signature-requests/{id}/cancel/ - Cancel request
    - POST /signature-requests/{id}/remind/ - Send reminder
    """

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter requests by organization."""
        organization_id = self.request.headers.get('X-Organization-ID')
        user_id = self.request.headers.get('X-User-ID')

        if not organization_id:
            return SignatureRequest.objects.none()

        queryset = SignatureRequest.objects.filter(
            document__organization_id=organization_id,
        ).select_related('document', 'signature')

        # Filter by role
        role = self.request.query_params.get('role')
        if role == 'requested':
            queryset = queryset.filter(requested_by=user_id)
        elif role == 'signer':
            queryset = queryset.filter(signer_id=user_id)

        # Filter by status
        request_status = self.request.query_params.get('status')
        if request_status:
            queryset = queryset.filter(status=request_status)

        return queryset.order_by('-created_at')

    def get_serializer_class(self):
        """Return appropriate serializer."""
        if self.action == 'create':
            return SignatureRequestCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return SignatureRequestUpdateSerializer
        return SignatureRequestSerializer

    def create(self, request, *args, **kwargs):
        """Create signature requests."""
        serializer = SignatureRequestCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user_id = request.headers.get('X-User-ID')
        user_name = request.headers.get('X-User-Name', 'Unknown')
        organization_id = request.headers.get('X-Organization-ID')

        try:
            data = serializer.validated_data

            # Get document
            document = Document.objects.get(
                id=data['document_id'],
                organization_id=organization_id,
            )

            created_requests = []

            for signer in data['signers']:
                sig_request = SignatureRequest.objects.create(
                    document=document,
                    signer_id=signer.get('id'),
                    signer_name=signer['name'],
                    signer_email=signer['email'],
                    requested_by=user_id,
                    requested_by_name=user_name,
                    message=data.get('message', ''),
                    deadline=data.get('deadline'),
                )

                created_requests.append(sig_request)

                # Send email notification
                if data.get('send_email', True):
                    send_signature_request_email.delay(str(sig_request.id))

            return Response(
                SignatureRequestSerializer(created_requests, many=True).data,
                status=status.HTTP_201_CREATED
            )

        except Document.DoesNotExist:
            return Response(
                {'error': 'Document not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Signature request creation failed: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel a signature request."""
        sig_request = self.get_object()
        user_id = request.headers.get('X-User-ID')

        # Only requester can cancel
        if str(sig_request.requested_by) != str(user_id):
            return Response(
                {'error': 'Only the requester can cancel'},
                status=status.HTTP_403_FORBIDDEN
            )

        if sig_request.status != 'pending':
            return Response(
                {'error': 'Only pending requests can be cancelled'},
                status=status.HTTP_400_BAD_REQUEST
            )

        from django.utils import timezone
        sig_request.status = 'cancelled'
        sig_request.completed_at = timezone.now()
        sig_request.save()

        return Response(SignatureRequestSerializer(sig_request).data)

    @action(detail=True, methods=['post'])
    def remind(self, request, pk=None):
        """Send reminder for signature request."""
        sig_request = self.get_object()

        if sig_request.status != 'pending':
            return Response(
                {'error': 'Can only remind for pending requests'},
                status=status.HTTP_400_BAD_REQUEST
            )

        from ...tasks import send_signature_reminder
        send_signature_reminder.delay(str(sig_request.id))

        return Response({'message': 'Reminder sent'})

    @action(detail=False, methods=['get'])
    def pending(self, request):
        """Get pending requests for current user."""
        user_id = request.headers.get('X-User-ID')
        user_email = request.headers.get('X-User-Email')

        from django.db.models import Q

        requests = SignatureRequest.objects.filter(
            Q(signer_id=user_id) | Q(signer_email=user_email),
            status='pending',
        ).select_related('document')

        return Response(
            SignatureRequestSerializer(requests, many=True).data
        )
