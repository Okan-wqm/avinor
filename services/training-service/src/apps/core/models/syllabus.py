# services/training-service/src/apps/core/models/syllabus.py
"""
Syllabus Models

Defines lessons, exercises, and curriculum content.
"""

import uuid
from decimal import Decimal
from typing import List, Dict, Any, Optional

from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.utils import timezone


class SyllabusLesson(models.Model):
    """
    Syllabus lesson model.

    Represents a single lesson in the training curriculum.
    """

    class LessonType(models.TextChoices):
        GROUND = 'ground', 'Ground Instruction'
        FLIGHT = 'flight', 'Flight Training'
        SIMULATOR = 'simulator', 'Simulator Training'
        BRIEFING = 'briefing', 'Briefing'
        DEBRIEFING = 'debriefing', 'Debriefing'
        EXAM = 'exam', 'Examination'
        STAGE_CHECK = 'stage_check', 'Stage Check'
        PROGRESS_CHECK = 'progress_check', 'Progress Check'
        SELF_STUDY = 'self_study', 'Self Study'

    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        ACTIVE = 'active', 'Active'
        INACTIVE = 'inactive', 'Inactive'
        ARCHIVED = 'archived', 'Archived'

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    organization_id = models.UUIDField(db_index=True)
    program = models.ForeignKey(
        'TrainingProgram',
        on_delete=models.CASCADE,
        related_name='lessons'
    )

    # ==========================================================================
    # Hierarchy
    # ==========================================================================
    stage_id = models.UUIDField(
        blank=True,
        null=True,
        help_text="Stage this lesson belongs to"
    )
    parent_lesson = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sub_lessons'
    )

    # ==========================================================================
    # Identification
    # ==========================================================================
    code = models.CharField(
        max_length=50,
        help_text="Lesson code (e.g., L01, FL-05)"
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    objective = models.TextField(
        blank=True,
        null=True,
        help_text="Learning objective for this lesson"
    )

    # ==========================================================================
    # Lesson Type
    # ==========================================================================
    lesson_type = models.CharField(
        max_length=50,
        choices=LessonType.choices
    )

    # ==========================================================================
    # Ordering
    # ==========================================================================
    sort_order = models.PositiveIntegerField(
        default=0,
        help_text="Order within program/stage"
    )

    # ==========================================================================
    # Duration
    # ==========================================================================
    duration_hours = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Total estimated duration"
    )
    ground_hours = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        blank=True,
        null=True
    )
    flight_hours = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        blank=True,
        null=True
    )
    simulator_hours = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        blank=True,
        null=True
    )
    briefing_hours = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        blank=True,
        null=True
    )

    # ==========================================================================
    # Requirements
    # ==========================================================================
    required_aircraft_type = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="single_engine, multi_engine, helicopter, etc."
    )
    required_aircraft_category = models.CharField(
        max_length=50,
        blank=True,
        null=True
    )
    required_conditions = ArrayField(
        models.CharField(max_length=50),
        default=list,
        blank=True,
        help_text="Required conditions: vfr, ifr, day, night, dual, solo"
    )
    required_equipment = ArrayField(
        models.CharField(max_length=100),
        default=list,
        blank=True,
        help_text="Required equipment for this lesson"
    )

    # ==========================================================================
    # Prerequisites
    # ==========================================================================
    prerequisite_lessons = ArrayField(
        models.UUIDField(),
        default=list,
        blank=True,
        help_text="Lesson IDs that must be completed first"
    )
    prerequisite_hours = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Minimum flight hours before this lesson"
    )
    prerequisite_conditions = models.JSONField(
        default=list,
        help_text='[{"type": "hours", "category": "dual", "value": 10}]'
    )

    # ==========================================================================
    # Content
    # ==========================================================================
    content = models.TextField(
        blank=True,
        null=True,
        help_text="Lesson content (Markdown supported)"
    )
    completion_standards = models.TextField(
        blank=True,
        null=True,
        help_text="Standards for successful completion"
    )
    resources = models.JSONField(
        default=list,
        help_text='[{"type": "video", "url": "...", "title": "..."}]'
    )
    references = models.JSONField(
        default=list,
        help_text="Reference materials (AIM, POH, etc.)"
    )

    # ==========================================================================
    # Grading
    # ==========================================================================
    grading_criteria = models.JSONField(
        default=list,
        help_text="Grading criteria for this lesson"
    )
    min_grade_to_pass = models.PositiveIntegerField(
        default=70,
        help_text="Minimum grade (0-100) to pass"
    )
    max_attempts = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text="Maximum allowed attempts"
    )

    # ==========================================================================
    # Completion Criteria
    # ==========================================================================
    completion_criteria = models.JSONField(
        default=dict,
        help_text='{"min_grade": 70, "instructor_signoff": true}'
    )
    requires_instructor_signoff = models.BooleanField(default=True)
    requires_student_signoff = models.BooleanField(default=False)

    # ==========================================================================
    # ATO Reference
    # ==========================================================================
    ato_reference = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="ATO syllabus reference number"
    )
    regulatory_reference = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Regulatory reference (e.g., EASA Part-FCL)"
    )

    # ==========================================================================
    # Notes
    # ==========================================================================
    instructor_notes = models.TextField(
        blank=True,
        null=True,
        help_text="Notes visible only to instructors"
    )
    common_errors = models.TextField(
        blank=True,
        null=True,
        help_text="Common student errors to watch for"
    )

    # ==========================================================================
    # Status
    # ==========================================================================
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE
    )

    # ==========================================================================
    # Metadata
    # ==========================================================================
    metadata = models.JSONField(default=dict)
    tags = ArrayField(
        models.CharField(max_length=50),
        default=list,
        blank=True
    )

    # ==========================================================================
    # Timestamps
    # ==========================================================================
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'syllabus_lessons'
        ordering = ['program', 'sort_order']
        indexes = [
            models.Index(fields=['program']),
            models.Index(fields=['stage_id']),
            models.Index(fields=['program', 'sort_order']),
            models.Index(fields=['lesson_type']),
        ]

    def __str__(self):
        return f"{self.code}: {self.name}"

    # ==========================================================================
    # Properties
    # ==========================================================================

    @property
    def is_flight_lesson(self) -> bool:
        """Check if this is a flight lesson."""
        return self.lesson_type in [self.LessonType.FLIGHT, self.LessonType.SIMULATOR]

    @property
    def is_ground_lesson(self) -> bool:
        """Check if this is a ground lesson."""
        return self.lesson_type in [self.LessonType.GROUND, self.LessonType.BRIEFING]

    @property
    def is_evaluation(self) -> bool:
        """Check if this is an evaluation lesson."""
        return self.lesson_type in [
            self.LessonType.EXAM,
            self.LessonType.STAGE_CHECK,
            self.LessonType.PROGRESS_CHECK
        ]

    @property
    def total_duration(self) -> Decimal:
        """Get total duration from all components."""
        total = Decimal('0')
        if self.ground_hours:
            total += self.ground_hours
        if self.flight_hours:
            total += self.flight_hours
        if self.simulator_hours:
            total += self.simulator_hours
        if self.briefing_hours:
            total += self.briefing_hours
        return total or (self.duration_hours or Decimal('0'))

    @property
    def exercise_count(self) -> int:
        """Get number of exercises."""
        return self.exercises.count()

    @property
    def has_prerequisites(self) -> bool:
        """Check if lesson has prerequisites."""
        return bool(self.prerequisite_lessons) or bool(self.prerequisite_hours)

    # ==========================================================================
    # Methods
    # ==========================================================================

    def check_prerequisites(self, completed_lesson_ids: List[str], total_hours: Decimal = None) -> Dict[str, Any]:
        """Check if prerequisites are met."""
        result = {
            'met': True,
            'missing_lessons': [],
            'hours_required': None,
            'hours_current': None,
        }

        # Check prerequisite lessons
        if self.prerequisite_lessons:
            completed_set = set(str(lid) for lid in completed_lesson_ids)
            for prereq_id in self.prerequisite_lessons:
                if str(prereq_id) not in completed_set:
                    result['met'] = False
                    result['missing_lessons'].append(str(prereq_id))

        # Check prerequisite hours
        if self.prerequisite_hours and total_hours is not None:
            result['hours_required'] = float(self.prerequisite_hours)
            result['hours_current'] = float(total_hours)
            if total_hours < self.prerequisite_hours:
                result['met'] = False

        return result

    def get_stage_name(self) -> Optional[str]:
        """Get the name of the stage this lesson belongs to."""
        if not self.stage_id:
            return None

        for stage in self.program.stages:
            if stage.get('id') == str(self.stage_id):
                return stage.get('name')
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'id': str(self.id),
            'code': self.code,
            'name': self.name,
            'description': self.description,
            'objective': self.objective,
            'lesson_type': self.lesson_type,
            'sort_order': self.sort_order,
            'duration': {
                'total': float(self.total_duration),
                'ground': float(self.ground_hours or 0),
                'flight': float(self.flight_hours or 0),
                'simulator': float(self.simulator_hours or 0),
                'briefing': float(self.briefing_hours or 0),
            },
            'min_grade_to_pass': self.min_grade_to_pass,
            'stage_id': str(self.stage_id) if self.stage_id else None,
            'stage_name': self.get_stage_name(),
            'status': self.status,
        }


class Exercise(models.Model):
    """
    Exercise model.

    Represents a specific exercise/maneuver within a lesson.
    """

    class GradingScale(models.TextChoices):
        NUMERIC = 'numeric', 'Numeric (0-100)'
        LETTER = 'letter', 'Letter (A-F)'
        SATISFACTORY = 'satisfactory', 'Satisfactory/Unsatisfactory'
        COMPETENCY = 'competency', 'Competency (1-4)'
        PASS_FAIL = 'pass_fail', 'Pass/Fail'

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    organization_id = models.UUIDField(db_index=True)
    lesson = models.ForeignKey(
        SyllabusLesson,
        on_delete=models.CASCADE,
        related_name='exercises'
    )

    # ==========================================================================
    # Identification
    # ==========================================================================
    code = models.CharField(max_length=50)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)

    # ==========================================================================
    # Ordering
    # ==========================================================================
    sort_order = models.PositiveIntegerField(default=0)

    # ==========================================================================
    # ATO Reference
    # ==========================================================================
    ato_reference = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="ATO exercise reference"
    )

    # ==========================================================================
    # Competency Elements
    # ==========================================================================
    competency_elements = models.JSONField(
        default=list,
        help_text='[{"name": "Coordination", "weight": 20}]'
    )

    # ==========================================================================
    # Grading
    # ==========================================================================
    grading_scale = models.CharField(
        max_length=20,
        choices=GradingScale.choices,
        default=GradingScale.NUMERIC
    )

    # ==========================================================================
    # Tolerances/Standards
    # ==========================================================================
    tolerances = models.JSONField(
        default=dict,
        help_text='{"altitude_ft": 100, "heading_deg": 10, "airspeed_kts": 5}'
    )
    standards = models.TextField(
        blank=True,
        null=True,
        help_text="Completion standards for this exercise"
    )

    # ==========================================================================
    # Completion Requirements
    # ==========================================================================
    min_demonstrations = models.PositiveIntegerField(
        default=1,
        help_text="Minimum successful demonstrations required"
    )
    min_grade = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text="Minimum grade to pass"
    )

    # ==========================================================================
    # Resources
    # ==========================================================================
    resources = models.JSONField(default=list)

    # ==========================================================================
    # Status
    # ==========================================================================
    is_required = models.BooleanField(
        default=True,
        help_text="Is this exercise required for lesson completion"
    )
    is_critical = models.BooleanField(
        default=False,
        help_text="Is this a critical exercise (failure = lesson failure)"
    )

    # ==========================================================================
    # Timestamps
    # ==========================================================================
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'exercises'
        ordering = ['lesson', 'sort_order']
        indexes = [
            models.Index(fields=['lesson']),
        ]

    def __str__(self):
        return f"{self.code}: {self.name}"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'id': str(self.id),
            'code': self.code,
            'name': self.name,
            'description': self.description,
            'sort_order': self.sort_order,
            'grading_scale': self.grading_scale,
            'min_demonstrations': self.min_demonstrations,
            'min_grade': self.min_grade,
            'tolerances': self.tolerances,
            'is_required': self.is_required,
            'is_critical': self.is_critical,
            'competency_elements': self.competency_elements,
        }
