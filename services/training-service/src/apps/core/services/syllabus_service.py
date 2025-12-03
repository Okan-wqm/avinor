# services/training-service/src/apps/core/services/syllabus_service.py
"""
Syllabus Service

Business logic for syllabus and lesson management.
"""

import uuid
import logging
from decimal import Decimal
from typing import List, Dict, Any, Optional, Tuple

from django.db import transaction
from django.db.models import Q, Count, Sum, Max
from django.core.exceptions import ValidationError

from ..models import SyllabusLesson, Exercise, TrainingProgram

logger = logging.getLogger(__name__)


class SyllabusService:
    """
    Service class for syllabus operations.

    Handles lessons, exercises, and curriculum structure.
    """

    # ==========================================================================
    # Lesson CRUD
    # ==========================================================================

    @staticmethod
    def create_lesson(
        organization_id: uuid.UUID,
        program_id: uuid.UUID,
        code: str,
        name: str,
        lesson_type: str,
        stage_id: uuid.UUID = None,
        **kwargs
    ) -> SyllabusLesson:
        """
        Create a new syllabus lesson.

        Args:
            organization_id: Organization UUID
            program_id: Training program UUID
            code: Lesson code
            name: Lesson name
            lesson_type: Type of lesson
            stage_id: Optional stage UUID
            **kwargs: Additional lesson fields

        Returns:
            Created SyllabusLesson instance
        """
        program = TrainingProgram.objects.get(
            id=program_id,
            organization_id=organization_id
        )

        # Check for duplicate code in program
        if SyllabusLesson.objects.filter(
            program=program,
            code=code
        ).exists():
            raise ValidationError(
                f"Lesson with code '{code}' already exists in this program"
            )

        # Get next sort order
        max_order = SyllabusLesson.objects.filter(
            program=program,
            stage_id=stage_id
        ).aggregate(max=Max('sort_order'))['max'] or 0

        with transaction.atomic():
            lesson = SyllabusLesson.objects.create(
                organization_id=organization_id,
                program=program,
                code=code,
                name=name,
                lesson_type=lesson_type,
                stage_id=stage_id,
                sort_order=max_order + 1,
                **kwargs
            )

            logger.info(
                f"Created lesson {lesson.code} in program {program.code}"
            )

            return lesson

    @staticmethod
    def update_lesson(
        lesson_id: uuid.UUID,
        organization_id: uuid.UUID,
        **kwargs
    ) -> SyllabusLesson:
        """
        Update a syllabus lesson.

        Args:
            lesson_id: Lesson UUID
            organization_id: Organization UUID
            **kwargs: Fields to update

        Returns:
            Updated SyllabusLesson instance
        """
        lesson = SyllabusLesson.objects.get(
            id=lesson_id,
            organization_id=organization_id
        )

        # Check code uniqueness if being changed
        new_code = kwargs.get('code')
        if new_code and new_code != lesson.code:
            if SyllabusLesson.objects.filter(
                program=lesson.program,
                code=new_code
            ).exclude(id=lesson_id).exists():
                raise ValidationError(
                    f"Lesson with code '{new_code}' already exists"
                )

        # Update fields
        for key, value in kwargs.items():
            if hasattr(lesson, key):
                setattr(lesson, key, value)

        lesson.save()

        logger.info(f"Updated lesson {lesson.code}")
        return lesson

    @staticmethod
    def get_lesson(
        lesson_id: uuid.UUID,
        organization_id: uuid.UUID
    ) -> SyllabusLesson:
        """
        Get a lesson by ID.

        Args:
            lesson_id: Lesson UUID
            organization_id: Organization UUID

        Returns:
            SyllabusLesson instance
        """
        return SyllabusLesson.objects.select_related('program').get(
            id=lesson_id,
            organization_id=organization_id
        )

    @staticmethod
    def list_lessons(
        organization_id: uuid.UUID,
        program_id: uuid.UUID = None,
        stage_id: uuid.UUID = None,
        lesson_type: str = None,
        status: str = None,
        search: str = None,
        page: int = 1,
        page_size: int = 50
    ) -> Tuple[List[SyllabusLesson], int]:
        """
        List lessons with filters.

        Args:
            organization_id: Organization UUID
            program_id: Filter by program
            stage_id: Filter by stage
            lesson_type: Filter by lesson type
            status: Filter by status
            search: Search in code and name
            page: Page number
            page_size: Items per page

        Returns:
            Tuple of (lessons list, total count)
        """
        queryset = SyllabusLesson.objects.filter(
            organization_id=organization_id
        ).select_related('program')

        # Apply filters
        if program_id:
            queryset = queryset.filter(program_id=program_id)
        if stage_id:
            queryset = queryset.filter(stage_id=stage_id)
        if lesson_type:
            queryset = queryset.filter(lesson_type=lesson_type)
        if status:
            queryset = queryset.filter(status=status)
        if search:
            queryset = queryset.filter(
                Q(code__icontains=search) |
                Q(name__icontains=search)
            )

        total = queryset.count()

        # Pagination
        offset = (page - 1) * page_size
        lessons = list(queryset[offset:offset + page_size])

        return lessons, total

    @staticmethod
    def delete_lesson(
        lesson_id: uuid.UUID,
        organization_id: uuid.UUID,
        force: bool = False
    ) -> bool:
        """
        Delete a syllabus lesson.

        Args:
            lesson_id: Lesson UUID
            organization_id: Organization UUID
            force: Force delete even with completions

        Returns:
            True if deleted
        """
        lesson = SyllabusLesson.objects.get(
            id=lesson_id,
            organization_id=organization_id
        )

        # Check for completions
        completion_count = lesson.completions.count()
        if completion_count > 0 and not force:
            raise ValidationError(
                f"Cannot delete lesson with {completion_count} completions"
            )

        with transaction.atomic():
            # Archive if has history
            if completion_count > 0:
                lesson.status = SyllabusLesson.Status.ARCHIVED
                lesson.save()
                logger.info(f"Archived lesson {lesson.code}")
            else:
                lesson.delete()
                logger.info(f"Deleted lesson {lesson.code}")

        return True

    # ==========================================================================
    # Lesson Ordering
    # ==========================================================================

    @staticmethod
    def reorder_lessons(
        organization_id: uuid.UUID,
        program_id: uuid.UUID,
        lesson_order: List[str],
        stage_id: uuid.UUID = None
    ) -> List[SyllabusLesson]:
        """
        Reorder lessons in a program/stage.

        Args:
            organization_id: Organization UUID
            program_id: Program UUID
            lesson_order: List of lesson IDs in new order
            stage_id: Optional stage UUID

        Returns:
            Reordered lessons list
        """
        with transaction.atomic():
            for i, lesson_id in enumerate(lesson_order):
                SyllabusLesson.objects.filter(
                    id=lesson_id,
                    organization_id=organization_id,
                    program_id=program_id
                ).update(sort_order=i + 1)

        lessons = SyllabusLesson.objects.filter(
            organization_id=organization_id,
            program_id=program_id
        )

        if stage_id:
            lessons = lessons.filter(stage_id=stage_id)

        return list(lessons.order_by('sort_order'))

    @staticmethod
    def move_lesson_to_stage(
        lesson_id: uuid.UUID,
        organization_id: uuid.UUID,
        new_stage_id: uuid.UUID
    ) -> SyllabusLesson:
        """
        Move lesson to a different stage.

        Args:
            lesson_id: Lesson UUID
            organization_id: Organization UUID
            new_stage_id: Target stage UUID

        Returns:
            Updated SyllabusLesson
        """
        lesson = SyllabusLesson.objects.get(
            id=lesson_id,
            organization_id=organization_id
        )

        # Verify stage exists in program
        if new_stage_id:
            stage = lesson.program.get_stage(str(new_stage_id))
            if not stage:
                raise ValidationError(f"Stage {new_stage_id} not found")

        # Get max order in new stage
        max_order = SyllabusLesson.objects.filter(
            program=lesson.program,
            stage_id=new_stage_id
        ).aggregate(max=Max('sort_order'))['max'] or 0

        lesson.stage_id = new_stage_id
        lesson.sort_order = max_order + 1
        lesson.save()

        logger.info(f"Moved lesson {lesson.code} to stage {new_stage_id}")
        return lesson

    # ==========================================================================
    # Prerequisites
    # ==========================================================================

    @staticmethod
    def add_prerequisite(
        lesson_id: uuid.UUID,
        organization_id: uuid.UUID,
        prerequisite_lesson_id: uuid.UUID
    ) -> SyllabusLesson:
        """
        Add a prerequisite lesson.

        Args:
            lesson_id: Lesson UUID
            organization_id: Organization UUID
            prerequisite_lesson_id: Prerequisite lesson UUID

        Returns:
            Updated SyllabusLesson
        """
        lesson = SyllabusLesson.objects.get(
            id=lesson_id,
            organization_id=organization_id
        )

        # Verify prerequisite exists in same program
        prereq = SyllabusLesson.objects.get(
            id=prerequisite_lesson_id,
            program=lesson.program
        )

        # Check for circular dependency
        if SyllabusService._has_circular_dependency(
            lesson.id, prereq.id, lesson.program_id
        ):
            raise ValidationError("Adding this prerequisite would create a cycle")

        if prerequisite_lesson_id not in lesson.prerequisite_lessons:
            lesson.prerequisite_lessons.append(prerequisite_lesson_id)
            lesson.save()

        return lesson

    @staticmethod
    def remove_prerequisite(
        lesson_id: uuid.UUID,
        organization_id: uuid.UUID,
        prerequisite_lesson_id: uuid.UUID
    ) -> SyllabusLesson:
        """
        Remove a prerequisite lesson.

        Args:
            lesson_id: Lesson UUID
            organization_id: Organization UUID
            prerequisite_lesson_id: Prerequisite lesson UUID to remove

        Returns:
            Updated SyllabusLesson
        """
        lesson = SyllabusLesson.objects.get(
            id=lesson_id,
            organization_id=organization_id
        )

        if prerequisite_lesson_id in lesson.prerequisite_lessons:
            lesson.prerequisite_lessons.remove(prerequisite_lesson_id)
            lesson.save()

        return lesson

    @staticmethod
    def _has_circular_dependency(
        lesson_id: uuid.UUID,
        prereq_id: uuid.UUID,
        program_id: uuid.UUID,
        visited: set = None
    ) -> bool:
        """Check for circular prerequisite dependencies."""
        if visited is None:
            visited = set()

        if prereq_id in visited:
            return True

        if prereq_id == lesson_id:
            return True

        visited.add(prereq_id)

        try:
            prereq = SyllabusLesson.objects.get(id=prereq_id)
            for next_prereq in prereq.prerequisite_lessons:
                if SyllabusService._has_circular_dependency(
                    lesson_id, next_prereq, program_id, visited
                ):
                    return True
        except SyllabusLesson.DoesNotExist:
            pass

        return False

    @staticmethod
    def get_available_lessons(
        enrollment_id: uuid.UUID,
        organization_id: uuid.UUID
    ) -> List[SyllabusLesson]:
        """
        Get lessons available for a student based on prerequisites.

        Args:
            enrollment_id: Enrollment UUID
            organization_id: Organization UUID

        Returns:
            List of available lessons
        """
        from ..models import StudentEnrollment, LessonCompletion

        enrollment = StudentEnrollment.objects.get(
            id=enrollment_id,
            organization_id=organization_id
        )

        # Get completed lesson IDs
        completed_ids = set(
            str(c.lesson_id) for c in
            LessonCompletion.objects.filter(
                enrollment=enrollment,
                is_completed=True
            )
        )

        # Get all active lessons in program
        all_lessons = SyllabusLesson.objects.filter(
            program=enrollment.program,
            status='active'
        )

        available = []
        for lesson in all_lessons:
            if str(lesson.id) in completed_ids:
                continue  # Already completed

            # Check prerequisites
            prereq_check = lesson.check_prerequisites(
                list(completed_ids),
                enrollment.total_flight_hours
            )

            if prereq_check['met']:
                available.append(lesson)

        return available

    # ==========================================================================
    # Exercise CRUD
    # ==========================================================================

    @staticmethod
    def create_exercise(
        organization_id: uuid.UUID,
        lesson_id: uuid.UUID,
        code: str,
        name: str,
        **kwargs
    ) -> Exercise:
        """
        Create a new exercise.

        Args:
            organization_id: Organization UUID
            lesson_id: Lesson UUID
            code: Exercise code
            name: Exercise name
            **kwargs: Additional exercise fields

        Returns:
            Created Exercise instance
        """
        lesson = SyllabusLesson.objects.get(
            id=lesson_id,
            organization_id=organization_id
        )

        # Get next sort order
        max_order = Exercise.objects.filter(
            lesson=lesson
        ).aggregate(max=Max('sort_order'))['max'] or 0

        exercise = Exercise.objects.create(
            organization_id=organization_id,
            lesson=lesson,
            code=code,
            name=name,
            sort_order=max_order + 1,
            **kwargs
        )

        logger.info(f"Created exercise {exercise.code} in lesson {lesson.code}")
        return exercise

    @staticmethod
    def update_exercise(
        exercise_id: uuid.UUID,
        organization_id: uuid.UUID,
        **kwargs
    ) -> Exercise:
        """
        Update an exercise.

        Args:
            exercise_id: Exercise UUID
            organization_id: Organization UUID
            **kwargs: Fields to update

        Returns:
            Updated Exercise instance
        """
        exercise = Exercise.objects.get(
            id=exercise_id,
            organization_id=organization_id
        )

        for key, value in kwargs.items():
            if hasattr(exercise, key):
                setattr(exercise, key, value)

        exercise.save()

        logger.info(f"Updated exercise {exercise.code}")
        return exercise

    @staticmethod
    def delete_exercise(
        exercise_id: uuid.UUID,
        organization_id: uuid.UUID
    ) -> bool:
        """
        Delete an exercise.

        Args:
            exercise_id: Exercise UUID
            organization_id: Organization UUID

        Returns:
            True if deleted
        """
        exercise = Exercise.objects.get(
            id=exercise_id,
            organization_id=organization_id
        )

        # Check for grades
        if exercise.grades.exists():
            raise ValidationError(
                "Cannot delete exercise with existing grades"
            )

        exercise.delete()
        logger.info(f"Deleted exercise {exercise.code}")
        return True

    @staticmethod
    def list_exercises(
        organization_id: uuid.UUID,
        lesson_id: uuid.UUID
    ) -> List[Exercise]:
        """
        List exercises for a lesson.

        Args:
            organization_id: Organization UUID
            lesson_id: Lesson UUID

        Returns:
            List of exercises
        """
        return list(Exercise.objects.filter(
            organization_id=organization_id,
            lesson_id=lesson_id
        ).order_by('sort_order'))

    @staticmethod
    def reorder_exercises(
        organization_id: uuid.UUID,
        lesson_id: uuid.UUID,
        exercise_order: List[str]
    ) -> List[Exercise]:
        """
        Reorder exercises in a lesson.

        Args:
            organization_id: Organization UUID
            lesson_id: Lesson UUID
            exercise_order: List of exercise IDs in new order

        Returns:
            Reordered exercises list
        """
        with transaction.atomic():
            for i, exercise_id in enumerate(exercise_order):
                Exercise.objects.filter(
                    id=exercise_id,
                    organization_id=organization_id,
                    lesson_id=lesson_id
                ).update(sort_order=i + 1)

        return list(Exercise.objects.filter(
            organization_id=organization_id,
            lesson_id=lesson_id
        ).order_by('sort_order'))

    # ==========================================================================
    # Syllabus Structure
    # ==========================================================================

    @staticmethod
    def get_program_syllabus(
        program_id: uuid.UUID,
        organization_id: uuid.UUID
    ) -> Dict[str, Any]:
        """
        Get complete program syllabus structure.

        Args:
            program_id: Program UUID
            organization_id: Organization UUID

        Returns:
            Syllabus structure dictionary
        """
        program = TrainingProgram.objects.get(
            id=program_id,
            organization_id=organization_id
        )

        lessons = SyllabusLesson.objects.filter(
            program=program,
            status='active'
        ).prefetch_related('exercises').order_by('sort_order')

        # Group by stage
        stages_dict = {}
        no_stage_lessons = []

        for lesson in lessons:
            lesson_data = lesson.to_dict()
            lesson_data['exercises'] = [
                ex.to_dict() for ex in lesson.exercises.all()
            ]

            if lesson.stage_id:
                stage_key = str(lesson.stage_id)
                if stage_key not in stages_dict:
                    stage_info = program.get_stage(stage_key)
                    stages_dict[stage_key] = {
                        'id': stage_key,
                        'name': stage_info.get('name') if stage_info else 'Unknown',
                        'order': stage_info.get('order', 0) if stage_info else 0,
                        'lessons': []
                    }
                stages_dict[stage_key]['lessons'].append(lesson_data)
            else:
                no_stage_lessons.append(lesson_data)

        # Sort stages by order
        stages = sorted(stages_dict.values(), key=lambda x: x['order'])

        return {
            'program': {
                'id': str(program.id),
                'code': program.code,
                'name': program.name,
            },
            'stages': stages,
            'unassigned_lessons': no_stage_lessons,
            'statistics': {
                'total_lessons': lessons.count(),
                'total_exercises': sum(l.exercises.count() for l in lessons),
                'total_flight_hours': float(
                    lessons.aggregate(Sum('flight_hours'))['flight_hours__sum'] or 0
                ),
                'total_ground_hours': float(
                    lessons.aggregate(Sum('ground_hours'))['ground_hours__sum'] or 0
                ),
            }
        }

    @staticmethod
    def clone_lesson(
        lesson_id: uuid.UUID,
        organization_id: uuid.UUID,
        new_code: str,
        new_name: str = None,
        target_program_id: uuid.UUID = None,
        include_exercises: bool = True
    ) -> SyllabusLesson:
        """
        Clone a lesson.

        Args:
            lesson_id: Source lesson UUID
            organization_id: Organization UUID
            new_code: Code for new lesson
            new_name: Name for new lesson
            target_program_id: Target program (same if not specified)
            include_exercises: Whether to clone exercises

        Returns:
            New SyllabusLesson instance
        """
        source = SyllabusLesson.objects.get(
            id=lesson_id,
            organization_id=organization_id
        )

        target_program = (
            TrainingProgram.objects.get(id=target_program_id)
            if target_program_id
            else source.program
        )

        with transaction.atomic():
            # Get max sort order
            max_order = SyllabusLesson.objects.filter(
                program=target_program
            ).aggregate(max=Max('sort_order'))['max'] or 0

            new_lesson = SyllabusLesson.objects.create(
                organization_id=organization_id,
                program=target_program,
                code=new_code,
                name=new_name or f"{source.name} (Copy)",
                description=source.description,
                objective=source.objective,
                lesson_type=source.lesson_type,
                sort_order=max_order + 1,
                duration_hours=source.duration_hours,
                ground_hours=source.ground_hours,
                flight_hours=source.flight_hours,
                simulator_hours=source.simulator_hours,
                briefing_hours=source.briefing_hours,
                required_conditions=source.required_conditions,
                required_equipment=source.required_equipment,
                prerequisite_hours=source.prerequisite_hours,
                content=source.content,
                completion_standards=source.completion_standards,
                grading_criteria=source.grading_criteria,
                min_grade_to_pass=source.min_grade_to_pass,
                requires_instructor_signoff=source.requires_instructor_signoff,
                requires_student_signoff=source.requires_student_signoff,
                instructor_notes=source.instructor_notes,
                common_errors=source.common_errors,
                status=SyllabusLesson.Status.DRAFT,
            )

            # Clone exercises if requested
            if include_exercises:
                for exercise in source.exercises.all():
                    Exercise.objects.create(
                        organization_id=organization_id,
                        lesson=new_lesson,
                        code=exercise.code,
                        name=exercise.name,
                        description=exercise.description,
                        sort_order=exercise.sort_order,
                        grading_scale=exercise.grading_scale,
                        tolerances=exercise.tolerances,
                        standards=exercise.standards,
                        min_demonstrations=exercise.min_demonstrations,
                        min_grade=exercise.min_grade,
                        competency_elements=exercise.competency_elements,
                        is_required=exercise.is_required,
                        is_critical=exercise.is_critical,
                    )

            logger.info(f"Cloned lesson {source.code} to {new_lesson.code}")
            return new_lesson
