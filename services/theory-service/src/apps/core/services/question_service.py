# services/theory-service/src/apps/core/services/question_service.py
"""
Question Service

Business logic for question bank management.
"""

import logging
from typing import Dict, Any, List, Optional
from uuid import UUID
from decimal import Decimal
import csv
import io
import json

from django.db import transaction
from django.db.models import Q, Avg, Count, F
from django.utils import timezone

from ..models import (
    Question,
    QuestionReview,
    QuestionType,
    Difficulty,
    ReviewStatus,
)

logger = logging.getLogger(__name__)


class QuestionService:
    """Service for managing question bank."""

    @staticmethod
    def get_questions(
        organization_id: str,
        category: str = None,
        subcategory: str = None,
        difficulty: str = None,
        question_type: str = None,
        review_status: str = None,
        is_active: bool = None,
        search: str = None,
        tags: List[str] = None,
    ) -> List[Question]:
        """
        Get questions with optional filtering.

        Args:
            organization_id: Organization ID
            category: Filter by category
            subcategory: Filter by subcategory
            difficulty: Filter by difficulty
            question_type: Filter by question type
            review_status: Filter by review status
            is_active: Filter by active state
            search: Search term
            tags: Filter by tags

        Returns:
            List of questions
        """
        queryset = Question.objects.filter(organization_id=organization_id)

        if category:
            queryset = queryset.filter(category=category)

        if subcategory:
            queryset = queryset.filter(subcategory=subcategory)

        if difficulty:
            queryset = queryset.filter(difficulty=difficulty)

        if question_type:
            queryset = queryset.filter(question_type=question_type)

        if review_status:
            queryset = queryset.filter(review_status=review_status)

        if is_active is not None:
            queryset = queryset.filter(is_active=is_active)

        if search:
            queryset = queryset.filter(
                Q(question_text__icontains=search) |
                Q(reference_code__icontains=search) |
                Q(topic__icontains=search)
            )

        if tags:
            queryset = queryset.filter(tags__overlap=tags)

        return queryset.order_by('category', 'subcategory', '-created_at')

    @staticmethod
    @transaction.atomic
    def create_question(
        organization_id: str,
        category: str,
        question_text: str,
        options: List[Dict],
        correct_answer: Dict,
        created_by: str = None,
        **kwargs
    ) -> Question:
        """
        Create a new question.

        Args:
            organization_id: Organization ID
            category: Question category
            question_text: Question text
            options: Answer options
            correct_answer: Correct answer definition
            created_by: User ID who created
            **kwargs: Additional fields

        Returns:
            Created question
        """
        # Validate options
        QuestionService._validate_question_data(
            kwargs.get('question_type', QuestionType.MULTIPLE_CHOICE),
            options,
            correct_answer
        )

        question = Question.objects.create(
            organization_id=organization_id,
            category=category,
            question_text=question_text,
            options=options,
            correct_answer=correct_answer,
            created_by=created_by,
            **kwargs
        )

        logger.info(f"Created question: {question.id}")

        return question

    @staticmethod
    def get_question(
        question_id: str,
        organization_id: str = None
    ) -> Question:
        """
        Get question by ID.

        Args:
            question_id: Question ID
            organization_id: Optional organization filter

        Returns:
            Question instance
        """
        filters = {'id': question_id}
        if organization_id:
            filters['organization_id'] = organization_id

        return Question.objects.get(**filters)

    @staticmethod
    @transaction.atomic
    def update_question(
        question_id: str,
        organization_id: str,
        **updates
    ) -> Question:
        """
        Update a question.

        Args:
            question_id: Question ID
            organization_id: Organization ID
            **updates: Fields to update

        Returns:
            Updated question
        """
        question = Question.objects.select_for_update().get(
            id=question_id,
            organization_id=organization_id
        )

        # Validate if options or answer changed
        if 'options' in updates or 'correct_answer' in updates:
            QuestionService._validate_question_data(
                updates.get('question_type', question.question_type),
                updates.get('options', question.options),
                updates.get('correct_answer', question.correct_answer)
            )

        # Reset review status if content changed
        content_fields = ['question_text', 'options', 'correct_answer', 'explanation']
        if any(field in updates for field in content_fields):
            updates['review_status'] = ReviewStatus.PENDING

        for field, value in updates.items():
            if hasattr(question, field):
                setattr(question, field, value)

        question.save()

        logger.info(f"Updated question: {question.id}")

        return question

    @staticmethod
    @transaction.atomic
    def delete_question(
        question_id: str,
        organization_id: str
    ) -> None:
        """
        Delete a question (soft delete by deactivating).

        Args:
            question_id: Question ID
            organization_id: Organization ID
        """
        question = Question.objects.get(
            id=question_id,
            organization_id=organization_id
        )

        # Soft delete
        question.is_active = False
        question.save()

        logger.info(f"Deactivated question: {question_id}")

    @staticmethod
    @transaction.atomic
    def review_question(
        question_id: str,
        organization_id: str,
        reviewer_id: str,
        status: str,
        notes: str = '',
        suggested_changes: Dict = None
    ) -> Question:
        """
        Review a question.

        Args:
            question_id: Question ID
            organization_id: Organization ID
            reviewer_id: Reviewer user ID
            status: Review status
            notes: Review notes
            suggested_changes: Optional suggested changes

        Returns:
            Reviewed question
        """
        question = Question.objects.select_for_update().get(
            id=question_id,
            organization_id=organization_id
        )

        # Create review record
        QuestionReview.objects.create(
            question=question,
            reviewer_id=reviewer_id,
            status=status,
            notes=notes,
            suggested_changes=suggested_changes or {}
        )

        # Update question
        question.review_status = status
        question.reviewed_by = reviewer_id
        question.reviewed_at = timezone.now()
        question.review_notes = notes
        question.save()

        logger.info(f"Reviewed question: {question.id} - {status}")

        return question

    @staticmethod
    @transaction.atomic
    def bulk_import_questions(
        organization_id: str,
        questions_data: List[Dict],
        created_by: str = None
    ) -> Dict[str, Any]:
        """
        Bulk import questions.

        Args:
            organization_id: Organization ID
            questions_data: List of question dictionaries
            created_by: User ID who imported

        Returns:
            Import results
        """
        created = 0
        errors = []

        for i, q_data in enumerate(questions_data):
            try:
                QuestionService.create_question(
                    organization_id=organization_id,
                    created_by=created_by,
                    **q_data
                )
                created += 1
            except Exception as e:
                errors.append({
                    'index': i,
                    'error': str(e),
                    'data': q_data.get('question_text', '')[:50]
                })

        logger.info(f"Bulk imported {created} questions for org {organization_id}")

        return {
            'created': created,
            'errors': errors,
            'total': len(questions_data)
        }

    @staticmethod
    def import_from_csv(
        organization_id: str,
        csv_content: str,
        created_by: str = None
    ) -> Dict[str, Any]:
        """
        Import questions from CSV content.

        Args:
            organization_id: Organization ID
            csv_content: CSV file content
            created_by: User ID who imported

        Returns:
            Import results
        """
        reader = csv.DictReader(io.StringIO(csv_content))
        questions_data = []

        for row in reader:
            # Parse options from CSV columns
            options = []
            for opt_key in ['option_a', 'option_b', 'option_c', 'option_d']:
                if opt_key in row and row[opt_key]:
                    opt_id = opt_key[-1]  # a, b, c, d
                    options.append({
                        'id': opt_id,
                        'text': row[opt_key]
                    })

            # Parse correct answer
            correct = row.get('correct_answer', 'a').lower()

            questions_data.append({
                'category': row.get('category', ''),
                'subcategory': row.get('subcategory', ''),
                'question_text': row.get('question_text', ''),
                'question_type': row.get('question_type', 'multiple_choice'),
                'options': options,
                'correct_answer': {'option_id': correct},
                'explanation': row.get('explanation', ''),
                'difficulty': row.get('difficulty', 'medium'),
                'reference_code': row.get('reference_code', ''),
                'topic': row.get('topic', ''),
            })

        return QuestionService.bulk_import_questions(
            organization_id,
            questions_data,
            created_by
        )

    @staticmethod
    def export_questions(
        organization_id: str,
        category: str = None,
        format: str = 'json'
    ) -> Any:
        """
        Export questions to specified format.

        Args:
            organization_id: Organization ID
            category: Optional category filter
            format: Export format (json, csv)

        Returns:
            Exported data
        """
        queryset = Question.objects.filter(
            organization_id=organization_id,
            is_active=True
        )

        if category:
            queryset = queryset.filter(category=category)

        questions = list(queryset)

        if format == 'csv':
            output = io.StringIO()
            writer = csv.writer(output)

            # Header
            writer.writerow([
                'category', 'subcategory', 'topic', 'question_type',
                'question_text', 'option_a', 'option_b', 'option_c', 'option_d',
                'correct_answer', 'explanation', 'difficulty', 'reference_code'
            ])

            for q in questions:
                options = {opt['id']: opt['text'] for opt in q.options}
                correct = q.correct_answer.get('option_id', '')

                writer.writerow([
                    q.category,
                    q.subcategory,
                    q.topic,
                    q.question_type,
                    q.question_text,
                    options.get('a', ''),
                    options.get('b', ''),
                    options.get('c', ''),
                    options.get('d', ''),
                    correct,
                    q.explanation,
                    q.difficulty,
                    q.reference_code
                ])

            return output.getvalue()

        else:  # JSON
            return [
                {
                    'id': str(q.id),
                    'category': q.category,
                    'subcategory': q.subcategory,
                    'topic': q.topic,
                    'question_type': q.question_type,
                    'question_text': q.question_text,
                    'options': q.options,
                    'correct_answer': q.correct_answer,
                    'explanation': q.explanation,
                    'difficulty': q.difficulty,
                    'reference_code': q.reference_code,
                    'tags': q.tags,
                }
                for q in questions
            ]

    @staticmethod
    def get_question_statistics(
        organization_id: str,
        category: str = None
    ) -> Dict[str, Any]:
        """
        Get question bank statistics.

        Args:
            organization_id: Organization ID
            category: Optional category filter

        Returns:
            Statistics dictionary
        """
        queryset = Question.objects.filter(organization_id=organization_id)

        if category:
            queryset = queryset.filter(category=category)

        total = queryset.count()
        active = queryset.filter(is_active=True).count()

        by_category = queryset.values('category').annotate(
            count=Count('id'),
            avg_success_rate=Avg('success_rate'),
            avg_difficulty=Avg('difficulty_score')
        )

        by_difficulty = queryset.filter(is_active=True).values(
            'difficulty'
        ).annotate(count=Count('id'))

        by_review_status = queryset.values('review_status').annotate(
            count=Count('id')
        )

        # Questions needing attention
        low_success = queryset.filter(
            is_active=True,
            times_asked__gte=10,
            success_rate__lt=30
        ).count()

        high_success = queryset.filter(
            is_active=True,
            times_asked__gte=10,
            success_rate__gt=95
        ).count()

        return {
            'total': total,
            'active': active,
            'inactive': total - active,
            'by_category': list(by_category),
            'by_difficulty': list(by_difficulty),
            'by_review_status': list(by_review_status),
            'needs_attention': {
                'too_easy': high_success,
                'too_hard': low_success,
                'pending_review': queryset.filter(
                    review_status=ReviewStatus.PENDING
                ).count()
            }
        }

    @staticmethod
    def _validate_question_data(
        question_type: str,
        options: List[Dict],
        correct_answer: Dict
    ) -> None:
        """Validate question options and correct answer."""
        if question_type in [QuestionType.MULTIPLE_CHOICE, QuestionType.MULTI_SELECT]:
            if not options or len(options) < 2:
                raise ValueError("Multiple choice questions need at least 2 options")

            option_ids = {opt['id'] for opt in options}

            if question_type == QuestionType.MULTIPLE_CHOICE:
                correct_id = correct_answer.get('option_id')
                if not correct_id or correct_id not in option_ids:
                    raise ValueError("Invalid correct answer option ID")

            elif question_type == QuestionType.MULTI_SELECT:
                correct_ids = correct_answer.get('option_ids', [])
                if not correct_ids:
                    raise ValueError("Multi-select needs at least one correct option")
                for cid in correct_ids:
                    if cid not in option_ids:
                        raise ValueError(f"Invalid correct option ID: {cid}")

        elif question_type == QuestionType.TRUE_FALSE:
            if 'value' not in correct_answer:
                raise ValueError("True/False questions need a 'value' in correct_answer")

        elif question_type == QuestionType.FILL_BLANK:
            if 'answers' not in correct_answer or not correct_answer['answers']:
                raise ValueError("Fill blank questions need 'answers' list")

        elif question_type == QuestionType.MATCHING:
            if 'pairs' not in correct_answer or not correct_answer['pairs']:
                raise ValueError("Matching questions need 'pairs' in correct_answer")

        elif question_type == QuestionType.ORDERING:
            if 'sequence' not in correct_answer or not correct_answer['sequence']:
                raise ValueError("Ordering questions need 'sequence' in correct_answer")
