from django.contrib import admin
from .models import MaintenanceTask, MaintenanceRecord, MaintenanceSchedule, MELItem


@admin.register(MaintenanceTask)
class MaintenanceTaskAdmin(admin.ModelAdmin):
    list_display = ['task_code', 'title', 'task_type', 'interval_type', 'interval_value', 'is_active']
    list_filter = ['task_type', 'interval_type', 'is_active', 'is_mandatory']
    search_fields = ['task_code', 'title', 'description']
    ordering = ['task_code']


@admin.register(MaintenanceRecord)
class MaintenanceRecordAdmin(admin.ModelAdmin):
    list_display = ['work_order_number', 'title', 'status', 'scheduled_date', 'actual_completion']
    list_filter = ['status', 'release_to_service']
    search_fields = ['work_order_number', 'title', 'description']
    ordering = ['-scheduled_date']


@admin.register(MaintenanceSchedule)
class MaintenanceScheduleAdmin(admin.ModelAdmin):
    list_display = ['task', 'aircraft_id', 'due_date', 'due_hours', 'status', 'is_active']
    list_filter = ['status', 'is_active']
    search_fields = ['task__task_code', 'task__title']
    ordering = ['due_date']


@admin.register(MELItem)
class MELItemAdmin(admin.ModelAdmin):
    list_display = ['mel_reference', 'title', 'category', 'deferred_date', 'expiry_date', 'status']
    list_filter = ['category', 'status', 'placard_required']
    search_fields = ['mel_reference', 'title', 'description']
    ordering = ['-deferred_date']
