# services/certificate-service/src/apps/core/services/currency_service.py
"""
Currency Service

Business logic for pilot currency tracking.
Implements EASA FCL.060 and FAA 14 CFR 61.57 currency requirements.
"""

import logging
from datetime import date, timedelta
from decimal import Decimal
from typing import List, Dict, Any, Optional
from uuid import UUID

from django.db import transaction
from django.db.models import Q, Count
from django.utils import timezone

from ..models import (
    CurrencyRequirement,
    UserCurrencyStatus,
    CurrencyType,
    DEFAULT_CURRENCY_REQUIREMENTS,
)

logger = logging.getLogger(__name__)


# =============================================================================
# EASA FCL.060 Currency Requirements Constants
# =============================================================================
class EASACurrencyRules:
    """
    EASA FCL.060 Recent Experience Requirements.

    FCL.060 Recent experience:
    (a) Takeoffs and landings - passengers
        A pilot shall not operate an aircraft as PIC or co-pilot
        unless, in the preceding 90 days, they have carried out
        at least 3 takeoffs and landings in an aircraft of the
        same type or class, or in an FFS.

    (b) Instrument recency
        Unless a pilot holds a valid IR and has completed within
        the preceding 6 months:
        - At least 6 IFR approaches
        - Holding procedures
        - Intercepting and tracking through the use of navigation systems

    (c) Night currency
        For night operations, at least 1 takeoff and landing
        shall be performed at night in the preceding 90 days.
    """

    # Passenger carrying currency (FCL.060(a))
    PASSENGER_PERIOD_DAYS = 90
    PASSENGER_MIN_TAKEOFFS = 3
    PASSENGER_MIN_LANDINGS = 3

    # Night currency (FCL.060(c))
    NIGHT_PERIOD_DAYS = 90
    NIGHT_MIN_TAKEOFFS = 1
    NIGHT_MIN_LANDINGS = 1

    # IFR currency (FCL.060(b))
    IFR_PERIOD_DAYS = 180  # 6 months
    IFR_MIN_APPROACHES = 6
    IFR_MIN_HOLDING = 1

    # Type/class specific currency
    TYPE_RATING_PERIOD_DAYS = 90
    CLASS_RATING_PERIOD_DAYS = 90


class FAACurrencyRules:
    """
    FAA 14 CFR 61.57 Recent Flight Experience Requirements.

    61.57(a) - Passenger carrying
        No pilot may act as PIC carrying passengers unless within
        the preceding 90 days they have made:
        - 3 takeoffs and landings to a full stop (day or night)
        - For tailwheel: 3 full-stop landings

    61.57(b) - Night currency
        No pilot may act as PIC at night carrying passengers unless
        within the preceding 90 days they have made:
        - 3 takeoffs and landings to a full stop during night

    61.57(c) - Instrument proficiency check
        No pilot may act as PIC under IFR unless within the
        preceding 6 calendar months they have:
        - 6 instrument approaches
        - Holding procedures
        - Intercepting and tracking courses
    """

    # Passenger carrying currency (61.57(a))
    PASSENGER_PERIOD_DAYS = 90
    PASSENGER_MIN_TAKEOFFS = 3
    PASSENGER_MIN_LANDINGS = 3

    # Night currency (61.57(b))
    NIGHT_PERIOD_DAYS = 90
    NIGHT_MIN_TAKEOFFS = 3
    NIGHT_MIN_LANDINGS = 3

    # IFR currency (61.57(c))
    IFR_PERIOD_DAYS = 180  # 6 calendar months
    IFR_MIN_APPROACHES = 6
    IFR_MIN_HOLDING = 1

    # Tailwheel currency (61.57(a)(2))
    TAILWHEEL_PERIOD_DAYS = 90
    TAILWHEEL_MIN_LANDINGS = 3  # Must be to a full stop


class CurrencyService:
    """Service for managing pilot currency."""

    @staticmethod
    def create_requirement(
        organization_id: str,
        name: str,
        code: str,
        requirement_type: str,
        criteria: Dict[str, Any],
        **kwargs
    ) -> CurrencyRequirement:
        """
        Create a new currency requirement.

        Args:
            organization_id: Organization ID
            name: Requirement name
            code: Short code
            requirement_type: Type of requirement
            criteria: Criteria definition
            **kwargs: Additional fields

        Returns:
            Created CurrencyRequirement instance
        """
        requirement = CurrencyRequirement.objects.create(
            organization_id=organization_id,
            name=name,
            code=code,
            requirement_type=requirement_type,
            criteria=criteria,
            **kwargs
        )

        logger.info(
            f"Created currency requirement {requirement.id}",
            extra={'requirement_id': str(requirement.id), 'code': code}
        )

        return requirement

    @staticmethod
    def get_requirement(
        organization_id: str,
        requirement_id: str
    ) -> CurrencyRequirement:
        """
        Get a currency requirement by ID.

        Args:
            organization_id: Organization ID
            requirement_id: Requirement ID

        Returns:
            CurrencyRequirement instance

        Raises:
            ValueError: If not found
        """
        try:
            return CurrencyRequirement.objects.get(
                id=requirement_id,
                organization_id=organization_id
            )
        except CurrencyRequirement.DoesNotExist:
            raise ValueError(f'Currency requirement {requirement_id} not found')

    @staticmethod
    def list_requirements(
        organization_id: str,
        requirement_type: Optional[str] = None,
        active_only: bool = True
    ) -> List[CurrencyRequirement]:
        """
        List currency requirements.

        Args:
            organization_id: Organization ID
            requirement_type: Filter by type
            active_only: Only return active requirements

        Returns:
            List of CurrencyRequirement instances
        """
        queryset = CurrencyRequirement.objects.filter(organization_id=organization_id)

        if requirement_type:
            queryset = queryset.filter(requirement_type=requirement_type)
        if active_only:
            queryset = queryset.filter(is_active=True)

        return list(queryset.order_by('priority', 'name'))

    @staticmethod
    def initialize_default_requirements(organization_id: str) -> int:
        """
        Initialize default currency requirements for organization.

        Args:
            organization_id: Organization ID

        Returns:
            Number of requirements created
        """
        created = 0

        for req_data in DEFAULT_CURRENCY_REQUIREMENTS:
            _, was_created = CurrencyRequirement.objects.get_or_create(
                organization_id=organization_id,
                code=req_data['code'],
                defaults={
                    'name': req_data['name'],
                    'requirement_type': req_data['requirement_type'],
                    'regulatory_reference': req_data.get('regulatory_reference'),
                    'criteria': req_data['criteria'],
                    'applies_to': req_data.get('applies_to', {}),
                    'priority': req_data.get('priority', 100),
                }
            )
            if was_created:
                created += 1

        logger.info(
            f"Initialized {created} default currency requirements for org {organization_id}"
        )

        return created

    @staticmethod
    def get_user_currency_status(
        organization_id: str,
        user_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get user's currency status for all requirements.

        Args:
            organization_id: Organization ID
            user_id: User ID

        Returns:
            List of currency status dicts
        """
        # Get all active requirements
        requirements = CurrencyService.list_requirements(
            organization_id=organization_id,
            active_only=True
        )

        statuses = []

        for req in requirements:
            status = UserCurrencyStatus.objects.filter(
                organization_id=organization_id,
                user_id=user_id,
                requirement=req
            ).first()

            if status:
                statuses.append(status.get_status_info())
            else:
                # No status record - not current
                statuses.append({
                    'requirement_id': str(req.id),
                    'requirement_code': req.code,
                    'requirement_name': req.name,
                    'requirement_type': req.requirement_type,
                    'is_current': False,
                    'is_warning': False,
                    'valid_from': None,
                    'valid_until': None,
                    'current_count': {},
                    'criteria': req.criteria,
                    'regulatory_reference': req.regulatory_reference,
                })

        return statuses

    @staticmethod
    def check_currency(
        organization_id: str,
        user_id: str,
        operation_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Check user's overall currency status.

        Args:
            organization_id: Organization ID
            user_id: User ID
            operation_type: Optional operation type to check (e.g., 'passenger', 'night')

        Returns:
            Currency check result dict
        """
        statuses = CurrencyService.get_user_currency_status(
            organization_id=organization_id,
            user_id=user_id
        )

        issues = []
        warnings = []
        is_current = True

        for status in statuses:
            # Filter by operation type if specified
            if operation_type:
                applies_to = status.get('applies_to', {})
                operation_types = applies_to.get('operation_types', [])
                if operation_types and operation_type not in operation_types:
                    continue

            if not status['is_current']:
                is_current = False
                issues.append({
                    'type': status['requirement_type'],
                    'code': status['requirement_code'],
                    'message': f'{status["requirement_name"]} currency not met',
                    'severity': 'error',
                })
            elif status.get('is_warning'):
                warnings.append({
                    'type': status['requirement_type'],
                    'code': status['requirement_code'],
                    'message': f'{status["requirement_name"]} expiring soon',
                    'days_remaining': status.get('days_until_expiry'),
                    'severity': 'warning',
                })

        return {
            'user_id': user_id,
            'is_current': is_current,
            'operation_type': operation_type,
            'issues': issues,
            'warnings': warnings,
            'statuses': statuses,
            'checked_at': timezone.now().isoformat(),
        }

    @staticmethod
    def update_user_currency(
        organization_id: str,
        user_id: str,
        requirement_id: str,
        activity_data: Dict[str, Any]
    ) -> UserCurrencyStatus:
        """
        Update user's currency status based on activity.

        Args:
            organization_id: Organization ID
            user_id: User ID
            requirement_id: Requirement ID
            activity_data: Activity counts and dates

        Returns:
            Updated UserCurrencyStatus instance
        """
        requirement = CurrencyService.get_requirement(
            organization_id, requirement_id
        )

        status, created = UserCurrencyStatus.objects.get_or_create(
            organization_id=organization_id,
            user_id=user_id,
            requirement=requirement,
            defaults={
                'current_count': {},
                'is_current': False,
            }
        )

        status.update_currency(activity_data)

        logger.info(
            f"Updated currency status for user {user_id}",
            extra={
                'user_id': user_id,
                'requirement': requirement.code,
                'is_current': status.is_current
            }
        )

        return status

    @staticmethod
    def calculate_currency_from_flights(
        organization_id: str,
        user_id: str,
        flights: List[Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Calculate currency activity counts from flight data.

        Args:
            organization_id: Organization ID
            user_id: User ID
            flights: List of flight data dicts

        Returns:
            Dict of requirement_code -> activity_data
        """
        requirements = CurrencyService.list_requirements(
            organization_id=organization_id
        )

        results = {}

        for req in requirements:
            period_days = req.get_period_days()
            cutoff_date = date.today() - timedelta(days=period_days)

            # Filter flights within period
            period_flights = [
                f for f in flights
                if f.get('date') and date.fromisoformat(f['date']) >= cutoff_date
            ]

            # Calculate counts based on requirement type
            activity_data = {
                'counts': {},
                'first_date': None,
                'last_date': None,
                'last_flight_id': None,
            }

            if period_flights:
                activity_data['first_date'] = min(
                    date.fromisoformat(f['date']) for f in period_flights
                )
                activity_data['last_date'] = max(
                    date.fromisoformat(f['date']) for f in period_flights
                )
                activity_data['last_flight_id'] = period_flights[-1].get('id')

            if req.requirement_type == CurrencyType.TAKEOFF_LANDING:
                conditions = req.criteria.get('conditions', ['day'])
                if 'day' in conditions:
                    activity_data['counts']['takeoffs'] = sum(
                        f.get('takeoffs_day', 0) for f in period_flights
                    )
                    activity_data['counts']['landings'] = sum(
                        f.get('landings_day', 0) for f in period_flights
                    )
                elif 'night' in conditions:
                    activity_data['counts']['takeoffs'] = sum(
                        f.get('takeoffs_night', 0) for f in period_flights
                    )
                    activity_data['counts']['landings'] = sum(
                        f.get('landings_night', 0) for f in period_flights
                    )

            elif req.requirement_type == CurrencyType.NIGHT:
                activity_data['counts']['takeoffs'] = sum(
                    f.get('takeoffs_night', 0) for f in period_flights
                )
                activity_data['counts']['landings'] = sum(
                    f.get('landings_night', 0) for f in period_flights
                )

            elif req.requirement_type == CurrencyType.IFR:
                activity_data['counts']['approaches'] = sum(
                    f.get('approaches', 0) for f in period_flights
                )
                activity_data['counts']['holding_procedures'] = sum(
                    f.get('holding_procedures', 0) for f in period_flights
                )

            results[req.code] = activity_data

        return results

    @staticmethod
    def batch_update_currency(
        organization_id: str,
        user_id: str,
        flights: List[Dict[str, Any]]
    ) -> List[UserCurrencyStatus]:
        """
        Batch update all currency statuses for user based on flights.

        Args:
            organization_id: Organization ID
            user_id: User ID
            flights: List of flight data

        Returns:
            List of updated UserCurrencyStatus instances
        """
        activity_by_requirement = CurrencyService.calculate_currency_from_flights(
            organization_id=organization_id,
            user_id=user_id,
            flights=flights
        )

        updated_statuses = []

        for req_code, activity_data in activity_by_requirement.items():
            try:
                requirement = CurrencyRequirement.objects.get(
                    organization_id=organization_id,
                    code=req_code
                )
                status = CurrencyService.update_user_currency(
                    organization_id=organization_id,
                    user_id=user_id,
                    requirement_id=str(requirement.id),
                    activity_data=activity_data
                )
                updated_statuses.append(status)
            except CurrencyRequirement.DoesNotExist:
                continue

        return updated_statuses

    @staticmethod
    def get_currency_expiring(
        organization_id: str,
        days_ahead: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Get currency statuses expiring soon.

        Args:
            organization_id: Organization ID
            days_ahead: Days to look ahead

        Returns:
            List of expiring currency status dicts
        """
        expiry_date = date.today() + timedelta(days=days_ahead)

        statuses = UserCurrencyStatus.objects.filter(
            organization_id=organization_id,
            is_current=True,
            valid_until__isnull=False,
            valid_until__lte=expiry_date,
            valid_until__gte=date.today()
        ).select_related('requirement').order_by('valid_until')

        return [
            {
                'user_id': str(s.user_id),
                'requirement_code': s.requirement.code,
                'requirement_name': s.requirement.name,
                'valid_until': s.valid_until.isoformat(),
                'days_remaining': s.days_until_expiry,
            }
            for s in statuses
        ]

    @staticmethod
    def get_currency_statistics(
        organization_id: str
    ) -> Dict[str, Any]:
        """
        Get currency statistics for organization.

        Args:
            organization_id: Organization ID

        Returns:
            Statistics dict
        """
        statuses = UserCurrencyStatus.objects.filter(organization_id=organization_id)

        total_users = statuses.values('user_id').distinct().count()
        current_count = statuses.filter(is_current=True).count()
        warning_count = statuses.filter(is_warning=True).count()
        not_current_count = statuses.filter(is_current=False).count()

        by_requirement = statuses.values(
            'requirement__code'
        ).annotate(
            total=Count('id'),
            current=Count('id', filter=Q(is_current=True))
        )

        return {
            'total_users_tracked': total_users,
            'current_statuses': current_count,
            'warning_statuses': warning_count,
            'not_current_statuses': not_current_count,
            'by_requirement': {
                r['requirement__code']: {
                    'total': r['total'],
                    'current': r['current'],
                    'not_current': r['total'] - r['current']
                }
                for r in by_requirement
            },
        }

    # =========================================================================
    # EASA FCL.060 Specific Currency Methods
    # =========================================================================

    @staticmethod
    def check_fcl060_passenger_currency(
        flights: List[Dict[str, Any]],
        aircraft_type: Optional[str] = None,
        aircraft_class: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Check EASA FCL.060(a) passenger carrying currency.

        Pilot must have 3 takeoffs and 3 landings in the same type/class
        within the preceding 90 days.

        Args:
            flights: List of flight data dicts
            aircraft_type: Specific aircraft type (e.g., 'C172')
            aircraft_class: Aircraft class (e.g., 'SEP', 'MEP')

        Returns:
            Currency check result dict
        """
        cutoff_date = date.today() - timedelta(days=EASACurrencyRules.PASSENGER_PERIOD_DAYS)

        # Filter flights by type/class and date
        qualifying_flights = [
            f for f in flights
            if (
                f.get('date') and
                date.fromisoformat(str(f['date'])) >= cutoff_date and
                (not aircraft_type or f.get('aircraft_type') == aircraft_type) and
                (not aircraft_class or f.get('aircraft_class') == aircraft_class)
            )
        ]

        # Count takeoffs and landings
        takeoffs = sum(f.get('takeoffs_day', 0) + f.get('takeoffs_night', 0) for f in qualifying_flights)
        landings = sum(f.get('landings_day', 0) + f.get('landings_night', 0) for f in qualifying_flights)

        is_current = (
            takeoffs >= EASACurrencyRules.PASSENGER_MIN_TAKEOFFS and
            landings >= EASACurrencyRules.PASSENGER_MIN_LANDINGS
        )

        # Calculate expiry based on oldest qualifying flight
        expiry_date = None
        if qualifying_flights and is_current:
            oldest_flight_date = min(
                date.fromisoformat(str(f['date'])) for f in qualifying_flights
            )
            expiry_date = oldest_flight_date + timedelta(days=EASACurrencyRules.PASSENGER_PERIOD_DAYS)

        return {
            'regulation': 'EASA FCL.060(a)',
            'requirement': 'passenger_carrying',
            'is_current': is_current,
            'period_days': EASACurrencyRules.PASSENGER_PERIOD_DAYS,
            'aircraft_type': aircraft_type,
            'aircraft_class': aircraft_class,
            'current_count': {
                'takeoffs': takeoffs,
                'landings': landings,
            },
            'required_count': {
                'takeoffs': EASACurrencyRules.PASSENGER_MIN_TAKEOFFS,
                'landings': EASACurrencyRules.PASSENGER_MIN_LANDINGS,
            },
            'remaining_count': {
                'takeoffs': max(0, EASACurrencyRules.PASSENGER_MIN_TAKEOFFS - takeoffs),
                'landings': max(0, EASACurrencyRules.PASSENGER_MIN_LANDINGS - landings),
            },
            'expiry_date': expiry_date.isoformat() if expiry_date else None,
            'qualifying_flights': len(qualifying_flights),
        }

    @staticmethod
    def check_fcl060_night_currency(
        flights: List[Dict[str, Any]],
        aircraft_type: Optional[str] = None,
        aircraft_class: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Check EASA FCL.060(c) night currency.

        For night operations, at least 1 takeoff and 1 landing must be
        performed at night in the preceding 90 days.

        Args:
            flights: List of flight data dicts
            aircraft_type: Specific aircraft type
            aircraft_class: Aircraft class

        Returns:
            Currency check result dict
        """
        cutoff_date = date.today() - timedelta(days=EASACurrencyRules.NIGHT_PERIOD_DAYS)

        # Filter flights by type/class and date
        qualifying_flights = [
            f for f in flights
            if (
                f.get('date') and
                date.fromisoformat(str(f['date'])) >= cutoff_date and
                (not aircraft_type or f.get('aircraft_type') == aircraft_type) and
                (not aircraft_class or f.get('aircraft_class') == aircraft_class) and
                (f.get('takeoffs_night', 0) > 0 or f.get('landings_night', 0) > 0)
            )
        ]

        # Count night takeoffs and landings
        night_takeoffs = sum(f.get('takeoffs_night', 0) for f in qualifying_flights)
        night_landings = sum(f.get('landings_night', 0) for f in qualifying_flights)

        is_current = (
            night_takeoffs >= EASACurrencyRules.NIGHT_MIN_TAKEOFFS and
            night_landings >= EASACurrencyRules.NIGHT_MIN_LANDINGS
        )

        # Calculate expiry based on oldest qualifying flight
        expiry_date = None
        if qualifying_flights and is_current:
            oldest_flight_date = min(
                date.fromisoformat(str(f['date'])) for f in qualifying_flights
            )
            expiry_date = oldest_flight_date + timedelta(days=EASACurrencyRules.NIGHT_PERIOD_DAYS)

        return {
            'regulation': 'EASA FCL.060(c)',
            'requirement': 'night_operations',
            'is_current': is_current,
            'period_days': EASACurrencyRules.NIGHT_PERIOD_DAYS,
            'aircraft_type': aircraft_type,
            'aircraft_class': aircraft_class,
            'current_count': {
                'night_takeoffs': night_takeoffs,
                'night_landings': night_landings,
            },
            'required_count': {
                'night_takeoffs': EASACurrencyRules.NIGHT_MIN_TAKEOFFS,
                'night_landings': EASACurrencyRules.NIGHT_MIN_LANDINGS,
            },
            'remaining_count': {
                'night_takeoffs': max(0, EASACurrencyRules.NIGHT_MIN_TAKEOFFS - night_takeoffs),
                'night_landings': max(0, EASACurrencyRules.NIGHT_MIN_LANDINGS - night_landings),
            },
            'expiry_date': expiry_date.isoformat() if expiry_date else None,
            'qualifying_flights': len(qualifying_flights),
        }

    @staticmethod
    def check_fcl060_ifr_currency(
        flights: List[Dict[str, Any]],
        include_simulator: bool = True
    ) -> Dict[str, Any]:
        """
        Check EASA FCL.060(b) IFR currency.

        Pilot must have completed within 6 months:
        - 6 instrument approaches
        - Holding procedures
        - Intercepting and tracking through nav systems

        Args:
            flights: List of flight data dicts
            include_simulator: Include simulator time

        Returns:
            Currency check result dict
        """
        cutoff_date = date.today() - timedelta(days=EASACurrencyRules.IFR_PERIOD_DAYS)

        # Filter flights by date
        qualifying_flights = [
            f for f in flights
            if (
                f.get('date') and
                date.fromisoformat(str(f['date'])) >= cutoff_date and
                (f.get('instrument_approaches', 0) > 0 or
                 f.get('holding_procedures', 0) > 0 or
                 f.get('actual_instrument', 0) > 0 or
                 f.get('simulated_instrument', 0) > 0)
            )
        ]

        # Include simulator flights if enabled
        if include_simulator:
            qualifying_flights.extend([
                f for f in flights
                if (
                    f.get('date') and
                    date.fromisoformat(str(f['date'])) >= cutoff_date and
                    f.get('flight_type') == 'simulator' and
                    f.get('instrument_approaches', 0) > 0
                )
            ])

        # Count IFR activities
        approaches = sum(f.get('instrument_approaches', 0) for f in qualifying_flights)
        holding = sum(f.get('holding_procedures', 0) for f in qualifying_flights)
        tracking = sum(
            1 for f in qualifying_flights
            if f.get('navigation_tracking', False) or f.get('vor_tracking', 0) > 0
        )

        is_current = (
            approaches >= EASACurrencyRules.IFR_MIN_APPROACHES and
            holding >= EASACurrencyRules.IFR_MIN_HOLDING
        )

        # Calculate expiry based on oldest qualifying flight
        expiry_date = None
        if qualifying_flights and is_current:
            oldest_flight_date = min(
                date.fromisoformat(str(f['date'])) for f in qualifying_flights
            )
            expiry_date = oldest_flight_date + timedelta(days=EASACurrencyRules.IFR_PERIOD_DAYS)

        return {
            'regulation': 'EASA FCL.060(b)',
            'requirement': 'ifr_operations',
            'is_current': is_current,
            'period_days': EASACurrencyRules.IFR_PERIOD_DAYS,
            'current_count': {
                'approaches': approaches,
                'holding_procedures': holding,
                'nav_tracking': tracking,
            },
            'required_count': {
                'approaches': EASACurrencyRules.IFR_MIN_APPROACHES,
                'holding_procedures': EASACurrencyRules.IFR_MIN_HOLDING,
            },
            'remaining_count': {
                'approaches': max(0, EASACurrencyRules.IFR_MIN_APPROACHES - approaches),
                'holding_procedures': max(0, EASACurrencyRules.IFR_MIN_HOLDING - holding),
            },
            'expiry_date': expiry_date.isoformat() if expiry_date else None,
            'qualifying_flights': len(qualifying_flights),
            'includes_simulator': include_simulator,
        }

    @staticmethod
    def check_comprehensive_currency(
        flights: List[Dict[str, Any]],
        aircraft_type: Optional[str] = None,
        aircraft_class: Optional[str] = None,
        regulatory_authority: str = 'EASA'
    ) -> Dict[str, Any]:
        """
        Comprehensive currency check for all requirement types.

        Args:
            flights: List of flight data dicts
            aircraft_type: Specific aircraft type
            aircraft_class: Aircraft class
            regulatory_authority: EASA or FAA

        Returns:
            Comprehensive currency check result
        """
        if regulatory_authority.upper() == 'EASA':
            passenger = CurrencyService.check_fcl060_passenger_currency(
                flights, aircraft_type, aircraft_class
            )
            night = CurrencyService.check_fcl060_night_currency(
                flights, aircraft_type, aircraft_class
            )
            ifr = CurrencyService.check_fcl060_ifr_currency(flights)
        else:
            # FAA rules
            passenger = CurrencyService.check_faa_passenger_currency(
                flights, aircraft_type
            )
            night = CurrencyService.check_faa_night_currency(
                flights, aircraft_type
            )
            ifr = CurrencyService.check_faa_ifr_currency(flights)

        # Determine overall status
        is_current_vfr_day = passenger['is_current']
        is_current_vfr_night = passenger['is_current'] and night['is_current']
        is_current_ifr = passenger['is_current'] and ifr['is_current']
        is_current_ifr_night = is_current_ifr and night['is_current']

        # Collect all issues
        issues = []
        if not passenger['is_current']:
            issues.append({
                'type': 'passenger_currency',
                'code': 'PASSENGER_NOT_CURRENT',
                'message': f"Need {passenger['remaining_count']['takeoffs']} more takeoffs and {passenger['remaining_count']['landings']} landings",
                'severity': 'error'
            })
        if not night['is_current']:
            issues.append({
                'type': 'night_currency',
                'code': 'NIGHT_NOT_CURRENT',
                'message': f"Need {night['remaining_count'].get('night_takeoffs', 0)} more night takeoffs and {night['remaining_count'].get('night_landings', 0)} night landings",
                'severity': 'warning'  # Warning since it's only needed for night ops
            })
        if not ifr['is_current']:
            issues.append({
                'type': 'ifr_currency',
                'code': 'IFR_NOT_CURRENT',
                'message': f"Need {ifr['remaining_count']['approaches']} more approaches and {ifr['remaining_count']['holding_procedures']} holding procedures",
                'severity': 'warning'  # Warning since it's only needed for IFR ops
            })

        return {
            'regulatory_authority': regulatory_authority,
            'aircraft_type': aircraft_type,
            'aircraft_class': aircraft_class,
            'currency_status': {
                'vfr_day_passengers': is_current_vfr_day,
                'vfr_night_passengers': is_current_vfr_night,
                'ifr': is_current_ifr,
                'ifr_night': is_current_ifr_night,
            },
            'details': {
                'passenger': passenger,
                'night': night,
                'ifr': ifr,
            },
            'issues': issues,
            'checked_at': timezone.now().isoformat(),
        }

    # =========================================================================
    # FAA 14 CFR 61.57 Specific Currency Methods
    # =========================================================================

    @staticmethod
    def check_faa_passenger_currency(
        flights: List[Dict[str, Any]],
        aircraft_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Check FAA 14 CFR 61.57(a) passenger carrying currency.

        3 takeoffs and landings in the same category, class, and type
        (if type rating required) within preceding 90 days.

        Args:
            flights: List of flight data dicts
            aircraft_type: Specific aircraft type

        Returns:
            Currency check result dict
        """
        cutoff_date = date.today() - timedelta(days=FAACurrencyRules.PASSENGER_PERIOD_DAYS)

        qualifying_flights = [
            f for f in flights
            if (
                f.get('date') and
                date.fromisoformat(str(f['date'])) >= cutoff_date and
                (not aircraft_type or f.get('aircraft_type') == aircraft_type)
            )
        ]

        takeoffs = sum(f.get('takeoffs_day', 0) + f.get('takeoffs_night', 0) for f in qualifying_flights)
        landings = sum(f.get('landings_day', 0) + f.get('landings_night', 0) for f in qualifying_flights)

        is_current = (
            takeoffs >= FAACurrencyRules.PASSENGER_MIN_TAKEOFFS and
            landings >= FAACurrencyRules.PASSENGER_MIN_LANDINGS
        )

        expiry_date = None
        if qualifying_flights and is_current:
            oldest_flight_date = min(
                date.fromisoformat(str(f['date'])) for f in qualifying_flights
            )
            expiry_date = oldest_flight_date + timedelta(days=FAACurrencyRules.PASSENGER_PERIOD_DAYS)

        return {
            'regulation': 'FAA 14 CFR 61.57(a)',
            'requirement': 'passenger_carrying',
            'is_current': is_current,
            'period_days': FAACurrencyRules.PASSENGER_PERIOD_DAYS,
            'aircraft_type': aircraft_type,
            'current_count': {
                'takeoffs': takeoffs,
                'landings': landings,
            },
            'required_count': {
                'takeoffs': FAACurrencyRules.PASSENGER_MIN_TAKEOFFS,
                'landings': FAACurrencyRules.PASSENGER_MIN_LANDINGS,
            },
            'remaining_count': {
                'takeoffs': max(0, FAACurrencyRules.PASSENGER_MIN_TAKEOFFS - takeoffs),
                'landings': max(0, FAACurrencyRules.PASSENGER_MIN_LANDINGS - landings),
            },
            'expiry_date': expiry_date.isoformat() if expiry_date else None,
            'qualifying_flights': len(qualifying_flights),
        }

    @staticmethod
    def check_faa_night_currency(
        flights: List[Dict[str, Any]],
        aircraft_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Check FAA 14 CFR 61.57(b) night currency.

        3 takeoffs and landings to a full stop at night
        within preceding 90 days.

        Args:
            flights: List of flight data dicts
            aircraft_type: Specific aircraft type

        Returns:
            Currency check result dict
        """
        cutoff_date = date.today() - timedelta(days=FAACurrencyRules.NIGHT_PERIOD_DAYS)

        qualifying_flights = [
            f for f in flights
            if (
                f.get('date') and
                date.fromisoformat(str(f['date'])) >= cutoff_date and
                (not aircraft_type or f.get('aircraft_type') == aircraft_type) and
                (f.get('takeoffs_night', 0) > 0 or f.get('landings_night', 0) > 0)
            )
        ]

        night_takeoffs = sum(f.get('takeoffs_night', 0) for f in qualifying_flights)
        night_landings = sum(f.get('landings_night', 0) for f in qualifying_flights)

        is_current = (
            night_takeoffs >= FAACurrencyRules.NIGHT_MIN_TAKEOFFS and
            night_landings >= FAACurrencyRules.NIGHT_MIN_LANDINGS
        )

        expiry_date = None
        if qualifying_flights and is_current:
            oldest_flight_date = min(
                date.fromisoformat(str(f['date'])) for f in qualifying_flights
            )
            expiry_date = oldest_flight_date + timedelta(days=FAACurrencyRules.NIGHT_PERIOD_DAYS)

        return {
            'regulation': 'FAA 14 CFR 61.57(b)',
            'requirement': 'night_operations',
            'is_current': is_current,
            'period_days': FAACurrencyRules.NIGHT_PERIOD_DAYS,
            'aircraft_type': aircraft_type,
            'current_count': {
                'night_takeoffs': night_takeoffs,
                'night_landings': night_landings,
            },
            'required_count': {
                'night_takeoffs': FAACurrencyRules.NIGHT_MIN_TAKEOFFS,
                'night_landings': FAACurrencyRules.NIGHT_MIN_LANDINGS,
            },
            'remaining_count': {
                'night_takeoffs': max(0, FAACurrencyRules.NIGHT_MIN_TAKEOFFS - night_takeoffs),
                'night_landings': max(0, FAACurrencyRules.NIGHT_MIN_LANDINGS - night_landings),
            },
            'expiry_date': expiry_date.isoformat() if expiry_date else None,
            'qualifying_flights': len(qualifying_flights),
        }

    @staticmethod
    def check_faa_ifr_currency(
        flights: List[Dict[str, Any]],
        include_simulator: bool = True
    ) -> Dict[str, Any]:
        """
        Check FAA 14 CFR 61.57(c) IFR currency.

        Within 6 calendar months:
        - 6 instrument approaches
        - Holding procedures
        - Intercepting and tracking courses

        Args:
            flights: List of flight data dicts
            include_simulator: Include simulator approaches

        Returns:
            Currency check result dict
        """
        cutoff_date = date.today() - timedelta(days=FAACurrencyRules.IFR_PERIOD_DAYS)

        qualifying_flights = [
            f for f in flights
            if (
                f.get('date') and
                date.fromisoformat(str(f['date'])) >= cutoff_date and
                (f.get('instrument_approaches', 0) > 0 or
                 f.get('holding_procedures', 0) > 0)
            )
        ]

        if include_simulator:
            qualifying_flights.extend([
                f for f in flights
                if (
                    f.get('date') and
                    date.fromisoformat(str(f['date'])) >= cutoff_date and
                    f.get('flight_type') == 'simulator' and
                    f.get('instrument_approaches', 0) > 0
                )
            ])

        approaches = sum(f.get('instrument_approaches', 0) for f in qualifying_flights)
        holding = sum(f.get('holding_procedures', 0) for f in qualifying_flights)

        is_current = (
            approaches >= FAACurrencyRules.IFR_MIN_APPROACHES and
            holding >= FAACurrencyRules.IFR_MIN_HOLDING
        )

        expiry_date = None
        if qualifying_flights and is_current:
            oldest_flight_date = min(
                date.fromisoformat(str(f['date'])) for f in qualifying_flights
            )
            expiry_date = oldest_flight_date + timedelta(days=FAACurrencyRules.IFR_PERIOD_DAYS)

        return {
            'regulation': 'FAA 14 CFR 61.57(c)',
            'requirement': 'ifr_operations',
            'is_current': is_current,
            'period_days': FAACurrencyRules.IFR_PERIOD_DAYS,
            'current_count': {
                'approaches': approaches,
                'holding_procedures': holding,
            },
            'required_count': {
                'approaches': FAACurrencyRules.IFR_MIN_APPROACHES,
                'holding_procedures': FAACurrencyRules.IFR_MIN_HOLDING,
            },
            'remaining_count': {
                'approaches': max(0, FAACurrencyRules.IFR_MIN_APPROACHES - approaches),
                'holding_procedures': max(0, FAACurrencyRules.IFR_MIN_HOLDING - holding),
            },
            'expiry_date': expiry_date.isoformat() if expiry_date else None,
            'qualifying_flights': len(qualifying_flights),
            'includes_simulator': include_simulator,
        }

    @staticmethod
    def check_faa_tailwheel_currency(
        flights: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Check FAA 14 CFR 61.57(a)(2) tailwheel currency.

        3 full-stop landings in tailwheel aircraft
        within preceding 90 days.

        Args:
            flights: List of flight data dicts

        Returns:
            Currency check result dict
        """
        cutoff_date = date.today() - timedelta(days=FAACurrencyRules.TAILWHEEL_PERIOD_DAYS)

        qualifying_flights = [
            f for f in flights
            if (
                f.get('date') and
                date.fromisoformat(str(f['date'])) >= cutoff_date and
                f.get('is_tailwheel', False) and
                f.get('full_stop_landings', 0) > 0
            )
        ]

        full_stop_landings = sum(f.get('full_stop_landings', 0) for f in qualifying_flights)

        is_current = full_stop_landings >= FAACurrencyRules.TAILWHEEL_MIN_LANDINGS

        expiry_date = None
        if qualifying_flights and is_current:
            oldest_flight_date = min(
                date.fromisoformat(str(f['date'])) for f in qualifying_flights
            )
            expiry_date = oldest_flight_date + timedelta(days=FAACurrencyRules.TAILWHEEL_PERIOD_DAYS)

        return {
            'regulation': 'FAA 14 CFR 61.57(a)(2)',
            'requirement': 'tailwheel_operations',
            'is_current': is_current,
            'period_days': FAACurrencyRules.TAILWHEEL_PERIOD_DAYS,
            'current_count': {
                'full_stop_landings': full_stop_landings,
            },
            'required_count': {
                'full_stop_landings': FAACurrencyRules.TAILWHEEL_MIN_LANDINGS,
            },
            'remaining_count': {
                'full_stop_landings': max(0, FAACurrencyRules.TAILWHEEL_MIN_LANDINGS - full_stop_landings),
            },
            'expiry_date': expiry_date.isoformat() if expiry_date else None,
            'qualifying_flights': len(qualifying_flights),
        }

    @staticmethod
    def get_currency_requirements_info(
        regulatory_authority: str = 'EASA'
    ) -> Dict[str, Any]:
        """
        Get currency requirements information for display.

        Args:
            regulatory_authority: EASA or FAA

        Returns:
            Requirements information dict
        """
        if regulatory_authority.upper() == 'EASA':
            return {
                'authority': 'EASA',
                'regulation': 'FCL.060',
                'requirements': [
                    {
                        'code': 'FCL.060(a)',
                        'name': 'Recent experience - passengers',
                        'description': '3 takeoffs and 3 landings as PF in same type/class within 90 days',
                        'period_days': EASACurrencyRules.PASSENGER_PERIOD_DAYS,
                        'minimum': {
                            'takeoffs': EASACurrencyRules.PASSENGER_MIN_TAKEOFFS,
                            'landings': EASACurrencyRules.PASSENGER_MIN_LANDINGS,
                        },
                    },
                    {
                        'code': 'FCL.060(b)',
                        'name': 'Instrument recency',
                        'description': '6 approaches and holding procedures within 6 months',
                        'period_days': EASACurrencyRules.IFR_PERIOD_DAYS,
                        'minimum': {
                            'approaches': EASACurrencyRules.IFR_MIN_APPROACHES,
                            'holding_procedures': EASACurrencyRules.IFR_MIN_HOLDING,
                        },
                    },
                    {
                        'code': 'FCL.060(c)',
                        'name': 'Night operations',
                        'description': '1 night takeoff and 1 night landing within 90 days',
                        'period_days': EASACurrencyRules.NIGHT_PERIOD_DAYS,
                        'minimum': {
                            'night_takeoffs': EASACurrencyRules.NIGHT_MIN_TAKEOFFS,
                            'night_landings': EASACurrencyRules.NIGHT_MIN_LANDINGS,
                        },
                    },
                ],
            }
        else:
            return {
                'authority': 'FAA',
                'regulation': '14 CFR 61.57',
                'requirements': [
                    {
                        'code': '61.57(a)',
                        'name': 'Recent experience - passengers',
                        'description': '3 takeoffs and 3 landings in same category, class, type within 90 days',
                        'period_days': FAACurrencyRules.PASSENGER_PERIOD_DAYS,
                        'minimum': {
                            'takeoffs': FAACurrencyRules.PASSENGER_MIN_TAKEOFFS,
                            'landings': FAACurrencyRules.PASSENGER_MIN_LANDINGS,
                        },
                    },
                    {
                        'code': '61.57(b)',
                        'name': 'Night - passengers',
                        'description': '3 night takeoffs and landings to full stop within 90 days',
                        'period_days': FAACurrencyRules.NIGHT_PERIOD_DAYS,
                        'minimum': {
                            'night_takeoffs': FAACurrencyRules.NIGHT_MIN_TAKEOFFS,
                            'night_landings': FAACurrencyRules.NIGHT_MIN_LANDINGS,
                        },
                    },
                    {
                        'code': '61.57(c)',
                        'name': 'Instrument experience',
                        'description': '6 approaches and holding procedures within 6 calendar months',
                        'period_days': FAACurrencyRules.IFR_PERIOD_DAYS,
                        'minimum': {
                            'approaches': FAACurrencyRules.IFR_MIN_APPROACHES,
                            'holding_procedures': FAACurrencyRules.IFR_MIN_HOLDING,
                        },
                    },
                    {
                        'code': '61.57(a)(2)',
                        'name': 'Tailwheel',
                        'description': '3 full-stop landings in tailwheel aircraft within 90 days',
                        'period_days': FAACurrencyRules.TAILWHEEL_PERIOD_DAYS,
                        'minimum': {
                            'full_stop_landings': FAACurrencyRules.TAILWHEEL_MIN_LANDINGS,
                        },
                    },
                ],
            }
