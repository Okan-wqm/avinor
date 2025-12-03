# services/theory-service/src/apps/core/api/views/question_views.py
"""
Question Views

ViewSets for question-related API endpoints.
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from ...models import Question
from ...services import QuestionService
from ..serializers import (
    QuestionListSerializer,
    QuestionDetailSerializer,
    QuestionCreateSerializer,
    QuestionUpdateSerializer,
    QuestionReviewInputSerializer,
    QuestionReviewSerializer,
    QuestionBulkImportSerializer,
)


class QuestionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing question bank.

    Provides CRUD operations plus review, import, export actions.
    """

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Get questions filtered by organization."""
        organization_id = self.request.headers.get('X-Organization-ID')

        return QuestionService.get_questions(
            organization_id=organization_id,
            category=self.request.query_params.get('category'),
            subcategory=self.request.query_params.get('subcategory'),
            difficulty=self.request.query_params.get('difficulty'),
            question_type=self.request.query_params.get('question_type'),
            review_status=self.request.query_params.get('review_status'),
            is_active=self.request.query_params.get('is_active'),
            search=self.request.query_params.get('search'),
        )

    def get_serializer_class(self):
        """Return appropriate serializer class."""
        if self.action == 'list':
            return QuestionListSerializer
        elif self.action == 'create':
            return QuestionCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return QuestionUpdateSerializer
        return QuestionDetailSerializer

    def create(self, request, *args, **kwargs):
        """Create a new question."""
        organization_id = request.headers.get('X-Organization-ID')
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            question = QuestionService.create_question(
                organization_id=organization_id,
                created_by=str(request.user.id),
                **serializer.validated_data
            )

            return Response(
                QuestionDetailSerializer(question).data,
                status=status.HTTP_201_CREATED
            )
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    def update(self, request, *args, **kwargs):
        """Update a question."""
        organization_id = request.headers.get('X-Organization-ID')
        serializer = self.get_serializer(data=request.data, partial=kwargs.get('partial', False))
        serializer.is_valid(raise_exception=True)

        try:
            question = QuestionService.update_question(
                question_id=kwargs['pk'],
                organization_id=organization_id,
                **serializer.validated_data
            )

            return Response(QuestionDetailSerializer(question).data)
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    def destroy(self, request, *args, **kwargs):
        """Delete (deactivate) a question."""
        organization_id = request.headers.get('X-Organization-ID')

        QuestionService.delete_question(
            question_id=kwargs['pk'],
            organization_id=organization_id
        )

        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'])
    def review(self, request, pk=None):
        """Review a question."""
        organization_id = request.headers.get('X-Organization-ID')
        serializer = QuestionReviewInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        question = QuestionService.review_question(
            question_id=pk,
            organization_id=organization_id,
            reviewer_id=str(request.user.id),
            **serializer.validated_data
        )

        return Response(QuestionDetailSerializer(question).data)

    @action(detail=True, methods=['get'])
    def reviews(self, request, pk=None):
        """Get review history for a question."""
        organization_id = request.headers.get('X-Organization-ID')

        question = QuestionService.get_question(pk, organization_id)
        reviews = question.reviews.all()

        return Response(QuestionReviewSerializer(reviews, many=True).data)

    @action(detail=True, methods=['post'])
    def clone(self, request, pk=None):
        """Clone a question for creating a new version."""
        organization_id = request.headers.get('X-Organization-ID')

        question = QuestionService.get_question(pk, organization_id)
        new_question = question.clone()
        new_question.created_by = request.user.id
        new_question.save()

        return Response(
            QuestionDetailSerializer(new_question).data,
            status=status.HTTP_201_CREATED
        )

    @action(detail=False, methods=['post'], url_path='import')
    def bulk_import(self, request):
        """Bulk import questions."""
        organization_id = request.headers.get('X-Organization-ID')
        serializer = QuestionBulkImportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = QuestionService.bulk_import_questions(
            organization_id=organization_id,
            questions_data=serializer.validated_data['questions'],
            created_by=str(request.user.id)
        )

        return Response(result, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'], url_path='import-csv')
    def import_csv(self, request):
        """Import questions from CSV."""
        organization_id = request.headers.get('X-Organization-ID')
        csv_content = request.data.get('csv_content')

        if not csv_content:
            return Response(
                {'error': 'csv_content is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        result = QuestionService.import_from_csv(
            organization_id=organization_id,
            csv_content=csv_content,
            created_by=str(request.user.id)
        )

        return Response(result, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'], url_path='export')
    def export(self, request):
        """Export questions."""
        organization_id = request.headers.get('X-Organization-ID')
        category = request.query_params.get('category')
        export_format = request.query_params.get('format', 'json')

        result = QuestionService.export_questions(
            organization_id=organization_id,
            category=category,
            format=export_format
        )

        if export_format == 'csv':
            return Response(
                result,
                content_type='text/csv',
                headers={'Content-Disposition': 'attachment; filename="questions.csv"'}
            )

        return Response(result)

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get question bank statistics."""
        organization_id = request.headers.get('X-Organization-ID')
        category = request.query_params.get('category')

        stats = QuestionService.get_question_statistics(
            organization_id=organization_id,
            category=category
        )

        return Response(stats)

    @action(detail=False, methods=['get'])
    def categories(self, request):
        """Get list of categories with counts."""
        organization_id = request.headers.get('X-Organization-ID')

        categories = Question.objects.filter(
            organization_id=organization_id,
            is_active=True
        ).values('category').annotate(
            count=models.Count('id')
        ).order_by('category')

        return Response(list(categories))

    @action(detail=True, methods=['post'])
    def flag(self, request, pk=None):
        """Flag a question for review."""
        organization_id = request.headers.get('X-Organization-ID')
        reason = request.data.get('reason', '')

        question = QuestionService.update_question(
            question_id=pk,
            organization_id=organization_id,
            is_flagged=True,
            flag_reason=reason
        )

        return Response(QuestionDetailSerializer(question).data)

    @action(detail=True, methods=['post'])
    def unflag(self, request, pk=None):
        """Remove flag from a question."""
        organization_id = request.headers.get('X-Organization-ID')

        question = QuestionService.update_question(
            question_id=pk,
            organization_id=organization_id,
            is_flagged=False,
            flag_reason=''
        )

        return Response(QuestionDetailSerializer(question).data)


# Import models for annotation
from django.db import models
