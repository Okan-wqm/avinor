# services/theory-service/src/apps/core/models/exam.py
"""
Exam Models

Models for exam definitions and configuration.
"""

import uuid
from decimal import Decimal
from typing import Dict, Any, List, Optional
import random

from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.utils import timezone

from .course import Course, CourseModule
from .question import Question


class ExamType(models.TextChoices):
    """Exam type choices."""
    STANDARD = 'standard', 'Standard Exam'
    PRACTICE = 'practice', 'Practice Test'
    MOCK = 'mock', 'Mock Exam'
    FINAL = 'final', 'Final Exam'
    PROGRESS_CHECK = 'progress_check', 'Progress Check'
    DIAGNOSTIC = 'diagnostic', 'Diagnostic Test'
    REMEDIAL = 'remedial', 'Remedial Exam'


class QuestionSelection(models.TextChoices):
    """Question selection method choices."""
    FIXED = 'fixed', 'Fixed Questions'
    RANDOM = 'random', 'Random Selection'
    ADAPTIVE = 'adaptive', 'Adaptive Selection'
    WEIGHTED = 'weighted', 'Weighted Random'


class PassingType(models.TextChoices):
    """Passing criteria type choices."""
    PERCENTAGE = 'percentage', 'Percentage Based'
    POINTS = 'points', 'Points Based'
    CATEGORY = 'category', 'Category Based'  # Must pass each category


class ExamStatus(models.TextChoices):
    """Exam status choices."""
    DRAFT = 'draft', 'Draft'
    REVIEW = 'review', 'Under Review'
    PUBLISHED = 'published', 'Published'
    ARCHIVED = 'archived', 'Archived'


class Exam(models.Model):
    """
    Exam model.

    Represents an exam definition with questions and rules.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    organization_id = models.UUIDField(db_index=True)

    # Relationships
    course = models.ForeignKey(
        Course,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='exams'
    )
    module = models.ForeignKey(
        CourseModule,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='exams'
    )

    # Identification
    code = models.CharField(max_length=50, blank=True, default='')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')
    instructions = models.TextField(blank=True, default='')

    # Type
    exam_type = models.CharField(
        max_length=50,
        choices=ExamType.choices,
        default=ExamType.STANDARD
    )

    # Question selection
    question_selection = models.CharField(
        max_length=20,
        choices=QuestionSelection.choices,
        default=QuestionSelection.RANDOM
    )

    # Fixed questions (for fixed selection)
    fixed_questions = ArrayField(
        models.UUIDField(),
        default=list,
        blank=True
    )

    # Random selection rules
    random_rules = models.JSONField(default=list, blank=True)
    # Example:
    # [
    #   {"category": "air_law", "count": 10, "difficulty": "medium"},
    #   {"category": "meteorology", "count": 15},
    #   {"category": "navigation", "count": 10, "difficulty": ["easy", "medium"]}
    # ]

    # Question count
    total_questions = models.IntegerField()
    questions_per_page = models.IntegerField(default=1)

    # Time settings
    time_limit_minutes = models.IntegerField(null=True, blank=True)
    allow_pause = models.BooleanField(default=False)
    max_pause_count = models.IntegerField(default=3)
    max_pause_duration_minutes = models.IntegerField(default=30)

    # Passing criteria
    passing_score = models.IntegerField(default=75)
    passing_type = models.CharField(
        max_length=20,
        choices=PassingType.choices,
        default=PassingType.PERCENTAGE
    )
    category_passing_scores = models.JSONField(default=dict, blank=True)
    # Example: {"air_law": 70, "meteorology": 75}

    # Attempts
    max_attempts = models.IntegerField(null=True, blank=True)
    retry_delay_hours = models.IntegerField(default=0)
    cooldown_after_fail_hours = models.IntegerField(default=24)

    # Navigation
    allow_review = models.BooleanField(default=True)
    allow_skip = models.BooleanField(default=True)
    allow_back_navigation = models.BooleanField(default=True)
    force_answer_before_next = models.BooleanField(default=False)

    # Results display
    show_correct_answers = models.BooleanField(default=False)
    show_explanation = models.BooleanField(default=True)
    show_results_immediately = models.BooleanField(default=True)
    show_score_during_exam = models.BooleanField(default=False)
    show_category_breakdown = models.BooleanField(default=True)

    # Randomization
    randomize_questions = models.BooleanField(default=True)
    randomize_options = models.BooleanField(default=True)

    # Security
    require_proctoring = models.BooleanField(default=False)
    browser_lockdown = models.BooleanField(default=False)
    prevent_copy_paste = models.BooleanField(default=True)
    require_webcam = models.BooleanField(default=False)
    require_id_verification = models.BooleanField(default=False)
    max_tab_switches = models.IntegerField(null=True, blank=True)

    # Scheduling
    available_from = models.DateTimeField(null=True, blank=True)
    available_until = models.DateTimeField(null=True, blank=True)
    scheduled_windows = models.JSONField(default=list, blank=True)
    # Example: [{"start": "2024-01-01T09:00", "end": "2024-01-01T12:00"}]

    # Status
    status = models.CharField(
        max_length=20,
        choices=ExamStatus.choices,
        default=ExamStatus.DRAFT
    )
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)

    # Statistics
    attempt_count = models.IntegerField(default=0)
    pass_count = models.IntegerField(default=0)
    fail_count = models.IntegerField(default=0)
    pass_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True
    )
    average_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True
    )
    average_duration_minutes = models.IntegerField(null=True, blank=True)

    # Feedback
    pass_message = models.TextField(blank=True, default='')
    fail_message = models.TextField(blank=True, default='')
    certificate_template_id = models.UUIDField(null=True, blank=True)

    # Settings
    settings = models.JSONField(default=dict, blank=True)

    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.UUIDField(null=True, blank=True)

    class Meta:
        db_table = 'exams'
        ordering = ['name']
        indexes = [
            models.Index(fields=['organization_id']),
            models.Index(fields=['course']),
            models.Index(fields=['exam_type']),
            models.Index(fields=['status']),
            models.Index(fields=['is_published']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['organization_id', 'code'],
                condition=models.Q(code__gt=''),
                name='unique_exam_code_per_org'
            )
        ]

    def __str__(self):
        return self.name

    @property
    def is_active(self) -> bool:
        """Check if exam is active and available."""
        if not self.is_published:
            return False

        now = timezone.now()

        if self.available_from and now < self.available_from:
            return False

        if self.available_until and now > self.available_until:
            return False

        return True

    @property
    def is_timed(self) -> bool:
        """Check if exam has time limit."""
        return self.time_limit_minutes is not None and self.time_limit_minutes > 0

    def publish(self) -> None:
        """Publish the exam."""
        if self.total_questions == 0:
            raise ValueError("Cannot publish exam without questions")

        if self.question_selection == QuestionSelection.FIXED:
            if len(self.fixed_questions) < self.total_questions:
                raise ValueError("Not enough fixed questions selected")

        self.status = ExamStatus.PUBLISHED
        self.is_published = True
        self.published_at = timezone.now()
        self.save()

    def archive(self) -> None:
        """Archive the exam."""
        self.status = ExamStatus.ARCHIVED
        self.is_published = False
        self.save()

    def check_availability(self, user_id: str) -> Dict[str, Any]:
        """Check if exam is available for a user."""
        from .attempt import ExamAttempt

        result = {
            'available': True,
            'reason': None,
            'retry_after': None
        }

        # Check if published
        if not self.is_published:
            result['available'] = False
            result['reason'] = 'Exam is not published'
            return result

        now = timezone.now()

        # Check schedule
        if self.available_from and now < self.available_from:
            result['available'] = False
            result['reason'] = 'Exam not yet available'
            result['available_from'] = self.available_from.isoformat()
            return result

        if self.available_until and now > self.available_until:
            result['available'] = False
            result['reason'] = 'Exam availability has ended'
            return result

        # Check max attempts
        if self.max_attempts:
            completed_attempts = ExamAttempt.objects.filter(
                exam=self,
                user_id=user_id,
                status__in=['completed', 'submitted']
            ).count()

            if completed_attempts >= self.max_attempts:
                result['available'] = False
                result['reason'] = 'Maximum attempts reached'
                result['attempts_used'] = completed_attempts
                result['max_attempts'] = self.max_attempts
                return result

        # Check retry delay
        if self.retry_delay_hours > 0:
            last_attempt = ExamAttempt.objects.filter(
                exam=self,
                user_id=user_id,
                status__in=['completed', 'submitted']
            ).order_by('-completed_at').first()

            if last_attempt and last_attempt.completed_at:
                from datetime import timedelta
                retry_after = last_attempt.completed_at + timedelta(hours=self.retry_delay_hours)

                if now < retry_after:
                    result['available'] = False
                    result['reason'] = 'Retry delay not elapsed'
                    result['retry_after'] = retry_after.isoformat()
                    return result

        # Check cooldown after fail
        if self.cooldown_after_fail_hours > 0:
            last_failed = ExamAttempt.objects.filter(
                exam=self,
                user_id=user_id,
                passed=False,
                status='completed'
            ).order_by('-completed_at').first()

            if last_failed and last_failed.completed_at:
                from datetime import timedelta
                cooldown_until = last_failed.completed_at + timedelta(hours=self.cooldown_after_fail_hours)

                if now < cooldown_until:
                    result['available'] = False
                    result['reason'] = 'Cooldown period after failed attempt'
                    result['retry_after'] = cooldown_until.isoformat()
                    return result

        return result

    def select_questions(self) -> List[Dict[str, Any]]:
        """Select questions for an exam attempt."""
        questions = []

        if self.question_selection == QuestionSelection.FIXED:
            # Get fixed questions in order
            for q_id in self.fixed_questions:
                try:
                    question = Question.objects.get(id=q_id, is_active=True)
                    questions.append(question.get_for_exam(self.randomize_options))
                except Question.DoesNotExist:
                    pass

        elif self.question_selection in [QuestionSelection.RANDOM, QuestionSelection.WEIGHTED]:
            # Random selection based on rules
            for rule in self.random_rules:
                query = Question.objects.filter(
                    organization_id=self.organization_id,
                    category=rule['category'],
                    is_active=True,
                    review_status='approved'
                )

                # Filter by difficulty
                if 'difficulty' in rule:
                    difficulties = rule['difficulty']
                    if isinstance(difficulties, list):
                        query = query.filter(difficulty__in=difficulties)
                    else:
                        query = query.filter(difficulty=difficulties)

                # Filter by subcategory
                if 'subcategory' in rule:
                    query = query.filter(subcategory=rule['subcategory'])

                # Filter by tags
                if 'tags' in rule:
                    query = query.filter(tags__overlap=rule['tags'])

                # Get questions
                pool = list(query)
                count = min(rule['count'], len(pool))

                if self.question_selection == QuestionSelection.WEIGHTED:
                    # Weight by difficulty score (harder questions more likely)
                    weights = [q.difficulty_score for q in pool]
                    selected = random.choices(pool, weights=weights, k=count)
                else:
                    selected = random.sample(pool, count)

                for q in selected:
                    questions.append(q.get_for_exam(self.randomize_options))

        # Randomize order if configured
        if self.randomize_questions:
            random.shuffle(questions)

        # Limit to total_questions
        return questions[:self.total_questions]

    def calculate_passing(self, results: Dict[str, Any]) -> bool:
        """Calculate if results meet passing criteria."""
        if self.passing_type == PassingType.PERCENTAGE:
            return results.get('score_percentage', 0) >= self.passing_score

        elif self.passing_type == PassingType.POINTS:
            return results.get('earned_points', 0) >= self.passing_score

        elif self.passing_type == PassingType.CATEGORY:
            # Must pass each category
            category_results = results.get('results_by_category', {})

            for category, required_score in self.category_passing_scores.items():
                cat_result = category_results.get(category, {})
                if cat_result.get('percentage', 0) < required_score:
                    return False

            return True

        return False

    def update_statistics(self) -> None:
        """Update exam statistics from attempts."""
        from .attempt import ExamAttempt

        completed = ExamAttempt.objects.filter(
            exam=self,
            status='completed'
        )

        self.attempt_count = completed.count()
        self.pass_count = completed.filter(passed=True).count()
        self.fail_count = completed.filter(passed=False).count()

        if self.attempt_count > 0:
            self.pass_rate = Decimal(
                str(round((self.pass_count / self.attempt_count) * 100, 2))
            )

            scores = completed.exclude(
                score_percentage__isnull=True
            ).values_list('score_percentage', flat=True)

            if scores:
                self.average_score = Decimal(str(round(sum(scores) / len(scores), 2)))

            durations = completed.exclude(
                time_spent_seconds__isnull=True
            ).values_list('time_spent_seconds', flat=True)

            if durations:
                self.average_duration_minutes = sum(durations) // len(durations) // 60

        self.save()

    def get_summary(self) -> Dict[str, Any]:
        """Get exam summary."""
        return {
            'id': str(self.id),
            'code': self.code,
            'name': self.name,
            'exam_type': self.exam_type,
            'total_questions': self.total_questions,
            'time_limit_minutes': self.time_limit_minutes,
            'passing_score': self.passing_score,
            'max_attempts': self.max_attempts,
            'is_published': self.is_published,
            'attempt_count': self.attempt_count,
            'pass_rate': float(self.pass_rate) if self.pass_rate else None,
            'average_score': float(self.average_score) if self.average_score else None,
        }


class ExamQuestion(models.Model):
    """
    Exam question link model.

    Links specific questions to exams with ordering.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    exam = models.ForeignKey(
        Exam,
        on_delete=models.CASCADE,
        related_name='exam_questions'
    )
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name='exam_links'
    )

    # Ordering
    sort_order = models.IntegerField(default=0)

    # Override points
    points_override = models.IntegerField(null=True, blank=True)

    # Required
    is_required = models.BooleanField(default=False)

    # Audit
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'exam_questions'
        ordering = ['sort_order']
        constraints = [
            models.UniqueConstraint(
                fields=['exam', 'question'],
                name='unique_exam_question'
            )
        ]

    def __str__(self):
        return f"{self.exam.name} - Q{self.sort_order}"

    @property
    def points(self) -> int:
        """Get points for this question."""
        return self.points_override or self.question.points
