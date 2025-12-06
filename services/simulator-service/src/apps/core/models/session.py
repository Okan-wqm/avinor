# services/simulator-service/src/apps/core/models/session.py
"""
FSTD Session Model

Tracks simulator training sessions, assessments, and logbook entries.
Compliant with EASA training record requirements.
"""

import uuid
from decimal import Decimal
from django.db import models
from django.utils import timezone


class SessionType(models.TextChoices):
    """Types of FSTD sessions"""
    TRAINING = 'training', 'Training'
    PROFICIENCY_CHECK = 'check', 'Proficiency Check'
    REVALIDATION = 'revalidation', 'Revalidation'
    SKILL_TEST = 'skill_test', 'Skill Test'
    LINE_CHECK = 'line_check', 'Line Check'
    FAMILIARIZATION = 'familiarization', 'Familiarization'
    RECURRENT = 'recurrent', 'Recurrent Training'
    TYPE_RATING = 'type_rating', 'Type Rating Training'
    MCC = 'mcc', 'MCC Training'
    LOFT = 'loft', 'LOFT (Line Oriented Flight Training)'
    EBT = 'ebt', 'Evidence Based Training'
    EMERGENCY = 'emergency', 'Emergency Training'
    UPSET_RECOVERY = 'upset', 'Upset Prevention and Recovery'


class SessionStatus(models.TextChoices):
    """Session workflow status"""
    SCHEDULED = 'scheduled', 'Scheduled'
    CONFIRMED = 'confirmed', 'Confirmed'
    IN_PROGRESS = 'in_progress', 'In Progress'
    COMPLETED = 'completed', 'Completed'
    CANCELLED = 'cancelled', 'Cancelled'
    NO_SHOW = 'no_show', 'No Show'


class AssessmentResult(models.TextChoices):
    """Overall session assessment results"""
    PASS = 'pass', 'Pass'
    FAIL = 'fail', 'Fail'
    PARTIAL = 'partial', 'Partial Pass'
    INCOMPLETE = 'incomplete', 'Incomplete'
    DEFERRED = 'deferred', 'Deferred'
    NOT_ASSESSED = 'not_assessed', 'Not Assessed'


class FSTDSession(models.Model):
    """
    FSTD Training Session Record

    Tracks each simulator session including:
    - Session scheduling and timing
    - Personnel (trainee, instructor, examiner)
    - Training content and exercises
    - Assessment and grading
    - Signatures and certification
    - Billing information
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    organization_id = models.UUIDField(
        db_index=True,
        help_text="Organization running this session"
    )

    # Device Reference
    fstd_device_id = models.UUIDField(
        db_index=True,
        help_text="FSTD device used for this session"
    )
    fstd_device_name = models.CharField(
        max_length=100,
        blank=True,
        help_text="Device name for display (denormalized)"
    )

    # Booking Reference
    booking_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Related booking from booking-service"
    )

    # Personnel
    trainee_id = models.UUIDField(
        db_index=True,
        help_text="Primary trainee"
    )
    trainee_name = models.CharField(
        max_length=200,
        blank=True,
        help_text="Trainee name (denormalized)"
    )
    second_trainee_id = models.UUIDField(
        null=True,
        blank=True,
        help_text="Second trainee (for MCC, CRM training)"
    )
    second_trainee_name = models.CharField(
        max_length=200,
        blank=True
    )

    instructor_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Instructor conducting the session"
    )
    instructor_name = models.CharField(
        max_length=200,
        blank=True
    )
    instructor_certificate_number = models.CharField(
        max_length=100,
        blank=True,
        help_text="Instructor certificate/license number"
    )

    examiner_id = models.UUIDField(
        null=True,
        blank=True,
        help_text="Examiner (for checks and tests)"
    )
    examiner_name = models.CharField(
        max_length=200,
        blank=True
    )
    examiner_certificate_number = models.CharField(
        max_length=100,
        blank=True,
        help_text="Examiner authorization number"
    )

    # Session Timing
    session_date = models.DateField(
        db_index=True,
        help_text="Date of session"
    )
    scheduled_start = models.DateTimeField(
        help_text="Scheduled start time"
    )
    scheduled_end = models.DateTimeField(
        help_text="Scheduled end time"
    )
    actual_start = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Actual start time"
    )
    actual_end = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Actual end time"
    )

    # Duration
    scheduled_duration_minutes = models.IntegerField(
        help_text="Scheduled duration in minutes"
    )
    actual_duration_minutes = models.IntegerField(
        null=True,
        blank=True,
        help_text="Actual duration in minutes"
    )
    briefing_duration_minutes = models.IntegerField(
        default=0,
        help_text="Pre-session briefing duration"
    )
    debriefing_duration_minutes = models.IntegerField(
        default=0,
        help_text="Post-session debriefing duration"
    )

    # Session Classification
    session_type = models.CharField(
        max_length=30,
        choices=SessionType.choices,
        db_index=True,
        help_text="Type of session"
    )
    status = models.CharField(
        max_length=20,
        choices=SessionStatus.choices,
        default=SessionStatus.SCHEDULED,
        db_index=True
    )

    # Training Context
    training_program_id = models.UUIDField(
        null=True,
        blank=True,
        help_text="Related training program"
    )
    lesson_id = models.UUIDField(
        null=True,
        blank=True,
        help_text="Specific lesson being conducted"
    )
    course_id = models.UUIDField(
        null=True,
        blank=True,
        help_text="Related course"
    )

    # Content & Exercises
    exercises_planned = models.JSONField(
        default=list,
        blank=True,
        help_text="Planned exercises/maneuvers"
    )
    exercises_completed = models.JSONField(
        default=list,
        blank=True,
        help_text="Completed exercises with grades"
    )
    scenario_description = models.TextField(
        blank=True,
        help_text="LOFT/scenario description if applicable"
    )

    # Conditions Simulated
    aircraft_type = models.CharField(
        max_length=50,
        blank=True,
        help_text="Aircraft type simulated (e.g., B737-800)"
    )
    departure_airport = models.CharField(
        max_length=4,
        blank=True,
        help_text="Simulated departure airport ICAO"
    )
    arrival_airport = models.CharField(
        max_length=4,
        blank=True,
        help_text="Simulated arrival airport ICAO"
    )
    weather_conditions = models.JSONField(
        default=dict,
        blank=True,
        help_text="Weather conditions simulated"
    )
    malfunctions_introduced = models.JSONField(
        default=list,
        blank=True,
        help_text="Malfunctions/failures introduced"
    )

    # Assessment & Grading
    assessment_result = models.CharField(
        max_length=20,
        choices=AssessmentResult.choices,
        default=AssessmentResult.NOT_ASSESSED,
        db_index=True,
        help_text="Overall session result"
    )
    grade = models.CharField(
        max_length=20,
        blank=True,
        help_text="Overall grade (1-5, A-F, etc.)"
    )

    # CBTA Competencies
    competency_grades = models.JSONField(
        default=dict,
        blank=True,
        help_text="Competency-based grades (SAW, COM, FPM, etc.)"
    )

    # Remarks & Feedback
    instructor_remarks = models.TextField(
        blank=True,
        help_text="Instructor's remarks and feedback"
    )
    trainee_remarks = models.TextField(
        blank=True,
        help_text="Trainee's self-assessment/remarks"
    )
    areas_for_improvement = models.TextField(
        blank=True,
        help_text="Identified areas for improvement"
    )
    strengths = models.TextField(
        blank=True,
        help_text="Identified strengths"
    )
    recommendations = models.TextField(
        blank=True,
        help_text="Recommendations for further training"
    )

    # Signatures (EASA requirement)
    instructor_signature = models.JSONField(
        null=True,
        blank=True,
        help_text="Instructor digital signature data"
    )
    instructor_signed_at = models.DateTimeField(
        null=True,
        blank=True
    )
    trainee_signature = models.JSONField(
        null=True,
        blank=True,
        help_text="Trainee digital signature data"
    )
    trainee_signed_at = models.DateTimeField(
        null=True,
        blank=True
    )
    examiner_signature = models.JSONField(
        null=True,
        blank=True,
        help_text="Examiner digital signature data"
    )
    examiner_signed_at = models.DateTimeField(
        null=True,
        blank=True
    )

    # Certification
    certificate_issued = models.BooleanField(
        default=False,
        help_text="Was a certificate/endorsement issued"
    )
    certificate_type = models.CharField(
        max_length=100,
        blank=True,
        help_text="Type of certificate issued"
    )
    certificate_number = models.CharField(
        max_length=100,
        blank=True
    )
    certificate_id = models.UUIDField(
        null=True,
        blank=True,
        help_text="Reference to certificate-service"
    )

    # Billing
    is_billed = models.BooleanField(
        default=False,
        help_text="Has this session been billed"
    )
    billing_status = models.CharField(
        max_length=20,
        blank=True,
        choices=[
            ('pending', 'Pending'),
            ('billed', 'Billed'),
            ('paid', 'Paid'),
            ('waived', 'Waived'),
        ]
    )
    device_charge = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="FSTD usage charge"
    )
    instructor_charge = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Instructor fee"
    )
    other_charges = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Other charges"
    )
    total_charge = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Total session charge"
    )
    transaction_id = models.UUIDField(
        null=True,
        blank=True,
        help_text="Reference to finance-service transaction"
    )

    # Documents
    documents = models.JSONField(
        default=list,
        blank=True,
        help_text="Attached documents (briefing materials, etc.)"
    )
    recording_url = models.URLField(
        blank=True,
        help_text="Session recording URL if applicable"
    )

    # Notes
    notes = models.TextField(
        blank=True,
        help_text="General notes"
    )
    internal_notes = models.TextField(
        blank=True,
        help_text="Internal notes (not visible to trainee)"
    )

    # Cancellation
    cancelled_at = models.DateTimeField(
        null=True,
        blank=True
    )
    cancelled_by = models.UUIDField(
        null=True,
        blank=True
    )
    cancellation_reason = models.TextField(
        blank=True
    )

    # Metadata
    metadata = models.JSONField(
        default=dict,
        blank=True
    )

    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.UUIDField(null=True, blank=True)
    updated_by = models.UUIDField(null=True, blank=True)

    class Meta:
        db_table = 'fstd_sessions'
        ordering = ['-session_date', '-scheduled_start']
        verbose_name = 'FSTD Session'
        verbose_name_plural = 'FSTD Sessions'
        indexes = [
            models.Index(fields=['organization_id', 'session_date']),
            models.Index(fields=['trainee_id', 'session_date']),
            models.Index(fields=['instructor_id', 'session_date']),
            models.Index(fields=['fstd_device_id', 'session_date']),
            models.Index(fields=['status']),
            models.Index(fields=['session_type']),
        ]

    def __str__(self):
        return f"{self.session_type} - {self.trainee_name} - {self.session_date}"

    @property
    def duration_hours(self):
        """Get session duration in hours"""
        minutes = self.actual_duration_minutes or self.scheduled_duration_minutes
        return Decimal(minutes) / Decimal(60) if minutes else Decimal(0)

    @property
    def total_duration_hours(self):
        """Get total time including briefing/debriefing"""
        total_minutes = (
            (self.actual_duration_minutes or self.scheduled_duration_minutes or 0) +
            self.briefing_duration_minutes +
            self.debriefing_duration_minutes
        )
        return Decimal(total_minutes) / Decimal(60)

    @property
    def is_signed(self):
        """Check if session is fully signed"""
        return bool(self.instructor_signed_at and self.trainee_signed_at)

    def start_session(self, user_id=None):
        """Start the session"""
        self.status = SessionStatus.IN_PROGRESS
        self.actual_start = timezone.now()
        self.updated_by = user_id
        self.save(update_fields=['status', 'actual_start', 'updated_at', 'updated_by'])

    def complete_session(self, user_id=None):
        """Complete the session"""
        self.status = SessionStatus.COMPLETED
        self.actual_end = timezone.now()
        if self.actual_start:
            delta = self.actual_end - self.actual_start
            self.actual_duration_minutes = int(delta.total_seconds() / 60)
        self.updated_by = user_id
        self.save()

    def cancel_session(self, reason: str, user_id=None):
        """Cancel the session"""
        self.status = SessionStatus.CANCELLED
        self.cancelled_at = timezone.now()
        self.cancelled_by = user_id
        self.cancellation_reason = reason
        self.save()

    def sign_instructor(self, signature_data: dict, user_id=None):
        """Record instructor signature"""
        self.instructor_signature = signature_data
        self.instructor_signed_at = timezone.now()
        self.updated_by = user_id
        self.save(update_fields=['instructor_signature', 'instructor_signed_at', 'updated_at', 'updated_by'])

    def sign_trainee(self, signature_data: dict, user_id=None):
        """Record trainee signature"""
        self.trainee_signature = signature_data
        self.trainee_signed_at = timezone.now()
        self.updated_by = user_id
        self.save(update_fields=['trainee_signature', 'trainee_signed_at', 'updated_at', 'updated_by'])

    def calculate_charges(self, device_hourly_rate: Decimal, instructor_hourly_rate: Decimal = None):
        """Calculate session charges"""
        hours = self.duration_hours

        self.device_charge = hours * device_hourly_rate

        if instructor_hourly_rate and self.instructor_id:
            instructor_hours = self.total_duration_hours  # Include briefing/debriefing
            self.instructor_charge = instructor_hours * instructor_hourly_rate

        self.total_charge = (
            (self.device_charge or Decimal(0)) +
            (self.instructor_charge or Decimal(0)) +
            (self.other_charges or Decimal(0))
        )
        self.save(update_fields=['device_charge', 'instructor_charge', 'total_charge', 'updated_at'])

    def get_logbook_entry(self):
        """Generate logbook entry data for this session"""
        return {
            'date': self.session_date,
            'fstd_type': self.fstd_device_name,
            'session_type': self.get_session_type_display(),
            'total_time': str(self.duration_hours),
            'instructor': self.instructor_name,
            'exercises': self.exercises_completed,
            'remarks': self.instructor_remarks,
            'result': self.get_assessment_result_display(),
        }

    @classmethod
    def get_trainee_sessions(cls, trainee_id, organization_id=None, start_date=None, end_date=None):
        """Get all sessions for a trainee"""
        queryset = cls.objects.filter(trainee_id=trainee_id)

        if organization_id:
            queryset = queryset.filter(organization_id=organization_id)
        if start_date:
            queryset = queryset.filter(session_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(session_date__lte=end_date)

        return queryset.order_by('-session_date')

    @classmethod
    def get_trainee_total_hours(cls, trainee_id, organization_id=None, fstd_type=None):
        """Calculate total simulator hours for a trainee"""
        from django.db.models import Sum

        queryset = cls.objects.filter(
            trainee_id=trainee_id,
            status=SessionStatus.COMPLETED
        )

        if organization_id:
            queryset = queryset.filter(organization_id=organization_id)

        result = queryset.aggregate(
            total_minutes=Sum('actual_duration_minutes')
        )

        total_minutes = result['total_minutes'] or 0
        return Decimal(total_minutes) / Decimal(60)
