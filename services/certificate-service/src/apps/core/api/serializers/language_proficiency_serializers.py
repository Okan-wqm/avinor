# services/certificate-service/src/apps/core/api/serializers/language_proficiency_serializers.py
"""
Language Proficiency API Serializers
"""

from rest_framework import serializers
from ...models import (
    LanguageProficiency,
    LanguageTestHistory,
    LanguageCode,
    ProficiencyLevel,
    LanguageProficiencyStatus,
)


class LanguageProficiencySerializer(serializers.ModelSerializer):
    """Serializer for LanguageProficiency model."""

    language_display = serializers.CharField(
        source='get_language_display',
        read_only=True
    )
    level_description = serializers.CharField(read_only=True)
    is_operational = serializers.BooleanField(read_only=True)
    is_valid = serializers.BooleanField(read_only=True)
    is_expired = serializers.BooleanField(read_only=True)
    is_expiring_soon = serializers.BooleanField(read_only=True)
    days_until_expiry = serializers.IntegerField(read_only=True)

    class Meta:
        model = LanguageProficiency
        fields = [
            'id',
            'organization_id',
            'user_id',
            'language',
            'language_display',
            'proficiency_level',
            'level_description',
            'pronunciation_level',
            'structure_level',
            'vocabulary_level',
            'fluency_level',
            'comprehension_level',
            'interaction_level',
            'test_date',
            'test_center',
            'test_center_code',
            'examiner_name',
            'examiner_id',
            'examiner_number',
            'issue_date',
            'expiry_date',
            'status',
            'certificate_number',
            'issuing_authority',
            'document_url',
            'verified',
            'verified_at',
            'is_operational',
            'is_valid',
            'is_expired',
            'is_expiring_soon',
            'days_until_expiry',
            'notes',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'proficiency_level',
            'expiry_date',
            'verified',
            'verified_at',
            'created_at',
            'updated_at',
        ]


class LanguageProficiencyCreateSerializer(serializers.Serializer):
    """Serializer for recording language proficiency test."""

    language = serializers.ChoiceField(choices=LanguageCode.choices)
    test_date = serializers.DateField()
    test_center = serializers.CharField(max_length=255)
    test_center_code = serializers.CharField(max_length=50, required=False, allow_blank=True)
    examiner_name = serializers.CharField(max_length=255)
    examiner_id = serializers.UUIDField(required=False, allow_null=True)
    examiner_number = serializers.CharField(max_length=50, required=False, allow_blank=True)

    # Component levels
    pronunciation_level = serializers.IntegerField(min_value=1, max_value=6)
    structure_level = serializers.IntegerField(min_value=1, max_value=6)
    vocabulary_level = serializers.IntegerField(min_value=1, max_value=6)
    fluency_level = serializers.IntegerField(min_value=1, max_value=6)
    comprehension_level = serializers.IntegerField(min_value=1, max_value=6)
    interaction_level = serializers.IntegerField(min_value=1, max_value=6)

    # Optional fields
    issuing_authority = serializers.CharField(max_length=100, required=False)
    certificate_number = serializers.CharField(max_length=100, required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)
    examiner_comments = serializers.CharField(required=False, allow_blank=True)
    areas_for_improvement = serializers.CharField(required=False, allow_blank=True)


class LanguageTestHistorySerializer(serializers.ModelSerializer):
    """Serializer for LanguageTestHistory model."""

    language_display = serializers.CharField(
        source='get_language_display',
        read_only=True
    )

    class Meta:
        model = LanguageTestHistory
        fields = [
            'id',
            'organization_id',
            'user_id',
            'language',
            'language_display',
            'test_date',
            'test_center',
            'examiner_name',
            'passed',
            'overall_level',
            'pronunciation_level',
            'structure_level',
            'vocabulary_level',
            'fluency_level',
            'comprehension_level',
            'interaction_level',
            'examiner_comments',
            'areas_for_improvement',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class LanguageProficiencyValiditySerializer(serializers.Serializer):
    """Serializer for language proficiency validity check."""

    is_valid = serializers.BooleanField()
    error_code = serializers.CharField(required=False, allow_null=True)
    message = serializers.CharField(required=False, allow_null=True)
    warning = serializers.CharField(required=False, allow_null=True)
    proficiency = LanguageProficiencySerializer(required=False, allow_null=True)


class LanguageProficiencyVerifySerializer(serializers.Serializer):
    """Serializer for verifying language proficiency."""

    notes = serializers.CharField(required=False, allow_blank=True)
