# services/certificate-service/src/apps/core/models/certificate.py
"""
Certificate Model

Main certificate/license model for pilots.
"""

import uuid
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional, Dict, Any, List

from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.core.validators import MinLengthValidator
from django.utils import timezone


class CertificateType(models.TextChoices):
    """Certificate type choices."""
    PILOT_LICENSE = 'pilot_license', 'Pilot License'
    MEDICAL = 'medical', 'Medical Certificate'
    LANGUAGE_PROFICIENCY = 'language_proficiency', 'Language Proficiency'
    INSTRUCTOR_CERTIFICATE = 'instructor_certificate', 'Instructor Certificate'
    EXAMINER_AUTHORIZATION = 'examiner_authorization', 'Examiner Authorization'
    RADIO_LICENSE = 'radio_license', 'Radio License'
    DANGEROUS_GOODS = 'dangerous_goods', 'Dangerous Goods'
    CREW_RESOURCE_MANAGEMENT = 'crew_resource_management', 'CRM'


class CertificateSubtype(models.TextChoices):
    """Certificate subtype choices."""
    # Pilot Licenses
    SPL = 'spl', 'Student Pilot License'
    PPL = 'ppl', 'Private Pilot License'
    CPL = 'cpl', 'Commercial Pilot License'
    ATPL = 'atpl', 'Airline Transport Pilot License'
    MPL = 'mpl', 'Multi-Crew Pilot License'
    LAPL = 'lapl', 'Light Aircraft Pilot License'
    # Instructor
    FI = 'fi', 'Flight Instructor'
    IRI = 'iri', 'Instrument Rating Instructor'
    CRI = 'cri', 'Class Rating Instructor'
    TRI = 'tri', 'Type Rating Instructor'
    # Language
    ICAO_LEVEL_4 = 'icao_4', 'ICAO Level 4'
    ICAO_LEVEL_5 = 'icao_5', 'ICAO Level 5'
    ICAO_LEVEL_6 = 'icao_6', 'ICAO Level 6'


class CertificateStatus(models.TextChoices):
    """Certificate status choices."""
    ACTIVE = 'active', 'Active'
    EXPIRED = 'expired', 'Expired'
    SUSPENDED = 'suspended', 'Suspended'
    REVOKED = 'revoked', 'Revoked'
    PENDING_RENEWAL = 'pending_renewal', 'Pending Renewal'
    PENDING_VERIFICATION = 'pending_verification', 'Pending Verification'


class IssuingAuthority(models.TextChoices):
    """Issuing authority choices."""
    EASA = 'easa', 'EASA (European Union Aviation Safety Agency)'
    FAA = 'faa', 'FAA (Federal Aviation Administration)'
    SHGM = 'shgm', 'SHGM (Sivil Havacılık Genel Müdürlüğü)'
    TCCA = 'tcca', 'TCCA (Transport Canada Civil Aviation)'
    CASA = 'casa', 'CASA (Civil Aviation Safety Authority)'
    CAA_UK = 'caa_uk', 'CAA UK (Civil Aviation Authority)'
    DGCA = 'dgca', 'DGCA (Directorate General of Civil Aviation)'
    CAAC = 'caac', 'CAAC (Civil Aviation Administration of China)'
    OTHER = 'other', 'Other'


class Certificate(models.Model):
    """
    Certificate/License model.

    Stores pilot licenses, instructor certificates, and other aviation certificates.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    organization_id = models.UUIDField(db_index=True)
    user_id = models.UUIDField(db_index=True)

    # Certificate Type
    certificate_type = models.CharField(
        max_length=50,
        choices=CertificateType.choices,
        db_index=True
    )
    certificate_subtype = models.CharField(
        max_length=50,
        choices=CertificateSubtype.choices,
        blank=True,
        null=True
    )

    # Issuing Information
    issuing_authority = models.CharField(
        max_length=50,
        choices=IssuingAuthority.choices
    )
    issuing_country = models.CharField(
        max_length=2,
        blank=True,
        null=True,
        help_text='ISO 3166-1 alpha-2 country code'
    )

    # Numbers
    certificate_number = models.CharField(
        max_length=100,
        validators=[MinLengthValidator(2)]
    )
    reference_number = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    # Dates
    issue_date = models.DateField()
    expiry_date = models.DateField(blank=True, null=True)
    first_issue_date = models.DateField(
        blank=True,
        null=True,
        help_text='Date of first issue (for renewals)'
    )

    # Status
    status = models.CharField(
        max_length=30,
        choices=CertificateStatus.choices,
        default=CertificateStatus.PENDING_VERIFICATION,
        db_index=True
    )

    # Restrictions
    restrictions = ArrayField(
        models.CharField(max_length=255),
        default=list,
        blank=True,
        help_text='List of restrictions/limitations'
    )
    limitations = models.TextField(
        blank=True,
        null=True,
        help_text='Detailed limitations text'
    )

    # Verification
    verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(blank=True, null=True)
    verified_by = models.UUIDField(blank=True, null=True)
    verification_method = models.CharField(
        max_length=50,
        blank=True,
        null=True
    )
    verification_notes = models.TextField(blank=True, null=True)

    # Document
    document_url = models.URLField(max_length=500, blank=True, null=True)
    document_filename = models.CharField(max_length=255, blank=True, null=True)
    document_uploaded_at = models.DateTimeField(blank=True, null=True)

    # Reminders
    reminder_days = ArrayField(
        models.IntegerField(),
        default=lambda: [90, 60, 30, 14, 7],
        help_text='Days before expiry to send reminders'
    )
    last_reminder_sent = models.DateTimeField(blank=True, null=True)
    next_reminder_date = models.DateField(blank=True, null=True)

    # Notes
    notes = models.TextField(blank=True, null=True)

    # Metadata
    metadata = models.JSONField(default=dict, blank=True)

    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.UUIDField(blank=True, null=True)

    class Meta:
        db_table = 'certificates'
        ordering = ['-issue_date']
        indexes = [
            models.Index(fields=['organization_id', 'user_id']),
            models.Index(fields=['certificate_type', 'status']),
            models.Index(fields=['expiry_date']),
            models.Index(fields=['issuing_authority']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['organization_id', 'user_id', 'certificate_type', 'certificate_number'],
                name='unique_certificate_per_user'
            )
        ]

    def __str__(self) -> str:
        return f"{self.get_certificate_type_display()}: {self.certificate_number}"

    @property
    def is_expired(self) -> bool:
        """Check if certificate is expired."""
        if not self.expiry_date:
            return False
        return self.expiry_date < date.today()

    @property
    def days_until_expiry(self) -> Optional[int]:
        """Calculate days until expiry."""
        if not self.expiry_date:
            return None
        return (self.expiry_date - date.today()).days

    @property
    def is_expiring_soon(self) -> bool:
        """Check if expiring within 90 days."""
        days = self.days_until_expiry
        if days is None:
            return False
        return 0 < days <= 90

    @property
    def is_valid(self) -> bool:
        """Check if certificate is valid for operations."""
        return (
            self.status == CertificateStatus.ACTIVE and
            self.verified and
            not self.is_expired
        )

    @property
    def expiry_status(self) -> str:
        """Get human-readable expiry status."""
        if not self.expiry_date:
            return 'No expiry'

        days = self.days_until_expiry
        if days < 0:
            return f'Expired {abs(days)} days ago'
        elif days == 0:
            return 'Expires today'
        elif days <= 7:
            return f'Expires in {days} days (critical)'
        elif days <= 30:
            return f'Expires in {days} days (warning)'
        elif days <= 90:
            return f'Expires in {days} days'
        else:
            return f'Valid for {days} days'

    def update_status(self) -> None:
        """Update status based on current state."""
        if self.status in [CertificateStatus.REVOKED, CertificateStatus.SUSPENDED]:
            return

        if self.is_expired:
            self.status = CertificateStatus.EXPIRED
        elif self.is_expiring_soon and self.status == CertificateStatus.ACTIVE:
            self.status = CertificateStatus.PENDING_RENEWAL
        elif not self.verified:
            self.status = CertificateStatus.PENDING_VERIFICATION

        self.save(update_fields=['status', 'updated_at'])

    def verify(
        self,
        verified_by: uuid.UUID,
        method: str,
        notes: Optional[str] = None
    ) -> None:
        """Mark certificate as verified."""
        self.verified = True
        self.verified_at = timezone.now()
        self.verified_by = verified_by
        self.verification_method = method
        self.verification_notes = notes

        if self.status == CertificateStatus.PENDING_VERIFICATION:
            self.status = CertificateStatus.ACTIVE

        self.save()

    def suspend(self, reason: str) -> None:
        """Suspend the certificate."""
        self.status = CertificateStatus.SUSPENDED
        self.notes = f"{self.notes or ''}\nSuspended: {reason}".strip()
        self.save()

    def revoke(self, reason: str) -> None:
        """Revoke the certificate."""
        self.status = CertificateStatus.REVOKED
        self.notes = f"{self.notes or ''}\nRevoked: {reason}".strip()
        self.save()

    def reinstate(self) -> None:
        """Reinstate a suspended certificate."""
        if self.status != CertificateStatus.SUSPENDED:
            raise ValueError('Can only reinstate suspended certificates')

        self.status = CertificateStatus.ACTIVE
        self.notes = f"{self.notes or ''}\nReinstated on {date.today()}".strip()
        self.save()

    def calculate_next_reminder(self) -> Optional[date]:
        """Calculate the next reminder date."""
        if not self.expiry_date or not self.reminder_days:
            return None

        today = date.today()
        for days in sorted(self.reminder_days, reverse=True):
            reminder_date = self.expiry_date - timedelta(days=days)
            if reminder_date > today:
                return reminder_date

        return None

    def get_validity_info(self) -> Dict[str, Any]:
        """Get detailed validity information."""
        return {
            'certificate_id': str(self.id),
            'certificate_type': self.certificate_type,
            'certificate_number': self.certificate_number,
            'status': self.status,
            'is_valid': self.is_valid,
            'is_verified': self.verified,
            'is_expired': self.is_expired,
            'is_expiring_soon': self.is_expiring_soon,
            'expiry_date': self.expiry_date.isoformat() if self.expiry_date else None,
            'days_until_expiry': self.days_until_expiry,
            'expiry_status': self.expiry_status,
            'restrictions': self.restrictions,
            'issuing_authority': self.issuing_authority,
        }
