# services/document-service/src/apps/core/models/signature.py
"""
Document Signature Model

Digital signature support with multiple signature types and verification.
"""

import uuid
from django.db import models
from django.utils import timezone


class SignatureType(models.TextChoices):
    """Types of digital signatures."""
    DRAWN = 'drawn', 'Hand-drawn Signature'
    TYPED = 'typed', 'Typed Name'
    UPLOADED = 'uploaded', 'Uploaded Image'
    CERTIFICATE = 'certificate', 'PKI Certificate'
    BIOMETRIC = 'biometric', 'Biometric Signature'


class SignatureStatus(models.TextChoices):
    """Signature validation status."""
    VALID = 'valid', 'Valid'
    REVOKED = 'revoked', 'Revoked'
    EXPIRED = 'expired', 'Expired'
    INVALID = 'invalid', 'Invalid'
    PENDING = 'pending', 'Pending Verification'


class DocumentSignature(models.Model):
    """
    Digital signature attached to a document.

    Supports:
    - Multiple signature types (drawn, typed, certificate-based)
    - Position tracking for PDF embedding
    - IP/geolocation audit trail
    - RFC 3161 timestamp tokens
    - PKI certificate validation
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    organization_id = models.UUIDField(db_index=True)

    document = models.ForeignKey(
        'Document',
        on_delete=models.CASCADE,
        related_name='signatures'
    )

    # =========================================================================
    # SIGNER INFORMATION
    # =========================================================================
    signer_id = models.UUIDField(db_index=True)
    signer_name = models.CharField(max_length=255)
    signer_email = models.EmailField(blank=True, null=True)
    signer_title = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Job title or role"
    )
    signer_role = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Role in context of this document (e.g., Instructor, Examiner)"
    )

    # =========================================================================
    # SIGNATURE DATA
    # =========================================================================
    signature_type = models.CharField(
        max_length=50,
        choices=SignatureType.choices
    )
    signature_data = models.TextField(
        blank=True,
        null=True,
        help_text="Base64 encoded signature image or reference"
    )
    signature_hash = models.CharField(
        max_length=64,
        blank=True,
        null=True,
        help_text="SHA-256 hash of signature data"
    )

    # =========================================================================
    # POSITION (for PDF embedding)
    # =========================================================================
    page_number = models.PositiveIntegerField(
        blank=True,
        null=True
    )
    position_x = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="X position in points from left"
    )
    position_y = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Y position in points from bottom"
    )
    width = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True
    )
    height = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True
    )

    # =========================================================================
    # PKI CERTIFICATE (for certificate-based signatures)
    # =========================================================================
    certificate_serial = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )
    certificate_issuer = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )
    certificate_subject = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )
    certificate_valid_from = models.DateTimeField(
        null=True,
        blank=True
    )
    certificate_valid_to = models.DateTimeField(
        null=True,
        blank=True
    )
    certificate_fingerprint = models.CharField(
        max_length=64,
        blank=True,
        null=True
    )

    # =========================================================================
    # AUDIT TRAIL
    # =========================================================================
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True, null=True)
    geolocation = models.JSONField(
        default=dict,
        blank=True,
        help_text="Latitude, longitude, and location details"
    )

    # =========================================================================
    # TIMESTAMP
    # =========================================================================
    signed_at = models.DateTimeField(default=timezone.now)
    timestamp_token = models.TextField(
        blank=True,
        null=True,
        help_text="RFC 3161 timestamp token"
    )
    timestamp_authority = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="TSA (Time Stamping Authority) URL"
    )

    # =========================================================================
    # STATUS & VERIFICATION
    # =========================================================================
    status = models.CharField(
        max_length=20,
        choices=SignatureStatus.choices,
        default=SignatureStatus.VALID
    )
    verification_status = models.CharField(
        max_length=50,
        blank=True,
        null=True
    )
    verification_message = models.TextField(
        blank=True,
        null=True
    )
    last_verified_at = models.DateTimeField(
        null=True,
        blank=True
    )

    # =========================================================================
    # SIGNATURE REQUEST (if signature was requested)
    # =========================================================================
    request_id = models.UUIDField(
        null=True,
        blank=True,
        help_text="Reference to signature request"
    )
    requested_by = models.UUIDField(
        null=True,
        blank=True
    )
    requested_at = models.DateTimeField(
        null=True,
        blank=True
    )

    # =========================================================================
    # REVOCATION
    # =========================================================================
    revoked_at = models.DateTimeField(null=True, blank=True)
    revoked_by = models.UUIDField(null=True, blank=True)
    revocation_reason = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'document_signatures'
        ordering = ['signed_at']
        indexes = [
            models.Index(fields=['document_id', 'signer_id']),
            models.Index(fields=['signer_id']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.signer_name} - {self.signed_at.strftime('%Y-%m-%d %H:%M')}"

    # =========================================================================
    # PROPERTIES
    # =========================================================================

    @property
    def is_valid(self) -> bool:
        """Check if signature is currently valid."""
        return self.status == SignatureStatus.VALID

    @property
    def is_certificate_signature(self) -> bool:
        """Check if this is a PKI certificate signature."""
        return self.signature_type == SignatureType.CERTIFICATE

    @property
    def certificate_is_valid(self) -> bool:
        """Check if the PKI certificate is still valid."""
        if not self.is_certificate_signature:
            return True

        now = timezone.now()
        if self.certificate_valid_from and now < self.certificate_valid_from:
            return False
        if self.certificate_valid_to and now > self.certificate_valid_to:
            return False
        return True

    # =========================================================================
    # METHODS
    # =========================================================================

    def revoke(self, revoked_by: uuid.UUID, reason: str = None) -> None:
        """Revoke this signature."""
        self.status = SignatureStatus.REVOKED
        self.revoked_at = timezone.now()
        self.revoked_by = revoked_by
        self.revocation_reason = reason
        self.save(update_fields=[
            'status', 'revoked_at', 'revoked_by', 'revocation_reason'
        ])

    def verify(self) -> tuple[bool, str]:
        """
        Verify signature validity.

        Returns:
            Tuple of (is_valid, message)
        """
        # Check if already revoked
        if self.status == SignatureStatus.REVOKED:
            return False, "Signature has been revoked"

        # Check certificate validity for PKI signatures
        if self.is_certificate_signature:
            if not self.certificate_is_valid:
                self.status = SignatureStatus.EXPIRED
                self.verification_status = 'certificate_expired'
                self.verification_message = "PKI certificate has expired"
                self.last_verified_at = timezone.now()
                self.save(update_fields=[
                    'status', 'verification_status', 'verification_message',
                    'last_verified_at'
                ])
                return False, "PKI certificate has expired"

        # Update verification timestamp
        self.verification_status = 'valid'
        self.verification_message = "Signature verified successfully"
        self.last_verified_at = timezone.now()
        self.save(update_fields=[
            'verification_status', 'verification_message', 'last_verified_at'
        ])

        return True, "Signature is valid"


class SignatureRequest(models.Model):
    """
    Request for document signature from a specific user.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    organization_id = models.UUIDField(db_index=True)

    document = models.ForeignKey(
        'Document',
        on_delete=models.CASCADE,
        related_name='signature_requests'
    )

    # Requester
    requested_by = models.UUIDField()
    requested_by_name = models.CharField(max_length=255)

    # Target signer
    signer_id = models.UUIDField(db_index=True)
    signer_email = models.EmailField()
    signer_name = models.CharField(max_length=255)
    signer_role = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    # Request details
    message = models.TextField(
        blank=True,
        null=True,
        help_text="Message to signer"
    )
    deadline = models.DateTimeField(
        null=True,
        blank=True
    )

    # Signature placement
    page_number = models.PositiveIntegerField(
        blank=True,
        null=True
    )
    position_x = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True
    )
    position_y = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True
    )

    # Status
    status = models.CharField(
        max_length=20,
        default='pending',
        choices=[
            ('pending', 'Pending'),
            ('signed', 'Signed'),
            ('declined', 'Declined'),
            ('expired', 'Expired'),
            ('cancelled', 'Cancelled'),
        ]
    )

    # Notification tracking
    email_sent = models.BooleanField(default=False)
    email_sent_at = models.DateTimeField(null=True, blank=True)
    reminder_count = models.PositiveIntegerField(default=0)
    last_reminder_at = models.DateTimeField(null=True, blank=True)

    # Result
    signature = models.ForeignKey(
        DocumentSignature,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='request'
    )
    declined_reason = models.TextField(blank=True, null=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'document_signature_requests'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['document_id', 'signer_id']),
            models.Index(fields=['signer_id', 'status']),
        ]

    def __str__(self):
        return f"Request for {self.signer_name} on {self.document}"

    @property
    def is_overdue(self) -> bool:
        """Check if request is past deadline."""
        if not self.deadline:
            return False
        return timezone.now() > self.deadline and self.status == 'pending'

    def mark_signed(self, signature: DocumentSignature) -> None:
        """Mark request as completed with signature."""
        self.status = 'signed'
        self.signature = signature
        self.completed_at = timezone.now()
        self.save(update_fields=['status', 'signature', 'completed_at'])

    def decline(self, reason: str = None) -> None:
        """Decline the signature request."""
        self.status = 'declined'
        self.declined_reason = reason
        self.completed_at = timezone.now()
        self.save(update_fields=['status', 'declined_reason', 'completed_at'])

    def cancel(self) -> None:
        """Cancel the signature request."""
        self.status = 'cancelled'
        self.completed_at = timezone.now()
        self.save(update_fields=['status', 'completed_at'])
