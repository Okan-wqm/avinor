# services/certificate-service/src/apps/core/api/serializers/certificate_serializers.py
"""
Certificate Serializers

API serializers for certificate/license management.
"""

from rest_framework import serializers

from ...models import (
    Certificate,
    CertificateType,
    CertificateSubtype,
    CertificateStatus,
    IssuingAuthority,
)


class CertificateSerializer(serializers.ModelSerializer):
    """Full certificate serializer."""

    certificate_type_display = serializers.CharField(
        source='get_certificate_type_display',
        read_only=True
    )
    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )
    is_valid = serializers.BooleanField(read_only=True)
    is_expired = serializers.BooleanField(read_only=True)
    is_expiring_soon = serializers.BooleanField(read_only=True)
    days_until_expiry = serializers.IntegerField(read_only=True)
    expiry_status = serializers.CharField(read_only=True)

    class Meta:
        model = Certificate
        fields = [
            'id',
            'organization_id',
            'user_id',
            'certificate_type',
            'certificate_type_display',
            'certificate_subtype',
            'issuing_authority',
            'issuing_country',
            'certificate_number',
            'reference_number',
            'issue_date',
            'expiry_date',
            'first_issue_date',
            'status',
            'status_display',
            'restrictions',
            'limitations',
            'verified',
            'verified_at',
            'verified_by',
            'verification_method',
            'document_url',
            'notes',
            'is_valid',
            'is_expired',
            'is_expiring_soon',
            'days_until_expiry',
            'expiry_status',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'organization_id',
            'verified',
            'verified_at',
            'verified_by',
            'verification_method',
            'created_at',
            'updated_at',
        ]


class CertificateCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating certificates."""

    class Meta:
        model = Certificate
        fields = [
            'user_id',
            'certificate_type',
            'certificate_subtype',
            'issuing_authority',
            'issuing_country',
            'certificate_number',
            'reference_number',
            'issue_date',
            'expiry_date',
            'first_issue_date',
            'restrictions',
            'limitations',
            'document_url',
            'notes',
        ]

    def validate_certificate_type(self, value):
        """Validate certificate type."""
        if value not in CertificateType.values:
            raise serializers.ValidationError(
                f'Invalid certificate type. Must be one of: {CertificateType.values}'
            )
        return value

    def validate_issuing_authority(self, value):
        """Validate issuing authority."""
        if value not in IssuingAuthority.values:
            raise serializers.ValidationError(
                f'Invalid issuing authority. Must be one of: {IssuingAuthority.values}'
            )
        return value

    def validate(self, attrs):
        """Cross-field validation."""
        issue_date = attrs.get('issue_date')
        expiry_date = attrs.get('expiry_date')

        if expiry_date and issue_date and expiry_date <= issue_date:
            raise serializers.ValidationError({
                'expiry_date': 'Expiry date must be after issue date'
            })

        return attrs


class CertificateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating certificates."""

    class Meta:
        model = Certificate
        fields = [
            'certificate_subtype',
            'issuing_country',
            'reference_number',
            'expiry_date',
            'restrictions',
            'limitations',
            'document_url',
            'notes',
        ]


class CertificateListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for certificate lists."""

    certificate_type_display = serializers.CharField(
        source='get_certificate_type_display',
        read_only=True
    )
    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )
    days_until_expiry = serializers.IntegerField(read_only=True)
    is_valid = serializers.BooleanField(read_only=True)

    class Meta:
        model = Certificate
        fields = [
            'id',
            'user_id',
            'certificate_type',
            'certificate_type_display',
            'certificate_subtype',
            'issuing_authority',
            'certificate_number',
            'issue_date',
            'expiry_date',
            'status',
            'status_display',
            'verified',
            'days_until_expiry',
            'is_valid',
        ]


class CertificateVerifySerializer(serializers.Serializer):
    """Serializer for certificate verification request."""

    verification_method = serializers.ChoiceField(
        choices=[
            ('document_check', 'Document Check'),
            ('authority_verification', 'Authority Verification'),
            ('online_verification', 'Online Verification'),
        ]
    )
    notes = serializers.CharField(required=False, allow_blank=True)


class CertificateSuspendSerializer(serializers.Serializer):
    """Serializer for suspending a certificate."""

    reason = serializers.CharField(min_length=10)


class CertificateRevokeSerializer(serializers.Serializer):
    """Serializer for revoking a certificate."""

    reason = serializers.CharField(min_length=10)


class CertificateRenewSerializer(serializers.Serializer):
    """Serializer for renewing a certificate."""

    new_expiry_date = serializers.DateField()
    new_certificate_number = serializers.CharField(required=False)


class ExpiringCertificateSerializer(serializers.Serializer):
    """Serializer for expiring certificate info."""

    certificate_id = serializers.UUIDField()
    user_id = serializers.UUIDField()
    certificate_type = serializers.CharField()
    certificate_number = serializers.CharField()
    expiry_date = serializers.DateField()
    days_remaining = serializers.IntegerField()
    status = serializers.CharField()
