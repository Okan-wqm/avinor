# services/aircraft-service/src/apps/core/models/document.py
"""
Aircraft Document Model

Document management for aircraft records.
"""

import uuid
from datetime import date, timedelta
from typing import Optional

from django.db import models
from django.utils import timezone


class AircraftDocument(models.Model):
    """
    Aircraft document management model.

    Supports:
    - Various document types (registration, insurance, manuals, etc.)
    - Version control
    - Expiry tracking with reminders
    - Access control (public/private)
    """

    class DocumentType(models.TextChoices):
        REGISTRATION = 'registration', 'Registration Certificate'
        AIRWORTHINESS = 'airworthiness', 'Airworthiness Certificate'
        INSURANCE = 'insurance', 'Insurance Certificate'
        WEIGHT_BALANCE = 'weight_balance', 'Weight & Balance'
        POH = 'poh', "Pilot's Operating Handbook"
        AFM = 'afm', 'Aircraft Flight Manual'
        CHECKLIST = 'checklist', 'Checklist'
        MAINTENANCE_MANUAL = 'maintenance_manual', 'Maintenance Manual'
        PARTS_CATALOG = 'parts_catalog', 'Illustrated Parts Catalog'
        AD_COMPLIANCE = 'ad_compliance', 'AD Compliance'
        SB_COMPLIANCE = 'sb_compliance', 'Service Bulletin Compliance'
        INSPECTION = 'inspection', 'Inspection Report'
        LOGBOOK = 'logbook', 'Logbook Page'
        JOURNEY_LOG = 'journey_log', 'Journey Log'
        LEASE_AGREEMENT = 'lease_agreement', 'Lease Agreement'
        OTHER = 'other', 'Other'

    class FileType(models.TextChoices):
        PDF = 'pdf', 'PDF'
        IMAGE = 'image', 'Image'
        DOCUMENT = 'document', 'Document'
        SPREADSHEET = 'spreadsheet', 'Spreadsheet'
        OTHER = 'other', 'Other'

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    organization_id = models.UUIDField(db_index=True)
    aircraft = models.ForeignKey(
        'Aircraft',
        on_delete=models.CASCADE,
        related_name='documents'
    )

    # ==========================================================================
    # Document Information
    # ==========================================================================

    document_type = models.CharField(
        max_length=50,
        choices=DocumentType.choices
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)

    # ==========================================================================
    # File Information
    # ==========================================================================

    file_url = models.URLField(max_length=500)
    file_name = models.CharField(max_length=255, blank=True, null=True)
    file_size_bytes = models.BigIntegerField(blank=True, null=True)
    file_type = models.CharField(
        max_length=50,
        choices=FileType.choices,
        default=FileType.PDF
    )
    mime_type = models.CharField(max_length=100, blank=True, null=True)

    # ==========================================================================
    # Version Control
    # ==========================================================================

    version = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text='Document version (e.g., Rev A, v2.0)'
    )
    revision_date = models.DateField(
        blank=True,
        null=True,
        help_text='Date of this revision'
    )
    effective_date = models.DateField(
        blank=True,
        null=True,
        help_text='Date document becomes effective'
    )
    expiry_date = models.DateField(
        blank=True,
        null=True,
        help_text='Document expiration date'
    )
    supersedes = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='superseded_by',
        help_text='Previous version this document supersedes'
    )

    # ==========================================================================
    # Document Reference
    # ==========================================================================

    document_number = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text='Official document/certificate number'
    )
    issuing_authority = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text='Authority that issued the document'
    )

    # ==========================================================================
    # Status
    # ==========================================================================

    is_current = models.BooleanField(
        default=True,
        help_text='Is this the current/active version'
    )
    is_required = models.BooleanField(
        default=False,
        help_text='Is this document required for operations'
    )

    # ==========================================================================
    # Reminder Settings
    # ==========================================================================

    reminder_days = models.IntegerField(
        blank=True,
        null=True,
        help_text='Days before expiry to send reminder'
    )
    reminder_sent = models.BooleanField(default=False)
    reminder_sent_at = models.DateTimeField(blank=True, null=True)

    # ==========================================================================
    # Access Control
    # ==========================================================================

    is_public = models.BooleanField(
        default=False,
        help_text='Visible to all pilots assigned to aircraft'
    )
    is_downloadable = models.BooleanField(
        default=True,
        help_text='Can be downloaded by authorized users'
    )

    # ==========================================================================
    # Metadata
    # ==========================================================================

    tags = models.JSONField(
        default=list,
        blank=True,
        help_text='Tags for categorization'
    )
    metadata = models.JSONField(default=dict, blank=True)

    # ==========================================================================
    # Timestamps
    # ==========================================================================

    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.UUIDField(blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.UUIDField(blank=True, null=True)

    class Meta:
        db_table = 'aircraft_documents'
        ordering = ['aircraft', 'document_type', '-created_at']
        verbose_name = 'Aircraft Document'
        verbose_name_plural = 'Aircraft Documents'
        indexes = [
            models.Index(fields=['aircraft', 'document_type']),
            models.Index(fields=['expiry_date']),
            models.Index(fields=['is_current']),
        ]

    def __str__(self):
        return f"{self.aircraft.registration} - {self.title}"

    # ==========================================================================
    # Properties
    # ==========================================================================

    @property
    def is_expired(self) -> bool:
        """Check if document is expired."""
        if not self.expiry_date:
            return False
        return self.expiry_date < date.today()

    @property
    def days_until_expiry(self) -> Optional[int]:
        """Days until document expires."""
        if not self.expiry_date:
            return None
        delta = self.expiry_date - date.today()
        return delta.days

    @property
    def is_expiring_soon(self) -> bool:
        """Check if document is expiring within reminder period."""
        if not self.expiry_date or not self.reminder_days:
            return False
        days = self.days_until_expiry
        return days is not None and 0 < days <= self.reminder_days

    @property
    def needs_reminder(self) -> bool:
        """Check if reminder needs to be sent."""
        return self.is_expiring_soon and not self.reminder_sent

    @property
    def file_size_display(self) -> str:
        """Get human-readable file size."""
        if not self.file_size_bytes:
            return "Unknown"

        size = self.file_size_bytes
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

    # ==========================================================================
    # Methods
    # ==========================================================================

    def mark_as_superseded(self, new_document: 'AircraftDocument') -> None:
        """Mark this document as superseded by another."""
        self.is_current = False
        self.save(update_fields=['is_current', 'updated_at'])

    def send_reminder(self) -> None:
        """Mark reminder as sent."""
        self.reminder_sent = True
        self.reminder_sent_at = timezone.now()
        self.save(update_fields=['reminder_sent', 'reminder_sent_at', 'updated_at'])

    def reset_reminder(self) -> None:
        """Reset reminder status (for new expiry date)."""
        self.reminder_sent = False
        self.reminder_sent_at = None
        self.save(update_fields=['reminder_sent', 'reminder_sent_at', 'updated_at'])

    @classmethod
    def get_expiring_documents(
        cls,
        organization_id: uuid.UUID = None,
        days_ahead: int = 30
    ):
        """Get documents expiring within specified days."""
        future_date = date.today() + timedelta(days=days_ahead)

        queryset = cls.objects.filter(
            is_current=True,
            expiry_date__isnull=False,
            expiry_date__lte=future_date,
            expiry_date__gte=date.today()
        ).select_related('aircraft')

        if organization_id:
            queryset = queryset.filter(organization_id=organization_id)

        return queryset.order_by('expiry_date')

    @classmethod
    def get_expired_documents(cls, organization_id: uuid.UUID = None):
        """Get all expired documents that are still marked as current."""
        queryset = cls.objects.filter(
            is_current=True,
            expiry_date__lt=date.today()
        ).select_related('aircraft')

        if organization_id:
            queryset = queryset.filter(organization_id=organization_id)

        return queryset.order_by('expiry_date')

    @classmethod
    def get_missing_required_documents(
        cls,
        aircraft_id: uuid.UUID
    ) -> list:
        """Get list of required document types missing for an aircraft."""
        required_types = [
            cls.DocumentType.REGISTRATION,
            cls.DocumentType.AIRWORTHINESS,
            cls.DocumentType.INSURANCE,
            cls.DocumentType.WEIGHT_BALANCE,
        ]

        existing = cls.objects.filter(
            aircraft_id=aircraft_id,
            is_current=True,
            document_type__in=required_types
        ).values_list('document_type', flat=True)

        missing = [t for t in required_types if t not in existing]
        return missing
