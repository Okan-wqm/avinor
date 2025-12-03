# services/training-service/src/apps/core/models/training_program.py
"""
Training Program Model

Defines training programs, curricula, and their requirements.
"""

import uuid
from decimal import Decimal
from typing import List, Dict, Any, Optional

from django.db import models
from django.db.models import Sum, Count, Q
from django.utils import timezone


class TrainingProgram(models.Model):
    """
    Training program model.

    Represents a complete training curriculum (PPL, CPL, IR, etc.)
    with all requirements, stages, and pricing.
    """

    class ProgramType(models.TextChoices):
        PPL = 'ppl', 'Private Pilot License'
        CPL = 'cpl', 'Commercial Pilot License'
        IR = 'ir', 'Instrument Rating'
        ME = 'me', 'Multi-Engine Rating'
        FI = 'fi', 'Flight Instructor'
        IRI = 'iri', 'Instrument Rating Instructor'
        CRI = 'cri', 'Class Rating Instructor'
        ATP = 'atp', 'Airline Transport Pilot'
        TYPE_RATING = 'type_rating', 'Type Rating'
        MCC = 'mcc', 'Multi-Crew Cooperation'
        RECURRENT = 'recurrent', 'Recurrent Training'
        PROFICIENCY = 'proficiency', 'Proficiency Check'
        CUSTOM = 'custom', 'Custom Program'

    class RegulatoryAuthority(models.TextChoices):
        EASA = 'EASA', 'European Union Aviation Safety Agency'
        FAA = 'FAA', 'Federal Aviation Administration'
        SHGM = 'SHGM', 'Sivil Havacılık Genel Müdürlüğü'
        CAA = 'CAA', 'Civil Aviation Authority'
        ICAO = 'ICAO', 'International Civil Aviation Organization'

    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        ACTIVE = 'active', 'Active'
        DEPRECATED = 'deprecated', 'Deprecated'
        ARCHIVED = 'archived', 'Archived'

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    organization_id = models.UUIDField(db_index=True)

    # ==========================================================================
    # Identification
    # ==========================================================================
    code = models.CharField(
        max_length=50,
        help_text="Unique program code (e.g., PPL-2024)"
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)

    # ==========================================================================
    # Program Type
    # ==========================================================================
    program_type = models.CharField(
        max_length=50,
        choices=ProgramType.choices
    )

    # ==========================================================================
    # Regulatory Information
    # ==========================================================================
    regulatory_authority = models.CharField(
        max_length=20,
        choices=RegulatoryAuthority.choices,
        blank=True,
        null=True
    )
    approval_number = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="ATO approval number"
    )
    approval_date = models.DateField(blank=True, null=True)
    expiry_date = models.DateField(blank=True, null=True)

    # ==========================================================================
    # Minimum Hour Requirements
    # ==========================================================================
    min_hours_total = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Minimum total flight hours required"
    )
    min_hours_dual = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Minimum dual instruction hours"
    )
    min_hours_solo = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Minimum solo flight hours"
    )
    min_hours_pic = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Minimum PIC hours"
    )
    min_hours_cross_country = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Minimum cross-country hours"
    )
    min_hours_night = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Minimum night flying hours"
    )
    min_hours_instrument = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Minimum instrument hours"
    )
    min_hours_simulator = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Minimum simulator hours"
    )
    min_hours_ground = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Minimum ground instruction hours"
    )

    # ==========================================================================
    # Prerequisites
    # ==========================================================================
    prerequisites = models.JSONField(
        default=list,
        help_text='[{"type": "license", "value": "PPL"}, {"type": "hours", "value": 200}]'
    )
    min_age = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text="Minimum age requirement"
    )
    required_medical_class = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text="Required medical certificate class (1, 2, or 3)"
    )

    # ==========================================================================
    # Duration
    # ==========================================================================
    estimated_duration_days = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text="Estimated program duration in days"
    )
    max_duration_months = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text="Maximum allowed duration in months"
    )

    # ==========================================================================
    # Pricing
    # ==========================================================================
    base_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True
    )
    currency = models.CharField(
        max_length=3,
        default='NOK'
    )
    price_includes_vat = models.BooleanField(default=True)

    # ==========================================================================
    # Syllabus Information
    # ==========================================================================
    syllabus_version = models.CharField(
        max_length=50,
        blank=True,
        null=True
    )
    syllabus_document_url = models.URLField(
        max_length=500,
        blank=True,
        null=True
    )

    # ==========================================================================
    # Stages (stored as JSON for flexibility)
    # ==========================================================================
    stages = models.JSONField(
        default=list,
        help_text='[{"id": "uuid", "name": "Pre-Solo", "order": 1}]'
    )

    # ==========================================================================
    # Status and Publishing
    # ==========================================================================
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT
    )
    is_published = models.BooleanField(default=False)

    # ==========================================================================
    # Visual
    # ==========================================================================
    thumbnail_url = models.URLField(
        max_length=500,
        blank=True,
        null=True
    )

    # ==========================================================================
    # Metadata
    # ==========================================================================
    metadata = models.JSONField(default=dict)
    tags = models.JSONField(
        default=list,
        help_text="Tags for categorization"
    )

    # ==========================================================================
    # Audit
    # ==========================================================================
    created_by = models.UUIDField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'training_programs'
        ordering = ['name']
        indexes = [
            models.Index(fields=['organization_id']),
            models.Index(fields=['program_type']),
            models.Index(fields=['status']),
            models.Index(fields=['organization_id', 'code']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['organization_id', 'code'],
                name='unique_program_code_per_org'
            )
        ]

    def __str__(self):
        return f"{self.code}: {self.name}"

    # ==========================================================================
    # Properties
    # ==========================================================================

    @property
    def is_active(self) -> bool:
        """Check if program is active and published."""
        return self.status == self.Status.ACTIVE and self.is_published

    @property
    def total_lessons(self) -> int:
        """Get total number of lessons."""
        return self.lessons.filter(status='active').count()

    @property
    def total_flight_hours(self) -> Decimal:
        """Get total planned flight hours."""
        result = self.lessons.filter(
            status='active'
        ).aggregate(total=Sum('flight_hours'))
        return result['total'] or Decimal('0')

    @property
    def total_ground_hours(self) -> Decimal:
        """Get total planned ground hours."""
        result = self.lessons.filter(
            status='active'
        ).aggregate(total=Sum('ground_hours'))
        return result['total'] or Decimal('0')

    @property
    def stage_count(self) -> int:
        """Get number of stages."""
        return len(self.stages) if self.stages else 0

    @property
    def active_enrollments_count(self) -> int:
        """Get count of active enrollments."""
        return self.enrollments.filter(status='active').count()

    # ==========================================================================
    # Methods
    # ==========================================================================

    def get_stage(self, stage_id: str) -> Optional[Dict[str, Any]]:
        """Get stage by ID."""
        if not self.stages:
            return None
        for stage in self.stages:
            if stage.get('id') == stage_id:
                return stage
        return None

    def get_stage_by_order(self, order: int) -> Optional[Dict[str, Any]]:
        """Get stage by order number."""
        if not self.stages:
            return None
        for stage in self.stages:
            if stage.get('order') == order:
                return stage
        return None

    def get_next_stage(self, current_stage_id: str) -> Optional[Dict[str, Any]]:
        """Get the next stage after current."""
        if not self.stages:
            return None

        current = self.get_stage(current_stage_id)
        if not current:
            return None

        current_order = current.get('order', 0)
        for stage in sorted(self.stages, key=lambda x: x.get('order', 0)):
            if stage.get('order', 0) > current_order:
                return stage
        return None

    def add_stage(self, name: str, description: str = None) -> Dict[str, Any]:
        """Add a new stage to the program."""
        if not self.stages:
            self.stages = []

        # Get next order
        max_order = max([s.get('order', 0) for s in self.stages], default=0)

        stage = {
            'id': str(uuid.uuid4()),
            'name': name,
            'description': description,
            'order': max_order + 1,
            'created_at': timezone.now().isoformat(),
        }

        self.stages.append(stage)
        self.save()
        return stage

    def publish(self) -> None:
        """Publish the program."""
        if self.status != self.Status.ACTIVE:
            self.status = self.Status.ACTIVE
        self.is_published = True
        self.save()

    def archive(self) -> None:
        """Archive the program."""
        self.status = self.Status.ARCHIVED
        self.is_published = False
        self.save()

    def get_requirements_summary(self) -> Dict[str, Any]:
        """Get summary of program requirements."""
        return {
            'min_hours': {
                'total': float(self.min_hours_total or 0),
                'dual': float(self.min_hours_dual or 0),
                'solo': float(self.min_hours_solo or 0),
                'pic': float(self.min_hours_pic or 0),
                'cross_country': float(self.min_hours_cross_country or 0),
                'night': float(self.min_hours_night or 0),
                'instrument': float(self.min_hours_instrument or 0),
                'simulator': float(self.min_hours_simulator or 0),
                'ground': float(self.min_hours_ground or 0),
            },
            'min_age': self.min_age,
            'medical_class': self.required_medical_class,
            'prerequisites': self.prerequisites,
            'duration': {
                'estimated_days': self.estimated_duration_days,
                'max_months': self.max_duration_months,
            }
        }

    def to_summary_dict(self) -> Dict[str, Any]:
        """Convert to summary dictionary."""
        return {
            'id': str(self.id),
            'code': self.code,
            'name': self.name,
            'program_type': self.program_type,
            'status': self.status,
            'is_published': self.is_published,
            'total_lessons': self.total_lessons,
            'stage_count': self.stage_count,
            'base_price': float(self.base_price) if self.base_price else None,
            'currency': self.currency,
        }


class ProgramStage(models.Model):
    """
    Program stage model (optional - for more complex stage management).

    Can be used instead of or alongside JSON stages field.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    program = models.ForeignKey(
        TrainingProgram,
        on_delete=models.CASCADE,
        related_name='stage_records'
    )
    organization_id = models.UUIDField()

    # ==========================================================================
    # Stage Details
    # ==========================================================================
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    code = models.CharField(max_length=50, blank=True, null=True)

    # Order within program
    sort_order = models.PositiveIntegerField(default=0)

    # ==========================================================================
    # Requirements
    # ==========================================================================
    min_hours_before = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Minimum hours required before this stage"
    )
    min_lessons_before = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text="Minimum lessons completed before this stage"
    )

    # ==========================================================================
    # Stage Check Requirements
    # ==========================================================================
    requires_stage_check = models.BooleanField(default=True)
    stage_check_type = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Type of stage check (oral, flight, combined)"
    )

    # ==========================================================================
    # Metadata
    # ==========================================================================
    metadata = models.JSONField(default=dict)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'program_stages'
        ordering = ['program', 'sort_order']
        constraints = [
            models.UniqueConstraint(
                fields=['program', 'code'],
                name='unique_stage_code_per_program'
            )
        ]

    def __str__(self):
        return f"{self.program.code} - {self.name}"
