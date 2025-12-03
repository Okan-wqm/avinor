# services/booking-service/src/apps/api/views/availability_views.py
"""
Availability API Views

Views for managing resource availability and operating hours.
"""

import logging
from datetime import datetime, date, timedelta

from django.utils import timezone
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend

from apps.core.models import Availability
from apps.core.models.availability import OperatingHours
from apps.core.services import AvailabilityService, AvailabilityError
from apps.api.serializers import (
    AvailabilitySerializer,
    AvailabilityListSerializer,
    AvailabilityDetailSerializer,
    AvailabilityCreateSerializer,
    AvailabilityUpdateSerializer,
    OperatingHoursSerializer,
    OperatingHoursCreateSerializer,
    AvailableSlotSerializer,
    AvailableSlotsRequestSerializer,
    ResourceScheduleSerializer,
    ResourceAvailabilityCheckSerializer,
    ResourceAvailabilityResultSerializer,
)
from .pagination import StandardResultsSetPagination

logger = logging.getLogger(__name__)


class AvailabilityViewSet(viewsets.ModelViewSet):
    """
    ViewSet for availability management.

    Manages resource availability blocks (available, unavailable, limited).
    """

    queryset = Availability.objects.all()
    serializer_class = AvailabilitySerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['resource_type', 'resource_id', 'availability_type']
    ordering_fields = ['start_datetime', 'created_at']
    ordering = ['start_datetime']

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.availability_service = AvailabilityService()

    def get_queryset(self):
        """Filter queryset by organization and date range."""
        queryset = super().get_queryset()
        organization_id = self.request.headers.get('X-Organization-ID')

        if organization_id:
            queryset = queryset.filter(organization_id=organization_id)

        # Date range filter
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')

        if start_date:
            try:
                start_dt = datetime.strptime(start_date, '%Y-%m-%d')
                queryset = queryset.filter(end_datetime__gte=start_dt)
            except ValueError:
                pass

        if end_date:
            try:
                end_dt = datetime.strptime(end_date, '%Y-%m-%d')
                queryset = queryset.filter(start_datetime__lte=end_dt)
            except ValueError:
                pass

        return queryset

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return AvailabilityListSerializer
        elif self.action == 'retrieve':
            return AvailabilityDetailSerializer
        elif self.action == 'create':
            return AvailabilityCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return AvailabilityUpdateSerializer
        return AvailabilitySerializer

    def create(self, request, *args, **kwargs):
        """Create a new availability entry."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        notify_affected = data.pop('notify_affected', True)

        try:
            availability = self.availability_service.create_availability(
                created_by=request.user.id if hasattr(request, 'user') else None,
                **data
            )

            # TODO: Send notifications if notify_affected and type is unavailable

            output_serializer = AvailabilityDetailSerializer(availability)
            return Response(
                output_serializer.data,
                status=status.HTTP_201_CREATED
            )

        except AvailabilityError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['get'])
    def for_resource(self, request):
        """Get availability for a specific resource."""
        organization_id = request.headers.get('X-Organization-ID')
        resource_type = request.query_params.get('resource_type')
        resource_id = request.query_params.get('resource_id')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        if not all([organization_id, resource_type, resource_id]):
            return Response(
                {'error': 'organization_id, resource_type, and resource_id are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            start = datetime.strptime(start_date, '%Y-%m-%d').date() if start_date else timezone.now().date()
            end = datetime.strptime(end_date, '%Y-%m-%d').date() if end_date else start + timedelta(days=30)
        except ValueError:
            return Response(
                {'error': 'Invalid date format. Use YYYY-MM-DD'},
                status=status.HTTP_400_BAD_REQUEST
            )

        availability = self.availability_service.list_availability(
            organization_id=organization_id,
            resource_type=resource_type,
            resource_id=resource_id,
            start_date=start,
            end_date=end
        )

        serializer = AvailabilityListSerializer(availability, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def check(self, request):
        """Check if a resource is available."""
        serializer = ResourceAvailabilityCheckSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        organization_id = request.headers.get('X-Organization-ID')

        result = self.availability_service.is_resource_available(
            organization_id=organization_id,
            resource_type=data['resource_type'],
            resource_id=data['resource_id'],
            start=data['start'],
            end=data['end'],
            booking_type=data.get('booking_type')
        )

        output_serializer = ResourceAvailabilityResultSerializer(result)
        return Response(output_serializer.data)

    @action(detail=False, methods=['post'])
    def bulk_create(self, request):
        """Create multiple availability entries at once."""
        entries = request.data.get('entries', [])

        if not entries:
            return Response(
                {'error': 'No entries provided'},
                status=status.HTTP_400_BAD_REQUEST
            )

        created = []
        errors = []

        for i, entry_data in enumerate(entries):
            serializer = AvailabilityCreateSerializer(data=entry_data)
            if serializer.is_valid():
                try:
                    data = serializer.validated_data
                    data.pop('notify_affected', None)

                    availability = self.availability_service.create_availability(
                        created_by=request.user.id if hasattr(request, 'user') else None,
                        **data
                    )
                    created.append(str(availability.id))
                except Exception as e:
                    errors.append({'index': i, 'error': str(e)})
            else:
                errors.append({'index': i, 'errors': serializer.errors})

        return Response({
            'created_count': len(created),
            'created_ids': created,
            'errors': errors,
        }, status=status.HTTP_201_CREATED if created else status.HTTP_400_BAD_REQUEST)


class OperatingHoursViewSet(viewsets.ModelViewSet):
    """
    ViewSet for operating hours management.

    Manages location operating schedules.
    """

    queryset = OperatingHours.objects.all()
    serializer_class = OperatingHoursSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['location_id', 'day_of_week', 'is_active']

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.availability_service = AvailabilityService()

    def get_queryset(self):
        """Filter queryset by organization."""
        queryset = super().get_queryset()
        organization_id = self.request.headers.get('X-Organization-ID')

        if organization_id:
            queryset = queryset.filter(organization_id=organization_id)

        return queryset

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action in ['create', 'update', 'partial_update']:
            return OperatingHoursCreateSerializer
        return OperatingHoursSerializer

    @action(detail=False, methods=['get'])
    def weekly_schedule(self, request):
        """Get weekly operating schedule for a location."""
        organization_id = request.headers.get('X-Organization-ID')
        location_id = request.query_params.get('location_id')

        if not location_id:
            return Response(
                {'error': 'location_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        schedule = self.availability_service.get_weekly_schedule(
            organization_id=organization_id,
            location_id=location_id
        )

        return Response(schedule)

    @action(detail=False, methods=['post'])
    def set_weekly(self, request):
        """Set operating hours for entire week."""
        organization_id = request.headers.get('X-Organization-ID')
        location_id = request.data.get('location_id')
        schedule = request.data.get('schedule', {})

        if not location_id:
            return Response(
                {'error': 'location_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        day_map = {
            'sunday': 0, 'monday': 1, 'tuesday': 2, 'wednesday': 3,
            'thursday': 4, 'friday': 5, 'saturday': 6
        }

        created_or_updated = []
        for day_name, times in schedule.items():
            if day_name.lower() not in day_map:
                continue

            day_of_week = day_map[day_name.lower()]

            if times.get('is_open', True) and times.get('open') and times.get('close'):
                try:
                    open_time = datetime.strptime(times['open'], '%H:%M').time()
                    close_time = datetime.strptime(times['close'], '%H:%M').time()

                    operating_hours = self.availability_service.set_operating_hours(
                        organization_id=organization_id,
                        location_id=location_id,
                        day_of_week=day_of_week,
                        open_time=open_time,
                        close_time=close_time
                    )
                    created_or_updated.append(day_name)
                except ValueError as e:
                    logger.warning(f"Invalid time format for {day_name}: {e}")
            else:
                # Mark as closed
                OperatingHours.objects.filter(
                    organization_id=organization_id,
                    location_id=location_id,
                    day_of_week=day_of_week
                ).update(is_active=False)

        return Response({
            'success': True,
            'days_updated': created_or_updated,
        })


class AvailableSlotsView(APIView):
    """View for finding available booking slots."""

    permission_classes = [IsAuthenticated]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.availability_service = AvailabilityService()

    def get(self, request):
        """Get available slots for a given date and duration."""
        organization_id = request.headers.get('X-Organization-ID')
        target_date_str = request.query_params.get('date')
        duration = request.query_params.get('duration', 60)
        aircraft_id = request.query_params.get('aircraft_id')
        instructor_id = request.query_params.get('instructor_id')
        location_id = request.query_params.get('location_id')
        slot_interval = request.query_params.get('interval', 30)

        if not organization_id:
            return Response(
                {'error': 'Organization ID required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            target_date = datetime.strptime(target_date_str, '%Y-%m-%d').date() if target_date_str else timezone.now().date()
        except ValueError:
            return Response(
                {'error': 'Invalid date format. Use YYYY-MM-DD'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            duration_minutes = int(duration)
            slot_interval_minutes = int(slot_interval)
        except ValueError:
            return Response(
                {'error': 'Invalid duration or interval'},
                status=status.HTTP_400_BAD_REQUEST
            )

        slots = self.availability_service.get_available_slots(
            organization_id=organization_id,
            target_date=target_date,
            duration_minutes=duration_minutes,
            aircraft_id=aircraft_id,
            instructor_id=instructor_id,
            location_id=location_id,
            slot_interval=slot_interval_minutes
        )

        return Response({
            'date': target_date.isoformat(),
            'duration_minutes': duration_minutes,
            'slot_count': len(slots),
            'slots': slots,
        })

    def post(self, request):
        """Find available slots with detailed criteria."""
        serializer = AvailableSlotsRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        organization_id = request.headers.get('X-Organization-ID')

        slots = self.availability_service.get_available_slots(
            organization_id=organization_id,
            target_date=data['target_date'],
            duration_minutes=data['duration_minutes'],
            aircraft_id=data.get('aircraft_id'),
            instructor_id=data.get('instructor_id'),
            location_id=data.get('location_id'),
            slot_interval=data.get('slot_interval', 30)
        )

        return Response({
            'date': data['target_date'].isoformat(),
            'duration_minutes': data['duration_minutes'],
            'slot_count': len(slots),
            'slots': slots,
        })


class ResourceScheduleView(APIView):
    """View for getting resource schedules."""

    permission_classes = [IsAuthenticated]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.availability_service = AvailabilityService()

    def get(self, request):
        """Get schedule for a specific resource on a date."""
        organization_id = request.headers.get('X-Organization-ID')
        resource_type = request.query_params.get('resource_type')
        resource_id = request.query_params.get('resource_id')
        target_date_str = request.query_params.get('date')

        if not all([organization_id, resource_type, resource_id]):
            return Response(
                {'error': 'organization_id, resource_type, and resource_id are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            target_date = datetime.strptime(target_date_str, '%Y-%m-%d').date() if target_date_str else timezone.now().date()
        except ValueError:
            return Response(
                {'error': 'Invalid date format. Use YYYY-MM-DD'},
                status=status.HTTP_400_BAD_REQUEST
            )

        schedule = self.availability_service.get_resource_schedule(
            organization_id=organization_id,
            resource_type=resource_type,
            resource_id=resource_id,
            target_date=target_date
        )

        serializer = ResourceScheduleSerializer(schedule)
        return Response(serializer.data)

    def post(self, request):
        """Get schedules for multiple resources."""
        organization_id = request.headers.get('X-Organization-ID')
        resources = request.data.get('resources', [])
        target_date_str = request.data.get('date')

        if not resources:
            return Response(
                {'error': 'resources list is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            target_date = datetime.strptime(target_date_str, '%Y-%m-%d').date() if target_date_str else timezone.now().date()
        except ValueError:
            return Response(
                {'error': 'Invalid date format. Use YYYY-MM-DD'},
                status=status.HTTP_400_BAD_REQUEST
            )

        schedules = []
        for resource in resources:
            schedule = self.availability_service.get_resource_schedule(
                organization_id=organization_id,
                resource_type=resource.get('type'),
                resource_id=resource.get('id'),
                target_date=target_date
            )
            schedules.append(schedule)

        return Response({
            'date': target_date.isoformat(),
            'schedules': schedules,
        })
