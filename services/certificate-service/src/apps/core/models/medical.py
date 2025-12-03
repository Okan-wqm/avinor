# services/certificate-service/src/apps/core/models/medical.py
"""
Medical Certificate Model

Medical certificates for pilots with class-based validity.
"""

import uuid
from datetime import date, timedelta
from typing import Optional, Dict, Any, List

from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.utils import timezone


class MedicalClass(models.TextChoices):
    """Medical certificate class choices."""
    CLASS_1 = 'class_1', 'Class 1 (ATPL/CPL)'
    CLASS_2 = 'class_2', 'Class 2 (PPL)'
    CLASS_3 = 'class_3', 'Class 3 (ATC)'
    LAPL = 'lapl', 'LAPL Medical'
    BASICMED = 'basicmed', 'BasicMed (FAA)'


class MedicalStatus(models.TextChoices):
    """Medical certificate status choices."""
    ACTIVE = 'active', 'Active'
    EXPIRED = 'expired', 'Expired'
    SUSPENDED = 'suspended', 'Suspended'
    REVOKED = 'revoked', 'Revoked'
    DEFERRED = 'deferred', 'Deferred'


class MedicalLimitation(models.TextChoices):
    """Common medical limitation codes."""
    VDL = 'vdl', 'VDL - Shall wear corrective lenses'
    VNL = 'vnl', 'VNL - Shall have corrective lenses available'
    VML = 'vml', 'VML - Shall wear multifocal lenses'
    HAL = 'hal', 'HAL - Shall wear hearing aid(s)'
    OML = 'oml', 'OML - Valid only with OPL'
    OPL = 'opl', 'OPL - Specific ophthalmological limitation'
    OSL = 'osl', 'OSL - Otolaryngological limitation'
    TML = 'tml', 'TML - Time limitation'
    SSL = 'ssl', 'SSL - Special restriction'
    SIC = 'sic', 'SIC - Valid only as or with qualified co-pilot'
    OCL = 'ocl', 'OCL - Operational condition limitation'
    RXO = 'rxo', 'RXO - Wearing approved glasses for near vision'


class MedicalCertificate(models.Model):
    """
    Medical Certificate model.

    Stores medical certification information with class-based validity periods.
    Validity periods vary by medical class and pilot age.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    organization_id = models.UUIDField(db_index=True)
    user_id = models.UUIDField(db_index=True)

    # Medical Class
    medical_class = models.CharField(
        max_length=20,
        choices=MedicalClass.choices,
        db_index=True
    )

    # Issuing Information
    issuing_authority = models.CharField(max_length=50)
    issuing_country = models.CharField(
        max_length=2,
        blank=True,
        null=True,
        help_text='ISO 3166-1 alpha-2 country code'
    )

    # Certificate Number
    certificate_number = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    # AME Information
    ame_name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name='AME Name',
        help_text='Aviation Medical Examiner name'
    )
    ame_license_number = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name='AME License Number'
    )
    ame_address = models.TextField(
        blank=True,
        null=True,
        verbose_name='AME Address'
    )
    ame_contact = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name='AME Contact'
    )

    # Dates
    examination_date = models.DateField()
    issue_date = models.DateField()
    expiry_date = models.DateField(db_index=True)

    # Age at examination (affects validity)
    pilot_age_at_exam = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text='Pilot age at time of examination'
    )
    pilot_birth_date = models.DateField(
        blank=True,
        null=True
    )

    # Status
    status = models.CharField(
        max_length=20,
        choices=MedicalStatus.choices,
        default=MedicalStatus.ACTIVE,
        db_index=True
    )

    # Limitations
    limitations = ArrayField(
        models.CharField(max_length=255),
        default=list,
        blank=True,
        help_text='List of medical limitations/restrictions'
    )
    limitation_codes = ArrayField(
        models.CharField(max_length=10),
        default=list,
        blank=True,
        help_text='Standard limitation codes (VDL, HAL, etc.)'
    )
    limitation_details = models.TextField(
        blank=True,
        null=True,
        help_text='Detailed explanation of limitations'
    )

    # Examination Results (summary - not detailed medical data)
    examination_results = models.JSONField(
        default=dict,
        blank=True,
        help_text='Summary examination results'
    )

    # Document
    document_url = models.URLField(max_length=500, blank=True, null=True)
    document_filename = models.CharField(max_length=255, blank=True, null=True)

    # Reminder tracking
    reminder_sent_90_days = models.BooleanField(default=False)
    reminder_sent_60_days = models.BooleanField(default=False)
    reminder_sent_30_days = models.BooleanField(default=False)
    reminder_sent_14_days = models.BooleanField(default=False)
    reminder_sent_7_days = models.BooleanField(default=False)
    last_reminder_sent = models.DateTimeField(blank=True, null=True)

    # Notes
    notes = models.TextField(blank=True, null=True)

    # Metadata
    metadata = models.JSONField(default=dict, blank=True)

    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.UUIDField(blank=True, null=True)

    class Meta:
        db_table = 'medical_certificates'
        ordering = ['-expiry_date']
        indexes = [
            models.Index(fields=['organization_id', 'user_id']),
            models.Index(fields=['medical_class', 'status']),
            models.Index(fields=['expiry_date', 'status']),
        ]
        verbose_name = 'Medical Certificate'
        verbose_name_plural = 'Medical Certificates'

    def __str__(self) -> str:
        return f"{self.get_medical_class_display()} - {self.user_id}"

    @property
    def is_valid(self) -> bool:
        """Check if medical is currently valid."""
        return (
            self.status == MedicalStatus.ACTIVE and
            self.expiry_date >= date.today()
        )

    @property
    def is_expired(self) -> bool:
        """Check if medical is expired."""
        return self.expiry_date < date.today()

    @property
    def days_until_expiry(self) -> int:
        """Calculate days until expiry."""
        return (self.expiry_date - date.today()).days

    @property
    def is_expiring_soon(self) -> bool:
        """Check if expiring within 90 days."""
        days = self.days_until_expiry
        return 0 < days <= 90

    @property
    def expiry_status(self) -> str:
        """Get human-readable expiry status."""
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

    @classmethod
    def calculate_validity_period(
        cls,
        medical_class: str,
        pilot_age: int,
        authority: str = 'easa'
    ) -> int:
        """
        Calculate validity period in months based on class and age.

        EASA FCL.025 validity periods:
        - Class 1: <40 years = 12 months, 40-59 years = 6 months, 60+ years = 6 months
        - Class 2: <40 years = 60 months, 40-49 years = 24 months, 50+ years = 12 months
        - LAPL: <40 years = 60 months, 40+ years = 24 months
        """
        if authority.lower() in ['easa', 'shgm']:
            if medical_class == MedicalClass.CLASS_1:
                if pilot_age < 40:
                    return 12
                elif pilot_age < 60:
                    return 6
                else:
                    return 6
            elif medical_class == MedicalClass.CLASS_2:
                if pilot_age < 40:
                    return 60
                elif pilot_age < 50:
                    return 24
                else:
                    return 12
            elif medical_class == MedicalClass.LAPL:
                if pilot_age < 40:
                    return 60
                else:
                    return 24
            elif medical_class == MedicalClass.CLASS_3:
                if pilot_age < 40:
                    return 24
                else:
                    return 12
        elif authority.lower() == 'faa':
            # FAA validity periods (different rules)
            if medical_class == MedicalClass.CLASS_1:
                if pilot_age < 40:
                    return 12
                else:
                    return 6
            elif medical_class == MedicalClass.CLASS_2:
                if pilot_age < 40:
                    return 12
                else:
                    return 12
            elif medical_class == MedicalClass.CLASS_3:
                if pilot_age < 40:
                    return 60
                else:
                    return 24

        # Default to 12 months
        return 12

    def calculate_expiry_date(self) -> date:
        """Calculate expiry date based on class and age."""
        if not self.pilot_age_at_exam:
            # Calculate age from birth date
            if self.pilot_birth_date:
                age_delta = self.examination_date - self.pilot_birth_date
                self.pilot_age_at_exam = age_delta.days // 365

        validity_months = self.calculate_validity_period(
            self.medical_class,
            self.pilot_age_at_exam or 30,  # Default age
            self.issuing_authority
        )

        # Calculate expiry date (end of month)
        expiry = self.issue_date + timedelta(days=validity_months * 30)
        # Move to end of month for most authorities
        import calendar
        _, last_day = calendar.monthrange(expiry.year, expiry.month)
        return date(expiry.year, expiry.month, last_day)

    def update_status(self) -> None:
        """Update status based on current state."""
        if self.status in [MedicalStatus.REVOKED, MedicalStatus.SUSPENDED, MedicalStatus.DEFERRED]:
            return

        if self.is_expired:
            self.status = MedicalStatus.EXPIRED
            self.save(update_fields=['status', 'updated_at'])

    def get_applicable_privileges(self) -> List[str]:
        """Get privileges associated with this medical class."""
        privileges = {
            MedicalClass.CLASS_1: [
                'ATPL holder privileges',
                'CPL holder privileges',
                'PPL holder privileges',
                'Commercial operations',
                'Single pilot operations',
                'Multi-crew operations'
            ],
            MedicalClass.CLASS_2: [
                'PPL holder privileges',
                'Private operations',
                'Non-commercial operations'
            ],
            MedicalClass.CLASS_3: [
                'ATC duties'
            ],
            MedicalClass.LAPL: [
                'LAPL holder privileges',
                'Light aircraft operations',
                'Non-commercial operations',
                'Max 4 persons on board'
            ],
            MedicalClass.BASICMED: [
                'PPL holder privileges (limited)',
                'Day VFR operations',
                'US domestic flights only',
                'Max 6 persons on board',
                'Aircraft under 6000 lbs'
            ]
        }
        return privileges.get(self.medical_class, [])

    def get_validity_info(self) -> Dict[str, Any]:
        """Get detailed validity information."""
        return {
            'medical_id': str(self.id),
            'medical_class': self.medical_class,
            'status': self.status,
            'is_valid': self.is_valid,
            'is_expired': self.is_expired,
            'is_expiring_soon': self.is_expiring_soon,
            'expiry_date': self.expiry_date.isoformat(),
            'days_until_expiry': self.days_until_expiry,
            'expiry_status': self.expiry_status,
            'limitations': self.limitations,
            'limitation_codes': self.limitation_codes,
            'issuing_authority': self.issuing_authority,
            'privileges': self.get_applicable_privileges(),
        }

    def should_send_reminder(self, days: int) -> bool:
        """Check if reminder should be sent for given days."""
        if self.days_until_expiry > days:
            return False

        reminder_field = f'reminder_sent_{days}_days'
        if hasattr(self, reminder_field):
            return not getattr(self, reminder_field)
        return False

    def mark_reminder_sent(self, days: int) -> None:
        """Mark reminder as sent."""
        reminder_field = f'reminder_sent_{days}_days'
        if hasattr(self, reminder_field):
            setattr(self, reminder_field, True)
            self.last_reminder_sent = timezone.now()
            self.save(update_fields=[reminder_field, 'last_reminder_sent', 'updated_at'])
