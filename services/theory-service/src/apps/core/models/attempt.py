# services/theory-service/src/apps/core/models/attempt.py
"""
Exam Attempt Models

Models for tracking exam attempts and answers.
"""

import uuid
from decimal import Decimal
from typing import Dict, Any, List, Optional
from datetime import timedelta

from django.db import models
from django.utils import timezone

from .exam import Exam
from .question import Question


class AttemptStatus(models.TextChoices):
    """Attempt status choices."""
    IN_PROGRESS = 'in_progress', 'In Progress'
    PAUSED = 'paused', 'Paused'
    SUBMITTED = 'submitted', 'Submitted'
    COMPLETED = 'completed', 'Completed'
    ABANDONED = 'abandoned', 'Abandoned'
    INVALIDATED = 'invalidated', 'Invalidated'
    TIMED_OUT = 'timed_out', 'Timed Out'


class GradeLetter(models.TextChoices):
    """Grade letter choices."""
    A_PLUS = 'A+', 'A+'
    A = 'A', 'A'
    A_MINUS = 'A-', 'A-'
    B_PLUS = 'B+', 'B+'
    B = 'B', 'B'
    B_MINUS = 'B-', 'B-'
    C_PLUS = 'C+', 'C+'
    C = 'C', 'C'
    C_MINUS = 'C-', 'C-'
    D = 'D', 'D'
    F = 'F', 'F'


class ExamAttempt(models.Model):
    """
    Exam attempt model.

    Tracks a single attempt at an exam by a user.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    organization_id = models.UUIDField(db_index=True)

    # Relationships
    exam = models.ForeignKey(
        Exam,
        on_delete=models.PROTECT,
        related_name='attempts'
    )
    user_id = models.UUIDField(db_index=True)
    enrollment_id = models.UUIDField(null=True, blank=True)

    # Attempt info
    attempt_number = models.IntegerField(default=1)

    # Timing
    started_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    time_spent_seconds = models.IntegerField(default=0)
    time_limit_at = models.DateTimeField(null=True, blank=True)

    # Pause tracking
    pause_count = models.IntegerField(default=0)
    total_pause_seconds = models.IntegerField(default=0)
    last_paused_at = models.DateTimeField(null=True, blank=True)

    # Status
    status = models.CharField(
        max_length=20,
        choices=AttemptStatus.choices,
        default=AttemptStatus.IN_PROGRESS
    )

    # Questions (snapshot at start)
    questions = models.JSONField(default=list)
    # Example:
    # [
    #   {"question_id": "uuid", "order": 1, "points": 1},
    #   {"question_id": "uuid", "order": 2, "points": 2}
    # ]

    # Current position
    current_question_index = models.IntegerField(default=0)

    # Answers
    answers = models.JSONField(default=dict)
    # Example:
    # {
    #   "question_id": {
    #     "selected": "a",
    #     "answered_at": "2024-01-01T10:00:00Z",
    #     "time_spent_seconds": 45,
    #     "flagged": false
    #   }
    # }

    # Scoring
    total_points = models.IntegerField(default=0)
    earned_points = models.IntegerField(default=0)
    score_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True
    )

    # Results
    passed = models.BooleanField(null=True, blank=True)
    grade = models.CharField(
        max_length=10,
        choices=GradeLetter.choices,
        blank=True,
        default=''
    )

    # Detailed results
    results_by_category = models.JSONField(default=dict, blank=True)
    # Example: {"air_law": {"correct": 8, "total": 10, "percentage": 80}}

    correct_count = models.IntegerField(default=0)
    incorrect_count = models.IntegerField(default=0)
    unanswered_count = models.IntegerField(default=0)
    partial_count = models.IntegerField(default=0)

    # Question-level results
    question_results = models.JSONField(default=dict, blank=True)
    # Example: {
    #   "question_id": {
    #     "correct": true,
    #     "points_earned": 1,
    #     "time_spent": 30
    #   }
    # }

    # Client info
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, default='')
    device_info = models.JSONField(default=dict, blank=True)

    # Proctoring
    proctoring_enabled = models.BooleanField(default=False)
    proctoring_data = models.JSONField(default=dict, blank=True)
    flagged_events = models.JSONField(default=list, blank=True)
    # Example: [
    #   {"type": "tab_switch", "timestamp": "...", "count": 3},
    #   {"type": "face_not_visible", "timestamp": "...", "duration": 10}
    # ]

    # Review
    reviewed_by = models.UUIDField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_notes = models.TextField(blank=True, default='')
    score_adjusted = models.BooleanField(default=False)
    original_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True
    )

    # Certificate
    certificate_issued = models.BooleanField(default=False)
    certificate_id = models.UUIDField(null=True, blank=True)

    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'exam_attempts'
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['exam', 'user_id']),
            models.Index(fields=['user_id']),
            models.Index(fields=['status']),
            models.Index(fields=['started_at']),
            models.Index(fields=['completed_at']),
        ]

    def __str__(self):
        return f"{self.exam.name} - Attempt {self.attempt_number} by {self.user_id}"

    @property
    def is_active(self) -> bool:
        """Check if attempt is still active."""
        return self.status in [AttemptStatus.IN_PROGRESS, AttemptStatus.PAUSED]

    @property
    def is_completed(self) -> bool:
        """Check if attempt is completed."""
        return self.status in [AttemptStatus.COMPLETED, AttemptStatus.SUBMITTED]

    @property
    def time_remaining_seconds(self) -> Optional[int]:
        """Calculate remaining time in seconds."""
        if not self.exam.time_limit_minutes:
            return None

        if self.status != AttemptStatus.IN_PROGRESS:
            return 0

        if self.time_limit_at:
            remaining = (self.time_limit_at - timezone.now()).total_seconds()
            return max(0, int(remaining))

        total_allowed = self.exam.time_limit_minutes * 60
        elapsed = self.time_spent_seconds

        if self.status == AttemptStatus.IN_PROGRESS and self.started_at:
            # Add current session time
            current_session = (timezone.now() - self.started_at).total_seconds()
            elapsed += int(current_session)

        return max(0, total_allowed - elapsed)

    @property
    def progress_percentage(self) -> float:
        """Calculate progress through exam."""
        if not self.questions:
            return 0

        answered = len(self.answers)
        total = len(self.questions)

        return round((answered / total) * 100, 1)

    @property
    def duration_minutes(self) -> int:
        """Get total duration in minutes."""
        return self.time_spent_seconds // 60

    def start(self) -> None:
        """Start the exam attempt."""
        if self.exam.time_limit_minutes:
            self.time_limit_at = timezone.now() + timedelta(
                minutes=self.exam.time_limit_minutes
            )
        self.status = AttemptStatus.IN_PROGRESS
        self.save()

    def pause(self) -> None:
        """Pause the exam attempt."""
        if not self.exam.allow_pause:
            raise ValueError("Pausing is not allowed for this exam")

        if self.pause_count >= self.exam.max_pause_count:
            raise ValueError("Maximum pause count reached")

        # Save current time spent
        if self.started_at:
            session_time = (timezone.now() - self.started_at).total_seconds()
            self.time_spent_seconds += int(session_time)

        self.status = AttemptStatus.PAUSED
        self.pause_count += 1
        self.last_paused_at = timezone.now()
        self.save()

    def resume(self) -> None:
        """Resume the exam attempt."""
        if self.status != AttemptStatus.PAUSED:
            raise ValueError("Attempt is not paused")

        if self.last_paused_at:
            pause_duration = (timezone.now() - self.last_paused_at).total_seconds()

            # Check max pause duration
            if pause_duration > self.exam.max_pause_duration_minutes * 60:
                self.status = AttemptStatus.ABANDONED
                self.save()
                raise ValueError("Pause duration exceeded, attempt abandoned")

            self.total_pause_seconds += int(pause_duration)

        self.status = AttemptStatus.IN_PROGRESS
        self.started_at = timezone.now()  # Reset session start
        self.save()

    def save_answer(
        self,
        question_id: str,
        answer: Any,
        time_spent_seconds: int = 0,
        flagged: bool = False
    ) -> None:
        """Save an answer for a question."""
        if not self.is_active:
            raise ValueError("Cannot save answer to inactive attempt")

        # Check time limit
        if self.time_remaining_seconds == 0:
            self.status = AttemptStatus.TIMED_OUT
            self.save()
            raise ValueError("Time limit exceeded")

        self.answers[question_id] = {
            'selected': answer,
            'answered_at': timezone.now().isoformat(),
            'time_spent_seconds': time_spent_seconds,
            'flagged': flagged
        }
        self.save()

    def flag_question(self, question_id: str, flagged: bool = True) -> None:
        """Flag or unflag a question for review."""
        if question_id in self.answers:
            self.answers[question_id]['flagged'] = flagged
        else:
            self.answers[question_id] = {
                'flagged': flagged,
                'answered_at': timezone.now().isoformat()
            }
        self.save()

    def submit(self) -> Dict[str, Any]:
        """Submit the exam and calculate results."""
        if self.status == AttemptStatus.COMPLETED:
            raise ValueError("Attempt already completed")

        # Calculate final time spent
        if self.started_at and self.status == AttemptStatus.IN_PROGRESS:
            session_time = (timezone.now() - self.started_at).total_seconds()
            self.time_spent_seconds += int(session_time)

        self.submitted_at = timezone.now()
        self.status = AttemptStatus.SUBMITTED

        # Calculate results
        results = self._calculate_results()

        # Update fields
        self.earned_points = results['earned_points']
        self.score_percentage = Decimal(str(results['score_percentage']))
        self.correct_count = results['correct_count']
        self.incorrect_count = results['incorrect_count']
        self.unanswered_count = results['unanswered_count']
        self.partial_count = results.get('partial_count', 0)
        self.results_by_category = results['by_category']
        self.question_results = results['question_results']

        # Determine pass/fail
        self.passed = self.exam.calculate_passing(results)

        # Calculate grade
        self.grade = self._calculate_grade()

        # Mark as completed
        self.status = AttemptStatus.COMPLETED
        self.completed_at = timezone.now()

        self.save()

        # Update exam statistics
        self.exam.update_statistics()

        return self.get_results()

    def _calculate_results(self) -> Dict[str, Any]:
        """Calculate exam results."""
        earned_points = 0
        correct_count = 0
        incorrect_count = 0
        partial_count = 0
        by_category = {}
        question_results = {}

        # Get all questions
        question_ids = [q['question_id'] for q in self.questions]
        questions_map = {
            str(q.id): q
            for q in Question.objects.filter(id__in=question_ids)
        }

        for q_data in self.questions:
            q_id = q_data['question_id']
            question = questions_map.get(q_id)

            if not question:
                continue

            # Initialize category stats
            cat = question.category
            if cat not in by_category:
                by_category[cat] = {
                    'correct': 0,
                    'incorrect': 0,
                    'total': 0,
                    'points_earned': 0,
                    'points_possible': 0
                }

            by_category[cat]['total'] += 1
            by_category[cat]['points_possible'] += question.points

            # Check answer
            answer_data = self.answers.get(q_id)

            if not answer_data or 'selected' not in answer_data:
                question_results[q_id] = {
                    'correct': False,
                    'unanswered': True,
                    'points_earned': 0,
                    'time_spent_seconds': 0
                }
                by_category[cat]['incorrect'] += 1
                continue

            result = question.check_answer(answer_data['selected'])
            time_spent = answer_data.get('time_spent_seconds', 0)

            if result.get('correct'):
                points = q_data.get('points', question.points)
                earned_points += points
                correct_count += 1
                by_category[cat]['correct'] += 1
                by_category[cat]['points_earned'] += points

                question_results[q_id] = {
                    'correct': True,
                    'points_earned': points,
                    'time_spent_seconds': time_spent
                }

            elif 'partial_score' in result:
                partial_points = int(question.points * result['partial_score'])
                earned_points += partial_points
                partial_count += 1
                by_category[cat]['points_earned'] += partial_points

                question_results[q_id] = {
                    'correct': False,
                    'partial': True,
                    'partial_score': result['partial_score'],
                    'points_earned': partial_points,
                    'time_spent_seconds': time_spent
                }

            else:
                incorrect_count += 1
                by_category[cat]['incorrect'] += 1

                question_results[q_id] = {
                    'correct': False,
                    'points_earned': 0,
                    'time_spent_seconds': time_spent
                }

            # Update question statistics
            question.update_statistics(
                is_correct=result.get('correct', False),
                time_seconds=time_spent,
                selected_option=answer_data['selected'] if isinstance(answer_data['selected'], str) else None
            )

        # Calculate category percentages
        for cat in by_category:
            total = by_category[cat]['total']
            if total > 0:
                by_category[cat]['percentage'] = round(
                    (by_category[cat]['correct'] / total) * 100, 2
                )

        # Calculate overall score
        unanswered_count = len(self.questions) - len([
            a for a in self.answers.values()
            if 'selected' in a
        ])

        score_percentage = 0
        if self.total_points > 0:
            score_percentage = round((earned_points / self.total_points) * 100, 2)

        return {
            'earned_points': earned_points,
            'total_points': self.total_points,
            'score_percentage': score_percentage,
            'correct_count': correct_count,
            'incorrect_count': incorrect_count,
            'unanswered_count': unanswered_count,
            'partial_count': partial_count,
            'by_category': by_category,
            'question_results': question_results
        }

    def _calculate_grade(self) -> str:
        """Calculate letter grade from score."""
        if self.score_percentage is None:
            return ''

        score = float(self.score_percentage)

        if score >= 97:
            return GradeLetter.A_PLUS
        elif score >= 93:
            return GradeLetter.A
        elif score >= 90:
            return GradeLetter.A_MINUS
        elif score >= 87:
            return GradeLetter.B_PLUS
        elif score >= 83:
            return GradeLetter.B
        elif score >= 80:
            return GradeLetter.B_MINUS
        elif score >= 77:
            return GradeLetter.C_PLUS
        elif score >= 73:
            return GradeLetter.C
        elif score >= 70:
            return GradeLetter.C_MINUS
        elif score >= 60:
            return GradeLetter.D
        else:
            return GradeLetter.F

    def get_results(self, include_answers: bool = False) -> Dict[str, Any]:
        """Get formatted exam results."""
        result = {
            'attempt_id': str(self.id),
            'exam_id': str(self.exam.id),
            'exam_name': self.exam.name,
            'status': self.status,
            'started_at': self.started_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'time_spent_minutes': self.duration_minutes,
            'total_questions': len(self.questions),
            'correct_count': self.correct_count,
            'incorrect_count': self.incorrect_count,
            'unanswered_count': self.unanswered_count,
            'earned_points': self.earned_points,
            'total_points': self.total_points,
            'score_percentage': float(self.score_percentage) if self.score_percentage else 0,
            'passed': self.passed,
            'grade': self.grade,
            'passing_score': self.exam.passing_score,
        }

        if self.exam.show_category_breakdown:
            result['results_by_category'] = self.results_by_category

        if include_answers and self.exam.show_correct_answers:
            result['question_results'] = self._get_detailed_question_results()

        return result

    def _get_detailed_question_results(self) -> List[Dict[str, Any]]:
        """Get detailed results for each question."""
        detailed = []

        question_ids = [q['question_id'] for q in self.questions]
        questions_map = {
            str(q.id): q
            for q in Question.objects.filter(id__in=question_ids)
        }

        for q_data in self.questions:
            q_id = q_data['question_id']
            question = questions_map.get(q_id)

            if not question:
                continue

            answer_data = self.answers.get(q_id, {})
            result_data = self.question_results.get(q_id, {})

            item = {
                'question_id': q_id,
                'order': q_data['order'],
                'question_text': question.question_text,
                'question_type': question.question_type,
                'your_answer': answer_data.get('selected'),
                'correct_answer': question.correct_answer,
                'is_correct': result_data.get('correct', False),
                'points_earned': result_data.get('points_earned', 0),
                'points_possible': question.points,
            }

            if self.exam.show_explanation:
                item['explanation'] = question.explanation

            detailed.append(item)

        return detailed

    def add_proctoring_event(self, event_type: str, data: Dict = None) -> None:
        """Add a proctoring event."""
        event = {
            'type': event_type,
            'timestamp': timezone.now().isoformat(),
            'data': data or {}
        }
        self.flagged_events.append(event)
        self.save()

    def invalidate(self, reason: str, reviewer_id: str = None) -> None:
        """Invalidate the attempt."""
        self.status = AttemptStatus.INVALIDATED
        self.review_notes = reason
        if reviewer_id:
            self.reviewed_by = reviewer_id
            self.reviewed_at = timezone.now()
        self.save()


class AttemptAnswer(models.Model):
    """
    Individual answer model.

    Detailed tracking of each answer (optional, for audit purposes).
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    attempt = models.ForeignKey(
        ExamAttempt,
        on_delete=models.CASCADE,
        related_name='attempt_answers'
    )
    question_id = models.UUIDField()

    # Answer
    selected_answer = models.JSONField()
    time_spent_seconds = models.IntegerField(default=0)

    # Result
    is_correct = models.BooleanField(null=True, blank=True)
    points_earned = models.IntegerField(default=0)
    partial_score = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        null=True,
        blank=True
    )

    # Tracking
    flagged = models.BooleanField(default=False)
    changed_count = models.IntegerField(default=0)

    # Audit
    answered_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'attempt_answers'
        ordering = ['answered_at']
        constraints = [
            models.UniqueConstraint(
                fields=['attempt', 'question_id'],
                name='unique_attempt_answer'
            )
        ]

    def __str__(self):
        return f"Answer for {self.question_id} in {self.attempt.id}"
