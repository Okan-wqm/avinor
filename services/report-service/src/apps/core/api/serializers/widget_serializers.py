"""
Widget Serializers.
"""
from rest_framework import serializers
from ...models import Widget


class WidgetSerializer(serializers.ModelSerializer):
    """Full serializer for widgets."""

    class Meta:
        model = Widget
        fields = [
            'id', 'dashboard_id', 'title', 'widget_type', 'data_source',
            'query_config', 'visualization_config', 'position_x', 'position_y',
            'width', 'height', 'auto_refresh', 'refresh_interval_seconds',
            'cache_duration_seconds', 'last_cached_at', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'dashboard_id', 'last_cached_at', 'created_at', 'updated_at']


class WidgetCreateSerializer(serializers.Serializer):
    """Serializer for creating widgets."""
    dashboard_id = serializers.UUIDField()
    title = serializers.CharField(max_length=255)
    widget_type = serializers.ChoiceField(choices=Widget.WidgetType.choices)
    data_source = serializers.CharField(max_length=100)
    query_config = serializers.JSONField()
    visualization_config = serializers.JSONField(required=False, default=dict)
    position_x = serializers.IntegerField(default=0, min_value=0)
    position_y = serializers.IntegerField(default=0, min_value=0)
    width = serializers.IntegerField(default=4, min_value=1, max_value=12)
    height = serializers.IntegerField(default=3, min_value=1, max_value=12)
    auto_refresh = serializers.BooleanField(default=False)
    refresh_interval_seconds = serializers.IntegerField(default=300, min_value=10)
    cache_duration_seconds = serializers.IntegerField(default=60, min_value=0)


class WidgetUpdateSerializer(serializers.Serializer):
    """Serializer for updating widgets."""
    title = serializers.CharField(max_length=255, required=False)
    widget_type = serializers.ChoiceField(choices=Widget.WidgetType.choices, required=False)
    data_source = serializers.CharField(max_length=100, required=False)
    query_config = serializers.JSONField(required=False)
    visualization_config = serializers.JSONField(required=False)
    position_x = serializers.IntegerField(required=False, min_value=0)
    position_y = serializers.IntegerField(required=False, min_value=0)
    width = serializers.IntegerField(required=False, min_value=1, max_value=12)
    height = serializers.IntegerField(required=False, min_value=1, max_value=12)
    auto_refresh = serializers.BooleanField(required=False)
    refresh_interval_seconds = serializers.IntegerField(required=False, min_value=10)
    cache_duration_seconds = serializers.IntegerField(required=False, min_value=0)


class WidgetDataSerializer(serializers.Serializer):
    """Serializer for widget data response."""
    data = serializers.JSONField()
    cached = serializers.BooleanField()
    cached_at = serializers.CharField()


class WidgetReorderSerializer(serializers.Serializer):
    """Serializer for reordering widgets."""
    widget_id = serializers.UUIDField()
    x = serializers.IntegerField(min_value=0)
    y = serializers.IntegerField(min_value=0)
    width = serializers.IntegerField(min_value=1, max_value=12)
    height = serializers.IntegerField(min_value=1, max_value=12)
