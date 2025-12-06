"""
Schedule Serializers.
"""
from rest_framework import serializers
from ...models import ReportSchedule


class ScheduleSerializer(serializers.ModelSerializer):
    """Full serializer for schedules."""
    template_name = serializers.CharField(source='template.name', read_only=True)

    class Meta:
        model = ReportSchedule
        fields = [
            'id', 'template_id', 'template_name', 'organization_id',
            'name', 'frequency', 'time_of_day', 'day_of_week', 'day_of_month',
            'parameters', 'recipient_user_ids', 'recipient_emails',
            'output_formats', 'is_active', 'last_run', 'next_run',
            'created_by_id', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'organization_id', 'created_by_id', 'last_run',
            'created_at', 'updated_at'
        ]


class ScheduleCreateSerializer(serializers.Serializer):
    """Serializer for creating schedules."""
    template_id = serializers.UUIDField()
    name = serializers.CharField(max_length=255)
    frequency = serializers.ChoiceField(choices=ReportSchedule.Frequency.choices)
    time_of_day = serializers.TimeField()
    day_of_week = serializers.IntegerField(required=False, allow_null=True, min_value=0, max_value=6)
    day_of_month = serializers.IntegerField(required=False, allow_null=True, min_value=1, max_value=31)
    parameters = serializers.JSONField(required=False, default=dict)
    recipient_user_ids = serializers.ListField(child=serializers.UUIDField())
    recipient_emails = serializers.ListField(
        child=serializers.EmailField(),
        required=False,
        default=list
    )
    output_formats = serializers.ListField(
        child=serializers.ChoiceField(choices=['pdf', 'excel', 'csv', 'json', 'html'])
    )


class ScheduleUpdateSerializer(serializers.Serializer):
    """Serializer for updating schedules."""
    name = serializers.CharField(max_length=255, required=False)
    frequency = serializers.ChoiceField(choices=ReportSchedule.Frequency.choices, required=False)
    time_of_day = serializers.TimeField(required=False)
    day_of_week = serializers.IntegerField(required=False, allow_null=True, min_value=0, max_value=6)
    day_of_month = serializers.IntegerField(required=False, allow_null=True, min_value=1, max_value=31)
    parameters = serializers.JSONField(required=False)
    recipient_user_ids = serializers.ListField(child=serializers.UUIDField(), required=False)
    recipient_emails = serializers.ListField(child=serializers.EmailField(), required=False)
    output_formats = serializers.ListField(
        child=serializers.ChoiceField(choices=['pdf', 'excel', 'csv', 'json', 'html']),
        required=False
    )
    is_active = serializers.BooleanField(required=False)
