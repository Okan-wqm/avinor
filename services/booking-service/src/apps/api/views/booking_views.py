# services/booking-service/src/apps/api/views/booking_views.py
"""
Booking API Views

Comprehensive views for booking management.
"""

import logging
from datetime import datetime, date, timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend

from apps.core.models import Booking
from apps.core.services import (
    BookingService,
    BookingNotFoundError,
    BookingConflictError,
    BookingValidationError,
    BookingStateError,
    RuleViolationError,
)
from apps.api.serializers import (
    BookingSerializer,
    BookingListSerializer,
    BookingDetailSerializer,
    BookingCreateSerializer,
    BookingUpdateSerializer,
    BookingCancelSerializer,
    BookingCheckInSerializer,
    BookingDispatchSerializer,
    BookingCompleteSerializer,
    BookingConflictSerializer,
    BookingCostEstimateSerializer,
    BookingCostEstimateResultSerializer,
)
from .filters import BookingFilter
from .pagination import StandardResultsSetPagination

logger = logging.getLogger(__name__)


class BookingViewSet(viewsets.ModelViewSet):
    """
    ViewSet for booking management.

    Provides CRUD operations and workflow actions for bookings.
    """

    queryset = Booking.objects.all()
    serializer_class = BookingSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = BookingFilter
    search_fields = ['booking_number', 'route', 'remarks']
    ordering_fields = ['scheduled_start', 'created_at', 'booking_number', 'status']
    ordering = ['-scheduled_start']

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.booking_service = BookingService()

    def get_queryset(self):
        """Filter queryset by organization."""
        queryset = super().get_queryset()
        organization_id = self.request.headers.get('X-Organization-ID')

        if organization_id:
            queryset = queryset.filter(organization_id=organization_id)

        return queryset

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return BookingListSerializer
        elif self.action == 'retrieve':
            return BookingDetailSerializer
        elif self.action == 'create':
            return BookingCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return BookingUpdateSerializer
        return BookingSerializer

    def create(self, request, *args, **kwargs):
        """Create a new booking."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        validate_only = data.pop('validate_only', False)
        skip_conflict_check = data.pop('skip_conflict_check', False)
        skip_rule_check = data.pop('skip_rule_check', False)

        try:
            booking = self.booking_service.create_booking(
                created_by=request.user.id if hasattr(request, 'user') else None,
                validate_only=validate_only,
                skip_conflict_check=skip_conflict_check,
                skip_rule_check=skip_rule_check,
                **data
            )

            if validate_only:
                return Response({
                    'valid': True,
                    'message': 'Booking validation successful'
                }, status=status.HTTP_200_OK)

            output_serializer = BookingDetailSerializer(booking)
            return Response(
                output_serializer.data,
                status=status.HTTP_201_CREATED
            )

        except BookingConflictError as e:
            return Response({
                'error': 'conflict',
                'message': str(e),
                'conflicts': getattr(e, 'conflicts', [])
            }, status=status.HTTP_409_CONFLICT)

        except BookingValidationError as e:
            return Response({
                'error': 'validation',
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

        except RuleViolationError as e:
            return Response({
                'error': 'rule_violation',
                'message': str(e),
                'rule': getattr(e, 'rule', None)
            }, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        """Update a booking."""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()

        serializer = self.get_serializer(
            instance, data=request.data, partial=partial
        )
        serializer.is_valid(raise_exception=True)

        try:
            booking = self.booking_service.update_booking(
                booking_id=instance.id,
                **serializer.validated_data
            )

            output_serializer = BookingDetailSerializer(booking)
            return Response(output_serializer.data)

        except BookingStateError as e:
            return Response({
                'error': 'state_error',
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

        except BookingConflictError as e:
            return Response({
                'error': 'conflict',
                'message': str(e)
            }, status=status.HTTP_409_CONFLICT)

    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        """Confirm a booking."""
        try:
            booking = self.booking_service.confirm_booking(pk)
            serializer = BookingDetailSerializer(booking)
            return Response(serializer.data)
        except BookingNotFoundError:
            return Response(
                {'error': 'Booking not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except BookingStateError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def check_in(self, request, pk=None):
        """Check in for a booking."""
        serializer = BookingCheckInSerializer(
            data=request.data,
            context={'booking': self.get_object()}
        )
        serializer.is_valid(raise_exception=True)

        try:
            booking = self.booking_service.check_in(
                booking_id=pk,
                **serializer.validated_data
            )
            output_serializer = BookingDetailSerializer(booking)
            return Response(output_serializer.data)

        except BookingStateError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def dispatch(self, request, pk=None):
        """Dispatch aircraft for booking."""
        serializer = BookingDispatchSerializer(
            data=request.data,
            context={'booking': self.get_object()}
        )
        serializer.is_valid(raise_exception=True)

        try:
            booking = self.booking_service.dispatch(
                booking_id=pk,
                **serializer.validated_data
            )
            output_serializer = BookingDetailSerializer(booking)
            return Response(output_serializer.data)

        except BookingStateError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """Start the flight/booking."""
        notes = request.data.get('notes')

        try:
            booking = self.booking_service.start_booking(
                booking_id=pk,
                notes=notes
            )
            serializer = BookingDetailSerializer(booking)
            return Response(serializer.data)

        except BookingStateError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Complete a booking."""
        serializer = BookingCompleteSerializer(
            data=request.data,
            context={'booking': self.get_object()}
        )
        serializer.is_valid(raise_exception=True)

        try:
            booking = self.booking_service.complete_booking(
                booking_id=pk,
                **serializer.validated_data
            )
            output_serializer = BookingDetailSerializer(booking)
            return Response(output_serializer.data)

        except BookingStateError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel a booking."""
        serializer = BookingCancelSerializer(
            data=request.data,
            context={'booking': self.get_object()}
        )
        serializer.is_valid(raise_exception=True)

        try:
            data = serializer.validated_data
            booking = self.booking_service.cancel_booking(
                booking_id=pk,
                cancelled_by=request.user.id if hasattr(request, 'user') else None,
                cancellation_type=data.get('cancellation_type'),
                reason=data.get('reason'),
                waive_fee=data.get('waive_fee', False)
            )
            output_serializer = BookingDetailSerializer(booking)
            return Response(output_serializer.data)

        except BookingStateError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def no_show(self, request, pk=None):
        """Mark booking as no-show."""
        notes = request.data.get('notes')

        try:
            booking = self.booking_service.mark_no_show(
                booking_id=pk,
                marked_by=request.user.id if hasattr(request, 'user') else None,
                notes=notes
            )
            serializer = BookingDetailSerializer(booking)
            return Response(serializer.data)

        except BookingStateError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['get'])
    def my_bookings(self, request):
        """Get current user's bookings."""
        user_id = request.headers.get('X-User-ID')
        organization_id = request.headers.get('X-Organization-ID')

        if not user_id:
            return Response(
                {'error': 'User ID required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        bookings = self.booking_service.get_user_bookings(
            organization_id=organization_id,
            user_id=user_id,
            include_past=request.query_params.get('include_past', 'false').lower() == 'true'
        )

        serializer = BookingListSerializer(bookings, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def upcoming(self, request):
        """Get upcoming bookings."""
        organization_id = request.headers.get('X-Organization-ID')
        days = int(request.query_params.get('days', 7))

        start_date = timezone.now().date()
        end_date = start_date + timedelta(days=days)

        queryset = self.get_queryset().filter(
            scheduled_start__date__gte=start_date,
            scheduled_start__date__lte=end_date
        ).exclude(
            status__in=[Booking.Status.CANCELLED, Booking.Status.COMPLETED]
        ).order_by('scheduled_start')

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = BookingListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = BookingListSerializer(queryset, many=True)
        return Response(serializer.data)


class BookingCalendarView(APIView):
    """View for calendar data."""

    permission_classes = [IsAuthenticated]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.booking_service = BookingService()

    def get(self, request):
        """Get calendar view of bookings."""
        organization_id = request.headers.get('X-Organization-ID')
        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')
        aircraft_id = request.query_params.get('aircraft_id')
        instructor_id = request.query_params.get('instructor_id')
        location_id = request.query_params.get('location_id')

        if not organization_id:
            return Response(
                {'error': 'Organization ID required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date() if start_date_str else timezone.now().date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else start_date + timedelta(days=7)
        except ValueError:
            return Response(
                {'error': 'Invalid date format. Use YYYY-MM-DD'},
                status=status.HTTP_400_BAD_REQUEST
            )

        calendar_data = self.booking_service.get_calendar(
            organization_id=organization_id,
            start_date=start_date,
            end_date=end_date,
            aircraft_id=aircraft_id,
            instructor_id=instructor_id,
            location_id=location_id
        )

        return Response(calendar_data)


class BookingConflictCheckView(APIView):
    """View for checking booking conflicts."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Check for conflicts with proposed booking."""
        organization_id = request.data.get('organization_id') or request.headers.get('X-Organization-ID')
        scheduled_start = request.data.get('scheduled_start')
        scheduled_end = request.data.get('scheduled_end')
        aircraft_id = request.data.get('aircraft_id')
        instructor_id = request.data.get('instructor_id')
        student_id = request.data.get('student_id')
        exclude_booking_id = request.data.get('exclude_booking_id')

        if not all([organization_id, scheduled_start, scheduled_end]):
            return Response(
                {'error': 'organization_id, scheduled_start, and scheduled_end are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            start_dt = datetime.fromisoformat(scheduled_start.replace('Z', '+00:00'))
            end_dt = datetime.fromisoformat(scheduled_end.replace('Z', '+00:00'))
        except (ValueError, TypeError):
            return Response(
                {'error': 'Invalid datetime format'},
                status=status.HTTP_400_BAD_REQUEST
            )

        conflicts = Booking.get_conflicts(
            organization_id=organization_id,
            start=start_dt,
            end=end_dt,
            aircraft_id=aircraft_id,
            instructor_id=instructor_id,
            student_id=student_id,
            exclude_booking_id=exclude_booking_id
        )

        result = {
            'has_conflicts': len(conflicts) > 0,
            'conflicts': [
                {
                    'id': str(c.id),
                    'booking_number': c.booking_number,
                    'scheduled_start': c.scheduled_start.isoformat(),
                    'scheduled_end': c.scheduled_end.isoformat(),
                    'block_start': c.block_start.isoformat(),
                    'block_end': c.block_end.isoformat(),
                    'aircraft_id': str(c.aircraft_id) if c.aircraft_id else None,
                    'instructor_id': str(c.instructor_id) if c.instructor_id else None,
                    'student_id': str(c.student_id) if c.student_id else None,
                    'status': c.status,
                }
                for c in conflicts
            ]
        }

        serializer = BookingConflictSerializer(result)
        return Response(serializer.data)


class BookingCostEstimateView(APIView):
    """View for estimating booking costs."""

    permission_classes = [IsAuthenticated]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.booking_service = BookingService()

    def post(self, request):
        """Calculate estimated cost for a booking."""
        serializer = BookingCostEstimateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data

        estimate = self.booking_service.estimate_cost(
            organization_id=data['organization_id'],
            aircraft_id=data.get('aircraft_id'),
            duration_minutes=data['duration_minutes'],
            booking_type=data['booking_type'],
            include_instructor=data.get('include_instructor', False)
        )

        result_serializer = BookingCostEstimateResultSerializer(estimate)
        return Response(result_serializer.data)
