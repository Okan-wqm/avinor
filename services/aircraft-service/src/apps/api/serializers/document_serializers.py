# services/aircraft-service/src/apps/api/serializers/document_serializers.py
"""
Document Serializers

Serializers for aircraft document management.
"""

from rest_framework import serializers

from apps.core.models import AircraftDocument


class DocumentListSerializer(serializers.ModelSerializer):
    """Serializer for document list view."""

    document_type_display = serializers.CharField(
        source='get_document_type_display', read_only=True
    )
    file_type_display = serializers.CharField(
        source='get_file_type_display', read_only=True
    )
    file_size_display = serializers.CharField(read_only=True)
    is_expired = serializers.BooleanField(read_only=True)
    days_until_expiry = serializers.IntegerField(read_only=True)
    is_expiring_soon = serializers.BooleanField(read_only=True)

    class Meta:
        model = AircraftDocument
        fields = [
            'id', 'aircraft', 'document_type', 'document_type_display',
            'title', 'file_url', 'file_name', 'file_type', 'file_type_display',
            'file_size_display', 'version',
            'expiry_date', 'is_expired', 'days_until_expiry', 'is_expiring_soon',
            'is_current', 'is_required',
            'created_at',
        ]


class DocumentDetailSerializer(serializers.ModelSerializer):
    """Serializer for document detail view."""

    document_type_display = serializers.CharField(
        source='get_document_type_display', read_only=True
    )
    file_type_display = serializers.CharField(
        source='get_file_type_display', read_only=True
    )
    file_size_display = serializers.CharField(read_only=True)
    is_expired = serializers.BooleanField(read_only=True)
    days_until_expiry = serializers.IntegerField(read_only=True)
    is_expiring_soon = serializers.BooleanField(read_only=True)
    needs_reminder = serializers.BooleanField(read_only=True)

    class Meta:
        model = AircraftDocument
        fields = [
            'id', 'organization_id', 'aircraft',

            # Document info
            'document_type', 'document_type_display',
            'title', 'description',

            # File info
            'file_url', 'file_name', 'file_size_bytes', 'file_size_display',
            'file_type', 'file_type_display', 'mime_type',

            # Version control
            'version', 'revision_date', 'effective_date',
            'expiry_date', 'supersedes',

            # Status
            'is_expired', 'days_until_expiry', 'is_expiring_soon',
            'is_current', 'is_required',

            # Reference
            'document_number', 'issuing_authority',

            # Reminder
            'reminder_days', 'reminder_sent', 'reminder_sent_at', 'needs_reminder',

            # Access
            'is_public', 'is_downloadable',

            # Metadata
            'tags', 'metadata',

            # Timestamps
            'created_at', 'created_by', 'updated_at', 'updated_by',
        ]
        read_only_fields = [
            'id', 'organization_id',
            'is_expired', 'days_until_expiry', 'is_expiring_soon',
            'needs_reminder', 'reminder_sent', 'reminder_sent_at',
            'created_at', 'updated_at',
        ]


class DocumentCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a document."""

    class Meta:
        model = AircraftDocument
        fields = [
            'document_type', 'title', 'description',
            'file_url', 'file_name', 'file_size_bytes', 'file_type', 'mime_type',
            'version', 'revision_date', 'effective_date', 'expiry_date',
            'document_number', 'issuing_authority',
            'is_required', 'reminder_days',
            'is_public', 'is_downloadable',
            'tags', 'metadata',
        ]

    def validate_document_type(self, value):
        valid_types = [choice[0] for choice in AircraftDocument.DocumentType.choices]
        if value not in valid_types:
            raise serializers.ValidationError(
                f"Invalid document type. Must be one of: {', '.join(valid_types)}"
            )
        return value

    def validate_file_url(self, value):
        if not value.startswith(('http://', 'https://', 's3://')):
            raise serializers.ValidationError(
                "File URL must be a valid HTTP(S) or S3 URL"
            )
        return value

    def validate(self, attrs):
        """Validate document data."""
        # Reminder days should be positive if set
        reminder_days = attrs.get('reminder_days')
        if reminder_days is not None and reminder_days < 0:
            raise serializers.ValidationError({
                'reminder_days': "Reminder days must be positive"
            })

        # If expiry date and reminder days, validate logic
        expiry_date = attrs.get('expiry_date')
        if expiry_date and reminder_days:
            from datetime import date, timedelta
            if expiry_date - timedelta(days=reminder_days) < date.today():
                # Expiry is sooner than reminder period - that's okay, just noting
                pass

        return attrs


class DocumentUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating a document."""

    class Meta:
        model = AircraftDocument
        fields = [
            'title', 'description',
            'version', 'revision_date', 'effective_date', 'expiry_date',
            'document_number', 'issuing_authority',
            'is_required', 'reminder_days',
            'is_public', 'is_downloadable',
            'tags', 'metadata',
        ]


class DocumentComplianceSerializer(serializers.Serializer):
    """Serializer for document compliance response."""

    aircraft_id = serializers.UUIDField()
    registration = serializers.CharField()
    is_compliant = serializers.BooleanField()

    missing_documents = serializers.ListField(
        child=serializers.DictField()
    )
    expired_documents = serializers.ListField(
        child=serializers.DictField()
    )
    expiring_soon = serializers.ListField(
        child=serializers.DictField()
    )

    checked_at = serializers.DateTimeField()
