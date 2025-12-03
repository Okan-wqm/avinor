"""
Theory Service Models.
"""
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from shared.common.mixins import UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin


class Course(UUIDPrimaryKeyMixin, TimestampMixin, models.Model):
    """
    Ground school courses.
    """
    class CourseType(models.TextChoices):
        PPL = 'ppl', 'Private Pilot License'
        CPL = 'cpl', 'Commercial Pilot License'
        ATPL = 'atpl', 'Airline Transport Pilot License'
        IR = 'ir', 'Instrument Rating'
        MEP = 'mep', 'Multi-Engine Piston'
        TYPE_RATING = 'type_rating', 'Type Rating'
        RECURRENT = 'recurrent', 'Recurrent Training'
        CUSTOM = 'custom', 'Custom Course'

    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        PUBLISHED = 'published', 'Published'
        ARCHIVED = 'archived', 'Archived'

    organization_id = models.UUIDField()

    # Course info
    code = models.CharField(max_length=50, unique=True)
    title = models.CharField(max_length=255)
    description = models.TextField()
    course_type = models.CharField(max_length=20, choices=CourseType.choices)

    # Content
    objectives = models.TextField(blank=True)
    prerequisites = models.TextField(blank=True)
    syllabus = models.JSONField(default=list, blank=True)

    # Scheduling
    duration_hours = models.IntegerField(null=True, blank=True)
    validity_days = models.IntegerField(null=True, blank=True)

    # Pricing
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    # Status
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)

    # Resources
    cover_image_url = models.URLField(blank=True)
    resources = models.JSONField(default=list, blank=True)

    # Instructors
    instructor_ids = models.JSONField(default=list, blank=True)

    class Meta:
        db_table = 'courses'
        ordering = ['code']
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['organization_id']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.code} - {self.title}"


class Lesson(UUIDPrimaryKeyMixin, TimestampMixin, models.Model):
    """
    Individual lessons within a course.
    """
    class LessonType(models.TextChoices):
        VIDEO = 'video', 'Video Lesson'
        TEXT = 'text', 'Text Content'
        PRESENTATION = 'presentation', 'Presentation'
        INTERACTIVE = 'interactive', 'Interactive'
        QUIZ = 'quiz', 'Quiz'
        ASSIGNMENT = 'assignment', 'Assignment'

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='lessons'
    )

    # Lesson info
    order = models.IntegerField(default=0)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    lesson_type = models.CharField(max_length=20, choices=LessonType.choices)

    # Content
    content = models.TextField(blank=True)
    content_url = models.URLField(blank=True)
    video_url = models.URLField(blank=True)
    duration_minutes = models.IntegerField(null=True, blank=True)

    # Resources
    attachments = models.JSONField(default=list, blank=True)
    references = models.JSONField(default=list, blank=True)

    # Settings
    is_mandatory = models.BooleanField(default=True)
    is_published = models.BooleanField(default=False)
    passing_score = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )

    class Meta:
        db_table = 'lessons'
        ordering = ['course', 'order']
        indexes = [
            models.Index(fields=['course', 'order']),
        ]

    def __str__(self):
        return f"{self.course.code} - {self.title}"


class Quiz(UUIDPrimaryKeyMixin, TimestampMixin, models.Model):
    """
    Quizzes for assessments.
    """
    class QuizType(models.TextChoices):
        PRACTICE = 'practice', 'Practice Quiz'
        GRADED = 'graded', 'Graded Quiz'
        FINAL_EXAM = 'final_exam', 'Final Exam'

    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.CASCADE,
        related_name='quizzes',
        null=True,
        blank=True
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='quizzes'
    )

    # Quiz info
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    quiz_type = models.CharField(max_length=20, choices=QuizType.choices)

    # Settings
    time_limit_minutes = models.IntegerField(null=True, blank=True)
    passing_score = models.IntegerField(
        default=70,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    max_attempts = models.IntegerField(null=True, blank=True)
    shuffle_questions = models.BooleanField(default=True)
    show_correct_answers = models.BooleanField(default=False)

    # Status
    is_published = models.BooleanField(default=False)

    class Meta:
        db_table = 'quizzes'
        ordering = ['course', 'title']

    def __str__(self):
        return f"{self.course.code} - {self.title}"


class Question(UUIDPrimaryKeyMixin, TimestampMixin, models.Model):
    """
    Questions for quizzes.
    """
    class QuestionType(models.TextChoices):
        MULTIPLE_CHOICE = 'multiple_choice', 'Multiple Choice'
        TRUE_FALSE = 'true_false', 'True/False'
        MULTI_SELECT = 'multi_select', 'Multiple Selection'
        SHORT_ANSWER = 'short_answer', 'Short Answer'

    quiz = models.ForeignKey(
        Quiz,
        on_delete=models.CASCADE,
        related_name='questions'
    )

    # Question info
    order = models.IntegerField(default=0)
    question_text = models.TextField()
    question_type = models.CharField(max_length=20, choices=QuestionType.choices)

    # Points
    points = models.IntegerField(default=1, validators=[MinValueValidator(1)])

    # Options (for multiple choice)
    options = models.JSONField(default=list, blank=True)  # [{text: "", is_correct: bool}]

    # Correct answer (for non-multiple choice)
    correct_answer = models.TextField(blank=True)

    # Explanation
    explanation = models.TextField(blank=True)

    # Media
    image_url = models.URLField(blank=True)

    class Meta:
        db_table = 'questions'
        ordering = ['quiz', 'order']

    def __str__(self):
        return f"{self.quiz.title} - Q{self.order}"


class StudentProgress(UUIDPrimaryKeyMixin, TimestampMixin, models.Model):
    """
    Tracks student progress through courses and lessons.
    """
    class Status(models.TextChoices):
        NOT_STARTED = 'not_started', 'Not Started'
        IN_PROGRESS = 'in_progress', 'In Progress'
        COMPLETED = 'completed', 'Completed'

    student_id = models.UUIDField()
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='student_progress'
    )
    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.CASCADE,
        related_name='student_progress',
        null=True,
        blank=True
    )

    # Progress tracking
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NOT_STARTED)
    progress_percentage = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )

    # Time tracking
    time_spent_minutes = models.IntegerField(default=0)
    last_accessed = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # Enrollment
    enrolled_at = models.DateTimeField(auto_now_add=True)
    enrollment_expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'student_progress'
        unique_together = ['student_id', 'course', 'lesson']
        ordering = ['-last_accessed']
        indexes = [
            models.Index(fields=['student_id']),
            models.Index(fields=['course']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        lesson_part = f" - {self.lesson.title}" if self.lesson else ""
        return f"Student {self.student_id} - {self.course.code}{lesson_part}"


class ExamAttempt(UUIDPrimaryKeyMixin, TimestampMixin, models.Model):
    """
    Records of quiz/exam attempts by students.
    """
    class Status(models.TextChoices):
        IN_PROGRESS = 'in_progress', 'In Progress'
        COMPLETED = 'completed', 'Completed'
        ABANDONED = 'abandoned', 'Abandoned'

    student_id = models.UUIDField()
    quiz = models.ForeignKey(
        Quiz,
        on_delete=models.CASCADE,
        related_name='attempts'
    )

    # Attempt info
    attempt_number = models.IntegerField(default=1)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.IN_PROGRESS)

    # Timing
    started_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    time_spent_minutes = models.IntegerField(null=True, blank=True)

    # Answers
    answers = models.JSONField(default=dict, blank=True)  # {question_id: answer}

    # Scoring
    score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    points_earned = models.IntegerField(null=True, blank=True)
    points_possible = models.IntegerField(null=True, blank=True)
    passed = models.BooleanField(null=True, blank=True)

    # Grading
    graded_at = models.DateTimeField(null=True, blank=True)
    graded_by_id = models.UUIDField(null=True, blank=True)
    feedback = models.TextField(blank=True)

    class Meta:
        db_table = 'exam_attempts'
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['student_id']),
            models.Index(fields=['quiz']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"Student {self.student_id} - {self.quiz.title} (Attempt {self.attempt_number})"
