# services/theory-service/src/apps/core/api/serializers/exam_serializers.py
"""
Exam Serializers

Serializers for exam-related API endpoints.
"""

from rest_framework import serializers

from ...models import (
    Exam,
    ExamAttempt,
    ExamQuestion,
    ExamType,
    ExamStatus,
    QuestionSelection,
    PassingType,
    AttemptStatus,
)


class ExamListSerializer(serializers.ModelSerializer):
    """Serializer for exam list view."""

    is_active = serializers.ReadOnlyField()
    is_timed = serializers.ReadOnlyField()
    course_name = serializers.CharField(source='course.name', read_only=True, allow_null=True)

    class Meta:
        model = Exam
        fields = [
            'id',
            'code',
            'name',
            'description',
            'exam_type',
            'course',
            'course_name',
            'total_questions',
            'time_limit_minutes',
            'passing_score',
            'max_attempts',
            'status',
            'is_published',
            'is_active',
            'is_timed',
            'attempt_count',
            'pass_rate',
            'average_score',
            'available_from',
            'available_until',
            'created_at',
        ]


class ExamDetailSerializer(serializers.ModelSerializer):
    """Serializer for exam detail view."""

    is_active = serializers.ReadOnlyField()
    is_timed = serializers.ReadOnlyField()
    course_name = serializers.CharField(source='course.name', read_only=True, allow_null=True)
    module_name = serializers.CharField(source='module.name', read_only=True, allow_null=True)

    class Meta:
        model = Exam
        fields = [
            'id',
            'organization_id',
            'code',
            'name',
            'description',
            'instructions',
            'exam_type',
            'course',
            'course_name',
            'module',
            'module_name',
            'question_selection',
            'fixed_questions',
            'random_rules',
            'total_questions',
            'questions_per_page',
            'time_limit_minutes',
            'allow_pause',
            'max_pause_count',
            'max_pause_duration_minutes',
            'passing_score',
            'passing_type',
            'category_passing_scores',
            'max_attempts',
            'retry_delay_hours',
            'cooldown_after_fail_hours',
            'allow_review',
            'allow_skip',
            'allow_back_navigation',
            'force_answer_before_next',
            'show_correct_answers',
            'show_explanation',
            'show_results_immediately',
            'show_score_during_exam',
            'show_category_breakdown',
            'randomize_questions',
            'randomize_options',
            'require_proctoring',
            'browser_lockdown',
            'prevent_copy_paste',
            'require_webcam',
            'require_id_verification',
            'max_tab_switches',
            'available_from',
            'available_until',
            'scheduled_windows',
            'status',
            'is_published',
            'published_at',
            'is_active',
            'is_timed',
            'attempt_count',
            'pass_count',
            'fail_count',
            'pass_rate',
            'average_score',
            'average_duration_minutes',
            'pass_message',
            'fail_message',
            'certificate_template_id',
            'settings',
            'created_at',
            'updated_at',
            'created_by',
        ]
        read_only_fields = [
            'id', 'organization_id', 'published_at', 'attempt_count',
            'pass_count', 'fail_count', 'pass_rate', 'average_score',
            'average_duration_minutes', 'created_at', 'updated_at', 'created_by'
        ]


class ExamCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating exams."""

    class Meta:
        model = Exam
        fields = [
            'code',
            'name',
            'description',
            'instructions',
            'exam_type',
            'course',
            'module',
            'question_selection',
            'fixed_questions',
            'random_rules',
            'total_questions',
            'questions_per_page',
            'time_limit_minutes',
            'allow_pause',
            'max_pause_count',
            'max_pause_duration_minutes',
            'passing_score',
            'passing_type',
            'category_passing_scores',
            'max_attempts',
            'retry_delay_hours',
            'cooldown_after_fail_hours',
            'allow_review',
            'allow_skip',
            'allow_back_navigation',
            'force_answer_before_next',
            'show_correct_answers',
            'show_explanation',
            'show_results_immediately',
            'show_score_during_exam',
            'show_category_breakdown',
            'randomize_questions',
            'randomize_options',
            'require_proctoring',
            'browser_lockdown',
            'prevent_copy_paste',
            'require_webcam',
            'require_id_verification',
            'max_tab_switches',
            'available_from',
            'available_until',
            'scheduled_windows',
            'pass_message',
            'fail_message',
            'certificate_template_id',
            'settings',
        ]

    def validate(self, data):
        """Validate exam configuration."""
        question_selection = data.get('question_selection', QuestionSelection.RANDOM)
        total_questions = data.get('total_questions', 0)

        if question_selection == QuestionSelection.FIXED:
            fixed_questions = data.get('fixed_questions', [])
            if len(fixed_questions) < total_questions:
                raise serializers.ValidationError({
                    'fixed_questions': f'Need at least {total_questions} fixed questions'
                })
        else:
            random_rules = data.get('random_rules', [])
            if not random_rules:
                raise serializers.ValidationError({
                    'random_rules': 'Random selection requires random_rules'
                })
            total_from_rules = sum(rule.get('count', 0) for rule in random_rules)
            if total_from_rules < total_questions:
                raise serializers.ValidationError({
                    'random_rules': f'Rules must provide at least {total_questions} questions'
                })

        return data


class ExamUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating exams."""

    class Meta:
        model = Exam
        fields = [
            'name',
            'description',
            'instructions',
            'questions_per_page',
            'time_limit_minutes',
            'allow_pause',
            'max_pause_count',
            'max_pause_duration_minutes',
            'max_attempts',
            'retry_delay_hours',
            'cooldown_after_fail_hours',
            'allow_review',
            'allow_skip',
            'allow_back_navigation',
            'force_answer_before_next',
            'show_correct_answers',
            'show_explanation',
            'show_results_immediately',
            'show_score_during_exam',
            'show_category_breakdown',
            'randomize_questions',
            'randomize_options',
            'require_proctoring',
            'browser_lockdown',
            'prevent_copy_paste',
            'require_webcam',
            'require_id_verification',
            'max_tab_switches',
            'available_from',
            'available_until',
            'scheduled_windows',
            'pass_message',
            'fail_message',
            'certificate_template_id',
            'settings',
        ]


class ExamStartSerializer(serializers.Serializer):
    """Serializer for starting an exam."""

    enrollment_id = serializers.UUIDField(required=False)


class ExamStartResponseSerializer(serializers.Serializer):
    """Serializer for exam start response."""

    attempt_id = serializers.UUIDField()
    exam_id = serializers.UUIDField()
    exam_name = serializers.CharField()
    instructions = serializers.CharField(allow_blank=True)
    total_questions = serializers.IntegerField()
    total_points = serializers.IntegerField()
    time_limit_minutes = serializers.IntegerField(allow_null=True)
    time_limit_at = serializers.DateTimeField(allow_null=True)
    allow_pause = serializers.BooleanField()
    allow_skip = serializers.BooleanField()
    allow_review = serializers.BooleanField()
    allow_back_navigation = serializers.BooleanField()
    questions = serializers.ListField()


class ExamAnswerSerializer(serializers.Serializer):
    """Serializer for submitting an answer."""

    question_id = serializers.UUIDField()
    answer = serializers.JSONField()
    time_spent_seconds = serializers.IntegerField(required=False, default=0)
    flagged = serializers.BooleanField(required=False, default=False)


class ExamFlagSerializer(serializers.Serializer):
    """Serializer for flagging a question."""

    question_id = serializers.UUIDField()
    flagged = serializers.BooleanField(default=True)


class ExamAttemptSerializer(serializers.ModelSerializer):
    """Serializer for exam attempt list."""

    exam_name = serializers.CharField(source='exam.name', read_only=True)
    is_active = serializers.ReadOnlyField()
    is_completed = serializers.ReadOnlyField()
    progress_percentage = serializers.ReadOnlyField()
    duration_minutes = serializers.ReadOnlyField()

    class Meta:
        model = ExamAttempt
        fields = [
            'id',
            'exam',
            'exam_name',
            'attempt_number',
            'status',
            'started_at',
            'completed_at',
            'time_spent_seconds',
            'total_points',
            'earned_points',
            'score_percentage',
            'passed',
            'grade',
            'correct_count',
            'incorrect_count',
            'unanswered_count',
            'is_active',
            'is_completed',
            'progress_percentage',
            'duration_minutes',
        ]


class ExamResultSerializer(serializers.Serializer):
    """Serializer for exam results."""

    attempt_id = serializers.UUIDField()
    exam_id = serializers.UUIDField()
    exam_name = serializers.CharField()
    status = serializers.CharField()
    started_at = serializers.DateTimeField()
    completed_at = serializers.DateTimeField(allow_null=True)
    time_spent_minutes = serializers.IntegerField()
    total_questions = serializers.IntegerField()
    correct_count = serializers.IntegerField()
    incorrect_count = serializers.IntegerField()
    unanswered_count = serializers.IntegerField()
    earned_points = serializers.IntegerField()
    total_points = serializers.IntegerField()
    score_percentage = serializers.FloatField()
    passed = serializers.BooleanField(allow_null=True)
    grade = serializers.CharField(allow_blank=True)
    passing_score = serializers.IntegerField()
    results_by_category = serializers.DictField(required=False)
    question_results = serializers.ListField(required=False)


class ExamStatisticsSerializer(serializers.Serializer):
    """Serializer for exam statistics."""

    exam_id = serializers.UUIDField()
    exam_name = serializers.CharField()
    total_attempts = serializers.IntegerField()
    pass_rate = serializers.FloatField()
    average_score = serializers.FloatField()
    score_distribution = serializers.DictField()
    time_statistics = serializers.DictField()


class RandomRuleSerializer(serializers.Serializer):
    """Serializer for random question selection rules."""

    category = serializers.CharField()
    count = serializers.IntegerField(min_value=1)
    difficulty = serializers.CharField(required=False)
    subcategory = serializers.CharField(required=False)
    tags = serializers.ListField(child=serializers.CharField(), required=False)


class SetRandomRulesSerializer(serializers.Serializer):
    """Serializer for setting random rules."""

    rules = serializers.ListField(
        child=RandomRuleSerializer(),
        min_length=1
    )


class AddFixedQuestionsSerializer(serializers.Serializer):
    """Serializer for adding fixed questions."""

    question_ids = serializers.ListField(
        child=serializers.UUIDField(),
        min_length=1
    )
