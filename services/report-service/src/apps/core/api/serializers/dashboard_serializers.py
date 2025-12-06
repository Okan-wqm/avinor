"""
Dashboard Serializers.
"""
from rest_framework import serializers
from ...models import Dashboard, Widget


class WidgetMinimalSerializer(serializers.ModelSerializer):
    """Minimal widget serializer for dashboard embedding."""

    class Meta:
        model = Widget
        fields = [
            'id', 'title', 'widget_type', 'position_x', 'position_y',
            'width', 'height', 'auto_refresh'
        ]


class DashboardListSerializer(serializers.ModelSerializer):
    """Serializer for listing dashboards."""
    widget_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Dashboard
        fields = [
            'id', 'name', 'description', 'is_public', 'is_default',
            'is_active', 'owner_id', 'widget_count', 'created_at'
        ]
        read_only_fields = fields


class DashboardSerializer(serializers.ModelSerializer):
    """Full serializer for dashboards."""
    widgets = WidgetMinimalSerializer(many=True, read_only=True)

    class Meta:
        model = Dashboard
        fields = [
            'id', 'organization_id', 'name', 'description', 'layout_config',
            'is_public', 'allowed_roles', 'owner_id', 'is_active', 'is_default',
            'widgets', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'organization_id', 'owner_id', 'widgets', 'created_at', 'updated_at']


class DashboardCreateSerializer(serializers.Serializer):
    """Serializer for creating dashboards."""
    name = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    layout_config = serializers.JSONField(required=False, default=dict)
    is_public = serializers.BooleanField(default=False)
    is_default = serializers.BooleanField(default=False)
    allowed_roles = serializers.ListField(required=False, default=list)


class DashboardUpdateSerializer(serializers.Serializer):
    """Serializer for updating dashboards."""
    name = serializers.CharField(max_length=255, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    layout_config = serializers.JSONField(required=False)
    is_public = serializers.BooleanField(required=False)
    is_default = serializers.BooleanField(required=False)
    allowed_roles = serializers.ListField(required=False)
