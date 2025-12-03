# services/theory-service/src/apps/core/services/course_service.py
"""
Course Service

Business logic for course management.
"""

import logging
from typing import Dict, Any, List, Optional
from uuid import UUID
from decimal import Decimal

from django.db import transaction
from django.db.models import Q, Avg, Count
from django.utils import timezone

from ..models import (
    Course,
    CourseModule,
    CourseAttachment,
    CourseStatus,
    ContentType,
)

logger = logging.getLogger(__name__)


class CourseService:
    """Service for managing theory courses."""

    @staticmethod
    def get_courses(
        organization_id: str,
        category: str = None,
        program_type: str = None,
        status: str = None,
        is_published: bool = None,
        search: str = None,
        tags: List[str] = None,
    ) -> List[Course]:
        """
        Get courses with optional filtering.

        Args:
            organization_id: Organization ID
            category: Filter by category
            program_type: Filter by program type
            status: Filter by status
            is_published: Filter by published state
            search: Search term
            tags: Filter by tags

        Returns:
            List of courses
        """
        queryset = Course.objects.filter(organization_id=organization_id)

        if category:
            queryset = queryset.filter(category=category)

        if program_type:
            queryset = queryset.filter(program_type=program_type)

        if status:
            queryset = queryset.filter(status=status)

        if is_published is not None:
            queryset = queryset.filter(is_published=is_published)

        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(code__icontains=search) |
                Q(description__icontains=search)
            )

        if tags:
            queryset = queryset.filter(tags__overlap=tags)

        return queryset.order_by('name')

    @staticmethod
    @transaction.atomic
    def create_course(
        organization_id: str,
        code: str,
        name: str,
        category: str,
        created_by: str = None,
        **kwargs
    ) -> Course:
        """
        Create a new course.

        Args:
            organization_id: Organization ID
            code: Course code
            name: Course name
            category: Course category
            created_by: User ID who created
            **kwargs: Additional course fields

        Returns:
            Created course
        """
        # Check for duplicate code
        if Course.objects.filter(
            organization_id=organization_id,
            code=code
        ).exists():
            raise ValueError(f"Course with code '{code}' already exists")

        course = Course.objects.create(
            organization_id=organization_id,
            code=code,
            name=name,
            category=category,
            created_by=created_by,
            **kwargs
        )

        logger.info(f"Created course: {course.id} - {course.code}")

        return course

    @staticmethod
    def get_course(course_id: str, organization_id: str = None) -> Course:
        """
        Get course by ID.

        Args:
            course_id: Course ID
            organization_id: Optional organization filter

        Returns:
            Course instance
        """
        filters = {'id': course_id}
        if organization_id:
            filters['organization_id'] = organization_id

        return Course.objects.get(**filters)

    @staticmethod
    @transaction.atomic
    def update_course(
        course_id: str,
        organization_id: str,
        **updates
    ) -> Course:
        """
        Update a course.

        Args:
            course_id: Course ID
            organization_id: Organization ID
            **updates: Fields to update

        Returns:
            Updated course
        """
        course = Course.objects.select_for_update().get(
            id=course_id,
            organization_id=organization_id
        )

        # Don't allow certain updates on published courses
        if course.is_published:
            restricted_fields = ['code', 'category']
            for field in restricted_fields:
                if field in updates:
                    raise ValueError(
                        f"Cannot change '{field}' on published course"
                    )

        for field, value in updates.items():
            if hasattr(course, field):
                setattr(course, field, value)

        course.save()

        logger.info(f"Updated course: {course.id}")

        return course

    @staticmethod
    @transaction.atomic
    def publish_course(
        course_id: str,
        organization_id: str
    ) -> Course:
        """
        Publish a course.

        Args:
            course_id: Course ID
            organization_id: Organization ID

        Returns:
            Published course
        """
        course = Course.objects.select_for_update().get(
            id=course_id,
            organization_id=organization_id
        )

        # Validation
        if course.modules.count() == 0:
            raise ValueError("Cannot publish course without modules")

        course.publish()

        logger.info(f"Published course: {course.id}")

        return course

    @staticmethod
    @transaction.atomic
    def archive_course(
        course_id: str,
        organization_id: str
    ) -> Course:
        """
        Archive a course.

        Args:
            course_id: Course ID
            organization_id: Organization ID

        Returns:
            Archived course
        """
        course = Course.objects.select_for_update().get(
            id=course_id,
            organization_id=organization_id
        )

        course.archive()

        logger.info(f"Archived course: {course.id}")

        return course

    @staticmethod
    @transaction.atomic
    def clone_course(
        course_id: str,
        organization_id: str,
        new_code: str,
        new_name: str = None
    ) -> Course:
        """
        Clone a course with all its modules.

        Args:
            course_id: Source course ID
            organization_id: Organization ID
            new_code: New course code
            new_name: Optional new name

        Returns:
            Cloned course
        """
        source = Course.objects.get(
            id=course_id,
            organization_id=organization_id
        )

        # Create new course
        new_course = Course.objects.create(
            organization_id=organization_id,
            code=new_code,
            name=new_name or f"{source.name} (Copy)",
            description=source.description,
            short_description=source.short_description,
            category=source.category,
            program_type=source.program_type,
            estimated_hours=source.estimated_hours,
            min_score_to_pass=source.min_score_to_pass,
            require_module_completion=source.require_module_completion,
            require_final_exam=source.require_final_exam,
            thumbnail_url=source.thumbnail_url,
            tags=source.tags.copy(),
            learning_objectives=source.learning_objectives.copy() if source.learning_objectives else [],
            settings=source.settings.copy() if source.settings else {},
            status=CourseStatus.DRAFT,
            is_published=False,
        )

        # Clone modules
        for module in source.modules.all():
            CourseModule.objects.create(
                course=new_course,
                name=module.name,
                description=module.description,
                sort_order=module.sort_order,
                content_type=module.content_type,
                content=module.content,
                content_html=module.content_html,
                video_url=module.video_url,
                video_duration_seconds=module.video_duration_seconds,
                estimated_minutes=module.estimated_minutes,
                has_quiz=module.has_quiz,
                quiz_id=module.quiz_id,
                completion_criteria=module.completion_criteria.copy() if module.completion_criteria else {},
                learning_objectives=module.learning_objectives.copy() if module.learning_objectives else [],
            )

        logger.info(f"Cloned course {source.id} to {new_course.id}")

        return new_course

    # =========================================================================
    # MODULE MANAGEMENT
    # =========================================================================

    @staticmethod
    def get_course_modules(
        course_id: str,
        organization_id: str = None
    ) -> List[CourseModule]:
        """
        Get all modules for a course.

        Args:
            course_id: Course ID
            organization_id: Optional organization filter

        Returns:
            List of modules
        """
        filters = {'course_id': course_id}
        if organization_id:
            filters['course__organization_id'] = organization_id

        return CourseModule.objects.filter(**filters).order_by('sort_order')

    @staticmethod
    @transaction.atomic
    def create_module(
        course_id: str,
        organization_id: str,
        name: str,
        **kwargs
    ) -> CourseModule:
        """
        Create a new module in a course.

        Args:
            course_id: Course ID
            organization_id: Organization ID
            name: Module name
            **kwargs: Additional module fields

        Returns:
            Created module
        """
        course = Course.objects.get(
            id=course_id,
            organization_id=organization_id
        )

        # Get next sort order
        max_order = CourseModule.objects.filter(
            course=course
        ).aggregate(max_order=models.Max('sort_order'))['max_order'] or 0

        module = CourseModule.objects.create(
            course=course,
            name=name,
            sort_order=max_order + 1,
            **kwargs
        )

        # Update course estimated hours if needed
        CourseService._update_course_duration(course)

        logger.info(f"Created module: {module.id} for course {course_id}")

        return module

    @staticmethod
    @transaction.atomic
    def update_module(
        module_id: str,
        organization_id: str,
        **updates
    ) -> CourseModule:
        """
        Update a module.

        Args:
            module_id: Module ID
            organization_id: Organization ID
            **updates: Fields to update

        Returns:
            Updated module
        """
        module = CourseModule.objects.select_for_update().get(
            id=module_id,
            course__organization_id=organization_id
        )

        for field, value in updates.items():
            if hasattr(module, field):
                setattr(module, field, value)

        module.save()

        # Update course estimated hours if duration changed
        if 'estimated_minutes' in updates or 'video_duration_seconds' in updates:
            CourseService._update_course_duration(module.course)

        logger.info(f"Updated module: {module.id}")

        return module

    @staticmethod
    @transaction.atomic
    def delete_module(
        module_id: str,
        organization_id: str
    ) -> None:
        """
        Delete a module.

        Args:
            module_id: Module ID
            organization_id: Organization ID
        """
        module = CourseModule.objects.get(
            id=module_id,
            course__organization_id=organization_id
        )
        course = module.course

        module.delete()

        # Reorder remaining modules
        for i, m in enumerate(course.modules.order_by('sort_order')):
            m.sort_order = i + 1
            m.save()

        # Update course duration
        CourseService._update_course_duration(course)

        logger.info(f"Deleted module: {module_id}")

    @staticmethod
    @transaction.atomic
    def reorder_modules(
        course_id: str,
        organization_id: str,
        module_order: List[str]
    ) -> List[CourseModule]:
        """
        Reorder modules in a course.

        Args:
            course_id: Course ID
            organization_id: Organization ID
            module_order: List of module IDs in desired order

        Returns:
            Reordered modules
        """
        course = Course.objects.get(
            id=course_id,
            organization_id=organization_id
        )

        modules = []
        for i, module_id in enumerate(module_order):
            module = CourseModule.objects.get(id=module_id, course=course)
            module.sort_order = i + 1
            module.save()
            modules.append(module)

        logger.info(f"Reordered modules for course: {course_id}")

        return modules

    # =========================================================================
    # ATTACHMENT MANAGEMENT
    # =========================================================================

    @staticmethod
    @transaction.atomic
    def add_attachment(
        course_id: str,
        organization_id: str,
        name: str,
        file_url: str,
        file_type: str,
        module_id: str = None,
        **kwargs
    ) -> CourseAttachment:
        """
        Add an attachment to a course or module.

        Args:
            course_id: Course ID
            organization_id: Organization ID
            name: Attachment name
            file_url: File URL
            file_type: File type
            module_id: Optional module ID
            **kwargs: Additional fields

        Returns:
            Created attachment
        """
        course = Course.objects.get(
            id=course_id,
            organization_id=organization_id
        )

        module = None
        if module_id:
            module = CourseModule.objects.get(id=module_id, course=course)

        attachment = CourseAttachment.objects.create(
            course=course,
            module=module,
            name=name,
            file_url=file_url,
            file_type=file_type,
            **kwargs
        )

        logger.info(f"Added attachment: {attachment.id}")

        return attachment

    @staticmethod
    def delete_attachment(
        attachment_id: str,
        organization_id: str
    ) -> None:
        """
        Delete an attachment.

        Args:
            attachment_id: Attachment ID
            organization_id: Organization ID
        """
        attachment = CourseAttachment.objects.get(
            id=attachment_id,
            course__organization_id=organization_id
        )
        attachment.delete()

        logger.info(f"Deleted attachment: {attachment_id}")

    # =========================================================================
    # STATISTICS
    # =========================================================================

    @staticmethod
    def get_course_statistics(
        course_id: str,
        organization_id: str
    ) -> Dict[str, Any]:
        """
        Get detailed course statistics.

        Args:
            course_id: Course ID
            organization_id: Organization ID

        Returns:
            Statistics dictionary
        """
        from ..models import CourseEnrollment, ExamAttempt

        course = Course.objects.get(
            id=course_id,
            organization_id=organization_id
        )

        enrollments = CourseEnrollment.objects.filter(course=course)

        # Enrollment stats
        total_enrolled = enrollments.count()
        in_progress = enrollments.filter(status='in_progress').count()
        completed = enrollments.filter(status='completed').count()

        # Time stats
        avg_time = enrollments.aggregate(
            avg_time=Avg('total_time_spent_seconds')
        )['avg_time']

        # Exam stats
        exam_ids = course.exams.values_list('id', flat=True)
        attempts = ExamAttempt.objects.filter(exam_id__in=exam_ids)

        total_attempts = attempts.filter(status='completed').count()
        passed_attempts = attempts.filter(passed=True).count()

        pass_rate = 0
        if total_attempts > 0:
            pass_rate = round((passed_attempts / total_attempts) * 100, 2)

        avg_score = attempts.filter(
            status='completed'
        ).aggregate(avg_score=Avg('score_percentage'))['avg_score']

        # Module stats
        module_stats = []
        for module in course.modules.all():
            from ..models import ModuleProgress
            progress = ModuleProgress.objects.filter(module=module)
            module_stats.append({
                'module_id': str(module.id),
                'name': module.name,
                'views': progress.aggregate(views=Count('id'))['views'],
                'completions': progress.filter(completed=True).count(),
                'avg_time_minutes': (progress.aggregate(
                    avg_time=Avg('time_spent_seconds')
                )['avg_time'] or 0) // 60
            })

        return {
            'course_id': str(course.id),
            'enrollment': {
                'total': total_enrolled,
                'in_progress': in_progress,
                'completed': completed,
                'completion_rate': course.completion_rate,
            },
            'time': {
                'average_hours': round((avg_time or 0) / 3600, 2),
                'estimated_hours': float(course.estimated_hours) if course.estimated_hours else None,
            },
            'exams': {
                'total_attempts': total_attempts,
                'pass_rate': pass_rate,
                'average_score': float(avg_score) if avg_score else None,
            },
            'modules': module_stats,
            'rating': {
                'average': float(course.rating) if course.rating else None,
                'count': course.rating_count,
            }
        }

    # =========================================================================
    # HELPERS
    # =========================================================================

    @staticmethod
    def _update_course_duration(course: Course) -> None:
        """Update course estimated hours from modules."""
        total_minutes = sum(
            m.estimated_minutes or 0
            for m in course.modules.all()
        )

        if total_minutes > 0:
            course.estimated_hours = Decimal(str(round(total_minutes / 60, 2)))
            course.save()
