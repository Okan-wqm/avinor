# services/aircraft-service/src/apps/core/models/time_log.py
"""
Aircraft Time Log Model

Counter history and audit trail for aircraft time tracking.
"""

import uuid
from decimal import Decimal
from datetime import date

from django.db import models


class AircraftTimeLog(models.Model):
    """
    Aircraft time log for tracking counter changes.

    Records all changes to aircraft counters including:
    - Flight time additions
    - Maintenance adjustments
    - Counter corrections
    - Import/migration entries
    """

    class SourceType(models.TextChoices):
        FLIGHT = 'flight', 'Flight'
        MAINTENANCE = 'maintenance', 'Maintenance'
        ADJUSTMENT = 'adjustment', 'Manual Adjustment'
        CORRECTION = 'correction', 'Correction'
        IMPORT = 'import', 'Data Import'
        INITIAL = 'initial', 'Initial Entry'

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    aircraft = models.ForeignKey(
        'Aircraft',
        on_delete=models.CASCADE,
        related_name='time_logs'
    )

    # ==========================================================================
    # Source Information
    # ==========================================================================

    source_type = models.CharField(
        max_length=50,
        choices=SourceType.choices
    )
    source_id = models.UUIDField(
        blank=True,
        null=True,
        help_text='ID of the source record (flight_id, work_order_id, etc.)'
    )
    source_reference = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text='Reference number of source'
    )

    # ==========================================================================
    # Log Date
    # ==========================================================================

    log_date = models.DateField(
        default=date.today,
        help_text='Date of the time change'
    )

    # ==========================================================================
    # Hobbs Time
    # ==========================================================================

    hobbs_before = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True
    )
    hobbs_after = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True
    )
    hobbs_change = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )

    # ==========================================================================
    # Tach Time
    # ==========================================================================

    tach_before = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True
    )
    tach_after = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True
    )
    tach_change = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )

    # ==========================================================================
    # Total Time
    # ==========================================================================

    total_time_before = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True
    )
    total_time_after = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True
    )
    total_time_change = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )

    # ==========================================================================
    # Landings
    # ==========================================================================

    landings_before = models.IntegerField(blank=True, null=True)
    landings_after = models.IntegerField(blank=True, null=True)
    landings_change = models.IntegerField(default=0)

    # ==========================================================================
    # Cycles
    # ==========================================================================

    cycles_before = models.IntegerField(blank=True, null=True)
    cycles_after = models.IntegerField(blank=True, null=True)
    cycles_change = models.IntegerField(default=0)

    # ==========================================================================
    # Engine Times (for multi-engine)
    # ==========================================================================

    engine_times = models.JSONField(
        default=dict,
        blank=True,
        help_text='Engine-specific time changes: {"1": {"before": 100, "after": 101.2, "change": 1.2}}'
    )

    # ==========================================================================
    # Notes
    # ==========================================================================

    notes = models.TextField(
        blank=True,
        null=True,
        help_text='Notes about this time entry'
    )
    adjustment_reason = models.TextField(
        blank=True,
        null=True,
        help_text='Reason for manual adjustment (required for corrections)'
    )

    # ==========================================================================
    # Audit
    # ==========================================================================

    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.UUIDField(
        blank=True,
        null=True,
        help_text='User who created this entry'
    )
    created_by_name = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    class Meta:
        db_table = 'aircraft_time_logs'
        ordering = ['-log_date', '-created_at']
        verbose_name = 'Aircraft Time Log'
        verbose_name_plural = 'Aircraft Time Logs'
        indexes = [
            models.Index(fields=['aircraft', 'log_date']),
            models.Index(fields=['source_type', 'source_id']),
            models.Index(fields=['-created_at']),
        ]

    def __str__(self):
        return f"{self.aircraft.registration} - {self.log_date} ({self.source_type})"

    # ==========================================================================
    # Class Methods
    # ==========================================================================

    @classmethod
    def create_from_flight(
        cls,
        aircraft,
        flight_id: uuid.UUID,
        hobbs_change: Decimal,
        tach_change: Decimal = None,
        landings: int = 0,
        cycles: int = 0,
        flight_date: date = None,
        created_by: uuid.UUID = None,
        notes: str = None
    ) -> 'AircraftTimeLog':
        """Create time log entry from a flight."""
        return cls.objects.create(
            aircraft=aircraft,
            source_type=cls.SourceType.FLIGHT,
            source_id=flight_id,
            log_date=flight_date or date.today(),
            hobbs_before=aircraft.hobbs_time,
            hobbs_after=aircraft.hobbs_time + hobbs_change,
            hobbs_change=hobbs_change,
            tach_before=aircraft.tach_time if tach_change else None,
            tach_after=aircraft.tach_time + tach_change if tach_change else None,
            tach_change=tach_change or Decimal('0.00'),
            total_time_before=aircraft.total_time_hours,
            total_time_after=aircraft.total_time_hours + hobbs_change,
            total_time_change=hobbs_change,
            landings_before=aircraft.total_landings,
            landings_after=aircraft.total_landings + landings,
            landings_change=landings,
            cycles_before=aircraft.total_cycles,
            cycles_after=aircraft.total_cycles + cycles,
            cycles_change=cycles,
            created_by=created_by,
            notes=notes
        )

    @classmethod
    def create_adjustment(
        cls,
        aircraft,
        field: str,
        new_value: Decimal,
        reason: str,
        created_by: uuid.UUID,
        created_by_name: str = None
    ) -> 'AircraftTimeLog':
        """Create time log entry for manual adjustment."""
        log_data = {
            'aircraft': aircraft,
            'source_type': cls.SourceType.ADJUSTMENT,
            'log_date': date.today(),
            'adjustment_reason': reason,
            'created_by': created_by,
            'created_by_name': created_by_name,
        }

        # Set before/after values based on field
        if field == 'hobbs_time':
            log_data['hobbs_before'] = aircraft.hobbs_time
            log_data['hobbs_after'] = new_value
            log_data['hobbs_change'] = new_value - aircraft.hobbs_time
        elif field == 'tach_time':
            log_data['tach_before'] = aircraft.tach_time
            log_data['tach_after'] = new_value
            log_data['tach_change'] = new_value - aircraft.tach_time
        elif field == 'total_time_hours':
            log_data['total_time_before'] = aircraft.total_time_hours
            log_data['total_time_after'] = new_value
            log_data['total_time_change'] = new_value - aircraft.total_time_hours
        elif field == 'total_landings':
            log_data['landings_before'] = aircraft.total_landings
            log_data['landings_after'] = int(new_value)
            log_data['landings_change'] = int(new_value) - aircraft.total_landings
        elif field == 'total_cycles':
            log_data['cycles_before'] = aircraft.total_cycles
            log_data['cycles_after'] = int(new_value)
            log_data['cycles_change'] = int(new_value) - aircraft.total_cycles

        return cls.objects.create(**log_data)

    @classmethod
    def get_history(
        cls,
        aircraft_id: uuid.UUID,
        start_date: date = None,
        end_date: date = None,
        source_type: str = None,
        limit: int = 100
    ):
        """Get time log history for an aircraft."""
        queryset = cls.objects.filter(aircraft_id=aircraft_id)

        if start_date:
            queryset = queryset.filter(log_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(log_date__lte=end_date)
        if source_type:
            queryset = queryset.filter(source_type=source_type)

        return queryset.order_by('-log_date', '-created_at')[:limit]

    @classmethod
    def get_totals_for_period(
        cls,
        aircraft_id: uuid.UUID,
        start_date: date,
        end_date: date
    ) -> dict:
        """Get total time changes for a period."""
        from django.db.models import Sum

        result = cls.objects.filter(
            aircraft_id=aircraft_id,
            log_date__gte=start_date,
            log_date__lte=end_date
        ).aggregate(
            total_hobbs=Sum('hobbs_change'),
            total_tach=Sum('tach_change'),
            total_time=Sum('total_time_change'),
            total_landings=Sum('landings_change'),
            total_cycles=Sum('cycles_change'),
        )

        return {
            'hobbs': float(result['total_hobbs'] or 0),
            'tach': float(result['total_tach'] or 0),
            'total_time': float(result['total_time'] or 0),
            'landings': result['total_landings'] or 0,
            'cycles': result['total_cycles'] or 0,
            'period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat(),
            }
        }
