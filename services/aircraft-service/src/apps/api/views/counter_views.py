# services/aircraft-service/src/apps/api/views/counter_views.py
"""
Counter Views

ViewSet for aircraft counter and time tracking management.
"""

import logging
from datetime import date, timedelta

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from apps.core.models import Aircraft, AircraftTimeLog
from apps.core.services import CounterService, CounterError, AircraftNotFoundError
from apps.api.serializers import (
    CounterSerializer,
    CounterUpdateSerializer,
    CounterAdjustmentSerializer,
    TimeLogSerializer,
    UtilizationStatsSerializer,
    PeriodSummarySerializer,
    BulkImportSerializer,
)

logger = logging.getLogger(__name__)


class CounterViewSet(viewsets.ViewSet):
    """
    ViewSet for counter management.

    Nested under aircraft: /aircraft/{aircraft_id}/counters/

    Actions:
    - list: Get current counter values
    - update_flight: Add flight time
    - adjustment: Make manual adjustment
    - logs: Get time log history
    - summary: Get period summary
    - utilization: Get utilization statistics
    - import: Bulk import counters
    """

    permission_classes = [IsAuthenticated]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.counter_service = CounterService()

    def list(self, request, aircraft_pk=None):
        """Get current counter values."""
        try:
            counters = self.counter_service.get_counters(aircraft_pk)
            serializer = CounterSerializer(counters)
            return Response(serializer.data)
        except AircraftNotFoundError:
            return Response(
                {'error': 'Aircraft not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['post'], url_path='flight')
    def update_flight(self, request, aircraft_pk=None):
        """Add flight time to counters."""
        serializer = CounterUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user_id = request.headers.get('X-User-ID')

        try:
            result = self.counter_service.add_flight_time(
                aircraft_id=aircraft_pk,
                flight_id=serializer.validated_data['flight_id'],
                hobbs_time=serializer.validated_data['hobbs_time'],
                tach_time=serializer.validated_data.get('tach_time'),
                landings=serializer.validated_data.get('landings', 0),
                cycles=serializer.validated_data.get('cycles', 0),
                flight_date=serializer.validated_data.get('flight_date'),
                engine_times=serializer.validated_data.get('engine_times'),
                created_by=user_id,
                notes=serializer.validated_data.get('notes'),
            )
            return Response(result, status=status.HTTP_201_CREATED)
        except AircraftNotFoundError:
            return Response(
                {'error': 'Aircraft not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except CounterError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['post'])
    def adjustment(self, request, aircraft_pk=None):
        """Make a manual counter adjustment."""
        serializer = CounterAdjustmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user_id = request.headers.get('X-User-ID')
        user_name = request.headers.get('X-User-Name', '')

        try:
            result = self.counter_service.adjust_counter(
                aircraft_id=aircraft_pk,
                field=serializer.validated_data['field'],
                new_value=serializer.validated_data['new_value'],
                reason=serializer.validated_data['reason'],
                created_by=user_id,
                created_by_name=user_name,
            )
            return Response(result)
        except AircraftNotFoundError:
            return Response(
                {'error': 'Aircraft not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except CounterError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['post'], url_path='engine-adjustment')
    def engine_adjustment(self, request, aircraft_pk=None):
        """Make an engine-specific counter adjustment."""
        engine_position = request.data.get('engine_position')
        field = request.data.get('field')
        new_value = request.data.get('new_value')
        reason = request.data.get('reason')

        if not all([engine_position, field, new_value, reason]):
            return Response(
                {'error': 'engine_position, field, new_value, and reason are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user_id = request.headers.get('X-User-ID')

        try:
            from decimal import Decimal
            result = self.counter_service.adjust_engine_counter(
                aircraft_id=aircraft_pk,
                engine_position=int(engine_position),
                field=field,
                new_value=Decimal(str(new_value)),
                reason=reason,
                created_by=user_id,
            )
            return Response(result)
        except AircraftNotFoundError:
            return Response(
                {'error': 'Aircraft not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except CounterError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['get'])
    def logs(self, request, aircraft_pk=None):
        """Get time log history."""
        # Parse query params
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        source_type = request.query_params.get('source_type')
        limit = int(request.query_params.get('limit', 100))
        offset = int(request.query_params.get('offset', 0))

        # Parse dates
        if start_date:
            start_date = date.fromisoformat(start_date)
        if end_date:
            end_date = date.fromisoformat(end_date)

        try:
            result = self.counter_service.get_time_logs(
                aircraft_id=aircraft_pk,
                start_date=start_date,
                end_date=end_date,
                source_type=source_type,
                limit=limit,
                offset=offset,
            )
            return Response(result)
        except AircraftNotFoundError:
            return Response(
                {'error': 'Aircraft not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['get'])
    def summary(self, request, aircraft_pk=None):
        """Get period summary."""
        # Default to last 30 days
        end_date = request.query_params.get('end_date')
        start_date = request.query_params.get('start_date')

        if end_date:
            end_date = date.fromisoformat(end_date)
        else:
            end_date = date.today()

        if start_date:
            start_date = date.fromisoformat(start_date)
        else:
            start_date = end_date - timedelta(days=30)

        try:
            result = self.counter_service.get_period_summary(
                aircraft_id=aircraft_pk,
                start_date=start_date,
                end_date=end_date,
            )
            serializer = PeriodSummarySerializer(result)
            return Response(serializer.data)
        except AircraftNotFoundError:
            return Response(
                {'error': 'Aircraft not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['get'])
    def utilization(self, request, aircraft_pk=None):
        """Get utilization statistics."""
        period_days = int(request.query_params.get('days', 30))

        try:
            result = self.counter_service.get_utilization_stats(
                aircraft_id=aircraft_pk,
                period_days=period_days,
            )
            serializer = UtilizationStatsSerializer(result)
            return Response(serializer.data)
        except AircraftNotFoundError:
            return Response(
                {'error': 'Aircraft not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['post'], url_path='import')
    def bulk_import(self, request, aircraft_pk=None):
        """Bulk import counter values."""
        serializer = BulkImportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user_id = request.headers.get('X-User-ID')

        try:
            result = self.counter_service.bulk_import_counters(
                aircraft_id=aircraft_pk,
                counters=serializer.validated_data,
                import_date=serializer.validated_data.get('import_date'),
                created_by=user_id,
                notes=serializer.validated_data.get('notes'),
            )
            return Response(result, status=status.HTTP_201_CREATED)
        except AircraftNotFoundError:
            return Response(
                {'error': 'Aircraft not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except CounterError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
