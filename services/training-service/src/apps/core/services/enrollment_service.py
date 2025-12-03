# services/training-service/src/apps/core/services/enrollment_service.py
"""
Enrollment Service

Business logic for student enrollment management.
"""

import uuid
import logging
from decimal import Decimal
from typing import List, Dict, Any, Optional, Tuple
from datetime import date, timedelta

from django.db import transaction
from django.db.models import Q, Count, Avg, Sum, F
from django.core.exceptions import ValidationError
from django.utils import timezone

from ..models import (
    StudentEnrollment,
    TrainingProgram,
    LessonCompletion,
    StageCheck
)

logger = logging.getLogger(__name__)


class EnrollmentService:
    """
    Service class for student enrollment operations.

    Handles enrollment lifecycle, progress tracking, and status management.
    """

    # ==========================================================================
    # Enrollment CRUD
    # ==========================================================================

    @staticmethod
    def create_enrollment(
        organization_id: uuid.UUID,
        student_id: uuid.UUID,
        program_id: uuid.UUID,
        enrollment_date: date = None,
        primary_instructor_id: uuid.UUID = None,
        expected_completion: date = None,
        **kwargs
    ) -> StudentEnrollment:
        """
        Create a new student enrollment.

        Args:
            organization_id: Organization UUID
            student_id: Student UUID
            program_id: Training program UUID
            enrollment_date: Date of enrollment (defaults to today)
            primary_instructor_id: Assigned instructor UUID
            expected_completion: Expected completion date
            **kwargs: Additional enrollment fields

        Returns:
            Created StudentEnrollment instance

        Raises:
            ValidationError: If student already enrolled in program
        """
        # Check for existing enrollment
        if StudentEnrollment.objects.filter(
            student_id=student_id,
            program_id=program_id,
            status__in=['pending', 'active', 'on_hold']
        ).exists():
            raise ValidationError(
                "Student is already enrolled in this program"
            )

        # Get program
        program = TrainingProgram.objects.get(
            id=program_id,
            organization_id=organization_id
        )

        # Validate program is published
        if not program.is_published:
            raise ValidationError(
                "Cannot enroll in unpublished program"
            )

        with transaction.atomic():
            # Calculate expected completion if not provided
            if not expected_completion and program.estimated_duration_days:
                expected_completion = (
                    (enrollment_date or date.today()) +
                    timedelta(days=program.estimated_duration_days)
                )

            # Calculate expiry date if max duration set
            expiry_date = None
            if program.max_duration_months:
                expiry_date = (
                    (enrollment_date or date.today()) +
                    timedelta(days=program.max_duration_months * 30)
                )

            # Get total lessons count
            total_lessons = program.lessons.filter(status='active').count()

            enrollment = StudentEnrollment.objects.create(
                organization_id=organization_id,
                student_id=student_id,
                program=program,
                enrollment_date=enrollment_date or date.today(),
                expected_completion=expected_completion,
                expiry_date=expiry_date,
                primary_instructor_id=primary_instructor_id,
                lessons_total=total_lessons,
                **kwargs
            )

            # Generate enrollment number
            enrollment.enrollment_number = EnrollmentService._generate_enrollment_number(
                organization_id,
                program.code,
                enrollment.id
            )
            enrollment.save()

            logger.info(
                f"Created enrollment {enrollment.enrollment_number} "
                f"for student {student_id} in program {program.code}"
            )

            return enrollment

    @staticmethod
    def _generate_enrollment_number(
        organization_id: uuid.UUID,
        program_code: str,
        enrollment_id: uuid.UUID
    ) -> str:
        """Generate unique enrollment number."""
        year = date.today().year
        short_id = str(enrollment_id)[:8].upper()
        return f"{program_code}-{year}-{short_id}"

    @staticmethod
    def get_enrollment(
        enrollment_id: uuid.UUID,
        organization_id: uuid.UUID
    ) -> StudentEnrollment:
        """
        Get an enrollment by ID.

        Args:
            enrollment_id: Enrollment UUID
            organization_id: Organization UUID

        Returns:
            StudentEnrollment instance
        """
        return StudentEnrollment.objects.select_related('program').get(
            id=enrollment_id,
            organization_id=organization_id
        )

    @staticmethod
    def list_enrollments(
        organization_id: uuid.UUID,
        student_id: uuid.UUID = None,
        program_id: uuid.UUID = None,
        instructor_id: uuid.UUID = None,
        status: str = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[StudentEnrollment], int]:
        """
        List enrollments with filters.

        Args:
            organization_id: Organization UUID
            student_id: Filter by student
            program_id: Filter by program
            instructor_id: Filter by instructor
            status: Filter by status
            page: Page number
            page_size: Items per page

        Returns:
            Tuple of (enrollments list, total count)
        """
        queryset = StudentEnrollment.objects.filter(
            organization_id=organization_id
        ).select_related('program')

        # Apply filters
        if student_id:
            queryset = queryset.filter(student_id=student_id)
        if program_id:
            queryset = queryset.filter(program_id=program_id)
        if instructor_id:
            queryset = queryset.filter(
                Q(primary_instructor_id=instructor_id) |
                Q(secondary_instructor_ids__contains=[str(instructor_id)])
            )
        if status:
            queryset = queryset.filter(status=status)

        total = queryset.count()

        # Pagination
        offset = (page - 1) * page_size
        enrollments = list(queryset[offset:offset + page_size])

        return enrollments, total

    @staticmethod
    def update_enrollment(
        enrollment_id: uuid.UUID,
        organization_id: uuid.UUID,
        **kwargs
    ) -> StudentEnrollment:
        """
        Update an enrollment.

        Args:
            enrollment_id: Enrollment UUID
            organization_id: Organization UUID
            **kwargs: Fields to update

        Returns:
            Updated StudentEnrollment instance
        """
        enrollment = StudentEnrollment.objects.get(
            id=enrollment_id,
            organization_id=organization_id
        )

        # Update allowed fields
        allowed_fields = {
            'primary_instructor_id', 'secondary_instructor_ids',
            'expected_completion', 'notes', 'instructor_notes',
            'metadata'
        }

        for key, value in kwargs.items():
            if key in allowed_fields and hasattr(enrollment, key):
                setattr(enrollment, key, value)

        enrollment.save()

        logger.info(f"Updated enrollment {enrollment.enrollment_number}")
        return enrollment

    # ==========================================================================
    # Status Management
    # ==========================================================================

    @staticmethod
    def activate_enrollment(
        enrollment_id: uuid.UUID,
        organization_id: uuid.UUID,
        start_date: date = None
    ) -> StudentEnrollment:
        """
        Activate an enrollment.

        Args:
            enrollment_id: Enrollment UUID
            organization_id: Organization UUID
            start_date: Training start date

        Returns:
            Activated StudentEnrollment
        """
        enrollment = StudentEnrollment.objects.get(
            id=enrollment_id,
            organization_id=organization_id
        )

        if enrollment.status not in ['pending', 'on_hold']:
            raise ValidationError(
                f"Cannot activate enrollment with status '{enrollment.status}'"
            )

        enrollment.activate(start_date)

        logger.info(f"Activated enrollment {enrollment.enrollment_number}")
        return enrollment

    @staticmethod
    def put_on_hold(
        enrollment_id: uuid.UUID,
        organization_id: uuid.UUID,
        reason: str
    ) -> StudentEnrollment:
        """
        Put enrollment on hold.

        Args:
            enrollment_id: Enrollment UUID
            organization_id: Organization UUID
            reason: Reason for hold

        Returns:
            Updated StudentEnrollment
        """
        enrollment = StudentEnrollment.objects.get(
            id=enrollment_id,
            organization_id=organization_id
        )

        if enrollment.status != 'active':
            raise ValidationError(
                "Can only put active enrollments on hold"
            )

        enrollment.put_on_hold(reason)

        logger.info(
            f"Put enrollment {enrollment.enrollment_number} on hold: {reason}"
        )
        return enrollment

    @staticmethod
    def resume_enrollment(
        enrollment_id: uuid.UUID,
        organization_id: uuid.UUID
    ) -> StudentEnrollment:
        """
        Resume enrollment from hold.

        Args:
            enrollment_id: Enrollment UUID
            organization_id: Organization UUID

        Returns:
            Resumed StudentEnrollment
        """
        enrollment = StudentEnrollment.objects.get(
            id=enrollment_id,
            organization_id=organization_id
        )

        if enrollment.status != 'on_hold':
            raise ValidationError(
                "Can only resume enrollments that are on hold"
            )

        enrollment.resume()

        logger.info(f"Resumed enrollment {enrollment.enrollment_number}")
        return enrollment

    @staticmethod
    def withdraw_enrollment(
        enrollment_id: uuid.UUID,
        organization_id: uuid.UUID,
        reason: str
    ) -> StudentEnrollment:
        """
        Withdraw from enrollment.

        Args:
            enrollment_id: Enrollment UUID
            organization_id: Organization UUID
            reason: Withdrawal reason

        Returns:
            Withdrawn StudentEnrollment
        """
        enrollment = StudentEnrollment.objects.get(
            id=enrollment_id,
            organization_id=organization_id
        )

        if enrollment.status in ['completed', 'withdrawn']:
            raise ValidationError(
                f"Cannot withdraw from {enrollment.status} enrollment"
            )

        enrollment.withdraw(reason)

        logger.info(
            f"Withdrew enrollment {enrollment.enrollment_number}: {reason}"
        )
        return enrollment

    @staticmethod
    def complete_enrollment(
        enrollment_id: uuid.UUID,
        organization_id: uuid.UUID,
        completion_date: date = None
    ) -> StudentEnrollment:
        """
        Mark enrollment as completed.

        Args:
            enrollment_id: Enrollment UUID
            organization_id: Organization UUID
            completion_date: Completion date

        Returns:
            Completed StudentEnrollment
        """
        enrollment = StudentEnrollment.objects.get(
            id=enrollment_id,
            organization_id=organization_id
        )

        # Verify completion requirements
        requirements = enrollment.check_hour_requirements()
        if not requirements['met']:
            missing = [
                k for k, v in requirements['details'].items()
                if not v['met']
            ]
            raise ValidationError(
                f"Hour requirements not met: {', '.join(missing)}"
            )

        # Verify all lessons completed
        if enrollment.lessons_completed < enrollment.lessons_total:
            raise ValidationError(
                f"Not all lessons completed "
                f"({enrollment.lessons_completed}/{enrollment.lessons_total})"
            )

        enrollment.complete(completion_date)

        logger.info(f"Completed enrollment {enrollment.enrollment_number}")
        return enrollment

    # ==========================================================================
    # Instructor Assignment
    # ==========================================================================

    @staticmethod
    def assign_primary_instructor(
        enrollment_id: uuid.UUID,
        organization_id: uuid.UUID,
        instructor_id: uuid.UUID
    ) -> StudentEnrollment:
        """
        Assign primary instructor to enrollment.

        Args:
            enrollment_id: Enrollment UUID
            organization_id: Organization UUID
            instructor_id: Instructor UUID

        Returns:
            Updated StudentEnrollment
        """
        enrollment = StudentEnrollment.objects.get(
            id=enrollment_id,
            organization_id=organization_id
        )

        enrollment.primary_instructor_id = instructor_id
        enrollment.save()

        logger.info(
            f"Assigned instructor {instructor_id} to "
            f"enrollment {enrollment.enrollment_number}"
        )
        return enrollment

    @staticmethod
    def add_secondary_instructor(
        enrollment_id: uuid.UUID,
        organization_id: uuid.UUID,
        instructor_id: uuid.UUID
    ) -> StudentEnrollment:
        """
        Add secondary instructor to enrollment.

        Args:
            enrollment_id: Enrollment UUID
            organization_id: Organization UUID
            instructor_id: Instructor UUID

        Returns:
            Updated StudentEnrollment
        """
        enrollment = StudentEnrollment.objects.get(
            id=enrollment_id,
            organization_id=organization_id
        )

        instructor_str = str(instructor_id)
        if instructor_str not in enrollment.secondary_instructor_ids:
            enrollment.secondary_instructor_ids.append(instructor_str)
            enrollment.save()

        return enrollment

    @staticmethod
    def remove_secondary_instructor(
        enrollment_id: uuid.UUID,
        organization_id: uuid.UUID,
        instructor_id: uuid.UUID
    ) -> StudentEnrollment:
        """
        Remove secondary instructor from enrollment.

        Args:
            enrollment_id: Enrollment UUID
            organization_id: Organization UUID
            instructor_id: Instructor UUID

        Returns:
            Updated StudentEnrollment
        """
        enrollment = StudentEnrollment.objects.get(
            id=enrollment_id,
            organization_id=organization_id
        )

        instructor_str = str(instructor_id)
        if instructor_str in enrollment.secondary_instructor_ids:
            enrollment.secondary_instructor_ids.remove(instructor_str)
            enrollment.save()

        return enrollment

    # ==========================================================================
    # Progress and Hours
    # ==========================================================================

    @staticmethod
    def update_progress(
        enrollment_id: uuid.UUID,
        organization_id: uuid.UUID
    ) -> StudentEnrollment:
        """
        Update enrollment progress from completions.

        Args:
            enrollment_id: Enrollment UUID
            organization_id: Organization UUID

        Returns:
            Updated StudentEnrollment
        """
        enrollment = StudentEnrollment.objects.get(
            id=enrollment_id,
            organization_id=organization_id
        )

        enrollment.update_progress()
        enrollment.update_hours()

        return enrollment

    @staticmethod
    def add_hours(
        enrollment_id: uuid.UUID,
        organization_id: uuid.UUID,
        flight_hours: Decimal = None,
        ground_hours: Decimal = None,
        simulator_hours: Decimal = None,
        dual_hours: Decimal = None,
        solo_hours: Decimal = None,
        pic_hours: Decimal = None,
        cross_country_hours: Decimal = None,
        night_hours: Decimal = None,
        instrument_hours: Decimal = None
    ) -> StudentEnrollment:
        """
        Manually add hours to enrollment.

        Args:
            enrollment_id: Enrollment UUID
            organization_id: Organization UUID
            Various hour types to add

        Returns:
            Updated StudentEnrollment
        """
        enrollment = StudentEnrollment.objects.get(
            id=enrollment_id,
            organization_id=organization_id
        )

        if flight_hours:
            enrollment.total_flight_hours += flight_hours
        if ground_hours:
            enrollment.total_ground_hours += ground_hours
        if simulator_hours:
            enrollment.total_simulator_hours += simulator_hours
        if dual_hours:
            enrollment.dual_hours += dual_hours
        if solo_hours:
            enrollment.solo_hours += solo_hours
        if pic_hours:
            enrollment.pic_hours += pic_hours
        if cross_country_hours:
            enrollment.cross_country_hours += cross_country_hours
        if night_hours:
            enrollment.night_hours += night_hours
        if instrument_hours:
            enrollment.instrument_hours += instrument_hours

        enrollment.save()

        logger.info(f"Added hours to enrollment {enrollment.enrollment_number}")
        return enrollment

    # ==========================================================================
    # Stage Advancement
    # ==========================================================================

    @staticmethod
    def advance_to_next_stage(
        enrollment_id: uuid.UUID,
        organization_id: uuid.UUID
    ) -> StudentEnrollment:
        """
        Advance student to next stage.

        Args:
            enrollment_id: Enrollment UUID
            organization_id: Organization UUID

        Returns:
            Updated StudentEnrollment
        """
        enrollment = StudentEnrollment.objects.get(
            id=enrollment_id,
            organization_id=organization_id
        )

        if not enrollment.current_stage_id:
            raise ValidationError("No current stage set")

        # Get next stage
        next_stage = enrollment.program.get_next_stage(
            str(enrollment.current_stage_id)
        )

        if not next_stage:
            raise ValidationError("Already at final stage")

        # Verify current stage is complete
        current_stage_check = StageCheck.objects.filter(
            enrollment=enrollment,
            stage_id=enrollment.current_stage_id,
            is_passed=True
        ).exists()

        if not current_stage_check:
            raise ValidationError(
                "Must pass stage check before advancing"
            )

        enrollment.advance_to_stage(next_stage['id'])

        logger.info(
            f"Advanced enrollment {enrollment.enrollment_number} "
            f"to stage {next_stage['name']}"
        )
        return enrollment

    # ==========================================================================
    # Financial
    # ==========================================================================

    @staticmethod
    def record_payment(
        enrollment_id: uuid.UUID,
        organization_id: uuid.UUID,
        amount: Decimal,
        payment_reference: str = None
    ) -> StudentEnrollment:
        """
        Record a payment for enrollment.

        Args:
            enrollment_id: Enrollment UUID
            organization_id: Organization UUID
            amount: Payment amount
            payment_reference: Payment reference

        Returns:
            Updated StudentEnrollment
        """
        enrollment = StudentEnrollment.objects.get(
            id=enrollment_id,
            organization_id=organization_id
        )

        enrollment.total_paid += amount
        enrollment.balance = enrollment.total_charges - enrollment.total_paid
        enrollment.save()

        logger.info(
            f"Recorded payment {amount} for "
            f"enrollment {enrollment.enrollment_number}"
        )
        return enrollment

    @staticmethod
    def add_charge(
        enrollment_id: uuid.UUID,
        organization_id: uuid.UUID,
        amount: Decimal,
        description: str = None
    ) -> StudentEnrollment:
        """
        Add a charge to enrollment.

        Args:
            enrollment_id: Enrollment UUID
            organization_id: Organization UUID
            amount: Charge amount
            description: Charge description

        Returns:
            Updated StudentEnrollment
        """
        enrollment = StudentEnrollment.objects.get(
            id=enrollment_id,
            organization_id=organization_id
        )

        enrollment.total_charges += amount
        enrollment.balance = enrollment.total_charges - enrollment.total_paid
        enrollment.save()

        logger.info(
            f"Added charge {amount} to "
            f"enrollment {enrollment.enrollment_number}"
        )
        return enrollment

    # ==========================================================================
    # Bulk Operations
    # ==========================================================================

    @staticmethod
    def check_expired_enrollments(
        organization_id: uuid.UUID
    ) -> List[StudentEnrollment]:
        """
        Find and mark expired enrollments.

        Args:
            organization_id: Organization UUID

        Returns:
            List of expired enrollments
        """
        today = date.today()

        expired = StudentEnrollment.objects.filter(
            organization_id=organization_id,
            status='active',
            expiry_date__lt=today
        )

        expired_list = list(expired)

        for enrollment in expired_list:
            enrollment.status = StudentEnrollment.Status.EXPIRED
            enrollment.save()

            logger.info(
                f"Marked enrollment {enrollment.enrollment_number} as expired"
            )

        return expired_list

    @staticmethod
    def get_student_enrollments_summary(
        organization_id: uuid.UUID,
        student_id: uuid.UUID
    ) -> Dict[str, Any]:
        """
        Get summary of all enrollments for a student.

        Args:
            organization_id: Organization UUID
            student_id: Student UUID

        Returns:
            Summary dictionary
        """
        enrollments = StudentEnrollment.objects.filter(
            organization_id=organization_id,
            student_id=student_id
        ).select_related('program')

        total_hours = enrollments.aggregate(
            flight=Sum('total_flight_hours'),
            ground=Sum('total_ground_hours'),
            simulator=Sum('total_simulator_hours'),
        )

        return {
            'student_id': str(student_id),
            'enrollments': {
                'total': enrollments.count(),
                'active': enrollments.filter(status='active').count(),
                'completed': enrollments.filter(status='completed').count(),
            },
            'total_hours': {
                'flight': float(total_hours['flight'] or 0),
                'ground': float(total_hours['ground'] or 0),
                'simulator': float(total_hours['simulator'] or 0),
            },
            'programs': [
                {
                    'enrollment_id': str(e.id),
                    'program_code': e.program.code,
                    'program_name': e.program.name,
                    'status': e.status,
                    'progress': float(e.completion_percentage),
                }
                for e in enrollments
            ]
        }
