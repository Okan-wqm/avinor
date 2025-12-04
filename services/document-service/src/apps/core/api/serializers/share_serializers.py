# services/document-service/src/apps/core/api/serializers/share_serializers.py
"""
Share Serializers
"""

from rest_framework import serializers

from ...models import (
    DocumentShare,
    ShareAccessLog,
    ShareTargetType,
    SharePermission,
)


class ShareSerializer(serializers.ModelSerializer):
    """Base share serializer."""

    target_type_display = serializers.CharField(
        source='get_target_type_display',
        read_only=True
    )
    permission_display = serializers.CharField(
        source='get_permission_display',
        read_only=True
    )
    is_active = serializers.BooleanField(read_only=True)
    access_count = serializers.SerializerMethodField()

    class Meta:
        model = DocumentShare
        fields = [
            'id',
            'document_id',
            'folder_id',
            'shared_by',
            'target_type',
            'target_type_display',
            'target_id',
            'target_email',
            'permission',
            'permission_display',
            'expires_at',
            'is_active',
            'access_count',
            'max_downloads',
            'download_count',
            'max_views',
            'view_count',
            'share_token',
            'created_at',
        ]
        read_only_fields = [
            'id',
            'shared_by',
            'download_count',
            'view_count',
            'share_token',
            'created_at',
        ]

    def get_access_count(self, obj):
        """Get total access count."""
        return obj.view_count + obj.download_count


class ShareDetailSerializer(ShareSerializer):
    """Full share details."""

    document_title = serializers.CharField(
        source='document.title',
        read_only=True,
        allow_null=True
    )
    folder_name = serializers.CharField(
        source='folder.name',
        read_only=True,
        allow_null=True
    )
    shared_by_name = serializers.SerializerMethodField()
    public_url = serializers.SerializerMethodField()

    class Meta(ShareSerializer.Meta):
        fields = ShareSerializer.Meta.fields + [
            'document_title',
            'folder_name',
            'shared_by_name',
            'public_url',
            'has_password',
            'message',
            'notify_on_access',
            'revoked_at',
            'revoked_reason',
            'last_accessed_at',
        ]

    def get_shared_by_name(self, obj):
        """Get sharer name from context or cache."""
        return self.context.get('user_names', {}).get(str(obj.shared_by), 'Unknown')

    def get_public_url(self, obj):
        """Get public share URL."""
        if obj.target_type == ShareTargetType.PUBLIC:
            base_url = self.context.get('base_url', '')
            return f"{base_url}/share/{obj.share_token}"
        return None


class ShareCreateSerializer(serializers.Serializer):
    """Serializer for creating shares."""

    document_id = serializers.UUIDField(required=False, allow_null=True)
    folder_id = serializers.UUIDField(required=False, allow_null=True)
    target_type = serializers.ChoiceField(
        choices=[(t.value, t.name) for t in ShareTargetType],
        required=True
    )
    target_id = serializers.UUIDField(required=False, allow_null=True)
    target_email = serializers.EmailField(required=False, allow_blank=True)
    permission = serializers.ChoiceField(
        choices=[(p.value, p.name) for p in SharePermission],
        default=SharePermission.VIEW.value
    )
    expires_at = serializers.DateTimeField(required=False, allow_null=True)
    max_downloads = serializers.IntegerField(
        min_value=0,
        required=False,
        allow_null=True,
        help_text="0 = unlimited"
    )
    max_views = serializers.IntegerField(
        min_value=0,
        required=False,
        allow_null=True,
        help_text="0 = unlimited"
    )
    password = serializers.CharField(
        max_length=100,
        required=False,
        write_only=True,
        help_text="Password protect the share"
    )
    message = serializers.CharField(
        max_length=2000,
        required=False,
        allow_blank=True
    )
    notify_on_access = serializers.BooleanField(default=False)
    send_notification = serializers.BooleanField(
        default=True,
        help_text="Send email notification to target"
    )

    def validate(self, data):
        """Validate share creation."""
        document_id = data.get('document_id')
        folder_id = data.get('folder_id')
        target_type = data.get('target_type')
        target_id = data.get('target_id')
        target_email = data.get('target_email')

        # Must share either document or folder
        if not document_id and not folder_id:
            raise serializers.ValidationError(
                "Must specify either document_id or folder_id"
            )

        if document_id and folder_id:
            raise serializers.ValidationError(
                "Cannot share both document and folder in same share"
            )

        # Validate target based on type
        if target_type == ShareTargetType.USER.value:
            if not target_id:
                raise serializers.ValidationError({
                    'target_id': "Required for user shares"
                })

        elif target_type == ShareTargetType.EMAIL.value:
            if not target_email:
                raise serializers.ValidationError({
                    'target_email': "Required for email shares"
                })

        elif target_type == ShareTargetType.ROLE.value:
            if not target_id:
                raise serializers.ValidationError({
                    'target_id': "Required for role shares (role ID)"
                })

        elif target_type == ShareTargetType.ORGANIZATION.value:
            if not target_id:
                raise serializers.ValidationError({
                    'target_id': "Required for organization shares"
                })

        # Public shares don't need target

        # Validate expiration
        if data.get('expires_at'):
            from django.utils import timezone
            if data['expires_at'] < timezone.now():
                raise serializers.ValidationError({
                    'expires_at': "Expiration must be in the future"
                })

        return data


class ShareUpdateSerializer(serializers.Serializer):
    """Serializer for updating shares."""

    permission = serializers.ChoiceField(
        choices=[(p.value, p.name) for p in SharePermission],
        required=False
    )
    expires_at = serializers.DateTimeField(required=False, allow_null=True)
    max_downloads = serializers.IntegerField(
        min_value=0,
        required=False,
        allow_null=True
    )
    max_views = serializers.IntegerField(
        min_value=0,
        required=False,
        allow_null=True
    )
    password = serializers.CharField(
        max_length=100,
        required=False,
        write_only=True,
        allow_blank=True,
        help_text="Set empty string to remove password"
    )
    notify_on_access = serializers.BooleanField(required=False)


class PublicShareSerializer(serializers.Serializer):
    """Serializer for accessing public shares."""

    token = serializers.CharField(required=True)
    password = serializers.CharField(required=False, write_only=True)

    def validate_token(self, value):
        """Validate share token exists and is valid."""
        try:
            share = DocumentShare.objects.select_related(
                'document', 'folder'
            ).get(share_token=value)

            # Check if expired
            if not share.is_active:
                raise serializers.ValidationError(
                    "This share link has expired or been revoked"
                )

            # Check view limit
            if share.max_views and share.view_count >= share.max_views:
                raise serializers.ValidationError(
                    "View limit reached for this share"
                )

            self.context['share'] = share
            return value

        except DocumentShare.DoesNotExist:
            raise serializers.ValidationError("Invalid share link")

    def validate(self, data):
        """Validate password if required."""
        share = self.context.get('share')

        if share and share.has_password:
            password = data.get('password')
            if not password:
                raise serializers.ValidationError({
                    'password': "Password required for this share"
                })

            if not share.check_password(password):
                raise serializers.ValidationError({
                    'password': "Incorrect password"
                })

        return data


class PublicShareInfoSerializer(serializers.Serializer):
    """Serializer for public share info (without accessing)."""

    share_type = serializers.SerializerMethodField()
    title = serializers.SerializerMethodField()
    requires_password = serializers.BooleanField(source='has_password')
    expires_at = serializers.DateTimeField()
    permission = serializers.CharField()
    shared_by_name = serializers.CharField()
    message = serializers.CharField()

    def get_share_type(self, obj):
        return 'document' if obj.document_id else 'folder'

    def get_title(self, obj):
        if obj.document:
            return obj.document.title or obj.document.original_name
        if obj.folder:
            return obj.folder.name
        return 'Shared Content'


class ShareAccessLogSerializer(serializers.ModelSerializer):
    """Serializer for share access logs."""

    access_type_display = serializers.CharField(
        source='get_access_type_display',
        read_only=True
    )

    class Meta:
        model = ShareAccessLog
        fields = [
            'id',
            'share_id',
            'accessed_by',
            'access_type',
            'access_type_display',
            'accessed_at',
            'ip_address',
            'user_agent',
            'success',
            'failure_reason',
        ]


class ShareRevokeSerializer(serializers.Serializer):
    """Serializer for revoking shares."""

    reason = serializers.CharField(max_length=500, required=False, allow_blank=True)


class BulkShareSerializer(serializers.Serializer):
    """Serializer for bulk sharing."""

    document_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        max_length=50
    )
    folder_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        max_length=50
    )
    target_type = serializers.ChoiceField(
        choices=[(t.value, t.name) for t in ShareTargetType],
        required=True
    )
    targets = serializers.ListField(
        child=serializers.DictField(),
        max_length=20,
        help_text="List of {id: uuid} or {email: string}"
    )
    permission = serializers.ChoiceField(
        choices=[(p.value, p.name) for p in SharePermission],
        default=SharePermission.VIEW.value
    )
    expires_at = serializers.DateTimeField(required=False, allow_null=True)
    message = serializers.CharField(max_length=2000, required=False)

    def validate(self, data):
        """Validate bulk share."""
        document_ids = data.get('document_ids', [])
        folder_ids = data.get('folder_ids', [])

        if not document_ids and not folder_ids:
            raise serializers.ValidationError(
                "Must provide at least one document_id or folder_id"
            )

        if not data.get('targets'):
            raise serializers.ValidationError({
                'targets': "Must provide at least one target"
            })

        return data
