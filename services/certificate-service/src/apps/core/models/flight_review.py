# services/certificate-service/src/apps/core/models/flight_review.py
"""
Flight Review Model

Biennial Flight Review (BFR) and Proficiency Checks.
Compliant with FAA 14 CFR 61.56 and EASA FCL.
"""

import uuid
from datetime import date, timedelta
from typing import Optional, Dict, Any, List

from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.utils import timezone


class FlightReviewType(models.TextChoices):
    """Flight review type choices."""
    # FAA
    BFR = 'bfr', 'Biennial Flight Review (FAA)'
    IPC = 'ipc', 'Instrument Proficiency Check'
    # EASA
    PROFICIENCY_CHECK = 'proficiency_check', 'Proficiency Check (EASA)'
    LINE_CHECK = 'line_check', 'Line Check'
    OPERATOR_CHECK = 'operator_check', 'Operator Proficiency Check (OPC)'
    LICENSE_SKILL_TEST = 'license_skill_test', 'License Skill Test'
    # Other
    REVALIDATION = 'revalidation', 'Rating Revalidation'
    RENEWAL = 'renewal', 'Rating Renewal'
    RECENCY = 'recency', 'Recency Training'
    COMPETENCY = 'competency', 'Competency Check'


class FlightReviewResult(models.TextChoices):
    """Flight review result choices."""
    PASSED = 'passed', 'Passed'
    FAILED = 'failed', 'Failed'
    INCOMPLETE = 'incomplete', 'Incomplete'
    DEFERRED = 'deferred', 'Deferred'


class FlightReviewStatus(models.TextChoices):
    """Flight review status choices."""
    ACTIVE = 'active', 'Active'
    EXPIRED = 'expired', 'Expired'
    PENDING = 'pending', 'Pending'


class FlightReview(models.Model):
    """
    Flight Review Model.

    Tracks flight reviews, proficiency checks, and skill tests.

    FAA BFR Requirements (14 CFR 61.56):
    - Required every 24 calendar months
    - Minimum 1 hour ground, 1 hour flight
    - Must cover current flight rules and maneuvers

    EASA Proficiency Check (FCL.740):
    - SEP/MEP: Every 24 months
    - IR: Every 12 months
    - Type ratings: Per aircraft type requirements
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    organization_id = models.UUIDField(db_index=True)
    user_id = models.UUIDField(db_index=True)

    # Review Type
    review_type = models.CharField(
        max_length=30,
        choices=FlightReviewType.choices,
        db_index=True
    )

    # Rating/Certificate Reference
    rating_id = models.UUIDField(
        blank=True,
        null=True,
        help_text='Associated rating if applicable'
    )
    certificate_id = models.UUIDField(
        blank=True,
        null=True,
        help_text='Associated certificate if applicable'
    )
    aircraft_type = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text='Aircraft type for type-specific checks'
    )
    aircraft_icao = models.CharField(
        max_length=4,
        blank=True,
        null=True,
        help_text='ICAO aircraft type designator'
    )

    # Review Details
    review_date = models.DateField(db_index=True)
    completion_date = models.DateField(
        blank=True,
        null=True,
        help_text='Date review was completed (if different from start)'
    )
    expiry_date = models.DateField(db_index=True)

    # Result
    result = models.CharField(
        max_length=20,
        choices=FlightReviewResult.choices,
        default=FlightReviewResult.PASSED
    )
    status = models.CharField(
        max_length=20,
        choices=FlightReviewStatus.choices,
        default=FlightReviewStatus.ACTIVE,
        db_index=True
    )

    # Instructor/Examiner
    instructor_id = models.UUIDField(
        db_index=True,
        help_text='Instructor or examiner who conducted the review'
    )
    instructor_name = models.CharField(max_length=255)
    instructor_certificate_number = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    # Training Time
    ground_time_hours = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=0,
        help_text='Ground instruction time in hours'
    )
    flight_time_hours = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=0,
        help_text='Flight time in hours'
    )
    simulator_time_hours = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=0,
        help_text='Simulator time in hours'
    )

    # Aircraft Used
    aircraft_registration = models.CharField(
        max_length=20,
        blank=True,
        null=True
    )
    aircraft_id = models.UUIDField(
        blank=True,
        null=True,
        help_text='Aircraft ID if in system'
    )

    # Topics/Maneuvers Covered
    topics_covered = ArrayField(
        models.CharField(max_length=255),
        default=list,
        blank=True,
        help_text='Ground topics covered'
    )
    maneuvers_performed = ArrayField(
        models.CharField(max_length=255),
        default=list,
        blank=True,
        help_text='Flight maneuvers performed'
    )

    # Graded Maneuvers (for skill tests)
    maneuver_grades = models.JSONField(
        default=dict,
        blank=True,
        help_text='Detailed grades for each maneuver'
    )

    # Areas for Improvement
    areas_satisfactory = ArrayField(
        models.CharField(max_length=255),
        default=list,
        blank=True
    )
    areas_for_improvement = ArrayField(
        models.CharField(max_length=255),
        default=list,
        blank=True
    )
    unsatisfactory_items = ArrayField(
        models.CharField(max_length=255),
        default=list,
        blank=True,
        help_text='Items that did not meet standards'
    )

    # Comments
    instructor_comments = models.TextField(blank=True, null=True)
    pilot_comments = models.TextField(blank=True, null=True)
    recommendations = models.TextField(blank=True, null=True)

    # Document
    document_url = models.URLField(max_length=500, blank=True, null=True)
    document_filename = models.CharField(max_length=255, blank=True, null=True)

    # Logbook Entry
    logbook_entry_text = models.TextField(
        blank=True,
        null=True,
        help_text='Text to be entered in pilot logbook'
    )
    logbook_entry_created = models.BooleanField(default=False)

    # Flight ID (if linked to a flight record)
    flight_id = models.UUIDField(
        blank=True,
        null=True,
        help_text='Associated flight record ID'
    )

    # Verification
    verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(blank=True, null=True)
    verified_by = models.UUIDField(blank=True, null=True)

    # Metadata
    metadata = models.JSONField(default=dict, blank=True)
    regulatory_reference = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text='e.g., FAR 61.56, EASA FCL.740'
    )

    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'flight_reviews'
        ordering = ['-review_date']
        indexes = [
            models.Index(fields=['organization_id', 'user_id']),
            models.Index(fields=['review_type', 'status']),
            models.Index(fields=['expiry_date']),
            models.Index(fields=['instructor_id']),
        ]
        verbose_name = 'Flight Review'
        verbose_name_plural = 'Flight Reviews'

    def __str__(self) -> str:
        return f"{self.get_review_type_display()} - {self.review_date}"

    def save(self, *args, **kwargs):
        """Override save to calculate expiry date."""
        if not self.completion_date:
            self.completion_date = self.review_date

        if not self.expiry_date:
            self.expiry_date = self.calculate_expiry_date()

        # Generate logbook entry text
        if not self.logbook_entry_text and self.result == FlightReviewResult.PASSED:
            self.logbook_entry_text = self.generate_logbook_entry()

        super().save(*args, **kwargs)

    def calculate_expiry_date(self) -> date:
        """
        Calculate expiry date based on review type.

        FAA BFR: End of 24th calendar month
        EASA PC: Varies by rating type
        IPC: End of 6th calendar month
        """
        base_date = self.completion_date or self.review_date

        if self.review_type == FlightReviewType.BFR:
            # FAA: End of 24th calendar month
            year = base_date.year + 2
            month = base_date.month
            # Last day of month
            if month == 12:
                return date(year + 1, 1, 1) - timedelta(days=1)
            else:
                return date(year, month + 1, 1) - timedelta(days=1)

        elif self.review_type == FlightReviewType.IPC:
            # IPC: 6 calendar months
            month = base_date.month + 6
            year = base_date.year
            if month > 12:
                month -= 12
                year += 1
            if month == 12:
                return date(year + 1, 1, 1) - timedelta(days=1)
            else:
                return date(year, month + 1, 1) - timedelta(days=1)

        elif self.review_type == FlightReviewType.PROFICIENCY_CHECK:
            # EASA: Usually 12 or 24 months depending on rating
            # Default to 12 months for safety
            return base_date + timedelta(days=365)

        elif self.review_type in [FlightReviewType.LINE_CHECK, FlightReviewType.OPERATOR_CHECK]:
            # Usually 12 months
            return base_date + timedelta(days=365)

        else:
            # Default to 24 months
            return base_date + timedelta(days=730)

    def generate_logbook_entry(self) -> str:
        """Generate standard logbook entry text."""
        entry_lines = [
            f"{self.get_review_type_display()} - SATISFACTORY",
            f"Date: {self.review_date.strftime('%Y-%m-%d')}",
        ]

        if self.ground_time_hours > 0:
            entry_lines.append(f"Ground: {self.ground_time_hours} hours")
        if self.flight_time_hours > 0:
            entry_lines.append(f"Flight: {self.flight_time_hours} hours")

        if self.regulatory_reference:
            entry_lines.append(f"Per: {self.regulatory_reference}")

        entry_lines.append(f"Instructor: {self.instructor_name}")
        if self.instructor_certificate_number:
            entry_lines.append(f"Cert #: {self.instructor_certificate_number}")

        return '\n'.join(entry_lines)

    @property
    def is_expired(self) -> bool:
        """Check if flight review is expired."""
        return self.expiry_date < date.today()

    @property
    def days_until_expiry(self) -> int:
        """Calculate days until expiry."""
        return (self.expiry_date - date.today()).days

    @property
    def is_expiring_soon(self) -> bool:
        """Check if expiring within 90 days."""
        return 0 < self.days_until_expiry <= 90

    @property
    def is_valid(self) -> bool:
        """Check if flight review is valid."""
        return (
            self.status == FlightReviewStatus.ACTIVE and
            self.result == FlightReviewResult.PASSED and
            not self.is_expired
        )

    @property
    def total_time_hours(self) -> float:
        """Get total training time."""
        return float(
            self.ground_time_hours +
            self.flight_time_hours +
            self.simulator_time_hours
        )

    def get_validity_info(self) -> Dict[str, Any]:
        """Get detailed validity information."""
        return {
            'review_id': str(self.id),
            'user_id': str(self.user_id),
            'review_type': self.review_type,
            'review_type_display': self.get_review_type_display(),
            'review_date': self.review_date.isoformat(),
            'expiry_date': self.expiry_date.isoformat(),
            'result': self.result,
            'status': self.status,
            'is_valid': self.is_valid,
            'is_expired': self.is_expired,
            'is_expiring_soon': self.is_expiring_soon,
            'days_until_expiry': self.days_until_expiry,
            'instructor_name': self.instructor_name,
            'aircraft_type': self.aircraft_type,
            'ground_time': float(self.ground_time_hours),
            'flight_time': float(self.flight_time_hours),
            'total_time': self.total_time_hours,
            'verified': self.verified,
        }

    def update_status(self) -> None:
        """Update status based on current state."""
        if self.result != FlightReviewResult.PASSED:
            return

        if self.is_expired:
            self.status = FlightReviewStatus.EXPIRED
            self.save(update_fields=['status', 'updated_at'])


class SkillTest(models.Model):
    """
    Skill Test Model.

    Tracks practical skill tests for licenses and ratings.
    EASA FCL skill tests and FAA practical tests (checkrides).
    """

    class TestType(models.TextChoices):
        """Skill test type choices."""
        # License Tests
        PPL_SKILL_TEST = 'ppl_skill', 'PPL Skill Test'
        CPL_SKILL_TEST = 'cpl_skill', 'CPL Skill Test'
        ATPL_SKILL_TEST = 'atpl_skill', 'ATPL Skill Test'
        IR_SKILL_TEST = 'ir_skill', 'IR Skill Test'
        # Rating Tests
        TYPE_RATING_TEST = 'type_rating', 'Type Rating Skill Test'
        CLASS_RATING_TEST = 'class_rating', 'Class Rating Skill Test'
        INSTRUCTOR_TEST = 'instructor', 'Instructor Skill Test'
        # FAA
        CHECKRIDE = 'checkride', 'Practical Test (Checkride)'

    class TestResult(models.TextChoices):
        """Skill test result choices."""
        PASS = 'pass', 'Pass'
        FAIL = 'fail', 'Fail'
        PARTIAL_PASS = 'partial', 'Partial Pass'
        DISCONTINUED = 'discontinued', 'Discontinued'

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    organization_id = models.UUIDField(db_index=True)
    user_id = models.UUIDField(db_index=True)

    # Test Details
    test_type = models.CharField(
        max_length=30,
        choices=TestType.choices,
        db_index=True
    )
    test_date = models.DateField(db_index=True)
    result = models.CharField(
        max_length=20,
        choices=TestResult.choices
    )

    # Examiner
    examiner_id = models.UUIDField(
        db_index=True,
        help_text='Examiner who conducted the test'
    )
    examiner_name = models.CharField(max_length=255)
    examiner_number = models.CharField(max_length=100)
    examiner_authority = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text='Examiner authorization (FE, DPE, etc.)'
    )

    # Aircraft/Simulator
    aircraft_type = models.CharField(max_length=50)
    aircraft_icao = models.CharField(max_length=4, blank=True, null=True)
    aircraft_registration = models.CharField(max_length=20, blank=True, null=True)
    is_simulator = models.BooleanField(default=False)
    simulator_level = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text='FFS Level D, FTD, etc.'
    )

    # Time
    oral_time_hours = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=0
    )
    flight_time_hours = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=0
    )

    # Test Sections/Areas
    test_sections = models.JSONField(
        default=dict,
        help_text='Graded test sections and results'
    )
    failed_sections = ArrayField(
        models.CharField(max_length=255),
        default=list,
        blank=True
    )

    # Application/Reference
    application_number = models.CharField(max_length=100, blank=True, null=True)
    iacra_number = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text='FAA IACRA application number'
    )

    # Certificate/License Issued
    certificate_issued = models.BooleanField(default=False)
    certificate_id = models.UUIDField(blank=True, null=True)
    rating_id = models.UUIDField(blank=True, null=True)
    temporary_certificate_number = models.CharField(max_length=100, blank=True, null=True)

    # Comments
    examiner_comments = models.TextField(blank=True, null=True)
    retest_requirements = models.TextField(
        blank=True,
        null=True,
        help_text='Requirements for retest if failed'
    )

    # Document
    document_url = models.URLField(max_length=500, blank=True, null=True)

    # Metadata
    metadata = models.JSONField(default=dict, blank=True)

    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'skill_tests'
        ordering = ['-test_date']
        indexes = [
            models.Index(fields=['organization_id', 'user_id']),
            models.Index(fields=['test_type', 'result']),
            models.Index(fields=['examiner_id']),
        ]

    def __str__(self) -> str:
        return f"{self.get_test_type_display()} - {self.result} - {self.test_date}"

    @property
    def is_passed(self) -> bool:
        """Check if test was passed."""
        return self.result in [self.TestResult.PASS, self.TestResult.PARTIAL_PASS]

    def get_test_info(self) -> Dict[str, Any]:
        """Get test information."""
        return {
            'test_id': str(self.id),
            'user_id': str(self.user_id),
            'test_type': self.test_type,
            'test_type_display': self.get_test_type_display(),
            'test_date': self.test_date.isoformat(),
            'result': self.result,
            'is_passed': self.is_passed,
            'examiner_name': self.examiner_name,
            'aircraft_type': self.aircraft_type,
            'oral_time': float(self.oral_time_hours),
            'flight_time': float(self.flight_time_hours),
            'certificate_issued': self.certificate_issued,
        }
