# services/organization-service/src/apps/core/views/location.py
"""
Location ViewSet

REST API endpoints for location management.
"""

import logging
from typing import Any

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction

from apps.core.models import Location
from apps.core.serializers import (
    LocationSerializer,
    LocationListSerializer,
    LocationCreateSerializer,
    LocationUpdateSerializer,
    LocationOperatingHoursSerializer,
    LocationWeatherSerializer,
)
from apps.core.services import (
    LocationService,
    LocationError,
)

logger = logging.getLogger(__name__)


class LocationViewSet(viewsets.ViewSet):
    """
    ViewSet for Location CRUD and management operations.

    Endpoints:
    - GET /organizations/{org_id}/locations/ - List locations
    - POST /organizations/{org_id}/locations/ - Create location
    - GET /organizations/{org_id}/locations/{id}/ - Get location details
    - PUT /organizations/{org_id}/locations/{id}/ - Update location
    - DELETE /organizations/{org_id}/locations/{id}/ - Soft delete location
    - PUT /organizations/{org_id}/locations/{id}/primary/ - Set as primary
    - PUT /organizations/{org_id}/locations/{id}/operating-hours/ - Update hours
    - GET /organizations/{org_id}/locations/{id}/weather/ - Get weather
    - PUT /organizations/{org_id}/locations/{id}/facilities/ - Update facilities
    - PUT /organizations/{org_id}/locations/{id}/runways/ - Update runways
    - PUT /organizations/{org_id}/locations/{id}/frequencies/ - Update frequencies
    - POST /organizations/{org_id}/locations/reorder/ - Reorder locations
    """

    permission_classes = [IsAuthenticated]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.location_service = LocationService()

    def list(self, request: Request, organization_pk: str = None) -> Response:
        """List all locations for organization."""
        queryset = Location.objects.filter(
            organization_id=organization_pk,
            deleted_at__isnull=True
        ).order_by('display_order', 'name')

        # Filter by type
        location_type = request.query_params.get('location_type')
        if location_type:
            queryset = queryset.filter(location_type=location_type)

        # Filter by active status
        is_active = request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')

        # Filter by primary
        is_primary = request.query_params.get('is_primary')
        if is_primary is not None:
            queryset = queryset.filter(is_primary=is_primary.lower() == 'true')

        # Search by name or ICAO
        search = request.query_params.get('search')
        if search:
            from django.db.models import Q
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(airport_icao__icontains=search) |
                Q(city__icontains=search)
            )

        serializer = LocationListSerializer(queryset, many=True)
        return Response({
            'status': 'success',
            'data': serializer.data,
            'count': queryset.count(),
        })

    def create(self, request: Request, organization_pk: str = None) -> Response:
        """Create a new location."""
        serializer = LocationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            with transaction.atomic():
                location = self.location_service.create_location(
                    organization_id=organization_pk,
                    created_by_user_id=request.user.id,
                    **serializer.validated_data
                )

            output_serializer = LocationSerializer(location)
            return Response({
                'status': 'success',
                'message': 'Location created successfully',
                'data': output_serializer.data,
            }, status=status.HTTP_201_CREATED)

        except LocationError as e:
            logger.warning(f"Location creation failed: {e}")
            return Response({
                'status': 'error',
                'message': str(e),
                'code': 'LOCATION_ERROR',
            }, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request: Request, organization_pk: str = None, pk: str = None) -> Response:
        """Get location details."""
        try:
            location = self.location_service.get_location(pk, organization_pk)
            if not location:
                return Response({
                    'status': 'error',
                    'message': 'Location not found',
                    'code': 'NOT_FOUND',
                }, status=status.HTTP_404_NOT_FOUND)

            serializer = LocationSerializer(location)
            return Response({
                'status': 'success',
                'data': serializer.data,
            })

        except LocationError as e:
            return Response({
                'status': 'error',
                'message': str(e),
                'code': 'LOCATION_ERROR',
            }, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request: Request, organization_pk: str = None, pk: str = None) -> Response:
        """Update location."""
        serializer = LocationUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            with transaction.atomic():
                location = self.location_service.update_location(
                    location_id=pk,
                    organization_id=organization_pk,
                    updated_by_user_id=request.user.id,
                    **serializer.validated_data
                )

            output_serializer = LocationSerializer(location)
            return Response({
                'status': 'success',
                'message': 'Location updated successfully',
                'data': output_serializer.data,
            })

        except LocationError as e:
            logger.warning(f"Location update failed: {e}")
            return Response({
                'status': 'error',
                'message': str(e),
                'code': 'LOCATION_ERROR',
            }, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request: Request, organization_pk: str = None, pk: str = None) -> Response:
        """Soft delete location."""
        try:
            with transaction.atomic():
                self.location_service.delete_location(
                    location_id=pk,
                    organization_id=organization_pk,
                    deleted_by_user_id=request.user.id
                )

            return Response({
                'status': 'success',
                'message': 'Location deleted successfully',
            })

        except LocationError as e:
            logger.warning(f"Location deletion failed: {e}")
            return Response({
                'status': 'error',
                'message': str(e),
                'code': 'LOCATION_ERROR',
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['put'], url_path='primary')
    def set_primary(self, request: Request, organization_pk: str = None, pk: str = None) -> Response:
        """Set location as primary."""
        try:
            with transaction.atomic():
                location = self.location_service.set_primary_location(
                    location_id=pk,
                    organization_id=organization_pk
                )

            serializer = LocationSerializer(location)
            return Response({
                'status': 'success',
                'message': 'Primary location updated',
                'data': serializer.data,
            })

        except LocationError as e:
            return Response({
                'status': 'error',
                'message': str(e),
                'code': 'LOCATION_ERROR',
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['put'], url_path='operating-hours')
    def update_operating_hours(
        self, request: Request, organization_pk: str = None, pk: str = None
    ) -> Response:
        """Update location operating hours."""
        serializer = LocationOperatingHoursSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            with transaction.atomic():
                location = self.location_service.update_operating_hours(
                    location_id=pk,
                    organization_id=organization_pk,
                    operating_hours=serializer.validated_data
                )

            output_serializer = LocationSerializer(location)
            return Response({
                'status': 'success',
                'message': 'Operating hours updated',
                'data': output_serializer.data,
            })

        except LocationError as e:
            return Response({
                'status': 'error',
                'message': str(e),
                'code': 'LOCATION_ERROR',
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'], url_path='weather')
    def get_weather(self, request: Request, organization_pk: str = None, pk: str = None) -> Response:
        """Get weather information for location."""
        try:
            weather = self.location_service.get_weather(
                location_id=pk,
                organization_id=organization_pk
            )

            if not weather:
                return Response({
                    'status': 'error',
                    'message': 'Weather information not available',
                    'code': 'NOT_AVAILABLE',
                }, status=status.HTTP_404_NOT_FOUND)

            serializer = LocationWeatherSerializer(data=weather)
            serializer.is_valid()

            return Response({
                'status': 'success',
                'data': weather,
            })

        except LocationError as e:
            return Response({
                'status': 'error',
                'message': str(e),
                'code': 'LOCATION_ERROR',
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['put'], url_path='facilities')
    def update_facilities(
        self, request: Request, organization_pk: str = None, pk: str = None
    ) -> Response:
        """Update location facilities."""
        facilities = request.data.get('facilities', [])
        if not isinstance(facilities, list):
            return Response({
                'status': 'error',
                'message': 'Facilities must be a list',
                'code': 'VALIDATION_ERROR',
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                location = self.location_service.update_facilities(
                    location_id=pk,
                    organization_id=organization_pk,
                    facilities=facilities
                )

            serializer = LocationSerializer(location)
            return Response({
                'status': 'success',
                'message': 'Facilities updated',
                'data': serializer.data,
            })

        except LocationError as e:
            return Response({
                'status': 'error',
                'message': str(e),
                'code': 'LOCATION_ERROR',
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['put'], url_path='runways')
    def update_runways(
        self, request: Request, organization_pk: str = None, pk: str = None
    ) -> Response:
        """Update location runways."""
        runways = request.data.get('runways', [])
        if not isinstance(runways, list):
            return Response({
                'status': 'error',
                'message': 'Runways must be a list',
                'code': 'VALIDATION_ERROR',
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                location = self.location_service.update_runways(
                    location_id=pk,
                    organization_id=organization_pk,
                    runways=runways
                )

            serializer = LocationSerializer(location)
            return Response({
                'status': 'success',
                'message': 'Runways updated',
                'data': serializer.data,
            })

        except LocationError as e:
            return Response({
                'status': 'error',
                'message': str(e),
                'code': 'LOCATION_ERROR',
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['put'], url_path='frequencies')
    def update_frequencies(
        self, request: Request, organization_pk: str = None, pk: str = None
    ) -> Response:
        """Update location radio frequencies."""
        frequencies = request.data.get('frequencies', [])
        if not isinstance(frequencies, list):
            return Response({
                'status': 'error',
                'message': 'Frequencies must be a list',
                'code': 'VALIDATION_ERROR',
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                location = self.location_service.update_frequencies(
                    location_id=pk,
                    organization_id=organization_pk,
                    frequencies=frequencies
                )

            serializer = LocationSerializer(location)
            return Response({
                'status': 'success',
                'message': 'Frequencies updated',
                'data': serializer.data,
            })

        except LocationError as e:
            return Response({
                'status': 'error',
                'message': str(e),
                'code': 'LOCATION_ERROR',
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], url_path='reorder')
    def reorder(self, request: Request, organization_pk: str = None) -> Response:
        """Reorder locations display order."""
        order_data = request.data.get('order', [])
        if not order_data:
            return Response({
                'status': 'error',
                'message': 'Order data is required',
                'code': 'VALIDATION_ERROR',
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                self.location_service.reorder_locations(
                    organization_id=organization_pk,
                    order=order_data
                )

            return Response({
                'status': 'success',
                'message': 'Locations reordered successfully',
            })

        except LocationError as e:
            return Response({
                'status': 'error',
                'message': str(e),
                'code': 'LOCATION_ERROR',
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='activate')
    def activate(self, request: Request, organization_pk: str = None, pk: str = None) -> Response:
        """Activate a location."""
        try:
            location = Location.objects.get(
                id=pk,
                organization_id=organization_pk,
                deleted_at__isnull=True
            )
            location.is_active = True
            location.save(update_fields=['is_active', 'updated_at'])

            serializer = LocationSerializer(location)
            return Response({
                'status': 'success',
                'message': 'Location activated',
                'data': serializer.data,
            })

        except Location.DoesNotExist:
            return Response({
                'status': 'error',
                'message': 'Location not found',
                'code': 'NOT_FOUND',
            }, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['post'], url_path='deactivate')
    def deactivate(self, request: Request, organization_pk: str = None, pk: str = None) -> Response:
        """Deactivate a location."""
        try:
            location = Location.objects.get(
                id=pk,
                organization_id=organization_pk,
                deleted_at__isnull=True
            )
            location.is_active = False
            location.save(update_fields=['is_active', 'updated_at'])

            serializer = LocationSerializer(location)
            return Response({
                'status': 'success',
                'message': 'Location deactivated',
                'data': serializer.data,
            })

        except Location.DoesNotExist:
            return Response({
                'status': 'error',
                'message': 'Location not found',
                'code': 'NOT_FOUND',
            }, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['get'], url_path='is-open')
    def is_open(self, request: Request, organization_pk: str = None, pk: str = None) -> Response:
        """Check if location is currently open."""
        try:
            result = self.location_service.is_location_open(
                location_id=pk,
                organization_id=organization_pk
            )

            return Response({
                'status': 'success',
                'data': result,
            })

        except LocationError as e:
            return Response({
                'status': 'error',
                'message': str(e),
                'code': 'LOCATION_ERROR',
            }, status=status.HTTP_400_BAD_REQUEST)
