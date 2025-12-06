# services/certificate-service/src/apps/core/models/theoretical_exam.py
"""
Theoretical Knowledge Examination Model

EASA FCL.025 - Theoretical Knowledge Examinations
Comprehensive theoretical exam tracking per EASA Part-FCL.
"""

import uuid
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional, Dict, Any, List
from dateutil.relativedelta import relativedelta

from django.db import models
from django.contrib.postgres.fields import ArrayField


class ExamLicenseType(models.TextChoices):
    """License type for theoretical exams."""
    LAPL_A = 'lapl_a', 'LAPL(A) - Light Aircraft Pilot Licence'
    PPL_A = 'ppl_a', 'PPL(A) - Private Pilot Licence'
    CPL_A = 'cpl_a', 'CPL(A) - Commercial Pilot Licence'
    ATPL_A = 'atpl_a', 'ATPL(A) - Airline Transport Pilot Licence'
    IR = 'ir', 'Instrument Rating'
    EIR = 'eir', 'En-Route Instrument Rating'
    LAPL_H = 'lapl_h', 'LAPL(H) - Helicopter'
    PPL_H = 'ppl_h', 'PPL(H)'
    CPL_H = 'cpl_h', 'CPL(H)'
    ATPL_H = 'atpl_h', 'ATPL(H)'


class ExamSubject(models.TextChoices):
    """EASA theoretical knowledge examination subjects."""
    # All Licenses
    AIR_LAW = '010', 'Air Law (010)'
    AIRFRAMES = '021', 'Airframe & Systems (021)'
    INSTRUMENTATION = '022', 'Instrumentation (022)'
    MASS_BALANCE = '031', 'Mass and Balance (031)'
    PERFORMANCE = '032', 'Performance (032)'
    FLIGHT_PLANNING = '033', 'Flight Planning & Monitoring (033)'
    HUMAN_PERFORMANCE = '040', 'Human Performance (040)'
    METEOROLOGY = '050', 'Meteorology (050)'
    NAVIGATION_GENERAL = '061', 'General Navigation (061)'
    RADIO_NAVIGATION = '062', 'Radio Navigation (062)'
    OPERATIONAL_PROCEDURES = '070', 'Operational Procedures (070)'
    PRINCIPLES_FLIGHT = '080', 'Principles of Flight (080)'
    COMMUNICATIONS_VFR = '091', 'VFR Communications (091)'
    COMMUNICATIONS_IFR = '092', 'IFR Communications (092)'


class ExamStatus(models.TextChoices):
    """Theoretical exam status."""
    SCHEDULED = 'scheduled', 'Scheduled'
    IN_PROGRESS = 'in_progress', 'In Progress'
    PASSED = 'passed', 'Passed'
    FAILED = 'failed', 'Failed'
    DEFERRED = 'deferred', 'Deferred'
    EXPIRED = 'expired', 'Expired'
    CANCELLED = 'cancelled', 'Cancelled'


# =============================================================================
# FCL.025 Requirements
# =============================================================================
class FCL025Requirements:
    """
    EASA FCL.025 Theoretical Knowledge Examination Requirements.

    Key requirements:
    - Pass mark: 75% per subject
    - ATPL: 18-month period to pass all exams
    - IR: 18-month period
    - CPL/PPL: Acceptance period
    - Maximum 4 attempts per subject
    - All subjects valid for 36 months from pass date
    """

    # Pass Mark
    PASS_MARK_PERCENTAGE = 75

    # Examination Periods
    ATPL_EXAM_PERIOD_MONTHS = 18  # Complete all exams within
    IR_EXAM_PERIOD_MONTHS = 18
    CPL_EXAM_PERIOD_MONTHS = 18
    PPL_EXAM_PERIOD_MONTHS = 18

    # Validity
    THEORY_VALIDITY_MONTHS = 36  # Valid for skill test

    # Attempts
    MAX_ATTEMPTS_PER_SUBJECT = 4
    MAX_SITTINGS = 6  # Total sittings allowed

    # ATPL Subjects
    ATPL_SUBJECTS = [
        ExamSubject.AIR_LAW,
        ExamSubject.AIRFRAMES,
        ExamSubject.INSTRUMENTATION,
        ExamSubject.MASS_BALANCE,
        ExamSubject.PERFORMANCE,
        ExamSubject.FLIGHT_PLANNING,
        ExamSubject.HUMAN_PERFORMANCE,
        ExamSubject.METEOROLOGY,
        ExamSubject.NAVIGATION_GENERAL,
        ExamSubject.RADIO_NAVIGATION,
        ExamSubject.OPERATIONAL_PROCEDURES,
        ExamSubject.PRINCIPLES_FLIGHT,
        ExamSubject.COMMUNICATIONS_IFR,
    ]

    # PPL Subjects (combined syllabus)
    PPL_SUBJECTS = [
        ExamSubject.AIR_LAW,
        ExamSubject.HUMAN_PERFORMANCE,
        ExamSubject.METEOROLOGY,
        ExamSubject.COMMUNICATIONS_VFR,
        ExamSubject.PRINCIPLES_FLIGHT,
        ExamSubject.OPERATIONAL_PROCEDURES,
        ExamSubject.PERFORMANCE,
        ExamSubject.NAVIGATION_GENERAL,
    ]

    # IR Subjects
    IR_SUBJECTS = [
        ExamSubject.AIR_LAW,
        ExamSubject.METEOROLOGY,
        ExamSubject.RADIO_NAVIGATION,
        ExamSubject.COMMUNICATIONS_IFR,
        ExamSubject.FLIGHT_PLANNING,
        ExamSubject.HUMAN_PERFORMANCE,
    ]


class TheoreticalExamEnrollment(models.Model):
    """
    Pilot enrollment for theoretical knowledge examinations.

    Tracks the overall examination process for a license type.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    organization_id = models.UUIDField(db_index=True)
    user_id = models.UUIDField(db_index=True)

    # Enrollment Details
    license_type = models.CharField(
        max_length=20,
        choices=ExamLicenseType.choices
    )
    enrollment_date = models.DateField(
        help_text='Date of first exam sitting'
    )
    completion_deadline = models.DateField(
        help_text='Must complete all exams by this date'
    )

    # Status
    status = models.CharField(
        max_length=20,
        choices=[
            ('active', 'Active'),
            ('completed', 'Completed - All Passed'),
            ('failed', 'Failed - Maximum Attempts'),
            ('expired', 'Expired'),
        ],
        default='active'
    )

    # Progress
    subjects_required = ArrayField(
        models.CharField(max_length=10),
        default=list,
        help_text='Subjects required for this license'
    )
    subjects_passed = ArrayField(
        models.CharField(max_length=10),
        default=list,
        blank=True
    )
    subjects_failed = ArrayField(
        models.CharField(max_length=10),
        default=list,
        blank=True
    )

    # Sittings
    total_sittings = models.PositiveIntegerField(
        default=0,
        help_text='Total exam sittings used'
    )
    max_sittings = models.PositiveIntegerField(
        default=6,
        help_text='Maximum sittings allowed'
    )

    # Validity (after all passed)
    all_passed_date = models.DateField(
        blank=True,
        null=True,
        help_text='Date when all subjects passed'
    )
    validity_expiry = models.DateField(
        blank=True,
        null=True,
        help_text='Theory validity expiry for skill test'
    )

    # ATO
    ato_name = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text='Approved Training Organization'
    )
    ato_approval_number = models.CharField(
        max_length=50,
        blank=True,
        null=True
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
        db_table = 'theoretical_exam_enrollments'
        ordering = ['-enrollment_date']
        indexes = [
            models.Index(fields=['organization_id', 'user_id']),
            models.Index(fields=['license_type']),
            models.Index(fields=['status']),
        ]
        unique_together = [['user_id', 'license_type']]

    def __str__(self) -> str:
        return f"{self.get_license_type_display()} - {self.status}"

    @property
    def is_within_deadline(self) -> bool:
        """Check if still within completion deadline."""
        return date.today() <= self.completion_deadline

    @property
    def days_remaining(self) -> int:
        """Days remaining until deadline."""
        return (self.completion_deadline - date.today()).days

    @property
    def progress_percentage(self) -> float:
        """Calculate completion percentage."""
        if not self.subjects_required:
            return 0.0
        return (len(self.subjects_passed) / len(self.subjects_required)) * 100

    @property
    def is_complete(self) -> bool:
        """Check if all subjects passed."""
        if not self.subjects_required:
            return False
        return set(self.subjects_passed) >= set(self.subjects_required)

    @property
    def theory_is_valid(self) -> bool:
        """Check if theory is still valid for skill test."""
        if not self.validity_expiry:
            return False
        return date.today() <= self.validity_expiry

    def mark_subject_passed(self, subject: str, pass_date: date) -> None:
        """Mark a subject as passed."""
        if subject not in self.subjects_passed:
            self.subjects_passed.append(subject)
        if subject in self.subjects_failed:
            self.subjects_failed.remove(subject)

        # Check if all passed
        if self.is_complete:
            self.all_passed_date = pass_date
            self.validity_expiry = pass_date + relativedelta(
                months=FCL025Requirements.THEORY_VALIDITY_MONTHS
            )
            self.status = 'completed'

        self.save()

    def get_progress_summary(self) -> Dict[str, Any]:
        """Get examination progress summary."""
        return {
            'enrollment_id': str(self.id),
            'license_type': self.license_type,
            'status': self.status,
            'enrollment_date': self.enrollment_date.isoformat(),
            'completion_deadline': self.completion_deadline.isoformat(),
            'days_remaining': self.days_remaining,
            'is_within_deadline': self.is_within_deadline,
            'subjects_required': self.subjects_required,
            'subjects_passed': self.subjects_passed,
            'subjects_remaining': [
                s for s in self.subjects_required
                if s not in self.subjects_passed
            ],
            'progress_percentage': self.progress_percentage,
            'sittings_used': self.total_sittings,
            'sittings_remaining': self.max_sittings - self.total_sittings,
            'theory_validity_expiry': (
                self.validity_expiry.isoformat()
                if self.validity_expiry else None
            ),
            'theory_is_valid': self.theory_is_valid,
        }


class TheoreticalExamResult(models.Model):
    """
    Individual theoretical exam result.

    Records each exam attempt with score and result.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    organization_id = models.UUIDField(db_index=True)
    enrollment_id = models.UUIDField(db_index=True)
    user_id = models.UUIDField(db_index=True)

    # Exam Details
    subject = models.CharField(
        max_length=10,
        choices=ExamSubject.choices
    )
    exam_date = models.DateField()
    sitting_number = models.PositiveIntegerField(
        help_text='Which sitting this exam was in'
    )
    attempt_number = models.PositiveIntegerField(
        help_text='Attempt number for this subject'
    )

    # Score
    score_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text='Score as percentage'
    )
    questions_total = models.PositiveIntegerField(
        blank=True,
        null=True
    )
    questions_correct = models.PositiveIntegerField(
        blank=True,
        null=True
    )
    pass_mark = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('75.00')
    )

    # Status
    status = models.CharField(
        max_length=20,
        choices=ExamStatus.choices
    )

    # Validity (if passed)
    valid_until = models.DateField(
        blank=True,
        null=True,
        help_text='Subject validity for skill test'
    )

    # Exam Center
    exam_center = models.CharField(
        max_length=200,
        blank=True,
        null=True
    )
    exam_center_id = models.CharField(
        max_length=50,
        blank=True,
        null=True
    )
    invigilator_name = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    # Reference
    exam_reference = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text='CAA/Exam system reference number'
    )

    # Time
    time_allowed_minutes = models.PositiveIntegerField(
        blank=True,
        null=True
    )
    time_taken_minutes = models.PositiveIntegerField(
        blank=True,
        null=True
    )

    # Feedback
    weak_areas = ArrayField(
        models.CharField(max_length=100),
        default=list,
        blank=True,
        help_text='Topics needing improvement'
    )
    feedback = models.TextField(blank=True, null=True)

    # Notes
    notes = models.TextField(blank=True, null=True)

    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'theoretical_exam_results'
        ordering = ['-exam_date', 'subject']
        indexes = [
            models.Index(fields=['organization_id', 'user_id']),
            models.Index(fields=['enrollment_id']),
            models.Index(fields=['subject']),
            models.Index(fields=['exam_date']),
            models.Index(fields=['status']),
        ]

    def __str__(self) -> str:
        return f"{self.get_subject_display()} - {self.score_percentage}% - {self.status}"

    @property
    def is_passed(self) -> bool:
        """Check if exam was passed."""
        return self.score_percentage >= self.pass_mark

    @property
    def is_valid(self) -> bool:
        """Check if result is still valid."""
        if self.status != ExamStatus.PASSED:
            return False
        if not self.valid_until:
            return False
        return date.today() <= self.valid_until

    def get_result_summary(self) -> Dict[str, Any]:
        """Get exam result summary."""
        return {
            'result_id': str(self.id),
            'subject': self.subject,
            'subject_name': self.get_subject_display(),
            'exam_date': self.exam_date.isoformat(),
            'attempt_number': self.attempt_number,
            'score_percentage': float(self.score_percentage),
            'pass_mark': float(self.pass_mark),
            'status': self.status,
            'is_passed': self.is_passed,
            'is_valid': self.is_valid,
            'valid_until': self.valid_until.isoformat() if self.valid_until else None,
            'weak_areas': self.weak_areas,
        }


class TheoreticalExamSchedule(models.Model):
    """
    Scheduled theoretical exams.

    Tracks upcoming exam bookings.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    organization_id = models.UUIDField(db_index=True)
    enrollment_id = models.UUIDField(db_index=True)
    user_id = models.UUIDField(db_index=True)

    # Schedule Details
    subjects = ArrayField(
        models.CharField(max_length=10),
        help_text='Subjects scheduled for this sitting'
    )
    scheduled_date = models.DateField()
    scheduled_time = models.TimeField(blank=True, null=True)

    # Sitting
    sitting_number = models.PositiveIntegerField()

    # Status
    status = models.CharField(
        max_length=20,
        choices=[
            ('scheduled', 'Scheduled'),
            ('confirmed', 'Confirmed'),
            ('completed', 'Completed'),
            ('cancelled', 'Cancelled'),
            ('no_show', 'No Show'),
        ],
        default='scheduled'
    )

    # Location
    exam_center = models.CharField(max_length=200)
    exam_center_address = models.TextField(blank=True, null=True)

    # Booking Reference
    booking_reference = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    # Notes
    notes = models.TextField(blank=True, null=True)

    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'theoretical_exam_schedules'
        ordering = ['scheduled_date']
        indexes = [
            models.Index(fields=['organization_id', 'user_id']),
            models.Index(fields=['scheduled_date']),
            models.Index(fields=['status']),
        ]

    def __str__(self) -> str:
        return f"{self.scheduled_date} - {', '.join(self.subjects)}"
