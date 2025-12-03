# services/training-service/src/apps/core/models/completion.py
"""
Lesson Completion and Exercise Grade Models

Tracks student progress through lessons and exercise performance.
"""

import uuid
from decimal import Decimal
from typing import List, Dict, Any, Optional
from datetime import date, datetime

from django.db import models
from django.db.models import Avg, Count, Q
from django.utils import timezone


class LessonCompletion(models.Model):
    """
    Lesson completion model.

    Records a student's completion of a specific lesson including
    timing, grades, and instructor feedback.
    """

    class Status(models.TextChoices):
        SCHEDULED = 'scheduled', 'Scheduled'
        IN_PROGRESS = 'in_progress', 'In Progress'
        COMPLETED = 'completed', 'Completed'
        INCOMPLETE = 'incomplete', 'Incomplete'
        CANCELLED = 'cancelled', 'Cancelled'
        NO_SHOW = 'no_show', 'No Show'

    class CompletionResult(models.TextChoices):
        PASS = 'pass', 'Pass'
        FAIL = 'fail', 'Fail'
        INCOMPLETE = 'incomplete', 'Incomplete'
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
        related_name='completions'
    )
    lesson = models.ForeignKey(
        'SyllabusLesson',
        on_delete=models.PROTECT,
        related_name='completions'
    )
    instructor_id = models.UUIDField(
        blank=True,
        null=True,
        help_text="Instructor who conducted the lesson"
    )

    # ==========================================================================
    # Flight Information (if applicable)
    # ==========================================================================
    flight_record_id = models.UUIDField(
        blank=True,
        null=True,
        help_text="Reference to flight record"
    )
    aircraft_id = models.UUIDField(
        blank=True,
        null=True,
        help_text="Aircraft used for the lesson"
    )
    booking_id = models.UUIDField(
        blank=True,
        null=True,
        help_text="Associated booking"
    )

    # ==========================================================================
    # Scheduling
    # ==========================================================================
    scheduled_date = models.DateField(
        blank=True,
        null=True
    )
    scheduled_start_time = models.TimeField(
        blank=True,
        null=True
    )
    scheduled_end_time = models.TimeField(
        blank=True,
        null=True
    )

    # ==========================================================================
    # Actual Times
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
    # Duration / Hours
    # ==========================================================================
    flight_time = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Actual flight time in hours"
    )
    ground_time = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Ground instruction time in hours"
    )
    simulator_time = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Simulator time in hours"
    )
    briefing_time = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Pre/post flight briefing time"
    )

    # ==========================================================================
    # Flight Hour Categories
    # ==========================================================================
    dual_time = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True
    )
    solo_time = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True
    )
    pic_time = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True
    )
    cross_country_time = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True
    )
    night_time = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True
    )
    instrument_time = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True
    )
    instrument_actual = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Actual instrument time (not simulated)"
    )
    instrument_simulated = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Simulated instrument time (hood)"
    )

    # ==========================================================================
    # Landings
    # ==========================================================================
    landings_day = models.PositiveIntegerField(default=0)
    landings_night = models.PositiveIntegerField(default=0)

    # ==========================================================================
    # Status and Completion
    # ==========================================================================
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.SCHEDULED
    )
    is_completed = models.BooleanField(default=False)
    completion_date = models.DateField(
        blank=True,
        null=True
    )
    result = models.CharField(
        max_length=20,
        choices=CompletionResult.choices,
        blank=True,
        null=True
    )

    # ==========================================================================
    # Grading
    # ==========================================================================
    grade = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Overall lesson grade (0-100)"
    )
    grade_letter = models.CharField(
        max_length=2,
        blank=True,
        null=True,
        help_text="Letter grade if applicable"
    )

    # ==========================================================================
    # Attempt Tracking
    # ==========================================================================
    attempt_number = models.PositiveIntegerField(
        default=1,
        help_text="Which attempt this is"
    )
    is_repeat = models.BooleanField(
        default=False,
        help_text="Is this a repeat of a failed lesson"
    )
    previous_attempt_id = models.UUIDField(
        blank=True,
        null=True,
        help_text="Reference to previous failed attempt"
    )

    # ==========================================================================
    # Sign-offs
    # ==========================================================================
    instructor_signoff = models.BooleanField(default=False)
    instructor_signoff_date = models.DateTimeField(
        blank=True,
        null=True
    )
    instructor_signoff_notes = models.TextField(
        blank=True,
        null=True
    )
    student_signoff = models.BooleanField(default=False)
    student_signoff_date = models.DateTimeField(
        blank=True,
        null=True
    )

    # ==========================================================================
    # Feedback and Notes
    # ==========================================================================
    instructor_comments = models.TextField(
        blank=True,
        null=True,
        help_text="Instructor feedback on performance"
    )
    student_notes = models.TextField(
        blank=True,
        null=True,
        help_text="Student's own notes"
    )
    areas_of_improvement = models.JSONField(
        default=list,
        help_text="Specific areas needing improvement"
    )
    strengths = models.JSONField(
        default=list,
        help_text="Areas of strong performance"
    )

    # ==========================================================================
    # Weather Conditions
    # ==========================================================================
    weather_conditions = models.JSONField(
        default=dict,
        help_text='{"wind": "10kts", "visibility": "10sm", "ceiling": "clear"}'
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

    # ==========================================================================
    # Timestamps
    # ==========================================================================
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'lesson_completions'
        ordering = ['-actual_date', '-created_at']
        indexes = [
            models.Index(fields=['enrollment']),
            models.Index(fields=['lesson']),
            models.Index(fields=['instructor_id']),
            models.Index(fields=['status']),
            models.Index(fields=['actual_date']),
            models.Index(fields=['enrollment', 'lesson']),
        ]

    def __str__(self):
        return f"{self.enrollment.student_id} - {self.lesson.code}"

    # ==========================================================================
    # Properties
    # ==========================================================================

    @property
    def total_time(self) -> Decimal:
        """Get total training time for this completion."""
        total = Decimal('0')
        if self.flight_time:
            total += self.flight_time
        if self.ground_time:
            total += self.ground_time
        if self.simulator_time:
            total += self.simulator_time
        return total

    @property
    def total_landings(self) -> int:
        """Get total landings."""
        return self.landings_day + self.landings_night

    @property
    def is_passed(self) -> bool:
        """Check if lesson was passed."""
        if self.result:
            return self.result in [
                self.CompletionResult.PASS,
                self.CompletionResult.SATISFACTORY
            ]
        if self.grade and self.lesson.min_grade_to_pass:
            return self.grade >= self.lesson.min_grade_to_pass
        return self.is_completed

    @property
    def exercise_grades_summary(self) -> Dict[str, Any]:
        """Get summary of exercise grades."""
        grades = self.exercise_grades.all()
        if not grades.exists():
            return {'count': 0, 'average': None}

        avg = grades.aggregate(avg=Avg('grade'))['avg']
        return {
            'count': grades.count(),
            'average': float(avg) if avg else None,
            'passed': grades.filter(is_passed=True).count(),
            'failed': grades.filter(is_passed=False).count(),
        }

    # ==========================================================================
    # Methods
    # ==========================================================================

    def complete(
        self,
        grade: Decimal = None,
        result: str = None,
        instructor_comments: str = None
    ) -> None:
        """Mark the lesson as completed."""
        self.status = self.Status.COMPLETED
        self.is_completed = True
        self.completion_date = date.today()

        if grade is not None:
            self.grade = grade

        if result:
            self.result = result
        elif grade is not None and self.lesson.min_grade_to_pass:
            self.result = (
                self.CompletionResult.PASS
                if grade >= self.lesson.min_grade_to_pass
                else self.CompletionResult.FAIL
            )

        if instructor_comments:
            self.instructor_comments = instructor_comments

        self.save()

        # Update enrollment progress
        self.enrollment.update_progress()
        self.enrollment.update_hours()

    def instructor_sign(self, notes: str = None) -> None:
        """Record instructor sign-off."""
        self.instructor_signoff = True
        self.instructor_signoff_date = timezone.now()
        if notes:
            self.instructor_signoff_notes = notes
        self.save()

    def student_sign(self) -> None:
        """Record student sign-off."""
        self.student_signoff = True
        self.student_signoff_date = timezone.now()
        self.save()

    def cancel(self, reason: str, cancelled_by: uuid.UUID) -> None:
        """Cancel the lesson."""
        self.status = self.Status.CANCELLED
        self.cancellation_reason = reason
        self.cancelled_by_id = cancelled_by
        self.cancelled_at = timezone.now()
        self.save()

    def mark_no_show(self) -> None:
        """Mark student as no-show."""
        self.status = self.Status.NO_SHOW
        self.save()

    def calculate_grade_from_exercises(self) -> Optional[Decimal]:
        """Calculate overall grade from exercise grades."""
        grades = self.exercise_grades.filter(grade__isnull=False)
        if not grades.exists():
            return None

        total_weight = Decimal('0')
        weighted_sum = Decimal('0')

        for eg in grades:
            weight = Decimal(str(eg.weight or 1))
            weighted_sum += eg.grade * weight
            total_weight += weight

        if total_weight > 0:
            return weighted_sum / total_weight
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'id': str(self.id),
            'enrollment_id': str(self.enrollment_id),
            'lesson': {
                'id': str(self.lesson.id),
                'code': self.lesson.code,
                'name': self.lesson.name,
            },
            'instructor_id': str(self.instructor_id) if self.instructor_id else None,
            'status': self.status,
            'is_completed': self.is_completed,
            'result': self.result,
            'grade': float(self.grade) if self.grade else None,
            'times': {
                'flight': float(self.flight_time or 0),
                'ground': float(self.ground_time or 0),
                'simulator': float(self.simulator_time or 0),
                'total': float(self.total_time),
            },
            'dates': {
                'scheduled': self.scheduled_date.isoformat() if self.scheduled_date else None,
                'actual': self.actual_date.isoformat() if self.actual_date else None,
                'completion': self.completion_date.isoformat() if self.completion_date else None,
            },
            'signoffs': {
                'instructor': self.instructor_signoff,
                'student': self.student_signoff,
            },
            'attempt_number': self.attempt_number,
        }


class ExerciseGrade(models.Model):
    """
    Exercise grade model.

    Records the grade for a specific exercise within a lesson completion.
    """

    class GradeValue(models.TextChoices):
        """Standard competency grading values."""
        NOT_OBSERVED = '0', 'Not Observed'
        UNSATISFACTORY = '1', 'Unsatisfactory'
        NEEDS_IMPROVEMENT = '2', 'Needs Improvement'
        SATISFACTORY = '3', 'Satisfactory'
        PROFICIENT = '4', 'Proficient'

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    organization_id = models.UUIDField(db_index=True)

    # ==========================================================================
    # Relationships
    # ==========================================================================
    completion = models.ForeignKey(
        LessonCompletion,
        on_delete=models.CASCADE,
        related_name='exercise_grades'
    )
    exercise = models.ForeignKey(
        'Exercise',
        on_delete=models.PROTECT,
        related_name='grades'
    )

    # ==========================================================================
    # Grading
    # ==========================================================================
    grade = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Numeric grade (0-100)"
    )
    competency_grade = models.CharField(
        max_length=1,
        choices=GradeValue.choices,
        blank=True,
        null=True,
        help_text="Competency-based grade (1-4)"
    )
    letter_grade = models.CharField(
        max_length=2,
        blank=True,
        null=True
    )
    is_passed = models.BooleanField(default=False)

    # ==========================================================================
    # Weighting
    # ==========================================================================
    weight = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('1.00'),
        help_text="Weight for calculating overall grade"
    )

    # ==========================================================================
    # Attempt Details
    # ==========================================================================
    demonstrations = models.PositiveIntegerField(
        default=1,
        help_text="Number of demonstrations performed"
    )
    successful_demonstrations = models.PositiveIntegerField(
        default=0,
        help_text="Number of successful demonstrations"
    )

    # ==========================================================================
    # Performance Details
    # ==========================================================================
    performance_notes = models.TextField(
        blank=True,
        null=True
    )
    deviations = models.JSONField(
        default=dict,
        help_text='{"altitude": -50, "heading": 5, "airspeed": -3}'
    )

    # ==========================================================================
    # Competency Elements
    # ==========================================================================
    competency_scores = models.JSONField(
        default=dict,
        help_text='{"coordination": 3, "situational_awareness": 4}'
    )

    # ==========================================================================
    # Timestamps
    # ==========================================================================
    graded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'exercise_grades'
        ordering = ['completion', 'exercise__sort_order']
        indexes = [
            models.Index(fields=['completion']),
            models.Index(fields=['exercise']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['completion', 'exercise'],
                name='unique_exercise_grade_per_completion'
            )
        ]

    def __str__(self):
        return f"{self.exercise.code} - {self.grade}"

    # ==========================================================================
    # Properties
    # ==========================================================================

    @property
    def is_within_tolerances(self) -> bool:
        """Check if performance was within exercise tolerances."""
        if not self.deviations or not self.exercise.tolerances:
            return True

        tolerances = self.exercise.tolerances
        for key, deviation in self.deviations.items():
            if key in tolerances:
                if abs(deviation) > tolerances[key]:
                    return False
        return True

    @property
    def demonstration_success_rate(self) -> Optional[float]:
        """Get success rate of demonstrations."""
        if self.demonstrations == 0:
            return None
        return self.successful_demonstrations / self.demonstrations

    # ==========================================================================
    # Methods
    # ==========================================================================

    def evaluate_pass(self) -> bool:
        """Evaluate if exercise is passed based on criteria."""
        exercise = self.exercise

        # Check minimum grade
        if exercise.min_grade and self.grade:
            if self.grade < exercise.min_grade:
                self.is_passed = False
                self.save()
                return False

        # Check minimum demonstrations
        if self.successful_demonstrations < exercise.min_demonstrations:
            self.is_passed = False
            self.save()
            return False

        # Check competency grade
        if self.competency_grade:
            # Grade of 3 (Satisfactory) or higher passes
            if int(self.competency_grade) < 3:
                self.is_passed = False
                self.save()
                return False

        self.is_passed = True
        self.save()
        return True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'id': str(self.id),
            'exercise': {
                'id': str(self.exercise.id),
                'code': self.exercise.code,
                'name': self.exercise.name,
            },
            'grade': float(self.grade) if self.grade else None,
            'competency_grade': self.competency_grade,
            'letter_grade': self.letter_grade,
            'is_passed': self.is_passed,
            'demonstrations': self.demonstrations,
            'successful_demonstrations': self.successful_demonstrations,
            'deviations': self.deviations,
            'competency_scores': self.competency_scores,
            'performance_notes': self.performance_notes,
        }
