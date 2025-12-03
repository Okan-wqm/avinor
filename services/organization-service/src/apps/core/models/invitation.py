# services/organization-service/src/apps/core/models/invitation.py
"""
Organization Invitation Model

Handles user invitations to organizations.
"""

import uuid
import secrets
from datetime import timedelta
from django.db import models
from django.utils import timezone


class OrganizationInvitation(models.Model):
    """
    Organization invitation model.

    Allows organization admins to invite users via email.
    Invitations have expiration and can be accepted once.
    """

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        ACCEPTED = 'accepted', 'Accepted'
        EXPIRED = 'expired', 'Expired'
        CANCELLED = 'cancelled', 'Cancelled'
        REVOKED = 'revoked', 'Revoked'

    # Primary Key
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    # Organization Reference
    organization = models.ForeignKey(
        'Organization',
        on_delete=models.CASCADE,
        related_name='invitations'
    )

    # Invitation Details
    email = models.EmailField(help_text="Email address to invite")
    role_id = models.UUIDField(
        blank=True,
        null=True,
        help_text="Role to assign when invitation is accepted"
    )
    role_code = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Role code to assign (alternative to role_id)"
    )

    # Token
    token = models.CharField(
        max_length=255,
        unique=True,
        help_text="Secure invitation token"
    )
    expires_at = models.DateTimeField(help_text="When the invitation expires")

    # Status
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )

    # Acceptance
    accepted_at = models.DateTimeField(blank=True, null=True)
    accepted_by_user_id = models.UUIDField(
        blank=True,
        null=True,
        help_text="User ID who accepted the invitation"
    )

    # Sender
    invited_by = models.UUIDField(help_text="User who sent the invitation")
    invited_by_email = models.EmailField(
        blank=True,
        null=True,
        help_text="Email of user who sent the invitation"
    )

    # Personal Message
    message = models.TextField(
        blank=True,
        null=True,
        help_text="Personal message included in invitation"
    )

    # Metadata
    metadata = models.JSONField(default=dict, blank=True)

    # Tracking
    sent_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="When invitation email was sent"
    )
    sent_count = models.IntegerField(
        default=0,
        help_text="Number of times invitation was sent"
    )
    last_sent_at = models.DateTimeField(blank=True, null=True)

    # Audit
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'organization_invitations'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organization', 'status']),
            models.Index(fields=['email']),
            models.Index(fields=['token']),
            models.Index(fields=['status', 'expires_at']),
        ]

    def __str__(self):
        return f"Invitation to {self.email} for {self.organization.name}"

    def save(self, *args, **kwargs):
        # Generate token if not set
        if not self.token:
            self.token = self._generate_token()

        # Set expiration if not set
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(days=7)

        super().save(*args, **kwargs)

    @staticmethod
    def _generate_token() -> str:
        """Generate a secure invitation token."""
        return secrets.token_urlsafe(32)

    @property
    def is_expired(self) -> bool:
        """Check if invitation has expired."""
        return timezone.now() > self.expires_at

    @property
    def is_pending(self) -> bool:
        """Check if invitation is still pending."""
        return self.status == self.Status.PENDING and not self.is_expired

    @property
    def can_be_accepted(self) -> bool:
        """Check if invitation can be accepted."""
        return self.is_pending

    @property
    def days_until_expiry(self) -> int:
        """Get days until invitation expires."""
        if self.is_expired:
            return 0
        delta = self.expires_at - timezone.now()
        return max(0, delta.days)

    def accept(self, user_id: uuid.UUID) -> bool:
        """
        Accept the invitation.

        Args:
            user_id: The user ID accepting the invitation

        Returns:
            True if accepted successfully
        """
        if not self.can_be_accepted:
            return False

        self.status = self.Status.ACCEPTED
        self.accepted_at = timezone.now()
        self.accepted_by_user_id = user_id
        self.save(update_fields=[
            'status', 'accepted_at', 'accepted_by_user_id'
        ])
        return True

    def cancel(self) -> bool:
        """Cancel the invitation."""
        if self.status != self.Status.PENDING:
            return False

        self.status = self.Status.CANCELLED
        self.save(update_fields=['status'])
        return True

    def revoke(self) -> bool:
        """Revoke the invitation (admin action)."""
        if self.status == self.Status.ACCEPTED:
            return False

        self.status = self.Status.REVOKED
        self.save(update_fields=['status'])
        return True

    def mark_as_sent(self):
        """Mark invitation as sent."""
        now = timezone.now()
        if not self.sent_at:
            self.sent_at = now
        self.last_sent_at = now
        self.sent_count += 1
        self.save(update_fields=['sent_at', 'last_sent_at', 'sent_count'])

    def extend_expiry(self, days: int = 7):
        """Extend invitation expiry."""
        self.expires_at = timezone.now() + timedelta(days=days)
        self.save(update_fields=['expires_at'])

    def regenerate_token(self):
        """Regenerate the invitation token."""
        self.token = self._generate_token()
        self.save(update_fields=['token'])

    @classmethod
    def create_invitation(
        cls,
        organization,
        email: str,
        invited_by: uuid.UUID,
        role_id: uuid.UUID = None,
        role_code: str = None,
        message: str = None,
        expires_in_days: int = 7
    ):
        """
        Create a new invitation.

        Args:
            organization: The organization to invite to
            email: Email address to invite
            invited_by: User ID of inviter
            role_id: Optional role ID to assign
            role_code: Optional role code to assign
            message: Optional personal message
            expires_in_days: Days until expiration

        Returns:
            OrganizationInvitation instance
        """
        return cls.objects.create(
            organization=organization,
            email=email.lower(),
            invited_by=invited_by,
            role_id=role_id,
            role_code=role_code,
            message=message,
            expires_at=timezone.now() + timedelta(days=expires_in_days)
        )

    @classmethod
    def get_pending_for_email(cls, email: str, organization=None):
        """Get pending invitations for an email."""
        queryset = cls.objects.filter(
            email=email.lower(),
            status=cls.Status.PENDING,
            expires_at__gt=timezone.now()
        )
        if organization:
            queryset = queryset.filter(organization=organization)
        return queryset

    @classmethod
    def expire_old_invitations(cls) -> int:
        """
        Mark expired invitations as expired.

        Returns:
            Number of invitations expired
        """
        return cls.objects.filter(
            status=cls.Status.PENDING,
            expires_at__lt=timezone.now()
        ).update(status=cls.Status.EXPIRED)
