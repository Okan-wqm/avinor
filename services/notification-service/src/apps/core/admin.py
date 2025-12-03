from django.contrib import admin
from .models import NotificationTemplate, Notification, NotificationPreference, DeviceToken, NotificationBatch

@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'template_type', 'is_active']
    list_filter = ['template_type', 'is_active']
    search_fields = ['name', 'code']

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['id', 'user_id', 'channel', 'status', 'subject', 'created_at']
    list_filter = ['channel', 'status', 'priority']
    search_fields = ['subject', 'recipient_email']

@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ['user_id', 'email_enabled', 'sms_enabled', 'push_enabled']

@admin.register(DeviceToken)
class DeviceTokenAdmin(admin.ModelAdmin):
    list_display = ['user_id', 'platform', 'is_active', 'last_used_at']
    list_filter = ['platform', 'is_active']

@admin.register(NotificationBatch)
class NotificationBatchAdmin(admin.ModelAdmin):
    list_display = ['name', 'status', 'recipient_count', 'sent_count', 'created_at']
    list_filter = ['status']
