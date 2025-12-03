# services/theory-service/src/apps/core/api/serializers/enrollment_serializers.py
"""
Enrollment Serializers

Serializers for enrollment-related API endpoints.
"""

from rest_framework import serializers

from ...models import (
    CourseEnrollment,
    ModuleProgress,
    EnrollmentStatus,
)


class ModuleProgressSerializer(serializers.ModelSerializer):
    """Serializer for module progress."""

    module_name = serializers.CharField(source='module.name', read_only=True)
    sort_order = serializers.IntegerField(source='module.sort_order', read_only=True)
    time_spent_minutes = serializers.ReadOnlyField()

    class Meta:
        model = ModuleProgress
        fields = [
            'id',
            'module',
            'module_name',
            'sort_order',
            'started_at',
            'completed_at',
            'completed',
            'time_spent_seconds',
            'time_spent_minutes',
            'view_count',
            'video_watched_percentage',
            'video_last_position_seconds',
            'content_scroll_percentage',
            'quiz_attempted',
            'quiz_passed',
            'quiz_score',
            'quiz_attempts',
            'bookmarked',
            'last_accessed_at',
        ]
        read_only_fields = [
            'id', 'module', 'started_at', 'completed_at', 'view_count',
            'quiz_attempts', 'last_accessed_at'
        ]


class EnrollmentListSerializer(serializers.ModelSerializer):
    """Serializer for enrollment list view."""

    course_code = serializers.CharField(source='course.code', read_only=True)
    course_name = serializers.CharField(source='course.name', read_only=True)
    is_active = serializers.ReadOnlyField()
    is_expired = serializers.ReadOnlyField()
    days_since_enrollment = serializers.ReadOnlyField()
    days_until_expiry = serializers.ReadOnlyField()
    total_time_spent_hours = serializers.ReadOnlyField()

    class Meta:
        model = CourseEnrollment
        fields = [
            'id',
            'course',
            'course_code',
            'course_name',
            'user_id',
            'status',
            'enrolled_at',
            'started_at',
            'completed_at',
            'expires_at',
            'progress_percentage',
            'modules_completed',
            'modules_total',
            'total_time_spent_seconds',
            'total_time_spent_hours',
            'exam_attempts',
            'best_score',
            'passed',
            'certificate_issued',
            'is_active',
            'is_expired',
            'days_since_enrollment',
            'days_until_expiry',
            'last_accessed_at',
        ]


class EnrollmentDetailSerializer(serializers.ModelSerializer):
    """Serializer for enrollment detail view."""

    course_code = serializers.CharField(source='course.code', read_only=True)
    course_name = serializers.CharField(source='course.name', read_only=True)
    module_progress = ModuleProgressSerializer(many=True, read_only=True)
    is_active = serializers.ReadOnlyField()
    is_expired = serializers.ReadOnlyField()
    days_since_enrollment = serializers.ReadOnlyField()
    days_until_expiry = serializers.ReadOnlyField()
    total_time_spent_hours = serializers.ReadOnlyField()

    class Meta:
        model = CourseEnrollment
        fields = [
            'id',
            'organization_id',
            'course',
            'course_code',
            'course_name',
            'user_id',
            'status',
            'enrolled_at',
            'started_at',
            'completed_at',
            'expires_at',
            'progress_percentage',
            'modules_completed',
            'modules_total',
            'total_time_spent_seconds',
            'total_time_spent_hours',
            'exam_attempts',
            'best_score',
            'latest_score',
            'passed',
            'passed_at',
            'certificate_issued',
            'certificate_id',
            'certificate_url',
            'is_active',
            'is_expired',
            'days_since_enrollment',
            'days_until_expiry',
            'last_accessed_at',
            'last_module_id',
            'last_activity',
            'rating',
            'review',
            'reviewed_at',
            'notes',
            'completion_details',
            'module_progress',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id', 'organization_id', 'user_id', 'enrolled_at', 'started_at',
            'completed_at', 'modules_completed', 'modules_total',
            'total_time_spent_seconds', 'exam_attempts', 'best_score',
            'latest_score', 'passed', 'passed_at', 'certificate_issued',
            'certificate_id', 'certificate_url', 'last_accessed_at',
            'last_module_id', 'last_activity', 'reviewed_at',
            'created_at', 'updated_at'
        ]


class EnrollmentCreateSerializer(serializers.Serializer):
    """Serializer for creating enrollments."""

    course_id = serializers.UUIDField()
    expires_in_days = serializers.IntegerField(required=False, allow_null=True)


class ModuleActivitySerializer(serializers.Serializer):
    """Serializer for recording module activity."""

    time_spent_seconds = serializers.IntegerField(default=0)
    video_watched_percentage = serializers.IntegerField(required=False, min_value=0, max_value=100)
    video_position_seconds = serializers.IntegerField(required=False)
    scroll_percentage = serializers.IntegerField(required=False, min_value=0, max_value=100)


class QuizResultSerializer(serializers.Serializer):
    """Serializer for module quiz results."""

    score = serializers.DecimalField(max_digits=5, decimal_places=2)
    passed = serializers.BooleanField()


class ReviewSerializer(serializers.Serializer):
    """Serializer for course reviews."""

    rating = serializers.IntegerField(min_value=1, max_value=5)
    review = serializers.CharField(required=False, allow_blank=True)


class SuspendEnrollmentSerializer(serializers.Serializer):
    """Serializer for suspending enrollment."""

    reason = serializers.CharField(required=False, allow_blank=True)


class ReactivateEnrollmentSerializer(serializers.Serializer):
    """Serializer for reactivating enrollment."""

    extend_days = serializers.IntegerField(required=False, allow_null=True)


class EnrollmentProgressSerializer(serializers.Serializer):
    """Serializer for enrollment progress response."""

    enrollment_id = serializers.UUIDField()
    course_id = serializers.UUIDField()
    course_name = serializers.CharField()
    status = serializers.CharField()
    progress_percentage = serializers.FloatField()
    modules_completed = serializers.IntegerField()
    modules_total = serializers.IntegerField()
    time_spent_hours = serializers.FloatField()
    exam_attempts = serializers.IntegerField()
    best_score = serializers.FloatField(allow_null=True)
    passed = serializers.BooleanField()
    certificate_issued = serializers.BooleanField()
    days_since_enrollment = serializers.IntegerField()
    days_until_expiry = serializers.IntegerField(allow_null=True)
    last_accessed_at = serializers.DateTimeField(allow_null=True)
    modules = serializers.ListField()
    next_module = serializers.DictField(allow_null=True)
    course_summary = serializers.DictField()


class UserCoursesSerializer(serializers.Serializer):
    """Serializer for user's enrolled courses."""

    in_progress = EnrollmentListSerializer(many=True)
    completed = EnrollmentListSerializer(many=True)
    expired = EnrollmentListSerializer(many=True)
