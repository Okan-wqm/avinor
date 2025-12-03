# services/organization-service/src/apps/core/services/invitation_service.py
"""
Invitation Service

Business logic for organization invitations including:
- Creating and sending invitations
- Accepting invitations
- Managing invitation lifecycle
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import timedelta
from uuid import UUID

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.core.cache import cache

from apps.core.models import Organization, OrganizationInvitation

logger = logging.getLogger(__name__)


# ==================== EXCEPTIONS ====================

class InvitationError(Exception):
    """Base exception for invitation errors."""
    pass


class InvitationNotFoundError(InvitationError):
    """Raised when invitation is not found."""
    pass


class InvitationExpiredError(InvitationError):
    """Raised when invitation has expired."""
    pass


class InvitationAlreadyAcceptedError(InvitationError):
    """Raised when invitation is already accepted."""
    pass


# ==================== SERVICE ====================

class InvitationService:
    """
    Service for organization invitation management.

    Handles creating, sending, accepting, and managing invitations.
    """

    CACHE_PREFIX = 'invitation'
    DEFAULT_EXPIRY_DAYS = 7

    def __init__(self):
        self._event_publisher = None
        self._email_service = None

    # ==================== CREATE INVITATIONS ====================

    def create_invitation(
        self,
        organization_id: UUID,
        email: str,
        invited_by: UUID,
        role_id: UUID = None,
        role_code: str = None,
        message: str = None,
        expires_in_days: int = None
    ) -> OrganizationInvitation:
        """
        Create a new invitation.

        Args:
            organization_id: Organization UUID
            email: Email to invite
            invited_by: User creating the invitation
            role_id: Role to assign on acceptance
            role_code: Role code to assign (alternative)
            message: Personal message
            expires_in_days: Days until expiration

        Returns:
            Created OrganizationInvitation instance
        """
        # Get organization
        try:
            org = Organization.objects.get(id=organization_id, deleted_at__isnull=True)
        except Organization.DoesNotExist:
            raise InvitationError(f"Organization {organization_id} not found")

        # Normalize email
        email = email.lower().strip()

        # Check for existing pending invitation
        existing = OrganizationInvitation.objects.filter(
            organization_id=organization_id,
            email=email,
            status=OrganizationInvitation.Status.PENDING,
            expires_at__gt=timezone.now()
        ).first()

        if existing:
            # Extend existing invitation instead of creating new
            existing.extend_expiry(expires_in_days or self.DEFAULT_EXPIRY_DAYS)
            existing.message = message or existing.message
            existing.role_id = role_id or existing.role_id
            existing.role_code = role_code or existing.role_code
            existing.save()
            return existing

        # Create new invitation
        invitation = OrganizationInvitation.create_invitation(
            organization=org,
            email=email,
            invited_by=invited_by,
            role_id=role_id,
            role_code=role_code,
            message=message,
            expires_in_days=expires_in_days or self.DEFAULT_EXPIRY_DAYS
        )

        logger.info(f"Created invitation for {email} to {org.name}")

        # Publish event
        self._publish_event('invitation.created', {
            'invitation_id': str(invitation.id),
            'organization_id': str(organization_id),
            'email': email,
            'invited_by': str(invited_by),
        })

        return invitation

    def create_bulk_invitations(
        self,
        organization_id: UUID,
        emails: List[str],
        invited_by: UUID,
        role_id: UUID = None,
        role_code: str = None,
        message: str = None
    ) -> Dict[str, Any]:
        """
        Create multiple invitations at once.

        Args:
            organization_id: Organization UUID
            emails: List of emails to invite
            invited_by: User creating invitations
            role_id: Role to assign
            role_code: Role code to assign
            message: Personal message

        Returns:
            Dict with results
        """
        results = {
            'created': [],
            'existing': [],
            'failed': [],
        }

        for email in emails:
            try:
                invitation = self.create_invitation(
                    organization_id=organization_id,
                    email=email,
                    invited_by=invited_by,
                    role_id=role_id,
                    role_code=role_code,
                    message=message
                )
                results['created'].append({
                    'email': email,
                    'invitation_id': str(invitation.id),
                })
            except InvitationError as e:
                results['failed'].append({
                    'email': email,
                    'error': str(e),
                })

        logger.info(
            f"Bulk invitations for {organization_id}: "
            f"{len(results['created'])} created, {len(results['failed'])} failed"
        )

        return results

    # ==================== SEND INVITATIONS ====================

    def send_invitation(
        self,
        invitation_id: UUID,
        resend: bool = False
    ) -> bool:
        """
        Send invitation email.

        Args:
            invitation_id: Invitation UUID
            resend: Whether this is a resend

        Returns:
            True if sent successfully
        """
        try:
            invitation = OrganizationInvitation.objects.select_related(
                'organization'
            ).get(id=invitation_id)
        except OrganizationInvitation.DoesNotExist:
            raise InvitationNotFoundError(f"Invitation {invitation_id} not found")

        if not invitation.is_pending:
            raise InvitationError(
                f"Cannot send invitation with status: {invitation.status}"
            )

        # In production, this would call an email service
        # For now, just mark as sent
        invitation.mark_as_sent()

        logger.info(
            f"{'Resent' if resend else 'Sent'} invitation {invitation_id} "
            f"to {invitation.email}"
        )

        self._publish_event('invitation.sent', {
            'invitation_id': str(invitation_id),
            'email': invitation.email,
            'organization_id': str(invitation.organization_id),
            'resend': resend,
        })

        return True

    def resend_invitation(self, invitation_id: UUID) -> bool:
        """Resend an invitation."""
        return self.send_invitation(invitation_id, resend=True)

    # ==================== ACCEPT INVITATIONS ====================

    def accept_invitation(
        self,
        token: str,
        user_id: UUID
    ) -> Dict[str, Any]:
        """
        Accept an invitation.

        Args:
            token: Invitation token
            user_id: User accepting the invitation

        Returns:
            Dict with acceptance result
        """
        try:
            invitation = OrganizationInvitation.objects.select_related(
                'organization'
            ).get(token=token)
        except OrganizationInvitation.DoesNotExist:
            raise InvitationNotFoundError("Invalid invitation token")

        # Check status
        if invitation.status == OrganizationInvitation.Status.ACCEPTED:
            raise InvitationAlreadyAcceptedError("Invitation has already been accepted")

        if invitation.status != OrganizationInvitation.Status.PENDING:
            raise InvitationError(f"Invitation cannot be accepted: {invitation.status}")

        # Check expiration
        if invitation.is_expired:
            invitation.status = OrganizationInvitation.Status.EXPIRED
            invitation.save()
            raise InvitationExpiredError("Invitation has expired")

        # Accept the invitation
        with transaction.atomic():
            invitation.accept(user_id)

            logger.info(
                f"Invitation {invitation.id} accepted by user {user_id} "
                f"for org {invitation.organization.name}"
            )

            # Publish event
            self._publish_event('invitation.accepted', {
                'invitation_id': str(invitation.id),
                'organization_id': str(invitation.organization_id),
                'user_id': str(user_id),
                'role_id': str(invitation.role_id) if invitation.role_id else None,
                'role_code': invitation.role_code,
            })

        return {
            'success': True,
            'organization': {
                'id': str(invitation.organization.id),
                'name': invitation.organization.name,
                'slug': invitation.organization.slug,
            },
            'role_id': str(invitation.role_id) if invitation.role_id else None,
            'role_code': invitation.role_code,
        }

    # ==================== MANAGE INVITATIONS ====================

    def get_invitation(self, invitation_id: UUID) -> Optional[OrganizationInvitation]:
        """Get invitation by ID."""
        try:
            return OrganizationInvitation.objects.select_related(
                'organization'
            ).get(id=invitation_id)
        except OrganizationInvitation.DoesNotExist:
            return None

    def get_invitation_by_token(self, token: str) -> Optional[OrganizationInvitation]:
        """Get invitation by token."""
        try:
            return OrganizationInvitation.objects.select_related(
                'organization'
            ).get(token=token)
        except OrganizationInvitation.DoesNotExist:
            return None

    def list_invitations(
        self,
        organization_id: UUID,
        status: str = None,
        email: str = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[OrganizationInvitation]:
        """
        List invitations for an organization.

        Args:
            organization_id: Organization UUID
            status: Filter by status
            email: Filter by email
            limit: Maximum results
            offset: Result offset

        Returns:
            List of OrganizationInvitation instances
        """
        queryset = OrganizationInvitation.objects.filter(
            organization_id=organization_id
        ).order_by('-created_at')

        if status:
            queryset = queryset.filter(status=status)
        if email:
            queryset = queryset.filter(email__icontains=email.lower())

        return list(queryset[offset:offset + limit])

    def cancel_invitation(
        self,
        invitation_id: UUID,
        cancelled_by: UUID
    ) -> bool:
        """
        Cancel an invitation.

        Args:
            invitation_id: Invitation UUID
            cancelled_by: User cancelling

        Returns:
            True if cancelled
        """
        try:
            invitation = OrganizationInvitation.objects.get(id=invitation_id)
        except OrganizationInvitation.DoesNotExist:
            raise InvitationNotFoundError(f"Invitation {invitation_id} not found")

        if not invitation.cancel():
            raise InvitationError(f"Cannot cancel invitation with status: {invitation.status}")

        logger.info(f"Cancelled invitation {invitation_id}")

        self._publish_event('invitation.cancelled', {
            'invitation_id': str(invitation_id),
            'organization_id': str(invitation.organization_id),
            'email': invitation.email,
            'cancelled_by': str(cancelled_by),
        })

        return True

    def revoke_invitation(
        self,
        invitation_id: UUID,
        revoked_by: UUID
    ) -> bool:
        """
        Revoke an invitation (admin action).

        Args:
            invitation_id: Invitation UUID
            revoked_by: Admin revoking

        Returns:
            True if revoked
        """
        try:
            invitation = OrganizationInvitation.objects.get(id=invitation_id)
        except OrganizationInvitation.DoesNotExist:
            raise InvitationNotFoundError(f"Invitation {invitation_id} not found")

        if not invitation.revoke():
            raise InvitationError(f"Cannot revoke invitation with status: {invitation.status}")

        logger.info(f"Revoked invitation {invitation_id}")

        self._publish_event('invitation.revoked', {
            'invitation_id': str(invitation_id),
            'organization_id': str(invitation.organization_id),
            'email': invitation.email,
            'revoked_by': str(revoked_by),
        })

        return True

    # ==================== UTILITY METHODS ====================

    def get_pending_for_email(
        self,
        email: str,
        organization_id: UUID = None
    ) -> List[OrganizationInvitation]:
        """Get pending invitations for an email address."""
        return list(OrganizationInvitation.get_pending_for_email(
            email=email.lower(),
            organization=Organization.objects.get(id=organization_id) if organization_id else None
        ))

    def expire_old_invitations(self) -> int:
        """
        Mark expired invitations as expired.

        Returns:
            Number of invitations expired
        """
        count = OrganizationInvitation.expire_old_invitations()
        if count > 0:
            logger.info(f"Expired {count} old invitations")
        return count

    def get_invitation_statistics(
        self,
        organization_id: UUID
    ) -> Dict[str, int]:
        """
        Get invitation statistics for an organization.

        Args:
            organization_id: Organization UUID

        Returns:
            Dict with counts by status
        """
        from django.db.models import Count

        stats = OrganizationInvitation.objects.filter(
            organization_id=organization_id
        ).values('status').annotate(count=Count('id'))

        result = {
            'pending': 0,
            'accepted': 0,
            'expired': 0,
            'cancelled': 0,
            'revoked': 0,
            'total': 0,
        }

        for stat in stats:
            result[stat['status']] = stat['count']
            result['total'] += stat['count']

        return result

    # ==================== PRIVATE METHODS ====================

    def _publish_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Publish an event."""
        try:
            from apps.core.events import publish_event
            publish_event(event_type, data)
        except Exception as e:
            logger.error(f"Failed to publish event {event_type}: {e}")
