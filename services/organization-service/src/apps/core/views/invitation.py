# services/organization-service/src/apps/core/views/invitation.py
"""
Invitation ViewSet

REST API endpoints for organization invitation management.
"""

import logging
from typing import Any

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.db import transaction

from apps.core.models import OrganizationInvitation
from apps.core.serializers import (
    InvitationSerializer,
    InvitationListSerializer,
    InvitationCreateSerializer,
    InvitationBulkCreateSerializer,
    InvitationAcceptSerializer,
    InvitationResendSerializer,
    InvitationStatisticsSerializer,
)
from apps.core.services import (
    InvitationService,
    InvitationError,
)

logger = logging.getLogger(__name__)


class InvitationViewSet(viewsets.ViewSet):
    """
    ViewSet for Organization Invitation management.

    Endpoints:
    - GET /organizations/{org_id}/invitations/ - List invitations
    - POST /organizations/{org_id}/invitations/ - Create invitation
    - POST /organizations/{org_id}/invitations/bulk/ - Bulk create
    - GET /organizations/{org_id}/invitations/{id}/ - Get invitation
    - DELETE /organizations/{org_id}/invitations/{id}/ - Cancel invitation
    - POST /organizations/{org_id}/invitations/{id}/resend/ - Resend
    - POST /organizations/{org_id}/invitations/{id}/revoke/ - Revoke
    - GET /organizations/{org_id}/invitations/statistics/ - Get stats
    - POST /invitations/accept/ - Accept invitation (public)
    - GET /invitations/validate/{token}/ - Validate token (public)
    """

    permission_classes = [IsAuthenticated]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.invitation_service = InvitationService()

    def get_permissions(self):
        """Allow unauthenticated access for accept and validate endpoints."""
        if self.action in ['accept', 'validate_token']:
            return [AllowAny()]
        return super().get_permissions()

    def list(self, request: Request, organization_pk: str = None) -> Response:
        """List all invitations for organization."""
        queryset = OrganizationInvitation.objects.filter(
            organization_id=organization_pk
        ).order_by('-created_at')

        # Filter by status
        status_filter = request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        # Filter by email
        email = request.query_params.get('email')
        if email:
            queryset = queryset.filter(email__icontains=email)

        # Filter pending only
        pending_only = request.query_params.get('pending_only', 'false')
        if pending_only.lower() == 'true':
            queryset = queryset.filter(
                status=OrganizationInvitation.Status.PENDING
            )

        serializer = InvitationListSerializer(queryset, many=True)
        return Response({
            'status': 'success',
            'data': serializer.data,
            'count': queryset.count(),
        })

    def create(self, request: Request, organization_pk: str = None) -> Response:
        """Create a new invitation."""
        serializer = InvitationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            with transaction.atomic():
                invitation = self.invitation_service.create_invitation(
                    organization_id=organization_pk,
                    invited_by_user_id=request.user.id,
                    invited_by_email=getattr(request.user, 'email', None),
                    **serializer.validated_data
                )

            output_serializer = InvitationSerializer(invitation)
            return Response({
                'status': 'success',
                'message': 'Invitation created successfully',
                'data': output_serializer.data,
            }, status=status.HTTP_201_CREATED)

        except InvitationError as e:
            logger.warning(f"Invitation creation failed: {e}")
            return Response({
                'status': 'error',
                'message': str(e),
                'code': 'INVITATION_ERROR',
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], url_path='bulk')
    def bulk_create(self, request: Request, organization_pk: str = None) -> Response:
        """Create multiple invitations."""
        serializer = InvitationBulkCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            with transaction.atomic():
                result = self.invitation_service.bulk_create_invitations(
                    organization_id=organization_pk,
                    emails=serializer.validated_data['emails'],
                    role_id=serializer.validated_data.get('role_id'),
                    role_code=serializer.validated_data.get('role_code'),
                    message=serializer.validated_data.get('message'),
                    invited_by_user_id=request.user.id,
                    invited_by_email=getattr(request.user, 'email', None)
                )

            return Response({
                'status': 'success',
                'message': f"Created {result['created']} invitations",
                'data': result,
            }, status=status.HTTP_201_CREATED)

        except InvitationError as e:
            logger.warning(f"Bulk invitation creation failed: {e}")
            return Response({
                'status': 'error',
                'message': str(e),
                'code': 'INVITATION_ERROR',
            }, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request: Request, organization_pk: str = None, pk: str = None) -> Response:
        """Get invitation details."""
        try:
            invitation = OrganizationInvitation.objects.get(
                id=pk,
                organization_id=organization_pk
            )
            serializer = InvitationSerializer(invitation)
            return Response({
                'status': 'success',
                'data': serializer.data,
            })

        except OrganizationInvitation.DoesNotExist:
            return Response({
                'status': 'error',
                'message': 'Invitation not found',
                'code': 'NOT_FOUND',
            }, status=status.HTTP_404_NOT_FOUND)

    def destroy(self, request: Request, organization_pk: str = None, pk: str = None) -> Response:
        """Cancel an invitation."""
        try:
            with transaction.atomic():
                self.invitation_service.cancel_invitation(
                    invitation_id=pk,
                    organization_id=organization_pk,
                    cancelled_by_user_id=request.user.id
                )

            return Response({
                'status': 'success',
                'message': 'Invitation cancelled',
            })

        except InvitationError as e:
            logger.warning(f"Invitation cancellation failed: {e}")
            return Response({
                'status': 'error',
                'message': str(e),
                'code': 'INVITATION_ERROR',
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='resend')
    def resend(self, request: Request, organization_pk: str = None, pk: str = None) -> Response:
        """Resend an invitation email."""
        try:
            with transaction.atomic():
                invitation = self.invitation_service.resend_invitation(
                    invitation_id=pk,
                    organization_id=organization_pk
                )

            serializer = InvitationSerializer(invitation)
            return Response({
                'status': 'success',
                'message': 'Invitation resent successfully',
                'data': serializer.data,
            })

        except InvitationError as e:
            logger.warning(f"Invitation resend failed: {e}")
            return Response({
                'status': 'error',
                'message': str(e),
                'code': 'INVITATION_ERROR',
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='revoke')
    def revoke(self, request: Request, organization_pk: str = None, pk: str = None) -> Response:
        """Revoke an invitation."""
        try:
            with transaction.atomic():
                self.invitation_service.revoke_invitation(
                    invitation_id=pk,
                    organization_id=organization_pk,
                    revoked_by_user_id=request.user.id
                )

            return Response({
                'status': 'success',
                'message': 'Invitation revoked',
            })

        except InvitationError as e:
            logger.warning(f"Invitation revoke failed: {e}")
            return Response({
                'status': 'error',
                'message': str(e),
                'code': 'INVITATION_ERROR',
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='extend')
    def extend(self, request: Request, organization_pk: str = None, pk: str = None) -> Response:
        """Extend invitation expiry."""
        days = request.data.get('days', 7)

        try:
            with transaction.atomic():
                invitation = self.invitation_service.extend_invitation(
                    invitation_id=pk,
                    organization_id=organization_pk,
                    days=days
                )

            serializer = InvitationSerializer(invitation)
            return Response({
                'status': 'success',
                'message': f'Invitation extended by {days} days',
                'data': serializer.data,
            })

        except InvitationError as e:
            logger.warning(f"Invitation extension failed: {e}")
            return Response({
                'status': 'error',
                'message': str(e),
                'code': 'INVITATION_ERROR',
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'], url_path='statistics')
    def statistics(self, request: Request, organization_pk: str = None) -> Response:
        """Get invitation statistics."""
        try:
            stats = self.invitation_service.get_invitation_statistics(
                organization_pk
            )

            serializer = InvitationStatisticsSerializer(data=stats)
            serializer.is_valid()

            return Response({
                'status': 'success',
                'data': stats,
            })

        except InvitationError as e:
            return Response({
                'status': 'error',
                'message': str(e),
                'code': 'INVITATION_ERROR',
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], url_path='accept', permission_classes=[AllowAny])
    def accept(self, request: Request, organization_pk: str = None) -> Response:
        """Accept an invitation (public endpoint)."""
        serializer = InvitationAcceptSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        token = serializer.validated_data['token']

        # Get user_id from authenticated user or from request body
        if request.user.is_authenticated:
            user_id = request.user.id
        else:
            user_id = request.data.get('user_id')
            if not user_id:
                return Response({
                    'status': 'error',
                    'message': 'User ID is required for unauthenticated requests',
                    'code': 'VALIDATION_ERROR',
                }, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                result = self.invitation_service.accept_invitation(
                    token=token,
                    accepted_by_user_id=user_id
                )

            return Response({
                'status': 'success',
                'message': 'Invitation accepted successfully',
                'data': result,
            })

        except InvitationError as e:
            logger.warning(f"Invitation acceptance failed: {e}")
            return Response({
                'status': 'error',
                'message': str(e),
                'code': 'INVITATION_ERROR',
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(
        detail=False,
        methods=['get'],
        url_path='validate/(?P<token>[^/.]+)',
        permission_classes=[AllowAny]
    )
    def validate_token(self, request: Request, organization_pk: str = None, token: str = None) -> Response:
        """Validate an invitation token (public endpoint)."""
        try:
            invitation = OrganizationInvitation.objects.select_related(
                'organization'
            ).get(token=token)

            response_data = {
                'valid': True,
                'email': invitation.email,
                'organization_id': str(invitation.organization_id),
                'organization_name': invitation.organization.name,
                'role_code': invitation.role_code,
                'status': invitation.status,
                'expires_at': invitation.expires_at.isoformat(),
                'is_expired': invitation.is_expired,
                'is_pending': invitation.is_pending,
                'message': invitation.message,
            }

            # Check if already accepted
            if invitation.status == OrganizationInvitation.Status.ACCEPTED:
                response_data['valid'] = False
                response_data['reason'] = 'Invitation has already been accepted'

            # Check if expired
            elif invitation.is_expired:
                response_data['valid'] = False
                response_data['reason'] = 'Invitation has expired'

            # Check if cancelled or revoked
            elif invitation.status in [
                OrganizationInvitation.Status.CANCELLED,
                OrganizationInvitation.Status.REVOKED
            ]:
                response_data['valid'] = False
                response_data['reason'] = f'Invitation has been {invitation.status}'

            return Response({
                'status': 'success',
                'data': response_data,
            })

        except OrganizationInvitation.DoesNotExist:
            return Response({
                'status': 'error',
                'message': 'Invalid invitation token',
                'code': 'INVALID_TOKEN',
                'data': {
                    'valid': False,
                    'reason': 'Token not found',
                },
            }, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['get'], url_path='pending-for-email')
    def pending_for_email(self, request: Request, organization_pk: str = None) -> Response:
        """Get pending invitations for an email address."""
        email = request.query_params.get('email')
        if not email:
            return Response({
                'status': 'error',
                'message': 'Email parameter is required',
                'code': 'VALIDATION_ERROR',
            }, status=status.HTTP_400_BAD_REQUEST)

        invitations = OrganizationInvitation.objects.filter(
            email=email.lower().strip(),
            status=OrganizationInvitation.Status.PENDING
        ).select_related('organization').order_by('-created_at')

        # Optionally filter by organization
        if organization_pk:
            invitations = invitations.filter(organization_id=organization_pk)

        serializer = InvitationListSerializer(invitations, many=True)
        return Response({
            'status': 'success',
            'data': serializer.data,
            'count': invitations.count(),
        })

    @action(detail=False, methods=['post'], url_path='cleanup-expired')
    def cleanup_expired(self, request: Request, organization_pk: str = None) -> Response:
        """Cleanup expired invitations (admin action)."""
        try:
            count = self.invitation_service.cleanup_expired_invitations(
                organization_id=organization_pk
            )

            return Response({
                'status': 'success',
                'message': f'Marked {count} invitations as expired',
                'data': {
                    'cleaned_up': count,
                },
            })

        except InvitationError as e:
            return Response({
                'status': 'error',
                'message': str(e),
                'code': 'INVITATION_ERROR',
            }, status=status.HTTP_400_BAD_REQUEST)
