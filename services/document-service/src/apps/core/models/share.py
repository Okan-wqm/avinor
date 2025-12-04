# services/document-service/src/apps/core/models/share.py
"""
Document Share Model

Sharing and access control for documents and folders.
"""

import uuid
import secrets
from django.db import models
from django.utils import timezone


class ShareTargetType(models.TextChoices):
    """Who the document is shared with."""
    USER = 'user', 'Specific User'
    ROLE = 'role', 'Role'
    ORGANIZATION = 'organization', 'Organization'
    PUBLIC = 'public', 'Public Link'
    EMAIL = 'email', 'Email Address'


class SharePermission(models.TextChoices):
    """Permission levels for shared documents."""
    VIEW = 'view', 'View Only'
    DOWNLOAD = 'download', 'View & Download'
    EDIT = 'edit', 'View, Download & Edit'
    MANAGE = 'manage', 'Full Management'
    SIGN = 'sign', 'View & Sign'


class DocumentShare(models.Model):
    """
    Sharing configuration for documents and folders.

    Supports:
    - User/role/organization sharing
    - Public links with optional password
    - Expiration dates
    - Download limits
    - Granular permissions
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    organization_id = models.UUIDField(db_index=True)

    # =========================================================================
    # SOURCE (what is being shared)
    # =========================================================================
    document = models.ForeignKey(
        'Document',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='shares'
    )
    folder = models.ForeignKey(
        'DocumentFolder',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='shares'
    )

    # =========================================================================
    # TARGET (who it's shared with)
    # =========================================================================
    shared_with_type = models.CharField(
        max_length=20,
        choices=ShareTargetType.choices
    )
    shared_with_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="User ID, Role ID, or Organization ID"
    )
    shared_with_email = models.EmailField(
        blank=True,
        null=True,
        help_text="For email-based sharing"
    )
    shared_with_name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Display name of recipient"
    )

    # =========================================================================
    # PERMISSIONS
    # =========================================================================
    permission = models.CharField(
        max_length=20,
        choices=SharePermission.choices,
        default=SharePermission.VIEW
    )

    # =========================================================================
    # VALIDITY
    # =========================================================================
    expires_at = models.DateTimeField(
        null=True,
        blank=True
    )
    is_active = models.BooleanField(default=True)

    # =========================================================================
    # PUBLIC LINK SETTINGS
    # =========================================================================
    share_token = models.CharField(
        max_length=100,
        unique=True,
        db_index=True
    )
    share_url = models.CharField(
        max_length=500,
        blank=True,
        null=True
    )

    # Security
    password_protected = models.BooleanField(default=False)
    password_hash = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    # =========================================================================
    # ACCESS LIMITS
    # =========================================================================
    max_downloads = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Maximum number of downloads allowed"
    )
    max_views = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Maximum number of views allowed"
    )

    # Usage counters
    download_count = models.PositiveIntegerField(default=0)
    view_count = models.PositiveIntegerField(default=0)

    # =========================================================================
    # NOTIFICATIONS
    # =========================================================================
    notify_on_access = models.BooleanField(
        default=False,
        help_text="Notify owner when document is accessed"
    )
    notification_email = models.EmailField(
        blank=True,
        null=True,
        help_text="Email to notify (defaults to owner)"
    )

    # =========================================================================
    # AUDIT
    # =========================================================================
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.UUIDField()
    last_accessed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'document_shares'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['document_id', 'shared_with_id']),
            models.Index(fields=['folder_id', 'shared_with_id']),
            models.Index(fields=['share_token']),
            models.Index(fields=['shared_with_type', 'shared_with_id']),
            models.Index(fields=['expires_at']),
        ]

    def __str__(self):
        target = self.document or self.folder
        return f"Share: {target} -> {self.shared_with_type}"

    def save(self, *args, **kwargs):
        """Generate share token if not set."""
        if not self.share_token:
            self.share_token = self.generate_token()
        super().save(*args, **kwargs)

    # =========================================================================
    # PROPERTIES
    # =========================================================================

    @property
    def is_expired(self) -> bool:
        """Check if share has expired."""
        if not self.expires_at:
            return False
        return timezone.now() > self.expires_at

    @property
    def is_download_limit_reached(self) -> bool:
        """Check if download limit has been reached."""
        if not self.max_downloads:
            return False
        return self.download_count >= self.max_downloads

    @property
    def is_view_limit_reached(self) -> bool:
        """Check if view limit has been reached."""
        if not self.max_views:
            return False
        return self.view_count >= self.max_views

    @property
    def is_valid(self) -> bool:
        """Check if share is currently valid."""
        if not self.is_active:
            return False
        if self.is_expired:
            return False
        return True

    @property
    def remaining_downloads(self) -> int | None:
        """Get remaining download count."""
        if not self.max_downloads:
            return None
        return max(0, self.max_downloads - self.download_count)

    @property
    def remaining_views(self) -> int | None:
        """Get remaining view count."""
        if not self.max_views:
            return None
        return max(0, self.max_views - self.view_count)

    @property
    def target(self):
        """Get the shared document or folder."""
        return self.document or self.folder

    # =========================================================================
    # METHODS
    # =========================================================================

    @staticmethod
    def generate_token() -> str:
        """Generate a secure share token."""
        return secrets.token_urlsafe(32)

    def can_access(self, action: str = 'view') -> tuple[bool, str]:
        """
        Check if share allows the requested action.

        Args:
            action: 'view', 'download', 'edit', 'sign', or 'manage'

        Returns:
            Tuple of (allowed, reason)
        """
        if not self.is_active:
            return False, "Share has been deactivated"

        if self.is_expired:
            return False, "Share link has expired"

        if action == 'view' and self.is_view_limit_reached:
            return False, "View limit has been reached"

        if action == 'download' and self.is_download_limit_reached:
            return False, "Download limit has been reached"

        # Check permission level
        permission_hierarchy = {
            SharePermission.VIEW: ['view'],
            SharePermission.DOWNLOAD: ['view', 'download'],
            SharePermission.EDIT: ['view', 'download', 'edit'],
            SharePermission.MANAGE: ['view', 'download', 'edit', 'manage'],
            SharePermission.SIGN: ['view', 'sign'],
        }

        allowed_actions = permission_hierarchy.get(self.permission, [])
        if action not in allowed_actions:
            return False, f"Permission '{self.permission}' does not allow '{action}'"

        return True, ""

    def record_access(self, action: str = 'view') -> None:
        """Record an access event."""
        self.last_accessed_at = timezone.now()
        update_fields = ['last_accessed_at']

        if action == 'view':
            self.view_count += 1
            update_fields.append('view_count')
        elif action == 'download':
            self.download_count += 1
            update_fields.append('download_count')

        self.save(update_fields=update_fields)

    def deactivate(self) -> None:
        """Deactivate the share."""
        self.is_active = False
        self.save(update_fields=['is_active', 'updated_at'])

    def extend_expiry(self, days: int) -> None:
        """Extend the expiry date."""
        from datetime import timedelta

        if self.expires_at:
            base = max(self.expires_at, timezone.now())
        else:
            base = timezone.now()

        self.expires_at = base + timedelta(days=days)
        self.save(update_fields=['expires_at', 'updated_at'])

    def set_password(self, password: str) -> None:
        """Set password protection."""
        from django.contrib.auth.hashers import make_password

        self.password_protected = True
        self.password_hash = make_password(password)
        self.save(update_fields=['password_protected', 'password_hash', 'updated_at'])

    def check_password(self, password: str) -> bool:
        """Check if password is correct."""
        if not self.password_protected:
            return True

        from django.contrib.auth.hashers import check_password
        return check_password(password, self.password_hash)

    def remove_password(self) -> None:
        """Remove password protection."""
        self.password_protected = False
        self.password_hash = None
        self.save(update_fields=['password_protected', 'password_hash', 'updated_at'])


class ShareAccessLog(models.Model):
    """
    Audit log for share access events.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    share = models.ForeignKey(
        DocumentShare,
        on_delete=models.CASCADE,
        related_name='access_logs'
    )

    # Access details
    action = models.CharField(
        max_length=20,
        choices=[
            ('view', 'Viewed'),
            ('download', 'Downloaded'),
            ('edit', 'Edited'),
            ('sign', 'Signed'),
        ]
    )

    # Accessor information
    user_id = models.UUIDField(null=True, blank=True)
    user_email = models.EmailField(blank=True, null=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True, null=True)
    geolocation = models.JSONField(default=dict, blank=True)

    # Timestamp
    accessed_at = models.DateTimeField(auto_now_add=True)

    # Status
    success = models.BooleanField(default=True)
    failure_reason = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    class Meta:
        db_table = 'document_share_access_logs'
        ordering = ['-accessed_at']
        indexes = [
            models.Index(fields=['share_id', 'accessed_at']),
            models.Index(fields=['user_id']),
        ]

    def __str__(self):
        return f"{self.action} on {self.share} at {self.accessed_at}"
