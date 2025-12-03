# services/flight-service/src/apps/api/views/currency_views.py
"""
Currency Views

REST API views for pilot currency operations.
"""

import logging
from uuid import UUID

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.services import CurrencyService
from apps.core.services.exceptions import FlightValidationError
from apps.api.serializers import CurrencyStatusSerializer
from apps.api.serializers.statistics_serializers import (
    CurrencyValidationSerializer,
    CurrencyValidationRequestSerializer,
)
from .base import BaseFlightViewSet

logger = logging.getLogger(__name__)


class CurrencyViewSet(BaseFlightViewSet):
    """
    ViewSet for pilot currency operations.

    Handles currency checks, validation, and status tracking.
    """

    # ==========================================================================
    # Currency Status
    # ==========================================================================

    @action(detail=False, methods=['get'])
    def status(self, request):
        """
        Get pilot currency status.

        GET /api/v1/currency/status/
        """
        organization_id = self.get_organization_id()

        # Get pilot_id from query params or use current user
        pilot_id = request.query_params.get('pilot_id')
        if pilot_id:
            pilot_id = UUID(pilot_id)
        else:
            pilot_id = self.get_user_id()

        status_data = CurrencyService.get_currency_summary(
            organization_id=organization_id,
            user_id=pilot_id
        )

        serializer = CurrencyStatusSerializer(status_data)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def check(self, request):
        """
        Check all currency requirements for a pilot.

        GET /api/v1/currency/check/
        """
        organization_id = self.get_organization_id()

        pilot_id = request.query_params.get('pilot_id')
        if pilot_id:
            pilot_id = UUID(pilot_id)
        else:
            pilot_id = self.get_user_id()

        results = CurrencyService.check_all_currency(
            organization_id=organization_id,
            user_id=pilot_id
        )

        # Convert results to serializable format
        currency_data = []
        for result in results:
            currency_data.append({
                'type': result.currency_type.value,
                'status': result.status.value,
                'current': result.current_count,
                'required': result.required_count,
                'period_days': result.period_days,
                'expires_on': result.expires_on.isoformat() if result.expires_on else None,
                'days_remaining': result.days_remaining,
                'description': result.details.get('description') if result.details else None,
            })

        return Response({
            'pilot_id': str(pilot_id),
            'currencies': currency_data
        })

    # ==========================================================================
    # Pre-flight Validation
    # ==========================================================================

    @action(detail=False, methods=['post'])
    def validate_for_flight(self, request):
        """
        Validate pilot currency for a specific flight.

        POST /api/v1/currency/validate_for_flight/
        """
        organization_id = self.get_organization_id()

        pilot_id = request.data.get('pilot_id')
        if pilot_id:
            pilot_id = UUID(pilot_id)
        else:
            pilot_id = self.get_user_id()

        serializer = CurrencyValidationRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        validation = CurrencyService.validate_for_flight(
            organization_id=organization_id,
            user_id=pilot_id,
            flight_type=serializer.validated_data['flight_type'],
            flight_rules=serializer.validated_data['flight_rules'],
            has_passengers=serializer.validated_data.get('has_passengers', False),
            is_night=serializer.validated_data.get('is_night', False)
        )

        response_serializer = CurrencyValidationSerializer(validation)
        return Response(response_serializer.data)

    # ==========================================================================
    # Organization-wide Currency
    # ==========================================================================

    @action(detail=False, methods=['get'])
    def organization(self, request):
        """
        Check currency for all pilots in organization.

        GET /api/v1/currency/organization/
        """
        organization_id = self.get_organization_id()

        results = CurrencyService.check_organization_currency(
            organization_id=organization_id
        )

        return Response({
            'organization_id': str(organization_id),
            'pilots': results
        })

    @action(detail=False, methods=['get'])
    def expiring(self, request):
        """
        Get pilots with expiring currency.

        GET /api/v1/currency/expiring/
        """
        organization_id = self.get_organization_id()

        # Get days threshold from query params (default 30)
        days = int(request.query_params.get('days', 30))

        all_pilots = CurrencyService.check_organization_currency(
            organization_id=organization_id
        )

        # Filter to pilots with expiring or expired currency
        expiring_pilots = []
        for pilot in all_pilots:
            if pilot['expired_count'] > 0 or pilot['expiring_soon_count'] > 0:
                expiring_pilots.append(pilot)

        return Response({
            'organization_id': str(organization_id),
            'threshold_days': days,
            'count': len(expiring_pilots),
            'pilots': expiring_pilots
        })

    # ==========================================================================
    # Currency Details
    # ==========================================================================

    @action(detail=False, methods=['get'])
    def day_vfr(self, request):
        """
        Get day VFR currency details.

        GET /api/v1/currency/day_vfr/
        """
        organization_id = self.get_organization_id()

        pilot_id = request.query_params.get('pilot_id')
        if pilot_id:
            pilot_id = UUID(pilot_id)
        else:
            pilot_id = self.get_user_id()

        from apps.core.services.currency_service import CurrencyType

        requirement = next(
            (r for r in CurrencyService.STANDARD_REQUIREMENTS
             if r.currency_type == CurrencyType.DAY_VFR),
            None
        )

        if requirement:
            result = CurrencyService.check_currency(
                organization_id=organization_id,
                user_id=pilot_id,
                requirement=requirement
            )

            return Response({
                'pilot_id': str(pilot_id),
                'type': result.currency_type.value,
                'status': result.status.value,
                'current': result.current_count,
                'required': result.required_count,
                'period_days': result.period_days,
                'expires_on': result.expires_on.isoformat() if result.expires_on else None,
                'days_remaining': result.days_remaining,
                'description': result.details.get('description') if result.details else None,
            })

        return Response({'error': 'Currency type not found'}, status=400)

    @action(detail=False, methods=['get'])
    def night_vfr(self, request):
        """
        Get night VFR currency details.

        GET /api/v1/currency/night_vfr/
        """
        organization_id = self.get_organization_id()

        pilot_id = request.query_params.get('pilot_id')
        if pilot_id:
            pilot_id = UUID(pilot_id)
        else:
            pilot_id = self.get_user_id()

        from apps.core.services.currency_service import CurrencyType

        requirement = next(
            (r for r in CurrencyService.STANDARD_REQUIREMENTS
             if r.currency_type == CurrencyType.NIGHT_VFR),
            None
        )

        if requirement:
            result = CurrencyService.check_currency(
                organization_id=organization_id,
                user_id=pilot_id,
                requirement=requirement
            )

            return Response({
                'pilot_id': str(pilot_id),
                'type': result.currency_type.value,
                'status': result.status.value,
                'current': result.current_count,
                'required': result.required_count,
                'period_days': result.period_days,
                'expires_on': result.expires_on.isoformat() if result.expires_on else None,
                'days_remaining': result.days_remaining,
                'description': result.details.get('description') if result.details else None,
            })

        return Response({'error': 'Currency type not found'}, status=400)

    @action(detail=False, methods=['get'])
    def ifr(self, request):
        """
        Get IFR currency details.

        GET /api/v1/currency/ifr/
        """
        organization_id = self.get_organization_id()

        pilot_id = request.query_params.get('pilot_id')
        if pilot_id:
            pilot_id = UUID(pilot_id)
        else:
            pilot_id = self.get_user_id()

        from apps.core.services.currency_service import CurrencyType

        requirement = next(
            (r for r in CurrencyService.STANDARD_REQUIREMENTS
             if r.currency_type == CurrencyType.IFR),
            None
        )

        if requirement:
            result = CurrencyService.check_currency(
                organization_id=organization_id,
                user_id=pilot_id,
                requirement=requirement
            )

            return Response({
                'pilot_id': str(pilot_id),
                'type': result.currency_type.value,
                'status': result.status.value,
                'current': result.current_count,
                'required': result.required_count,
                'period_days': result.period_days,
                'expires_on': result.expires_on.isoformat() if result.expires_on else None,
                'days_remaining': result.days_remaining,
                'description': result.details.get('description') if result.details else None,
            })

        return Response({'error': 'Currency type not found'}, status=400)
