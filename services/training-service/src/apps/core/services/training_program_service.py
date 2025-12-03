# services/training-service/src/apps/core/services/training_program_service.py
"""
Training Program Service

Business logic for training program management.
"""

import uuid
import logging
from decimal import Decimal
from typing import List, Dict, Any, Optional, Tuple
from datetime import date

from django.db import transaction
from django.db.models import Q, Count, Avg, Sum
from django.core.exceptions import ValidationError

from ..models import TrainingProgram, ProgramStage, SyllabusLesson

logger = logging.getLogger(__name__)


class TrainingProgramService:
    """
    Service class for training program operations.

    Handles program creation, management, and syllabus organization.
    """

    # ==========================================================================
    # Program CRUD Operations
    # ==========================================================================

    @staticmethod
    def create_program(
        organization_id: uuid.UUID,
        code: str,
        name: str,
        program_type: str,
        created_by: uuid.UUID = None,
        **kwargs
    ) -> TrainingProgram:
        """
        Create a new training program.

        Args:
            organization_id: Organization UUID
            code: Unique program code
            name: Program name
            program_type: Type of program (PPL, CPL, IR, etc.)
            created_by: User creating the program
            **kwargs: Additional program fields

        Returns:
            Created TrainingProgram instance

        Raises:
            ValidationError: If code already exists for organization
        """
        # Check for duplicate code
        if TrainingProgram.objects.filter(
            organization_id=organization_id,
            code=code
        ).exists():
            raise ValidationError(
                f"Program with code '{code}' already exists"
            )

        # Validate program type
        valid_types = [choice[0] for choice in TrainingProgram.ProgramType.choices]
        if program_type not in valid_types:
            raise ValidationError(
                f"Invalid program type. Must be one of: {', '.join(valid_types)}"
            )

        with transaction.atomic():
            program = TrainingProgram.objects.create(
                organization_id=organization_id,
                code=code,
                name=name,
                program_type=program_type,
                created_by=created_by,
                **kwargs
            )

            logger.info(
                f"Created training program: {program.code} "
                f"(org: {organization_id})"
            )

            return program

    @staticmethod
    def update_program(
        program_id: uuid.UUID,
        organization_id: uuid.UUID,
        **kwargs
    ) -> TrainingProgram:
        """
        Update a training program.

        Args:
            program_id: Program UUID
            organization_id: Organization UUID
            **kwargs: Fields to update

        Returns:
            Updated TrainingProgram instance
        """
        program = TrainingProgram.objects.get(
            id=program_id,
            organization_id=organization_id
        )

        # Check code uniqueness if being changed
        new_code = kwargs.get('code')
        if new_code and new_code != program.code:
            if TrainingProgram.objects.filter(
                organization_id=organization_id,
                code=new_code
            ).exclude(id=program_id).exists():
                raise ValidationError(
                    f"Program with code '{new_code}' already exists"
                )

        # Update fields
        for key, value in kwargs.items():
            if hasattr(program, key):
                setattr(program, key, value)

        program.save()

        logger.info(f"Updated training program: {program.code}")
        return program

    @staticmethod
    def get_program(
        program_id: uuid.UUID,
        organization_id: uuid.UUID
    ) -> TrainingProgram:
        """
        Get a training program by ID.

        Args:
            program_id: Program UUID
            organization_id: Organization UUID

        Returns:
            TrainingProgram instance
        """
        return TrainingProgram.objects.get(
            id=program_id,
            organization_id=organization_id
        )

    @staticmethod
    def list_programs(
        organization_id: uuid.UUID,
        status: str = None,
        program_type: str = None,
        is_published: bool = None,
        search: str = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[TrainingProgram], int]:
        """
        List training programs with filters.

        Args:
            organization_id: Organization UUID
            status: Filter by status
            program_type: Filter by program type
            is_published: Filter by published state
            search: Search in code and name
            page: Page number
            page_size: Items per page

        Returns:
            Tuple of (programs list, total count)
        """
        queryset = TrainingProgram.objects.filter(
            organization_id=organization_id
        )

        # Apply filters
        if status:
            queryset = queryset.filter(status=status)
        if program_type:
            queryset = queryset.filter(program_type=program_type)
        if is_published is not None:
            queryset = queryset.filter(is_published=is_published)
        if search:
            queryset = queryset.filter(
                Q(code__icontains=search) |
                Q(name__icontains=search)
            )

        total = queryset.count()

        # Pagination
        offset = (page - 1) * page_size
        programs = list(queryset[offset:offset + page_size])

        return programs, total

    @staticmethod
    def delete_program(
        program_id: uuid.UUID,
        organization_id: uuid.UUID,
        force: bool = False
    ) -> bool:
        """
        Delete a training program.

        Args:
            program_id: Program UUID
            organization_id: Organization UUID
            force: Force delete even with enrollments

        Returns:
            True if deleted

        Raises:
            ValidationError: If program has active enrollments
        """
        program = TrainingProgram.objects.get(
            id=program_id,
            organization_id=organization_id
        )

        # Check for active enrollments
        active_count = program.enrollments.filter(
            status__in=['active', 'pending', 'on_hold']
        ).count()

        if active_count > 0 and not force:
            raise ValidationError(
                f"Cannot delete program with {active_count} active enrollments"
            )

        with transaction.atomic():
            # Archive instead of hard delete if has history
            if program.enrollments.exists():
                program.status = TrainingProgram.Status.ARCHIVED
                program.is_published = False
                program.save()
                logger.info(f"Archived training program: {program.code}")
            else:
                program.delete()
                logger.info(f"Deleted training program: {program.code}")

        return True

    # ==========================================================================
    # Publishing
    # ==========================================================================

    @staticmethod
    def publish_program(
        program_id: uuid.UUID,
        organization_id: uuid.UUID
    ) -> TrainingProgram:
        """
        Publish a training program.

        Args:
            program_id: Program UUID
            organization_id: Organization UUID

        Returns:
            Published TrainingProgram
        """
        program = TrainingProgram.objects.get(
            id=program_id,
            organization_id=organization_id
        )

        # Validate program is ready for publishing
        errors = TrainingProgramService.validate_for_publishing(program)
        if errors:
            raise ValidationError(errors)

        program.publish()
        logger.info(f"Published training program: {program.code}")

        return program

    @staticmethod
    def unpublish_program(
        program_id: uuid.UUID,
        organization_id: uuid.UUID
    ) -> TrainingProgram:
        """
        Unpublish a training program.

        Args:
            program_id: Program UUID
            organization_id: Organization UUID

        Returns:
            Unpublished TrainingProgram
        """
        program = TrainingProgram.objects.get(
            id=program_id,
            organization_id=organization_id
        )

        program.is_published = False
        program.save()

        logger.info(f"Unpublished training program: {program.code}")
        return program

    @staticmethod
    def validate_for_publishing(program: TrainingProgram) -> List[str]:
        """
        Validate program is ready for publishing.

        Args:
            program: TrainingProgram instance

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        # Must have at least one lesson
        if program.lessons.filter(status='active').count() == 0:
            errors.append("Program must have at least one active lesson")

        # Must have stages if lessons reference stages
        lessons_with_stages = program.lessons.filter(
            stage_id__isnull=False
        ).exists()
        if lessons_with_stages and not program.stages:
            errors.append("Program has lessons with stages but no stages defined")

        # Validate minimum hours if set
        if program.min_hours_total:
            total_planned = program.total_flight_hours
            if total_planned < program.min_hours_total:
                errors.append(
                    f"Planned flight hours ({total_planned}) less than "
                    f"minimum required ({program.min_hours_total})"
                )

        return errors

    # ==========================================================================
    # Stage Management
    # ==========================================================================

    @staticmethod
    def add_stage(
        program_id: uuid.UUID,
        organization_id: uuid.UUID,
        name: str,
        description: str = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Add a stage to a training program.

        Args:
            program_id: Program UUID
            organization_id: Organization UUID
            name: Stage name
            description: Stage description
            **kwargs: Additional stage fields

        Returns:
            Created stage dictionary
        """
        program = TrainingProgram.objects.get(
            id=program_id,
            organization_id=organization_id
        )

        stage = program.add_stage(name, description)

        # Update with additional fields
        if kwargs:
            for key, value in kwargs.items():
                stage[key] = value

            # Save updated stages
            stages = program.stages
            for i, s in enumerate(stages):
                if s['id'] == stage['id']:
                    stages[i] = stage
                    break
            program.stages = stages
            program.save()

        logger.info(f"Added stage '{name}' to program {program.code}")
        return stage

    @staticmethod
    def update_stage(
        program_id: uuid.UUID,
        organization_id: uuid.UUID,
        stage_id: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Update a stage in a training program.

        Args:
            program_id: Program UUID
            organization_id: Organization UUID
            stage_id: Stage ID within the program
            **kwargs: Fields to update

        Returns:
            Updated stage dictionary
        """
        program = TrainingProgram.objects.get(
            id=program_id,
            organization_id=organization_id
        )

        stage = program.get_stage(stage_id)
        if not stage:
            raise ValidationError(f"Stage {stage_id} not found")

        # Update stage
        for key, value in kwargs.items():
            stage[key] = value

        # Save updated stages
        stages = program.stages
        for i, s in enumerate(stages):
            if s['id'] == stage_id:
                stages[i] = stage
                break

        program.stages = stages
        program.save()

        logger.info(f"Updated stage {stage_id} in program {program.code}")
        return stage

    @staticmethod
    def remove_stage(
        program_id: uuid.UUID,
        organization_id: uuid.UUID,
        stage_id: str
    ) -> bool:
        """
        Remove a stage from a training program.

        Args:
            program_id: Program UUID
            organization_id: Organization UUID
            stage_id: Stage ID to remove

        Returns:
            True if removed
        """
        program = TrainingProgram.objects.get(
            id=program_id,
            organization_id=organization_id
        )

        # Check if any lessons use this stage
        lesson_count = program.lessons.filter(stage_id=stage_id).count()
        if lesson_count > 0:
            raise ValidationError(
                f"Cannot remove stage with {lesson_count} lessons"
            )

        # Remove stage
        program.stages = [
            s for s in program.stages
            if s.get('id') != stage_id
        ]
        program.save()

        logger.info(f"Removed stage {stage_id} from program {program.code}")
        return True

    @staticmethod
    def reorder_stages(
        program_id: uuid.UUID,
        organization_id: uuid.UUID,
        stage_order: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Reorder stages in a training program.

        Args:
            program_id: Program UUID
            organization_id: Organization UUID
            stage_order: List of stage IDs in new order

        Returns:
            Reordered stages list
        """
        program = TrainingProgram.objects.get(
            id=program_id,
            organization_id=organization_id
        )

        # Create order map
        order_map = {stage_id: i + 1 for i, stage_id in enumerate(stage_order)}

        # Reorder stages
        for stage in program.stages:
            if stage['id'] in order_map:
                stage['order'] = order_map[stage['id']]

        # Sort by new order
        program.stages = sorted(
            program.stages,
            key=lambda x: x.get('order', 999)
        )
        program.save()

        logger.info(f"Reordered stages in program {program.code}")
        return program.stages

    # ==========================================================================
    # Program Statistics
    # ==========================================================================

    @staticmethod
    def get_program_statistics(
        program_id: uuid.UUID,
        organization_id: uuid.UUID
    ) -> Dict[str, Any]:
        """
        Get statistics for a training program.

        Args:
            program_id: Program UUID
            organization_id: Organization UUID

        Returns:
            Statistics dictionary
        """
        program = TrainingProgram.objects.get(
            id=program_id,
            organization_id=organization_id
        )

        # Enrollment stats
        enrollments = program.enrollments.all()
        enrollment_stats = enrollments.aggregate(
            total=Count('id'),
            active=Count('id', filter=Q(status='active')),
            completed=Count('id', filter=Q(status='completed')),
            withdrawn=Count('id', filter=Q(status='withdrawn')),
            avg_completion=Avg(
                'completion_percentage',
                filter=Q(status__in=['active', 'completed'])
            ),
            avg_grade=Avg('average_grade', filter=Q(average_grade__isnull=False)),
        )

        # Lesson stats
        lessons = program.lessons.filter(status='active')
        lesson_stats = lessons.aggregate(
            total=Count('id'),
            flight=Count('id', filter=Q(lesson_type='flight')),
            ground=Count('id', filter=Q(lesson_type='ground')),
            simulator=Count('id', filter=Q(lesson_type='simulator')),
            total_flight_hours=Sum('flight_hours'),
            total_ground_hours=Sum('ground_hours'),
        )

        # Completion rate by stage
        stage_stats = []
        for stage in (program.stages or []):
            stage_id = stage.get('id')
            stage_lessons = lessons.filter(stage_id=stage_id)

            stage_stats.append({
                'stage_id': stage_id,
                'stage_name': stage.get('name'),
                'lesson_count': stage_lessons.count(),
            })

        return {
            'program_id': str(program.id),
            'program_code': program.code,
            'enrollments': {
                'total': enrollment_stats['total'] or 0,
                'active': enrollment_stats['active'] or 0,
                'completed': enrollment_stats['completed'] or 0,
                'withdrawn': enrollment_stats['withdrawn'] or 0,
                'average_completion': float(
                    enrollment_stats['avg_completion'] or 0
                ),
                'average_grade': float(
                    enrollment_stats['avg_grade'] or 0
                ) if enrollment_stats['avg_grade'] else None,
            },
            'lessons': {
                'total': lesson_stats['total'] or 0,
                'by_type': {
                    'flight': lesson_stats['flight'] or 0,
                    'ground': lesson_stats['ground'] or 0,
                    'simulator': lesson_stats['simulator'] or 0,
                },
                'planned_hours': {
                    'flight': float(lesson_stats['total_flight_hours'] or 0),
                    'ground': float(lesson_stats['total_ground_hours'] or 0),
                }
            },
            'stages': stage_stats,
            'requirements': program.get_requirements_summary(),
        }

    # ==========================================================================
    # Clone / Template
    # ==========================================================================

    @staticmethod
    def clone_program(
        source_program_id: uuid.UUID,
        organization_id: uuid.UUID,
        new_code: str,
        new_name: str,
        include_lessons: bool = True
    ) -> TrainingProgram:
        """
        Clone a training program.

        Args:
            source_program_id: Source program UUID
            organization_id: Organization UUID
            new_code: Code for the new program
            new_name: Name for the new program
            include_lessons: Whether to clone lessons

        Returns:
            New TrainingProgram instance
        """
        source = TrainingProgram.objects.get(
            id=source_program_id,
            organization_id=organization_id
        )

        with transaction.atomic():
            # Create new program
            new_program = TrainingProgram.objects.create(
                organization_id=organization_id,
                code=new_code,
                name=new_name,
                program_type=source.program_type,
                description=source.description,
                regulatory_authority=source.regulatory_authority,
                min_hours_total=source.min_hours_total,
                min_hours_dual=source.min_hours_dual,
                min_hours_solo=source.min_hours_solo,
                min_hours_pic=source.min_hours_pic,
                min_hours_cross_country=source.min_hours_cross_country,
                min_hours_night=source.min_hours_night,
                min_hours_instrument=source.min_hours_instrument,
                min_hours_simulator=source.min_hours_simulator,
                min_hours_ground=source.min_hours_ground,
                prerequisites=source.prerequisites,
                min_age=source.min_age,
                required_medical_class=source.required_medical_class,
                estimated_duration_days=source.estimated_duration_days,
                max_duration_months=source.max_duration_months,
                base_price=source.base_price,
                currency=source.currency,
                stages=source.stages,
                status=TrainingProgram.Status.DRAFT,
                is_published=False,
            )

            # Clone lessons if requested
            if include_lessons:
                # Create mapping from old to new stage IDs
                stage_map = {}
                if source.stages:
                    new_stages = []
                    for stage in source.stages:
                        new_stage_id = str(uuid.uuid4())
                        stage_map[stage['id']] = new_stage_id
                        new_stage = stage.copy()
                        new_stage['id'] = new_stage_id
                        new_stages.append(new_stage)
                    new_program.stages = new_stages
                    new_program.save()

                # Clone lessons
                for lesson in source.lessons.all():
                    new_stage_id = None
                    if lesson.stage_id:
                        new_stage_id = stage_map.get(str(lesson.stage_id))

                    SyllabusLesson.objects.create(
                        organization_id=organization_id,
                        program=new_program,
                        stage_id=new_stage_id,
                        code=lesson.code,
                        name=lesson.name,
                        description=lesson.description,
                        objective=lesson.objective,
                        lesson_type=lesson.lesson_type,
                        sort_order=lesson.sort_order,
                        duration_hours=lesson.duration_hours,
                        ground_hours=lesson.ground_hours,
                        flight_hours=lesson.flight_hours,
                        simulator_hours=lesson.simulator_hours,
                        briefing_hours=lesson.briefing_hours,
                        required_conditions=lesson.required_conditions,
                        required_equipment=lesson.required_equipment,
                        prerequisite_hours=lesson.prerequisite_hours,
                        content=lesson.content,
                        completion_standards=lesson.completion_standards,
                        grading_criteria=lesson.grading_criteria,
                        min_grade_to_pass=lesson.min_grade_to_pass,
                        requires_instructor_signoff=lesson.requires_instructor_signoff,
                        status=SyllabusLesson.Status.DRAFT,
                    )

            logger.info(
                f"Cloned program {source.code} to {new_program.code}"
            )

            return new_program

    # ==========================================================================
    # Export / Import
    # ==========================================================================

    @staticmethod
    def export_program(
        program_id: uuid.UUID,
        organization_id: uuid.UUID
    ) -> Dict[str, Any]:
        """
        Export a training program to dictionary format.

        Args:
            program_id: Program UUID
            organization_id: Organization UUID

        Returns:
            Program data dictionary
        """
        program = TrainingProgram.objects.select_related().get(
            id=program_id,
            organization_id=organization_id
        )

        lessons_data = []
        for lesson in program.lessons.all():
            lesson_dict = lesson.to_dict()

            # Include exercises
            exercises = [ex.to_dict() for ex in lesson.exercises.all()]
            lesson_dict['exercises'] = exercises

            lessons_data.append(lesson_dict)

        return {
            'version': '1.0',
            'program': {
                'code': program.code,
                'name': program.name,
                'description': program.description,
                'program_type': program.program_type,
                'regulatory_authority': program.regulatory_authority,
                'requirements': program.get_requirements_summary(),
                'stages': program.stages,
            },
            'lessons': lessons_data,
            'metadata': program.metadata,
        }
