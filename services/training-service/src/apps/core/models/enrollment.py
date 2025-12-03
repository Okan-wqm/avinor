# services/training-service/src/apps/core/models/enrollment.py
"""
Student Enrollment Model

Manages student enrollments in training programs.
"""

import uuid
from decimal import Decimal
from typing import List, Dict, Any, Optional
from datetime import date

from django.db import models
from django.db.models import Sum, Count, Q
from django.utils import timezone


class StudentEnrollment(models.Model):
    """
    Student enrollment model.

    Tracks a student's enrollment in a training program including
    progress, hours, and current status.
    """

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        ACTIVE = 'active', 'Active'
        ON_HOLD = 'on_hold', 'On Hold'
        COMPLETED = 'completed', 'Completed'
        WITHDRAWN = 'withdrawn', 'Withdrawn'
        EXPIRED = 'expired', 'Expired'
        SUSPENDED = 'suspended', 'Suspended'

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    organization_id = models.UUIDField(db_index=True)

    # ==========================================================================
    # Relationships
    # ==========================================================================
    student_id = models.UUIDField(db_index=True)
    program = models.ForeignKey(
        'TrainingProgram',
        on_delete=models.PROTECT,
        related_name='enrollments'
    )
    primary_instructor_id = models.UUIDField(
        blank=True,
        null=True,
        help_text="Assigned primary instructor"
    )
    secondary_instructor_ids = models.JSONField(
        default=list,
        help_text="Additional authorized instructors"
    )

    # ==========================================================================
    # Enrollment Information
    # ==========================================================================
    enrollment_number = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Enrollment reference number"
    )

    # ==========================================================================
    # Dates
    # ==========================================================================
    enrollment_date = models.DateField()
    start_date = models.DateField(
        blank=True,
        null=True,
        help_text="Date training actually started"
    )
    expected_completion = models.DateField(
        blank=True,
        null=True
    )
    actual_completion = models.DateField(
        blank=True,
        null=True
    )
    expiry_date = models.DateField(
        blank=True,
        null=True,
        help_text="Date enrollment expires if not completed"
    )

    # ==========================================================================
    # Status
    # ==========================================================================
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    hold_reason = models.TextField(
        blank=True,
        null=True
    )
    hold_date = models.DateField(blank=True, null=True)
    withdrawal_reason = models.TextField(
        blank=True,
        null=True
    )
    withdrawal_date = models.DateField(blank=True, null=True)

    # ==========================================================================
    # Current Position in Program
    # ==========================================================================
    current_stage_id = models.UUIDField(
        blank=True,
        null=True,
        help_text="Current training stage"
    )
    current_lesson_id = models.UUIDField(
        blank=True,
        null=True,
        help_text="Current/next lesson"
    )

    # ==========================================================================
    # Total Hours
    # ==========================================================================
    total_flight_hours = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal('0.00')
    )
    total_ground_hours = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal('0.00')
    )
    total_simulator_hours = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal('0.00')
    )

    # ==========================================================================
    # Category Hours
    # ==========================================================================
    dual_hours = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal('0.00')
    )
    solo_hours = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal('0.00')
    )
    pic_hours = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal('0.00')
    )
    cross_country_hours = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal('0.00')
    )
    night_hours = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal('0.00')
    )
    instrument_hours = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal('0.00')
    )

    # ==========================================================================
    # Progress Statistics
    # ==========================================================================
    lessons_completed = models.PositiveIntegerField(default=0)
    lessons_total = models.PositiveIntegerField(default=0)
    completion_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00')
    )
    exercises_completed = models.PositiveIntegerField(default=0)
    exercises_total = models.PositiveIntegerField(default=0)

    # ==========================================================================
    # Performance
    # ==========================================================================
    average_grade = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True
    )
    stage_checks_passed = models.PositiveIntegerField(default=0)
    stage_checks_failed = models.PositiveIntegerField(default=0)

    # ==========================================================================
    # Financial
    # ==========================================================================
    total_paid = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    total_charges = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    balance = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    currency = models.CharField(max_length=3, default='NOK')

    # ==========================================================================
    # Notes
    # ==========================================================================
    notes = models.TextField(
        blank=True,
        null=True,
        help_text="General enrollment notes"
    )
    instructor_notes = models.TextField(
        blank=True,
        null=True,
        help_text="Notes from instructors"
    )

    # ==========================================================================
    # Metadata
    # ==========================================================================
    metadata = models.JSONField(default=dict)
    training_records_url = models.URLField(
        max_length=500,
        blank=True,
        null=True
    )

    # ==========================================================================
    # Timestamps
    # ==========================================================================
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'student_enrollments'
        ordering = ['-enrollment_date']
        indexes = [
            models.Index(fields=['student_id']),
            models.Index(fields=['program']),
            models.Index(fields=['primary_instructor_id']),
            models.Index(fields=['status']),
            models.Index(fields=['organization_id', 'student_id']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['student_id', 'program'],
                name='unique_student_program_enrollment'
            )
        ]

    def __str__(self):
        return f"Enrollment: {self.student_id} - {self.program.code}"

    # ==========================================================================
    # Properties
    # ==========================================================================

    @property
    def is_active(self) -> bool:
        """Check if enrollment is active."""
        return self.status == self.Status.ACTIVE

    @property
    def is_completed(self) -> bool:
        """Check if enrollment is completed."""
        return self.status == self.Status.COMPLETED

    @property
    def days_enrolled(self) -> int:
        """Get number of days since enrollment."""
        return (date.today() - self.enrollment_date).days

    @property
    def days_remaining(self) -> Optional[int]:
        """Get days remaining until expected completion."""
        if self.expected_completion:
            remaining = (self.expected_completion - date.today()).days
            return max(0, remaining)
        return None

    @property
    def total_training_hours(self) -> Decimal:
        """Get total training hours (flight + ground + sim)."""
        return (
            self.total_flight_hours +
            self.total_ground_hours +
            self.total_simulator_hours
        )

    @property
    def progress_status(self) -> str:
        """Get a status string based on progress."""
        if self.completion_percentage >= 100:
            return 'completed'
        elif self.completion_percentage >= 75:
            return 'advanced'
        elif self.completion_percentage >= 50:
            return 'intermediate'
        elif self.completion_percentage >= 25:
            return 'beginner'
        else:
            return 'starting'

    @property
    def current_stage_name(self) -> Optional[str]:
        """Get name of current stage."""
        if not self.current_stage_id:
            return None
        stage = self.program.get_stage(str(self.current_stage_id))
        return stage.get('name') if stage else None

    # ==========================================================================
    # Methods
    # ==========================================================================

    def update_progress(self) -> None:
        """Update progress statistics from completions."""
        from .completion import LessonCompletion

        # Count completed lessons
        completed = LessonCompletion.objects.filter(
            enrollment=self,
            is_completed=True
        ).count()

        # Get total lessons in program
        total = self.program.lessons.filter(status='active').count()

        self.lessons_completed = completed
        self.lessons_total = total

        if total > 0:
            self.completion_percentage = Decimal(completed) / Decimal(total) * 100
        else:
            self.completion_percentage = Decimal('0')

        # Update average grade
        avg_result = LessonCompletion.objects.filter(
            enrollment=self,
            is_completed=True,
            grade__isnull=False
        ).aggregate(avg=models.Avg('grade'))

        if avg_result['avg']:
            self.average_grade = Decimal(str(avg_result['avg']))

        self.save()

    def update_hours(self) -> None:
        """Update hour totals from completions."""
        from .completion import LessonCompletion

        hours = LessonCompletion.objects.filter(
            enrollment=self
        ).aggregate(
            flight=Sum('flight_time'),
            ground=Sum('ground_time'),
            simulator=Sum('simulator_time'),
        )

        self.total_flight_hours = hours['flight'] or Decimal('0')
        self.total_ground_hours = hours['ground'] or Decimal('0')
        self.total_simulator_hours = hours['simulator'] or Decimal('0')
        self.save()

    def activate(self, start_date: date = None) -> None:
        """Activate the enrollment."""
        self.status = self.Status.ACTIVE
        self.start_date = start_date or date.today()

        # Set first stage if not set
        if not self.current_stage_id and self.program.stages:
            self.current_stage_id = self.program.stages[0].get('id')

        # Set first lesson if not set
        if not self.current_lesson_id:
            first_lesson = self.program.lessons.filter(
                status='active'
            ).order_by('sort_order').first()
            if first_lesson:
                self.current_lesson_id = first_lesson.id

        self.save()

    def put_on_hold(self, reason: str) -> None:
        """Put enrollment on hold."""
        self.status = self.Status.ON_HOLD
        self.hold_reason = reason
        self.hold_date = date.today()
        self.save()

    def resume(self) -> None:
        """Resume enrollment from hold."""
        if self.status == self.Status.ON_HOLD:
            self.status = self.Status.ACTIVE
            self.hold_reason = None
            self.hold_date = None
            self.save()

    def withdraw(self, reason: str) -> None:
        """Withdraw from enrollment."""
        self.status = self.Status.WITHDRAWN
        self.withdrawal_reason = reason
        self.withdrawal_date = date.today()
        self.save()

    def complete(self, completion_date: date = None) -> None:
        """Mark enrollment as completed."""
        self.status = self.Status.COMPLETED
        self.actual_completion = completion_date or date.today()
        self.completion_percentage = Decimal('100.00')
        self.save()

    def advance_to_stage(self, stage_id: str) -> None:
        """Advance to a new stage."""
        self.current_stage_id = stage_id

        # Get first lesson in new stage
        from .syllabus import SyllabusLesson
        first_lesson = SyllabusLesson.objects.filter(
            program=self.program,
            stage_id=stage_id,
            status='active'
        ).order_by('sort_order').first()

        if first_lesson:
            self.current_lesson_id = first_lesson.id

        self.save()

    def set_next_lesson(self, lesson_id: uuid.UUID) -> None:
        """Set the next lesson."""
        self.current_lesson_id = lesson_id
        self.save()

    def check_hour_requirements(self) -> Dict[str, Any]:
        """Check if minimum hour requirements are met."""
        program = self.program
        requirements = {
            'met': True,
            'details': {}
        }

        checks = [
            ('total', self.total_flight_hours, program.min_hours_total),
            ('dual', self.dual_hours, program.min_hours_dual),
            ('solo', self.solo_hours, program.min_hours_solo),
            ('pic', self.pic_hours, program.min_hours_pic),
            ('cross_country', self.cross_country_hours, program.min_hours_cross_country),
            ('night', self.night_hours, program.min_hours_night),
            ('instrument', self.instrument_hours, program.min_hours_instrument),
            ('simulator', self.total_simulator_hours, program.min_hours_simulator),
        ]

        for name, current, required in checks:
            if required:
                met = current >= required
                requirements['details'][name] = {
                    'current': float(current),
                    'required': float(required),
                    'met': met,
                    'remaining': float(max(Decimal('0'), required - current))
                }
                if not met:
                    requirements['met'] = False

        return requirements

    def get_progress_summary(self) -> Dict[str, Any]:
        """Get detailed progress summary."""
        return {
            'enrollment_id': str(self.id),
            'student_id': str(self.student_id),
            'program': {
                'id': str(self.program.id),
                'code': self.program.code,
                'name': self.program.name,
            },
            'status': self.status,
            'progress': {
                'lessons_completed': self.lessons_completed,
                'lessons_total': self.lessons_total,
                'percentage': float(self.completion_percentage),
                'status': self.progress_status,
            },
            'hours': {
                'flight': float(self.total_flight_hours),
                'ground': float(self.total_ground_hours),
                'simulator': float(self.total_simulator_hours),
                'total': float(self.total_training_hours),
                'dual': float(self.dual_hours),
                'solo': float(self.solo_hours),
                'pic': float(self.pic_hours),
                'cross_country': float(self.cross_country_hours),
                'night': float(self.night_hours),
                'instrument': float(self.instrument_hours),
            },
            'current_stage': {
                'id': str(self.current_stage_id) if self.current_stage_id else None,
                'name': self.current_stage_name,
            },
            'current_lesson_id': str(self.current_lesson_id) if self.current_lesson_id else None,
            'performance': {
                'average_grade': float(self.average_grade) if self.average_grade else None,
                'stage_checks_passed': self.stage_checks_passed,
                'stage_checks_failed': self.stage_checks_failed,
            },
            'dates': {
                'enrollment_date': self.enrollment_date.isoformat(),
                'start_date': self.start_date.isoformat() if self.start_date else None,
                'expected_completion': self.expected_completion.isoformat() if self.expected_completion else None,
                'actual_completion': self.actual_completion.isoformat() if self.actual_completion else None,
            },
            'days_enrolled': self.days_enrolled,
            'days_remaining': self.days_remaining,
        }
