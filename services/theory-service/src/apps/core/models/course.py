# services/theory-service/src/apps/core/models/course.py
"""
Course Models

Models for theory courses and course modules.
"""

import uuid
from decimal import Decimal
from typing import Dict, Any, List, Optional

from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.utils import timezone


class CourseCategory(models.TextChoices):
    """Course category choices."""
    AIR_LAW = 'air_law', 'Air Law'
    METEOROLOGY = 'meteorology', 'Meteorology'
    NAVIGATION = 'navigation', 'Navigation'
    HUMAN_PERFORMANCE = 'human_performance', 'Human Performance'
    FLIGHT_PLANNING = 'flight_planning', 'Flight Planning'
    AIRCRAFT_GENERAL = 'aircraft_general', 'Aircraft General Knowledge'
    PRINCIPLES_OF_FLIGHT = 'principles_of_flight', 'Principles of Flight'
    OPERATIONAL_PROCEDURES = 'operational_procedures', 'Operational Procedures'
    COMMUNICATIONS = 'communications', 'Communications'
    MASS_BALANCE = 'mass_balance', 'Mass and Balance'
    PERFORMANCE = 'performance', 'Performance'
    INSTRUMENTS = 'instruments', 'Instruments'
    RADIO_NAVIGATION = 'radio_navigation', 'Radio Navigation'


class ProgramType(models.TextChoices):
    """Program type choices."""
    PPL = 'ppl', 'Private Pilot License'
    CPL = 'cpl', 'Commercial Pilot License'
    ATPL = 'atpl', 'Airline Transport Pilot License'
    IR = 'ir', 'Instrument Rating'
    ME = 'me', 'Multi-Engine Rating'
    FI = 'fi', 'Flight Instructor'
    CRI = 'cri', 'Class Rating Instructor'
    IRI = 'iri', 'Instrument Rating Instructor'


class CourseStatus(models.TextChoices):
    """Course status choices."""
    DRAFT = 'draft', 'Draft'
    REVIEW = 'review', 'Under Review'
    PUBLISHED = 'published', 'Published'
    ARCHIVED = 'archived', 'Archived'


class Course(models.Model):
    """
    Theory course model.

    Represents an online theory course with modules and content.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    organization_id = models.UUIDField(db_index=True)

    # Identification
    code = models.CharField(max_length=50)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')
    short_description = models.CharField(max_length=500, blank=True, default='')

    # Category
    category = models.CharField(
        max_length=50,
        choices=CourseCategory.choices
    )
    subcategory = models.CharField(max_length=100, blank=True, default='')

    # Program association
    program_type = models.CharField(
        max_length=50,
        choices=ProgramType.choices,
        blank=True,
        default=''
    )

    # Duration
    estimated_hours = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True
    )

    # Prerequisites
    prerequisites = ArrayField(
        models.UUIDField(),
        default=list,
        blank=True,
        help_text='Prerequisite course IDs'
    )

    # Passing criteria
    min_score_to_pass = models.IntegerField(default=75)
    require_module_completion = models.BooleanField(default=True)
    require_final_exam = models.BooleanField(default=True)

    # Status
    status = models.CharField(
        max_length=20,
        choices=CourseStatus.choices,
        default=CourseStatus.DRAFT
    )
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)

    # Visual
    thumbnail_url = models.URLField(max_length=500, blank=True, default='')
    banner_url = models.URLField(max_length=500, blank=True, default='')

    # Statistics
    enrolled_count = models.IntegerField(default=0)
    completion_count = models.IntegerField(default=0)
    completion_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00')
    )
    average_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True
    )
    average_duration_hours = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True
    )
    rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        null=True,
        blank=True
    )
    rating_count = models.IntegerField(default=0)

    # Metadata
    tags = ArrayField(
        models.CharField(max_length=50),
        default=list,
        blank=True
    )
    learning_objectives = models.JSONField(default=list, blank=True)

    # Pricing (if applicable)
    is_free = models.BooleanField(default=True)
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    currency = models.CharField(max_length=3, default='USD')

    # Settings
    settings = models.JSONField(default=dict, blank=True)

    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.UUIDField(null=True, blank=True)

    class Meta:
        db_table = 'courses'
        ordering = ['name']
        indexes = [
            models.Index(fields=['organization_id']),
            models.Index(fields=['category']),
            models.Index(fields=['status']),
            models.Index(fields=['program_type']),
            models.Index(fields=['is_published']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['organization_id', 'code'],
                name='unique_course_code_per_org'
            )
        ]

    def __str__(self):
        return f"{self.code}: {self.name}"

    @property
    def is_active(self) -> bool:
        """Check if course is active and published."""
        return self.status == CourseStatus.PUBLISHED and self.is_published

    @property
    def module_count(self) -> int:
        """Get number of modules in course."""
        return self.modules.count()

    @property
    def total_duration_minutes(self) -> int:
        """Calculate total duration from all modules."""
        return sum(
            m.estimated_minutes or 0
            for m in self.modules.all()
        )

    def publish(self) -> None:
        """Publish the course."""
        if self.modules.count() == 0:
            raise ValueError("Cannot publish course without modules")

        self.status = CourseStatus.PUBLISHED
        self.is_published = True
        self.published_at = timezone.now()
        self.save()

    def archive(self) -> None:
        """Archive the course."""
        self.status = CourseStatus.ARCHIVED
        self.is_published = False
        self.save()

    def check_prerequisites(self, completed_course_ids: List[str]) -> Dict[str, Any]:
        """Check if prerequisites are met."""
        if not self.prerequisites:
            return {'met': True, 'missing': []}

        missing = []
        for prereq_id in self.prerequisites:
            if str(prereq_id) not in [str(c) for c in completed_course_ids]:
                missing.append(str(prereq_id))

        return {
            'met': len(missing) == 0,
            'missing': missing
        }

    def update_statistics(self) -> None:
        """Update course statistics from enrollments."""
        from .enrollment import CourseEnrollment

        enrollments = CourseEnrollment.objects.filter(course=self)

        self.enrolled_count = enrollments.count()

        completed = enrollments.filter(status='completed')
        self.completion_count = completed.count()

        if self.enrolled_count > 0:
            self.completion_rate = Decimal(
                str(round(self.completion_count / self.enrolled_count * 100, 2))
            )

        scores = completed.exclude(best_score__isnull=True).values_list('best_score', flat=True)
        if scores:
            self.average_score = Decimal(str(round(sum(scores) / len(scores), 2)))

        self.save()

    def get_summary(self) -> Dict[str, Any]:
        """Get course summary."""
        return {
            'id': str(self.id),
            'code': self.code,
            'name': self.name,
            'category': self.category,
            'program_type': self.program_type,
            'estimated_hours': float(self.estimated_hours) if self.estimated_hours else None,
            'module_count': self.module_count,
            'min_score_to_pass': self.min_score_to_pass,
            'enrolled_count': self.enrolled_count,
            'completion_rate': float(self.completion_rate),
            'average_score': float(self.average_score) if self.average_score else None,
            'is_published': self.is_published,
        }


class ContentType(models.TextChoices):
    """Module content type choices."""
    TEXT = 'text', 'Text Content'
    VIDEO = 'video', 'Video Content'
    MIXED = 'mixed', 'Mixed Content'
    INTERACTIVE = 'interactive', 'Interactive Content'
    DOCUMENT = 'document', 'Document/PDF'
    PRESENTATION = 'presentation', 'Presentation'


class CourseModule(models.Model):
    """
    Course module model.

    Represents a module/lesson within a course.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='modules'
    )

    # Identification
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')

    # Ordering
    sort_order = models.IntegerField(default=0)

    # Content
    content_type = models.CharField(
        max_length=50,
        choices=ContentType.choices,
        default=ContentType.MIXED
    )
    content = models.TextField(blank=True, default='')  # Markdown/HTML
    content_html = models.TextField(blank=True, default='')  # Rendered HTML

    # Video
    video_url = models.URLField(max_length=500, blank=True, default='')
    video_duration_seconds = models.IntegerField(null=True, blank=True)
    video_provider = models.CharField(max_length=50, blank=True, default='')
    video_thumbnail_url = models.URLField(max_length=500, blank=True, default='')

    # Audio (for podcasts/narration)
    audio_url = models.URLField(max_length=500, blank=True, default='')
    audio_duration_seconds = models.IntegerField(null=True, blank=True)

    # Document
    document_url = models.URLField(max_length=500, blank=True, default='')
    document_pages = models.IntegerField(null=True, blank=True)

    # Duration
    estimated_minutes = models.IntegerField(null=True, blank=True)

    # Quiz
    has_quiz = models.BooleanField(default=False)
    quiz_id = models.UUIDField(null=True, blank=True)
    quiz_required = models.BooleanField(default=False)
    quiz_passing_score = models.IntegerField(default=75)

    # Completion criteria
    completion_criteria = models.JSONField(default=dict, blank=True)
    # Example: {
    #   "video_watched_percentage": 90,
    #   "quiz_passed": true,
    #   "min_time_spent_seconds": 300,
    #   "scroll_to_bottom": true
    # }

    # Interactivity
    interactive_elements = models.JSONField(default=list, blank=True)

    # Learning objectives
    learning_objectives = models.JSONField(default=list, blank=True)

    # Key points
    key_points = models.JSONField(default=list, blank=True)

    # Resources
    resources = models.JSONField(default=list, blank=True)

    # Statistics
    view_count = models.IntegerField(default=0)
    completion_count = models.IntegerField(default=0)
    average_time_seconds = models.IntegerField(null=True, blank=True)

    # Status
    is_active = models.BooleanField(default=True)
    is_preview = models.BooleanField(default=False)  # Free preview

    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'course_modules'
        ordering = ['sort_order']
        indexes = [
            models.Index(fields=['course', 'sort_order']),
        ]

    def __str__(self):
        return f"{self.course.code} - {self.name}"

    @property
    def organization_id(self):
        """Get organization ID from parent course."""
        return self.course.organization_id

    @property
    def video_duration_minutes(self) -> Optional[int]:
        """Get video duration in minutes."""
        if self.video_duration_seconds:
            return self.video_duration_seconds // 60
        return None

    @property
    def has_video(self) -> bool:
        """Check if module has video content."""
        return bool(self.video_url)

    @property
    def has_content(self) -> bool:
        """Check if module has text content."""
        return bool(self.content)

    @property
    def next_module(self) -> Optional['CourseModule']:
        """Get next module in sequence."""
        return CourseModule.objects.filter(
            course=self.course,
            sort_order__gt=self.sort_order
        ).order_by('sort_order').first()

    @property
    def previous_module(self) -> Optional['CourseModule']:
        """Get previous module in sequence."""
        return CourseModule.objects.filter(
            course=self.course,
            sort_order__lt=self.sort_order
        ).order_by('-sort_order').first()

    def check_completion(
        self,
        video_watched_percentage: int = 0,
        quiz_passed: bool = False,
        time_spent_seconds: int = 0,
        scrolled_to_bottom: bool = False
    ) -> Dict[str, Any]:
        """Check if completion criteria are met."""
        criteria = self.completion_criteria

        if not criteria:
            # Default: just viewing is enough
            return {'completed': True, 'details': {}}

        details = {}
        all_met = True

        # Video watched
        if 'video_watched_percentage' in criteria:
            required = criteria['video_watched_percentage']
            met = video_watched_percentage >= required
            details['video_watched'] = {
                'required': required,
                'actual': video_watched_percentage,
                'met': met
            }
            if not met:
                all_met = False

        # Quiz passed
        if criteria.get('quiz_passed'):
            details['quiz_passed'] = {
                'required': True,
                'actual': quiz_passed,
                'met': quiz_passed
            }
            if not quiz_passed:
                all_met = False

        # Minimum time spent
        if 'min_time_spent_seconds' in criteria:
            required = criteria['min_time_spent_seconds']
            met = time_spent_seconds >= required
            details['time_spent'] = {
                'required': required,
                'actual': time_spent_seconds,
                'met': met
            }
            if not met:
                all_met = False

        # Scrolled to bottom
        if criteria.get('scroll_to_bottom'):
            details['scrolled'] = {
                'required': True,
                'actual': scrolled_to_bottom,
                'met': scrolled_to_bottom
            }
            if not scrolled_to_bottom:
                all_met = False

        return {
            'completed': all_met,
            'details': details
        }

    def get_summary(self) -> Dict[str, Any]:
        """Get module summary."""
        return {
            'id': str(self.id),
            'name': self.name,
            'sort_order': self.sort_order,
            'content_type': self.content_type,
            'estimated_minutes': self.estimated_minutes,
            'has_video': self.has_video,
            'has_quiz': self.has_quiz,
            'video_duration_minutes': self.video_duration_minutes,
            'is_preview': self.is_preview,
        }


class CourseAttachment(models.Model):
    """
    Course attachment model.

    Represents downloadable files attached to courses or modules.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='attachments'
    )
    module = models.ForeignKey(
        CourseModule,
        on_delete=models.CASCADE,
        related_name='attachments',
        null=True,
        blank=True
    )

    # File info
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')
    file_url = models.URLField(max_length=500)
    file_type = models.CharField(max_length=50)
    file_size_bytes = models.BigIntegerField(null=True, blank=True)

    # Ordering
    sort_order = models.IntegerField(default=0)

    # Access
    is_downloadable = models.BooleanField(default=True)
    requires_enrollment = models.BooleanField(default=True)

    # Statistics
    download_count = models.IntegerField(default=0)

    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'course_attachments'
        ordering = ['sort_order']

    def __str__(self):
        return f"{self.course.code} - {self.name}"

    @property
    def file_size_mb(self) -> Optional[float]:
        """Get file size in MB."""
        if self.file_size_bytes:
            return round(self.file_size_bytes / (1024 * 1024), 2)
        return None
