# services/theory-service/src/apps/core/services/enrollment_service.py
"""
Enrollment Service

Business logic for course enrollment management.
"""

import logging
from typing import Dict, Any, List, Optional
from uuid import UUID
from decimal import Decimal
from datetime import timedelta

from django.db import transaction
from django.db.models import Q, Avg, Count
from django.utils import timezone

from ..models import (
    Course,
    CourseModule,
    CourseEnrollment,
    ModuleProgress,
    EnrollmentStatus,
)

logger = logging.getLogger(__name__)


class EnrollmentService:
    """Service for managing course enrollments."""

    @staticmethod
    def get_enrollments(
        organization_id: str,
        user_id: str = None,
        course_id: str = None,
        status: str = None,
    ) -> List[CourseEnrollment]:
        """
        Get enrollments with optional filtering.

        Args:
            organization_id: Organization ID
            user_id: Filter by user
            course_id: Filter by course
            status: Filter by status

        Returns:
            List of enrollments
        """
        queryset = CourseEnrollment.objects.filter(
            organization_id=organization_id
        )

        if user_id:
            queryset = queryset.filter(user_id=user_id)

        if course_id:
            queryset = queryset.filter(course_id=course_id)

        if status:
            queryset = queryset.filter(status=status)

        return queryset.select_related('course').order_by('-enrolled_at')

    @staticmethod
    @transaction.atomic
    def enroll_user(
        organization_id: str,
        user_id: str,
        course_id: str,
        expires_in_days: int = None,
    ) -> CourseEnrollment:
        """
        Enroll a user in a course.

        Args:
            organization_id: Organization ID
            user_id: User ID
            course_id: Course ID
            expires_in_days: Optional expiry in days

        Returns:
            Created enrollment
        """
        course = Course.objects.get(
            id=course_id,
            organization_id=organization_id
        )

        # Check if course is published
        if not course.is_published:
            raise ValueError("Cannot enroll in unpublished course")

        # Check if already enrolled
        existing = CourseEnrollment.objects.filter(
            course=course,
            user_id=user_id
        ).first()

        if existing:
            if existing.status in [EnrollmentStatus.ENROLLED, EnrollmentStatus.IN_PROGRESS]:
                raise ValueError("User is already enrolled in this course")
            elif existing.status == EnrollmentStatus.COMPLETED:
                # Allow re-enrollment for completed courses
                existing.status = EnrollmentStatus.ENROLLED
                existing.progress_percentage = Decimal('0.00')
                existing.modules_completed = 0
                existing.total_time_spent_seconds = 0
                existing.passed = False
                existing.save()
                return existing

        # Check prerequisites
        prereq_check = course.check_prerequisites(
            EnrollmentService._get_completed_course_ids(organization_id, user_id)
        )
        if not prereq_check['met']:
            raise ValueError(
                f"Prerequisites not met. Missing courses: {prereq_check['missing']}"
            )

        # Calculate expiry
        expires_at = None
        if expires_in_days:
            expires_at = timezone.now() + timedelta(days=expires_in_days)

        # Create enrollment
        enrollment = CourseEnrollment.objects.create(
            organization_id=organization_id,
            course=course,
            user_id=user_id,
            expires_at=expires_at,
            modules_total=course.modules.filter(is_active=True).count()
        )

        # Create module progress records
        for module in course.modules.filter(is_active=True):
            ModuleProgress.objects.create(
                enrollment=enrollment,
                module=module
            )

        # Update course statistics
        course.enrolled_count += 1
        course.save()

        # Publish event
        from ..events.publishers import publish_course_enrolled
        publish_course_enrolled(
            organization_id=str(organization_id),
            enrollment_id=str(enrollment.id),
            user_id=str(user_id),
            course_id=str(course_id)
        )

        logger.info(f"User {user_id} enrolled in course {course_id}")

        return enrollment

    @staticmethod
    def get_enrollment(
        enrollment_id: str,
        user_id: str = None,
        organization_id: str = None
    ) -> CourseEnrollment:
        """
        Get enrollment by ID.

        Args:
            enrollment_id: Enrollment ID
            user_id: Optional user filter
            organization_id: Optional organization filter

        Returns:
            Enrollment instance
        """
        filters = {'id': enrollment_id}
        if user_id:
            filters['user_id'] = user_id
        if organization_id:
            filters['organization_id'] = organization_id

        return CourseEnrollment.objects.select_related('course').get(**filters)

    @staticmethod
    @transaction.atomic
    def start_course(
        enrollment_id: str,
        user_id: str
    ) -> CourseEnrollment:
        """
        Start a course (transition to in_progress).

        Args:
            enrollment_id: Enrollment ID
            user_id: User ID

        Returns:
            Updated enrollment
        """
        enrollment = CourseEnrollment.objects.select_for_update().get(
            id=enrollment_id,
            user_id=user_id
        )

        enrollment.start()

        logger.info(f"User {user_id} started course {enrollment.course_id}")

        return enrollment

    @staticmethod
    @transaction.atomic
    def record_module_activity(
        enrollment_id: str,
        module_id: str,
        user_id: str,
        time_spent_seconds: int = 0,
        video_watched_percentage: int = None,
        video_position_seconds: int = None,
        scroll_percentage: int = None,
    ) -> ModuleProgress:
        """
        Record learning activity on a module.

        Args:
            enrollment_id: Enrollment ID
            module_id: Module ID
            user_id: User ID
            time_spent_seconds: Time spent on module
            video_watched_percentage: Video progress
            video_position_seconds: Video position
            scroll_percentage: Content scroll progress

        Returns:
            Updated module progress
        """
        enrollment = CourseEnrollment.objects.select_for_update().get(
            id=enrollment_id,
            user_id=user_id
        )

        progress, created = ModuleProgress.objects.get_or_create(
            enrollment=enrollment,
            module_id=module_id
        )

        # Start module if first access
        if not progress.started_at:
            progress.start()

        # Record view
        progress.record_view(time_spent_seconds)

        # Update video progress
        if video_watched_percentage is not None:
            progress.update_video_progress(
                video_watched_percentage,
                video_position_seconds or 0
            )

        # Update scroll progress
        if scroll_percentage is not None:
            progress.update_scroll_progress(scroll_percentage)

        # Update enrollment
        enrollment.record_activity(
            module_id=module_id,
            time_spent_seconds=time_spent_seconds,
            activity=f"Studying {progress.module.name}"
        )

        return progress

    @staticmethod
    @transaction.atomic
    def complete_module(
        enrollment_id: str,
        module_id: str,
        user_id: str,
    ) -> ModuleProgress:
        """
        Mark a module as completed.

        Args:
            enrollment_id: Enrollment ID
            module_id: Module ID
            user_id: User ID

        Returns:
            Updated module progress
        """
        enrollment = CourseEnrollment.objects.select_for_update().get(
            id=enrollment_id,
            user_id=user_id
        )

        progress = ModuleProgress.objects.get(
            enrollment=enrollment,
            module_id=module_id
        )

        progress.complete()

        # Publish event
        from ..events.publishers import publish_module_completed
        publish_module_completed(
            organization_id=str(enrollment.organization_id),
            enrollment_id=str(enrollment_id),
            module_id=module_id,
            user_id=str(user_id),
            course_id=str(enrollment.course_id)
        )

        logger.info(f"User {user_id} completed module {module_id}")

        return progress

    @staticmethod
    @transaction.atomic
    def record_quiz_result(
        enrollment_id: str,
        module_id: str,
        user_id: str,
        score: Decimal,
        passed: bool
    ) -> ModuleProgress:
        """
        Record a module quiz result.

        Args:
            enrollment_id: Enrollment ID
            module_id: Module ID
            user_id: User ID
            score: Quiz score
            passed: Whether passed

        Returns:
            Updated module progress
        """
        enrollment = CourseEnrollment.objects.select_for_update().get(
            id=enrollment_id,
            user_id=user_id
        )

        progress = ModuleProgress.objects.get(
            enrollment=enrollment,
            module_id=module_id
        )

        progress.record_quiz_attempt(score, passed)

        return progress

    @staticmethod
    @transaction.atomic
    def record_exam_result(
        enrollment_id: str,
        user_id: str,
        score: Decimal,
        passed: bool
    ) -> CourseEnrollment:
        """
        Record final exam result for course.

        Args:
            enrollment_id: Enrollment ID
            user_id: User ID
            score: Exam score
            passed: Whether passed

        Returns:
            Updated enrollment
        """
        enrollment = CourseEnrollment.objects.select_for_update().get(
            id=enrollment_id,
            user_id=user_id
        )

        enrollment.update_exam_score(score, passed)

        if passed:
            # Publish event
            from ..events.publishers import publish_course_completed
            publish_course_completed(
                organization_id=str(enrollment.organization_id),
                enrollment_id=str(enrollment_id),
                user_id=str(user_id),
                course_id=str(enrollment.course_id),
                score=float(score)
            )

            logger.info(f"User {user_id} completed course {enrollment.course_id}")

        return enrollment

    @staticmethod
    @transaction.atomic
    def suspend_enrollment(
        enrollment_id: str,
        organization_id: str,
        reason: str = ''
    ) -> CourseEnrollment:
        """
        Suspend an enrollment.

        Args:
            enrollment_id: Enrollment ID
            organization_id: Organization ID
            reason: Suspension reason

        Returns:
            Updated enrollment
        """
        enrollment = CourseEnrollment.objects.select_for_update().get(
            id=enrollment_id,
            organization_id=organization_id
        )

        enrollment.suspend(reason)

        logger.info(f"Suspended enrollment: {enrollment_id}")

        return enrollment

    @staticmethod
    @transaction.atomic
    def reactivate_enrollment(
        enrollment_id: str,
        organization_id: str,
        extend_days: int = None
    ) -> CourseEnrollment:
        """
        Reactivate a suspended enrollment.

        Args:
            enrollment_id: Enrollment ID
            organization_id: Organization ID
            extend_days: Optional days to extend expiry

        Returns:
            Updated enrollment
        """
        enrollment = CourseEnrollment.objects.select_for_update().get(
            id=enrollment_id,
            organization_id=organization_id
        )

        if enrollment.status not in [EnrollmentStatus.SUSPENDED, EnrollmentStatus.EXPIRED]:
            raise ValueError("Enrollment is not suspended or expired")

        enrollment.status = EnrollmentStatus.IN_PROGRESS
        enrollment.notes = ''

        if extend_days:
            if enrollment.expires_at:
                enrollment.expires_at = enrollment.expires_at + timedelta(days=extend_days)
            else:
                enrollment.expires_at = timezone.now() + timedelta(days=extend_days)

        enrollment.save()

        logger.info(f"Reactivated enrollment: {enrollment_id}")

        return enrollment

    @staticmethod
    def get_enrollment_progress(
        enrollment_id: str,
        user_id: str = None
    ) -> Dict[str, Any]:
        """
        Get detailed progress for an enrollment.

        Args:
            enrollment_id: Enrollment ID
            user_id: Optional user filter

        Returns:
            Progress details
        """
        filters = {'id': enrollment_id}
        if user_id:
            filters['user_id'] = user_id

        enrollment = CourseEnrollment.objects.select_related(
            'course'
        ).prefetch_related(
            'module_progress__module'
        ).get(**filters)

        # Get module progress
        modules = []
        for progress in enrollment.module_progress.all():
            modules.append(progress.get_summary())

        # Get next module to study
        next_module = None
        for progress in enrollment.module_progress.order_by('module__sort_order'):
            if not progress.completed:
                next_module = {
                    'module_id': str(progress.module.id),
                    'name': progress.module.name
                }
                break

        return {
            **enrollment.get_progress_summary(),
            'modules': modules,
            'next_module': next_module,
            'course_summary': enrollment.course.get_summary()
        }

    @staticmethod
    def submit_review(
        enrollment_id: str,
        user_id: str,
        rating: int,
        review: str = ''
    ) -> CourseEnrollment:
        """
        Submit a course review.

        Args:
            enrollment_id: Enrollment ID
            user_id: User ID
            rating: Rating (1-5)
            review: Review text

        Returns:
            Updated enrollment
        """
        enrollment = CourseEnrollment.objects.get(
            id=enrollment_id,
            user_id=user_id
        )

        if enrollment.status != EnrollmentStatus.COMPLETED:
            raise ValueError("Can only review completed courses")

        enrollment.submit_review(rating, review)

        # Update course rating
        EnrollmentService._update_course_rating(enrollment.course)

        logger.info(f"User {user_id} reviewed course {enrollment.course_id}")

        return enrollment

    # =========================================================================
    # HELPERS
    # =========================================================================

    @staticmethod
    def _get_completed_course_ids(
        organization_id: str,
        user_id: str
    ) -> List[str]:
        """Get list of completed course IDs for user."""
        return list(
            CourseEnrollment.objects.filter(
                organization_id=organization_id,
                user_id=user_id,
                status=EnrollmentStatus.COMPLETED
            ).values_list('course_id', flat=True)
        )

    @staticmethod
    def _update_course_rating(course: Course) -> None:
        """Update course average rating."""
        enrollments = CourseEnrollment.objects.filter(
            course=course
        ).exclude(rating__isnull=True)

        if enrollments.exists():
            avg = enrollments.aggregate(avg_rating=Avg('rating'))['avg_rating']
            course.rating = Decimal(str(round(avg, 2)))
            course.rating_count = enrollments.count()
            course.save()
