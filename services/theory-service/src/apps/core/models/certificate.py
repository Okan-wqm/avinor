# services/theory-service/src/apps/core/models/certificate.py
"""
Certificate Models

Models for course completion certificates.
"""

import uuid
from typing import Dict, Any, Optional

from django.db import models
from django.utils import timezone

from .course import Course
from .enrollment import CourseEnrollment


class CertificateStatus(models.TextChoices):
    """Certificate status choices."""
    PENDING = 'pending', 'Pending Generation'
    GENERATED = 'generated', 'Generated'
    ISSUED = 'issued', 'Issued'
    REVOKED = 'revoked', 'Revoked'
    EXPIRED = 'expired', 'Expired'


class Certificate(models.Model):
    """
    Certificate model.

    Represents a certificate issued upon course completion.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    organization_id = models.UUIDField(db_index=True)

    # Relationships
    course = models.ForeignKey(
        Course,
        on_delete=models.PROTECT,
        related_name='certificates'
    )
    enrollment = models.ForeignKey(
        CourseEnrollment,
        on_delete=models.PROTECT,
        related_name='certificates'
    )
    user_id = models.UUIDField(db_index=True)

    # Certificate info
    certificate_number = models.CharField(max_length=100, unique=True)
    title = models.CharField(max_length=255)

    # Recipient info (snapshot at time of issue)
    recipient_name = models.CharField(max_length=255)
    recipient_email = models.EmailField(blank=True, default='')

    # Achievement details
    course_name = models.CharField(max_length=255)
    course_category = models.CharField(max_length=50)
    completion_date = models.DateField()
    score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True
    )
    grade = models.CharField(max_length=10, blank=True, default='')
    hours_completed = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True
    )

    # Validity
    valid_from = models.DateField()
    valid_until = models.DateField(null=True, blank=True)
    is_perpetual = models.BooleanField(default=True)

    # Status
    status = models.CharField(
        max_length=20,
        choices=CertificateStatus.choices,
        default=CertificateStatus.PENDING
    )

    # Document
    template_id = models.UUIDField(null=True, blank=True)
    pdf_url = models.URLField(max_length=500, blank=True, default='')
    thumbnail_url = models.URLField(max_length=500, blank=True, default='')

    # Verification
    verification_code = models.CharField(max_length=50, unique=True)
    verification_url = models.URLField(max_length=500, blank=True, default='')
    qr_code_url = models.URLField(max_length=500, blank=True, default='')

    # Blockchain (optional)
    blockchain_hash = models.CharField(max_length=255, blank=True, default='')
    blockchain_tx_id = models.CharField(max_length=255, blank=True, default='')

    # Digital signature
    signed_by = models.CharField(max_length=255, blank=True, default='')
    signature_title = models.CharField(max_length=255, blank=True, default='')
    digital_signature = models.TextField(blank=True, default='')

    # Sharing
    is_public = models.BooleanField(default=False)
    share_url = models.URLField(max_length=500, blank=True, default='')
    linkedin_added = models.BooleanField(default=False)

    # Access tracking
    view_count = models.IntegerField(default=0)
    download_count = models.IntegerField(default=0)
    last_verified_at = models.DateTimeField(null=True, blank=True)

    # Revocation
    revoked_at = models.DateTimeField(null=True, blank=True)
    revoked_by = models.UUIDField(null=True, blank=True)
    revocation_reason = models.TextField(blank=True, default='')

    # Metadata
    metadata = models.JSONField(default=dict, blank=True)

    # Audit
    issued_at = models.DateTimeField(null=True, blank=True)
    issued_by = models.UUIDField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'certificates'
        ordering = ['-issued_at']
        indexes = [
            models.Index(fields=['user_id']),
            models.Index(fields=['certificate_number']),
            models.Index(fields=['verification_code']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.certificate_number} - {self.recipient_name}"

    @property
    def is_valid(self) -> bool:
        """Check if certificate is currently valid."""
        if self.status in [CertificateStatus.REVOKED, CertificateStatus.EXPIRED]:
            return False

        if not self.is_perpetual and self.valid_until:
            if timezone.now().date() > self.valid_until:
                return False

        return True

    @property
    def days_until_expiry(self) -> Optional[int]:
        """Get days until certificate expires."""
        if self.is_perpetual or not self.valid_until:
            return None

        delta = self.valid_until - timezone.now().date()
        return max(0, delta.days)

    @classmethod
    def generate_certificate_number(cls, organization_id: str, course_code: str) -> str:
        """Generate a unique certificate number."""
        import hashlib
        import time

        base = f"{organization_id}-{course_code}-{time.time()}"
        hash_part = hashlib.sha256(base.encode()).hexdigest()[:8].upper()
        timestamp = int(time.time())

        return f"CERT-{course_code[:4].upper()}-{timestamp}-{hash_part}"

    @classmethod
    def generate_verification_code(cls) -> str:
        """Generate a unique verification code."""
        import secrets
        return secrets.token_urlsafe(16)

    def issue(self, issued_by: str = None) -> None:
        """Issue the certificate."""
        self.status = CertificateStatus.ISSUED
        self.issued_at = timezone.now()

        if issued_by:
            self.issued_by = issued_by

        self.save()

        # Update enrollment
        self.enrollment.certificate_issued = True
        self.enrollment.certificate_id = self.id
        self.enrollment.certificate_url = self.pdf_url
        self.enrollment.save()

    def revoke(self, reason: str, revoked_by: str = None) -> None:
        """Revoke the certificate."""
        self.status = CertificateStatus.REVOKED
        self.revoked_at = timezone.now()
        self.revocation_reason = reason

        if revoked_by:
            self.revoked_by = revoked_by

        self.save()

        # Update enrollment
        self.enrollment.certificate_issued = False
        self.enrollment.save()

    def expire(self) -> None:
        """Mark certificate as expired."""
        self.status = CertificateStatus.EXPIRED
        self.save()

    def record_view(self) -> None:
        """Record a certificate view."""
        self.view_count += 1
        self.save()

    def record_download(self) -> None:
        """Record a certificate download."""
        self.download_count += 1
        self.save()

    def record_verification(self) -> None:
        """Record a verification check."""
        self.last_verified_at = timezone.now()
        self.save()

    def verify(self) -> Dict[str, Any]:
        """Verify certificate and return details."""
        self.record_verification()

        return {
            'valid': self.is_valid,
            'certificate_number': self.certificate_number,
            'recipient_name': self.recipient_name,
            'course_name': self.course_name,
            'completion_date': self.completion_date.isoformat(),
            'status': self.status,
            'organization_id': str(self.organization_id),
            'issued_at': self.issued_at.isoformat() if self.issued_at else None,
            'valid_until': self.valid_until.isoformat() if self.valid_until else None,
            'revoked': self.status == CertificateStatus.REVOKED,
            'revocation_reason': self.revocation_reason if self.status == CertificateStatus.REVOKED else None,
        }

    def get_public_data(self) -> Dict[str, Any]:
        """Get publicly shareable certificate data."""
        return {
            'certificate_number': self.certificate_number,
            'title': self.title,
            'recipient_name': self.recipient_name,
            'course_name': self.course_name,
            'completion_date': self.completion_date.isoformat(),
            'score': float(self.score) if self.score else None,
            'grade': self.grade,
            'valid': self.is_valid,
            'verification_code': self.verification_code,
            'issued_at': self.issued_at.isoformat() if self.issued_at else None,
            'signed_by': self.signed_by,
            'signature_title': self.signature_title,
        }

    def get_linkedin_data(self) -> Dict[str, Any]:
        """Get data formatted for LinkedIn certification."""
        return {
            'name': self.course_name,
            'organization': str(self.organization_id),  # Would need org name
            'issueDate': {
                'year': self.completion_date.year,
                'month': self.completion_date.month
            },
            'expirationDate': {
                'year': self.valid_until.year,
                'month': self.valid_until.month
            } if self.valid_until else None,
            'certificationId': self.certificate_number,
            'certificationUrl': self.verification_url or self.share_url
        }
