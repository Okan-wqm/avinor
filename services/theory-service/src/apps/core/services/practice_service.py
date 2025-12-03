# services/theory-service/src/apps/core/services/practice_service.py
"""
Practice Service

Business logic for practice questions and study sessions.
"""

import logging
import random
from typing import Dict, Any, List, Optional
from uuid import UUID
from decimal import Decimal

from django.db import transaction
from django.db.models import Q, F
from django.utils import timezone

from ..models import (
    Question,
    QuestionType,
    Difficulty,
)

logger = logging.getLogger(__name__)


class PracticeService:
    """Service for practice questions and study sessions."""

    @staticmethod
    def get_practice_questions(
        organization_id: str,
        count: int = 10,
        category: str = None,
        categories: List[str] = None,
        difficulty: str = None,
        difficulties: List[str] = None,
        exclude_ids: List[str] = None,
        include_explanations: bool = False,
        randomize: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Get practice questions based on criteria.

        Args:
            organization_id: Organization ID
            count: Number of questions to return
            category: Single category filter
            categories: Multiple categories filter
            difficulty: Single difficulty filter
            difficulties: Multiple difficulties filter
            exclude_ids: Question IDs to exclude
            include_explanations: Whether to include explanations
            randomize: Whether to randomize order

        Returns:
            List of practice questions
        """
        queryset = Question.objects.filter(
            organization_id=organization_id,
            is_active=True,
            review_status='approved'
        )

        # Category filter
        if category:
            queryset = queryset.filter(category=category)
        elif categories:
            queryset = queryset.filter(category__in=categories)

        # Difficulty filter
        if difficulty:
            queryset = queryset.filter(difficulty=difficulty)
        elif difficulties:
            queryset = queryset.filter(difficulty__in=difficulties)

        # Exclude specific questions
        if exclude_ids:
            queryset = queryset.exclude(id__in=exclude_ids)

        # Get questions
        questions = list(queryset)

        # Randomize if requested
        if randomize and len(questions) > count:
            questions = random.sample(questions, count)
        else:
            questions = questions[:count]

        # Format questions
        result = []
        for q in questions:
            options = list(q.options) if q.options else []
            if randomize:
                random.shuffle(options)

            question_data = {
                'id': str(q.id),
                'type': q.question_type,
                'text': q.question_text,
                'html': q.question_html or None,
                'image_url': q.image_url or None,
                'options': [
                    {'id': opt['id'], 'text': opt['text']}
                    for opt in options
                ] if options else None,
                'category': q.category,
                'subcategory': q.subcategory,
                'difficulty': q.difficulty,
                'points': q.points,
            }

            if include_explanations:
                question_data['explanation'] = q.explanation
                question_data['correct_answer'] = q.correct_answer

            result.append(question_data)

        return result

    @staticmethod
    def check_practice_answer(
        organization_id: str,
        question_id: str,
        answer: Any,
        time_spent_seconds: int = None
    ) -> Dict[str, Any]:
        """
        Check a practice answer and get feedback.

        Args:
            organization_id: Organization ID
            question_id: Question ID
            answer: User's answer
            time_spent_seconds: Time spent on question

        Returns:
            Answer check result with explanation
        """
        question = Question.objects.get(
            id=question_id,
            organization_id=organization_id
        )

        # Check answer
        result = question.check_answer(answer)

        # Update statistics (don't affect actual stats for practice)
        # but we could track practice attempts separately

        return {
            'correct': result.get('correct', False),
            'partial_score': result.get('partial_score'),
            'correct_answer': question.correct_answer,
            'explanation': question.explanation,
            'explanation_html': question.explanation_html,
            'explanation_image_url': question.explanation_image_url,
            'hint': question.hint if question.show_hint_after_wrong and not result.get('correct') else None,
            'difficulty': question.difficulty,
            'success_rate': float(question.success_rate) if question.success_rate else None,
        }

    @staticmethod
    def get_category_breakdown(
        organization_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get question breakdown by category.

        Args:
            organization_id: Organization ID

        Returns:
            Category breakdown with counts
        """
        from django.db.models import Count

        breakdown = Question.objects.filter(
            organization_id=organization_id,
            is_active=True,
            review_status='approved'
        ).values('category').annotate(
            total=Count('id'),
            easy=Count('id', filter=Q(difficulty=Difficulty.EASY)),
            medium=Count('id', filter=Q(difficulty=Difficulty.MEDIUM)),
            hard=Count('id', filter=Q(difficulty=Difficulty.HARD)),
            expert=Count('id', filter=Q(difficulty=Difficulty.EXPERT))
        ).order_by('category')

        return list(breakdown)

    @staticmethod
    def get_adaptive_questions(
        organization_id: str,
        user_performance: Dict[str, float],
        count: int = 10,
        categories: List[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get questions adaptively based on user performance.

        Focuses on weak areas and adjusts difficulty.

        Args:
            organization_id: Organization ID
            user_performance: Dict of category -> success_rate
            count: Number of questions
            categories: Optional category filter

        Returns:
            Adaptive question set
        """
        questions = []

        # Sort categories by performance (weakest first)
        sorted_categories = sorted(
            user_performance.items(),
            key=lambda x: x[1]
        )

        # Determine difficulty based on overall performance
        avg_performance = sum(user_performance.values()) / len(user_performance) if user_performance else 50

        if avg_performance < 40:
            target_difficulties = [Difficulty.EASY, Difficulty.MEDIUM]
        elif avg_performance < 60:
            target_difficulties = [Difficulty.MEDIUM]
        elif avg_performance < 80:
            target_difficulties = [Difficulty.MEDIUM, Difficulty.HARD]
        else:
            target_difficulties = [Difficulty.HARD, Difficulty.EXPERT]

        # Allocate questions to categories (more to weak areas)
        questions_per_category = {}
        remaining = count

        for i, (category, performance) in enumerate(sorted_categories):
            if categories and category not in categories:
                continue

            # Weak categories get more questions
            weight = 1 - (performance / 100)
            allocation = int(count * weight / 2)  # Up to half of questions
            allocation = min(allocation, remaining, count // 2)

            if allocation > 0:
                questions_per_category[category] = allocation
                remaining -= allocation

        # Distribute remaining questions
        if remaining > 0:
            for category, _ in sorted_categories:
                if category not in questions_per_category:
                    questions_per_category[category] = 0
                questions_per_category[category] += 1
                remaining -= 1
                if remaining == 0:
                    break

        # Fetch questions for each category
        result_questions = []

        for category, needed in questions_per_category.items():
            if needed <= 0:
                continue

            queryset = Question.objects.filter(
                organization_id=organization_id,
                category=category,
                is_active=True,
                review_status='approved',
                difficulty__in=target_difficulties
            )

            pool = list(queryset)

            if len(pool) > needed:
                selected = random.sample(pool, needed)
            else:
                selected = pool

            for q in selected:
                options = list(q.options) if q.options else []
                random.shuffle(options)

                result_questions.append({
                    'id': str(q.id),
                    'type': q.question_type,
                    'text': q.question_text,
                    'image_url': q.image_url or None,
                    'options': [
                        {'id': opt['id'], 'text': opt['text']}
                        for opt in options
                    ] if options else None,
                    'category': q.category,
                    'difficulty': q.difficulty,
                    'points': q.points,
                    'is_weak_area': user_performance.get(category, 100) < 70
                })

        # Shuffle final result
        random.shuffle(result_questions)

        return result_questions[:count]

    @staticmethod
    def get_quick_quiz(
        organization_id: str,
        category: str = None,
        count: int = 5
    ) -> Dict[str, Any]:
        """
        Generate a quick quiz for rapid practice.

        Args:
            organization_id: Organization ID
            category: Optional category
            count: Number of questions

        Returns:
            Quick quiz data
        """
        questions = PracticeService.get_practice_questions(
            organization_id=organization_id,
            count=count,
            category=category,
            difficulties=[Difficulty.EASY, Difficulty.MEDIUM],
            randomize=True
        )

        return {
            'quiz_id': str(UUID(int=random.getrandbits(128))),
            'category': category,
            'question_count': len(questions),
            'questions': questions,
            'time_limit_seconds': count * 60,  # 1 minute per question
        }

    @staticmethod
    def get_flashcard_set(
        organization_id: str,
        category: str = None,
        count: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get questions formatted as flashcards.

        Args:
            organization_id: Organization ID
            category: Optional category
            count: Number of flashcards

        Returns:
            Flashcard data
        """
        queryset = Question.objects.filter(
            organization_id=organization_id,
            is_active=True,
            review_status='approved'
        )

        if category:
            queryset = queryset.filter(category=category)

        # Prefer questions with explanations for flashcards
        queryset = queryset.exclude(explanation='')

        questions = list(queryset)

        if len(questions) > count:
            questions = random.sample(questions, count)

        flashcards = []
        for q in questions:
            # Get correct answer text
            correct_text = ''
            if q.question_type == QuestionType.MULTIPLE_CHOICE:
                correct_id = q.correct_answer.get('option_id')
                for opt in q.options:
                    if opt['id'] == correct_id:
                        correct_text = opt['text']
                        break
            elif q.question_type == QuestionType.TRUE_FALSE:
                correct_text = 'True' if q.correct_answer.get('value') else 'False'
            elif q.question_type == QuestionType.FILL_BLANK:
                answers = q.correct_answer.get('answers', [])
                correct_text = answers[0] if answers else ''

            flashcards.append({
                'id': str(q.id),
                'front': q.question_text,
                'front_image': q.image_url or None,
                'back': correct_text,
                'explanation': q.explanation,
                'category': q.category,
                'difficulty': q.difficulty,
            })

        random.shuffle(flashcards)

        return flashcards

    @staticmethod
    def get_topic_questions(
        organization_id: str,
        topic: str,
        count: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get questions for a specific topic.

        Args:
            organization_id: Organization ID
            topic: Topic string
            count: Number of questions

        Returns:
            Topic questions
        """
        queryset = Question.objects.filter(
            organization_id=organization_id,
            is_active=True,
            review_status='approved'
        ).filter(
            Q(topic__icontains=topic) |
            Q(question_text__icontains=topic) |
            Q(tags__contains=[topic])
        )

        questions = list(queryset)

        if len(questions) > count:
            questions = random.sample(questions, count)

        return PracticeService._format_questions(questions)

    @staticmethod
    def get_learning_objective_questions(
        organization_id: str,
        learning_objective_id: str,
        count: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get questions for a specific learning objective.

        Args:
            organization_id: Organization ID
            learning_objective_id: Learning objective ID
            count: Number of questions

        Returns:
            Learning objective questions
        """
        queryset = Question.objects.filter(
            organization_id=organization_id,
            learning_objective_id=learning_objective_id,
            is_active=True,
            review_status='approved'
        )

        questions = list(queryset)

        if len(questions) > count:
            questions = random.sample(questions, count)

        return PracticeService._format_questions(questions)

    @staticmethod
    def _format_questions(questions: List[Question]) -> List[Dict[str, Any]]:
        """Format questions for API response."""
        result = []

        for q in questions:
            options = list(q.options) if q.options else []
            random.shuffle(options)

            result.append({
                'id': str(q.id),
                'type': q.question_type,
                'text': q.question_text,
                'html': q.question_html or None,
                'image_url': q.image_url or None,
                'options': [
                    {'id': opt['id'], 'text': opt['text']}
                    for opt in options
                ] if options else None,
                'category': q.category,
                'subcategory': q.subcategory,
                'topic': q.topic,
                'difficulty': q.difficulty,
                'points': q.points,
            })

        return result
