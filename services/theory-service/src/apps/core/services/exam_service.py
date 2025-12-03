# services/theory-service/src/apps/core/services/exam_service.py
"""
Exam Service

Business logic for exam management and execution.
"""

import logging
from typing import Dict, Any, List, Optional
from uuid import UUID
from decimal import Decimal

from django.db import transaction
from django.db.models import Q, Avg, Count
from django.utils import timezone

from ..models import (
    Exam,
    ExamQuestion,
    ExamAttempt,
    Question,
    ExamType,
    ExamStatus,
    AttemptStatus,
)

logger = logging.getLogger(__name__)


class ExamService:
    """Service for managing exams and exam attempts."""

    # =========================================================================
    # EXAM MANAGEMENT
    # =========================================================================

    @staticmethod
    def get_exams(
        organization_id: str,
        course_id: str = None,
        exam_type: str = None,
        status: str = None,
        is_published: bool = None,
    ) -> List[Exam]:
        """
        Get exams with optional filtering.

        Args:
            organization_id: Organization ID
            course_id: Filter by course
            exam_type: Filter by exam type
            status: Filter by status
            is_published: Filter by published state

        Returns:
            List of exams
        """
        queryset = Exam.objects.filter(organization_id=organization_id)

        if course_id:
            queryset = queryset.filter(course_id=course_id)

        if exam_type:
            queryset = queryset.filter(exam_type=exam_type)

        if status:
            queryset = queryset.filter(status=status)

        if is_published is not None:
            queryset = queryset.filter(is_published=is_published)

        return queryset.order_by('name')

    @staticmethod
    @transaction.atomic
    def create_exam(
        organization_id: str,
        name: str,
        total_questions: int,
        created_by: str = None,
        **kwargs
    ) -> Exam:
        """
        Create a new exam.

        Args:
            organization_id: Organization ID
            name: Exam name
            total_questions: Number of questions
            created_by: User ID who created
            **kwargs: Additional fields

        Returns:
            Created exam
        """
        exam = Exam.objects.create(
            organization_id=organization_id,
            name=name,
            total_questions=total_questions,
            created_by=created_by,
            **kwargs
        )

        logger.info(f"Created exam: {exam.id} - {exam.name}")

        return exam

    @staticmethod
    def get_exam(
        exam_id: str,
        organization_id: str = None
    ) -> Exam:
        """
        Get exam by ID.

        Args:
            exam_id: Exam ID
            organization_id: Optional organization filter

        Returns:
            Exam instance
        """
        filters = {'id': exam_id}
        if organization_id:
            filters['organization_id'] = organization_id

        return Exam.objects.get(**filters)

    @staticmethod
    @transaction.atomic
    def update_exam(
        exam_id: str,
        organization_id: str,
        **updates
    ) -> Exam:
        """
        Update an exam.

        Args:
            exam_id: Exam ID
            organization_id: Organization ID
            **updates: Fields to update

        Returns:
            Updated exam
        """
        exam = Exam.objects.select_for_update().get(
            id=exam_id,
            organization_id=organization_id
        )

        # Don't allow certain updates on published exams
        if exam.is_published:
            restricted_fields = ['total_questions', 'passing_score', 'question_selection']
            for field in restricted_fields:
                if field in updates:
                    raise ValueError(
                        f"Cannot change '{field}' on published exam"
                    )

        for field, value in updates.items():
            if hasattr(exam, field):
                setattr(exam, field, value)

        exam.save()

        logger.info(f"Updated exam: {exam.id}")

        return exam

    @staticmethod
    @transaction.atomic
    def publish_exam(
        exam_id: str,
        organization_id: str
    ) -> Exam:
        """
        Publish an exam.

        Args:
            exam_id: Exam ID
            organization_id: Organization ID

        Returns:
            Published exam
        """
        exam = Exam.objects.select_for_update().get(
            id=exam_id,
            organization_id=organization_id
        )

        exam.publish()

        logger.info(f"Published exam: {exam.id}")

        return exam

    @staticmethod
    @transaction.atomic
    def archive_exam(
        exam_id: str,
        organization_id: str
    ) -> Exam:
        """
        Archive an exam.

        Args:
            exam_id: Exam ID
            organization_id: Organization ID

        Returns:
            Archived exam
        """
        exam = Exam.objects.select_for_update().get(
            id=exam_id,
            organization_id=organization_id
        )

        exam.archive()

        logger.info(f"Archived exam: {exam.id}")

        return exam

    @staticmethod
    @transaction.atomic
    def add_fixed_questions(
        exam_id: str,
        organization_id: str,
        question_ids: List[str]
    ) -> Exam:
        """
        Add fixed questions to an exam.

        Args:
            exam_id: Exam ID
            organization_id: Organization ID
            question_ids: List of question IDs

        Returns:
            Updated exam
        """
        exam = Exam.objects.select_for_update().get(
            id=exam_id,
            organization_id=organization_id
        )

        # Validate questions exist and belong to org
        for q_id in question_ids:
            Question.objects.get(
                id=q_id,
                organization_id=organization_id,
                is_active=True
            )

        exam.fixed_questions = [UUID(q) for q in question_ids]
        exam.save()

        logger.info(f"Added {len(question_ids)} fixed questions to exam {exam.id}")

        return exam

    @staticmethod
    @transaction.atomic
    def set_random_rules(
        exam_id: str,
        organization_id: str,
        rules: List[Dict]
    ) -> Exam:
        """
        Set random selection rules for an exam.

        Args:
            exam_id: Exam ID
            organization_id: Organization ID
            rules: List of selection rules

        Returns:
            Updated exam
        """
        exam = Exam.objects.select_for_update().get(
            id=exam_id,
            organization_id=organization_id
        )

        # Validate rules
        total_count = sum(rule.get('count', 0) for rule in rules)

        # Validate categories have enough questions
        for rule in rules:
            query = Question.objects.filter(
                organization_id=organization_id,
                category=rule['category'],
                is_active=True,
                review_status='approved'
            )

            if 'difficulty' in rule:
                difficulties = rule['difficulty']
                if isinstance(difficulties, list):
                    query = query.filter(difficulty__in=difficulties)
                else:
                    query = query.filter(difficulty=difficulties)

            available = query.count()
            if available < rule['count']:
                raise ValueError(
                    f"Not enough questions in category '{rule['category']}': "
                    f"need {rule['count']}, have {available}"
                )

        exam.random_rules = rules
        exam.save()

        logger.info(f"Set random rules for exam {exam.id}")

        return exam

    # =========================================================================
    # EXAM EXECUTION
    # =========================================================================

    @staticmethod
    @transaction.atomic
    def start_exam(
        exam_id: str,
        user_id: str,
        organization_id: str,
        ip_address: str = None,
        user_agent: str = None,
        enrollment_id: str = None
    ) -> Dict[str, Any]:
        """
        Start an exam attempt.

        Args:
            exam_id: Exam ID
            user_id: User ID
            organization_id: Organization ID
            ip_address: Client IP address
            user_agent: Client user agent
            enrollment_id: Optional enrollment ID

        Returns:
            Exam start data with questions
        """
        exam = Exam.objects.get(
            id=exam_id,
            organization_id=organization_id
        )

        # Check availability
        availability = exam.check_availability(user_id)
        if not availability['available']:
            raise ValueError(availability['reason'])

        # Get attempt number
        attempt_number = ExamAttempt.objects.filter(
            exam=exam,
            user_id=user_id
        ).count() + 1

        # Select questions
        questions = exam.select_questions()

        if len(questions) < exam.total_questions:
            raise ValueError(
                f"Not enough questions available: need {exam.total_questions}, "
                f"got {len(questions)}"
            )

        # Calculate total points
        total_points = sum(q.get('points', 1) for q in questions)

        # Create attempt
        attempt = ExamAttempt.objects.create(
            organization_id=organization_id,
            exam=exam,
            user_id=user_id,
            enrollment_id=enrollment_id,
            attempt_number=attempt_number,
            questions=[
                {
                    'question_id': q['id'],
                    'order': i + 1,
                    'points': q.get('points', 1)
                }
                for i, q in enumerate(questions)
            ],
            total_points=total_points,
            ip_address=ip_address,
            user_agent=user_agent,
            proctoring_enabled=exam.require_proctoring,
        )

        # Start attempt
        attempt.start()

        logger.info(f"Started exam attempt: {attempt.id} for user {user_id}")

        # Format questions for client (no correct answers)
        formatted_questions = [
            {
                'order': i + 1,
                'question_id': q['id'],
                'type': q['type'],
                'text': q['text'],
                'html': q.get('html'),
                'image_url': q.get('image_url'),
                'audio_url': q.get('audio_url'),
                'options': q.get('options'),
                'points': q.get('points', 1),
                'time_limit_seconds': q.get('time_limit_seconds'),
            }
            for i, q in enumerate(questions)
        ]

        return {
            'attempt_id': str(attempt.id),
            'exam_id': str(exam.id),
            'exam_name': exam.name,
            'instructions': exam.instructions,
            'total_questions': len(formatted_questions),
            'total_points': total_points,
            'time_limit_minutes': exam.time_limit_minutes,
            'time_limit_at': attempt.time_limit_at.isoformat() if attempt.time_limit_at else None,
            'allow_pause': exam.allow_pause,
            'allow_skip': exam.allow_skip,
            'allow_review': exam.allow_review,
            'allow_back_navigation': exam.allow_back_navigation,
            'questions': formatted_questions,
        }

    @staticmethod
    @transaction.atomic
    def save_answer(
        attempt_id: str,
        question_id: str,
        answer: Any,
        user_id: str,
        time_spent_seconds: int = 0,
        flagged: bool = False
    ) -> Dict[str, Any]:
        """
        Save an answer during exam.

        Args:
            attempt_id: Attempt ID
            question_id: Question ID
            answer: Selected answer
            user_id: User ID (for verification)
            time_spent_seconds: Time spent on question
            flagged: Whether question is flagged for review

        Returns:
            Save confirmation
        """
        attempt = ExamAttempt.objects.select_for_update().get(
            id=attempt_id,
            user_id=user_id
        )

        attempt.save_answer(question_id, answer, time_spent_seconds, flagged)

        return {
            'saved': True,
            'question_id': question_id,
            'time_remaining_seconds': attempt.time_remaining_seconds,
            'progress_percentage': attempt.progress_percentage
        }

    @staticmethod
    @transaction.atomic
    def flag_question(
        attempt_id: str,
        question_id: str,
        user_id: str,
        flagged: bool = True
    ) -> Dict[str, Any]:
        """
        Flag/unflag a question for review.

        Args:
            attempt_id: Attempt ID
            question_id: Question ID
            user_id: User ID
            flagged: Flag state

        Returns:
            Confirmation
        """
        attempt = ExamAttempt.objects.select_for_update().get(
            id=attempt_id,
            user_id=user_id
        )

        attempt.flag_question(question_id, flagged)

        return {'flagged': flagged, 'question_id': question_id}

    @staticmethod
    @transaction.atomic
    def pause_exam(
        attempt_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Pause an exam attempt.

        Args:
            attempt_id: Attempt ID
            user_id: User ID

        Returns:
            Pause confirmation
        """
        attempt = ExamAttempt.objects.select_for_update().get(
            id=attempt_id,
            user_id=user_id
        )

        attempt.pause()

        return {
            'paused': True,
            'pause_count': attempt.pause_count,
            'max_pause_count': attempt.exam.max_pause_count
        }

    @staticmethod
    @transaction.atomic
    def resume_exam(
        attempt_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Resume a paused exam attempt.

        Args:
            attempt_id: Attempt ID
            user_id: User ID

        Returns:
            Resume data
        """
        attempt = ExamAttempt.objects.select_for_update().get(
            id=attempt_id,
            user_id=user_id
        )

        attempt.resume()

        return {
            'resumed': True,
            'time_remaining_seconds': attempt.time_remaining_seconds,
            'current_question_index': attempt.current_question_index
        }

    @staticmethod
    @transaction.atomic
    def submit_exam(
        attempt_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Submit exam for grading.

        Args:
            attempt_id: Attempt ID
            user_id: User ID

        Returns:
            Exam results
        """
        attempt = ExamAttempt.objects.select_for_update().select_related(
            'exam'
        ).get(
            id=attempt_id,
            user_id=user_id
        )

        results = attempt.submit()

        # Publish event
        from ..events.publishers import publish_exam_completed
        publish_exam_completed(
            organization_id=str(attempt.organization_id),
            attempt_id=str(attempt.id),
            user_id=str(user_id),
            exam_id=str(attempt.exam.id),
            passed=attempt.passed,
            score=float(attempt.score_percentage)
        )

        logger.info(
            f"Submitted exam attempt: {attempt.id}, "
            f"score: {attempt.score_percentage}%, passed: {attempt.passed}"
        )

        return results

    @staticmethod
    def get_attempt_results(
        attempt_id: str,
        user_id: str = None,
        include_answers: bool = False
    ) -> Dict[str, Any]:
        """
        Get exam attempt results.

        Args:
            attempt_id: Attempt ID
            user_id: Optional user ID for verification
            include_answers: Include detailed answers

        Returns:
            Exam results
        """
        filters = {'id': attempt_id}
        if user_id:
            filters['user_id'] = user_id

        attempt = ExamAttempt.objects.select_related('exam').get(**filters)

        if attempt.status not in [AttemptStatus.COMPLETED, AttemptStatus.SUBMITTED]:
            raise ValueError("Exam not yet completed")

        return attempt.get_results(include_answers=include_answers)

    # =========================================================================
    # USER EXAM HISTORY
    # =========================================================================

    @staticmethod
    def get_user_attempts(
        user_id: str,
        organization_id: str,
        exam_id: str = None,
        status: str = None
    ) -> List[ExamAttempt]:
        """
        Get user's exam attempts.

        Args:
            user_id: User ID
            organization_id: Organization ID
            exam_id: Optional exam filter
            status: Optional status filter

        Returns:
            List of attempts
        """
        queryset = ExamAttempt.objects.filter(
            user_id=user_id,
            organization_id=organization_id
        )

        if exam_id:
            queryset = queryset.filter(exam_id=exam_id)

        if status:
            queryset = queryset.filter(status=status)

        return queryset.select_related('exam').order_by('-started_at')

    @staticmethod
    def get_user_statistics(
        user_id: str,
        organization_id: str
    ) -> Dict[str, Any]:
        """
        Get user's exam statistics.

        Args:
            user_id: User ID
            organization_id: Organization ID

        Returns:
            Statistics dictionary
        """
        attempts = ExamAttempt.objects.filter(
            user_id=user_id,
            organization_id=organization_id,
            status=AttemptStatus.COMPLETED
        )

        total = attempts.count()
        passed = attempts.filter(passed=True).count()

        avg_score = attempts.aggregate(
            avg_score=Avg('score_percentage')
        )['avg_score']

        by_category = {}
        for attempt in attempts:
            for cat, data in attempt.results_by_category.items():
                if cat not in by_category:
                    by_category[cat] = {
                        'total_questions': 0,
                        'correct': 0
                    }
                by_category[cat]['total_questions'] += data.get('total', 0)
                by_category[cat]['correct'] += data.get('correct', 0)

        # Calculate category percentages
        for cat in by_category:
            total_q = by_category[cat]['total_questions']
            if total_q > 0:
                by_category[cat]['percentage'] = round(
                    (by_category[cat]['correct'] / total_q) * 100, 2
                )
            else:
                by_category[cat]['percentage'] = 0

        # Identify weak areas
        weak_categories = sorted(
            by_category.items(),
            key=lambda x: x[1]['percentage']
        )[:3]

        return {
            'total_attempts': total,
            'passed': passed,
            'failed': total - passed,
            'pass_rate': round((passed / total * 100), 2) if total > 0 else 0,
            'average_score': float(avg_score) if avg_score else 0,
            'by_category': by_category,
            'weak_areas': [
                {'category': cat, 'percentage': data['percentage']}
                for cat, data in weak_categories
            ]
        }

    # =========================================================================
    # EXAM STATISTICS
    # =========================================================================

    @staticmethod
    def get_exam_statistics(
        exam_id: str,
        organization_id: str
    ) -> Dict[str, Any]:
        """
        Get detailed exam statistics.

        Args:
            exam_id: Exam ID
            organization_id: Organization ID

        Returns:
            Statistics dictionary
        """
        exam = Exam.objects.get(
            id=exam_id,
            organization_id=organization_id
        )

        attempts = ExamAttempt.objects.filter(
            exam=exam,
            status=AttemptStatus.COMPLETED
        )

        # Score distribution
        score_ranges = {
            '90-100': 0,
            '80-89': 0,
            '70-79': 0,
            '60-69': 0,
            'below_60': 0
        }

        for attempt in attempts:
            score = float(attempt.score_percentage or 0)
            if score >= 90:
                score_ranges['90-100'] += 1
            elif score >= 80:
                score_ranges['80-89'] += 1
            elif score >= 70:
                score_ranges['70-79'] += 1
            elif score >= 60:
                score_ranges['60-69'] += 1
            else:
                score_ranges['below_60'] += 1

        # Time analysis
        time_stats = attempts.exclude(
            time_spent_seconds__isnull=True
        ).aggregate(
            avg_time=Avg('time_spent_seconds'),
            min_time=models.Min('time_spent_seconds'),
            max_time=models.Max('time_spent_seconds')
        )

        return {
            'exam_id': str(exam.id),
            'exam_name': exam.name,
            'total_attempts': exam.attempt_count,
            'pass_rate': float(exam.pass_rate) if exam.pass_rate else 0,
            'average_score': float(exam.average_score) if exam.average_score else 0,
            'score_distribution': score_ranges,
            'time_statistics': {
                'average_minutes': round((time_stats['avg_time'] or 0) / 60, 1),
                'min_minutes': round((time_stats['min_time'] or 0) / 60, 1),
                'max_minutes': round((time_stats['max_time'] or 0) / 60, 1),
                'time_limit_minutes': exam.time_limit_minutes
            }
        }
