# services/flight-service/src/apps/api/views/approach_views.py
"""
Approach and Hold Views

REST API views for approach and holding pattern operations.
"""

import logging
from uuid import UUID

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.models import Approach, Hold
from apps.core.services import FlightService
from apps.core.services.exceptions import FlightValidationError
from apps.api.serializers import (
    ApproachSerializer,
    ApproachCreateSerializer,
    HoldSerializer,
    HoldCreateSerializer,
)
from apps.api.serializers.approach_serializers import (
    ApproachBulkCreateSerializer,
    ApproachStatisticsSerializer,
)
from .base import BaseFlightViewSet, PaginationMixin

logger = logging.getLogger(__name__)


class ApproachViewSet(BaseFlightViewSet, PaginationMixin):
    """
    ViewSet for approach operations.

    Approaches are managed in the context of flights.
    """

    def list(self, request):
        """
        List approaches with optional filters.

        GET /api/v1/approaches/
        """
        organization_id = self.get_organization_id()
        page, page_size = self.get_pagination_params()

        # Build query
        queryset = Approach.objects.filter(organization_id=organization_id)

        # Apply filters
        flight_id = request.query_params.get('flight_id')
        if flight_id:
            queryset = queryset.filter(flight_id=UUID(flight_id))

        approach_type = request.query_params.get('approach_type')
        if approach_type:
            queryset = queryset.filter(approach_type=approach_type)

        airport = request.query_params.get('airport_icao')
        if airport:
            queryset = queryset.filter(airport_icao=airport.upper())

        in_imc = request.query_params.get('in_imc')
        if in_imc is not None:
            queryset = queryset.filter(in_imc=in_imc.lower() == 'true')

        # Order
        queryset = queryset.order_by('-executed_at', '-created_at')

        # Paginate
        from django.core.paginator import Paginator
        paginator = Paginator(queryset, page_size)
        page_obj = paginator.get_page(page)

        serializer = ApproachSerializer(page_obj.object_list, many=True)
        return Response({
            'results': serializer.data,
            'total': paginator.count,
            'page': page,
            'page_size': page_size,
            'total_pages': paginator.num_pages,
        })

    def retrieve(self, request, pk=None):
        """
        Retrieve a single approach.

        GET /api/v1/approaches/{id}/
        """
        organization_id = self.get_organization_id()

        try:
            approach = Approach.objects.get(
                id=UUID(pk),
                organization_id=organization_id
            )
        except Approach.DoesNotExist:
            raise FlightValidationError(
                message=f"Approach not found: {pk}",
                field="id"
            )

        serializer = ApproachSerializer(approach)
        return Response(serializer.data)

    def create(self, request):
        """
        Create a new approach for a flight.

        POST /api/v1/approaches/
        """
        organization_id = self.get_organization_id()

        flight_id = request.data.get('flight_id')
        if not flight_id:
            raise FlightValidationError(
                message="flight_id is required",
                field="flight_id"
            )

        serializer = ApproachCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        approach = FlightService.add_approach(
            flight_id=UUID(flight_id),
            organization_id=organization_id,
            approach_data=serializer.validated_data
        )

        response_serializer = ApproachSerializer(approach)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, pk=None):
        """
        Update an approach.

        PUT /api/v1/approaches/{id}/
        """
        organization_id = self.get_organization_id()

        try:
            approach = Approach.objects.get(
                id=UUID(pk),
                organization_id=organization_id
            )
        except Approach.DoesNotExist:
            raise FlightValidationError(
                message=f"Approach not found: {pk}",
                field="id"
            )

        serializer = ApproachCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        for key, value in serializer.validated_data.items():
            setattr(approach, key, value)
        approach.save()

        response_serializer = ApproachSerializer(approach)
        return Response(response_serializer.data)

    def destroy(self, request, pk=None):
        """
        Delete an approach.

        DELETE /api/v1/approaches/{id}/
        """
        organization_id = self.get_organization_id()

        try:
            approach = Approach.objects.get(
                id=UUID(pk),
                organization_id=organization_id
            )
        except Approach.DoesNotExist:
            raise FlightValidationError(
                message=f"Approach not found: {pk}",
                field="id"
            )

        approach.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['post'])
    def bulk_create(self, request):
        """
        Create multiple approaches for a flight.

        POST /api/v1/approaches/bulk_create/
        """
        organization_id = self.get_organization_id()

        flight_id = request.data.get('flight_id')
        if not flight_id:
            raise FlightValidationError(
                message="flight_id is required",
                field="flight_id"
            )

        serializer = ApproachBulkCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        approaches = []
        for approach_data in serializer.validated_data['approaches']:
            approach = FlightService.add_approach(
                flight_id=UUID(flight_id),
                organization_id=organization_id,
                approach_data=approach_data
            )
            approaches.append(approach)

        response_serializer = ApproachSerializer(approaches, many=True)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """
        Get approach statistics.

        GET /api/v1/approaches/statistics/
        """
        organization_id = self.get_organization_id()
        user_id = self.get_optional_user_id()

        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        if start_date:
            from datetime import datetime
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        if end_date:
            from datetime import datetime
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()

        stats = Approach.get_approach_statistics(
            organization_id=organization_id,
            pilot_id=user_id,
            start_date=start_date,
            end_date=end_date
        )

        serializer = ApproachStatisticsSerializer(stats)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def by_flight(self, request):
        """
        Get approaches for a specific flight.

        GET /api/v1/approaches/by_flight/?flight_id={uuid}
        """
        organization_id = self.get_organization_id()

        flight_id = request.query_params.get('flight_id')
        if not flight_id:
            raise FlightValidationError(
                message="flight_id is required",
                field="flight_id"
            )

        approaches = Approach.objects.filter(
            flight_id=UUID(flight_id),
            organization_id=organization_id
        ).order_by('sequence_number')

        serializer = ApproachSerializer(approaches, many=True)
        return Response(serializer.data)


class HoldViewSet(BaseFlightViewSet, PaginationMixin):
    """
    ViewSet for holding pattern operations.
    """

    def list(self, request):
        """
        List holds with optional filters.

        GET /api/v1/holds/
        """
        organization_id = self.get_organization_id()
        page, page_size = self.get_pagination_params()

        queryset = Hold.objects.filter(organization_id=organization_id)

        # Apply filters
        flight_id = request.query_params.get('flight_id')
        if flight_id:
            queryset = queryset.filter(flight_id=UUID(flight_id))

        in_imc = request.query_params.get('in_imc')
        if in_imc is not None:
            queryset = queryset.filter(in_imc=in_imc.lower() == 'true')

        queryset = queryset.order_by('-executed_at', '-created_at')

        from django.core.paginator import Paginator
        paginator = Paginator(queryset, page_size)
        page_obj = paginator.get_page(page)

        serializer = HoldSerializer(page_obj.object_list, many=True)
        return Response({
            'results': serializer.data,
            'total': paginator.count,
            'page': page,
            'page_size': page_size,
            'total_pages': paginator.num_pages,
        })

    def retrieve(self, request, pk=None):
        """
        Retrieve a single hold.

        GET /api/v1/holds/{id}/
        """
        organization_id = self.get_organization_id()

        try:
            hold = Hold.objects.get(
                id=UUID(pk),
                organization_id=organization_id
            )
        except Hold.DoesNotExist:
            raise FlightValidationError(
                message=f"Hold not found: {pk}",
                field="id"
            )

        serializer = HoldSerializer(hold)
        return Response(serializer.data)

    def create(self, request):
        """
        Create a new hold for a flight.

        POST /api/v1/holds/
        """
        organization_id = self.get_organization_id()

        flight_id = request.data.get('flight_id')
        if not flight_id:
            raise FlightValidationError(
                message="flight_id is required",
                field="flight_id"
            )

        serializer = HoldCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        hold = FlightService.add_hold(
            flight_id=UUID(flight_id),
            organization_id=organization_id,
            hold_data=serializer.validated_data
        )

        response_serializer = HoldSerializer(hold)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, pk=None):
        """
        Update a hold.

        PUT /api/v1/holds/{id}/
        """
        organization_id = self.get_organization_id()

        try:
            hold = Hold.objects.get(
                id=UUID(pk),
                organization_id=organization_id
            )
        except Hold.DoesNotExist:
            raise FlightValidationError(
                message=f"Hold not found: {pk}",
                field="id"
            )

        serializer = HoldCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        for key, value in serializer.validated_data.items():
            setattr(hold, key, value)
        hold.save()

        response_serializer = HoldSerializer(hold)
        return Response(response_serializer.data)

    def destroy(self, request, pk=None):
        """
        Delete a hold.

        DELETE /api/v1/holds/{id}/
        """
        organization_id = self.get_organization_id()

        try:
            hold = Hold.objects.get(
                id=UUID(pk),
                organization_id=organization_id
            )
        except Hold.DoesNotExist:
            raise FlightValidationError(
                message=f"Hold not found: {pk}",
                field="id"
            )

        hold.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'])
    def by_flight(self, request):
        """
        Get holds for a specific flight.

        GET /api/v1/holds/by_flight/?flight_id={uuid}
        """
        organization_id = self.get_organization_id()

        flight_id = request.query_params.get('flight_id')
        if not flight_id:
            raise FlightValidationError(
                message="flight_id is required",
                field="flight_id"
            )

        holds = Hold.objects.filter(
            flight_id=UUID(flight_id),
            organization_id=organization_id
        ).order_by('executed_at')

        serializer = HoldSerializer(holds, many=True)
        return Response(serializer.data)
