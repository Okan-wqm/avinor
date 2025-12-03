# services/certificate-service/src/apps/core/models/verification.py
"""
Verification Model

Certificate verification records and audit trail.
"""

import uuid
from datetime import date
from typing import Optional, Dict, Any

from django.db import models
from django.utils import timezone


class VerificationMethod(models.TextChoices):
    """Verification method choices."""
    DOCUMENT_CHECK = 'document_check', 'Document Check'
    AUTHORITY_VERIFICATION = 'authority_verification', 'Authority Verification'
    ONLINE_VERIFICATION = 'online_verification', 'Online Verification'
    THIRD_PARTY = 'third_party', 'Third Party Verification'
    SELF_DECLARATION = 'self_declaration', 'Self Declaration'
    AUTOMATIC = 'automatic', 'Automatic System Check'


class VerificationStatus(models.TextChoices):
    """Verification status choices."""
    PENDING = 'pending', 'Pending'
    IN_PROGRESS = 'in_progress', 'In Progress'
    VERIFIED = 'verified', 'Verified'
    FAILED = 'failed', 'Failed'
    EXPIRED = 'expired', 'Expired'
    NEEDS_REVIEW = 'needs_review', 'Needs Review'


class CertificateVerification(models.Model):
    """
    Certificate Verification record.

    Tracks verification attempts and results for certificates.
    Provides audit trail for compliance purposes.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    organization_id = models.UUIDField(db_index=True)

    # Certificate Reference
    certificate_id = models.UUIDField(
        db_index=True,
        help_text='Reference to the certificate being verified'
    )
    certificate_type = models.CharField(
        max_length=50,
        help_text='Type of certificate (for audit purposes)'
    )
    certificate_number = models.CharField(
        max_length=100,
        help_text='Certificate number at time of verification'
    )

    # User
    user_id = models.UUIDField(
        db_index=True,
        help_text='Certificate holder'
    )

    # Verification Details
    verification_method = models.CharField(
        max_length=50,
        choices=VerificationMethod.choices,
        db_index=True
    )
    status = models.CharField(
        max_length=30,
        choices=VerificationStatus.choices,
        default=VerificationStatus.PENDING,
        db_index=True
    )

    # Dates
    requested_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(blank=True, null=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    expires_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text='When this verification expires'
    )

    # Verifier
    verified_by = models.UUIDField(
        blank=True,
        null=True,
        help_text='User who performed verification'
    )
    verifier_name = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )
    verifier_role = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    # Authority Response (if authority verification)
    authority_name = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )
    authority_response = models.JSONField(
        default=dict,
        blank=True,
        help_text='Response from issuing authority'
    )
    authority_reference = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text='Authority verification reference number'
    )

    # Document Details (if document check)
    document_url = models.URLField(
        max_length=500,
        blank=True,
        null=True
    )
    document_hash = models.CharField(
        max_length=64,
        blank=True,
        null=True,
        help_text='SHA-256 hash of verified document'
    )
    document_pages_checked = models.PositiveIntegerField(
        default=0
    )

    # Verification Result
    is_valid = models.BooleanField(
        blank=True,
        null=True,
        help_text='Whether certificate was found valid'
    )
    validity_date = models.DateField(
        blank=True,
        null=True,
        help_text='Certificate validity date as verified'
    )

    # Issues Found
    issues = models.JSONField(
        default=list,
        blank=True,
        help_text='List of issues found during verification'
    )
    # Example:
    # [
    #     {"code": "EXPIRED", "message": "Certificate expired", "severity": "error"},
    #     {"code": "MISMATCH", "message": "Name mismatch", "severity": "warning"}
    # ]

    # Discrepancies
    discrepancies = models.JSONField(
        default=dict,
        blank=True,
        help_text='Any discrepancies found'
    )
    # Example:
    # {
    #     "name": {"expected": "John Doe", "actual": "John D Doe"},
    #     "expiry_date": {"expected": "2024-12-31", "actual": "2024-06-30"}
    # }

    # Notes
    notes = models.TextField(
        blank=True,
        null=True,
        help_text='Verification notes'
    )
    failure_reason = models.TextField(
        blank=True,
        null=True,
        help_text='Reason for verification failure'
    )

    # Metadata
    metadata = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(
        blank=True,
        null=True,
        help_text='IP address of verifier'
    )
    user_agent = models.CharField(
        max_length=500,
        blank=True,
        null=True
    )

    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'certificate_verifications'
        ordering = ['-requested_at']
        indexes = [
            models.Index(fields=['organization_id', 'certificate_id']),
            models.Index(fields=['user_id']),
            models.Index(fields=['status', 'verification_method']),
            models.Index(fields=['requested_at']),
        ]

    def __str__(self) -> str:
        return f"Verification {self.id} - {self.status}"

    @property
    def is_expired(self) -> bool:
        """Check if verification has expired."""
        if not self.expires_at:
            return False
        return self.expires_at < timezone.now()

    @property
    def duration_seconds(self) -> Optional[int]:
        """Calculate verification duration in seconds."""
        if not self.started_at or not self.completed_at:
            return None
        return int((self.completed_at - self.started_at).total_seconds())

    def start_verification(self, verifier_id: uuid.UUID, verifier_name: str) -> None:
        """Start the verification process."""
        self.status = VerificationStatus.IN_PROGRESS
        self.started_at = timezone.now()
        self.verified_by = verifier_id
        self.verifier_name = verifier_name
        self.save()

    def complete_verification(
        self,
        is_valid: bool,
        validity_date: Optional[date] = None,
        issues: Optional[list] = None,
        notes: Optional[str] = None
    ) -> None:
        """Complete the verification with result."""
        self.status = VerificationStatus.VERIFIED if is_valid else VerificationStatus.FAILED
        self.completed_at = timezone.now()
        self.is_valid = is_valid
        self.validity_date = validity_date
        if issues:
            self.issues = issues
        if notes:
            self.notes = notes
        self.save()

    def fail_verification(
        self,
        reason: str,
        issues: Optional[list] = None
    ) -> None:
        """Mark verification as failed."""
        self.status = VerificationStatus.FAILED
        self.completed_at = timezone.now()
        self.is_valid = False
        self.failure_reason = reason
        if issues:
            self.issues = issues
        self.save()

    def flag_for_review(self, reason: str) -> None:
        """Flag verification for manual review."""
        self.status = VerificationStatus.NEEDS_REVIEW
        self.notes = f"{self.notes or ''}\nFlagged for review: {reason}".strip()
        self.save()

    def get_summary(self) -> Dict[str, Any]:
        """Get verification summary."""
        return {
            'verification_id': str(self.id),
            'certificate_id': str(self.certificate_id),
            'certificate_type': self.certificate_type,
            'certificate_number': self.certificate_number,
            'verification_method': self.verification_method,
            'status': self.status,
            'is_valid': self.is_valid,
            'requested_at': self.requested_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'duration_seconds': self.duration_seconds,
            'verifier_name': self.verifier_name,
            'issues_count': len(self.issues) if self.issues else 0,
            'has_discrepancies': bool(self.discrepancies),
        }

    @classmethod
    def get_verification_statistics(
        cls,
        organization_id: uuid.UUID,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get verification statistics for organization."""
        from django.db.models import Count, Avg
        from datetime import timedelta

        cutoff = timezone.now() - timedelta(days=days)

        verifications = cls.objects.filter(
            organization_id=organization_id,
            requested_at__gte=cutoff
        )

        stats = verifications.aggregate(
            total=Count('id'),
        )

        by_status = verifications.values('status').annotate(
            count=Count('id')
        )

        by_method = verifications.values('verification_method').annotate(
            count=Count('id')
        )

        return {
            'period_days': days,
            'total_verifications': stats['total'],
            'by_status': {s['status']: s['count'] for s in by_status},
            'by_method': {m['verification_method']: m['count'] for m in by_method},
            'success_rate': (
                verifications.filter(is_valid=True).count() / stats['total'] * 100
                if stats['total'] > 0 else 0
            ),
        }
