# services/booking-service/src/apps/core/services/rule_service.py
"""
Rule Service

Manages booking rules and validation.
"""

import uuid
import logging
from datetime import datetime, date, time, timedelta
from decimal import Decimal
from typing import Optional, Dict, Any, List

from django.db import transaction
from django.utils import timezone

from apps.core.models import Booking, BookingRule

logger = logging.getLogger(__name__)


class RuleService:
    """
    Service for managing booking rules.

    Handles:
    - Rule CRUD
    - Rule validation
    - Rule merging
    """

    # ==========================================================================
    # Rule CRUD
    # ==========================================================================

    @transaction.atomic
    def create_rule(
        self,
        organization_id: uuid.UUID,
        rule_type: str,
        name: str,
        created_by: uuid.UUID = None,
        **kwargs
    ) -> BookingRule:
        """Create a new booking rule."""
        rule = BookingRule.objects.create(
            organization_id=organization_id,
            rule_type=rule_type,
            name=name,
            created_by=created_by,
            **kwargs
        )

        logger.info(f"Created booking rule: {name} ({rule_type})")
        return rule

    def get_rule(self, rule_id: uuid.UUID) -> BookingRule:
        """Get a rule by ID."""
        from . import RuleViolationError

        try:
            return BookingRule.objects.get(id=rule_id)
        except BookingRule.DoesNotExist:
            raise RuleViolationError(f"Rule {rule_id} not found")

    def list_rules(
        self,
        organization_id: uuid.UUID,
        rule_type: str = None,
        target_id: uuid.UUID = None,
        active_only: bool = True
    ) -> List[BookingRule]:
        """List booking rules."""
        queryset = BookingRule.objects.filter(organization_id=organization_id)

        if rule_type:
            queryset = queryset.filter(rule_type=rule_type)

        if target_id:
            queryset = queryset.filter(target_id=target_id)

        if active_only:
            queryset = queryset.filter(is_active=True)

        return list(queryset.order_by('-priority', 'name'))

    def update_rule(
        self,
        rule_id: uuid.UUID,
        **kwargs
    ) -> BookingRule:
        """Update a booking rule."""
        rule = self.get_rule(rule_id)

        allowed_fields = [
            'name', 'description', 'priority', 'is_active',
            'min_booking_duration', 'max_booking_duration',
            'min_notice_hours', 'max_advance_days',
            'max_daily_hours', 'max_weekly_hours',
            'max_daily_bookings', 'max_concurrent_bookings',
            'operating_hours', 'required_buffer_minutes',
            'preflight_minutes', 'postflight_minutes',
            'who_can_book', 'requires_approval_from',
            'required_qualifications', 'required_currency',
            'require_positive_balance', 'minimum_balance',
            'require_prepayment', 'prepayment_percentage',
            'free_cancellation_hours', 'late_cancellation_fee_percent',
            'no_show_fee_percent', 'effective_from', 'effective_to',
        ]

        for field, value in kwargs.items():
            if field in allowed_fields:
                setattr(rule, field, value)

        rule.save()

        logger.info(f"Updated booking rule: {rule.name}")
        return rule

    def delete_rule(self, rule_id: uuid.UUID):
        """Delete a booking rule (soft delete by deactivating)."""
        rule = self.get_rule(rule_id)
        rule.is_active = False
        rule.save()

        logger.info(f"Deactivated booking rule: {rule.name}")

    # ==========================================================================
    # Rule Application
    # ==========================================================================

    def get_applicable_rules(
        self,
        organization_id: uuid.UUID,
        aircraft_id: uuid.UUID = None,
        instructor_id: uuid.UUID = None,
        student_id: uuid.UUID = None,
        location_id: uuid.UUID = None,
        booking_type: str = None
    ) -> List[BookingRule]:
        """Get all applicable rules for a booking context."""
        return list(BookingRule.get_applicable_rules(
            organization_id,
            aircraft_id=aircraft_id,
            instructor_id=instructor_id,
            student_id=student_id,
            location_id=location_id,
            booking_type=booking_type
        ))

    def get_merged_rules(
        self,
        organization_id: uuid.UUID,
        **kwargs
    ) -> Dict[str, Any]:
        """Get merged rules with higher priority taking precedence."""
        return BookingRule.get_merged_rules(organization_id, **kwargs)

    # ==========================================================================
    # Validation
    # ==========================================================================

    def validate_booking(
        self,
        organization_id: uuid.UUID,
        scheduled_start: datetime,
        scheduled_end: datetime,
        user_id: uuid.UUID,
        aircraft_id: uuid.UUID = None,
        instructor_id: uuid.UUID = None,
        student_id: uuid.UUID = None,
        location_id: uuid.UUID = None,
        booking_type: str = None
    ) -> Dict[str, Any]:
        """Validate a booking against all applicable rules."""
        result = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'rules_applied': [],
        }

        # Get merged rules
        rules = self.get_merged_rules(
            organization_id,
            aircraft_id=aircraft_id,
            instructor_id=instructor_id,
            student_id=student_id,
            location_id=location_id,
            booking_type=booking_type
        )

        duration_minutes = (scheduled_end - scheduled_start).total_seconds() / 60
        hours_until = (scheduled_start - timezone.now()).total_seconds() / 3600
        days_until = (scheduled_start.date() - timezone.now().date()).days

        # Duration validation
        if rules.get('min_booking_duration'):
            if duration_minutes < rules['min_booking_duration']:
                result['valid'] = False
                result['errors'].append(
                    f"Minimum booking duration is {rules['min_booking_duration']} minutes"
                )
            result['rules_applied'].append('min_booking_duration')

        if rules.get('max_booking_duration'):
            if duration_minutes > rules['max_booking_duration']:
                result['valid'] = False
                result['errors'].append(
                    f"Maximum booking duration is {rules['max_booking_duration']} minutes"
                )
            result['rules_applied'].append('max_booking_duration')

        # Notice period
        if rules.get('min_notice_hours'):
            if hours_until < rules['min_notice_hours']:
                result['valid'] = False
                result['errors'].append(
                    f"Minimum {rules['min_notice_hours']} hours notice required"
                )
            result['rules_applied'].append('min_notice_hours')

        # Advance booking
        if rules.get('max_advance_days'):
            if days_until > rules['max_advance_days']:
                result['valid'] = False
                result['errors'].append(
                    f"Cannot book more than {rules['max_advance_days']} days in advance"
                )
            result['rules_applied'].append('max_advance_days')

        # Daily hours check
        if rules.get('max_daily_hours') and student_id:
            daily_hours = self._get_daily_hours(
                organization_id, student_id, scheduled_start.date()
            )
            total_hours = daily_hours + (duration_minutes / 60)
            if total_hours > float(rules['max_daily_hours']):
                result['valid'] = False
                result['errors'].append(
                    f"Maximum {rules['max_daily_hours']} hours per day allowed"
                )
            result['rules_applied'].append('max_daily_hours')

        # Weekly hours check
        if rules.get('max_weekly_hours') and student_id:
            weekly_hours = self._get_weekly_hours(
                organization_id, student_id, scheduled_start.date()
            )
            total_hours = weekly_hours + (duration_minutes / 60)
            if total_hours > float(rules['max_weekly_hours']):
                result['valid'] = False
                result['errors'].append(
                    f"Maximum {rules['max_weekly_hours']} hours per week allowed"
                )
            result['rules_applied'].append('max_weekly_hours')

        # Concurrent bookings
        if rules.get('max_concurrent_bookings') and student_id:
            active_count = self._get_active_booking_count(
                organization_id, student_id
            )
            if active_count >= rules['max_concurrent_bookings']:
                result['valid'] = False
                result['errors'].append(
                    f"Maximum {rules['max_concurrent_bookings']} active bookings allowed"
                )
            result['rules_applied'].append('max_concurrent_bookings')

        # Approval required check (warning, not error)
        if rules.get('requires_approval_from'):
            result['warnings'].append('This booking will require approval')
            result['requires_approval'] = True

        return result

    def calculate_cancellation_fee(
        self,
        organization_id: uuid.UUID,
        hours_until_start: float,
        estimated_cost: Decimal,
        aircraft_id: uuid.UUID = None
    ) -> Dict[str, Any]:
        """Calculate cancellation fee based on rules."""
        rules = self.get_merged_rules(
            organization_id,
            aircraft_id=aircraft_id
        )

        free_hours = rules.get('free_cancellation_hours', 24)
        late_percent = rules.get('late_cancellation_fee_percent', Decimal('50.00'))
        no_show_percent = rules.get('no_show_fee_percent', Decimal('100.00'))

        if hours_until_start >= free_hours:
            return {
                'fee': Decimal('0.00'),
                'fee_percent': Decimal('0.00'),
                'is_free': True,
                'is_late': False,
            }

        if hours_until_start <= 0:
            fee_percent = no_show_percent
            is_late = True
        else:
            fee_percent = late_percent
            is_late = True

        fee = estimated_cost * (fee_percent / Decimal('100.00'))

        return {
            'fee': fee,
            'fee_percent': fee_percent,
            'is_free': False,
            'is_late': is_late,
        }

    # ==========================================================================
    # Private Methods
    # ==========================================================================

    def _get_daily_hours(
        self,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        target_date: date
    ) -> float:
        """Get total booking hours for a user on a date."""
        from django.db.models import Sum

        result = Booking.objects.filter(
            organization_id=organization_id,
            scheduled_start__date=target_date,
            status__in=Booking.get_active_statuses()
        ).filter(
            models.Q(student_id=user_id) | models.Q(pilot_id=user_id)
        ).aggregate(
            total=Sum('scheduled_duration')
        )

        return (result['total'] or 0) / 60

    def _get_weekly_hours(
        self,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        target_date: date
    ) -> float:
        """Get total booking hours for a user in the week."""
        from django.db.models import Sum

        # Get Monday of the week
        week_start = target_date - timedelta(days=target_date.weekday())
        week_end = week_start + timedelta(days=6)

        result = Booking.objects.filter(
            organization_id=organization_id,
            scheduled_start__date__gte=week_start,
            scheduled_start__date__lte=week_end,
            status__in=Booking.get_active_statuses()
        ).filter(
            models.Q(student_id=user_id) | models.Q(pilot_id=user_id)
        ).aggregate(
            total=Sum('scheduled_duration')
        )

        return (result['total'] or 0) / 60

    def _get_active_booking_count(
        self,
        organization_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> int:
        """Get count of active future bookings for a user."""
        return Booking.objects.filter(
            organization_id=organization_id,
            scheduled_start__gte=timezone.now(),
            status__in=Booking.get_active_statuses()
        ).filter(
            models.Q(student_id=user_id) | models.Q(pilot_id=user_id)
        ).count()


# Import models at module level to avoid issues
from django.db import models
