# services/theory-service/src/apps/core/models/enrollment.py
"""
Course Enrollment Models

Models for tracking student course enrollments and progress.
"""

import uuid
from decimal import Decimal
from typing import Dict, Any, List, Optional

from django.db import models
from django.utils import timezone

from .course import Course, CourseModule


class EnrollmentStatus(models.TextChoices):
    """Enrollment status choices."""
    ENROLLED = 'enrolled', 'Enrolled'
    IN_PROGRESS = 'in_progress', 'In Progress'
    COMPLETED = 'completed', 'Completed'
    EXPIRED = 'expired', 'Expired'
    SUSPENDED = 'suspended', 'Suspended'
    DROPPED = 'dropped', 'Dropped'


class CourseEnrollment(models.Model):
    """
    Course enrollment model.

    Tracks a student's enrollment and progress in a course.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    organization_id = models.UUIDField(db_index=True)

    # Relationships
    course = models.ForeignKey(
        Course,
        on_delete=models.PROTECT,
        related_name='enrollments'
    )
    user_id = models.UUIDField(db_index=True)

    # Dates
    enrolled_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    # Progress
    progress_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00')
    )
    modules_completed = models.IntegerField(default=0)
    modules_total = models.IntegerField(default=0)

    # Time tracking
    total_time_spent_seconds = models.IntegerField(default=0)

    # Exam performance
    exam_attempts = models.IntegerField(default=0)
    best_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True
    )
    latest_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True
    )
    passed = models.BooleanField(default=False)
    passed_at = models.DateTimeField(null=True, blank=True)

    # Certificate
    certificate_issued = models.BooleanField(default=False)
    certificate_id = models.UUIDField(null=True, blank=True)
    certificate_url = models.URLField(max_length=500, blank=True, default='')

    # Status
    status = models.CharField(
        max_length=20,
        choices=EnrollmentStatus.choices,
        default=EnrollmentStatus.ENROLLED
    )

    # Activity tracking
    last_accessed_at = models.DateTimeField(null=True, blank=True)
    last_module_id = models.UUIDField(null=True, blank=True)
    last_activity = models.CharField(max_length=255, blank=True, default='')

    # Notes
    notes = models.TextField(blank=True, default='')

    # Completion details
    completion_details = models.JSONField(default=dict, blank=True)

    # Rating
    rating = models.IntegerField(null=True, blank=True)  # 1-5
    review = models.TextField(blank=True, default='')
    reviewed_at = models.DateTimeField(null=True, blank=True)

    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'course_enrollments'
        ordering = ['-enrolled_at']
        indexes = [
            models.Index(fields=['user_id']),
            models.Index(fields=['course']),
            models.Index(fields=['status']),
            models.Index(fields=['organization_id', 'user_id']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['course', 'user_id'],
                name='unique_course_enrollment'
            )
        ]

    def __str__(self):
        return f"{self.user_id} enrolled in {self.course.name}"

    @property
    def is_active(self) -> bool:
        """Check if enrollment is active."""
        if self.status not in [EnrollmentStatus.ENROLLED, EnrollmentStatus.IN_PROGRESS]:
            return False

        if self.expires_at and timezone.now() > self.expires_at:
            return False

        return True

    @property
    def is_expired(self) -> bool:
        """Check if enrollment has expired."""
        if self.expires_at and timezone.now() > self.expires_at:
            return True
        return False

    @property
    def days_since_enrollment(self) -> int:
        """Get days since enrollment."""
        return (timezone.now() - self.enrolled_at).days

    @property
    def days_until_expiry(self) -> Optional[int]:
        """Get days until expiry."""
        if not self.expires_at:
            return None
        delta = self.expires_at - timezone.now()
        return max(0, delta.days)

    @property
    def total_time_spent_hours(self) -> float:
        """Get total time spent in hours."""
        return round(self.total_time_spent_seconds / 3600, 2)

    def start(self) -> None:
        """Start the course."""
        if self.status == EnrollmentStatus.ENROLLED:
            self.status = EnrollmentStatus.IN_PROGRESS
            self.started_at = timezone.now()
            self.save()

    def complete(self) -> None:
        """Mark course as completed."""
        self.status = EnrollmentStatus.COMPLETED
        self.completed_at = timezone.now()
        self.progress_percentage = Decimal('100.00')
        self.save()

        # Update course statistics
        self.course.update_statistics()

    def suspend(self, reason: str = '') -> None:
        """Suspend the enrollment."""
        self.status = EnrollmentStatus.SUSPENDED
        self.notes = reason
        self.save()

    def expire(self) -> None:
        """Mark enrollment as expired."""
        self.status = EnrollmentStatus.EXPIRED
        self.save()

    def update_progress(self) -> None:
        """Update progress from module completions."""
        total_modules = self.course.modules.filter(is_active=True).count()
        completed_modules = self.module_progress.filter(completed=True).count()

        self.modules_total = total_modules
        self.modules_completed = completed_modules

        if total_modules > 0:
            self.progress_percentage = Decimal(
                str(round((completed_modules / total_modules) * 100, 2))
            )

        self.save()

        # Check for course completion
        if self.progress_percentage >= 100:
            if not self.course.require_final_exam or self.passed:
                self.complete()

    def update_exam_score(self, score: Decimal, passed: bool) -> None:
        """Update with new exam score."""
        self.exam_attempts += 1
        self.latest_score = score

        if self.best_score is None or score > self.best_score:
            self.best_score = score

        if passed and not self.passed:
            self.passed = True
            self.passed_at = timezone.now()

            # Check for course completion
            if self.progress_percentage >= 100 or not self.course.require_module_completion:
                self.complete()

        self.save()

    def record_activity(
        self,
        module_id: str = None,
        time_spent_seconds: int = 0,
        activity: str = ''
    ) -> None:
        """Record learning activity."""
        self.last_accessed_at = timezone.now()

        if module_id:
            self.last_module_id = module_id

        if activity:
            self.last_activity = activity

        self.total_time_spent_seconds += time_spent_seconds
        self.save()

    def submit_review(self, rating: int, review: str = '') -> None:
        """Submit course review."""
        if rating < 1 or rating > 5:
            raise ValueError("Rating must be between 1 and 5")

        self.rating = rating
        self.review = review
        self.reviewed_at = timezone.now()
        self.save()

    def get_progress_summary(self) -> Dict[str, Any]:
        """Get detailed progress summary."""
        return {
            'enrollment_id': str(self.id),
            'course_id': str(self.course.id),
            'course_name': self.course.name,
            'status': self.status,
            'progress_percentage': float(self.progress_percentage),
            'modules_completed': self.modules_completed,
            'modules_total': self.modules_total,
            'time_spent_hours': self.total_time_spent_hours,
            'exam_attempts': self.exam_attempts,
            'best_score': float(self.best_score) if self.best_score else None,
            'passed': self.passed,
            'certificate_issued': self.certificate_issued,
            'days_since_enrollment': self.days_since_enrollment,
            'days_until_expiry': self.days_until_expiry,
            'last_accessed_at': self.last_accessed_at.isoformat() if self.last_accessed_at else None,
        }


class ModuleProgress(models.Model):
    """
    Module progress model.

    Tracks detailed progress through individual modules.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    enrollment = models.ForeignKey(
        CourseEnrollment,
        on_delete=models.CASCADE,
        related_name='module_progress'
    )
    module = models.ForeignKey(
        CourseModule,
        on_delete=models.CASCADE,
        related_name='progress_records'
    )

    # Progress
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    completed = models.BooleanField(default=False)

    # Time tracking
    time_spent_seconds = models.IntegerField(default=0)
    view_count = models.IntegerField(default=0)

    # Content progress
    video_watched_percentage = models.IntegerField(default=0)
    video_last_position_seconds = models.IntegerField(default=0)
    content_scroll_percentage = models.IntegerField(default=0)

    # Quiz
    quiz_attempted = models.BooleanField(default=False)
    quiz_passed = models.BooleanField(default=False)
    quiz_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True
    )
    quiz_attempts = models.IntegerField(default=0)

    # Notes
    notes = models.TextField(blank=True, default='')
    bookmarked = models.BooleanField(default=False)

    # Last activity
    last_accessed_at = models.DateTimeField(null=True, blank=True)

    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'module_progress'
        ordering = ['module__sort_order']
        constraints = [
            models.UniqueConstraint(
                fields=['enrollment', 'module'],
                name='unique_module_progress'
            )
        ]

    def __str__(self):
        return f"{self.enrollment.user_id} - {self.module.name}"

    @property
    def time_spent_minutes(self) -> int:
        """Get time spent in minutes."""
        return self.time_spent_seconds // 60

    def start(self) -> None:
        """Start the module."""
        if not self.started_at:
            self.started_at = timezone.now()
            self.view_count = 1
            self.save()

            # Start enrollment if needed
            if self.enrollment.status == EnrollmentStatus.ENROLLED:
                self.enrollment.start()

    def record_view(self, time_spent_seconds: int = 0) -> None:
        """Record a module view."""
        self.view_count += 1
        self.time_spent_seconds += time_spent_seconds
        self.last_accessed_at = timezone.now()
        self.save()

        # Update enrollment
        self.enrollment.record_activity(
            module_id=str(self.module.id),
            time_spent_seconds=time_spent_seconds,
            activity=f"Viewed {self.module.name}"
        )

    def update_video_progress(
        self,
        watched_percentage: int,
        position_seconds: int
    ) -> None:
        """Update video watching progress."""
        self.video_watched_percentage = max(
            self.video_watched_percentage,
            watched_percentage
        )
        self.video_last_position_seconds = position_seconds
        self.save()

        # Check completion
        self._check_completion()

    def update_scroll_progress(self, scroll_percentage: int) -> None:
        """Update content scroll progress."""
        self.content_scroll_percentage = max(
            self.content_scroll_percentage,
            scroll_percentage
        )
        self.save()

        # Check completion
        self._check_completion()

    def record_quiz_attempt(self, score: Decimal, passed: bool) -> None:
        """Record a quiz attempt."""
        self.quiz_attempted = True
        self.quiz_attempts += 1

        if self.quiz_score is None or score > self.quiz_score:
            self.quiz_score = score

        if passed:
            self.quiz_passed = True

        self.save()

        # Check completion
        self._check_completion()

    def complete(self) -> None:
        """Mark module as completed."""
        if not self.completed:
            self.completed = True
            self.completed_at = timezone.now()
            self.save()

            # Update enrollment progress
            self.enrollment.update_progress()

    def _check_completion(self) -> None:
        """Check if module completion criteria are met."""
        if self.completed:
            return

        result = self.module.check_completion(
            video_watched_percentage=self.video_watched_percentage,
            quiz_passed=self.quiz_passed,
            time_spent_seconds=self.time_spent_seconds,
            scrolled_to_bottom=self.content_scroll_percentage >= 90
        )

        if result['completed']:
            self.complete()

    def get_summary(self) -> Dict[str, Any]:
        """Get module progress summary."""
        return {
            'module_id': str(self.module.id),
            'module_name': self.module.name,
            'sort_order': self.module.sort_order,
            'started': self.started_at is not None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed': self.completed,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'time_spent_minutes': self.time_spent_minutes,
            'video_watched_percentage': self.video_watched_percentage,
            'quiz_passed': self.quiz_passed,
            'quiz_score': float(self.quiz_score) if self.quiz_score else None,
            'bookmarked': self.bookmarked,
        }
