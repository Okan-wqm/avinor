# services/theory-service/src/apps/core/models/question.py
"""
Question Models

Models for question bank management.
"""

import uuid
from decimal import Decimal
from typing import Dict, Any, List, Optional

from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.utils import timezone


class QuestionType(models.TextChoices):
    """Question type choices."""
    MULTIPLE_CHOICE = 'multiple_choice', 'Multiple Choice'
    TRUE_FALSE = 'true_false', 'True/False'
    MULTI_SELECT = 'multi_select', 'Multiple Selection'
    FILL_BLANK = 'fill_blank', 'Fill in the Blank'
    MATCHING = 'matching', 'Matching'
    ORDERING = 'ordering', 'Ordering/Sequence'
    SHORT_ANSWER = 'short_answer', 'Short Answer'
    HOTSPOT = 'hotspot', 'Hotspot/Image Click'


class Difficulty(models.TextChoices):
    """Question difficulty choices."""
    EASY = 'easy', 'Easy'
    MEDIUM = 'medium', 'Medium'
    HARD = 'hard', 'Hard'
    EXPERT = 'expert', 'Expert'


class ReviewStatus(models.TextChoices):
    """Question review status choices."""
    PENDING = 'pending', 'Pending Review'
    APPROVED = 'approved', 'Approved'
    REJECTED = 'rejected', 'Rejected'
    NEEDS_REVISION = 'needs_revision', 'Needs Revision'


class Question(models.Model):
    """
    Question model.

    Represents a question in the question bank.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    organization_id = models.UUIDField(db_index=True)

    # Categorization
    category = models.CharField(max_length=50, db_index=True)
    subcategory = models.CharField(max_length=100, blank=True, default='')
    topic = models.CharField(max_length=255, blank=True, default='')
    tags = ArrayField(
        models.CharField(max_length=50),
        default=list,
        blank=True
    )

    # Reference
    reference_code = models.CharField(max_length=100, blank=True, default='')
    learning_objective = models.CharField(max_length=255, blank=True, default='')
    learning_objective_id = models.CharField(max_length=50, blank=True, default='')

    # Question type
    question_type = models.CharField(
        max_length=50,
        choices=QuestionType.choices,
        default=QuestionType.MULTIPLE_CHOICE
    )

    # Question content
    question_text = models.TextField()
    question_html = models.TextField(blank=True, default='')

    # Media
    image_url = models.URLField(max_length=500, blank=True, default='')
    image_alt_text = models.CharField(max_length=255, blank=True, default='')
    audio_url = models.URLField(max_length=500, blank=True, default='')
    video_url = models.URLField(max_length=500, blank=True, default='')

    # Options (for multiple choice, etc.)
    options = models.JSONField(default=list)
    # Example for multiple_choice:
    # [
    #   {"id": "a", "text": "Answer A", "image_url": null},
    #   {"id": "b", "text": "Answer B", "image_url": null},
    #   {"id": "c", "text": "Answer C", "image_url": null},
    #   {"id": "d", "text": "Answer D", "image_url": null}
    # ]

    # Correct answer
    correct_answer = models.JSONField()
    # Examples:
    # multiple_choice: {"option_id": "a"}
    # multi_select: {"option_ids": ["a", "c"]}
    # true_false: {"value": true}
    # fill_blank: {"answers": ["answer1", "answer2"], "case_sensitive": false}
    # matching: {"pairs": [{"left": "1", "right": "a"}, ...]}
    # ordering: {"sequence": ["a", "c", "b", "d"]}

    # Explanation
    explanation = models.TextField(blank=True, default='')
    explanation_html = models.TextField(blank=True, default='')
    explanation_image_url = models.URLField(max_length=500, blank=True, default='')

    # Hint
    hint = models.TextField(blank=True, default='')
    show_hint_after_wrong = models.BooleanField(default=False)

    # Difficulty
    difficulty = models.CharField(
        max_length=20,
        choices=Difficulty.choices,
        default=Difficulty.MEDIUM
    )
    difficulty_score = models.IntegerField(default=50)  # 1-100

    # Points
    points = models.IntegerField(default=1)
    negative_points = models.IntegerField(default=0)
    partial_credit = models.BooleanField(default=False)

    # Time
    time_limit_seconds = models.IntegerField(null=True, blank=True)
    recommended_time_seconds = models.IntegerField(null=True, blank=True)

    # Statistics
    times_asked = models.IntegerField(default=0)
    times_correct = models.IntegerField(default=0)
    times_incorrect = models.IntegerField(default=0)
    times_skipped = models.IntegerField(default=0)
    success_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True
    )
    average_time_seconds = models.IntegerField(null=True, blank=True)
    discrimination_index = models.DecimalField(
        max_digits=4,
        decimal_places=3,
        null=True,
        blank=True
    )

    # Option statistics
    option_stats = models.JSONField(default=dict, blank=True)
    # Example: {"a": 150, "b": 30, "c": 10, "d": 10}

    # Flags
    is_active = models.BooleanField(default=True)
    is_pilot_question = models.BooleanField(default=False)  # Being tested
    is_flagged = models.BooleanField(default=False)  # Needs attention
    flag_reason = models.TextField(blank=True, default='')

    # Review
    review_status = models.CharField(
        max_length=20,
        choices=ReviewStatus.choices,
        default=ReviewStatus.PENDING
    )
    reviewed_by = models.UUIDField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_notes = models.TextField(blank=True, default='')

    # Source
    source = models.CharField(max_length=255, blank=True, default='')
    source_reference = models.CharField(max_length=255, blank=True, default='')

    # Version
    version = models.IntegerField(default=1)
    previous_version_id = models.UUIDField(null=True, blank=True)

    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.UUIDField(null=True, blank=True)
    updated_by = models.UUIDField(null=True, blank=True)

    class Meta:
        db_table = 'questions'
        ordering = ['category', 'subcategory', '-created_at']
        indexes = [
            models.Index(fields=['organization_id']),
            models.Index(fields=['category']),
            models.Index(fields=['difficulty']),
            models.Index(fields=['question_type']),
            models.Index(fields=['is_active']),
            models.Index(fields=['review_status']),
        ]

    def __str__(self):
        text = self.question_text[:50]
        if len(self.question_text) > 50:
            text += '...'
        return f"{self.category}: {text}"

    @property
    def has_media(self) -> bool:
        """Check if question has any media."""
        return bool(self.image_url or self.audio_url or self.video_url)

    @property
    def is_approved(self) -> bool:
        """Check if question is approved for use."""
        return self.review_status == ReviewStatus.APPROVED

    @property
    def answer_rate(self) -> Optional[float]:
        """Calculate answer rate (answered vs skipped)."""
        total = self.times_asked + self.times_skipped
        if total == 0:
            return None
        return round((self.times_asked / total) * 100, 2)

    def update_statistics(self, is_correct: bool, time_seconds: int = None, selected_option: str = None) -> None:
        """Update question statistics after an answer."""
        self.times_asked += 1

        if is_correct:
            self.times_correct += 1
        else:
            self.times_incorrect += 1

        # Update success rate
        if self.times_asked > 0:
            self.success_rate = Decimal(
                str(round((self.times_correct / self.times_asked) * 100, 2))
            )

        # Update average time
        if time_seconds:
            if self.average_time_seconds is None:
                self.average_time_seconds = time_seconds
            else:
                # Running average
                total_time = self.average_time_seconds * (self.times_asked - 1) + time_seconds
                self.average_time_seconds = total_time // self.times_asked

        # Update option statistics
        if selected_option:
            if not self.option_stats:
                self.option_stats = {}
            self.option_stats[selected_option] = self.option_stats.get(selected_option, 0) + 1

        # Auto-adjust difficulty based on success rate
        self._update_difficulty_score()

        self.save()

    def _update_difficulty_score(self) -> None:
        """Automatically adjust difficulty score based on statistics."""
        if self.times_asked < 10:
            return  # Not enough data

        # Invert success rate: lower success = higher difficulty
        if self.success_rate is not None:
            # Map success rate (0-100) to difficulty score (100-0)
            self.difficulty_score = int(100 - float(self.success_rate))

    def check_answer(self, given_answer: Any) -> Dict[str, Any]:
        """Check if given answer is correct."""
        if self.question_type == QuestionType.MULTIPLE_CHOICE:
            is_correct = given_answer == self.correct_answer.get('option_id')
            return {
                'correct': is_correct,
                'correct_answer': self.correct_answer.get('option_id'),
                'explanation': self.explanation if not is_correct else None
            }

        elif self.question_type == QuestionType.TRUE_FALSE:
            is_correct = given_answer == self.correct_answer.get('value')
            return {
                'correct': is_correct,
                'correct_answer': self.correct_answer.get('value'),
                'explanation': self.explanation if not is_correct else None
            }

        elif self.question_type == QuestionType.MULTI_SELECT:
            correct_ids = set(self.correct_answer.get('option_ids', []))
            given_ids = set(given_answer if isinstance(given_answer, list) else [])

            if self.partial_credit:
                # Calculate partial score
                correct_selected = len(correct_ids & given_ids)
                incorrect_selected = len(given_ids - correct_ids)
                total_correct = len(correct_ids)

                if total_correct > 0:
                    score = max(0, (correct_selected - incorrect_selected) / total_correct)
                else:
                    score = 0

                return {
                    'correct': score == 1.0,
                    'partial_score': round(score, 2),
                    'correct_answer': list(correct_ids),
                    'explanation': self.explanation if score < 1.0 else None
                }
            else:
                is_correct = correct_ids == given_ids
                return {
                    'correct': is_correct,
                    'correct_answer': list(correct_ids),
                    'explanation': self.explanation if not is_correct else None
                }

        elif self.question_type == QuestionType.FILL_BLANK:
            correct_answers = self.correct_answer.get('answers', [])
            case_sensitive = self.correct_answer.get('case_sensitive', False)

            if case_sensitive:
                is_correct = given_answer in correct_answers
            else:
                is_correct = given_answer.lower() in [a.lower() for a in correct_answers]

            return {
                'correct': is_correct,
                'correct_answer': correct_answers[0] if correct_answers else None,
                'explanation': self.explanation if not is_correct else None
            }

        elif self.question_type == QuestionType.MATCHING:
            correct_pairs = self.correct_answer.get('pairs', [])
            given_pairs = given_answer if isinstance(given_answer, list) else []

            if self.partial_credit:
                correct_count = 0
                for given_pair in given_pairs:
                    for correct_pair in correct_pairs:
                        if (given_pair.get('left') == correct_pair.get('left') and
                            given_pair.get('right') == correct_pair.get('right')):
                            correct_count += 1
                            break

                score = correct_count / len(correct_pairs) if correct_pairs else 0
                return {
                    'correct': score == 1.0,
                    'partial_score': round(score, 2),
                    'correct_answer': correct_pairs,
                    'explanation': self.explanation if score < 1.0 else None
                }
            else:
                # All pairs must match
                is_correct = len(given_pairs) == len(correct_pairs)
                if is_correct:
                    for given_pair in given_pairs:
                        found = False
                        for correct_pair in correct_pairs:
                            if (given_pair.get('left') == correct_pair.get('left') and
                                given_pair.get('right') == correct_pair.get('right')):
                                found = True
                                break
                        if not found:
                            is_correct = False
                            break

                return {
                    'correct': is_correct,
                    'correct_answer': correct_pairs,
                    'explanation': self.explanation if not is_correct else None
                }

        elif self.question_type == QuestionType.ORDERING:
            correct_sequence = self.correct_answer.get('sequence', [])
            is_correct = given_answer == correct_sequence

            if not is_correct and self.partial_credit:
                # Calculate how many items are in correct position
                correct_positions = sum(
                    1 for i, item in enumerate(given_answer)
                    if i < len(correct_sequence) and item == correct_sequence[i]
                )
                score = correct_positions / len(correct_sequence) if correct_sequence else 0
                return {
                    'correct': False,
                    'partial_score': round(score, 2),
                    'correct_answer': correct_sequence,
                    'explanation': self.explanation
                }

            return {
                'correct': is_correct,
                'correct_answer': correct_sequence,
                'explanation': self.explanation if not is_correct else None
            }

        return {'correct': False, 'explanation': 'Unknown question type'}

    def get_for_exam(self, randomize_options: bool = True) -> Dict[str, Any]:
        """Get question formatted for exam (without correct answer)."""
        options = list(self.options) if self.options else []

        if randomize_options and self.question_type in [
            QuestionType.MULTIPLE_CHOICE,
            QuestionType.MULTI_SELECT
        ]:
            import random
            random.shuffle(options)

        return {
            'id': str(self.id),
            'type': self.question_type,
            'text': self.question_text,
            'html': self.question_html or None,
            'image_url': self.image_url or None,
            'audio_url': self.audio_url or None,
            'options': [
                {'id': opt['id'], 'text': opt['text'], 'image_url': opt.get('image_url')}
                for opt in options
            ] if options else None,
            'points': self.points,
            'time_limit_seconds': self.time_limit_seconds,
            'hint': self.hint if self.show_hint_after_wrong else None,
        }

    def clone(self) -> 'Question':
        """Create a new version of this question."""
        new_question = Question(
            organization_id=self.organization_id,
            category=self.category,
            subcategory=self.subcategory,
            topic=self.topic,
            tags=self.tags.copy(),
            reference_code=self.reference_code,
            learning_objective=self.learning_objective,
            question_type=self.question_type,
            question_text=self.question_text,
            question_html=self.question_html,
            image_url=self.image_url,
            options=self.options.copy() if self.options else [],
            correct_answer=self.correct_answer.copy(),
            explanation=self.explanation,
            explanation_html=self.explanation_html,
            difficulty=self.difficulty,
            difficulty_score=self.difficulty_score,
            points=self.points,
            time_limit_seconds=self.time_limit_seconds,
            review_status=ReviewStatus.PENDING,
            version=self.version + 1,
            previous_version_id=self.id,
            created_by=self.created_by,
        )
        return new_question


class QuestionReview(models.Model):
    """
    Question review model.

    Tracks review history for questions.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name='reviews'
    )

    # Review
    reviewer_id = models.UUIDField()
    status = models.CharField(
        max_length=20,
        choices=ReviewStatus.choices
    )
    notes = models.TextField(blank=True, default='')

    # Changes suggested
    suggested_changes = models.JSONField(default=dict, blank=True)

    # Audit
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'question_reviews'
        ordering = ['-created_at']

    def __str__(self):
        return f"Review for {self.question.id} - {self.status}"
