# services/document-service/src/apps/core/services/share_service.py
"""
Share Service

Document and folder sharing operations.
"""

import uuid
import logging
from typing import List, Optional
from datetime import datetime, timedelta

from django.db import transaction
from django.conf import settings

from ..models import (
    Document,
    DocumentFolder,
    DocumentShare,
    SharePermission,
    ShareTargetType,
)
from ..models.share import ShareAccessLog


logger = logging.getLogger(__name__)


class ShareError(Exception):
    """Share operation error."""
    pass


class ShareService:
    """
    Service for document sharing operations.

    Handles:
    - Creating and managing shares
    - Public link generation
    - Access control and verification
    - Share statistics and audit logs
    """

    # =========================================================================
    # CREATE SHARES
    # =========================================================================

    @transaction.atomic
    def share_document(
        self,
        document_id: uuid.UUID,
        created_by: uuid.UUID,
        shared_with_type: str,
        permission: str = SharePermission.VIEW,
        shared_with_id: uuid.UUID = None,
        shared_with_email: str = None,
        shared_with_name: str = None,
        expires_at: datetime = None,
        password: str = None,
        max_downloads: int = None,
        max_views: int = None,
        notify_on_access: bool = False,
    ) -> DocumentShare:
        """
        Share a document with a user, role, or generate public link.

        Args:
            document_id: Document UUID
            created_by: User creating the share
            shared_with_type: Target type (user, role, organization, public, email)
            permission: Permission level
            shared_with_id: Target user/role/org UUID
            shared_with_email: Target email for email shares
            shared_with_name: Display name of recipient
            expires_at: Expiration datetime
            password: Optional password protection
            max_downloads: Maximum downloads allowed
            max_views: Maximum views allowed
            notify_on_access: Notify owner on access

        Returns:
            Created DocumentShare instance
        """
        try:
            document = Document.objects.get(id=document_id)
        except Document.DoesNotExist:
            raise ShareError(f"Document not found: {document_id}")

        # Check for existing share
        if shared_with_type != ShareTargetType.PUBLIC:
            existing = DocumentShare.objects.filter(
                document_id=document_id,
                shared_with_type=shared_with_type,
                shared_with_id=shared_with_id,
                is_active=True,
            ).first()

            if existing:
                # Update existing share
                return self._update_share(
                    existing,
                    permission=permission,
                    expires_at=expires_at,
                    max_downloads=max_downloads,
                    max_views=max_views,
                )

        share = DocumentShare.objects.create(
            organization_id=document.organization_id,
            document=document,
            shared_with_type=shared_with_type,
            shared_with_id=shared_with_id,
            shared_with_email=shared_with_email,
            shared_with_name=shared_with_name,
            permission=permission,
            expires_at=expires_at,
            max_downloads=max_downloads,
            max_views=max_views,
            notify_on_access=notify_on_access,
            created_by=created_by,
        )

        # Set password if provided
        if password:
            share.set_password(password)

        # Generate share URL
        share.share_url = self._generate_share_url(share.share_token)
        share.save(update_fields=['share_url'])

        logger.info(
            f"Created share for document {document_id} -> "
            f"{shared_with_type}:{shared_with_id or shared_with_email}"
        )

        return share

    @transaction.atomic
    def share_folder(
        self,
        folder_id: uuid.UUID,
        created_by: uuid.UUID,
        shared_with_type: str,
        permission: str = SharePermission.VIEW,
        shared_with_id: uuid.UUID = None,
        shared_with_email: str = None,
        shared_with_name: str = None,
        expires_at: datetime = None,
    ) -> DocumentShare:
        """
        Share a folder with a user, role, or organization.

        Args:
            folder_id: Folder UUID
            created_by: User creating the share
            shared_with_type: Target type
            permission: Permission level
            shared_with_id: Target UUID
            shared_with_email: Target email
            shared_with_name: Display name
            expires_at: Expiration datetime

        Returns:
            Created DocumentShare instance
        """
        try:
            folder = DocumentFolder.objects.get(id=folder_id)
        except DocumentFolder.DoesNotExist:
            raise ShareError(f"Folder not found: {folder_id}")

        # Update folder's shared flag
        folder.is_shared = True
        folder.save(update_fields=['is_shared'])

        share = DocumentShare.objects.create(
            organization_id=folder.organization_id,
            folder=folder,
            shared_with_type=shared_with_type,
            shared_with_id=shared_with_id,
            shared_with_email=shared_with_email,
            shared_with_name=shared_with_name,
            permission=permission,
            expires_at=expires_at,
            created_by=created_by,
        )

        share.share_url = self._generate_share_url(share.share_token)
        share.save(update_fields=['share_url'])

        logger.info(f"Created share for folder {folder_id}")

        return share

    def create_public_link(
        self,
        document_id: uuid.UUID,
        created_by: uuid.UUID,
        permission: str = SharePermission.VIEW,
        expires_in_days: int = None,
        password: str = None,
        max_downloads: int = None,
    ) -> DocumentShare:
        """
        Create a public share link for a document.

        Args:
            document_id: Document UUID
            created_by: User creating the link
            permission: Permission level
            expires_in_days: Days until expiration (None for no expiry)
            password: Optional password
            max_downloads: Maximum downloads

        Returns:
            Created DocumentShare instance
        """
        expires_at = None
        if expires_in_days:
            from django.utils import timezone
            expires_at = timezone.now() + timedelta(days=expires_in_days)

        return self.share_document(
            document_id=document_id,
            created_by=created_by,
            shared_with_type=ShareTargetType.PUBLIC,
            permission=permission,
            expires_at=expires_at,
            password=password,
            max_downloads=max_downloads,
        )

    # =========================================================================
    # RETRIEVE
    # =========================================================================

    def get_share(
        self,
        share_id: uuid.UUID,
    ) -> DocumentShare:
        """
        Get a share by ID.

        Args:
            share_id: Share UUID

        Returns:
            DocumentShare instance
        """
        try:
            return DocumentShare.objects.get(id=share_id)
        except DocumentShare.DoesNotExist:
            raise ShareError(f"Share not found: {share_id}")

    def get_share_by_token(
        self,
        token: str,
    ) -> DocumentShare:
        """
        Get a share by its public token.

        Args:
            token: Share token

        Returns:
            DocumentShare instance
        """
        try:
            return DocumentShare.objects.select_related(
                'document', 'folder'
            ).get(share_token=token)
        except DocumentShare.DoesNotExist:
            raise ShareError("Share link not found or has expired")

    def get_document_shares(
        self,
        document_id: uuid.UUID,
        active_only: bool = True,
    ) -> List[DocumentShare]:
        """
        Get all shares for a document.

        Args:
            document_id: Document UUID
            active_only: Only active shares

        Returns:
            List of DocumentShare instances
        """
        queryset = DocumentShare.objects.filter(document_id=document_id)

        if active_only:
            queryset = queryset.filter(is_active=True)

        return list(queryset.order_by('-created_at'))

    def get_shared_with_user(
        self,
        user_id: uuid.UUID,
        organization_id: uuid.UUID = None,
        include_role_shares: bool = True,
    ) -> List[DocumentShare]:
        """
        Get documents/folders shared with a user.

        Args:
            user_id: User UUID
            organization_id: Optional organization filter
            include_role_shares: Include shares to user's roles

        Returns:
            List of DocumentShare instances
        """
        from django.db.models import Q

        queryset = DocumentShare.objects.filter(
            is_active=True,
            shared_with_type=ShareTargetType.USER,
            shared_with_id=user_id,
        ).select_related('document', 'folder')

        if organization_id:
            queryset = queryset.filter(organization_id=organization_id)

        # Filter out expired
        from django.utils import timezone
        now = timezone.now()
        queryset = queryset.filter(
            Q(expires_at__isnull=True) | Q(expires_at__gt=now)
        )

        return list(queryset.order_by('-created_at'))

    # =========================================================================
    # ACCESS VERIFICATION
    # =========================================================================

    def verify_access(
        self,
        token: str,
        action: str = 'view',
        password: str = None,
        user_id: uuid.UUID = None,
        ip_address: str = None,
        user_agent: str = None,
    ) -> tuple[bool, DocumentShare, str]:
        """
        Verify access to a shared resource.

        Args:
            token: Share token
            action: Requested action (view, download, edit, sign)
            password: Password if required
            user_id: Accessing user's UUID
            ip_address: Client IP
            user_agent: Client user agent

        Returns:
            Tuple of (allowed, share_instance, message)
        """
        try:
            share = self.get_share_by_token(token)
        except ShareError:
            return False, None, "Share link not found or has expired"

        # Check if active
        if not share.is_valid:
            reason = "Share has expired" if share.is_expired else "Share is inactive"
            self._log_access(share, action, user_id, ip_address, user_agent, False, reason)
            return False, share, reason

        # Check password
        if share.password_protected:
            if not password:
                return False, share, "Password required"
            if not share.check_password(password):
                self._log_access(share, action, user_id, ip_address, user_agent, False, "Invalid password")
                return False, share, "Invalid password"

        # Check permission
        allowed, reason = share.can_access(action)
        if not allowed:
            self._log_access(share, action, user_id, ip_address, user_agent, False, reason)
            return False, share, reason

        # Log successful access
        self._log_access(share, action, user_id, ip_address, user_agent, True)

        return True, share, "Access granted"

    def access_shared_document(
        self,
        token: str,
        action: str = 'view',
        password: str = None,
        user_id: uuid.UUID = None,
        ip_address: str = None,
        user_agent: str = None,
    ) -> Document:
        """
        Access a shared document after verification.

        Args:
            token: Share token
            action: Action to perform
            password: Password if required
            user_id: Accessing user
            ip_address: Client IP
            user_agent: Client user agent

        Returns:
            Document instance
        """
        allowed, share, message = self.verify_access(
            token, action, password, user_id, ip_address, user_agent
        )

        if not allowed:
            raise ShareError(message)

        if not share.document:
            raise ShareError("This share is for a folder, not a document")

        # Record access
        share.record_access(action)

        return share.document

    # =========================================================================
    # UPDATE & DELETE
    # =========================================================================

    def _update_share(
        self,
        share: DocumentShare,
        **updates
    ) -> DocumentShare:
        """Update existing share."""
        allowed_fields = {
            'permission', 'expires_at', 'max_downloads', 'max_views',
            'notify_on_access', 'is_active',
        }

        for field, value in updates.items():
            if field in allowed_fields and value is not None:
                setattr(share, field, value)

        share.save()
        return share

    def update_share(
        self,
        share_id: uuid.UUID,
        updated_by: uuid.UUID,
        **updates
    ) -> DocumentShare:
        """
        Update a share.

        Args:
            share_id: Share UUID
            updated_by: User updating
            **updates: Fields to update

        Returns:
            Updated DocumentShare instance
        """
        share = self.get_share(share_id)

        # Verify ownership (must be creator or document/folder owner)
        if share.created_by != updated_by:
            target = share.document or share.folder
            if target.owner_id != updated_by:
                raise ShareError("Not authorized to update this share")

        return self._update_share(share, **updates)

    def revoke_share(
        self,
        share_id: uuid.UUID,
        revoked_by: uuid.UUID,
    ) -> bool:
        """
        Revoke (deactivate) a share.

        Args:
            share_id: Share UUID
            revoked_by: User revoking

        Returns:
            True if revoked
        """
        share = self.get_share(share_id)

        # Verify ownership
        if share.created_by != revoked_by:
            target = share.document or share.folder
            if target.owner_id != revoked_by:
                raise ShareError("Not authorized to revoke this share")

        share.deactivate()

        # Update folder shared flag if needed
        if share.folder:
            remaining = DocumentShare.objects.filter(
                folder=share.folder,
                is_active=True,
            ).exists()
            if not remaining:
                share.folder.is_shared = False
                share.folder.save(update_fields=['is_shared'])

        logger.info(f"Revoked share: {share_id}")

        return True

    def revoke_all_shares(
        self,
        document_id: uuid.UUID = None,
        folder_id: uuid.UUID = None,
        revoked_by: uuid.UUID = None,
    ) -> int:
        """
        Revoke all shares for a document or folder.

        Args:
            document_id: Document UUID
            folder_id: Folder UUID
            revoked_by: User revoking

        Returns:
            Number of shares revoked
        """
        if document_id:
            queryset = DocumentShare.objects.filter(
                document_id=document_id,
                is_active=True,
            )
        elif folder_id:
            queryset = DocumentShare.objects.filter(
                folder_id=folder_id,
                is_active=True,
            )
        else:
            return 0

        count = queryset.update(is_active=False)

        logger.info(f"Revoked {count} shares")

        return count

    # =========================================================================
    # SHARE SETTINGS
    # =========================================================================

    def set_share_password(
        self,
        share_id: uuid.UUID,
        password: str,
        set_by: uuid.UUID,
    ) -> DocumentShare:
        """
        Set or update share password.

        Args:
            share_id: Share UUID
            password: New password
            set_by: User setting password

        Returns:
            Updated DocumentShare instance
        """
        share = self.get_share(share_id)
        share.set_password(password)

        logger.info(f"Password set for share: {share_id}")

        return share

    def remove_share_password(
        self,
        share_id: uuid.UUID,
        removed_by: uuid.UUID,
    ) -> DocumentShare:
        """
        Remove share password.

        Args:
            share_id: Share UUID
            removed_by: User removing password

        Returns:
            Updated DocumentShare instance
        """
        share = self.get_share(share_id)
        share.remove_password()

        logger.info(f"Password removed from share: {share_id}")

        return share

    def extend_share_expiry(
        self,
        share_id: uuid.UUID,
        days: int,
        extended_by: uuid.UUID,
    ) -> DocumentShare:
        """
        Extend share expiration.

        Args:
            share_id: Share UUID
            days: Days to extend
            extended_by: User extending

        Returns:
            Updated DocumentShare instance
        """
        share = self.get_share(share_id)
        share.extend_expiry(days)

        logger.info(f"Extended share {share_id} by {days} days")

        return share

    # =========================================================================
    # AUDIT & STATS
    # =========================================================================

    def get_share_statistics(
        self,
        share_id: uuid.UUID,
    ) -> dict:
        """
        Get statistics for a share.

        Args:
            share_id: Share UUID

        Returns:
            Dict with statistics
        """
        share = self.get_share(share_id)

        logs = ShareAccessLog.objects.filter(share=share)

        return {
            'share_id': str(share_id),
            'created_at': share.created_at.isoformat(),
            'expires_at': share.expires_at.isoformat() if share.expires_at else None,
            'is_active': share.is_active,
            'view_count': share.view_count,
            'download_count': share.download_count,
            'remaining_downloads': share.remaining_downloads,
            'remaining_views': share.remaining_views,
            'last_accessed_at': share.last_accessed_at.isoformat() if share.last_accessed_at else None,
            'total_access_attempts': logs.count(),
            'successful_accesses': logs.filter(success=True).count(),
            'failed_accesses': logs.filter(success=False).count(),
        }

    def get_access_logs(
        self,
        share_id: uuid.UUID,
        limit: int = 100,
    ) -> List[ShareAccessLog]:
        """
        Get access logs for a share.

        Args:
            share_id: Share UUID
            limit: Maximum records

        Returns:
            List of ShareAccessLog instances
        """
        return list(
            ShareAccessLog.objects.filter(
                share_id=share_id
            ).order_by('-accessed_at')[:limit]
        )

    def _log_access(
        self,
        share: DocumentShare,
        action: str,
        user_id: uuid.UUID = None,
        ip_address: str = None,
        user_agent: str = None,
        success: bool = True,
        failure_reason: str = None,
    ) -> ShareAccessLog:
        """Create access log entry."""
        return ShareAccessLog.objects.create(
            share=share,
            action=action,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            success=success,
            failure_reason=failure_reason,
        )

    def _generate_share_url(self, token: str) -> str:
        """Generate full share URL."""
        base_url = getattr(settings, 'SHARE_URL_BASE', 'http://localhost:8011')
        return f"{base_url}/api/v1/documents/share/{token}"
