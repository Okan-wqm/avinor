"""
Document Service Models.
"""
from django.db import models
from django.core.validators import MinValueValidator
from shared.common.mixins import UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin


class DocumentCategory(UUIDPrimaryKeyMixin, TimestampMixin, models.Model):
    """
    Categories for organizing documents.
    """
    organization_id = models.UUIDField()

    # Category details
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='subcategories'
    )

    # Icon/Color
    icon = models.CharField(max_length=50, blank=True)
    color = models.CharField(max_length=7, blank=True)  # Hex color

    # Status
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'document_categories'
        unique_together = ['organization_id', 'name']
        ordering = ['name']
        indexes = [
            models.Index(fields=['organization_id']),
        ]

    def __str__(self):
        return self.name


class Document(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, models.Model):
    """
    Documents with version control and access management.
    """
    class DocumentType(models.TextChoices):
        PDF = 'pdf', 'PDF Document'
        WORD = 'word', 'Word Document'
        EXCEL = 'excel', 'Excel Spreadsheet'
        POWERPOINT = 'powerpoint', 'PowerPoint Presentation'
        IMAGE = 'image', 'Image'
        VIDEO = 'video', 'Video'
        AUDIO = 'audio', 'Audio'
        TEXT = 'text', 'Text File'
        OTHER = 'other', 'Other'

    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        REVIEW = 'review', 'Under Review'
        APPROVED = 'approved', 'Approved'
        ARCHIVED = 'archived', 'Archived'

    class AccessLevel(models.TextChoices):
        PRIVATE = 'private', 'Private'
        INTERNAL = 'internal', 'Internal Only'
        PUBLIC = 'public', 'Public'

    organization_id = models.UUIDField()
    category = models.ForeignKey(
        DocumentCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='documents'
    )

    # Document details
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    document_number = models.CharField(max_length=50, blank=True)
    document_type = models.CharField(max_length=20, choices=DocumentType.choices)

    # Current version (denormalized for quick access)
    current_version_number = models.IntegerField(default=1)
    current_file_url = models.URLField()
    current_file_name = models.CharField(max_length=255)
    current_file_size_bytes = models.BigIntegerField(default=0)
    current_mime_type = models.CharField(max_length=100, default='application/pdf')

    # Ownership
    owner_id = models.UUIDField()  # User who created the document
    created_by_id = models.UUIDField()

    # Status
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    access_level = models.CharField(max_length=20, choices=AccessLevel.choices, default=AccessLevel.PRIVATE)

    # Tags
    tags = models.JSONField(default=list, blank=True)

    # Metadata
    metadata = models.JSONField(default=dict, blank=True)

    # References
    related_to_type = models.CharField(max_length=50, blank=True)  # student, aircraft, course, etc.
    related_to_id = models.UUIDField(null=True, blank=True)

    class Meta:
        db_table = 'documents'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organization_id']),
            models.Index(fields=['owner_id']),
            models.Index(fields=['status']),
            models.Index(fields=['document_number']),
            models.Index(fields=['related_to_type', 'related_to_id']),
        ]

    def __str__(self):
        return f"{self.title} (v{self.current_version_number})"


class DocumentVersion(UUIDPrimaryKeyMixin, TimestampMixin, models.Model):
    """
    Version history for documents.
    """
    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name='versions'
    )

    # Version details
    version_number = models.IntegerField()
    version_label = models.CharField(max_length=50, blank=True)  # e.g., "v1.0", "Draft 2"

    # File info
    file_url = models.URLField()
    file_name = models.CharField(max_length=255)
    file_size_bytes = models.BigIntegerField(default=0)
    mime_type = models.CharField(max_length=100, default='application/pdf')
    checksum = models.CharField(max_length=64, blank=True)  # SHA256

    # Change tracking
    uploaded_by_id = models.UUIDField()
    change_description = models.TextField(blank=True)

    # Status
    is_current = models.BooleanField(default=False)

    class Meta:
        db_table = 'document_versions'
        unique_together = ['document', 'version_number']
        ordering = ['-version_number']
        indexes = [
            models.Index(fields=['document']),
        ]

    def __str__(self):
        return f"{self.document.title} v{self.version_number}"


class DocumentShare(UUIDPrimaryKeyMixin, TimestampMixin, models.Model):
    """
    Document sharing and permissions.
    """
    class PermissionLevel(models.TextChoices):
        VIEW = 'view', 'View Only'
        DOWNLOAD = 'download', 'Can Download'
        EDIT = 'edit', 'Can Edit'
        ADMIN = 'admin', 'Full Control'

    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name='shares'
    )

    # Shared with
    shared_with_user_id = models.UUIDField(null=True, blank=True)
    shared_with_group_id = models.UUIDField(null=True, blank=True)
    shared_with_organization_id = models.UUIDField(null=True, blank=True)

    # Permissions
    permission_level = models.CharField(max_length=20, choices=PermissionLevel.choices, default=PermissionLevel.VIEW)

    # Sharing details
    shared_by_id = models.UUIDField()
    shared_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    # Public link
    public_token = models.CharField(max_length=64, unique=True, blank=True)
    is_public_link = models.BooleanField(default=False)
    require_password = models.BooleanField(default=False)
    password_hash = models.CharField(max_length=255, blank=True)

    # Tracking
    access_count = models.IntegerField(default=0)
    last_accessed = models.DateTimeField(null=True, blank=True)

    # Notes
    notes = models.TextField(blank=True)

    class Meta:
        db_table = 'document_shares'
        ordering = ['-shared_at']
        indexes = [
            models.Index(fields=['document']),
            models.Index(fields=['shared_with_user_id']),
            models.Index(fields=['public_token']),
        ]

    def __str__(self):
        if self.is_public_link:
            return f"Public link for {self.document.title}"
        return f"{self.document.title} shared with User {self.shared_with_user_id}"
