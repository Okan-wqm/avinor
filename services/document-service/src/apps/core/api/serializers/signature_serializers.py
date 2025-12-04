# services/document-service/src/apps/core/api/serializers/signature_serializers.py
"""
Signature Serializers
"""

from rest_framework import serializers

from ...models import (
    DocumentSignature,
    SignatureRequest,
    SignatureType,
    SignatureStatus,
)


class SignatureSerializer(serializers.ModelSerializer):
    """Document signature serializer."""

    signature_type_display = serializers.CharField(
        source='get_signature_type_display',
        read_only=True
    )
    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )
    is_valid = serializers.BooleanField(read_only=True)

    class Meta:
        model = DocumentSignature
        fields = [
            'id',
            'document_id',
            'signer_id',
            'signer_name',
            'signer_email',
            'signer_title',
            'signature_type',
            'signature_type_display',
            'status',
            'status_display',
            'is_valid',
            'signed_at',
            'reason',
            'location',
            'page_number',
            'position_x',
            'position_y',
            'width',
            'height',
            'certificate_serial',
            'certificate_issuer',
            'verification_token',
            'created_at',
        ]
        read_only_fields = [
            'id',
            'signer_id',
            'signer_name',
            'signer_email',
            'signed_at',
            'verification_token',
            'created_at',
        ]


class SignatureDetailSerializer(SignatureSerializer):
    """Full signature details."""

    class Meta(SignatureSerializer.Meta):
        fields = SignatureSerializer.Meta.fields + [
            'signature_hash',
            'certificate_valid_from',
            'certificate_valid_to',
            'ip_address',
            'user_agent',
            'revoked_at',
            'revoked_reason',
        ]


class SignatureCreateSerializer(serializers.Serializer):
    """Serializer for creating signatures."""

    document_id = serializers.UUIDField(required=True)
    signature_type = serializers.ChoiceField(
        choices=[(t.value, t.name) for t in SignatureType],
        default=SignatureType.DRAWN.value
    )
    signature_data = serializers.CharField(
        required=True,
        help_text="Base64 encoded signature image for drawn/uploaded, text for typed"
    )
    signer_title = serializers.CharField(max_length=100, required=False)
    reason = serializers.CharField(max_length=500, required=False)
    location = serializers.CharField(max_length=200, required=False)
    page_number = serializers.IntegerField(min_value=1, required=False)
    position_x = serializers.FloatField(required=False)
    position_y = serializers.FloatField(required=False)
    width = serializers.FloatField(required=False)
    height = serializers.FloatField(required=False)

    # For certificate-based signing
    certificate_data = serializers.CharField(required=False)
    certificate_password = serializers.CharField(required=False, write_only=True)

    def validate_signature_data(self, value):
        """Validate signature data format."""
        sig_type = self.initial_data.get('signature_type', SignatureType.DRAWN.value)

        if sig_type in [SignatureType.DRAWN.value, SignatureType.UPLOADED.value]:
            # Should be base64 encoded image
            if not value.startswith('data:image/') and len(value) < 100:
                raise serializers.ValidationError(
                    "Signature data should be base64 encoded image"
                )
        elif sig_type == SignatureType.TYPED.value:
            if len(value) > 100:
                raise serializers.ValidationError(
                    "Typed signature text too long"
                )

        return value


class SignatureRequestSerializer(serializers.ModelSerializer):
    """Signature request serializer."""

    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )
    document_title = serializers.CharField(
        source='document.title',
        read_only=True
    )
    is_overdue = serializers.SerializerMethodField()

    class Meta:
        model = SignatureRequest
        fields = [
            'id',
            'document_id',
            'document_title',
            'signer_id',
            'signer_name',
            'signer_email',
            'requested_by',
            'requested_by_name',
            'status',
            'status_display',
            'message',
            'deadline',
            'is_overdue',
            'email_sent',
            'email_sent_at',
            'reminder_count',
            'last_reminder_at',
            'created_at',
            'completed_at',
        ]
        read_only_fields = [
            'id',
            'requested_by',
            'requested_by_name',
            'status',
            'email_sent',
            'email_sent_at',
            'reminder_count',
            'last_reminder_at',
            'created_at',
            'completed_at',
        ]

    def get_is_overdue(self, obj):
        """Check if request is overdue."""
        if obj.deadline and obj.status == 'pending':
            from django.utils import timezone
            return obj.deadline < timezone.now()
        return False


class SignatureRequestCreateSerializer(serializers.Serializer):
    """Serializer for creating signature requests."""

    document_id = serializers.UUIDField(required=True)
    signers = serializers.ListField(
        child=serializers.DictField(),
        min_length=1,
        max_length=10,
        help_text="List of signer objects with id, name, email"
    )
    message = serializers.CharField(max_length=2000, required=False)
    deadline = serializers.DateTimeField(required=False, allow_null=True)
    send_email = serializers.BooleanField(default=True)

    def validate_signers(self, value):
        """Validate signers list."""
        for i, signer in enumerate(value):
            if not signer.get('email'):
                raise serializers.ValidationError(
                    f"Signer {i+1} must have an email address"
                )
            if not signer.get('name'):
                raise serializers.ValidationError(
                    f"Signer {i+1} must have a name"
                )

        # Check for duplicate emails
        emails = [s['email'].lower() for s in value]
        if len(emails) != len(set(emails)):
            raise serializers.ValidationError(
                "Duplicate signer emails not allowed"
            )

        return value


class SignatureRequestUpdateSerializer(serializers.Serializer):
    """Serializer for updating signature requests."""

    message = serializers.CharField(max_length=2000, required=False)
    deadline = serializers.DateTimeField(required=False, allow_null=True)

    def validate_deadline(self, value):
        """Validate deadline is in future."""
        if value:
            from django.utils import timezone
            if value < timezone.now():
                raise serializers.ValidationError(
                    "Deadline must be in the future"
                )
        return value


class SignatureVerifySerializer(serializers.Serializer):
    """Serializer for signature verification."""

    signature_id = serializers.UUIDField(required=False)
    verification_token = serializers.CharField(required=False)
    document_id = serializers.UUIDField(required=False)

    def validate(self, data):
        """Ensure at least one identifier provided."""
        if not any([
            data.get('signature_id'),
            data.get('verification_token'),
            data.get('document_id'),
        ]):
            raise serializers.ValidationError(
                "Must provide signature_id, verification_token, or document_id"
            )
        return data


class SignatureVerificationResultSerializer(serializers.Serializer):
    """Serializer for verification results."""

    is_valid = serializers.BooleanField()
    signature_id = serializers.UUIDField()
    document_id = serializers.UUIDField()
    signer_name = serializers.CharField()
    signer_email = serializers.CharField()
    signed_at = serializers.DateTimeField()
    signature_type = serializers.CharField()
    status = serializers.CharField()
    verification_message = serializers.CharField()
    certificate_info = serializers.DictField(required=False)


class SignatureRevokeSerializer(serializers.Serializer):
    """Serializer for revoking signatures."""

    reason = serializers.CharField(max_length=500, required=True)
