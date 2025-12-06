"""
Schedule Service.

Business logic for managing scheduled reports.
"""
import logging
from typing import Optional, List
from uuid import UUID
from datetime import datetime, timedelta, time as dt_time

from django.db import transaction
from django.db.models import QuerySet
from django.utils import timezone

from ..models import ReportSchedule, ReportTemplate
from ..exceptions import ScheduleNotFound, PermissionDenied
from ..validators import validate_schedule_time, validate_recipients, validate_output_formats
from .report_template_service import ReportTemplateService

logger = logging.getLogger(__name__)


class ScheduleService:
    """Service for managing scheduled reports."""

    @staticmethod
    def get_by_id(schedule_id: UUID, organization_id: UUID) -> ReportSchedule:
        """Get a schedule by ID."""
        try:
            return ReportSchedule.objects.select_related('template').get(
                id=schedule_id,
                organization_id=organization_id
            )
        except ReportSchedule.DoesNotExist:
            raise ScheduleNotFound(detail=f"Schedule with ID {schedule_id} not found.")

    @staticmethod
    def get_list(
        organization_id: UUID,
        template_id: Optional[UUID] = None,
        is_active: Optional[bool] = None,
        created_by_id: Optional[UUID] = None,
    ) -> QuerySet[ReportSchedule]:
        """Get list of schedules."""
        queryset = ReportSchedule.objects.filter(
            organization_id=organization_id
        ).select_related('template')

        if template_id:
            queryset = queryset.filter(template_id=template_id)

        if is_active is not None:
            queryset = queryset.filter(is_active=is_active)

        if created_by_id:
            queryset = queryset.filter(created_by_id=created_by_id)

        return queryset.order_by('next_run')

    @staticmethod
    def get_pending() -> QuerySet[ReportSchedule]:
        """Get schedules that are due to run."""
        return ReportSchedule.objects.filter(
            is_active=True,
            next_run__lte=timezone.now()
        ).select_related('template')

    @staticmethod
    @transaction.atomic
    def create(
        template_id: UUID,
        organization_id: UUID,
        created_by_id: UUID,
        name: str,
        frequency: str,
        time_of_day: dt_time,
        recipient_user_ids: List[UUID],
        output_formats: List[str],
        day_of_week: Optional[int] = None,
        day_of_month: Optional[int] = None,
        parameters: Optional[dict] = None,
        recipient_emails: Optional[List[str]] = None,
    ) -> ReportSchedule:
        """Create a new schedule."""
        # Verify template access
        template = ReportTemplateService.get_by_id(template_id, organization_id)

        # Validate inputs
        validate_schedule_time(frequency, day_of_week, day_of_month)
        validate_recipients(recipient_user_ids, recipient_emails or [])
        validate_output_formats(output_formats)

        # Calculate next run
        next_run = ScheduleService._calculate_next_run(
            frequency=frequency,
            time_of_day=time_of_day,
            day_of_week=day_of_week,
            day_of_month=day_of_month,
        )

        schedule = ReportSchedule.objects.create(
            template=template,
            organization_id=organization_id,
            created_by_id=created_by_id,
            name=name,
            frequency=frequency,
            time_of_day=time_of_day,
            day_of_week=day_of_week,
            day_of_month=day_of_month,
            parameters=parameters or {},
            recipient_user_ids=[str(uid) for uid in recipient_user_ids],
            recipient_emails=recipient_emails or [],
            output_formats=output_formats,
            next_run=next_run,
        )

        logger.info(
            f"Created schedule: {schedule.id}",
            extra={
                'schedule_id': str(schedule.id),
                'template_id': str(template_id),
                'frequency': frequency,
            }
        )

        return schedule

    @staticmethod
    @transaction.atomic
    def update(
        schedule_id: UUID,
        organization_id: UUID,
        user_id: UUID,
        **updates
    ) -> ReportSchedule:
        """Update a schedule."""
        schedule = ScheduleService.get_by_id(schedule_id, organization_id)

        if schedule.created_by_id != user_id:
            raise PermissionDenied(detail="Only the schedule creator can edit it.")

        # Validate updates
        frequency = updates.get('frequency', schedule.frequency)
        day_of_week = updates.get('day_of_week', schedule.day_of_week)
        day_of_month = updates.get('day_of_month', schedule.day_of_month)
        validate_schedule_time(frequency, day_of_week, day_of_month)

        if 'output_formats' in updates:
            validate_output_formats(updates['output_formats'])

        allowed_fields = [
            'name', 'frequency', 'time_of_day', 'day_of_week', 'day_of_month',
            'parameters', 'recipient_user_ids', 'recipient_emails',
            'output_formats', 'is_active'
        ]

        for field, value in updates.items():
            if field in allowed_fields:
                setattr(schedule, field, value)

        # Recalculate next run if timing changed
        if any(k in updates for k in ['frequency', 'time_of_day', 'day_of_week', 'day_of_month']):
            schedule.next_run = ScheduleService._calculate_next_run(
                frequency=schedule.frequency,
                time_of_day=schedule.time_of_day,
                day_of_week=schedule.day_of_week,
                day_of_month=schedule.day_of_month,
            )

        schedule.save()

        logger.info(f"Updated schedule: {schedule.id}")
        return schedule

    @staticmethod
    @transaction.atomic
    def delete(schedule_id: UUID, organization_id: UUID, user_id: UUID) -> None:
        """Delete a schedule."""
        schedule = ScheduleService.get_by_id(schedule_id, organization_id)

        if schedule.created_by_id != user_id:
            raise PermissionDenied(detail="Only the schedule creator can delete it.")

        schedule.delete()
        logger.info(f"Deleted schedule: {schedule_id}")

    @staticmethod
    def toggle_active(schedule_id: UUID, organization_id: UUID, user_id: UUID) -> ReportSchedule:
        """Toggle schedule active status."""
        schedule = ScheduleService.get_by_id(schedule_id, organization_id)

        if schedule.created_by_id != user_id:
            raise PermissionDenied(detail="Only the schedule creator can toggle it.")

        schedule.is_active = not schedule.is_active

        # Recalculate next run if reactivating
        if schedule.is_active:
            schedule.next_run = ScheduleService._calculate_next_run(
                frequency=schedule.frequency,
                time_of_day=schedule.time_of_day,
                day_of_week=schedule.day_of_week,
                day_of_month=schedule.day_of_month,
            )

        schedule.save()

        logger.info(f"Toggled schedule {schedule_id} to active={schedule.is_active}")
        return schedule

    @staticmethod
    def mark_executed(schedule: ReportSchedule) -> None:
        """Mark a schedule as executed and calculate next run."""
        schedule.last_run = timezone.now()
        schedule.next_run = ScheduleService._calculate_next_run(
            frequency=schedule.frequency,
            time_of_day=schedule.time_of_day,
            day_of_week=schedule.day_of_week,
            day_of_month=schedule.day_of_month,
        )
        schedule.save(update_fields=['last_run', 'next_run'])

    @staticmethod
    def _calculate_next_run(
        frequency: str,
        time_of_day: dt_time,
        day_of_week: Optional[int] = None,
        day_of_month: Optional[int] = None,
    ) -> datetime:
        """Calculate the next run time."""
        now = timezone.now()
        today = now.date()

        # Start with today at the specified time
        next_run = timezone.make_aware(
            datetime.combine(today, time_of_day)
        )

        if frequency == 'daily':
            if next_run <= now:
                next_run += timedelta(days=1)

        elif frequency == 'weekly':
            # Find next occurrence of the day of week
            days_ahead = day_of_week - now.weekday()
            if days_ahead <= 0:  # Target day already passed this week
                days_ahead += 7
            next_run = next_run + timedelta(days=days_ahead)
            if next_run <= now:
                next_run += timedelta(days=7)

        elif frequency == 'monthly':
            # Find next occurrence of the day of month
            next_run = next_run.replace(day=min(day_of_month, 28))
            if next_run <= now:
                # Move to next month
                if next_run.month == 12:
                    next_run = next_run.replace(year=next_run.year + 1, month=1)
                else:
                    next_run = next_run.replace(month=next_run.month + 1)

        elif frequency == 'quarterly':
            # Find next quarter start
            current_quarter = (now.month - 1) // 3
            next_quarter_month = ((current_quarter + 1) * 3) % 12 + 1
            next_year = now.year + (1 if next_quarter_month < now.month else 0)
            next_run = next_run.replace(
                year=next_year,
                month=next_quarter_month,
                day=min(day_of_month or 1, 28)
            )

        elif frequency == 'yearly':
            next_run = next_run.replace(day=min(day_of_month or 1, 28))
            if next_run <= now:
                next_run = next_run.replace(year=next_run.year + 1)

        return next_run
