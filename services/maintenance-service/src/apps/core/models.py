"""
Maintenance Service Models.
"""
from django.db import models
from django.core.validators import MinValueValidator
from shared.common.mixins import UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin


class MaintenanceTask(UUIDPrimaryKeyMixin, TimestampMixin, models.Model):
    """
    Defines maintenance tasks that need to be performed on aircraft.
    """
    class TaskType(models.TextChoices):
        INSPECTION = 'inspection', 'Inspection'
        REPAIR = 'repair', 'Repair'
        MODIFICATION = 'modification', 'Modification'
        OVERHAUL = 'overhaul', 'Overhaul'
        SERVICE = 'service', 'Service'
        AD_COMPLIANCE = 'ad_compliance', 'AD Compliance'
        SB_COMPLIANCE = 'sb_compliance', 'SB Compliance'

    class IntervalType(models.TextChoices):
        HOURS = 'hours', 'Flight Hours'
        CYCLES = 'cycles', 'Cycles'
        CALENDAR = 'calendar', 'Calendar Days'
        ANNUAL = 'annual', 'Annual'
        CONDITION = 'condition', 'Condition Based'

    aircraft_type_id = models.UUIDField(null=True, blank=True)  # If applicable to type
    aircraft_id = models.UUIDField(null=True, blank=True)  # If specific to aircraft
    organization_id = models.UUIDField()

    # Task definition
    task_code = models.CharField(max_length=50, unique=True)
    title = models.CharField(max_length=255)
    description = models.TextField()
    task_type = models.CharField(max_length=20, choices=TaskType.choices)

    # Scheduling
    interval_type = models.CharField(max_length=20, choices=IntervalType.choices)
    interval_value = models.IntegerField(null=True, blank=True)

    # Reference docs
    reference_document = models.CharField(max_length=255, blank=True)
    procedure_reference = models.CharField(max_length=255, blank=True)

    # Estimates
    estimated_hours = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    estimated_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    # Parts required
    parts_required = models.JSONField(default=list, blank=True)

    # Status
    is_active = models.BooleanField(default=True)
    is_mandatory = models.BooleanField(default=True)

    class Meta:
        db_table = 'maintenance_tasks'
        ordering = ['task_code']
        indexes = [
            models.Index(fields=['task_code']),
            models.Index(fields=['aircraft_id']),
            models.Index(fields=['organization_id']),
        ]

    def __str__(self):
        return f"{self.task_code} - {self.title}"


class MaintenanceRecord(UUIDPrimaryKeyMixin, TimestampMixin, models.Model):
    """
    Records of completed maintenance work.
    """
    class Status(models.TextChoices):
        SCHEDULED = 'scheduled', 'Scheduled'
        IN_PROGRESS = 'in_progress', 'In Progress'
        COMPLETED = 'completed', 'Completed'
        DEFERRED = 'deferred', 'Deferred'
        CANCELLED = 'cancelled', 'Cancelled'

    aircraft_id = models.UUIDField()
    organization_id = models.UUIDField()
    task = models.ForeignKey(
        MaintenanceTask,
        on_delete=models.PROTECT,
        related_name='records',
        null=True,
        blank=True
    )

    # Work details
    work_order_number = models.CharField(max_length=50, unique=True)
    title = models.CharField(max_length=255)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SCHEDULED)

    # Scheduling
    scheduled_date = models.DateField()
    scheduled_start_time = models.TimeField(null=True, blank=True)
    scheduled_end_time = models.TimeField(null=True, blank=True)

    # Actual timing
    actual_start = models.DateTimeField(null=True, blank=True)
    actual_completion = models.DateTimeField(null=True, blank=True)
    actual_hours = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)

    # Aircraft state at time of maintenance
    aircraft_hours_at_maintenance = models.DecimalField(max_digits=10, decimal_places=1, null=True, blank=True)
    aircraft_cycles_at_maintenance = models.IntegerField(null=True, blank=True)

    # Personnel
    performed_by_id = models.UUIDField(null=True, blank=True)
    supervisor_id = models.UUIDField(null=True, blank=True)
    inspector_id = models.UUIDField(null=True, blank=True)

    # Certification
    certified_date = models.DateTimeField(null=True, blank=True)
    certification_reference = models.CharField(max_length=255, blank=True)
    release_to_service = models.BooleanField(default=False)

    # Parts used
    parts_used = models.JSONField(default=list, blank=True)

    # Costs
    labor_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    parts_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    total_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    # Documentation
    notes = models.TextField(blank=True)
    attachments = models.JSONField(default=list, blank=True)

    class Meta:
        db_table = 'maintenance_records'
        ordering = ['-scheduled_date']
        indexes = [
            models.Index(fields=['work_order_number']),
            models.Index(fields=['aircraft_id']),
            models.Index(fields=['status']),
            models.Index(fields=['scheduled_date']),
        ]

    def __str__(self):
        return f"{self.work_order_number} - {self.title}"


class MaintenanceSchedule(UUIDPrimaryKeyMixin, TimestampMixin, models.Model):
    """
    Scheduled maintenance events for aircraft.
    """
    class Status(models.TextChoices):
        UPCOMING = 'upcoming', 'Upcoming'
        DUE = 'due', 'Due'
        OVERDUE = 'overdue', 'Overdue'
        COMPLETED = 'completed', 'Completed'

    aircraft_id = models.UUIDField()
    organization_id = models.UUIDField()
    task = models.ForeignKey(
        MaintenanceTask,
        on_delete=models.PROTECT,
        related_name='schedules'
    )

    # Due tracking
    due_date = models.DateField(null=True, blank=True)
    due_hours = models.DecimalField(max_digits=10, decimal_places=1, null=True, blank=True)
    due_cycles = models.IntegerField(null=True, blank=True)

    # Last completion
    last_completed_date = models.DateField(null=True, blank=True)
    last_completed_hours = models.DecimalField(max_digits=10, decimal_places=1, null=True, blank=True)
    last_completed_cycles = models.IntegerField(null=True, blank=True)
    last_maintenance_record_id = models.UUIDField(null=True, blank=True)

    # Status
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.UPCOMING)
    is_active = models.BooleanField(default=True)

    # Alerts
    alert_days_before = models.IntegerField(default=30)
    alert_hours_before = models.DecimalField(max_digits=10, decimal_places=1, default=10)
    alert_sent = models.BooleanField(default=False)

    class Meta:
        db_table = 'maintenance_schedules'
        ordering = ['due_date']
        indexes = [
            models.Index(fields=['aircraft_id']),
            models.Index(fields=['status']),
            models.Index(fields=['due_date']),
        ]

    def __str__(self):
        return f"{self.task.task_code} - Due: {self.due_date}"


class MELItem(UUIDPrimaryKeyMixin, TimestampMixin, models.Model):
    """
    Minimum Equipment List items for deferred maintenance.
    """
    class Category(models.TextChoices):
        A = 'A', 'Category A - May be inoperative'
        B = 'B', 'Category B - 3 day deferral'
        C = 'C', 'Category C - 10 day deferral'
        D = 'D', 'Category D - 120 day deferral'

    class Status(models.TextChoices):
        ACTIVE = 'active', 'Active'
        CLEARED = 'cleared', 'Cleared'
        EXPIRED = 'expired', 'Expired'

    aircraft_id = models.UUIDField()
    organization_id = models.UUIDField()
    squawk_id = models.UUIDField(null=True, blank=True)  # Link to aircraft squawk

    # MEL details
    mel_reference = models.CharField(max_length=50)
    item_number = models.CharField(max_length=50)
    category = models.CharField(max_length=1, choices=Category.choices)

    # Description
    title = models.CharField(max_length=255)
    description = models.TextField()
    affected_system = models.CharField(max_length=100)

    # Deferral tracking
    deferred_date = models.DateField()
    expiry_date = models.DateField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)

    # Personnel
    deferred_by_id = models.UUIDField()
    approved_by_id = models.UUIDField(null=True, blank=True)

    # Operations & Maintenance (O&M) procedures
    operational_procedures = models.TextField(blank=True)
    maintenance_procedures = models.TextField(blank=True)
    placard_required = models.BooleanField(default=False)
    placard_location = models.CharField(max_length=255, blank=True)

    # Clearance
    cleared_date = models.DateField(null=True, blank=True)
    cleared_by_id = models.UUIDField(null=True, blank=True)
    clearance_record_id = models.UUIDField(null=True, blank=True)  # Link to maintenance record
    clearance_notes = models.TextField(blank=True)

    # Documentation
    attachments = models.JSONField(default=list, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = 'mel_items'
        ordering = ['-deferred_date']
        indexes = [
            models.Index(fields=['aircraft_id']),
            models.Index(fields=['status']),
            models.Index(fields=['expiry_date']),
            models.Index(fields=['mel_reference']),
        ]

    def __str__(self):
        return f"{self.mel_reference} - {self.title}"
