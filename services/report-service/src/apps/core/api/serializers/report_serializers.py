"""
Report Serializers.
"""
from rest_framework import serializers
from ...models import Report


class ReportListSerializer(serializers.ModelSerializer):
    """Serializer for listing reports."""
    template_name = serializers.CharField(source='template.name', read_only=True)

    class Meta:
        model = Report
        fields = [
            'id', 'title', 'description', 'template_id', 'template_name',
            'status', 'output_format', 'row_count', 'file_size_bytes',
            'generated_at', 'processing_time_seconds'
        ]
        read_only_fields = fields


class ReportSerializer(serializers.ModelSerializer):
    """Full serializer for reports."""
    template_name = serializers.CharField(source='template.name', read_only=True)

    class Meta:
        model = Report
        fields = [
            'id', 'template_id', 'template_name', 'organization_id',
            'title', 'description', 'parameters', 'generated_by_id',
            'generated_at', 'data', 'row_count', 'output_format',
            'file_url', 'file_size_bytes', 'status', 'error_message',
            'processing_time_seconds', 'expires_at', 'created_at'
        ]
        read_only_fields = fields


class ReportCreateSerializer(serializers.Serializer):
    """Serializer for generating reports."""
    template_id = serializers.UUIDField()
    title = serializers.CharField(max_length=255, required=False, allow_blank=True)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    parameters = serializers.JSONField(default=dict)
    output_format = serializers.ChoiceField(
        choices=Report.Format.choices,
        default='pdf'
    )
