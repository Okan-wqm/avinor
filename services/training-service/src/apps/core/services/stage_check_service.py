# services/training-service/src/apps/core/services/stage_check_service.py
"""
Stage Check Service

Business logic for stage check management.
"""

import uuid
import logging
from decimal import Decimal
from typing import List, Dict, Any, Optional, Tuple
from datetime import date, time

from django.db import transaction
from django.db.models import Q, Count, Avg
from django.core.exceptions import ValidationError
from django.utils import timezone

from ..models import (
    StageCheck,
    StudentEnrollment,
    LessonCompletion,
    SyllabusLesson
)

logger = logging.getLogger(__name__)


class StageCheckService:
    """
    Service class for stage check operations.

    Handles scheduling, conducting, and recording stage checks.
    """

    # ==========================================================================
    # Stage Check CRUD
    # ==========================================================================

    @staticmethod
    def create_stage_check(
        organization_id: uuid.UUID,
        enrollment_id: uuid.UUID,
        stage_id: uuid.UUID,
        check_type: str,
        scheduled_date: date = None,
        examiner_id: uuid.UUID = None,
        recommending_instructor_id: uuid.UUID = None,
        **kwargs
    ) -> StageCheck:
        """
        Create a new stage check.

        Args:
            organization_id: Organization UUID
            enrollment_id: Enrollment UUID
            stage_id: Stage UUID
            check_type: Type of check (oral, flight, combined)
            scheduled_date: Scheduled date
            examiner_id: Examiner UUID
            recommending_instructor_id: Recommending instructor UUID
            **kwargs: Additional stage check fields

        Returns:
            Created StageCheck instance
        """
        enrollment = StudentEnrollment.objects.get(
            id=enrollment_id,
            organization_id=organization_id
        )

        # Verify stage exists in program
        stage = enrollment.program.get_stage(str(stage_id))
        if not stage:
            raise ValidationError(f"Stage {stage_id} not found in program")

        # Check for existing active stage check
        existing = StageCheck.objects.filter(
            enrollment=enrollment,
            stage_id=stage_id,
            status__in=['scheduled', 'in_progress']
        ).first()

        if existing:
            raise ValidationError(
                f"Stage check already {existing.status} for this stage"
            )

        # Determine attempt number
        previous_attempts = StageCheck.objects.filter(
            enrollment=enrollment,
            stage_id=stage_id
        ).count()

        # Get previous failed attempt if exists
        previous_failed = StageCheck.objects.filter(
            enrollment=enrollment,
            stage_id=stage_id,
            is_passed=False
        ).order_by('-created_at').first()

        with transaction.atomic():
            stage_check = StageCheck.objects.create(
                organization_id=organization_id,
                enrollment=enrollment,
                stage_id=stage_id,
                check_type=check_type,
                scheduled_date=scheduled_date,
                examiner_id=examiner_id,
                recommending_instructor_id=recommending_instructor_id,
                attempt_number=previous_attempts + 1,
                previous_attempt_id=previous_failed.id if previous_failed else None,
                **kwargs
            )

            # Generate check number
            stage_check.check_number = StageCheckService._generate_check_number(
                enrollment.program.code,
                stage_check.id
            )
            stage_check.save()

            logger.info(
                f"Created stage check {stage_check.check_number} "
                f"for enrollment {enrollment.enrollment_number}"
            )

            return stage_check

    @staticmethod
    def _generate_check_number(program_code: str, check_id: uuid.UUID) -> str:
        """Generate unique check number."""
        short_id = str(check_id)[:8].upper()
        return f"SC-{program_code}-{short_id}"

    @staticmethod
    def get_stage_check(
        check_id: uuid.UUID,
        organization_id: uuid.UUID
    ) -> StageCheck:
        """
        Get a stage check by ID.

        Args:
            check_id: Stage check UUID
            organization_id: Organization UUID

        Returns:
            StageCheck instance
        """
        return StageCheck.objects.select_related('enrollment').get(
            id=check_id,
            organization_id=organization_id
        )

    @staticmethod
    def list_stage_checks(
        organization_id: uuid.UUID,
        enrollment_id: uuid.UUID = None,
        examiner_id: uuid.UUID = None,
        stage_id: uuid.UUID = None,
        status: str = None,
        result: str = None,
        date_from: date = None,
        date_to: date = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[StageCheck], int]:
        """
        List stage checks with filters.

        Args:
            organization_id: Organization UUID
            enrollment_id: Filter by enrollment
            examiner_id: Filter by examiner
            stage_id: Filter by stage
            status: Filter by status
            result: Filter by result
            date_from: Start date
            date_to: End date
            page: Page number
            page_size: Items per page

        Returns:
            Tuple of (stage checks list, total count)
        """
        queryset = StageCheck.objects.filter(
            organization_id=organization_id
        ).select_related('enrollment')

        if enrollment_id:
            queryset = queryset.filter(enrollment_id=enrollment_id)
        if examiner_id:
            queryset = queryset.filter(examiner_id=examiner_id)
        if stage_id:
            queryset = queryset.filter(stage_id=stage_id)
        if status:
            queryset = queryset.filter(status=status)
        if result:
            queryset = queryset.filter(result=result)
        if date_from:
            queryset = queryset.filter(scheduled_date__gte=date_from)
        if date_to:
            queryset = queryset.filter(scheduled_date__lte=date_to)

        total = queryset.count()

        offset = (page - 1) * page_size
        stage_checks = list(queryset[offset:offset + page_size])

        return stage_checks, total

    @staticmethod
    def update_stage_check(
        check_id: uuid.UUID,
        organization_id: uuid.UUID,
        **kwargs
    ) -> StageCheck:
        """
        Update a stage check.

        Args:
            check_id: Stage check UUID
            organization_id: Organization UUID
            **kwargs: Fields to update

        Returns:
            Updated StageCheck instance
        """
        stage_check = StageCheck.objects.get(
            id=check_id,
            organization_id=organization_id
        )

        if stage_check.status == StageCheck.Status.COMPLETED:
            raise ValidationError("Cannot update a completed stage check")

        for key, value in kwargs.items():
            if hasattr(stage_check, key):
                setattr(stage_check, key, value)

        stage_check.save()

        logger.info(f"Updated stage check {stage_check.check_number}")
        return stage_check

    # ==========================================================================
    # Stage Check Workflow
    # ==========================================================================

    @staticmethod
    def schedule_stage_check(
        check_id: uuid.UUID,
        organization_id: uuid.UUID,
        scheduled_date: date,
        scheduled_time: time = None,
        examiner_id: uuid.UUID = None,
        location: str = None
    ) -> StageCheck:
        """
        Schedule a stage check.

        Args:
            check_id: Stage check UUID
            organization_id: Organization UUID
            scheduled_date: Date for the check
            scheduled_time: Time for the check
            examiner_id: Examiner UUID
            location: Location/airport

        Returns:
            Scheduled StageCheck
        """
        stage_check = StageCheck.objects.get(
            id=check_id,
            organization_id=organization_id
        )

        stage_check.schedule(scheduled_date, scheduled_time, examiner_id, location)

        logger.info(
            f"Scheduled stage check {stage_check.check_number} "
            f"for {scheduled_date}"
        )
        return stage_check

    @staticmethod
    def verify_prerequisites(
        check_id: uuid.UUID,
        organization_id: uuid.UUID,
        notes: str = None
    ) -> Dict[str, Any]:
        """
        Verify prerequisites for a stage check.

        Args:
            check_id: Stage check UUID
            organization_id: Organization UUID
            notes: Verification notes

        Returns:
            Verification result dictionary
        """
        stage_check = StageCheck.objects.get(
            id=check_id,
            organization_id=organization_id
        )

        enrollment = stage_check.enrollment
        stage_id = stage_check.stage_id

        # Get stage lessons
        stage_lessons = SyllabusLesson.objects.filter(
            program=enrollment.program,
            stage_id=stage_id,
            status='active'
        )

        # Get completed lessons
        completed_completions = LessonCompletion.objects.filter(
            enrollment=enrollment,
            is_completed=True,
            result__in=['pass', 'satisfactory']
        ).values_list('lesson_id', flat=True)

        completed_ids = set(str(lid) for lid in completed_completions)

        # Check each lesson
        missing_lessons = []
        for lesson in stage_lessons:
            if str(lesson.id) not in completed_ids:
                missing_lessons.append({
                    'id': str(lesson.id),
                    'code': lesson.code,
                    'name': lesson.name,
                })

        prerequisites_met = len(missing_lessons) == 0

        # Update stage check
        stage_check.prerequisites_verified = prerequisites_met
        stage_check.prerequisites_verification_date = timezone.now()
        if notes:
            stage_check.prerequisites_notes = notes
        stage_check.save()

        return {
            'verified': prerequisites_met,
            'missing_lessons': missing_lessons,
            'total_stage_lessons': stage_lessons.count(),
            'completed_lessons': len(completed_ids),
        }

    @staticmethod
    def start_stage_check(
        check_id: uuid.UUID,
        organization_id: uuid.UUID,
        examiner_id: uuid.UUID = None
    ) -> StageCheck:
        """
        Start conducting a stage check.

        Args:
            check_id: Stage check UUID
            organization_id: Organization UUID
            examiner_id: Examiner UUID

        Returns:
            Started StageCheck
        """
        stage_check = StageCheck.objects.get(
            id=check_id,
            organization_id=organization_id
        )

        if stage_check.status != StageCheck.Status.SCHEDULED:
            raise ValidationError(
                f"Cannot start stage check with status '{stage_check.status}'"
            )

        if not stage_check.prerequisites_verified:
            raise ValidationError(
                "Prerequisites must be verified before starting"
            )

        if examiner_id:
            stage_check.examiner_id = examiner_id

        stage_check.start()

        logger.info(f"Started stage check {stage_check.check_number}")
        return stage_check

    @staticmethod
    def pass_stage_check(
        check_id: uuid.UUID,
        organization_id: uuid.UUID,
        overall_grade: Decimal = None,
        oral_grade: Decimal = None,
        flight_grade: Decimal = None,
        examiner_comments: str = None,
        recommendations: str = None
    ) -> StageCheck:
        """
        Mark stage check as passed.

        Args:
            check_id: Stage check UUID
            organization_id: Organization UUID
            overall_grade: Overall grade
            oral_grade: Oral exam grade
            flight_grade: Flight check grade
            examiner_comments: Examiner feedback
            recommendations: Recommendations

        Returns:
            Passed StageCheck
        """
        stage_check = StageCheck.objects.get(
            id=check_id,
            organization_id=organization_id
        )

        if stage_check.status != StageCheck.Status.IN_PROGRESS:
            raise ValidationError("Stage check must be in progress to complete")

        with transaction.atomic():
            stage_check.oral_grade = oral_grade
            stage_check.flight_grade = flight_grade
            if recommendations:
                stage_check.recommendations = recommendations
            stage_check.save()

            stage_check.pass_check(overall_grade, examiner_comments)

            logger.info(
                f"Passed stage check {stage_check.check_number}, "
                f"grade: {overall_grade}"
            )

            return stage_check

    @staticmethod
    def fail_stage_check(
        check_id: uuid.UUID,
        organization_id: uuid.UUID,
        disapproval_reasons: List[str] = None,
        recheck_items: List[str] = None,
        additional_training: List[str] = None,
        examiner_comments: str = None,
        oral_grade: Decimal = None,
        flight_grade: Decimal = None
    ) -> StageCheck:
        """
        Mark stage check as failed.

        Args:
            check_id: Stage check UUID
            organization_id: Organization UUID
            disapproval_reasons: Reasons for failure
            recheck_items: Items to recheck
            additional_training: Required additional training
            examiner_comments: Examiner feedback
            oral_grade: Oral exam grade
            flight_grade: Flight check grade

        Returns:
            Failed StageCheck
        """
        stage_check = StageCheck.objects.get(
            id=check_id,
            organization_id=organization_id
        )

        if stage_check.status != StageCheck.Status.IN_PROGRESS:
            raise ValidationError("Stage check must be in progress to complete")

        with transaction.atomic():
            stage_check.oral_grade = oral_grade
            stage_check.flight_grade = flight_grade
            stage_check.save()

            stage_check.fail_check(
                disapproval_reasons,
                recheck_items,
                additional_training,
                examiner_comments
            )

            logger.info(
                f"Failed stage check {stage_check.check_number}"
            )

            return stage_check

    @staticmethod
    def defer_stage_check(
        check_id: uuid.UUID,
        organization_id: uuid.UUID,
        reason: str
    ) -> StageCheck:
        """
        Defer a stage check.

        Args:
            check_id: Stage check UUID
            organization_id: Organization UUID
            reason: Reason for deferral

        Returns:
            Deferred StageCheck
        """
        stage_check = StageCheck.objects.get(
            id=check_id,
            organization_id=organization_id
        )

        if stage_check.status == StageCheck.Status.COMPLETED:
            raise ValidationError("Cannot defer a completed stage check")

        stage_check.defer(reason)

        logger.info(
            f"Deferred stage check {stage_check.check_number}: {reason}"
        )
        return stage_check

    @staticmethod
    def cancel_stage_check(
        check_id: uuid.UUID,
        organization_id: uuid.UUID,
        reason: str,
        cancelled_by: uuid.UUID
    ) -> StageCheck:
        """
        Cancel a stage check.

        Args:
            check_id: Stage check UUID
            organization_id: Organization UUID
            reason: Cancellation reason
            cancelled_by: User cancelling

        Returns:
            Cancelled StageCheck
        """
        stage_check = StageCheck.objects.get(
            id=check_id,
            organization_id=organization_id
        )

        if stage_check.status == StageCheck.Status.COMPLETED:
            raise ValidationError("Cannot cancel a completed stage check")

        stage_check.cancel(reason, cancelled_by)

        logger.info(
            f"Cancelled stage check {stage_check.check_number}: {reason}"
        )
        return stage_check

    # ==========================================================================
    # Recording Details
    # ==========================================================================

    @staticmethod
    def record_oral_topic(
        check_id: uuid.UUID,
        organization_id: uuid.UUID,
        topic: str,
        grade: float,
        notes: str = None
    ) -> StageCheck:
        """
        Record oral examination topic result.

        Args:
            check_id: Stage check UUID
            organization_id: Organization UUID
            topic: Topic name
            grade: Topic grade
            notes: Topic notes

        Returns:
            Updated StageCheck
        """
        stage_check = StageCheck.objects.get(
            id=check_id,
            organization_id=organization_id
        )

        if stage_check.status != StageCheck.Status.IN_PROGRESS:
            raise ValidationError("Stage check must be in progress")

        stage_check.add_oral_topic(topic, grade, notes)

        return stage_check

    @staticmethod
    def record_flight_maneuver(
        check_id: uuid.UUID,
        organization_id: uuid.UUID,
        maneuver: str,
        grade: float,
        tolerances: Dict[str, Any] = None,
        notes: str = None
    ) -> StageCheck:
        """
        Record flight maneuver result.

        Args:
            check_id: Stage check UUID
            organization_id: Organization UUID
            maneuver: Maneuver name
            grade: Maneuver grade
            tolerances: Actual tolerances achieved
            notes: Maneuver notes

        Returns:
            Updated StageCheck
        """
        stage_check = StageCheck.objects.get(
            id=check_id,
            organization_id=organization_id
        )

        if stage_check.status != StageCheck.Status.IN_PROGRESS:
            raise ValidationError("Stage check must be in progress")

        stage_check.add_flight_maneuver(maneuver, grade, tolerances, notes)

        return stage_check

    @staticmethod
    def record_remedial_training(
        check_id: uuid.UUID,
        organization_id: uuid.UUID,
        training_date: date,
        hours: Decimal
    ) -> StageCheck:
        """
        Record completed remedial training.

        Args:
            check_id: Stage check UUID
            organization_id: Organization UUID
            training_date: Training date
            hours: Training hours

        Returns:
            Updated StageCheck
        """
        stage_check = StageCheck.objects.get(
            id=check_id,
            organization_id=organization_id
        )

        if stage_check.is_passed:
            raise ValidationError("Cannot add remedial training to passed check")

        stage_check.record_remedial_training(training_date, hours)

        logger.info(
            f"Recorded remedial training for {stage_check.check_number}: "
            f"{hours} hours on {training_date}"
        )
        return stage_check

    # ==========================================================================
    # Sign-offs
    # ==========================================================================

    @staticmethod
    def examiner_signoff(
        check_id: uuid.UUID,
        organization_id: uuid.UUID,
        examiner_id: uuid.UUID
    ) -> StageCheck:
        """
        Record examiner sign-off.

        Args:
            check_id: Stage check UUID
            organization_id: Organization UUID
            examiner_id: Examiner UUID

        Returns:
            Updated StageCheck
        """
        stage_check = StageCheck.objects.get(
            id=check_id,
            organization_id=organization_id
        )

        if stage_check.status != StageCheck.Status.COMPLETED:
            raise ValidationError("Stage check must be completed for sign-off")

        if stage_check.examiner_id != examiner_id:
            logger.warning(
                f"Sign-off by different examiner: "
                f"check {stage_check.examiner_id}, signing {examiner_id}"
            )

        stage_check.examiner_sign()

        logger.info(
            f"Examiner sign-off for stage check {stage_check.check_number}"
        )
        return stage_check

    @staticmethod
    def student_signoff(
        check_id: uuid.UUID,
        organization_id: uuid.UUID,
        student_id: uuid.UUID
    ) -> StageCheck:
        """
        Record student sign-off.

        Args:
            check_id: Stage check UUID
            organization_id: Organization UUID
            student_id: Student UUID

        Returns:
            Updated StageCheck
        """
        stage_check = StageCheck.objects.get(
            id=check_id,
            organization_id=organization_id
        )

        if stage_check.enrollment.student_id != student_id:
            raise ValidationError("Student does not own this enrollment")

        stage_check.student_sign()

        logger.info(
            f"Student sign-off for stage check {stage_check.check_number}"
        )
        return stage_check

    # ==========================================================================
    # Recheck
    # ==========================================================================

    @staticmethod
    def create_recheck(
        check_id: uuid.UUID,
        organization_id: uuid.UUID,
        scheduled_date: date = None,
        examiner_id: uuid.UUID = None
    ) -> StageCheck:
        """
        Create a recheck for a failed stage check.

        Args:
            check_id: Failed stage check UUID
            organization_id: Organization UUID
            scheduled_date: Schedule date for recheck
            examiner_id: Examiner UUID

        Returns:
            New StageCheck for recheck
        """
        original_check = StageCheck.objects.get(
            id=check_id,
            organization_id=organization_id
        )

        if original_check.is_passed:
            raise ValidationError("Cannot create recheck for passed stage check")

        if not original_check.can_retry:
            raise ValidationError("Maximum attempts reached for this stage check")

        # Check remedial training if required
        if (original_check.additional_training_required and
            not original_check.remedial_training_completed):
            raise ValidationError(
                "Remedial training must be completed before recheck"
            )

        with transaction.atomic():
            recheck = original_check.create_recheck()

            if scheduled_date:
                recheck.scheduled_date = scheduled_date
            if examiner_id:
                recheck.examiner_id = examiner_id

            # Copy recheck items from original
            recheck.flight_areas = original_check.recheck_items
            recheck.save()

            logger.info(
                f"Created recheck {recheck.check_number} "
                f"for {original_check.check_number}"
            )

            return recheck

    # ==========================================================================
    # Statistics
    # ==========================================================================

    @staticmethod
    def get_stage_check_statistics(
        organization_id: uuid.UUID,
        program_id: uuid.UUID = None,
        examiner_id: uuid.UUID = None,
        date_from: date = None,
        date_to: date = None
    ) -> Dict[str, Any]:
        """
        Get stage check statistics.

        Args:
            organization_id: Organization UUID
            program_id: Filter by program
            examiner_id: Filter by examiner
            date_from: Start date
            date_to: End date

        Returns:
            Statistics dictionary
        """
        queryset = StageCheck.objects.filter(
            organization_id=organization_id
        )

        if program_id:
            queryset = queryset.filter(enrollment__program_id=program_id)
        if examiner_id:
            queryset = queryset.filter(examiner_id=examiner_id)
        if date_from:
            queryset = queryset.filter(actual_date__gte=date_from)
        if date_to:
            queryset = queryset.filter(actual_date__lte=date_to)

        stats = queryset.aggregate(
            total=Count('id'),
            completed=Count('id', filter=Q(status='completed')),
            passed=Count('id', filter=Q(is_passed=True)),
            failed=Count('id', filter=Q(result='fail')),
            cancelled=Count('id', filter=Q(status='cancelled')),
            deferred=Count('id', filter=Q(status='deferred')),
            avg_oral_grade=Avg('oral_grade', filter=Q(oral_grade__isnull=False)),
            avg_flight_grade=Avg('flight_grade', filter=Q(flight_grade__isnull=False)),
            avg_overall_grade=Avg('overall_grade', filter=Q(overall_grade__isnull=False)),
        )

        completed = stats['completed'] or 0
        passed = stats['passed'] or 0
        pass_rate = (passed / completed * 100) if completed > 0 else 0

        # First attempt pass rate
        first_attempts = queryset.filter(attempt_number=1)
        first_attempt_stats = first_attempts.aggregate(
            total=Count('id'),
            passed=Count('id', filter=Q(is_passed=True))
        )
        first_attempt_total = first_attempt_stats['total'] or 0
        first_attempt_passed = first_attempt_stats['passed'] or 0
        first_attempt_rate = (
            first_attempt_passed / first_attempt_total * 100
            if first_attempt_total > 0 else 0
        )

        return {
            'total': stats['total'] or 0,
            'completed': completed,
            'passed': passed,
            'failed': stats['failed'] or 0,
            'cancelled': stats['cancelled'] or 0,
            'deferred': stats['deferred'] or 0,
            'pass_rate': round(pass_rate, 2),
            'first_attempt_pass_rate': round(first_attempt_rate, 2),
            'average_grades': {
                'oral': round(float(stats['avg_oral_grade'] or 0), 2),
                'flight': round(float(stats['avg_flight_grade'] or 0), 2),
                'overall': round(float(stats['avg_overall_grade'] or 0), 2),
            }
        }
