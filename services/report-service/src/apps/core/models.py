"""
Report Service Models.
"""
from django.db import models
from django.core.validators import MinValueValidator
from shared.common.mixins import UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin


class ReportTemplate(UUIDPrimaryKeyMixin, TimestampMixin, models.Model):
    """
    Templates for generating reports.
    """
    class ReportType(models.TextChoices):
        FINANCIAL = 'financial', 'Financial Report'
        FLIGHT_ACTIVITY = 'flight_activity', 'Flight Activity'
        STUDENT_PROGRESS = 'student_progress', 'Student Progress'
        AIRCRAFT_UTILIZATION = 'aircraft_utilization', 'Aircraft Utilization'
        MAINTENANCE = 'maintenance', 'Maintenance Report'
        INSTRUCTOR_ACTIVITY = 'instructor_activity', 'Instructor Activity'
        CUSTOM = 'custom', 'Custom Report'

    organization_id = models.UUIDField()

    # Template details
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    report_type = models.CharField(max_length=30, choices=ReportType.choices)

    # Query configuration
    data_source = models.CharField(max_length=100)  # Which service to query
    query_config = models.JSONField(default=dict)  # Filters, aggregations, etc.

    # Visualization
    chart_type = models.CharField(max_length=50, blank=True)  # bar, line, pie, table, etc.
    visualization_config = models.JSONField(default=dict, blank=True)

    # Layout
    columns = models.JSONField(default=list)  # Column definitions
    grouping = models.JSONField(default=list, blank=True)
    sorting = models.JSONField(default=list, blank=True)

    # Permissions
    is_public = models.BooleanField(default=False)
    allowed_roles = models.JSONField(default=list, blank=True)
    created_by_id = models.UUIDField()

    # Status
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'report_templates'
        ordering = ['name']
        indexes = [
            models.Index(fields=['organization_id']),
            models.Index(fields=['report_type']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return self.name


class Report(UUIDPrimaryKeyMixin, TimestampMixin, models.Model):
    """
    Generated report instances.
    """
    class Status(models.TextChoices):
        GENERATING = 'generating', 'Generating'
        COMPLETED = 'completed', 'Completed'
        FAILED = 'failed', 'Failed'

    class Format(models.TextChoices):
        PDF = 'pdf', 'PDF'
        EXCEL = 'excel', 'Excel'
        CSV = 'csv', 'CSV'
        JSON = 'json', 'JSON'
        HTML = 'html', 'HTML'

    template = models.ForeignKey(
        ReportTemplate,
        on_delete=models.CASCADE,
        related_name='reports'
    )
    organization_id = models.UUIDField()

    # Report details
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    # Parameters
    parameters = models.JSONField(default=dict)  # Date range, filters, etc.
    generated_by_id = models.UUIDField()
    generated_at = models.DateTimeField(auto_now_add=True)

    # Data
    data = models.JSONField(default=dict, blank=True)  # Cached result data
    row_count = models.IntegerField(default=0)

    # Output
    output_format = models.CharField(max_length=20, choices=Format.choices, default=Format.PDF)
    file_url = models.URLField(blank=True)
    file_size_bytes = models.BigIntegerField(default=0)

    # Status
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.GENERATING)
    error_message = models.TextField(blank=True)

    # Processing time
    processing_time_seconds = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)

    # Expiry
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'reports'
        ordering = ['-generated_at']
        indexes = [
            models.Index(fields=['organization_id']),
            models.Index(fields=['template']),
            models.Index(fields=['generated_by_id']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.title} - {self.generated_at.strftime('%Y-%m-%d')}"


class ReportSchedule(UUIDPrimaryKeyMixin, TimestampMixin, models.Model):
    """
    Scheduled automatic report generation.
    """
    class Frequency(models.TextChoices):
        DAILY = 'daily', 'Daily'
        WEEKLY = 'weekly', 'Weekly'
        MONTHLY = 'monthly', 'Monthly'
        QUARTERLY = 'quarterly', 'Quarterly'
        YEARLY = 'yearly', 'Yearly'

    template = models.ForeignKey(
        ReportTemplate,
        on_delete=models.CASCADE,
        related_name='schedules'
    )
    organization_id = models.UUIDField()

    # Schedule details
    name = models.CharField(max_length=255)
    frequency = models.CharField(max_length=20, choices=Frequency.choices)

    # Timing
    time_of_day = models.TimeField()
    day_of_week = models.IntegerField(null=True, blank=True)  # 0=Monday, 6=Sunday
    day_of_month = models.IntegerField(null=True, blank=True)  # 1-31

    # Parameters
    parameters = models.JSONField(default=dict)  # Default parameters for generation

    # Recipients
    recipient_user_ids = models.JSONField(default=list)  # Users to send report to
    recipient_emails = models.JSONField(default=list)  # Additional email addresses

    # Output
    output_formats = models.JSONField(default=list)  # ['pdf', 'excel']

    # Status
    is_active = models.BooleanField(default=True)
    last_run = models.DateTimeField(null=True, blank=True)
    next_run = models.DateTimeField()

    # Ownership
    created_by_id = models.UUIDField()

    class Meta:
        db_table = 'report_schedules'
        ordering = ['next_run']
        indexes = [
            models.Index(fields=['organization_id']),
            models.Index(fields=['is_active', 'next_run']),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_frequency_display()})"


class Dashboard(UUIDPrimaryKeyMixin, TimestampMixin, models.Model):
    """
    Dashboard configurations.
    """
    organization_id = models.UUIDField()

    # Dashboard details
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    # Layout
    layout_config = models.JSONField(default=dict)  # Grid positions, sizes

    # Permissions
    is_public = models.BooleanField(default=False)
    allowed_roles = models.JSONField(default=list, blank=True)
    owner_id = models.UUIDField()

    # Status
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)

    class Meta:
        db_table = 'dashboards'
        ordering = ['name']
        indexes = [
            models.Index(fields=['organization_id']),
            models.Index(fields=['owner_id']),
        ]

    def __str__(self):
        return self.name


class Widget(UUIDPrimaryKeyMixin, TimestampMixin, models.Model):
    """
    Dashboard widgets (charts, metrics, etc.).
    """
    class WidgetType(models.TextChoices):
        CHART = 'chart', 'Chart'
        METRIC = 'metric', 'Single Metric'
        TABLE = 'table', 'Data Table'
        GAUGE = 'gauge', 'Gauge'
        MAP = 'map', 'Map'
        TEXT = 'text', 'Text/HTML'

    dashboard = models.ForeignKey(
        Dashboard,
        on_delete=models.CASCADE,
        related_name='widgets'
    )

    # Widget details
    title = models.CharField(max_length=255)
    widget_type = models.CharField(max_length=20, choices=WidgetType.choices)

    # Data source
    data_source = models.CharField(max_length=100)  # Which service/endpoint
    query_config = models.JSONField(default=dict)

    # Visualization
    visualization_config = models.JSONField(default=dict)

    # Position
    position_x = models.IntegerField(default=0)
    position_y = models.IntegerField(default=0)
    width = models.IntegerField(default=4)
    height = models.IntegerField(default=3)

    # Refresh
    auto_refresh = models.BooleanField(default=False)
    refresh_interval_seconds = models.IntegerField(default=300)

    # Cache
    cache_duration_seconds = models.IntegerField(default=60)
    last_cached_at = models.DateTimeField(null=True, blank=True)
    cached_data = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'widgets'
        ordering = ['position_y', 'position_x']
        indexes = [
            models.Index(fields=['dashboard']),
        ]

    def __str__(self):
        return f"{self.title} ({self.get_widget_type_display()})"
