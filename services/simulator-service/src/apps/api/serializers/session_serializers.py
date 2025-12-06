# services/simulator-service/src/apps/api/serializers/session_serializers.py
"""
FSTD Session Serializers
"""

from rest_framework import serializers
from apps.core.models import FSTDSession


class FSTDSessionListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views"""

    duration_hours = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        read_only=True
    )
    is_signed = serializers.BooleanField(read_only=True)

    class Meta:
        model = FSTDSession
        fields = [
            'id',
            'session_date',
            'session_type',
            'status',
            'trainee_name',
            'instructor_name',
            'fstd_device_name',
            'scheduled_start',
            'scheduled_end',
            'duration_hours',
            'assessment_result',
            'is_signed',
        ]


class FSTDSessionSerializer(serializers.ModelSerializer):
    """Full serializer for detail views"""

    duration_hours = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        read_only=True
    )
    total_duration_hours = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        read_only=True
    )
    is_signed = serializers.BooleanField(read_only=True)
    logbook_entry = serializers.SerializerMethodField()

    class Meta:
        model = FSTDSession
        fields = '__all__'
        read_only_fields = [
            'id',
            'created_at',
            'updated_at',
            'actual_duration_minutes',
            'cancelled_at',
            'instructor_signed_at',
            'trainee_signed_at',
            'examiner_signed_at',
        ]

    def get_logbook_entry(self, obj):
        if obj.status == 'completed':
            return obj.get_logbook_entry()
        return None


class FSTDSessionCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating sessions"""

    class Meta:
        model = FSTDSession
        fields = [
            'fstd_device_id',
            'booking_id',
            'trainee_id',
            'trainee_name',
            'second_trainee_id',
            'second_trainee_name',
            'instructor_id',
            'instructor_name',
            'instructor_certificate_number',
            'examiner_id',
            'examiner_name',
            'examiner_certificate_number',
            'session_date',
            'scheduled_start',
            'scheduled_end',
            'scheduled_duration_minutes',
            'briefing_duration_minutes',
            'debriefing_duration_minutes',
            'session_type',
            'training_program_id',
            'lesson_id',
            'course_id',
            'exercises_planned',
            'scenario_description',
            'aircraft_type',
            'departure_airport',
            'arrival_airport',
            'notes',
        ]

    def create(self, validated_data):
        request = self.context.get('request')
        if request and hasattr(request, 'organization_id'):
            validated_data['organization_id'] = request.organization_id
        if request and hasattr(request, 'user'):
            validated_data['created_by'] = request.user.id
        return super().create(validated_data)


class SessionAssessmentSerializer(serializers.Serializer):
    """Serializer for session assessment updates"""

    assessment_result = serializers.ChoiceField(
        choices=FSTDSession.AssessmentResult if hasattr(FSTDSession, 'AssessmentResult') else [
            ('pass', 'Pass'),
            ('fail', 'Fail'),
            ('partial', 'Partial Pass'),
            ('incomplete', 'Incomplete'),
        ]
    )
    grade = serializers.CharField(max_length=20, required=False, allow_blank=True)
    competency_grades = serializers.JSONField(required=False)
    exercises_completed = serializers.JSONField(required=False)
    instructor_remarks = serializers.CharField(required=False, allow_blank=True)
    areas_for_improvement = serializers.CharField(required=False, allow_blank=True)
    strengths = serializers.CharField(required=False, allow_blank=True)
    recommendations = serializers.CharField(required=False, allow_blank=True)


class SessionSignatureSerializer(serializers.Serializer):
    """Serializer for session signatures"""

    signature_data = serializers.JSONField(
        help_text="Digital signature data (base64 image or signature object)"
    )
    signer_type = serializers.ChoiceField(
        choices=['instructor', 'trainee', 'examiner']
    )
