# services/certificate-service/src/apps/core/api/serializers/medical_serializers.py
"""
Medical Certificate Serializers

API serializers for medical certificate management.
"""

from rest_framework import serializers

from ...models import (
    MedicalCertificate,
    MedicalClass,
    MedicalStatus,
)


class MedicalCertificateSerializer(serializers.ModelSerializer):
    """Full medical certificate serializer."""

    medical_class_display = serializers.CharField(
        source='get_medical_class_display',
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
    applicable_privileges = serializers.ListField(
        source='get_applicable_privileges',
        read_only=True
    )

    class Meta:
        model = MedicalCertificate
        fields = [
            'id',
            'organization_id',
            'user_id',
            'medical_class',
            'medical_class_display',
            'issuing_authority',
            'issuing_country',
            'certificate_number',
            'ame_name',
            'ame_license_number',
            'ame_address',
            'ame_contact',
            'examination_date',
            'issue_date',
            'expiry_date',
            'pilot_age_at_exam',
            'pilot_birth_date',
            'status',
            'status_display',
            'limitations',
            'limitation_codes',
            'limitation_details',
            'document_url',
            'notes',
            'is_valid',
            'is_expired',
            'is_expiring_soon',
            'days_until_expiry',
            'expiry_status',
            'applicable_privileges',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'organization_id',
            'created_at',
            'updated_at',
        ]


class MedicalCertificateCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating medical certificates."""

    class Meta:
        model = MedicalCertificate
        fields = [
            'user_id',
            'medical_class',
            'issuing_authority',
            'issuing_country',
            'certificate_number',
            'ame_name',
            'ame_license_number',
            'ame_address',
            'ame_contact',
            'examination_date',
            'issue_date',
            'expiry_date',
            'pilot_age_at_exam',
            'pilot_birth_date',
            'limitations',
            'limitation_codes',
            'limitation_details',
            'document_url',
            'notes',
        ]

    def validate_medical_class(self, value):
        """Validate medical class."""
        if value not in MedicalClass.values:
            raise serializers.ValidationError(
                f'Invalid medical class. Must be one of: {MedicalClass.values}'
            )
        return value

    def validate(self, attrs):
        """Cross-field validation."""
        examination_date = attrs.get('examination_date')
        issue_date = attrs.get('issue_date')
        expiry_date = attrs.get('expiry_date')

        if issue_date and examination_date and issue_date < examination_date:
            raise serializers.ValidationError({
                'issue_date': 'Issue date cannot be before examination date'
            })

        if expiry_date and issue_date and expiry_date <= issue_date:
            raise serializers.ValidationError({
                'expiry_date': 'Expiry date must be after issue date'
            })

        return attrs


class MedicalCertificateListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for medical certificate lists."""

    medical_class_display = serializers.CharField(
        source='get_medical_class_display',
        read_only=True
    )
    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )
    days_until_expiry = serializers.IntegerField(read_only=True)
    is_valid = serializers.BooleanField(read_only=True)

    class Meta:
        model = MedicalCertificate
        fields = [
            'id',
            'user_id',
            'medical_class',
            'medical_class_display',
            'issuing_authority',
            'examination_date',
            'expiry_date',
            'status',
            'status_display',
            'limitation_codes',
            'days_until_expiry',
            'is_valid',
        ]


class MedicalValidityCheckSerializer(serializers.Serializer):
    """Serializer for medical validity check request."""

    user_id = serializers.UUIDField()
    required_class = serializers.ChoiceField(
        choices=MedicalClass.choices,
        required=False
    )


class MedicalValidityResponseSerializer(serializers.Serializer):
    """Serializer for medical validity check response."""

    is_valid = serializers.BooleanField()
    message = serializers.CharField()
    medical = serializers.DictField(allow_null=True)
    days_until_expiry = serializers.IntegerField(required=False)
