"""Training Service Models - Training programs, syllabi, and progress tracking."""
import uuid
from django.db import models
from shared.common.mixins import UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin


class TrainingProgram(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, models.Model):
    """Training program (e.g., PPL, CPL, IR)."""

    class ProgramType(models.TextChoices):
        PPL = 'ppl', 'Private Pilot License'
        CPL = 'cpl', 'Commercial Pilot License'
        ATPL = 'atpl', 'Airline Transport Pilot License'
        IR = 'ir', 'Instrument Rating'
        MEP = 'mep', 'Multi-Engine Piston'
        FI = 'fi', 'Flight Instructor'
        NIGHT = 'night', 'Night Rating'
        AEROBATIC = 'aerobatic', 'Aerobatic Rating'
        TAILWHEEL = 'tailwheel', 'Tailwheel Endorsement'
        CUSTOM = 'custom', 'Custom Program'

    organization_id = models.UUIDField()

    name = models.CharField(max_length=255)
    code = models.CharField(max_length=20)
    program_type = models.CharField(max_length=20, choices=ProgramType.choices, default=ProgramType.PPL)
    description = models.TextField(blank=True)

    # Requirements
    min_flight_hours = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    min_solo_hours = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    min_cross_country_hours = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    min_night_hours = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    min_instrument_hours = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    min_dual_hours = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    min_ground_hours = models.DecimalField(max_digits=5, decimal_places=1, default=0)

    # Prerequisites
    prerequisite_programs = models.ManyToManyField('self', symmetrical=False, blank=True)
    min_age = models.IntegerField(default=16)
    requires_medical = models.CharField(max_length=20, default='class2')  # class1, class2, class3

    # Pricing
    estimated_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default='USD')

    # Status
    is_active = models.BooleanField(default=True)
    version = models.CharField(max_length=20, default='1.0')

    class Meta:
        db_table = 'training_programs'
        unique_together = ['organization_id', 'code']
        ordering = ['name']


class Syllabus(UUIDPrimaryKeyMixin, TimestampMixin, models.Model):
    """Training syllabus containing lessons and stages."""

    program = models.ForeignKey(TrainingProgram, on_delete=models.CASCADE, related_name='syllabi')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    version = models.CharField(max_length=20, default='1.0')
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'syllabi'
        ordering = ['name']


class Stage(UUIDPrimaryKeyMixin, TimestampMixin, models.Model):
    """Stage/phase within a syllabus."""

    syllabus = models.ForeignKey(Syllabus, on_delete=models.CASCADE, related_name='stages')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    order = models.IntegerField(default=0)

    # Completion criteria
    min_flights = models.IntegerField(default=0)
    min_hours = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    requires_stage_check = models.BooleanField(default=False)

    class Meta:
        db_table = 'stages'
        ordering = ['order']


class Lesson(UUIDPrimaryKeyMixin, TimestampMixin, models.Model):
    """Individual lesson within a stage."""

    class LessonType(models.TextChoices):
        GROUND = 'ground', 'Ground Lesson'
        FLIGHT = 'flight', 'Flight Lesson'
        SIMULATOR = 'simulator', 'Simulator Session'
        BRIEFING = 'briefing', 'Briefing Only'
        STAGE_CHECK = 'stage_check', 'Stage Check'
        CHECK_RIDE = 'check_ride', 'Check Ride'

    stage = models.ForeignKey(Stage, on_delete=models.CASCADE, related_name='lessons')
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=20)
    lesson_type = models.CharField(max_length=20, choices=LessonType.choices, default=LessonType.FLIGHT)
    description = models.TextField(blank=True)
    order = models.IntegerField(default=0)

    # Duration
    ground_duration_minutes = models.IntegerField(default=0)
    flight_duration_minutes = models.IntegerField(default=0)

    # Content
    objectives = models.JSONField(default=list, blank=True)
    completion_standards = models.JSONField(default=list, blank=True)
    equipment_required = models.JSONField(default=list, blank=True)
    references = models.JSONField(default=list, blank=True)

    # Prerequisites
    prerequisite_lessons = models.ManyToManyField('self', symmetrical=False, blank=True)

    class Meta:
        db_table = 'lessons'
        ordering = ['order']


class StudentEnrollment(UUIDPrimaryKeyMixin, TimestampMixin, models.Model):
    """Student enrollment in a training program."""

    class Status(models.TextChoices):
        ACTIVE = 'active', 'Active'
        ON_HOLD = 'on_hold', 'On Hold'
        COMPLETED = 'completed', 'Completed'
        WITHDRAWN = 'withdrawn', 'Withdrawn'

    student_id = models.UUIDField()
    program = models.ForeignKey(TrainingProgram, on_delete=models.PROTECT, related_name='enrollments')
    syllabus = models.ForeignKey(Syllabus, on_delete=models.PROTECT, related_name='enrollments')
    instructor_id = models.UUIDField(null=True, blank=True)

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    enrolled_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    target_completion_date = models.DateField(null=True, blank=True)

    # Progress
    current_stage = models.ForeignKey(Stage, on_delete=models.SET_NULL, null=True, blank=True)
    current_lesson = models.ForeignKey(Lesson, on_delete=models.SET_NULL, null=True, blank=True)

    # Hours accumulated
    total_flight_hours = models.DecimalField(max_digits=6, decimal_places=1, default=0)
    total_ground_hours = models.DecimalField(max_digits=6, decimal_places=1, default=0)
    total_solo_hours = models.DecimalField(max_digits=6, decimal_places=1, default=0)

    notes = models.TextField(blank=True)

    class Meta:
        db_table = 'student_enrollments'
        unique_together = ['student_id', 'program']
        indexes = [
            models.Index(fields=['student_id']),
            models.Index(fields=['instructor_id']),
            models.Index(fields=['status']),
        ]


class LessonCompletion(UUIDPrimaryKeyMixin, TimestampMixin, models.Model):
    """Record of a completed lesson."""

    class Grade(models.TextChoices):
        SATISFACTORY = 'S', 'Satisfactory'
        UNSATISFACTORY = 'U', 'Unsatisfactory'
        INCOMPLETE = 'I', 'Incomplete'
        NOT_OBSERVED = 'N', 'Not Observed'

    enrollment = models.ForeignKey(StudentEnrollment, on_delete=models.CASCADE, related_name='completions')
    lesson = models.ForeignKey(Lesson, on_delete=models.PROTECT, related_name='completions')
    flight_id = models.UUIDField(null=True, blank=True)
    instructor_id = models.UUIDField()

    completed_at = models.DateTimeField()
    grade = models.CharField(max_length=1, choices=Grade.choices, default=Grade.SATISFACTORY)

    # Time
    ground_time_minutes = models.IntegerField(default=0)
    flight_time_minutes = models.IntegerField(default=0)

    # Objectives achieved
    objectives_achieved = models.JSONField(default=list, blank=True)
    objectives_incomplete = models.JSONField(default=list, blank=True)

    # Feedback
    instructor_comments = models.TextField(blank=True)
    student_notes = models.TextField(blank=True)

    # Signatures
    instructor_signature = models.TextField(blank=True)
    student_signature = models.TextField(blank=True)

    class Meta:
        db_table = 'lesson_completions'
        ordering = ['-completed_at']


class StageCheck(UUIDPrimaryKeyMixin, TimestampMixin, models.Model):
    """Stage check or progress check."""

    class Result(models.TextChoices):
        PASS = 'pass', 'Pass'
        FAIL = 'fail', 'Fail'
        INCOMPLETE = 'incomplete', 'Incomplete'

    enrollment = models.ForeignKey(StudentEnrollment, on_delete=models.CASCADE, related_name='stage_checks')
    stage = models.ForeignKey(Stage, on_delete=models.PROTECT, related_name='checks')
    examiner_id = models.UUIDField()
    flight_id = models.UUIDField(null=True, blank=True)

    scheduled_at = models.DateTimeField()
    completed_at = models.DateTimeField(null=True, blank=True)
    result = models.CharField(max_length=20, choices=Result.choices, null=True, blank=True)

    # Evaluation
    areas_satisfactory = models.JSONField(default=list, blank=True)
    areas_unsatisfactory = models.JSONField(default=list, blank=True)
    recommendations = models.TextField(blank=True)
    examiner_comments = models.TextField(blank=True)

    class Meta:
        db_table = 'stage_checks'
        ordering = ['-scheduled_at']
