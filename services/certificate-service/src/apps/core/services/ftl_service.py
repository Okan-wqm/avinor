# services/certificate-service/src/apps/core/services/ftl_service.py
"""
Flight Time Limitations (FTL) Service

Business logic for FTL compliance and fatigue management.
Implements EASA ORO.FTL and FAA Part 117 regulations.
"""

import logging
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Any, Optional, Tuple
from uuid import UUID

from django.db import transaction
from django.db.models import Sum, Q
from django.utils import timezone

from ..models import (
    FTLConfiguration,
    DutyPeriod,
    DutyType,
    RestPeriod,
    FTLViolation,
    FTLViolationType,
    PilotFTLSummary,
    FTLStandard,
)

logger = logging.getLogger(__name__)


class FTLService:
    """
    Service class for Flight Time Limitations operations.

    Handles duty period tracking, rest requirements,
    and FTL compliance checking.
    """

    # ==========================================================================
    # CONFIGURATION
    # ==========================================================================

    @staticmethod
    def get_or_create_config(
        organization_id: UUID,
    ) -> FTLConfiguration:
        """
        Get or create FTL configuration for organization.

        Args:
            organization_id: Organization UUID

        Returns:
            FTLConfiguration instance
        """
        config, created = FTLConfiguration.objects.get_or_create(
            organization_id=organization_id,
            defaults={'ftl_standard': FTLStandard.EASA_FTL}
        )

        if created:
            logger.info(f"Created default FTL configuration for org {organization_id}")

        return config

    @staticmethod
    @transaction.atomic
    def update_config(
        organization_id: UUID,
        **kwargs
    ) -> FTLConfiguration:
        """
        Update FTL configuration.

        Args:
            organization_id: Organization UUID
            **kwargs: Configuration fields to update

        Returns:
            Updated configuration
        """
        config = FTLService.get_or_create_config(organization_id)

        for field, value in kwargs.items():
            if hasattr(config, field):
                setattr(config, field, value)

        config.save()
        logger.info(f"Updated FTL configuration for org {organization_id}")

        return config

    # ==========================================================================
    # DUTY PERIOD OPERATIONS
    # ==========================================================================

    @staticmethod
    @transaction.atomic
    def start_duty_period(
        organization_id: UUID,
        user_id: UUID,
        duty_type: str,
        start_time: datetime,
        start_location: str = None,
        is_planned: bool = False,
        is_augmented: bool = False,
        timezone_name: str = 'UTC',
    ) -> Dict[str, Any]:
        """
        Start a new duty period.

        Args:
            organization_id: Organization UUID
            user_id: User UUID
            duty_type: Type of duty
            start_time: Duty start time (UTC)
            start_location: Starting location (ICAO)
            is_planned: Is this a planned/future duty
            is_augmented: Is crew augmented

        Returns:
            Duty period information
        """
        duty = DutyPeriod.objects.create(
            organization_id=organization_id,
            user_id=user_id,
            duty_type=duty_type,
            duty_date=start_time.date(),
            start_time=start_time,
            start_time_local=start_time,  # TODO: Convert to local
            timezone=timezone_name,
            start_location=start_location,
            is_planned=is_planned,
            is_augmented=is_augmented,
        )

        # Update FTL summary
        FTLService._update_pilot_status(organization_id, user_id, 'on_duty')

        logger.info(f"Started {duty_type} for user {user_id}")

        return duty.get_duty_info()

    @staticmethod
    @transaction.atomic
    def end_duty_period(
        duty_id: UUID,
        end_time: datetime,
        end_location: str = None,
        flight_time_hours: Decimal = None,
        sectors: int = None,
        flight_ids: List[UUID] = None,
        notes: str = None,
    ) -> Dict[str, Any]:
        """
        End a duty period.

        Args:
            duty_id: Duty period UUID
            end_time: Duty end time (UTC)
            end_location: Ending location (ICAO)
            flight_time_hours: Total flight time during duty
            sectors: Number of flight sectors
            flight_ids: Associated flight IDs

        Returns:
            Updated duty period information
        """
        duty = DutyPeriod.objects.get(id=duty_id)
        duty.end_time = end_time
        duty.end_time_local = end_time  # TODO: Convert to local
        duty.end_location = end_location
        duty.is_completed = True

        if flight_time_hours is not None:
            duty.flight_time_hours = flight_time_hours
        if sectors is not None:
            duty.sectors = sectors
        if flight_ids:
            duty.flight_ids = flight_ids
        if notes:
            duty.notes = notes

        duty.save()

        # Check for FTL violations
        violations = FTLService.check_duty_violations(duty)

        # Update summary
        FTLService.recalculate_summary(duty.organization_id, duty.user_id)

        logger.info(f"Ended duty period {duty_id}")

        return {
            **duty.get_duty_info(),
            'violations': violations,
        }

    @staticmethod
    @transaction.atomic
    def record_rest_period(
        organization_id: UUID,
        user_id: UUID,
        start_time: datetime,
        end_time: datetime = None,
        location: str = None,
        accommodation_type: str = None,
        is_suitable_accommodation: bool = True,
        is_reduced_rest: bool = False,
        is_weekly_rest: bool = False,
        preceding_duty_id: UUID = None,
    ) -> Dict[str, Any]:
        """
        Record a rest period.

        Args:
            organization_id: Organization UUID
            user_id: User UUID
            start_time: Rest start time
            end_time: Rest end time (optional)
            location: Rest location
            ... additional fields

        Returns:
            Rest period information
        """
        preceding_duty = None
        if preceding_duty_id:
            preceding_duty = DutyPeriod.objects.get(id=preceding_duty_id)

        rest = RestPeriod.objects.create(
            organization_id=organization_id,
            user_id=user_id,
            rest_date=start_time.date(),
            start_time=start_time,
            end_time=end_time,
            location=location,
            accommodation_type=accommodation_type,
            is_suitable_accommodation=is_suitable_accommodation,
            is_reduced_rest=is_reduced_rest,
            is_weekly_rest=is_weekly_rest,
            preceding_duty=preceding_duty,
        )

        # Update pilot status
        FTLService._update_pilot_status(organization_id, user_id, 'resting')

        logger.info(f"Recorded rest period for user {user_id}")

        return {
            'rest_id': str(rest.id),
            'start_time': rest.start_time.isoformat(),
            'end_time': rest.end_time.isoformat() if rest.end_time else None,
            'duration_hours': float(rest.duration_hours),
            'location': rest.location,
        }

    # ==========================================================================
    # COMPLIANCE CHECKING
    # ==========================================================================

    @staticmethod
    def check_duty_violations(
        duty: DutyPeriod,
    ) -> List[Dict[str, Any]]:
        """
        Check for FTL violations in a completed duty period.

        Args:
            duty: Completed DutyPeriod instance

        Returns:
            List of violations found
        """
        if not duty.is_completed:
            return []

        config = FTLService.get_or_create_config(duty.organization_id)
        violations = []

        # Check FDP limit
        if duty.duty_type == DutyType.FLIGHT_DUTY:
            max_fdp = config.max_fdp_extended if duty.is_augmented else config.max_fdp_standard

            if duty.duration_hours > max_fdp:
                violation = FTLViolation.objects.create(
                    organization_id=duty.organization_id,
                    user_id=duty.user_id,
                    violation_type=FTLViolationType.FDP_EXCEEDED,
                    violation_date=duty.duty_date,
                    limit_name='Maximum FDP',
                    limit_value=max_fdp,
                    actual_value=duty.duration_hours,
                    exceeded_by=duty.duration_hours - max_fdp,
                    period_start=duty.duty_date,
                    period_end=duty.duty_date,
                    severity=FTLViolation.Severity.HIGH,
                    duty_period=duty,
                )
                violations.append({
                    'type': 'fdp_exceeded',
                    'limit': float(max_fdp),
                    'actual': float(duty.duration_hours),
                    'exceeded_by': float(duty.duration_hours - max_fdp),
                })

        # Check daily flight time
        if duty.flight_time_hours > config.max_flight_time_daily:
            violation = FTLViolation.objects.create(
                organization_id=duty.organization_id,
                user_id=duty.user_id,
                violation_type=FTLViolationType.FLIGHT_TIME_EXCEEDED,
                violation_date=duty.duty_date,
                limit_name='Maximum Daily Flight Time',
                limit_value=config.max_flight_time_daily,
                actual_value=duty.flight_time_hours,
                exceeded_by=duty.flight_time_hours - config.max_flight_time_daily,
                period_start=duty.duty_date,
                period_end=duty.duty_date,
                severity=FTLViolation.Severity.HIGH,
                duty_period=duty,
            )
            violations.append({
                'type': 'flight_time_exceeded',
                'limit': float(config.max_flight_time_daily),
                'actual': float(duty.flight_time_hours),
            })

        return violations

    @staticmethod
    def check_cumulative_limits(
        organization_id: UUID,
        user_id: UUID,
    ) -> Dict[str, Any]:
        """
        Check cumulative FTL limits.

        Args:
            organization_id: Organization UUID
            user_id: User UUID

        Returns:
            Cumulative limits check result
        """
        config = FTLService.get_or_create_config(organization_id)
        today = date.today()
        now = timezone.now()

        issues = []
        warnings = []

        # Calculate periods
        seven_days_ago = today - timedelta(days=7)
        twenty_eight_days_ago = today - timedelta(days=28)
        year_start = date(today.year, 1, 1)

        # Get flight time totals
        duties = DutyPeriod.objects.filter(
            organization_id=organization_id,
            user_id=user_id,
            is_completed=True,
        )

        # 7-day flight time
        flight_time_7 = duties.filter(
            duty_date__gte=seven_days_ago
        ).aggregate(total=Sum('flight_time_hours'))['total'] or Decimal('0')

        if flight_time_7 > config.max_flight_time_7_days:
            issues.append({
                'type': 'flight_time_7_days',
                'limit': float(config.max_flight_time_7_days),
                'actual': float(flight_time_7),
                'severity': 'error',
            })
        elif flight_time_7 > config.max_flight_time_7_days * Decimal('0.9'):
            warnings.append({
                'type': 'flight_time_7_days',
                'limit': float(config.max_flight_time_7_days),
                'actual': float(flight_time_7),
                'remaining': float(config.max_flight_time_7_days - flight_time_7),
            })

        # 28-day flight time
        flight_time_28 = duties.filter(
            duty_date__gte=twenty_eight_days_ago
        ).aggregate(total=Sum('flight_time_hours'))['total'] or Decimal('0')

        if flight_time_28 > config.max_flight_time_28_days:
            issues.append({
                'type': 'flight_time_28_days',
                'limit': float(config.max_flight_time_28_days),
                'actual': float(flight_time_28),
                'severity': 'error',
            })

        # Calendar year flight time
        flight_time_year = duties.filter(
            duty_date__gte=year_start
        ).aggregate(total=Sum('flight_time_hours'))['total'] or Decimal('0')

        if flight_time_year > config.max_flight_time_calendar_year:
            issues.append({
                'type': 'flight_time_year',
                'limit': float(config.max_flight_time_calendar_year),
                'actual': float(flight_time_year),
                'severity': 'error',
            })

        # 7-day duty time
        duty_time_7 = duties.filter(
            duty_date__gte=seven_days_ago
        ).aggregate(total=Sum('duration_hours'))['total'] or Decimal('0')

        if duty_time_7 > config.max_duty_7_days:
            issues.append({
                'type': 'duty_time_7_days',
                'limit': float(config.max_duty_7_days),
                'actual': float(duty_time_7),
                'severity': 'error',
            })

        return {
            'user_id': str(user_id),
            'is_compliant': len(issues) == 0,
            'flight_time': {
                '7_days': float(flight_time_7),
                '28_days': float(flight_time_28),
                'calendar_year': float(flight_time_year),
            },
            'duty_time': {
                '7_days': float(duty_time_7),
            },
            'limits': {
                'flight_time_7_days': float(config.max_flight_time_7_days),
                'flight_time_28_days': float(config.max_flight_time_28_days),
                'flight_time_year': float(config.max_flight_time_calendar_year),
                'duty_7_days': float(config.max_duty_7_days),
            },
            'issues': issues,
            'warnings': warnings,
            'checked_at': now.isoformat(),
        }

    @staticmethod
    def check_rest_requirements(
        organization_id: UUID,
        user_id: UUID,
    ) -> Dict[str, Any]:
        """
        Check rest requirements compliance.

        Args:
            organization_id: Organization UUID
            user_id: User UUID

        Returns:
            Rest requirements check result
        """
        config = FTLService.get_or_create_config(organization_id)
        today = date.today()

        issues = []
        warnings = []

        # Get last rest period
        last_rest = RestPeriod.objects.filter(
            organization_id=organization_id,
            user_id=user_id,
        ).order_by('-end_time').first()

        if last_rest and last_rest.end_time:
            rest_duration = last_rest.duration_hours

            if rest_duration < config.min_rest_after_fdp:
                issues.append({
                    'type': 'insufficient_rest',
                    'required': float(config.min_rest_after_fdp),
                    'actual': float(rest_duration),
                    'severity': 'error',
                })

        # Check weekly rest
        seven_days_ago = today - timedelta(days=7)
        weekly_rests = RestPeriod.objects.filter(
            organization_id=organization_id,
            user_id=user_id,
            is_weekly_rest=True,
            rest_date__gte=seven_days_ago,
        ).count()

        if weekly_rests == 0:
            # Check if any rest period meets weekly rest duration
            long_rest = RestPeriod.objects.filter(
                organization_id=organization_id,
                user_id=user_id,
                rest_date__gte=seven_days_ago,
                duration_hours__gte=config.min_weekly_rest,
            ).exists()

            if not long_rest:
                warnings.append({
                    'type': 'weekly_rest_due',
                    'message': 'Weekly rest period may be required',
                })

        # Count days off
        days_off_7 = FTLService._count_days_off(
            organization_id, user_id, seven_days_ago, today
        )

        if days_off_7 < config.days_off_per_7_days:
            issues.append({
                'type': 'insufficient_days_off',
                'required': config.days_off_per_7_days,
                'actual': days_off_7,
                'period': '7_days',
                'severity': 'warning',
            })

        return {
            'user_id': str(user_id),
            'is_compliant': len([i for i in issues if i.get('severity') == 'error']) == 0,
            'last_rest': {
                'end_time': last_rest.end_time.isoformat() if last_rest and last_rest.end_time else None,
                'duration_hours': float(last_rest.duration_hours) if last_rest else None,
            } if last_rest else None,
            'days_off_last_7': days_off_7,
            'issues': issues,
            'warnings': warnings,
        }

    @staticmethod
    def validate_planned_duty(
        organization_id: UUID,
        user_id: UUID,
        start_time: datetime,
        estimated_duration_hours: Decimal,
        estimated_flight_time_hours: Decimal = Decimal('0'),
        is_augmented: bool = False,
    ) -> Dict[str, Any]:
        """
        Validate a planned duty period before scheduling.

        Args:
            organization_id: Organization UUID
            user_id: User UUID
            start_time: Planned start time
            estimated_duration_hours: Estimated duty duration
            estimated_flight_time_hours: Estimated flight time
            is_augmented: Whether crew is augmented

        Returns:
            Validation result
        """
        config = FTLService.get_or_create_config(organization_id)

        issues = []
        warnings = []

        # Check FDP limit
        max_fdp = config.max_fdp_extended if is_augmented else config.max_fdp_standard
        if estimated_duration_hours > max_fdp:
            issues.append({
                'type': 'fdp_exceeded',
                'message': f'Planned FDP ({estimated_duration_hours}h) exceeds limit ({max_fdp}h)',
                'severity': 'error',
            })

        # Check cumulative limits
        cumulative = FTLService.check_cumulative_limits(organization_id, user_id)

        # Will this duty exceed 7-day limit?
        new_7_day_total = Decimal(str(cumulative['flight_time']['7_days'])) + estimated_flight_time_hours
        if new_7_day_total > config.max_flight_time_7_days:
            issues.append({
                'type': 'cumulative_exceeded',
                'message': f'Would exceed 7-day flight time limit',
                'current': cumulative['flight_time']['7_days'],
                'planned': float(estimated_flight_time_hours),
                'limit': float(config.max_flight_time_7_days),
                'severity': 'error',
            })

        # Check rest since last duty
        last_duty = DutyPeriod.objects.filter(
            organization_id=organization_id,
            user_id=user_id,
            is_completed=True,
        ).order_by('-end_time').first()

        if last_duty and last_duty.end_time:
            rest_hours = Decimal(str((start_time - last_duty.end_time).total_seconds() / 3600))
            if rest_hours < config.min_rest_between_duties:
                issues.append({
                    'type': 'insufficient_rest',
                    'message': f'Only {rest_hours:.1f}h rest since last duty (min {config.min_rest_between_duties}h)',
                    'severity': 'error',
                })

        is_valid = len([i for i in issues if i.get('severity') == 'error']) == 0

        return {
            'is_valid': is_valid,
            'can_schedule': is_valid,
            'max_fdp_available': float(max_fdp),
            'issues': issues,
            'warnings': warnings,
        }

    # ==========================================================================
    # SUMMARY OPERATIONS
    # ==========================================================================

    @staticmethod
    @transaction.atomic
    def recalculate_summary(
        organization_id: UUID,
        user_id: UUID,
    ) -> PilotFTLSummary:
        """
        Recalculate FTL summary for a pilot.

        Args:
            organization_id: Organization UUID
            user_id: User UUID

        Returns:
            Updated PilotFTLSummary instance
        """
        config = FTLService.get_or_create_config(organization_id)
        today = date.today()
        now = timezone.now()

        # Get or create summary
        summary, _ = PilotFTLSummary.objects.get_or_create(
            organization_id=organization_id,
            user_id=user_id,
        )

        # Calculate date ranges
        seven_days_ago = today - timedelta(days=7)
        fourteen_days_ago = today - timedelta(days=14)
        twenty_eight_days_ago = today - timedelta(days=28)
        year_start = date(today.year, 1, 1)

        # Get completed duties
        duties = DutyPeriod.objects.filter(
            organization_id=organization_id,
            user_id=user_id,
            is_completed=True,
        )

        # Today's flight time
        summary.flight_time_today = duties.filter(
            duty_date=today
        ).aggregate(total=Sum('flight_time_hours'))['total'] or Decimal('0')

        # Rolling totals
        summary.flight_time_7_days = duties.filter(
            duty_date__gte=seven_days_ago
        ).aggregate(total=Sum('flight_time_hours'))['total'] or Decimal('0')

        summary.flight_time_28_days = duties.filter(
            duty_date__gte=twenty_eight_days_ago
        ).aggregate(total=Sum('flight_time_hours'))['total'] or Decimal('0')

        summary.flight_time_calendar_year = duties.filter(
            duty_date__gte=year_start
        ).aggregate(total=Sum('flight_time_hours'))['total'] or Decimal('0')

        # Duty time totals
        summary.duty_time_7_days = duties.filter(
            duty_date__gte=seven_days_ago
        ).aggregate(total=Sum('duration_hours'))['total'] or Decimal('0')

        summary.duty_time_14_days = duties.filter(
            duty_date__gte=fourteen_days_ago
        ).aggregate(total=Sum('duration_hours'))['total'] or Decimal('0')

        summary.duty_time_28_days = duties.filter(
            duty_date__gte=twenty_eight_days_ago
        ).aggregate(total=Sum('duration_hours'))['total'] or Decimal('0')

        # Last FDP
        last_fdp = duties.filter(
            duty_type=DutyType.FLIGHT_DUTY
        ).order_by('-end_time').first()

        if last_fdp:
            summary.last_fdp_end = last_fdp.end_time
            summary.last_fdp_duration = last_fdp.duration_hours

        # Last rest
        last_rest = RestPeriod.objects.filter(
            organization_id=organization_id,
            user_id=user_id,
        ).order_by('-end_time').first()

        if last_rest:
            summary.last_rest_start = last_rest.start_time
            summary.last_rest_end = last_rest.end_time
            summary.last_rest_duration = last_rest.duration_hours

        # Days off
        summary.days_off_last_7 = FTLService._count_days_off(
            organization_id, user_id, seven_days_ago, today
        )
        summary.days_off_last_14 = FTLService._count_days_off(
            organization_id, user_id, fourteen_days_ago, today
        )

        # Calculate max available FDP
        summary.max_fdp_available = FTLService._calculate_max_fdp(
            config, summary
        )

        # Check compliance
        issues = []
        if summary.flight_time_7_days > config.max_flight_time_7_days:
            issues.append('7-day flight time exceeded')
        if summary.flight_time_28_days > config.max_flight_time_28_days:
            issues.append('28-day flight time exceeded')
        if summary.days_off_last_7 < config.days_off_per_7_days:
            issues.append('Insufficient days off')

        summary.is_compliant = len(issues) == 0
        summary.compliance_issues = issues

        # Determine current status
        active_duty = DutyPeriod.objects.filter(
            organization_id=organization_id,
            user_id=user_id,
            is_completed=False,
        ).first()

        if active_duty:
            summary.current_status = PilotFTLSummary.AvailabilityStatus.ON_DUTY
        elif last_rest and not last_rest.end_time:
            summary.current_status = PilotFTLSummary.AvailabilityStatus.RESTING
        elif not summary.is_compliant:
            summary.current_status = PilotFTLSummary.AvailabilityStatus.LIMIT_REACHED
        else:
            summary.current_status = PilotFTLSummary.AvailabilityStatus.AVAILABLE

        summary.save()

        return summary

    @staticmethod
    def get_pilot_ftl_status(
        organization_id: UUID,
        user_id: UUID,
    ) -> Dict[str, Any]:
        """
        Get comprehensive FTL status for a pilot.

        Args:
            organization_id: Organization UUID
            user_id: User UUID

        Returns:
            FTL status dictionary
        """
        # Ensure summary is up to date
        summary = FTLService.recalculate_summary(organization_id, user_id)

        # Get config for limits
        config = FTLService.get_or_create_config(organization_id)

        # Get active violations
        active_violations = FTLViolation.objects.filter(
            organization_id=organization_id,
            user_id=user_id,
            is_resolved=False,
        ).count()

        return {
            **summary.get_compliance_summary(),
            'limits': {
                'max_fdp': float(config.max_fdp_standard),
                'max_fdp_extended': float(config.max_fdp_extended),
                'flight_time_7_days': float(config.max_flight_time_7_days),
                'flight_time_28_days': float(config.max_flight_time_28_days),
                'flight_time_year': float(config.max_flight_time_calendar_year),
                'min_rest': float(config.min_rest_after_fdp),
            },
            'active_violations': active_violations,
            'ftl_standard': config.ftl_standard,
        }

    # ==========================================================================
    # PRIVATE HELPERS
    # ==========================================================================

    @staticmethod
    def _update_pilot_status(
        organization_id: UUID,
        user_id: UUID,
        status: str,
    ) -> None:
        """Update pilot's current FTL status."""
        summary, _ = PilotFTLSummary.objects.get_or_create(
            organization_id=organization_id,
            user_id=user_id,
        )

        status_map = {
            'on_duty': PilotFTLSummary.AvailabilityStatus.ON_DUTY,
            'resting': PilotFTLSummary.AvailabilityStatus.RESTING,
            'available': PilotFTLSummary.AvailabilityStatus.AVAILABLE,
            'standby': PilotFTLSummary.AvailabilityStatus.STANDBY,
        }

        summary.current_status = status_map.get(status, PilotFTLSummary.AvailabilityStatus.AVAILABLE)
        summary.save(update_fields=['current_status'])

    @staticmethod
    def _count_days_off(
        organization_id: UUID,
        user_id: UUID,
        start_date: date,
        end_date: date,
    ) -> int:
        """Count days off (no duty) in a period."""
        duty_dates = set(
            DutyPeriod.objects.filter(
                organization_id=organization_id,
                user_id=user_id,
                duty_date__gte=start_date,
                duty_date__lte=end_date,
            ).values_list('duty_date', flat=True)
        )

        total_days = (end_date - start_date).days + 1
        days_off = total_days - len(duty_dates)

        return max(0, days_off)

    @staticmethod
    def _calculate_max_fdp(
        config: FTLConfiguration,
        summary: PilotFTLSummary,
    ) -> Decimal:
        """Calculate maximum available FDP based on current limits."""
        max_fdp = config.max_fdp_standard

        # Reduce if approaching cumulative limits
        remaining_7_day = config.max_flight_time_7_days - summary.flight_time_7_days
        remaining_28_day = config.max_flight_time_28_days - summary.flight_time_28_days

        # Conservative estimate: assume 70% of FDP is actual flight time
        max_from_7_day = remaining_7_day / Decimal('0.7')
        max_from_28_day = remaining_28_day / Decimal('0.7')

        return min(max_fdp, max_from_7_day, max_from_28_day).quantize(Decimal('0.1'))
