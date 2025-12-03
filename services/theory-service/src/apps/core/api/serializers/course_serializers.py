# services/theory-service/src/apps/core/api/serializers/course_serializers.py
"""
Course Serializers

Serializers for course-related API endpoints.
"""

from rest_framework import serializers

from ...models import (
    Course,
    CourseModule,
    CourseAttachment,
    CourseCategory,
    ProgramType,
    CourseStatus,
    ContentType,
)


class CourseModuleSerializer(serializers.ModelSerializer):
    """Serializer for course module details."""

    video_duration_minutes = serializers.ReadOnlyField()
    has_video = serializers.ReadOnlyField()
    has_content = serializers.ReadOnlyField()

    class Meta:
        model = CourseModule
        fields = [
            'id',
            'name',
            'description',
            'sort_order',
            'content_type',
            'video_url',
            'video_duration_seconds',
            'video_duration_minutes',
            'video_thumbnail_url',
            'estimated_minutes',
            'has_quiz',
            'quiz_id',
            'quiz_required',
            'quiz_passing_score',
            'completion_criteria',
            'learning_objectives',
            'key_points',
            'has_video',
            'has_content',
            'is_active',
            'is_preview',
            'view_count',
            'completion_count',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'view_count', 'completion_count']


class CourseModuleCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating course modules."""

    class Meta:
        model = CourseModule
        fields = [
            'name',
            'description',
            'content_type',
            'content',
            'content_html',
            'video_url',
            'video_duration_seconds',
            'video_provider',
            'video_thumbnail_url',
            'audio_url',
            'audio_duration_seconds',
            'document_url',
            'document_pages',
            'estimated_minutes',
            'has_quiz',
            'quiz_id',
            'quiz_required',
            'quiz_passing_score',
            'completion_criteria',
            'learning_objectives',
            'key_points',
            'resources',
            'is_preview',
        ]


class CourseModuleUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating course modules."""

    class Meta:
        model = CourseModule
        fields = [
            'name',
            'description',
            'content_type',
            'content',
            'content_html',
            'video_url',
            'video_duration_seconds',
            'video_provider',
            'video_thumbnail_url',
            'audio_url',
            'audio_duration_seconds',
            'document_url',
            'document_pages',
            'estimated_minutes',
            'has_quiz',
            'quiz_id',
            'quiz_required',
            'quiz_passing_score',
            'completion_criteria',
            'learning_objectives',
            'key_points',
            'resources',
            'is_active',
            'is_preview',
        ]


class CourseAttachmentSerializer(serializers.ModelSerializer):
    """Serializer for course attachments."""

    file_size_mb = serializers.ReadOnlyField()

    class Meta:
        model = CourseAttachment
        fields = [
            'id',
            'name',
            'description',
            'file_url',
            'file_type',
            'file_size_bytes',
            'file_size_mb',
            'sort_order',
            'is_downloadable',
            'requires_enrollment',
            'download_count',
            'created_at',
        ]
        read_only_fields = ['id', 'download_count', 'created_at']


class CourseListSerializer(serializers.ModelSerializer):
    """Serializer for course list view."""

    module_count = serializers.ReadOnlyField()
    is_active = serializers.ReadOnlyField()

    class Meta:
        model = Course
        fields = [
            'id',
            'code',
            'name',
            'short_description',
            'category',
            'program_type',
            'estimated_hours',
            'module_count',
            'min_score_to_pass',
            'status',
            'is_published',
            'is_active',
            'thumbnail_url',
            'enrolled_count',
            'completion_rate',
            'average_score',
            'rating',
            'rating_count',
            'is_free',
            'price',
            'currency',
            'created_at',
        ]


class CourseDetailSerializer(serializers.ModelSerializer):
    """Serializer for course detail view."""

    modules = CourseModuleSerializer(many=True, read_only=True)
    attachments = CourseAttachmentSerializer(many=True, read_only=True)
    module_count = serializers.ReadOnlyField()
    total_duration_minutes = serializers.ReadOnlyField()
    is_active = serializers.ReadOnlyField()

    class Meta:
        model = Course
        fields = [
            'id',
            'organization_id',
            'code',
            'name',
            'description',
            'short_description',
            'category',
            'subcategory',
            'program_type',
            'estimated_hours',
            'prerequisites',
            'min_score_to_pass',
            'require_module_completion',
            'require_final_exam',
            'status',
            'is_published',
            'published_at',
            'is_active',
            'thumbnail_url',
            'banner_url',
            'enrolled_count',
            'completion_count',
            'completion_rate',
            'average_score',
            'average_duration_hours',
            'rating',
            'rating_count',
            'tags',
            'learning_objectives',
            'is_free',
            'price',
            'currency',
            'settings',
            'module_count',
            'total_duration_minutes',
            'modules',
            'attachments',
            'created_at',
            'updated_at',
            'created_by',
        ]
        read_only_fields = [
            'id', 'organization_id', 'published_at', 'enrolled_count',
            'completion_count', 'completion_rate', 'average_score',
            'average_duration_hours', 'rating', 'rating_count',
            'created_at', 'updated_at', 'created_by'
        ]


class CourseCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating courses."""

    class Meta:
        model = Course
        fields = [
            'code',
            'name',
            'description',
            'short_description',
            'category',
            'subcategory',
            'program_type',
            'estimated_hours',
            'prerequisites',
            'min_score_to_pass',
            'require_module_completion',
            'require_final_exam',
            'thumbnail_url',
            'banner_url',
            'tags',
            'learning_objectives',
            'is_free',
            'price',
            'currency',
            'settings',
        ]

    def validate_category(self, value):
        """Validate category is a valid choice."""
        if value not in CourseCategory.values:
            raise serializers.ValidationError(
                f"Invalid category. Must be one of: {CourseCategory.values}"
            )
        return value


class CourseUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating courses."""

    class Meta:
        model = Course
        fields = [
            'name',
            'description',
            'short_description',
            'subcategory',
            'program_type',
            'estimated_hours',
            'prerequisites',
            'min_score_to_pass',
            'require_module_completion',
            'require_final_exam',
            'thumbnail_url',
            'banner_url',
            'tags',
            'learning_objectives',
            'is_free',
            'price',
            'currency',
            'settings',
        ]


class ModuleReorderSerializer(serializers.Serializer):
    """Serializer for reordering modules."""

    module_order = serializers.ListField(
        child=serializers.UUIDField(),
        help_text="List of module IDs in desired order"
    )


class CourseCloneSerializer(serializers.Serializer):
    """Serializer for cloning a course."""

    new_code = serializers.CharField(max_length=50)
    new_name = serializers.CharField(max_length=255, required=False, allow_blank=True)


class CoursePublishSerializer(serializers.Serializer):
    """Serializer for publishing a course."""

    # No fields needed, just triggers publish action
    pass


class CourseStatisticsSerializer(serializers.Serializer):
    """Serializer for course statistics response."""

    course_id = serializers.UUIDField()
    enrollment = serializers.DictField()
    time = serializers.DictField()
    exams = serializers.DictField()
    modules = serializers.ListField()
    rating = serializers.DictField()
