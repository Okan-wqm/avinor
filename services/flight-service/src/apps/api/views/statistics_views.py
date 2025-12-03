# services/flight-service/src/apps/api/views/statistics_views.py
"""
Statistics Views

REST API views for flight statistics and analytics.
"""

import logging
from uuid import UUID

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.services import StatisticsService
from apps.core.services.exceptions import FlightValidationError
from apps.api.serializers import (
    PilotStatisticsSerializer,
    AircraftStatisticsSerializer,
    OrganizationStatisticsSerializer,
    DashboardStatisticsSerializer,
)
from apps.api.serializers.statistics_serializers import (
    TrainingStatisticsSerializer,
    PeriodComparisonSerializer,
    PeriodComparisonRequestSerializer,
    StatisticsFilterSerializer,
)
from .base import BaseFlightViewSet, DateRangeMixin

logger = logging.getLogger(__name__)


class StatisticsViewSet(BaseFlightViewSet, DateRangeMixin):
    """
    ViewSet for flight statistics operations.

    Provides comprehensive statistics and analytics.
    """

    # ==========================================================================
    # Dashboard
    # ==========================================================================

    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        """
        Get dashboard statistics.

        GET /api/v1/statistics/dashboard/
        """
        organization_id = self.get_organization_id()
        user_id = self.get_optional_user_id()

        stats = StatisticsService.get_dashboard_statistics(
            organization_id=organization_id,
            user_id=user_id
        )

        serializer = DashboardStatisticsSerializer(stats)
        return Response(serializer.data)

    # ==========================================================================
    # Pilot Statistics
    # ==========================================================================

    @action(detail=False, methods=['get'])
    def pilot(self, request):
        """
        Get pilot statistics.

        GET /api/v1/statistics/pilot/?pilot_id={uuid}
        """
        organization_id = self.get_organization_id()
        start_date, end_date = self.get_date_range()

        # Get pilot_id from query params or use current user
        pilot_id = request.query_params.get('pilot_id')
        if pilot_id:
            pilot_id = UUID(pilot_id)
        else:
            pilot_id = self.get_user_id()

        stats = StatisticsService.get_pilot_statistics(
            organization_id=organization_id,
            user_id=pilot_id,
            start_date=start_date,
            end_date=end_date
        )

        serializer = PilotStatisticsSerializer(stats)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def pilot_approaches(self, request):
        """
        Get pilot approach statistics.

        GET /api/v1/statistics/pilot_approaches/?pilot_id={uuid}
        """
        organization_id = self.get_organization_id()
        start_date, end_date = self.get_date_range()

        pilot_id = request.query_params.get('pilot_id')
        if pilot_id:
            pilot_id = UUID(pilot_id)
        else:
            pilot_id = self.get_user_id()

        stats = StatisticsService.get_pilot_approach_statistics(
            organization_id=organization_id,
            user_id=pilot_id,
            start_date=start_date,
            end_date=end_date
        )

        return Response(stats)

    # ==========================================================================
    # Aircraft Statistics
    # ==========================================================================

    @action(detail=False, methods=['get'])
    def aircraft(self, request):
        """
        Get aircraft statistics.

        GET /api/v1/statistics/aircraft/?aircraft_id={uuid}
        """
        organization_id = self.get_organization_id()
        start_date, end_date = self.get_date_range()

        aircraft_id = request.query_params.get('aircraft_id')
        if not aircraft_id:
            raise FlightValidationError(
                message="aircraft_id is required",
                field="aircraft_id"
            )

        stats = StatisticsService.get_aircraft_statistics(
            organization_id=organization_id,
            aircraft_id=UUID(aircraft_id),
            start_date=start_date,
            end_date=end_date
        )

        serializer = AircraftStatisticsSerializer(stats)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def aircraft_fuel(self, request):
        """
        Get aircraft fuel statistics.

        GET /api/v1/statistics/aircraft_fuel/?aircraft_id={uuid}
        """
        organization_id = self.get_organization_id()
        start_date, end_date = self.get_date_range()

        aircraft_id = request.query_params.get('aircraft_id')
        if not aircraft_id:
            raise FlightValidationError(
                message="aircraft_id is required",
                field="aircraft_id"
            )

        stats = StatisticsService.get_aircraft_fuel_statistics(
            organization_id=organization_id,
            aircraft_id=UUID(aircraft_id),
            start_date=start_date,
            end_date=end_date
        )

        return Response(stats)

    # ==========================================================================
    # Organization Statistics
    # ==========================================================================

    @action(detail=False, methods=['get'])
    def organization(self, request):
        """
        Get organization-wide statistics.

        GET /api/v1/statistics/organization/
        """
        organization_id = self.get_organization_id()
        start_date, end_date = self.get_date_range()

        stats = StatisticsService.get_organization_statistics(
            organization_id=organization_id,
            start_date=start_date,
            end_date=end_date
        )

        serializer = OrganizationStatisticsSerializer(stats)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def training(self, request):
        """
        Get training statistics.

        GET /api/v1/statistics/training/
        """
        organization_id = self.get_organization_id()
        start_date, end_date = self.get_date_range()

        stats = StatisticsService.get_organization_training_statistics(
            organization_id=organization_id,
            start_date=start_date,
            end_date=end_date
        )

        serializer = TrainingStatisticsSerializer(stats)
        return Response(serializer.data)

    # ==========================================================================
    # Comparisons
    # ==========================================================================

    @action(detail=False, methods=['post'])
    def compare(self, request):
        """
        Compare statistics between two periods.

        POST /api/v1/statistics/compare/
        """
        organization_id = self.get_organization_id()

        serializer = PeriodComparisonRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user_id = serializer.validated_data.get('user_id')

        comparison = StatisticsService.get_period_comparison(
            organization_id=organization_id,
            period_1_start=serializer.validated_data['period_1_start'],
            period_1_end=serializer.validated_data['period_1_end'],
            period_2_start=serializer.validated_data['period_2_start'],
            period_2_end=serializer.validated_data['period_2_end'],
            user_id=user_id
        )

        response_serializer = PeriodComparisonSerializer(comparison)
        return Response(response_serializer.data)

    # ==========================================================================
    # Summary Reports
    # ==========================================================================

    @action(detail=False, methods=['get'])
    def summary_report(self, request):
        """
        Get a comprehensive summary report.

        GET /api/v1/statistics/summary_report/
        """
        organization_id = self.get_organization_id()
        start_date, end_date = self.get_date_range()

        # Get all statistics
        org_stats = StatisticsService.get_organization_statistics(
            organization_id=organization_id,
            start_date=start_date,
            end_date=end_date
        )

        training_stats = StatisticsService.get_organization_training_statistics(
            organization_id=organization_id,
            start_date=start_date,
            end_date=end_date
        )

        return Response({
            'organization': org_stats,
            'training': training_stats,
            'period': {
                'start': start_date.isoformat() if start_date else None,
                'end': end_date.isoformat() if end_date else None,
            }
        })
