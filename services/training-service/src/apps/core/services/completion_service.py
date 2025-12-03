# services/training-service/src/apps/core/services/completion_service.py
"""
Completion Service

Business logic for lesson completion and grading.
"""

import uuid
import logging
from decimal import Decimal
from typing import List, Dict, Any, Optional, Tuple
from datetime import date, time

from django.db import transaction
from django.db.models import Q, Avg, Sum, Count
from django.core.exceptions import ValidationError
from django.utils import timezone

from ..models import (
    LessonCompletion,
    ExerciseGrade,
    StudentEnrollment,
    SyllabusLesson,
    Exercise
)

logger = logging.getLogger(__name__)


class CompletionService:
    """
    Service class for lesson completion operations.

    Handles lesson completions, exercise grading, and progress tracking.
    """

    # ==========================================================================
    # Lesson Completion CRUD
    # ==========================================================================

    @staticmethod
    def create_completion(
        organization_id: uuid.UUID,
        enrollment_id: uuid.UUID,
        lesson_id: uuid.UUID,
        instructor_id: uuid.UUID = None,
        scheduled_date: date = None,
        **kwargs
    ) -> LessonCompletion:
        """
        Create a new lesson completion record.

        Args:
            organization_id: Organization UUID
            enrollment_id: Enrollment UUID
            lesson_id: Lesson UUID
            instructor_id: Instructor UUID
            scheduled_date: Scheduled date
            **kwargs: Additional completion fields

        Returns:
            Created LessonCompletion instance
        """
        enrollment = StudentEnrollment.objects.get(
            id=enrollment_id,
            organization_id=organization_id
        )

        lesson = SyllabusLesson.objects.get(
            id=lesson_id,
            organization_id=organization_id
        )

        # Verify lesson belongs to enrollment's program
        if lesson.program_id != enrollment.program_id:
            raise ValidationError(
                "Lesson does not belong to enrollment's program"
            )

        # Check if lesson already has a completion in progress
        existing = LessonCompletion.objects.filter(
            enrollment=enrollment,
            lesson=lesson,
            status__in=['scheduled', 'in_progress']
        ).first()

        if existing:
            raise ValidationError(
                f"Lesson already has a {existing.status} completion record"
            )

        # Determine attempt number
        previous_attempts = LessonCompletion.objects.filter(
            enrollment=enrollment,
            lesson=lesson
        ).count()

        # Check max attempts
        if lesson.max_attempts and previous_attempts >= lesson.max_attempts:
            raise ValidationError(
                f"Maximum attempts ({lesson.max_attempts}) reached for this lesson"
            )

        with transaction.atomic():
            completion = LessonCompletion.objects.create(
                organization_id=organization_id,
                enrollment=enrollment,
                lesson=lesson,
                instructor_id=instructor_id,
                scheduled_date=scheduled_date or date.today(),
                attempt_number=previous_attempts + 1,
                is_repeat=previous_attempts > 0,
                **kwargs
            )

            logger.info(
                f"Created lesson completion for lesson {lesson.code}, "
                f"enrollment {enrollment.enrollment_number}"
            )

            return completion

    @staticmethod
    def get_completion(
        completion_id: uuid.UUID,
        organization_id: uuid.UUID
    ) -> LessonCompletion:
        """
        Get a lesson completion by ID.

        Args:
            completion_id: Completion UUID
            organization_id: Organization UUID

        Returns:
            LessonCompletion instance
        """
        return LessonCompletion.objects.select_related(
            'enrollment', 'lesson'
        ).get(
            id=completion_id,
            organization_id=organization_id
        )

    @staticmethod
    def list_completions(
        organization_id: uuid.UUID,
        enrollment_id: uuid.UUID = None,
        lesson_id: uuid.UUID = None,
        instructor_id: uuid.UUID = None,
        status: str = None,
        is_completed: bool = None,
        date_from: date = None,
        date_to: date = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[LessonCompletion], int]:
        """
        List lesson completions with filters.

        Args:
            organization_id: Organization UUID
            enrollment_id: Filter by enrollment
            lesson_id: Filter by lesson
            instructor_id: Filter by instructor
            status: Filter by status
            is_completed: Filter by completion state
            date_from: Filter by date range start
            date_to: Filter by date range end
            page: Page number
            page_size: Items per page

        Returns:
            Tuple of (completions list, total count)
        """
        queryset = LessonCompletion.objects.filter(
            organization_id=organization_id
        ).select_related('enrollment', 'lesson')

        # Apply filters
        if enrollment_id:
            queryset = queryset.filter(enrollment_id=enrollment_id)
        if lesson_id:
            queryset = queryset.filter(lesson_id=lesson_id)
        if instructor_id:
            queryset = queryset.filter(instructor_id=instructor_id)
        if status:
            queryset = queryset.filter(status=status)
        if is_completed is not None:
            queryset = queryset.filter(is_completed=is_completed)
        if date_from:
            queryset = queryset.filter(
                Q(actual_date__gte=date_from) |
                Q(scheduled_date__gte=date_from)
            )
        if date_to:
            queryset = queryset.filter(
                Q(actual_date__lte=date_to) |
                Q(scheduled_date__lte=date_to)
            )

        total = queryset.count()

        # Pagination
        offset = (page - 1) * page_size
        completions = list(queryset[offset:offset + page_size])

        return completions, total

    @staticmethod
    def update_completion(
        completion_id: uuid.UUID,
        organization_id: uuid.UUID,
        **kwargs
    ) -> LessonCompletion:
        """
        Update a lesson completion.

        Args:
            completion_id: Completion UUID
            organization_id: Organization UUID
            **kwargs: Fields to update

        Returns:
            Updated LessonCompletion instance
        """
        completion = LessonCompletion.objects.get(
            id=completion_id,
            organization_id=organization_id
        )

        if completion.is_completed:
            raise ValidationError("Cannot update a completed lesson")

        # Update allowed fields
        for key, value in kwargs.items():
            if hasattr(completion, key):
                setattr(completion, key, value)

        completion.save()

        logger.info(f"Updated lesson completion {completion_id}")
        return completion

    # ==========================================================================
    # Lesson Completion Workflow
    # ==========================================================================

    @staticmethod
    def start_lesson(
        completion_id: uuid.UUID,
        organization_id: uuid.UUID,
        instructor_id: uuid.UUID = None
    ) -> LessonCompletion:
        """
        Start a lesson (mark as in progress).

        Args:
            completion_id: Completion UUID
            organization_id: Organization UUID
            instructor_id: Instructor UUID

        Returns:
            Updated LessonCompletion
        """
        completion = LessonCompletion.objects.get(
            id=completion_id,
            organization_id=organization_id
        )

        if completion.status != LessonCompletion.Status.SCHEDULED:
            raise ValidationError(
                f"Cannot start lesson with status '{completion.status}'"
            )

        completion.status = LessonCompletion.Status.IN_PROGRESS
        completion.actual_date = date.today()
        completion.actual_start_time = timezone.now().time()

        if instructor_id:
            completion.instructor_id = instructor_id

        completion.save()

        logger.info(f"Started lesson completion {completion_id}")
        return completion

    @staticmethod
    def complete_lesson(
        completion_id: uuid.UUID,
        organization_id: uuid.UUID,
        grade: Decimal = None,
        result: str = None,
        instructor_comments: str = None,
        flight_time: Decimal = None,
        ground_time: Decimal = None,
        simulator_time: Decimal = None,
        **hour_kwargs
    ) -> LessonCompletion:
        """
        Complete a lesson with results.

        Args:
            completion_id: Completion UUID
            organization_id: Organization UUID
            grade: Overall grade
            result: Pass/Fail result
            instructor_comments: Instructor feedback
            flight_time: Flight time in hours
            ground_time: Ground time in hours
            simulator_time: Simulator time in hours
            **hour_kwargs: Additional hour fields

        Returns:
            Completed LessonCompletion
        """
        completion = LessonCompletion.objects.get(
            id=completion_id,
            organization_id=organization_id
        )

        if completion.is_completed:
            raise ValidationError("Lesson is already completed")

        with transaction.atomic():
            # Set times
            if flight_time is not None:
                completion.flight_time = flight_time
            if ground_time is not None:
                completion.ground_time = ground_time
            if simulator_time is not None:
                completion.simulator_time = simulator_time

            # Set hour categories
            for key, value in hour_kwargs.items():
                if hasattr(completion, key) and value is not None:
                    setattr(completion, key, value)

            # Calculate grade from exercises if not provided
            if grade is None:
                grade = completion.calculate_grade_from_exercises()

            completion.actual_end_time = timezone.now().time()
            completion.complete(grade, result, instructor_comments)

            logger.info(
                f"Completed lesson {completion.lesson.code}, "
                f"grade: {grade}, result: {completion.result}"
            )

            return completion

    @staticmethod
    def cancel_lesson(
        completion_id: uuid.UUID,
        organization_id: uuid.UUID,
        reason: str,
        cancelled_by: uuid.UUID
    ) -> LessonCompletion:
        """
        Cancel a scheduled lesson.

        Args:
            completion_id: Completion UUID
            organization_id: Organization UUID
            reason: Cancellation reason
            cancelled_by: User cancelling

        Returns:
            Cancelled LessonCompletion
        """
        completion = LessonCompletion.objects.get(
            id=completion_id,
            organization_id=organization_id
        )

        if completion.is_completed:
            raise ValidationError("Cannot cancel a completed lesson")

        completion.cancel(reason, cancelled_by)

        logger.info(f"Cancelled lesson completion {completion_id}: {reason}")
        return completion

    @staticmethod
    def mark_no_show(
        completion_id: uuid.UUID,
        organization_id: uuid.UUID
    ) -> LessonCompletion:
        """
        Mark student as no-show for lesson.

        Args:
            completion_id: Completion UUID
            organization_id: Organization UUID

        Returns:
            Updated LessonCompletion
        """
        completion = LessonCompletion.objects.get(
            id=completion_id,
            organization_id=organization_id
        )

        if completion.status != LessonCompletion.Status.SCHEDULED:
            raise ValidationError("Can only mark scheduled lessons as no-show")

        completion.mark_no_show()

        logger.info(f"Marked no-show for lesson completion {completion_id}")
        return completion

    # ==========================================================================
    # Sign-offs
    # ==========================================================================

    @staticmethod
    def instructor_signoff(
        completion_id: uuid.UUID,
        organization_id: uuid.UUID,
        instructor_id: uuid.UUID,
        notes: str = None
    ) -> LessonCompletion:
        """
        Record instructor sign-off.

        Args:
            completion_id: Completion UUID
            organization_id: Organization UUID
            instructor_id: Instructor UUID
            notes: Sign-off notes

        Returns:
            Updated LessonCompletion
        """
        completion = LessonCompletion.objects.get(
            id=completion_id,
            organization_id=organization_id
        )

        if not completion.is_completed:
            raise ValidationError("Lesson must be completed before sign-off")

        # Verify instructor conducted the lesson
        if completion.instructor_id != instructor_id:
            logger.warning(
                f"Sign-off by different instructor: "
                f"lesson {completion.instructor_id}, signing {instructor_id}"
            )

        completion.instructor_sign(notes)

        logger.info(
            f"Instructor sign-off for lesson completion {completion_id}"
        )
        return completion

    @staticmethod
    def student_signoff(
        completion_id: uuid.UUID,
        organization_id: uuid.UUID,
        student_id: uuid.UUID
    ) -> LessonCompletion:
        """
        Record student sign-off.

        Args:
            completion_id: Completion UUID
            organization_id: Organization UUID
            student_id: Student UUID

        Returns:
            Updated LessonCompletion
        """
        completion = LessonCompletion.objects.get(
            id=completion_id,
            organization_id=organization_id
        )

        # Verify student owns the enrollment
        if completion.enrollment.student_id != student_id:
            raise ValidationError("Student does not own this enrollment")

        completion.student_sign()

        logger.info(
            f"Student sign-off for lesson completion {completion_id}"
        )
        return completion

    # ==========================================================================
    # Exercise Grading
    # ==========================================================================

    @staticmethod
    def grade_exercise(
        completion_id: uuid.UUID,
        organization_id: uuid.UUID,
        exercise_id: uuid.UUID,
        grade: Decimal = None,
        competency_grade: str = None,
        demonstrations: int = None,
        successful_demonstrations: int = None,
        performance_notes: str = None,
        deviations: Dict[str, Any] = None,
        competency_scores: Dict[str, Any] = None
    ) -> ExerciseGrade:
        """
        Grade an exercise within a lesson.

        Args:
            completion_id: Completion UUID
            organization_id: Organization UUID
            exercise_id: Exercise UUID
            grade: Numeric grade
            competency_grade: Competency grade (1-4)
            demonstrations: Number of demonstrations
            successful_demonstrations: Successful demonstrations
            performance_notes: Notes on performance
            deviations: Deviation measurements
            competency_scores: Competency element scores

        Returns:
            Created or updated ExerciseGrade
        """
        completion = LessonCompletion.objects.get(
            id=completion_id,
            organization_id=organization_id
        )

        exercise = Exercise.objects.get(
            id=exercise_id,
            organization_id=organization_id,
            lesson=completion.lesson
        )

        # Get or create grade
        exercise_grade, created = ExerciseGrade.objects.get_or_create(
            completion=completion,
            exercise=exercise,
            defaults={
                'organization_id': organization_id,
            }
        )

        # Update fields
        if grade is not None:
            exercise_grade.grade = grade
        if competency_grade is not None:
            exercise_grade.competency_grade = competency_grade
        if demonstrations is not None:
            exercise_grade.demonstrations = demonstrations
        if successful_demonstrations is not None:
            exercise_grade.successful_demonstrations = successful_demonstrations
        if performance_notes is not None:
            exercise_grade.performance_notes = performance_notes
        if deviations is not None:
            exercise_grade.deviations = deviations
        if competency_scores is not None:
            exercise_grade.competency_scores = competency_scores

        # Evaluate pass/fail
        exercise_grade.evaluate_pass()

        logger.info(
            f"Graded exercise {exercise.code} in completion {completion_id}"
        )
        return exercise_grade

    @staticmethod
    def bulk_grade_exercises(
        completion_id: uuid.UUID,
        organization_id: uuid.UUID,
        grades: List[Dict[str, Any]]
    ) -> List[ExerciseGrade]:
        """
        Grade multiple exercises at once.

        Args:
            completion_id: Completion UUID
            organization_id: Organization UUID
            grades: List of grade dictionaries with exercise_id and grade info

        Returns:
            List of created/updated ExerciseGrades
        """
        results = []

        with transaction.atomic():
            for grade_data in grades:
                exercise_id = grade_data.pop('exercise_id')
                exercise_grade = CompletionService.grade_exercise(
                    completion_id=completion_id,
                    organization_id=organization_id,
                    exercise_id=exercise_id,
                    **grade_data
                )
                results.append(exercise_grade)

        return results

    @staticmethod
    def get_exercise_grades(
        completion_id: uuid.UUID,
        organization_id: uuid.UUID
    ) -> List[ExerciseGrade]:
        """
        Get all exercise grades for a completion.

        Args:
            completion_id: Completion UUID
            organization_id: Organization UUID

        Returns:
            List of ExerciseGrades
        """
        return list(ExerciseGrade.objects.filter(
            completion_id=completion_id,
            organization_id=organization_id
        ).select_related('exercise').order_by('exercise__sort_order'))

    # ==========================================================================
    # Statistics and Reports
    # ==========================================================================

    @staticmethod
    def get_completion_statistics(
        organization_id: uuid.UUID,
        enrollment_id: uuid.UUID = None,
        lesson_id: uuid.UUID = None,
        instructor_id: uuid.UUID = None,
        date_from: date = None,
        date_to: date = None
    ) -> Dict[str, Any]:
        """
        Get completion statistics.

        Args:
            organization_id: Organization UUID
            enrollment_id: Filter by enrollment
            lesson_id: Filter by lesson
            instructor_id: Filter by instructor
            date_from: Start date
            date_to: End date

        Returns:
            Statistics dictionary
        """
        queryset = LessonCompletion.objects.filter(
            organization_id=organization_id
        )

        if enrollment_id:
            queryset = queryset.filter(enrollment_id=enrollment_id)
        if lesson_id:
            queryset = queryset.filter(lesson_id=lesson_id)
        if instructor_id:
            queryset = queryset.filter(instructor_id=instructor_id)
        if date_from:
            queryset = queryset.filter(actual_date__gte=date_from)
        if date_to:
            queryset = queryset.filter(actual_date__lte=date_to)

        stats = queryset.aggregate(
            total=Count('id'),
            completed=Count('id', filter=Q(is_completed=True)),
            cancelled=Count('id', filter=Q(status='cancelled')),
            no_show=Count('id', filter=Q(status='no_show')),
            passed=Count('id', filter=Q(result__in=['pass', 'satisfactory'])),
            failed=Count('id', filter=Q(result__in=['fail', 'unsatisfactory'])),
            avg_grade=Avg('grade', filter=Q(grade__isnull=False)),
            total_flight_hours=Sum('flight_time'),
            total_ground_hours=Sum('ground_time'),
            total_simulator_hours=Sum('simulator_time'),
        )

        # Calculate pass rate
        completed = stats['completed'] or 0
        passed = stats['passed'] or 0
        pass_rate = (passed / completed * 100) if completed > 0 else 0

        return {
            'total_records': stats['total'] or 0,
            'completed': completed,
            'cancelled': stats['cancelled'] or 0,
            'no_show': stats['no_show'] or 0,
            'results': {
                'passed': passed,
                'failed': stats['failed'] or 0,
                'pass_rate': round(pass_rate, 2),
            },
            'average_grade': round(float(stats['avg_grade'] or 0), 2),
            'hours': {
                'flight': float(stats['total_flight_hours'] or 0),
                'ground': float(stats['total_ground_hours'] or 0),
                'simulator': float(stats['total_simulator_hours'] or 0),
            }
        }

    @staticmethod
    def get_lesson_history(
        organization_id: uuid.UUID,
        enrollment_id: uuid.UUID,
        lesson_id: uuid.UUID
    ) -> List[Dict[str, Any]]:
        """
        Get completion history for a specific lesson.

        Args:
            organization_id: Organization UUID
            enrollment_id: Enrollment UUID
            lesson_id: Lesson UUID

        Returns:
            List of completion records
        """
        completions = LessonCompletion.objects.filter(
            organization_id=organization_id,
            enrollment_id=enrollment_id,
            lesson_id=lesson_id
        ).order_by('attempt_number')

        return [c.to_dict() for c in completions]

    @staticmethod
    def get_instructor_performance(
        organization_id: uuid.UUID,
        instructor_id: uuid.UUID,
        date_from: date = None,
        date_to: date = None
    ) -> Dict[str, Any]:
        """
        Get instructor teaching performance statistics.

        Args:
            organization_id: Organization UUID
            instructor_id: Instructor UUID
            date_from: Start date
            date_to: End date

        Returns:
            Performance statistics
        """
        queryset = LessonCompletion.objects.filter(
            organization_id=organization_id,
            instructor_id=instructor_id
        )

        if date_from:
            queryset = queryset.filter(actual_date__gte=date_from)
        if date_to:
            queryset = queryset.filter(actual_date__lte=date_to)

        stats = queryset.aggregate(
            total_lessons=Count('id'),
            completed=Count('id', filter=Q(is_completed=True)),
            student_pass_rate=Avg(
                'grade',
                filter=Q(grade__isnull=False)
            ),
            total_flight_hours=Sum('flight_time'),
            total_ground_hours=Sum('ground_time'),
            unique_students=Count('enrollment__student_id', distinct=True),
        )

        # Lesson type breakdown
        by_type = queryset.filter(is_completed=True).values(
            'lesson__lesson_type'
        ).annotate(count=Count('id'))

        return {
            'instructor_id': str(instructor_id),
            'total_lessons_taught': stats['total_lessons'] or 0,
            'completed_lessons': stats['completed'] or 0,
            'average_student_grade': round(
                float(stats['student_pass_rate'] or 0), 2
            ),
            'hours': {
                'flight': float(stats['total_flight_hours'] or 0),
                'ground': float(stats['total_ground_hours'] or 0),
            },
            'unique_students': stats['unique_students'] or 0,
            'lessons_by_type': {
                item['lesson__lesson_type']: item['count']
                for item in by_type
            }
        }
