# services/theory-service/src/apps/core/api/serializers/question_serializers.py
"""
Question Serializers

Serializers for question-related API endpoints.
"""

from rest_framework import serializers

from ...models import (
    Question,
    QuestionReview,
    QuestionType,
    Difficulty,
    ReviewStatus,
)


class QuestionListSerializer(serializers.ModelSerializer):
    """Serializer for question list view."""

    has_media = serializers.ReadOnlyField()
    is_approved = serializers.ReadOnlyField()

    class Meta:
        model = Question
        fields = [
            'id',
            'category',
            'subcategory',
            'topic',
            'question_type',
            'question_text',
            'difficulty',
            'difficulty_score',
            'points',
            'times_asked',
            'success_rate',
            'has_media',
            'is_active',
            'is_approved',
            'review_status',
            'tags',
            'created_at',
        ]


class QuestionDetailSerializer(serializers.ModelSerializer):
    """Serializer for question detail view."""

    has_media = serializers.ReadOnlyField()
    is_approved = serializers.ReadOnlyField()
    answer_rate = serializers.ReadOnlyField()

    class Meta:
        model = Question
        fields = [
            'id',
            'organization_id',
            'category',
            'subcategory',
            'topic',
            'tags',
            'reference_code',
            'learning_objective',
            'learning_objective_id',
            'question_type',
            'question_text',
            'question_html',
            'image_url',
            'image_alt_text',
            'audio_url',
            'video_url',
            'options',
            'correct_answer',
            'explanation',
            'explanation_html',
            'explanation_image_url',
            'hint',
            'show_hint_after_wrong',
            'difficulty',
            'difficulty_score',
            'points',
            'negative_points',
            'partial_credit',
            'time_limit_seconds',
            'recommended_time_seconds',
            'times_asked',
            'times_correct',
            'times_incorrect',
            'times_skipped',
            'success_rate',
            'average_time_seconds',
            'option_stats',
            'has_media',
            'is_active',
            'is_pilot_question',
            'is_flagged',
            'flag_reason',
            'review_status',
            'reviewed_by',
            'reviewed_at',
            'review_notes',
            'is_approved',
            'answer_rate',
            'source',
            'source_reference',
            'version',
            'previous_version_id',
            'created_at',
            'updated_at',
            'created_by',
        ]
        read_only_fields = [
            'id', 'organization_id', 'times_asked', 'times_correct',
            'times_incorrect', 'times_skipped', 'success_rate',
            'average_time_seconds', 'option_stats', 'discrimination_index',
            'reviewed_by', 'reviewed_at', 'version', 'previous_version_id',
            'created_at', 'updated_at', 'created_by'
        ]


class QuestionCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating questions."""

    class Meta:
        model = Question
        fields = [
            'category',
            'subcategory',
            'topic',
            'tags',
            'reference_code',
            'learning_objective',
            'learning_objective_id',
            'question_type',
            'question_text',
            'question_html',
            'image_url',
            'image_alt_text',
            'audio_url',
            'video_url',
            'options',
            'correct_answer',
            'explanation',
            'explanation_html',
            'explanation_image_url',
            'hint',
            'show_hint_after_wrong',
            'difficulty',
            'points',
            'negative_points',
            'partial_credit',
            'time_limit_seconds',
            'recommended_time_seconds',
            'source',
            'source_reference',
        ]

    def validate(self, data):
        """Validate question data."""
        question_type = data.get('question_type', QuestionType.MULTIPLE_CHOICE)
        options = data.get('options', [])
        correct_answer = data.get('correct_answer', {})

        # Validate based on question type
        if question_type in [QuestionType.MULTIPLE_CHOICE, QuestionType.MULTI_SELECT]:
            if not options or len(options) < 2:
                raise serializers.ValidationError({
                    'options': 'Multiple choice questions require at least 2 options'
                })

            option_ids = {opt.get('id') for opt in options}

            if question_type == QuestionType.MULTIPLE_CHOICE:
                correct_id = correct_answer.get('option_id')
                if not correct_id or correct_id not in option_ids:
                    raise serializers.ValidationError({
                        'correct_answer': 'Invalid correct answer option_id'
                    })
            else:
                correct_ids = correct_answer.get('option_ids', [])
                if not correct_ids:
                    raise serializers.ValidationError({
                        'correct_answer': 'Multi-select needs at least one correct option'
                    })
                for cid in correct_ids:
                    if cid not in option_ids:
                        raise serializers.ValidationError({
                            'correct_answer': f'Invalid option_id: {cid}'
                        })

        elif question_type == QuestionType.TRUE_FALSE:
            if 'value' not in correct_answer:
                raise serializers.ValidationError({
                    'correct_answer': 'True/False questions need a value field'
                })

        elif question_type == QuestionType.FILL_BLANK:
            if 'answers' not in correct_answer or not correct_answer['answers']:
                raise serializers.ValidationError({
                    'correct_answer': 'Fill blank questions need an answers list'
                })

        return data


class QuestionUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating questions."""

    class Meta:
        model = Question
        fields = [
            'category',
            'subcategory',
            'topic',
            'tags',
            'reference_code',
            'learning_objective',
            'learning_objective_id',
            'question_type',
            'question_text',
            'question_html',
            'image_url',
            'image_alt_text',
            'audio_url',
            'video_url',
            'options',
            'correct_answer',
            'explanation',
            'explanation_html',
            'explanation_image_url',
            'hint',
            'show_hint_after_wrong',
            'difficulty',
            'points',
            'negative_points',
            'partial_credit',
            'time_limit_seconds',
            'recommended_time_seconds',
            'is_active',
            'is_pilot_question',
            'is_flagged',
            'flag_reason',
            'source',
            'source_reference',
        ]


class QuestionReviewInputSerializer(serializers.Serializer):
    """Serializer for reviewing a question."""

    status = serializers.ChoiceField(choices=ReviewStatus.choices)
    notes = serializers.CharField(required=False, allow_blank=True)
    suggested_changes = serializers.DictField(required=False)


class QuestionReviewSerializer(serializers.ModelSerializer):
    """Serializer for question review records."""

    class Meta:
        model = QuestionReview
        fields = [
            'id',
            'question',
            'reviewer_id',
            'status',
            'notes',
            'suggested_changes',
            'created_at',
        ]
        read_only_fields = ['id', 'question', 'reviewer_id', 'created_at']


class QuestionBulkImportSerializer(serializers.Serializer):
    """Serializer for bulk question import."""

    questions = serializers.ListField(
        child=serializers.DictField(),
        min_length=1,
        help_text="List of question data dictionaries"
    )


class QuestionCSVImportSerializer(serializers.Serializer):
    """Serializer for CSV question import."""

    csv_content = serializers.CharField(
        help_text="CSV file content as string"
    )


class QuestionExportSerializer(serializers.Serializer):
    """Serializer for question export request."""

    category = serializers.CharField(required=False, allow_blank=True)
    format = serializers.ChoiceField(
        choices=['json', 'csv'],
        default='json'
    )


class QuestionStatisticsSerializer(serializers.Serializer):
    """Serializer for question statistics response."""

    total = serializers.IntegerField()
    active = serializers.IntegerField()
    inactive = serializers.IntegerField()
    by_category = serializers.ListField()
    by_difficulty = serializers.ListField()
    by_review_status = serializers.ListField()
    needs_attention = serializers.DictField()


class PracticeQuestionSerializer(serializers.Serializer):
    """Serializer for practice question response."""

    id = serializers.UUIDField()
    type = serializers.CharField()
    text = serializers.CharField()
    html = serializers.CharField(allow_null=True)
    image_url = serializers.URLField(allow_null=True)
    audio_url = serializers.URLField(allow_null=True)
    options = serializers.ListField(allow_null=True)
    category = serializers.CharField()
    subcategory = serializers.CharField(allow_blank=True)
    difficulty = serializers.CharField()
    points = serializers.IntegerField()


class PracticeAnswerSerializer(serializers.Serializer):
    """Serializer for practice answer submission."""

    question_id = serializers.UUIDField()
    answer = serializers.JSONField()
    time_spent_seconds = serializers.IntegerField(required=False)


class PracticeAnswerResultSerializer(serializers.Serializer):
    """Serializer for practice answer result."""

    correct = serializers.BooleanField()
    partial_score = serializers.FloatField(allow_null=True)
    correct_answer = serializers.JSONField()
    explanation = serializers.CharField(allow_blank=True)
    explanation_html = serializers.CharField(allow_blank=True)
    explanation_image_url = serializers.URLField(allow_null=True)
    hint = serializers.CharField(allow_null=True)
    difficulty = serializers.CharField()
    success_rate = serializers.FloatField(allow_null=True)
