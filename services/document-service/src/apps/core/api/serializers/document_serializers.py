# services/document-service/src/apps/core/api/serializers/document_serializers.py
"""
Document Serializers
"""

from rest_framework import serializers

from ...models import (
    Document,
    DocumentType,
    DocumentStatus,
    AccessLevel,
    ProcessingStatus,
)


class DocumentSerializer(serializers.ModelSerializer):
    """Base document serializer."""

    document_type_display = serializers.CharField(
        source='get_document_type_display',
        read_only=True
    )
    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )
    access_level_display = serializers.CharField(
        source='get_access_level_display',
        read_only=True
    )
    file_size_display = serializers.CharField(read_only=True)
    is_expired = serializers.BooleanField(read_only=True)
    days_until_expiry = serializers.IntegerField(read_only=True)

    class Meta:
        model = Document
        fields = [
            'id',
            'organization_id',
            'owner_id',
            'folder_id',
            'title',
            'description',
            'original_name',
            'document_type',
            'document_type_display',
            'status',
            'status_display',
            'access_level',
            'access_level_display',
            'file_extension',
            'mime_type',
            'file_size',
            'file_size_display',
            'checksum',
            'version',
            'is_latest_version',
            'thumbnail_path',
            'preview_path',
            'page_count',
            'expiry_date',
            'is_expired',
            'days_until_expiry',
            'related_entity_type',
            'related_entity_id',
            'tags',
            'view_count',
            'download_count',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'file_extension',
            'mime_type',
            'file_size',
            'checksum',
            'version',
            'is_latest_version',
            'thumbnail_path',
            'preview_path',
            'page_count',
            'view_count',
            'download_count',
            'created_at',
            'updated_at',
        ]


class DocumentListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for document lists."""

    document_type_display = serializers.CharField(
        source='get_document_type_display',
        read_only=True
    )
    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )
    file_size_display = serializers.CharField(read_only=True)
    is_expired = serializers.BooleanField(read_only=True)

    class Meta:
        model = Document
        fields = [
            'id',
            'title',
            'original_name',
            'document_type',
            'document_type_display',
            'status',
            'status_display',
            'file_extension',
            'file_size',
            'file_size_display',
            'thumbnail_path',
            'expiry_date',
            'is_expired',
            'version',
            'created_at',
            'updated_at',
        ]


class DocumentDetailSerializer(DocumentSerializer):
    """Full document details including processing info."""

    processing_status_display = serializers.CharField(
        source='get_processing_status_display',
        read_only=True
    )
    is_viewable = serializers.BooleanField(read_only=True)
    is_image = serializers.BooleanField(read_only=True)
    is_pdf = serializers.BooleanField(read_only=True)

    class Meta(DocumentSerializer.Meta):
        fields = DocumentSerializer.Meta.fields + [
            'file_path',
            'processing_status',
            'processing_status_display',
            'processing_error',
            'virus_scanned',
            'virus_scan_result',
            'virus_scanned_at',
            'ocr_completed',
            'ocr_text',
            'ocr_language',
            'ocr_confidence',
            'is_viewable',
            'is_image',
            'is_pdf',
            'parent_document_id',
            'uploaded_by',
            'last_accessed_at',
            'last_accessed_by',
            'deleted_at',
            'deleted_by',
        ]


class DocumentUploadSerializer(serializers.Serializer):
    """Serializer for document upload."""

    file = serializers.FileField(required=True)
    title = serializers.CharField(max_length=255, required=False, allow_blank=True)
    description = serializers.CharField(required=False, allow_blank=True)
    document_type = serializers.ChoiceField(
        choices=[(t.value, t.name) for t in DocumentType],
        required=True
    )
    folder_id = serializers.UUIDField(required=False, allow_null=True)
    access_level = serializers.ChoiceField(
        choices=[(a.value, a.name) for a in AccessLevel],
        default=AccessLevel.PRIVATE.value
    )
    expiry_date = serializers.DateField(required=False, allow_null=True)
    related_entity_type = serializers.CharField(
        max_length=50,
        required=False,
        allow_blank=True
    )
    related_entity_id = serializers.UUIDField(required=False, allow_null=True)
    tags = serializers.ListField(
        child=serializers.CharField(max_length=50),
        required=False,
        default=list
    )
    metadata = serializers.JSONField(required=False, default=dict)

    def validate_file(self, value):
        """Validate uploaded file."""
        # Max 100MB
        max_size = 100 * 1024 * 1024
        if value.size > max_size:
            raise serializers.ValidationError(
                f"File size ({value.size}) exceeds maximum allowed (100MB)"
            )

        # Check extension
        allowed_extensions = {
            'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx',
            'txt', 'csv', 'json', 'xml',
            'jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp', 'tiff', 'tif',
            'zip', 'rar', '7z',
        }

        ext = value.name.rsplit('.', 1)[-1].lower() if '.' in value.name else ''
        if ext and ext not in allowed_extensions:
            raise serializers.ValidationError(
                f"File type '{ext}' is not allowed"
            )

        return value


class DocumentUpdateSerializer(serializers.ModelSerializer):
    """Serializer for document updates."""

    class Meta:
        model = Document
        fields = [
            'title',
            'description',
            'document_type',
            'access_level',
            'folder_id',
            'expiry_date',
            'related_entity_type',
            'related_entity_id',
            'tags',
            'metadata',
        ]

    def validate(self, data):
        """Validate update data."""
        instance = self.instance

        # Cannot update deleted documents
        if instance and instance.status == DocumentStatus.DELETED:
            raise serializers.ValidationError(
                "Cannot update a deleted document"
            )

        return data


class DocumentVersionSerializer(serializers.Serializer):
    """Serializer for creating new document version."""

    file = serializers.FileField(required=True)
    change_notes = serializers.CharField(
        max_length=1000,
        required=False,
        allow_blank=True
    )

    def validate_file(self, value):
        """Validate that new version has same type."""
        instance = self.context.get('document')

        if instance:
            ext = value.name.rsplit('.', 1)[-1].lower() if '.' in value.name else ''
            if ext != instance.file_extension:
                raise serializers.ValidationError(
                    f"New version must have same file type as original "
                    f"({instance.file_extension})"
                )

        return value


class DocumentSearchSerializer(serializers.Serializer):
    """Serializer for document search parameters."""

    query = serializers.CharField(required=False, allow_blank=True)
    document_type = serializers.ChoiceField(
        choices=[(t.value, t.name) for t in DocumentType],
        required=False
    )
    document_types = serializers.ListField(
        child=serializers.ChoiceField(
            choices=[(t.value, t.name) for t in DocumentType]
        ),
        required=False
    )
    status = serializers.ChoiceField(
        choices=[(s.value, s.name) for s in DocumentStatus],
        required=False
    )
    folder_id = serializers.UUIDField(required=False, allow_null=True)
    include_subfolders = serializers.BooleanField(default=False)
    owner_id = serializers.UUIDField(required=False)
    related_entity_type = serializers.CharField(required=False)
    related_entity_id = serializers.UUIDField(required=False)
    tags = serializers.ListField(
        child=serializers.CharField(),
        required=False
    )
    expiring_within_days = serializers.IntegerField(
        min_value=1,
        max_value=365,
        required=False
    )
    expired = serializers.BooleanField(required=False)
    created_after = serializers.DateTimeField(required=False)
    created_before = serializers.DateTimeField(required=False)
    order_by = serializers.ChoiceField(
        choices=[
            'created_at', '-created_at',
            'updated_at', '-updated_at',
            'title', '-title',
            'original_name', '-original_name',
            'file_size', '-file_size',
            'expiry_date', '-expiry_date',
        ],
        default='-created_at'
    )
    page = serializers.IntegerField(min_value=1, default=1)
    page_size = serializers.IntegerField(min_value=1, max_value=100, default=20)


class DocumentMoveSerializer(serializers.Serializer):
    """Serializer for moving documents."""

    document_ids = serializers.ListField(
        child=serializers.UUIDField(),
        min_length=1,
        max_length=100
    )
    target_folder_id = serializers.UUIDField(allow_null=True)


class DocumentBulkActionSerializer(serializers.Serializer):
    """Serializer for bulk document actions."""

    document_ids = serializers.ListField(
        child=serializers.UUIDField(),
        min_length=1,
        max_length=100
    )
    action = serializers.ChoiceField(
        choices=['delete', 'archive', 'restore', 'move']
    )
    target_folder_id = serializers.UUIDField(
        required=False,
        allow_null=True,
        help_text="Required for 'move' action"
    )

    def validate(self, data):
        if data['action'] == 'move' and not data.get('target_folder_id'):
            raise serializers.ValidationError({
                'target_folder_id': "Required for move action"
            })
        return data
