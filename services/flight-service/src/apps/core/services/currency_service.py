# services/flight-service/src/apps/core/services/currency_service.py
"""
Currency Service

Business logic for pilot currency tracking and validation.
"""

import uuid
import logging
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from django.db import transaction
from django.db.models import Q, Sum, Count
from django.utils import timezone

from ..models import (
    Flight,
    FlightCrewLog,
    PilotLogbookSummary,
    Approach,
)
from .exceptions import CurrencyError

logger = logging.getLogger(__name__)


class CurrencyType(str, Enum):
    """Types of pilot currency."""
    DAY_VFR = 'day_vfr'
    NIGHT_VFR = 'night_vfr'
    IFR = 'ifr'
    TAILWHEEL = 'tailwheel'
    HIGH_PERFORMANCE = 'high_performance'
    COMPLEX = 'complex'
    PASSENGER = 'passenger'
    NIGHT_PASSENGER = 'night_passenger'


class CurrencyStatus(str, Enum):
    """Currency status values."""
    CURRENT = 'current'
    EXPIRING_SOON = 'expiring_soon'
    EXPIRED = 'expired'
    NOT_APPLICABLE = 'not_applicable'


@dataclass
class CurrencyRequirement:
    """Currency requirement definition."""
    currency_type: CurrencyType
    description: str
    required_count: int
    period_days: int
    item_type: str  # 'landings', 'approaches', 'flights', 'hours'
    conditions: Optional[Dict[str, Any]] = None


@dataclass
class CurrencyResult:
    """Currency check result."""
    currency_type: CurrencyType
    status: CurrencyStatus
    current_count: int
    required_count: int
    period_days: int
    expires_on: Optional[date] = None
    days_remaining: Optional[int] = None
    details: Optional[Dict[str, Any]] = None


class CurrencyService:
    """
    Service class for pilot currency operations.

    Handles currency checks, calculations, and status tracking.
    """

    # Standard currency requirements (FAA-style, can be customized per organization)
    STANDARD_REQUIREMENTS = [
        CurrencyRequirement(
            currency_type=CurrencyType.DAY_VFR,
            description="Day VFR passenger carrying",
            required_count=3,
            period_days=90,
            item_type='landings',
            conditions={'day': True, 'full_stop': True}
        ),
        CurrencyRequirement(
            currency_type=CurrencyType.NIGHT_VFR,
            description="Night VFR passenger carrying",
            required_count=3,
            period_days=90,
            item_type='landings',
            conditions={'night': True, 'full_stop': True}
        ),
        CurrencyRequirement(
            currency_type=CurrencyType.IFR,
            description="IFR currency",
            required_count=6,
            period_days=180,
            item_type='approaches',
            conditions={'instrument': True}
        ),
    ]

    # ==========================================================================
    # Currency Check Operations
    # ==========================================================================

    @classmethod
    def check_all_currency(
        cls,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        requirements: List[CurrencyRequirement] = None
    ) -> List[CurrencyResult]:
        """
        Check all currency requirements for a pilot.

        Args:
            organization_id: Organization UUID
            user_id: Pilot user UUID
            requirements: Optional custom requirements, defaults to standard

        Returns:
            List of CurrencyResult objects
        """
        if requirements is None:
            requirements = cls.STANDARD_REQUIREMENTS

        results = []
        for req in requirements:
            result = cls.check_currency(organization_id, user_id, req)
            results.append(result)

        return results

    @classmethod
    def check_currency(
        cls,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        requirement: CurrencyRequirement
    ) -> CurrencyResult:
        """
        Check a specific currency requirement.

        Args:
            organization_id: Organization UUID
            user_id: Pilot user UUID
            requirement: Currency requirement to check

        Returns:
            CurrencyResult object
        """
        today = date.today()
        period_start = today - timedelta(days=requirement.period_days)

        # Get relevant data based on item type
        if requirement.item_type == 'landings':
            current_count = cls._count_landings(
                organization_id, user_id, period_start,
                requirement.conditions
            )
        elif requirement.item_type == 'approaches':
            current_count = cls._count_approaches(
                organization_id, user_id, period_start,
                requirement.conditions
            )
        elif requirement.item_type == 'flights':
            current_count = cls._count_flights(
                organization_id, user_id, period_start,
                requirement.conditions
            )
        elif requirement.item_type == 'hours':
            current_count = int(cls._count_hours(
                organization_id, user_id, period_start,
                requirement.conditions
            ))
        else:
            raise CurrencyError(
                message=f"Unknown item type: {requirement.item_type}",
                currency_type=requirement.currency_type.value
            )

        # Determine status
        if current_count >= requirement.required_count:
            status = CurrencyStatus.CURRENT

            # Calculate expiration
            expires_on = cls._calculate_expiration(
                organization_id, user_id, requirement,
                current_count
            )
            days_remaining = (expires_on - today).days if expires_on else None

            # Check if expiring soon (within 30 days)
            if days_remaining is not None and days_remaining <= 30:
                status = CurrencyStatus.EXPIRING_SOON
        else:
            status = CurrencyStatus.EXPIRED
            expires_on = None
            days_remaining = None

        return CurrencyResult(
            currency_type=requirement.currency_type,
            status=status,
            current_count=current_count,
            required_count=requirement.required_count,
            period_days=requirement.period_days,
            expires_on=expires_on,
            days_remaining=days_remaining,
            details={
                'description': requirement.description,
                'item_type': requirement.item_type,
                'conditions': requirement.conditions,
            }
        )

    @classmethod
    def get_currency_summary(
        cls,
        organization_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> Dict[str, Any]:
        """
        Get a summary of all currency statuses.

        Args:
            organization_id: Organization UUID
            user_id: Pilot user UUID

        Returns:
            Dictionary with currency summary
        """
        results = cls.check_all_currency(organization_id, user_id)

        summary = {
            'user_id': str(user_id),
            'checked_at': timezone.now().isoformat(),
            'overall_status': CurrencyStatus.CURRENT.value,
            'currencies': [],
            'expired_count': 0,
            'expiring_soon_count': 0,
            'current_count': 0,
        }

        for result in results:
            currency_data = {
                'type': result.currency_type.value,
                'status': result.status.value,
                'current': result.current_count,
                'required': result.required_count,
                'period_days': result.period_days,
                'expires_on': result.expires_on.isoformat() if result.expires_on else None,
                'days_remaining': result.days_remaining,
                'description': result.details.get('description') if result.details else None,
            }
            summary['currencies'].append(currency_data)

            if result.status == CurrencyStatus.EXPIRED:
                summary['expired_count'] += 1
                summary['overall_status'] = CurrencyStatus.EXPIRED.value
            elif result.status == CurrencyStatus.EXPIRING_SOON:
                summary['expiring_soon_count'] += 1
                if summary['overall_status'] != CurrencyStatus.EXPIRED.value:
                    summary['overall_status'] = CurrencyStatus.EXPIRING_SOON.value
            else:
                summary['current_count'] += 1

        return summary

    # ==========================================================================
    # Pre-flight Currency Validation
    # ==========================================================================

    @classmethod
    def validate_for_flight(
        cls,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        flight_type: str,
        flight_rules: str,
        has_passengers: bool = False,
        is_night: bool = False
    ) -> Dict[str, Any]:
        """
        Validate pilot currency for a specific flight.

        Args:
            organization_id: Organization UUID
            user_id: Pilot user UUID
            flight_type: Type of flight
            flight_rules: VFR/IFR
            has_passengers: Whether carrying passengers
            is_night: Whether flight is at night

        Returns:
            Dictionary with validation results
        """
        validation = {
            'user_id': str(user_id),
            'is_valid': True,
            'warnings': [],
            'errors': [],
            'currency_checks': [],
        }

        results = cls.check_all_currency(organization_id, user_id)

        # Check relevant currencies based on flight parameters
        for result in results:
            check = {
                'type': result.currency_type.value,
                'status': result.status.value,
                'required': False,
            }

            # Day VFR with passengers
            if (result.currency_type == CurrencyType.DAY_VFR and
                has_passengers and not is_night):
                check['required'] = True
                if result.status == CurrencyStatus.EXPIRED:
                    validation['errors'].append(
                        f"Day VFR passenger currency expired. Need {result.required_count - result.current_count} more landings."
                    )
                    validation['is_valid'] = False
                elif result.status == CurrencyStatus.EXPIRING_SOON:
                    validation['warnings'].append(
                        f"Day VFR passenger currency expiring in {result.days_remaining} days."
                    )

            # Night VFR with passengers
            elif (result.currency_type == CurrencyType.NIGHT_VFR and
                  has_passengers and is_night):
                check['required'] = True
                if result.status == CurrencyStatus.EXPIRED:
                    validation['errors'].append(
                        f"Night VFR passenger currency expired. Need {result.required_count - result.current_count} more night landings."
                    )
                    validation['is_valid'] = False
                elif result.status == CurrencyStatus.EXPIRING_SOON:
                    validation['warnings'].append(
                        f"Night VFR passenger currency expiring in {result.days_remaining} days."
                    )

            # IFR
            elif (result.currency_type == CurrencyType.IFR and
                  flight_rules == 'IFR'):
                check['required'] = True
                if result.status == CurrencyStatus.EXPIRED:
                    validation['errors'].append(
                        f"IFR currency expired. Need {result.required_count - result.current_count} more approaches."
                    )
                    validation['is_valid'] = False
                elif result.status == CurrencyStatus.EXPIRING_SOON:
                    validation['warnings'].append(
                        f"IFR currency expiring in {result.days_remaining} days."
                    )

            validation['currency_checks'].append(check)

        return validation

    # ==========================================================================
    # Currency Tracking Updates
    # ==========================================================================

    @classmethod
    @transaction.atomic
    def update_currency_from_flight(
        cls,
        flight: Flight
    ) -> None:
        """
        Update currency tracking after a flight is approved.

        Args:
            flight: Approved Flight instance
        """
        # Get logbook summary for PIC
        if flight.pic_id:
            from .logbook_service import LogbookService
            summary = LogbookService.get_or_create_summary(
                flight.organization_id, flight.pic_id
            )
            LogbookService.recalculate_currency(summary)

        # Get logbook summary for student (they may need currency too)
        if flight.student_id:
            from .logbook_service import LogbookService
            summary = LogbookService.get_or_create_summary(
                flight.organization_id, flight.student_id
            )
            LogbookService.recalculate_currency(summary)

    # ==========================================================================
    # Private Helper Methods
    # ==========================================================================

    @classmethod
    def _count_landings(
        cls,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        since_date: date,
        conditions: Dict[str, Any] = None
    ) -> int:
        """Count qualifying landings for currency."""
        conditions = conditions or {}

        # Get approved flights
        flights = Flight.objects.filter(
            organization_id=organization_id,
            flight_status=Flight.Status.APPROVED,
            flight_date__gte=since_date
        ).filter(
            Q(pic_id=user_id) | Q(student_id=user_id)
        )

        count = 0
        for flight in flights:
            if conditions.get('day') and conditions.get('full_stop'):
                count += flight.full_stop_day
            elif conditions.get('night') and conditions.get('full_stop'):
                count += flight.full_stop_night
            elif conditions.get('day'):
                count += flight.landings_day
            elif conditions.get('night'):
                count += flight.landings_night
            else:
                count += flight.total_landings

        return count

    @classmethod
    def _count_approaches(
        cls,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        since_date: date,
        conditions: Dict[str, Any] = None
    ) -> int:
        """Count qualifying approaches for currency."""
        # Get approved flight IDs
        flight_ids = Flight.objects.filter(
            organization_id=organization_id,
            flight_status=Flight.Status.APPROVED,
            flight_date__gte=since_date
        ).filter(
            Q(pic_id=user_id) | Q(student_id=user_id)
        ).values_list('id', flat=True)

        # Count approaches
        query = Approach.objects.filter(
            flight_id__in=flight_ids,
            organization_id=organization_id
        )

        # Exclude visual and contact approaches for IFR currency
        if conditions and conditions.get('instrument'):
            query = query.exclude(
                approach_type__in=[
                    Approach.ApproachType.VISUAL,
                    Approach.ApproachType.CONTACT
                ]
            )

        return query.count()

    @classmethod
    def _count_flights(
        cls,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        since_date: date,
        conditions: Dict[str, Any] = None
    ) -> int:
        """Count qualifying flights for currency."""
        query = Flight.objects.filter(
            organization_id=organization_id,
            flight_status=Flight.Status.APPROVED,
            flight_date__gte=since_date
        ).filter(
            Q(pic_id=user_id) | Q(student_id=user_id)
        )

        if conditions:
            if conditions.get('flight_type'):
                query = query.filter(flight_type=conditions['flight_type'])
            if conditions.get('flight_rules'):
                query = query.filter(flight_rules=conditions['flight_rules'])

        return query.count()

    @classmethod
    def _count_hours(
        cls,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        since_date: date,
        conditions: Dict[str, Any] = None
    ) -> Decimal:
        """Count qualifying flight hours for currency."""
        crew_logs = FlightCrewLog.objects.filter(
            organization_id=organization_id,
            user_id=user_id
        )

        # Get approved flight IDs in date range
        flight_ids = set(
            Flight.objects.filter(
                organization_id=organization_id,
                flight_status=Flight.Status.APPROVED,
                flight_date__gte=since_date
            ).values_list('id', flat=True)
        )

        total = Decimal('0')
        for log in crew_logs:
            if log.flight_id in flight_ids:
                if conditions and conditions.get('time_field'):
                    total += getattr(log, conditions['time_field'], Decimal('0'))
                else:
                    total += log.flight_time or Decimal('0')

        return total

    @classmethod
    def _calculate_expiration(
        cls,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        requirement: CurrencyRequirement,
        current_count: int
    ) -> Optional[date]:
        """Calculate when currency will expire based on oldest qualifying event."""
        today = date.today()
        period_start = today - timedelta(days=requirement.period_days)

        # Get flights in reverse chronological order
        flights = Flight.objects.filter(
            organization_id=organization_id,
            flight_status=Flight.Status.APPROVED,
            flight_date__gte=period_start
        ).filter(
            Q(pic_id=user_id) | Q(student_id=user_id)
        ).order_by('flight_date')

        if requirement.item_type == 'landings':
            # Find the flight that will cause expiration
            conditions = requirement.conditions or {}
            count = 0
            for flight in flights:
                if conditions.get('day') and conditions.get('full_stop'):
                    count += flight.full_stop_day
                elif conditions.get('night') and conditions.get('full_stop'):
                    count += flight.full_stop_night
                else:
                    count += flight.total_landings

                # When we've counted required amount, this flight date + period is expiration
                if count >= requirement.required_count:
                    return flight.flight_date + timedelta(days=requirement.period_days)

        elif requirement.item_type == 'approaches':
            flight_ids = flights.values_list('id', flat=True)
            approaches = Approach.objects.filter(
                flight_id__in=flight_ids,
                organization_id=organization_id
            )

            if requirement.conditions and requirement.conditions.get('instrument'):
                approaches = approaches.exclude(
                    approach_type__in=[
                        Approach.ApproachType.VISUAL,
                        Approach.ApproachType.CONTACT
                    ]
                )

            approaches = approaches.order_by('executed_at')
            count = 0
            for approach in approaches:
                count += 1
                if count >= requirement.required_count:
                    flight = flights.filter(id=approach.flight_id).first()
                    if flight:
                        return flight.flight_date + timedelta(days=requirement.period_days)

        return None

    # ==========================================================================
    # Batch Currency Check
    # ==========================================================================

    @classmethod
    def check_organization_currency(
        cls,
        organization_id: uuid.UUID
    ) -> List[Dict[str, Any]]:
        """
        Check currency for all pilots in an organization.

        Args:
            organization_id: Organization UUID

        Returns:
            List of pilot currency summaries
        """
        # Get all unique user IDs
        user_ids = set()

        # From flights as PIC
        user_ids.update(
            Flight.objects.filter(
                organization_id=organization_id,
                pic_id__isnull=False
            ).values_list('pic_id', flat=True)
        )

        # From flights as student
        user_ids.update(
            Flight.objects.filter(
                organization_id=organization_id,
                student_id__isnull=False
            ).values_list('student_id', flat=True)
        )

        results = []
        for user_id in user_ids:
            summary = cls.get_currency_summary(organization_id, user_id)
            results.append(summary)

        return results
