# services/certificate-service/src/apps/core/models/instructor.py
"""
Instructor Certificate Model

EASA FCL.900-930 - Instructor Requirements
Comprehensive instructor certificate management per EASA Part-FCL.
"""

import uuid
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional, Dict, Any, List
from dateutil.relativedelta import relativedelta

from django.db import models
from django.contrib.postgres.fields import ArrayField


class InstructorCategory(models.TextChoices):
    """Instructor certificate categories per FCL.900."""
    # Flight Instructors
    FI = 'fi', 'Flight Instructor (FI)'
    FI_A = 'fi_a', 'Flight Instructor - Aeroplane (FI(A))'
    FI_H = 'fi_h', 'Flight Instructor - Helicopter (FI(H))'
    FI_S = 'fi_s', 'Flight Instructor - Sailplane (FI(S))'
    FI_B = 'fi_b', 'Flight Instructor - Balloon (FI(B))'

    # Class Rating Instructors
    CRI = 'cri', 'Class Rating Instructor (CRI)'
    CRI_SP = 'cri_sp', 'CRI - Single Pilot'
    CRI_ME = 'cri_me', 'CRI - Multi-Engine'

    # Instrument Rating Instructors
    IRI = 'iri', 'Instrument Rating Instructor (IRI)'
    IRI_A = 'iri_a', 'IRI - Aeroplane'
    IRI_H = 'iri_h', 'IRI - Helicopter'

    # Type Rating Instructors
    TRI = 'tri', 'Type Rating Instructor (TRI)'
    TRI_SP = 'tri_sp', 'TRI - Single Pilot'
    TRI_MP = 'tri_mp', 'TRI - Multi Pilot'
    TRI_SFI = 'tri_sfi', 'TRI - Synthetic Flight Instructor'

    # Synthetic Training
    SFI = 'sfi', 'Synthetic Flight Instructor (SFI)'
    STI = 'sti', 'Synthetic Training Instructor (STI)'

    # Mountain Flying
    MI = 'mi', 'Mountain Rating Instructor (MI)'

    # Aerobatic
    ACI = 'aci', 'Aerobatic Flight Instructor'

    # Multi-Crew Cooperation
    MCCI = 'mcci', 'Multi-Crew Cooperation Instructor (MCCI)'


class InstructorStatus(models.TextChoices):
    """Instructor certificate status."""
    ACTIVE = 'active', 'Active'
    EXPIRED = 'expired', 'Expired'
    SUSPENDED = 'suspended', 'Suspended'
    REVOKED = 'revoked', 'Revoked'
    RESTRICTED = 'restricted', 'Restricted'
    PENDING = 'pending', 'Pending Approval'


class InstructorPrivilege(models.TextChoices):
    """Instructor privileges per FCL.910."""
    # FI Privileges (FCL.910.FI)
    PPL_TRAINING = 'ppl_training', 'PPL Training'
    LAPL_TRAINING = 'lapl_training', 'LAPL Training'
    CPL_TRAINING = 'cpl_training', 'CPL Training'
    NIGHT_TRAINING = 'night_training', 'Night Rating Training'
    CLASS_RATING = 'class_rating', 'Class Rating Training'
    SEP_TRAINING = 'sep_training', 'SEP Class Rating'
    MEP_TRAINING = 'mep_training', 'MEP Class Rating'
    IR_TRAINING = 'ir_training', 'Instrument Rating Training'
    FI_TRAINING = 'fi_training', 'FI Training (FI with privilege)'

    # CRI Privileges (FCL.910.CRI)
    CLASS_INITIAL = 'class_initial', 'Initial Class Rating'
    CLASS_REVALIDATION = 'class_revalidation', 'Class Rating Revalidation'

    # IRI Privileges (FCL.910.IRI)
    IR_ISSUE = 'ir_issue', 'IR Issue'
    IR_REVALIDATION = 'ir_revalidation', 'IR Revalidation'

    # TRI Privileges (FCL.910.TRI)
    TYPE_INITIAL = 'type_initial', 'Initial Type Rating'
    TYPE_REVALIDATION = 'type_revalidation', 'Type Rating Revalidation'
    TYPE_MCC = 'type_mcc', 'MCC Training on Type'


# =============================================================================
# FCL.915 - Prerequisites and Requirements
# =============================================================================
class FCL915Requirements:
    """FCL.915 Prerequisites for instructor certificates."""

    # FI(A) Prerequisites (FCL.915.FI)
    FI_A_MIN_HOURS = 200  # Or 150 if in integrated ATP course
    FI_A_PIC_HOURS = 100  # PIC time
    FI_A_XC_HOURS = 20  # Cross-country PIC
    FI_A_XC_PIC_HOURS = 10  # PIC XC with student

    # CRI Prerequisites (FCL.915.CRI)
    CRI_SP_PIC_HOURS = 300  # For single-pilot
    CRI_ME_PIC_HOURS = 500  # For multi-engine

    # IRI Prerequisites (FCL.915.IRI)
    IRI_INSTRUMENT_HOURS = 200  # IFR hours

    # TRI Prerequisites (FCL.915.TRI)
    TRI_SP_PIC_HOURS = 500  # Single pilot type
    TRI_MP_PIC_HOURS = 1500  # Multi-pilot type

    # Validity Periods
    FI_VALIDITY_MONTHS = 36  # 3 years
    CRI_VALIDITY_MONTHS = 36
    IRI_VALIDITY_MONTHS = 36
    TRI_VALIDITY_MONTHS = 36
    SFI_VALIDITY_MONTHS = 36


class InstructorCertificate(models.Model):
    """
    Instructor certificate record per EASA FCL.900-930.

    Comprehensive tracking of instructor certificates including:
    - Certificate validity
    - Privileges and restrictions
    - Refresher training compliance
    - Standardization checks
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    organization_id = models.UUIDField(db_index=True)
    user_id = models.UUIDField(db_index=True)

    # Certificate Details
    certificate_number = models.CharField(
        max_length=100,
        unique=True,
        help_text='Instructor certificate number'
    )
    category = models.CharField(
        max_length=20,
        choices=InstructorCategory.choices
    )
    status = models.CharField(
        max_length=20,
        choices=InstructorStatus.choices,
        default=InstructorStatus.ACTIVE
    )

    # Regulatory Reference
    regulatory_reference = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text='FCL reference (e.g., FCL.905.FI)'
    )

    # Dates
    issue_date = models.DateField()
    expiry_date = models.DateField()
    initial_issue_date = models.DateField(
        blank=True,
        null=True,
        help_text='Date of first issue'
    )

    # Issuing Authority
    issuing_authority = models.CharField(
        max_length=100,
        default='CAA',
        help_text='Authority that issued certificate'
    )
    issuing_state = models.CharField(
        max_length=50,
        default='NO',  # Norway
        help_text='State of issue (ISO code)'
    )

    # Privileges (FCL.905/910)
    privileges = ArrayField(
        models.CharField(max_length=50),
        default=list,
        blank=True,
        help_text='Instructor privileges'
    )

    # Aircraft Types (for TRI)
    aircraft_types = ArrayField(
        models.CharField(max_length=20),
        default=list,
        blank=True,
        help_text='Aircraft types for type rating instruction'
    )

    # Class Ratings (for CRI)
    class_ratings = ArrayField(
        models.CharField(max_length=20),
        default=list,
        blank=True,
        help_text='Class ratings for instruction'
    )

    # Restrictions (FCL.905)
    restrictions = ArrayField(
        models.CharField(max_length=100),
        default=list,
        blank=True,
        help_text='Certificate restrictions'
    )
    restriction_details = models.TextField(
        blank=True,
        null=True,
        help_text='Detailed restriction explanation'
    )

    # Experience Requirements Tracking
    total_instruction_hours = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        default=0,
        help_text='Total instruction hours given'
    )
    recent_instruction_hours = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text='Instruction hours in last 12 months'
    )

    # Refresher Training (FCL.940)
    last_refresher_date = models.DateField(
        blank=True,
        null=True,
        help_text='Last refresher seminar/training date'
    )
    next_refresher_due = models.DateField(
        blank=True,
        null=True,
        help_text='Next refresher due date'
    )
    refresher_provider = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text='ATO that provided refresher'
    )

    # Proficiency Check / Assessment of Competence
    last_assessment_date = models.DateField(
        blank=True,
        null=True,
        help_text='Last assessment of competence'
    )
    next_assessment_due = models.DateField(
        blank=True,
        null=True,
        help_text='Next assessment due'
    )
    assessor_name = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )
    assessor_id = models.UUIDField(blank=True, null=True)

    # Standardization (FCL.935)
    is_standardized = models.BooleanField(
        default=True,
        help_text='Completed standardization training'
    )
    standardization_date = models.DateField(
        blank=True,
        null=True
    )
    standardization_valid_until = models.DateField(
        blank=True,
        null=True
    )

    # FI Restricted Privileges (FCL.910.FI)
    # New FIs have restrictions lifted after experience
    fi_restrictions_lifted = models.BooleanField(
        default=False,
        help_text='FI restrictions lifted per FCL.910.FI(e)'
    )
    fi_hours_before_spin = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True,
        help_text='100h required before spin training'
    )
    fi_hours_before_fi_training = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True,
        help_text='500h + 50 FI hours for FI training privilege'
    )

    # Associated License
    license_id = models.UUIDField(
        blank=True,
        null=True,
        help_text='Associated pilot license'
    )

    # Language Proficiency (for FI)
    language_proficiency_required = models.BooleanField(default=True)
    language_proficiency_level = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text='ICAO level (4, 5, or 6)'
    )

    # Notes
    notes = models.TextField(blank=True, null=True)

    # Metadata
    metadata = models.JSONField(default=dict, blank=True)

    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.UUIDField(blank=True, null=True)

    class Meta:
        db_table = 'instructor_certificates'
        ordering = ['-issue_date']
        indexes = [
            models.Index(fields=['organization_id', 'user_id']),
            models.Index(fields=['category']),
            models.Index(fields=['status']),
            models.Index(fields=['expiry_date']),
            models.Index(fields=['certificate_number']),
        ]

    def __str__(self) -> str:
        return f"{self.get_category_display()} - {self.certificate_number}"

    @property
    def is_valid(self) -> bool:
        """Check if certificate is currently valid."""
        if self.status != InstructorStatus.ACTIVE:
            return False
        if self.expiry_date and self.expiry_date < date.today():
            return False
        return True

    @property
    def is_expired(self) -> bool:
        """Check if certificate is expired."""
        return self.expiry_date and self.expiry_date < date.today()

    @property
    def days_until_expiry(self) -> Optional[int]:
        """Days until expiry."""
        if not self.expiry_date:
            return None
        return (self.expiry_date - date.today()).days

    @property
    def requires_refresher(self) -> bool:
        """Check if refresher training is due."""
        if not self.next_refresher_due:
            return False
        return date.today() >= self.next_refresher_due

    @property
    def requires_assessment(self) -> bool:
        """Check if assessment of competence is due."""
        if not self.next_assessment_due:
            return False
        return date.today() >= self.next_assessment_due

    def has_privilege(self, privilege: str) -> bool:
        """Check if instructor has specific privilege."""
        return privilege in self.privileges

    def add_privilege(self, privilege: str) -> None:
        """Add privilege to instructor certificate."""
        if privilege not in self.privileges:
            self.privileges.append(privilege)
            self.save(update_fields=['privileges', 'updated_at'])

    def remove_privilege(self, privilege: str) -> None:
        """Remove privilege from instructor certificate."""
        if privilege in self.privileges:
            self.privileges.remove(privilege)
            self.save(update_fields=['privileges', 'updated_at'])

    def get_validity_info(self) -> Dict[str, Any]:
        """Get comprehensive validity information."""
        return {
            'certificate_id': str(self.id),
            'certificate_number': self.certificate_number,
            'category': self.category,
            'status': self.status,
            'is_valid': self.is_valid,
            'expiry_date': self.expiry_date.isoformat() if self.expiry_date else None,
            'days_until_expiry': self.days_until_expiry,
            'privileges': self.privileges,
            'restrictions': self.restrictions,
            'requires_refresher': self.requires_refresher,
            'requires_assessment': self.requires_assessment,
            'next_refresher_due': (
                self.next_refresher_due.isoformat()
                if self.next_refresher_due else None
            ),
            'next_assessment_due': (
                self.next_assessment_due.isoformat()
                if self.next_assessment_due else None
            ),
        }


class InstructorRevalidation(models.Model):
    """
    Instructor certificate revalidation record per FCL.940.

    FCL.940 Validity, revalidation, and renewal:
    - 3-year validity
    - Revalidation requires:
      (a) Assessment of competence within last 12 months
      (b) Training/seminar within validity period
      (c) Sufficient instruction given
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    organization_id = models.UUIDField(db_index=True)
    instructor_certificate_id = models.UUIDField(db_index=True)
    user_id = models.UUIDField(db_index=True)

    # Revalidation Details
    revalidation_date = models.DateField()
    previous_expiry = models.DateField(blank=True, null=True)
    new_expiry = models.DateField()

    # Requirements Met
    assessment_completed = models.BooleanField(default=False)
    assessment_date = models.DateField(blank=True, null=True)
    assessor_name = models.CharField(max_length=255, blank=True, null=True)
    assessor_id = models.UUIDField(blank=True, null=True)

    refresher_completed = models.BooleanField(default=False)
    refresher_date = models.DateField(blank=True, null=True)
    refresher_provider = models.CharField(max_length=200, blank=True, null=True)
    refresher_hours = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        blank=True,
        null=True
    )

    instruction_hours_in_period = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        blank=True,
        null=True,
        help_text='Instruction hours given during validity period'
    )

    # Is Renewal (after lapse)
    is_renewal = models.BooleanField(
        default=False,
        help_text='Renewal after certificate lapse'
    )
    renewal_training_completed = models.BooleanField(default=False)
    renewal_training_hours = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        blank=True,
        null=True
    )

    # Notes
    notes = models.TextField(blank=True, null=True)

    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.UUIDField(blank=True, null=True)

    class Meta:
        db_table = 'instructor_revalidations'
        ordering = ['-revalidation_date']

    def __str__(self) -> str:
        return f"Revalidation {self.revalidation_date}"


class InstructorActivity(models.Model):
    """
    Track instructor teaching activity for FCL.940 compliance.

    Records instruction given for revalidation tracking.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    organization_id = models.UUIDField(db_index=True)
    instructor_certificate_id = models.UUIDField(db_index=True)
    user_id = models.UUIDField(db_index=True)  # Instructor

    # Activity Details
    activity_date = models.DateField()
    activity_type = models.CharField(
        max_length=50,
        choices=[
            ('flight_training', 'Flight Training'),
            ('ground_training', 'Ground Training'),
            ('simulator_training', 'Simulator Training'),
            ('briefing', 'Briefing'),
            ('skill_test', 'Skill Test Preparation'),
            ('proficiency_check', 'Proficiency Check'),
        ]
    )

    # Student
    student_id = models.UUIDField(blank=True, null=True)
    student_name = models.CharField(max_length=255, blank=True, null=True)

    # Training Details
    training_type = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text='e.g., PPL, CPL, IR, Type Rating'
    )

    # Time
    instruction_hours = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        help_text='Hours of instruction'
    )
    flight_hours = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=0
    )
    simulator_hours = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=0
    )
    ground_hours = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=0
    )

    # Aircraft
    aircraft_registration = models.CharField(max_length=20, blank=True, null=True)
    aircraft_type = models.CharField(max_length=50, blank=True, null=True)

    # Exercises/Maneuvers
    exercises = ArrayField(
        models.CharField(max_length=100),
        default=list,
        blank=True
    )

    # Notes
    notes = models.TextField(blank=True, null=True)

    # Audit
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'instructor_activities'
        ordering = ['-activity_date']
        indexes = [
            models.Index(fields=['organization_id', 'instructor_certificate_id']),
            models.Index(fields=['activity_date']),
        ]

    def __str__(self) -> str:
        return f"{self.activity_date} - {self.instruction_hours}h"
