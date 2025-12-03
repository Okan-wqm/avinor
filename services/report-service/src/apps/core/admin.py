from django.contrib import admin
from .models import ReportTemplate, Report, ReportSchedule, Dashboard, Widget


@admin.register(ReportTemplate)
class ReportTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'report_type', 'data_source', 'is_public', 'is_active', 'created_by_id']
    list_filter = ['report_type', 'is_public', 'is_active']
    search_fields = ['name', 'description']
    ordering = ['name']


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ['title', 'template', 'generated_by_id', 'generated_at', 'output_format', 'status', 'row_count']
    list_filter = ['status', 'output_format']
    search_fields = ['title', 'description']
    ordering = ['-generated_at']


@admin.register(ReportSchedule)
class ReportScheduleAdmin(admin.ModelAdmin):
    list_display = ['name', 'template', 'frequency', 'is_active', 'last_run', 'next_run']
    list_filter = ['frequency', 'is_active']
    search_fields = ['name']
    ordering = ['next_run']


@admin.register(Dashboard)
class DashboardAdmin(admin.ModelAdmin):
    list_display = ['name', 'organization_id', 'owner_id', 'is_public', 'is_default', 'is_active']
    list_filter = ['is_public', 'is_default', 'is_active']
    search_fields = ['name', 'description']
    ordering = ['name']


@admin.register(Widget)
class WidgetAdmin(admin.ModelAdmin):
    list_display = ['title', 'dashboard', 'widget_type', 'data_source', 'auto_refresh', 'position_x', 'position_y', 'width', 'height']
    list_filter = ['widget_type', 'auto_refresh']
    search_fields = ['title']
    ordering = ['dashboard', 'position_y', 'position_x']
