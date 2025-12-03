# services/flight-service/src/apps/api/views/fuel_views.py
"""
Fuel and Oil Record Views

REST API views for fuel and oil record operations.
"""

import logging
from uuid import UUID

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.models import FuelRecord, OilRecord
from apps.core.services import FlightService, StatisticsService
from apps.core.services.exceptions import FlightValidationError
from apps.api.serializers import (
    FuelRecordSerializer,
    FuelRecordCreateSerializer,
    OilRecordSerializer,
    OilRecordCreateSerializer,
)
from apps.api.serializers.fuel_serializers import (
    FuelRecordUpdateSerializer,
    FuelStatisticsSerializer,
)
from .base import BaseFlightViewSet, PaginationMixin, DateRangeMixin

logger = logging.getLogger(__name__)


class FuelRecordViewSet(BaseFlightViewSet, PaginationMixin, DateRangeMixin):
    """
    ViewSet for fuel record operations.
    """

    def list(self, request):
        """
        List fuel records with optional filters.

        GET /api/v1/fuel-records/
        """
        organization_id = self.get_organization_id()
        page, page_size = self.get_pagination_params()

        queryset = FuelRecord.objects.filter(organization_id=organization_id)

        # Apply filters
        flight_id = request.query_params.get('flight_id')
        if flight_id:
            queryset = queryset.filter(flight_id=UUID(flight_id))

        aircraft_id = request.query_params.get('aircraft_id')
        if aircraft_id:
            queryset = queryset.filter(aircraft_id=UUID(aircraft_id))

        record_type = request.query_params.get('record_type')
        if record_type:
            queryset = queryset.filter(record_type=record_type)

        fuel_type = request.query_params.get('fuel_type')
        if fuel_type:
            queryset = queryset.filter(fuel_type=fuel_type)

        location = request.query_params.get('location_icao')
        if location:
            queryset = queryset.filter(location_icao=location.upper())

        # Date range
        start_date, end_date = self.get_date_range()
        if start_date:
            queryset = queryset.filter(recorded_at__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(recorded_at__date__lte=end_date)

        queryset = queryset.order_by('-recorded_at')

        from django.core.paginator import Paginator
        paginator = Paginator(queryset, page_size)
        page_obj = paginator.get_page(page)

        serializer = FuelRecordSerializer(page_obj.object_list, many=True)
        return Response({
            'results': serializer.data,
            'total': paginator.count,
            'page': page,
            'page_size': page_size,
            'total_pages': paginator.num_pages,
        })

    def retrieve(self, request, pk=None):
        """
        Retrieve a single fuel record.

        GET /api/v1/fuel-records/{id}/
        """
        organization_id = self.get_organization_id()

        try:
            record = FuelRecord.objects.get(
                id=UUID(pk),
                organization_id=organization_id
            )
        except FuelRecord.DoesNotExist:
            raise FlightValidationError(
                message=f"Fuel record not found: {pk}",
                field="id"
            )

        serializer = FuelRecordSerializer(record)
        return Response(serializer.data)

    def create(self, request):
        """
        Create a new fuel record.

        POST /api/v1/fuel-records/
        """
        organization_id = self.get_organization_id()
        user_id = self.get_user_id()

        flight_id = request.data.get('flight_id')
        if not flight_id:
            raise FlightValidationError(
                message="flight_id is required",
                field="flight_id"
            )

        serializer = FuelRecordCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        record = FlightService.add_fuel_record(
            flight_id=UUID(flight_id),
            organization_id=organization_id,
            created_by=user_id,
            fuel_data=serializer.validated_data
        )

        response_serializer = FuelRecordSerializer(record)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, pk=None):
        """
        Update a fuel record.

        PUT /api/v1/fuel-records/{id}/
        """
        organization_id = self.get_organization_id()

        try:
            record = FuelRecord.objects.get(
                id=UUID(pk),
                organization_id=organization_id
            )
        except FuelRecord.DoesNotExist:
            raise FlightValidationError(
                message=f"Fuel record not found: {pk}",
                field="id"
            )

        serializer = FuelRecordUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        for key, value in serializer.validated_data.items():
            setattr(record, key, value)
        record.save()

        response_serializer = FuelRecordSerializer(record)
        return Response(response_serializer.data)

    def destroy(self, request, pk=None):
        """
        Delete a fuel record.

        DELETE /api/v1/fuel-records/{id}/
        """
        organization_id = self.get_organization_id()

        try:
            record = FuelRecord.objects.get(
                id=UUID(pk),
                organization_id=organization_id
            )
        except FuelRecord.DoesNotExist:
            raise FlightValidationError(
                message=f"Fuel record not found: {pk}",
                field="id"
            )

        record.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'])
    def by_flight(self, request):
        """
        Get fuel records for a specific flight.

        GET /api/v1/fuel-records/by_flight/?flight_id={uuid}
        """
        organization_id = self.get_organization_id()

        flight_id = request.query_params.get('flight_id')
        if not flight_id:
            raise FlightValidationError(
                message="flight_id is required",
                field="flight_id"
            )

        records = FuelRecord.objects.filter(
            flight_id=UUID(flight_id),
            organization_id=organization_id
        ).order_by('recorded_at')

        serializer = FuelRecordSerializer(records, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def by_aircraft(self, request):
        """
        Get fuel records for a specific aircraft.

        GET /api/v1/fuel-records/by_aircraft/?aircraft_id={uuid}
        """
        organization_id = self.get_organization_id()

        aircraft_id = request.query_params.get('aircraft_id')
        if not aircraft_id:
            raise FlightValidationError(
                message="aircraft_id is required",
                field="aircraft_id"
            )

        start_date, end_date = self.get_date_range()

        queryset = FuelRecord.objects.filter(
            aircraft_id=UUID(aircraft_id),
            organization_id=organization_id
        )

        if start_date:
            queryset = queryset.filter(recorded_at__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(recorded_at__date__lte=end_date)

        queryset = queryset.order_by('-recorded_at')

        serializer = FuelRecordSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """
        Get fuel statistics for an aircraft.

        GET /api/v1/fuel-records/statistics/?aircraft_id={uuid}
        """
        organization_id = self.get_organization_id()

        aircraft_id = request.query_params.get('aircraft_id')
        if not aircraft_id:
            raise FlightValidationError(
                message="aircraft_id is required",
                field="aircraft_id"
            )

        start_date, end_date = self.get_date_range()

        stats = StatisticsService.get_aircraft_fuel_statistics(
            organization_id=organization_id,
            aircraft_id=UUID(aircraft_id),
            start_date=start_date,
            end_date=end_date
        )

        serializer = FuelStatisticsSerializer(stats)
        return Response(serializer.data)


class OilRecordViewSet(BaseFlightViewSet, PaginationMixin, DateRangeMixin):
    """
    ViewSet for oil record operations.
    """

    def list(self, request):
        """
        List oil records with optional filters.

        GET /api/v1/oil-records/
        """
        organization_id = self.get_organization_id()
        page, page_size = self.get_pagination_params()

        queryset = OilRecord.objects.filter(organization_id=organization_id)

        # Apply filters
        flight_id = request.query_params.get('flight_id')
        if flight_id:
            queryset = queryset.filter(flight_id=UUID(flight_id))

        aircraft_id = request.query_params.get('aircraft_id')
        if aircraft_id:
            queryset = queryset.filter(aircraft_id=UUID(aircraft_id))

        # Date range
        start_date, end_date = self.get_date_range()
        if start_date:
            queryset = queryset.filter(recorded_at__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(recorded_at__date__lte=end_date)

        queryset = queryset.order_by('-recorded_at')

        from django.core.paginator import Paginator
        paginator = Paginator(queryset, page_size)
        page_obj = paginator.get_page(page)

        serializer = OilRecordSerializer(page_obj.object_list, many=True)
        return Response({
            'results': serializer.data,
            'total': paginator.count,
            'page': page,
            'page_size': page_size,
            'total_pages': paginator.num_pages,
        })

    def retrieve(self, request, pk=None):
        """
        Retrieve a single oil record.

        GET /api/v1/oil-records/{id}/
        """
        organization_id = self.get_organization_id()

        try:
            record = OilRecord.objects.get(
                id=UUID(pk),
                organization_id=organization_id
            )
        except OilRecord.DoesNotExist:
            raise FlightValidationError(
                message=f"Oil record not found: {pk}",
                field="id"
            )

        serializer = OilRecordSerializer(record)
        return Response(serializer.data)

    def create(self, request):
        """
        Create a new oil record.

        POST /api/v1/oil-records/
        """
        organization_id = self.get_organization_id()
        user_id = self.get_user_id()

        flight_id = request.data.get('flight_id')
        if not flight_id:
            raise FlightValidationError(
                message="flight_id is required",
                field="flight_id"
            )

        serializer = OilRecordCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        record = FlightService.add_oil_record(
            flight_id=UUID(flight_id),
            organization_id=organization_id,
            created_by=user_id,
            oil_data=serializer.validated_data
        )

        response_serializer = OilRecordSerializer(record)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, pk=None):
        """
        Update an oil record.

        PUT /api/v1/oil-records/{id}/
        """
        organization_id = self.get_organization_id()

        try:
            record = OilRecord.objects.get(
                id=UUID(pk),
                organization_id=organization_id
            )
        except OilRecord.DoesNotExist:
            raise FlightValidationError(
                message=f"Oil record not found: {pk}",
                field="id"
            )

        serializer = OilRecordCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        for key, value in serializer.validated_data.items():
            setattr(record, key, value)
        record.save()

        response_serializer = OilRecordSerializer(record)
        return Response(response_serializer.data)

    def destroy(self, request, pk=None):
        """
        Delete an oil record.

        DELETE /api/v1/oil-records/{id}/
        """
        organization_id = self.get_organization_id()

        try:
            record = OilRecord.objects.get(
                id=UUID(pk),
                organization_id=organization_id
            )
        except OilRecord.DoesNotExist:
            raise FlightValidationError(
                message=f"Oil record not found: {pk}",
                field="id"
            )

        record.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'])
    def by_flight(self, request):
        """
        Get oil records for a specific flight.

        GET /api/v1/oil-records/by_flight/?flight_id={uuid}
        """
        organization_id = self.get_organization_id()

        flight_id = request.query_params.get('flight_id')
        if not flight_id:
            raise FlightValidationError(
                message="flight_id is required",
                field="flight_id"
            )

        records = OilRecord.objects.filter(
            flight_id=UUID(flight_id),
            organization_id=organization_id
        ).order_by('recorded_at')

        serializer = OilRecordSerializer(records, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def by_aircraft(self, request):
        """
        Get oil records for a specific aircraft.

        GET /api/v1/oil-records/by_aircraft/?aircraft_id={uuid}
        """
        organization_id = self.get_organization_id()

        aircraft_id = request.query_params.get('aircraft_id')
        if not aircraft_id:
            raise FlightValidationError(
                message="aircraft_id is required",
                field="aircraft_id"
            )

        start_date, end_date = self.get_date_range()

        queryset = OilRecord.objects.filter(
            aircraft_id=UUID(aircraft_id),
            organization_id=organization_id
        )

        if start_date:
            queryset = queryset.filter(recorded_at__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(recorded_at__date__lte=end_date)

        queryset = queryset.order_by('-recorded_at')

        serializer = OilRecordSerializer(queryset, many=True)
        return Response(serializer.data)
