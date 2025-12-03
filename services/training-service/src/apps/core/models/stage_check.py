# services/training-service/src/apps/core/models/stage_check.py
"""
Stage Check Model

Manages stage check evaluations for training progress milestones.
"""

import uuid
from decimal import Decimal
from typing import List, Dict, Any, Optional
from datetime import date, datetime

from django.db import models
from django.utils import timezone


class StageCheck(models.Model):
    """
    Stage check model.

    Records stage check evaluations which are milestone assessments
    in a training program.
    """

    class CheckType(models.TextChoices):
        ORAL = 'oral', 'Oral Examination'
        FLIGHT = 'flight', 'Flight Check'
        COMBINED = 'combined', 'Combined Oral & Flight'
        SIMULATOR = 'simulator', 'Simulator Check'
        WRITTEN = 'written', 'Written Examination'
        PRACTICAL = 'practical', 'Practical Assessment'

    class Status(models.TextChoices):
        SCHEDULED = 'scheduled', 'Scheduled'
        IN_PROGRESS = 'in_progress', 'In Progress'
        COMPLETED = 'completed', 'Completed'
        CANCELLED = 'cancelled', 'Cancelled'
        DEFERRED = 'deferred', 'Deferred'

    class Result(models.TextChoices):
        PASS = 'pass', 'Pass'
        FAIL = 'fail', 'Fail'
        INCOMPLETE = 'incomplete', 'Incomplete'
        DEFERRED = 'deferred', 'Deferred'
        SATISFACTORY = 'satisfactory', 'Satisfactory'
        UNSATISFACTORY = 'unsatisfactory', 'Unsatisfactory'

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    organization_id = models.UUIDField(db_index=True)

    # ==========================================================================
    # Relationships
    # ==========================================================================
    enrollment = models.ForeignKey(
        'StudentEnrollment',
        on_delete=models.CASCADE,
        related_name='stage_checks'
    )
    stage_id = models.UUIDField(
        help_text="Stage being checked"
    )
    examiner_id = models.UUIDField(
        blank=True,
        null=True,
        help_text="Examiner conducting the check"
    )
    recommending_instructor_id = models.UUIDField(
        blank=True,
        null=True,
        help_text="Instructor who recommended for stage check"
    )

    # ==========================================================================
    # Check Type
    # ==========================================================================
    check_type = models.CharField(
        max_length=20,
        choices=CheckType.choices
    )
    check_number = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Stage check reference number"
    )

    # ==========================================================================
    # Scheduling
    # ==========================================================================
    scheduled_date = models.DateField(
        blank=True,
        null=True
    )
    scheduled_time = models.TimeField(
        blank=True,
        null=True
    )
    location = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Location/airport for the check"
    )

    # ==========================================================================
    # Actual Execution
    # ==========================================================================
    actual_date = models.DateField(
        blank=True,
        null=True
    )
    actual_start_time = models.TimeField(
        blank=True,
        null=True
    )
    actual_end_time = models.TimeField(
        blank=True,
        null=True
    )

    # ==========================================================================
    # Flight Details (if applicable)
    # ==========================================================================
    aircraft_id = models.UUIDField(
        blank=True,
        null=True
    )
    flight_record_id = models.UUIDField(
        blank=True,
        null=True
    )
    flight_time = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True
    )
    ground_time = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True
    )

    # ==========================================================================
    # Weather (if applicable)
    # ==========================================================================
    weather_conditions = models.JSONField(
        default=dict,
        help_text='{"wind": "15G20", "visibility": "10SM", "ceiling": "SCT050"}'
    )

    # ==========================================================================
    # Status and Result
    # ==========================================================================
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.SCHEDULED
    )
    result = models.CharField(
        max_length=20,
        choices=Result.choices,
        blank=True,
        null=True
    )
    is_passed = models.BooleanField(
        default=False
    )

    # ==========================================================================
    # Grading
    # ==========================================================================
    oral_grade = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Oral examination grade"
    )
    flight_grade = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Flight check grade"
    )
    overall_grade = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Overall stage check grade"
    )
    min_passing_grade = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('70.00'),
        help_text="Minimum grade required to pass"
    )

    # ==========================================================================
    # Attempt Tracking
    # ==========================================================================
    attempt_number = models.PositiveIntegerField(
        default=1
    )
    max_attempts = models.PositiveIntegerField(
        default=3,
        help_text="Maximum allowed attempts"
    )
    previous_attempt_id = models.UUIDField(
        blank=True,
        null=True,
        help_text="Reference to previous failed attempt"
    )

    # ==========================================================================
    # Prerequisites Check
    # ==========================================================================
    prerequisites_verified = models.BooleanField(
        default=False
    )
    prerequisites_verification_date = models.DateTimeField(
        blank=True,
        null=True
    )
    prerequisites_notes = models.TextField(
        blank=True,
        null=True
    )

    # ==========================================================================
    # Oral Examination Details
    # ==========================================================================
    oral_topics = models.JSONField(
        default=list,
        help_text='[{"topic": "Weather", "grade": 85, "notes": "..."}]'
    )
    oral_duration_minutes = models.PositiveIntegerField(
        blank=True,
        null=True
    )

    # ==========================================================================
    # Flight Check Details
    # ==========================================================================
    flight_maneuvers = models.JSONField(
        default=list,
        help_text='[{"maneuver": "Steep Turns", "grade": 90, "tolerances": {...}}]'
    )
    flight_areas = models.JSONField(
        default=list,
        help_text="Areas of operation covered"
    )
    special_emphasis_areas = models.JSONField(
        default=list,
        help_text="Special emphasis areas evaluated"
    )

    # ==========================================================================
    # Examiner Feedback
    # ==========================================================================
    examiner_comments = models.TextField(
        blank=True,
        null=True
    )
    areas_of_concern = models.JSONField(
        default=list,
        help_text="Areas needing attention"
    )
    recommendations = models.TextField(
        blank=True,
        null=True
    )
    additional_training_required = models.JSONField(
        default=list,
        help_text="Additional training items required before recheck"
    )

    # ==========================================================================
    # Disapproval Details (if failed)
    # ==========================================================================
    disapproval_reasons = models.JSONField(
        default=list,
        help_text="Specific reasons for failure"
    )
    recheck_items = models.JSONField(
        default=list,
        help_text="Items to be rechecked"
    )
    remedial_training_completed = models.BooleanField(
        default=False
    )
    remedial_training_date = models.DateField(
        blank=True,
        null=True
    )
    remedial_training_hours = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True
    )

    # ==========================================================================
    # Sign-offs
    # ==========================================================================
    examiner_signoff = models.BooleanField(default=False)
    examiner_signoff_date = models.DateTimeField(
        blank=True,
        null=True
    )
    student_signoff = models.BooleanField(default=False)
    student_signoff_date = models.DateTimeField(
        blank=True,
        null=True
    )

    # ==========================================================================
    # Document References
    # ==========================================================================
    form_number = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Official form number (e.g., 8410)"
    )
    document_url = models.URLField(
        max_length=500,
        blank=True,
        null=True
    )

    # ==========================================================================
    # Cancellation
    # ==========================================================================
    cancellation_reason = models.TextField(
        blank=True,
        null=True
    )
    cancelled_by_id = models.UUIDField(
        blank=True,
        null=True
    )
    cancelled_at = models.DateTimeField(
        blank=True,
        null=True
    )

    # ==========================================================================
    # Metadata
    # ==========================================================================
    metadata = models.JSONField(default=dict)
    notes = models.TextField(
        blank=True,
        null=True
    )

    # ==========================================================================
    # Timestamps
    # ==========================================================================
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'stage_checks'
        ordering = ['-scheduled_date', '-created_at']
        indexes = [
            models.Index(fields=['enrollment']),
            models.Index(fields=['stage_id']),
            models.Index(fields=['examiner_id']),
            models.Index(fields=['status']),
            models.Index(fields=['result']),
            models.Index(fields=['scheduled_date']),
        ]

    def __str__(self):
        return f"Stage Check: {self.enrollment.student_id} - Stage {self.stage_id}"

    # ==========================================================================
    # Properties
    # ==========================================================================

    @property
    def stage_name(self) -> Optional[str]:
        """Get the name of the stage being checked."""
        stage = self.enrollment.program.get_stage(str(self.stage_id))
        return stage.get('name') if stage else None

    @property
    def is_final_attempt(self) -> bool:
        """Check if this is the final allowed attempt."""
        return self.attempt_number >= self.max_attempts

    @property
    def can_retry(self) -> bool:
        """Check if student can retry the stage check."""
        return (
            not self.is_passed and
            self.attempt_number < self.max_attempts
        )

    @property
    def total_check_time(self) -> Decimal:
        """Get total time for the check."""
        total = Decimal('0')
        if self.flight_time:
            total += self.flight_time
        if self.ground_time:
            total += self.ground_time
        return total

    @property
    def duration_minutes(self) -> Optional[int]:
        """Get duration in minutes if times are available."""
        if self.actual_start_time and self.actual_end_time:
            start = datetime.combine(date.today(), self.actual_start_time)
            end = datetime.combine(date.today(), self.actual_end_time)
            return int((end - start).total_seconds() / 60)
        return None

    # ==========================================================================
    # Methods
    # ==========================================================================

    def schedule(
        self,
        scheduled_date: date,
        scheduled_time=None,
        examiner_id: uuid.UUID = None,
        location: str = None
    ) -> None:
        """Schedule the stage check."""
        self.scheduled_date = scheduled_date
        if scheduled_time:
            self.scheduled_time = scheduled_time
        if examiner_id:
            self.examiner_id = examiner_id
        if location:
            self.location = location
        self.status = self.Status.SCHEDULED
        self.save()

    def start(self) -> None:
        """Mark stage check as in progress."""
        self.status = self.Status.IN_PROGRESS
        self.actual_date = date.today()
        self.actual_start_time = timezone.now().time()
        self.save()

    def complete(
        self,
        result: str,
        overall_grade: Decimal = None,
        oral_grade: Decimal = None,
        flight_grade: Decimal = None,
        examiner_comments: str = None
    ) -> None:
        """Complete the stage check with result."""
        self.status = self.Status.COMPLETED
        self.result = result
        self.actual_end_time = timezone.now().time()

        if overall_grade is not None:
            self.overall_grade = overall_grade
        if oral_grade is not None:
            self.oral_grade = oral_grade
        if flight_grade is not None:
            self.flight_grade = flight_grade
        if examiner_comments:
            self.examiner_comments = examiner_comments

        # Determine if passed
        self.is_passed = result in [
            self.Result.PASS,
            self.Result.SATISFACTORY
        ]

        # Update enrollment statistics
        enrollment = self.enrollment
        if self.is_passed:
            enrollment.stage_checks_passed += 1
        else:
            enrollment.stage_checks_failed += 1
        enrollment.save()

        self.save()

    def pass_check(
        self,
        overall_grade: Decimal = None,
        examiner_comments: str = None
    ) -> None:
        """Mark stage check as passed."""
        self.complete(
            result=self.Result.PASS,
            overall_grade=overall_grade,
            examiner_comments=examiner_comments
        )

        # Advance student to next stage
        next_stage = self.enrollment.program.get_next_stage(str(self.stage_id))
        if next_stage:
            self.enrollment.advance_to_stage(next_stage.get('id'))

    def fail_check(
        self,
        disapproval_reasons: List[str] = None,
        recheck_items: List[str] = None,
        additional_training: List[str] = None,
        examiner_comments: str = None
    ) -> None:
        """Mark stage check as failed."""
        self.complete(
            result=self.Result.FAIL,
            examiner_comments=examiner_comments
        )

        if disapproval_reasons:
            self.disapproval_reasons = disapproval_reasons
        if recheck_items:
            self.recheck_items = recheck_items
        if additional_training:
            self.additional_training_required = additional_training

        self.save()

    def cancel(self, reason: str, cancelled_by: uuid.UUID) -> None:
        """Cancel the stage check."""
        self.status = self.Status.CANCELLED
        self.cancellation_reason = reason
        self.cancelled_by_id = cancelled_by
        self.cancelled_at = timezone.now()
        self.save()

    def defer(self, reason: str) -> None:
        """Defer the stage check."""
        self.status = self.Status.DEFERRED
        self.result = self.Result.DEFERRED
        self.examiner_comments = reason
        self.save()

    def verify_prerequisites(self, notes: str = None) -> bool:
        """Verify prerequisites for stage check."""
        enrollment = self.enrollment

        # Check if all lessons in the stage are completed
        from .completion import LessonCompletion
        from .syllabus import SyllabusLesson

        stage_lessons = SyllabusLesson.objects.filter(
            program=enrollment.program,
            stage_id=self.stage_id,
            status='active'
        )

        completed_ids = set(
            str(c.lesson_id) for c in
            LessonCompletion.objects.filter(
                enrollment=enrollment,
                is_completed=True
            )
        )

        all_complete = all(
            str(lesson.id) in completed_ids
            for lesson in stage_lessons
        )

        self.prerequisites_verified = all_complete
        self.prerequisites_verification_date = timezone.now()

        if notes:
            self.prerequisites_notes = notes

        self.save()
        return all_complete

    def record_remedial_training(
        self,
        training_date: date,
        hours: Decimal
    ) -> None:
        """Record completed remedial training."""
        self.remedial_training_completed = True
        self.remedial_training_date = training_date
        self.remedial_training_hours = hours
        self.save()

    def examiner_sign(self) -> None:
        """Record examiner sign-off."""
        self.examiner_signoff = True
        self.examiner_signoff_date = timezone.now()
        self.save()

    def student_sign(self) -> None:
        """Record student sign-off."""
        self.student_signoff = True
        self.student_signoff_date = timezone.now()
        self.save()

    def create_recheck(self) -> 'StageCheck':
        """Create a new attempt for recheck."""
        if not self.can_retry:
            raise ValueError("Maximum attempts reached")

        recheck = StageCheck.objects.create(
            organization_id=self.organization_id,
            enrollment=self.enrollment,
            stage_id=self.stage_id,
            check_type=self.check_type,
            attempt_number=self.attempt_number + 1,
            max_attempts=self.max_attempts,
            previous_attempt_id=self.id,
            min_passing_grade=self.min_passing_grade,
        )
        return recheck

    def add_oral_topic(
        self,
        topic: str,
        grade: float,
        notes: str = None
    ) -> None:
        """Add oral examination topic result."""
        topic_data = {
            'topic': topic,
            'grade': grade,
        }
        if notes:
            topic_data['notes'] = notes

        if not self.oral_topics:
            self.oral_topics = []
        self.oral_topics.append(topic_data)
        self.save()

    def add_flight_maneuver(
        self,
        maneuver: str,
        grade: float,
        tolerances: Dict[str, Any] = None,
        notes: str = None
    ) -> None:
        """Add flight maneuver result."""
        maneuver_data = {
            'maneuver': maneuver,
            'grade': grade,
        }
        if tolerances:
            maneuver_data['tolerances'] = tolerances
        if notes:
            maneuver_data['notes'] = notes

        if not self.flight_maneuvers:
            self.flight_maneuvers = []
        self.flight_maneuvers.append(maneuver_data)
        self.save()

    def get_summary(self) -> Dict[str, Any]:
        """Get stage check summary."""
        return {
            'id': str(self.id),
            'enrollment_id': str(self.enrollment_id),
            'stage': {
                'id': str(self.stage_id),
                'name': self.stage_name,
            },
            'check_type': self.check_type,
            'status': self.status,
            'result': self.result,
            'is_passed': self.is_passed,
            'grades': {
                'oral': float(self.oral_grade) if self.oral_grade else None,
                'flight': float(self.flight_grade) if self.flight_grade else None,
                'overall': float(self.overall_grade) if self.overall_grade else None,
            },
            'attempt': {
                'number': self.attempt_number,
                'max': self.max_attempts,
                'can_retry': self.can_retry,
            },
            'dates': {
                'scheduled': self.scheduled_date.isoformat() if self.scheduled_date else None,
                'actual': self.actual_date.isoformat() if self.actual_date else None,
            },
            'examiner_id': str(self.examiner_id) if self.examiner_id else None,
            'signoffs': {
                'examiner': self.examiner_signoff,
                'student': self.student_signoff,
            },
        }
