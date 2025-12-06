"""
Report Template Serializers.
"""
from rest_framework import serializers
from ...models import ReportTemplate


class ReportTemplateListSerializer(serializers.ModelSerializer):
    """Serializer for listing report templates."""
    report_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = ReportTemplate
        fields = [
            'id', 'name', 'description', 'report_type', 'data_source',
            'chart_type', 'is_public', 'is_active', 'created_at', 'report_count'
        ]
        read_only_fields = fields


class ReportTemplateSerializer(serializers.ModelSerializer):
    """Full serializer for report templates."""

    class Meta:
        model = ReportTemplate
        fields = [
            'id', 'organization_id', 'name', 'description', 'report_type',
            'data_source', 'query_config', 'chart_type', 'visualization_config',
            'columns', 'grouping', 'sorting', 'is_public', 'allowed_roles',
            'created_by_id', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'organization_id', 'created_by_id', 'created_at', 'updated_at']


class ReportTemplateCreateSerializer(serializers.Serializer):
    """Serializer for creating report templates."""
    name = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    report_type = serializers.ChoiceField(choices=ReportTemplate.ReportType.choices)
    data_source = serializers.CharField(max_length=100)
    query_config = serializers.JSONField(required=False, default=dict)
    chart_type = serializers.CharField(max_length=50, required=False, allow_blank=True, default="")
    visualization_config = serializers.JSONField(required=False, default=dict)
    columns = serializers.ListField(child=serializers.DictField())
    grouping = serializers.ListField(required=False, default=list)
    sorting = serializers.ListField(required=False, default=list)
    is_public = serializers.BooleanField(default=False)
    allowed_roles = serializers.ListField(required=False, default=list)


class ReportTemplateUpdateSerializer(serializers.Serializer):
    """Serializer for updating report templates."""
    name = serializers.CharField(max_length=255, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    data_source = serializers.CharField(max_length=100, required=False)
    query_config = serializers.JSONField(required=False)
    chart_type = serializers.CharField(max_length=50, required=False, allow_blank=True)
    visualization_config = serializers.JSONField(required=False)
    columns = serializers.ListField(child=serializers.DictField(), required=False)
    grouping = serializers.ListField(required=False)
    sorting = serializers.ListField(required=False)
    is_public = serializers.BooleanField(required=False)
    allowed_roles = serializers.ListField(required=False)
