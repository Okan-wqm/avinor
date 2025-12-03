"""Notification Service Serializers."""
from rest_framework import serializers
from .models import NotificationTemplate, Notification, NotificationPreference, DeviceToken, NotificationBatch


class NotificationTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationTemplate
        fields = '__all__'


class NotificationSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    channel_display = serializers.CharField(source='get_channel_display', read_only=True)

    class Meta:
        model = Notification
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at', 'sent_at', 'delivered_at', 'read_at']


class NotificationListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'channel', 'status', 'subject', 'created_at', 'read_at']


class NotificationCreateSerializer(serializers.Serializer):
    user_id = serializers.UUIDField()
    channel = serializers.ChoiceField(choices=Notification.Channel.choices, default='email')
    template_code = serializers.CharField(required=False)
    subject = serializers.CharField(required=False)
    body = serializers.CharField(required=False)
    context = serializers.DictField(required=False, default=dict)
    scheduled_at = serializers.DateTimeField(required=False)
    priority = serializers.ChoiceField(choices=Notification.Priority.choices, default='normal')


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationPreference
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at', 'user_id']


class DeviceTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeviceToken
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class NotificationBatchSerializer(serializers.ModelSerializer):
    progress = serializers.SerializerMethodField()

    class Meta:
        model = NotificationBatch
        fields = '__all__'

    def get_progress(self, obj):
        if obj.recipient_count == 0:
            return 0
        return round((obj.sent_count + obj.failed_count) / obj.recipient_count * 100, 1)
