# services/theory-service/src/apps/core/api/serializers/certificate_serializers.py
"""
Certificate Serializers

Serializers for certificate-related API endpoints.
"""

from rest_framework import serializers

from ...models import (
    Certificate,
    CertificateStatus,
)


class CertificateListSerializer(serializers.ModelSerializer):
    """Serializer for certificate list view."""

    is_valid = serializers.ReadOnlyField()
    days_until_expiry = serializers.ReadOnlyField()

    class Meta:
        model = Certificate
        fields = [
            'id',
            'certificate_number',
            'title',
            'course_name',
            'recipient_name',
            'completion_date',
            'score',
            'grade',
            'status',
            'is_valid',
            'is_perpetual',
            'valid_until',
            'days_until_expiry',
            'pdf_url',
            'thumbnail_url',
            'is_public',
            'issued_at',
        ]


class CertificateDetailSerializer(serializers.ModelSerializer):
    """Serializer for certificate detail view."""

    is_valid = serializers.ReadOnlyField()
    days_until_expiry = serializers.ReadOnlyField()

    class Meta:
        model = Certificate
        fields = [
            'id',
            'organization_id',
            'course',
            'enrollment',
            'user_id',
            'certificate_number',
            'title',
            'recipient_name',
            'recipient_email',
            'course_name',
            'course_category',
            'completion_date',
            'score',
            'grade',
            'hours_completed',
            'valid_from',
            'valid_until',
            'is_perpetual',
            'is_valid',
            'days_until_expiry',
            'status',
            'template_id',
            'pdf_url',
            'thumbnail_url',
            'verification_code',
            'verification_url',
            'qr_code_url',
            'blockchain_hash',
            'blockchain_tx_id',
            'signed_by',
            'signature_title',
            'is_public',
            'share_url',
            'linkedin_added',
            'view_count',
            'download_count',
            'last_verified_at',
            'revoked_at',
            'revocation_reason',
            'metadata',
            'issued_at',
            'issued_by',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id', 'organization_id', 'certificate_number', 'verification_code',
            'view_count', 'download_count', 'last_verified_at', 'revoked_at',
            'issued_at', 'issued_by', 'created_at', 'updated_at'
        ]


class CertificateGenerateSerializer(serializers.Serializer):
    """Serializer for generating certificates."""

    enrollment_id = serializers.UUIDField()
    recipient_name = serializers.CharField(max_length=255)
    recipient_email = serializers.EmailField(required=False, allow_blank=True)
    template_id = serializers.UUIDField(required=False, allow_null=True)
    signed_by = serializers.CharField(max_length=255, required=False, allow_blank=True)
    signature_title = serializers.CharField(max_length=255, required=False, allow_blank=True)
    valid_years = serializers.IntegerField(required=False, allow_null=True)


class CertificateIssueSerializer(serializers.Serializer):
    """Serializer for issuing a certificate."""

    # No fields needed, just triggers issue action
    pass


class CertificateRevokeSerializer(serializers.Serializer):
    """Serializer for revoking a certificate."""

    reason = serializers.CharField()


class CertificateVerifySerializer(serializers.Serializer):
    """Serializer for certificate verification request."""

    verification_code = serializers.CharField(required=False)
    certificate_number = serializers.CharField(required=False)

    def validate(self, data):
        """Ensure at least one identifier is provided."""
        if not data.get('verification_code') and not data.get('certificate_number'):
            raise serializers.ValidationError(
                "Must provide either verification_code or certificate_number"
            )
        return data


class CertificateVerifyResponseSerializer(serializers.Serializer):
    """Serializer for certificate verification response."""

    valid = serializers.BooleanField()
    certificate_number = serializers.CharField(allow_null=True)
    recipient_name = serializers.CharField(allow_null=True)
    course_name = serializers.CharField(allow_null=True)
    completion_date = serializers.DateField(allow_null=True)
    status = serializers.CharField(allow_null=True)
    organization_id = serializers.UUIDField(allow_null=True)
    issued_at = serializers.DateTimeField(allow_null=True)
    valid_until = serializers.DateField(allow_null=True)
    revoked = serializers.BooleanField(allow_null=True)
    revocation_reason = serializers.CharField(allow_null=True)
    error = serializers.CharField(required=False, allow_null=True)


class CertificatePublicSerializer(serializers.Serializer):
    """Serializer for publicly viewable certificate data."""

    certificate_number = serializers.CharField()
    title = serializers.CharField()
    recipient_name = serializers.CharField()
    course_name = serializers.CharField()
    completion_date = serializers.DateField()
    score = serializers.FloatField(allow_null=True)
    grade = serializers.CharField(allow_blank=True)
    valid = serializers.BooleanField()
    verification_code = serializers.CharField()
    issued_at = serializers.DateTimeField(allow_null=True)
    signed_by = serializers.CharField(allow_blank=True)
    signature_title = serializers.CharField(allow_blank=True)


class CertificateUpdateDocumentSerializer(serializers.Serializer):
    """Serializer for updating certificate document URLs."""

    pdf_url = serializers.URLField(required=False)
    thumbnail_url = serializers.URLField(required=False)
    qr_code_url = serializers.URLField(required=False)
    share_url = serializers.URLField(required=False)
    verification_url = serializers.URLField(required=False)


class LinkedInDataSerializer(serializers.Serializer):
    """Serializer for LinkedIn certification data."""

    name = serializers.CharField()
    organization = serializers.CharField()
    issueDate = serializers.DictField()
    expirationDate = serializers.DictField(allow_null=True)
    certificationId = serializers.CharField()
    certificationUrl = serializers.URLField()


class UserCertificatesSerializer(serializers.Serializer):
    """Serializer for user's certificates list."""

    id = serializers.UUIDField()
    certificate_number = serializers.CharField()
    title = serializers.CharField()
    course_name = serializers.CharField()
    completion_date = serializers.DateField()
    score = serializers.FloatField(allow_null=True)
    grade = serializers.CharField()
    is_valid = serializers.BooleanField()
    pdf_url = serializers.URLField(allow_blank=True)
    verification_url = serializers.URLField(allow_blank=True)
    is_public = serializers.BooleanField()
