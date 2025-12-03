# services/certificate-service/src/apps/core/services/currency_service.py
"""
Currency Service

Business logic for pilot currency tracking.
"""

import logging
from datetime import date, timedelta
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
