# services/organization-service/src/apps/core/serializers/invitation.py
"""
Invitation Serializers

Serializers for organization invitation API endpoints.
"""

from rest_framework import serializers
from apps.core.models import OrganizationInvitation


class InvitationSerializer(serializers.ModelSerializer):
    """Full invitation serializer."""

    organization_name = serializers.CharField(
        source='organization.name',
        read_only=True
    )
    is_expired = serializers.BooleanField(read_only=True)
    is_pending = serializers.BooleanField(read_only=True)
    days_until_expiry = serializers.IntegerField(read_only=True)

    class Meta:
        model = OrganizationInvitation
        fields = [
            'id',
            'organization',
            'organization_name',
            'email',
            'role_id',
            'role_code',
            'status',
            'expires_at',
            'is_expired',
            'is_pending',
            'days_until_expiry',
            'accepted_at',
            'accepted_by_user_id',
            'invited_by',
            'invited_by_email',
            'message',
            'sent_at',
            'sent_count',
            'last_sent_at',
            'created_at',
        ]
        read_only_fields = [
            'id', 'organization', 'token', 'status',
            'accepted_at', 'accepted_by_user_id',
            'sent_at', 'sent_count', 'last_sent_at', 'created_at',
        ]


class InvitationListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for invitation lists."""

    organization_name = serializers.CharField(
        source='organization.name',
        read_only=True
    )
    is_pending = serializers.BooleanField(read_only=True)
    days_until_expiry = serializers.IntegerField(read_only=True)

    class Meta:
        model = OrganizationInvitation
        fields = [
            'id',
            'organization_name',
            'email',
            'role_code',
            'status',
            'expires_at',
            'is_pending',
            'days_until_expiry',
            'sent_count',
            'created_at',
        ]


class InvitationCreateSerializer(serializers.Serializer):
    """Serializer for creating invitations."""

    email = serializers.EmailField()
    role_id = serializers.UUIDField(required=False, allow_null=True)
    role_code = serializers.CharField(max_length=50, required=False, allow_blank=True)
    message = serializers.CharField(required=False, allow_blank=True)
    expires_in_days = serializers.IntegerField(
        min_value=1,
        max_value=30,
        default=7
    )

    def validate_email(self, value):
        return value.lower().strip()


class InvitationBulkCreateSerializer(serializers.Serializer):
    """Serializer for bulk creating invitations."""

    emails = serializers.ListField(
        child=serializers.EmailField(),
        min_length=1,
        max_length=100
    )
    role_id = serializers.UUIDField(required=False, allow_null=True)
    role_code = serializers.CharField(max_length=50, required=False, allow_blank=True)
    message = serializers.CharField(required=False, allow_blank=True)

    def validate_emails(self, value):
        # Normalize and deduplicate
        return list(set(email.lower().strip() for email in value))


class InvitationAcceptSerializer(serializers.Serializer):
    """Serializer for accepting invitations."""

    token = serializers.CharField(max_length=255)

    def validate_token(self, value):
        try:
            invitation = OrganizationInvitation.objects.get(token=value)
        except OrganizationInvitation.DoesNotExist:
            raise serializers.ValidationError("Invalid invitation token")

        if invitation.status == OrganizationInvitation.Status.ACCEPTED:
            raise serializers.ValidationError("Invitation has already been accepted")

        if invitation.status != OrganizationInvitation.Status.PENDING:
            raise serializers.ValidationError(
                f"Invitation cannot be accepted: {invitation.status}"
            )

        if invitation.is_expired:
            raise serializers.ValidationError("Invitation has expired")

        return value


class InvitationResendSerializer(serializers.Serializer):
    """Serializer for resending invitations."""

    invitation_id = serializers.UUIDField()


class InvitationStatisticsSerializer(serializers.Serializer):
    """Serializer for invitation statistics."""

    pending = serializers.IntegerField(read_only=True)
    accepted = serializers.IntegerField(read_only=True)
    expired = serializers.IntegerField(read_only=True)
    cancelled = serializers.IntegerField(read_only=True)
    revoked = serializers.IntegerField(read_only=True)
    total = serializers.IntegerField(read_only=True)
