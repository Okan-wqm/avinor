# services/document-service/src/apps/core/models/document.py
"""
Document Model

Core document storage model with versioning, metadata, and security features.
"""

import uuid
import hashlib
from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.utils import timezone
from datetime import date
from decimal import Decimal


class DocumentType(models.TextChoices):
    """Document type classifications for flight training."""
    CERTIFICATE = 'certificate', 'Certificate'
    LICENSE = 'license', 'License'
    MEDICAL = 'medical', 'Medical Certificate'
    TRAINING_RECORD = 'training_record', 'Training Record'
    FLIGHT_LOG = 'flight_log', 'Flight Log'
    MAINTENANCE = 'maintenance', 'Maintenance Document'
    INSURANCE = 'insurance', 'Insurance Document'
    MANUAL = 'manual', 'Manual / Handbook'
    CHECKLIST = 'checklist', 'Checklist'
    FORM = 'form', 'Form'
    REPORT = 'report', 'Report'
    INVOICE = 'invoice', 'Invoice'
    CONTRACT = 'contract', 'Contract'
    ENDORSEMENT = 'endorsement', 'Endorsement'
    EXAM_RESULT = 'exam_result', 'Exam Result'
    WEIGHT_BALANCE = 'weight_balance', 'Weight & Balance'
    POH = 'poh', 'Pilot Operating Handbook'
    AD_SB = 'ad_sb', 'AD/SB Document'
    OTHER = 'other', 'Other'


class DocumentStatus(models.TextChoices):
    """Document lifecycle status."""
    ACTIVE = 'active', 'Active'
    ARCHIVED = 'archived', 'Archived'
    DELETED = 'deleted', 'Deleted'
    PENDING_REVIEW = 'pending_review', 'Pending Review'
    REJECTED = 'rejected', 'Rejected'


class AccessLevel(models.TextChoices):
    """Access control levels."""
    PUBLIC = 'public', 'Public'
    ORGANIZATION = 'organization', 'Organization Only'
    PRIVATE = 'private', 'Private (Owner Only)'
    RESTRICTED = 'restricted', 'Restricted (Specific Users)'


class ProcessingStatus(models.TextChoices):
    """Document processing pipeline status."""
    PENDING = 'pending', 'Pending'
    UPLOADING = 'uploading', 'Uploading'
    PROCESSING = 'processing', 'Processing'
    SCANNING = 'scanning', 'Virus Scanning'
    OCR_PROCESSING = 'ocr_processing', 'OCR Processing'
    GENERATING_THUMBNAIL = 'generating_thumbnail', 'Generating Thumbnail'
    COMPLETED = 'completed', 'Completed'
    FAILED = 'failed', 'Failed'


class Document(models.Model):
    """
    Core document model for file storage and management.

    Supports:
    - Multi-tenant isolation via organization_id
    - Version control with parent document reference
    - Full-text search via OCR
    - Digital signatures
    - Expiry tracking for compliance documents
    - Access control at multiple levels
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    organization_id = models.UUIDField(db_index=True)

    # =========================================================================
    # FILE INFORMATION
    # =========================================================================
    file_name = models.CharField(
        max_length=255,
        help_text="Stored file name (may be UUID-based)"
    )
    original_name = models.CharField(
        max_length=255,
        help_text="Original uploaded file name"
    )
    file_path = models.CharField(
        max_length=500,
        help_text="Full storage path (S3/MinIO key)"
    )
    file_size = models.BigIntegerField(
        help_text="File size in bytes"
    )
    mime_type = models.CharField(
        max_length=100,
        help_text="MIME type of the file"
    )
    file_extension = models.CharField(
        max_length=20,
        blank=True,
        null=True
    )

    # =========================================================================
    # CATEGORIZATION
    # =========================================================================
    document_type = models.CharField(
        max_length=50,
        choices=DocumentType.choices,
        db_index=True
    )
    category = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Custom category within document type"
    )
    subcategory = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )
    tags = ArrayField(
        models.CharField(max_length=50),
        default=list,
        blank=True,
        help_text="Searchable tags for filtering"
    )

    # =========================================================================
    # OWNERSHIP & RELATIONSHIPS
    # =========================================================================
    owner_id = models.UUIDField(
        db_index=True,
        help_text="User who owns/uploaded the document"
    )
    owner_type = models.CharField(
        max_length=20,
        default='user'
    )

    folder = models.ForeignKey(
        'DocumentFolder',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='documents'
    )

    # Related entity (polymorphic reference to other services)
    related_entity_type = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        db_index=True,
        help_text="Type of related entity: user, aircraft, flight, booking, etc."
    )
    related_entity_id = models.UUIDField(
        blank=True,
        null=True,
        db_index=True
    )

    # =========================================================================
    # METADATA
    # =========================================================================
    title = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )
    description = models.TextField(
        blank=True,
        null=True
    )

    # Important dates
    document_date = models.DateField(
        blank=True,
        null=True,
        help_text="Date on the document itself"
    )
    expiry_date = models.DateField(
        blank=True,
        null=True,
        db_index=True,
        help_text="Expiration date for compliance tracking"
    )

    # =========================================================================
    # VERSION CONTROL
    # =========================================================================
    version = models.PositiveIntegerField(default=1)
    parent_document = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='versions'
    )
    is_latest_version = models.BooleanField(
        default=True,
        db_index=True
    )
    version_notes = models.TextField(
        blank=True,
        null=True,
        help_text="Notes about changes in this version"
    )

    # =========================================================================
    # STATUS
    # =========================================================================
    status = models.CharField(
        max_length=20,
        choices=DocumentStatus.choices,
        default=DocumentStatus.ACTIVE,
        db_index=True
    )

    processing_status = models.CharField(
        max_length=20,
        choices=ProcessingStatus.choices,
        default=ProcessingStatus.PENDING
    )
    processing_error = models.TextField(
        blank=True,
        null=True
    )

    # =========================================================================
    # OCR & TEXT EXTRACTION
    # =========================================================================
    ocr_text = models.TextField(
        blank=True,
        null=True,
        help_text="Extracted text from OCR processing"
    )
    ocr_completed = models.BooleanField(default=False)
    ocr_language = models.CharField(
        max_length=10,
        default='eng',
        help_text="OCR language code"
    )
    ocr_confidence = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="OCR confidence score (0-100)"
    )

    # =========================================================================
    # SECURITY
    # =========================================================================
    is_confidential = models.BooleanField(default=False)
    access_level = models.CharField(
        max_length=20,
        choices=AccessLevel.choices,
        default=AccessLevel.ORGANIZATION
    )

    encryption_key_id = models.UUIDField(
        null=True,
        blank=True,
        help_text="Reference to encryption key if encrypted at rest"
    )
    is_encrypted = models.BooleanField(default=False)

    # =========================================================================
    # INTEGRITY & SECURITY SCANNING
    # =========================================================================
    checksum = models.CharField(
        max_length=64,
        blank=True,
        null=True,
        help_text="SHA-256 checksum of file content"
    )
    checksum_algorithm = models.CharField(
        max_length=20,
        default='sha256'
    )

    virus_scanned = models.BooleanField(default=False)
    virus_scan_result = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="clean, infected, error"
    )
    virus_scan_details = models.TextField(
        blank=True,
        null=True
    )
    virus_scanned_at = models.DateTimeField(
        null=True,
        blank=True
    )

    # =========================================================================
    # SIGNATURE STATUS
    # =========================================================================
    is_signed = models.BooleanField(default=False)
    signature_count = models.PositiveIntegerField(default=0)
    requires_signature = models.BooleanField(
        default=False,
        help_text="Whether this document requires signing"
    )
    signature_deadline = models.DateTimeField(
        null=True,
        blank=True
    )

    # =========================================================================
    # VISUAL ASSETS
    # =========================================================================
    thumbnail_path = models.CharField(
        max_length=500,
        blank=True,
        null=True
    )
    preview_path = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        help_text="Path to preview image/PDF"
    )
    page_count = models.PositiveIntegerField(
        null=True,
        blank=True
    )

    # =========================================================================
    # STATISTICS
    # =========================================================================
    view_count = models.PositiveIntegerField(default=0)
    download_count = models.PositiveIntegerField(default=0)
    last_viewed_at = models.DateTimeField(null=True, blank=True)
    last_downloaded_at = models.DateTimeField(null=True, blank=True)

    # =========================================================================
    # AUDIT
    # =========================================================================
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.UUIDField(null=True, blank=True)
    updated_by = models.UUIDField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.UUIDField(null=True, blank=True)

    class Meta:
        db_table = 'documents'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organization_id', 'document_type']),
            models.Index(fields=['organization_id', 'owner_id']),
            models.Index(fields=['related_entity_type', 'related_entity_id']),
            models.Index(fields=['expiry_date']),
            models.Index(fields=['organization_id', 'status', 'is_latest_version']),
        ]

    def __str__(self):
        return self.title or self.original_name

    # =========================================================================
    # PROPERTIES
    # =========================================================================

    @property
    def is_expired(self) -> bool:
        """Check if document has expired."""
        if not self.expiry_date:
            return False
        return self.expiry_date < date.today()

    @property
    def days_until_expiry(self) -> int | None:
        """Days until document expires, negative if already expired."""
        if not self.expiry_date:
            return None
        return (self.expiry_date - date.today()).days

    @property
    def file_size_display(self) -> str:
        """Human-readable file size."""
        size = float(self.file_size)
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} PB"

    @property
    def is_image(self) -> bool:
        """Check if document is an image."""
        return self.mime_type.startswith('image/')

    @property
    def is_pdf(self) -> bool:
        """Check if document is a PDF."""
        return self.mime_type == 'application/pdf'

    @property
    def is_viewable(self) -> bool:
        """Check if document can be previewed in browser."""
        viewable_types = [
            'image/jpeg', 'image/png', 'image/gif', 'image/webp',
            'application/pdf', 'text/plain', 'text/html'
        ]
        return self.mime_type in viewable_types

    @property
    def needs_processing(self) -> bool:
        """Check if document still needs processing."""
        return self.processing_status not in [
            ProcessingStatus.COMPLETED,
            ProcessingStatus.FAILED
        ]

    @property
    def is_safe(self) -> bool:
        """Check if document passed virus scan."""
        return self.virus_scanned and self.virus_scan_result == 'clean'

    # =========================================================================
    # METHODS
    # =========================================================================

    def record_view(self, user_id: uuid.UUID = None) -> None:
        """Record a document view."""
        self.view_count += 1
        self.last_viewed_at = timezone.now()
        self.save(update_fields=['view_count', 'last_viewed_at'])

    def record_download(self, user_id: uuid.UUID = None) -> None:
        """Record a document download."""
        self.download_count += 1
        self.last_downloaded_at = timezone.now()
        self.save(update_fields=['download_count', 'last_downloaded_at'])

    def soft_delete(self, deleted_by: uuid.UUID = None) -> None:
        """Soft delete the document."""
        self.status = DocumentStatus.DELETED
        self.deleted_at = timezone.now()
        self.deleted_by = deleted_by
        self.save(update_fields=['status', 'deleted_at', 'deleted_by'])

    def archive(self) -> None:
        """Archive the document."""
        self.status = DocumentStatus.ARCHIVED
        self.save(update_fields=['status', 'updated_at'])

    def restore(self) -> None:
        """Restore a deleted or archived document."""
        self.status = DocumentStatus.ACTIVE
        self.deleted_at = None
        self.deleted_by = None
        self.save(update_fields=['status', 'deleted_at', 'deleted_by', 'updated_at'])

    def calculate_checksum(self, content: bytes) -> str:
        """Calculate SHA-256 checksum of content."""
        return hashlib.sha256(content).hexdigest()

    def mark_as_latest_version(self) -> None:
        """Mark this document as the latest version and unmark siblings."""
        if self.parent_document:
            # Unmark all other versions
            Document.objects.filter(
                parent_document=self.parent_document,
                is_latest_version=True
            ).exclude(id=self.id).update(is_latest_version=False)

        self.is_latest_version = True
        self.save(update_fields=['is_latest_version'])
