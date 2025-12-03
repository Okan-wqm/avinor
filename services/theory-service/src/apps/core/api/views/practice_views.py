# services/theory-service/src/apps/core/api/views/practice_views.py
"""
Practice Views

ViewSets for practice and study-related API endpoints.
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from ...services import PracticeService


class PracticeViewSet(viewsets.ViewSet):
    """
    ViewSet for practice questions and study features.

    Provides endpoints for practice questions, flashcards, quick quizzes.
    """

    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def questions(self, request):
        """
        Get practice questions.

        Query parameters:
        - count: Number of questions (default 10)
        - category: Filter by category
        - categories: Filter by multiple categories (comma-separated)
        - difficulty: Filter by difficulty
        - difficulties: Filter by multiple difficulties (comma-separated)
        - exclude: Comma-separated question IDs to exclude
        - include_explanations: Include explanations (default false)
        """
        organization_id = request.headers.get('X-Organization-ID')

        count = int(request.query_params.get('count', 10))
        category = request.query_params.get('category')
        categories = request.query_params.get('categories')
        difficulty = request.query_params.get('difficulty')
        difficulties = request.query_params.get('difficulties')
        exclude = request.query_params.get('exclude')
        include_explanations = request.query_params.get('include_explanations', 'false').lower() == 'true'

        # Parse comma-separated values
        if categories:
            categories = [c.strip() for c in categories.split(',')]
        if difficulties:
            difficulties = [d.strip() for d in difficulties.split(',')]
        if exclude:
            exclude = [e.strip() for e in exclude.split(',')]

        questions = PracticeService.get_practice_questions(
            organization_id=organization_id,
            count=count,
            category=category,
            categories=categories,
            difficulty=difficulty,
            difficulties=difficulties,
            exclude_ids=exclude,
            include_explanations=include_explanations,
        )

        return Response({
            'count': len(questions),
            'questions': questions
        })

    @action(detail=False, methods=['post'], url_path='check-answer')
    def check_answer(self, request):
        """Check a practice answer and get feedback."""
        organization_id = request.headers.get('X-Organization-ID')

        question_id = request.data.get('question_id')
        answer = request.data.get('answer')
        time_spent_seconds = request.data.get('time_spent_seconds')

        if not question_id:
            return Response(
                {'error': 'question_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if answer is None:
            return Response(
                {'error': 'answer is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            result = PracticeService.check_practice_answer(
                organization_id=organization_id,
                question_id=question_id,
                answer=answer,
                time_spent_seconds=time_spent_seconds
            )
            return Response(result)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['get'])
    def categories(self, request):
        """Get category breakdown with question counts."""
        organization_id = request.headers.get('X-Organization-ID')

        breakdown = PracticeService.get_category_breakdown(organization_id)

        return Response(breakdown)

    @action(detail=False, methods=['post'])
    def adaptive(self, request):
        """
        Get adaptive questions based on user performance.

        Request body:
        - performance: Dict of category -> success_rate
        - count: Number of questions (default 10)
        - categories: Optional list of categories to include
        """
        organization_id = request.headers.get('X-Organization-ID')

        performance = request.data.get('performance', {})
        count = int(request.data.get('count', 10))
        categories = request.data.get('categories')

        questions = PracticeService.get_adaptive_questions(
            organization_id=organization_id,
            user_performance=performance,
            count=count,
            categories=categories
        )

        return Response({
            'count': len(questions),
            'questions': questions
        })

    @action(detail=False, methods=['get'], url_path='quick-quiz')
    def quick_quiz(self, request):
        """Generate a quick quiz for rapid practice."""
        organization_id = request.headers.get('X-Organization-ID')

        category = request.query_params.get('category')
        count = int(request.query_params.get('count', 5))

        quiz = PracticeService.get_quick_quiz(
            organization_id=organization_id,
            category=category,
            count=count
        )

        return Response(quiz)

    @action(detail=False, methods=['get'])
    def flashcards(self, request):
        """Get flashcard set for study."""
        organization_id = request.headers.get('X-Organization-ID')

        category = request.query_params.get('category')
        count = int(request.query_params.get('count', 20))

        flashcards = PracticeService.get_flashcard_set(
            organization_id=organization_id,
            category=category,
            count=count
        )

        return Response({
            'count': len(flashcards),
            'flashcards': flashcards
        })

    @action(detail=False, methods=['get'], url_path='by-topic')
    def by_topic(self, request):
        """Get questions by topic."""
        organization_id = request.headers.get('X-Organization-ID')

        topic = request.query_params.get('topic')
        count = int(request.query_params.get('count', 10))

        if not topic:
            return Response(
                {'error': 'topic parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        questions = PracticeService.get_topic_questions(
            organization_id=organization_id,
            topic=topic,
            count=count
        )

        return Response({
            'topic': topic,
            'count': len(questions),
            'questions': questions
        })

    @action(detail=False, methods=['get'], url_path='by-learning-objective')
    def by_learning_objective(self, request):
        """Get questions by learning objective."""
        organization_id = request.headers.get('X-Organization-ID')

        lo_id = request.query_params.get('learning_objective_id')
        count = int(request.query_params.get('count', 10))

        if not lo_id:
            return Response(
                {'error': 'learning_objective_id parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        questions = PracticeService.get_learning_objective_questions(
            organization_id=organization_id,
            learning_objective_id=lo_id,
            count=count
        )

        return Response({
            'learning_objective_id': lo_id,
            'count': len(questions),
            'questions': questions
        })
