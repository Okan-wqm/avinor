# services/certificate-service/src/apps/core/models/examiner.py
"""
Examiner Authorization Model

EASA FCL.945-1025 - Examiner Requirements
Comprehensive examiner authorization management per EASA Part-FCL.
"""

import uuid
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional, Dict, Any, List
from dateutil.relativedelta import relativedelta

from django.db import models
from django.contrib.postgres.fields import ArrayField


class ExaminerCategory(models.TextChoices):
    """Examiner categories per FCL.1000."""
    # Flight Examiners
    FE = 'fe', 'Flight Examiner (FE)'
    FE_A = 'fe_a', 'Flight Examiner - Aeroplane (FE(A))'
    FE_H = 'fe_h', 'Flight Examiner - Helicopter (FE(H))'
    FE_S = 'fe_s', 'Flight Examiner - Sailplane (FE(S))'
    FE_B = 'fe_b', 'Flight Examiner - Balloon (FE(B))'

    # Type Rating Examiners
    TRE = 'tre', 'Type Rating Examiner (TRE)'
    TRE_A = 'tre_a', 'TRE - Aeroplane'
    TRE_H = 'tre_h', 'TRE - Helicopter'
    TRE_SP = 'tre_sp', 'TRE - Single Pilot'
    TRE_MP = 'tre_mp', 'TRE - Multi Pilot'

    # Class Rating Examiners
    CRE = 'cre', 'Class Rating Examiner (CRE)'
    CRE_SP = 'cre_sp', 'CRE - Single Pilot'
    CRE_ME = 'cre_me', 'CRE - Multi Engine'

    # Instrument Rating Examiners
    IRE = 'ire', 'Instrument Rating Examiner (IRE)'
    IRE_A = 'ire_a', 'IRE - Aeroplane'
    IRE_H = 'ire_h', 'IRE - Helicopter'

    # Synthetic Flight Examiners
    SFE = 'sfe', 'Synthetic Flight Examiner (SFE)'

    # Flight Instructor Examiners
    FIE = 'fie', 'Flight Instructor Examiner (FIE)'
    FIE_A = 'fie_a', 'FIE - Aeroplane'
    FIE_H = 'fie_h', 'FIE - Helicopter'


class ExaminerStatus(models.TextChoices):
    """Examiner authorization status."""
    ACTIVE = 'active', 'Active'
    EXPIRED = 'expired', 'Expired'
    SUSPENDED = 'suspended', 'Suspended'
    REVOKED = 'revoked', 'Revoked'
    RESTRICTED = 'restricted', 'Restricted'
    PENDING = 'pending', 'Pending Approval'


class ExaminerPrivilege(models.TextChoices):
    """Examiner privileges per FCL.1005."""
    # FE Privileges (FCL.1005.FE)
    SKILL_TEST_LAPL = 'skill_test_lapl', 'LAPL Skill Test'
    SKILL_TEST_PPL = 'skill_test_ppl', 'PPL Skill Test'
    SKILL_TEST_CPL = 'skill_test_cpl', 'CPL Skill Test'
    SKILL_TEST_IR = 'skill_test_ir', 'IR Skill Test'
    SKILL_TEST_NIGHT = 'skill_test_night', 'Night Rating Skill Test'
    PROFICIENCY_CHECK = 'proficiency_check', 'Proficiency Check'
    REVALIDATION = 'revalidation', 'Rating Revalidation'

    # TRE Privileges (FCL.1005.TRE)
    TYPE_SKILL_TEST = 'type_skill_test', 'Type Rating Skill Test'
    TYPE_PROFICIENCY = 'type_proficiency', 'Type Rating Proficiency Check'
    MCC_ASSESSMENT = 'mcc_assessment', 'MCC Assessment'
    ATPL_SKILL_TEST = 'atpl_skill_test', 'ATPL Skill Test'

    # CRE Privileges (FCL.1005.CRE)
    CLASS_SKILL_TEST = 'class_skill_test', 'Class Rating Skill Test'
    CLASS_PROFICIENCY = 'class_proficiency', 'Class Rating Proficiency Check'

    # IRE Privileges (FCL.1005.IRE)
    IR_SKILL_TEST = 'ir_skill_test', 'IR Skill Test'
    IR_PROFICIENCY = 'ir_proficiency', 'IR Proficiency Check'

    # FIE Privileges (FCL.1005.FIE)
    FI_ASSESSMENT = 'fi_assessment', 'FI Assessment of Competence'
    INSTRUCTOR_CHECK = 'instructor_check', 'Instructor Standardization'


# =============================================================================
# FCL.1010 - Prerequisites
# =============================================================================
class FCL1010Requirements:
    """FCL.1010 Prerequisites for examiner authorization."""

    # FE Prerequisites (FCL.1010.FE)
    FE_A_PIC_HOURS = 1000  # For PPL/CPL skill tests
    FE_A_INSTRUCTION_HOURS = 250  # Instruction given

    # TRE Prerequisites (FCL.1010.TRE)
    TRE_SP_PIC_HOURS = 500
    TRE_MP_PIC_HOURS = 1500
    TRE_INSTRUCTION_HOURS = 50  # Type instruction

    # CRE Prerequisites (FCL.1010.CRE)
    CRE_PIC_HOURS = 500
    CRE_INSTRUCTION_HOURS = 100

    # IRE Prerequisites (FCL.1010.IRE)
    IRE_IFR_HOURS = 300
    IRE_INSTRUCTION_HOURS = 100

    # FIE Prerequisites (FCL.1010.FIE)
    FIE_INSTRUCTION_HOURS = 500
    FIE_FI_INSTRUCTION_HOURS = 50

    # Validity Period
    EXAMINER_VALIDITY_MONTHS = 36  # 3 years


class ExaminerAuthorization(models.Model):
    """
    Examiner authorization record per EASA FCL.945-1025.

    Comprehensive tracking including:
    - Authorization validity
    - Privileges and restrictions
    - Standardization compliance
    - Examination activity tracking
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    organization_id = models.UUIDField(db_index=True)
    user_id = models.UUIDField(db_index=True)

    # Authorization Details
    authorization_number = models.CharField(
        max_length=100,
        unique=True,
        help_text='Examiner authorization number'
    )
    category = models.CharField(
        max_length=20,
        choices=ExaminerCategory.choices
    )
    status = models.CharField(
        max_length=20,
        choices=ExaminerStatus.choices,
        default=ExaminerStatus.ACTIVE
    )

    # Regulatory Reference
    regulatory_reference = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text='FCL reference (e.g., FCL.1000)'
    )

    # Dates
    issue_date = models.DateField()
    expiry_date = models.DateField()
    initial_issue_date = models.DateField(
        blank=True,
        null=True
    )

    # Issuing Authority
    issuing_authority = models.CharField(
        max_length=100,
        default='CAA',
        help_text='Competent authority that issued authorization'
    )
    issuing_state = models.CharField(
        max_length=50,
        default='NO',
        help_text='State of issue'
    )

    # Privileges (FCL.1005)
    privileges = ArrayField(
        models.CharField(max_length=50),
        default=list,
        blank=True,
        help_text='Examiner privileges'
    )

    # Aircraft Types (for TRE/SFE)
    aircraft_types = ArrayField(
        models.CharField(max_length=20),
        default=list,
        blank=True,
        help_text='Aircraft types for type rating examination'
    )

    # Class Ratings (for CRE)
    class_ratings = ArrayField(
        models.CharField(max_length=20),
        default=list,
        blank=True
    )

    # Restrictions
    restrictions = ArrayField(
        models.CharField(max_length=100),
        default=list,
        blank=True
    )
    restriction_details = models.TextField(blank=True, null=True)

    # Standardization (FCL.1015)
    is_standardized = models.BooleanField(
        default=True,
        help_text='Completed standardization per FCL.1015'
    )
    standardization_date = models.DateField(blank=True, null=True)
    standardization_valid_until = models.DateField(blank=True, null=True)
    standardization_authority = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    # Refresher Training
    last_refresher_date = models.DateField(blank=True, null=True)
    next_refresher_due = models.DateField(blank=True, null=True)

    # Experience Tracking
    total_examinations = models.PositiveIntegerField(
        default=0,
        help_text='Total examinations conducted'
    )
    examinations_in_period = models.PositiveIntegerField(
        default=0,
        help_text='Examinations in current validity period'
    )
    skill_tests_conducted = models.PositiveIntegerField(default=0)
    proficiency_checks_conducted = models.PositiveIntegerField(default=0)

    # Associated Instructor Certificate (required per FCL.1010)
    instructor_certificate_id = models.UUIDField(
        blank=True,
        null=True,
        help_text='Associated instructor certificate (FI/TRI/etc.)'
    )

    # Associated Pilot License
    license_id = models.UUIDField(blank=True, null=True)

    # CAA Oversight
    last_oversight_date = models.DateField(
        blank=True,
        null=True,
        help_text='Last CAA oversight/audit'
    )
    oversight_result = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        choices=[
            ('satisfactory', 'Satisfactory'),
            ('minor_findings', 'Minor Findings'),
            ('major_findings', 'Major Findings'),
            ('unsatisfactory', 'Unsatisfactory'),
        ]
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
        db_table = 'examiner_authorizations'
        ordering = ['-issue_date']
        indexes = [
            models.Index(fields=['organization_id', 'user_id']),
            models.Index(fields=['category']),
            models.Index(fields=['status']),
            models.Index(fields=['expiry_date']),
            models.Index(fields=['authorization_number']),
        ]

    def __str__(self) -> str:
        return f"{self.get_category_display()} - {self.authorization_number}"

    @property
    def is_valid(self) -> bool:
        """Check if authorization is currently valid."""
        if self.status != ExaminerStatus.ACTIVE:
            return False
        if self.expiry_date and self.expiry_date < date.today():
            return False
        if not self.is_standardized:
            return False
        if self.standardization_valid_until and self.standardization_valid_until < date.today():
            return False
        return True

    @property
    def is_expired(self) -> bool:
        """Check if authorization is expired."""
        return self.expiry_date and self.expiry_date < date.today()

    @property
    def days_until_expiry(self) -> Optional[int]:
        """Days until expiry."""
        if not self.expiry_date:
            return None
        return (self.expiry_date - date.today()).days

    def has_privilege(self, privilege: str) -> bool:
        """Check if examiner has specific privilege."""
        return privilege in self.privileges

    def can_examine_type(self, aircraft_type: str) -> bool:
        """Check if examiner can examine specific aircraft type."""
        if self.category in [
            ExaminerCategory.TRE, ExaminerCategory.TRE_A,
            ExaminerCategory.TRE_H, ExaminerCategory.TRE_SP,
            ExaminerCategory.TRE_MP
        ]:
            return aircraft_type in self.aircraft_types
        return True

    def increment_examinations(self, exam_type: str = 'skill_test') -> None:
        """Increment examination count."""
        self.total_examinations += 1
        self.examinations_in_period += 1
        if exam_type == 'skill_test':
            self.skill_tests_conducted += 1
        elif exam_type == 'proficiency_check':
            self.proficiency_checks_conducted += 1
        self.save(update_fields=[
            'total_examinations', 'examinations_in_period',
            'skill_tests_conducted', 'proficiency_checks_conducted',
            'updated_at'
        ])

    def get_validity_info(self) -> Dict[str, Any]:
        """Get comprehensive validity information."""
        return {
            'authorization_id': str(self.id),
            'authorization_number': self.authorization_number,
            'category': self.category,
            'status': self.status,
            'is_valid': self.is_valid,
            'expiry_date': self.expiry_date.isoformat() if self.expiry_date else None,
            'days_until_expiry': self.days_until_expiry,
            'privileges': self.privileges,
            'aircraft_types': self.aircraft_types,
            'restrictions': self.restrictions,
            'is_standardized': self.is_standardized,
            'standardization_valid_until': (
                self.standardization_valid_until.isoformat()
                if self.standardization_valid_until else None
            ),
            'total_examinations': self.total_examinations,
        }


class ExaminationRecord(models.Model):
    """
    Record of examinations conducted by examiners.

    Tracks skill tests, proficiency checks, and assessments.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    organization_id = models.UUIDField(db_index=True)
    examiner_authorization_id = models.UUIDField(db_index=True)
    examiner_id = models.UUIDField(db_index=True)

    # Candidate
    candidate_id = models.UUIDField(db_index=True)
    candidate_name = models.CharField(max_length=255)

    # Examination Details
    examination_date = models.DateField()
    examination_type = models.CharField(
        max_length=50,
        choices=[
            ('skill_test', 'Skill Test'),
            ('proficiency_check', 'Proficiency Check'),
            ('assessment_competence', 'Assessment of Competence'),
            ('revalidation', 'Revalidation Check'),
        ]
    )

    # What was examined
    license_type = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text='LAPL, PPL, CPL, ATPL'
    )
    rating_examined = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text='Rating being tested/checked'
    )
    aircraft_type = models.CharField(
        max_length=50,
        blank=True,
        null=True
    )

    # Result
    result = models.CharField(
        max_length=20,
        choices=[
            ('pass', 'Pass'),
            ('partial_pass', 'Partial Pass'),
            ('fail', 'Fail'),
            ('deferred', 'Deferred'),
        ]
    )
    sections_passed = ArrayField(
        models.CharField(max_length=50),
        default=list,
        blank=True
    )
    sections_failed = ArrayField(
        models.CharField(max_length=50),
        default=list,
        blank=True
    )

    # Duration
    flight_time = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        blank=True,
        null=True
    )
    simulator_time = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        blank=True,
        null=True
    )

    # Aircraft Used
    aircraft_registration = models.CharField(max_length=20, blank=True, null=True)
    simulator_id = models.CharField(max_length=50, blank=True, null=True)

    # Location
    location = models.CharField(max_length=100, blank=True, null=True)
    departure_aerodrome = models.CharField(max_length=10, blank=True, null=True)

    # CAA Form Reference
    form_reference = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text='CAA form number/reference'
    )
    form_url = models.URLField(max_length=500, blank=True, null=True)

    # Feedback
    feedback = models.TextField(blank=True, null=True)
    areas_for_improvement = ArrayField(
        models.CharField(max_length=200),
        default=list,
        blank=True
    )

    # Notes
    notes = models.TextField(blank=True, null=True)

    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'examination_records'
        ordering = ['-examination_date']
        indexes = [
            models.Index(fields=['organization_id', 'examiner_authorization_id']),
            models.Index(fields=['candidate_id']),
            models.Index(fields=['examination_date']),
            models.Index(fields=['result']),
        ]

    def __str__(self) -> str:
        return f"{self.examination_date} - {self.candidate_name} - {self.result}"


class ExaminerRevalidation(models.Model):
    """
    Examiner authorization revalidation record per FCL.1025.

    FCL.1025 Revalidation requirements:
    - Conduct specified number of examinations
    - Attend refresher seminar
    - CAA assessment/standardization
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    organization_id = models.UUIDField(db_index=True)
    examiner_authorization_id = models.UUIDField(db_index=True)
    user_id = models.UUIDField(db_index=True)

    # Revalidation Details
    revalidation_date = models.DateField()
    previous_expiry = models.DateField(blank=True, null=True)
    new_expiry = models.DateField()

    # Requirements
    examinations_conducted = models.PositiveIntegerField(
        default=0,
        help_text='Examinations in validity period'
    )
    min_examinations_required = models.PositiveIntegerField(
        default=2,
        help_text='Minimum examinations per category'
    )

    # Refresher Seminar
    refresher_completed = models.BooleanField(default=False)
    refresher_date = models.DateField(blank=True, null=True)
    refresher_provider = models.CharField(max_length=200, blank=True, null=True)

    # CAA Assessment
    caa_assessment_completed = models.BooleanField(default=False)
    caa_assessment_date = models.DateField(blank=True, null=True)
    caa_assessor = models.CharField(max_length=255, blank=True, null=True)
    caa_assessment_result = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        choices=[
            ('satisfactory', 'Satisfactory'),
            ('satisfactory_observations', 'Satisfactory with Observations'),
            ('unsatisfactory', 'Unsatisfactory'),
        ]
    )

    # Is Renewal
    is_renewal = models.BooleanField(default=False)

    # Notes
    notes = models.TextField(blank=True, null=True)

    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.UUIDField(blank=True, null=True)

    class Meta:
        db_table = 'examiner_revalidations'
        ordering = ['-revalidation_date']

    def __str__(self) -> str:
        return f"Revalidation {self.revalidation_date}"
