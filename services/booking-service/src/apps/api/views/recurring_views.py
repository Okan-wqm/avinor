# services/booking-service/src/apps/api/views/recurring_views.py
"""
Recurring Pattern API Views

Views for managing recurring booking patterns.
"""

import logging
from datetime import datetime, date

from django.db import transaction
from django.utils import timezone
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend

from apps.core.models import RecurringPattern, Booking
from apps.core.services import BookingService
from apps.api.serializers import (
    RecurringPatternSerializer,
    RecurringPatternListSerializer,
    RecurringPatternDetailSerializer,
    RecurringPatternCreateSerializer,
    RecurringPatternUpdateSerializer,
    RecurringPatternOccurrenceSerializer,
)
from .pagination import StandardResultsSetPagination

logger = logging.getLogger(__name__)


class RecurringPatternViewSet(viewsets.ModelViewSet):
    """
    ViewSet for recurring pattern management.

    Manages recurring booking patterns and their occurrences.
    """

    queryset = RecurringPattern.objects.all()
    serializer_class = RecurringPatternSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'frequency', 'aircraft_id', 'instructor_id', 'student_id']
    search_fields = ['name', 'description']
    ordering_fields = ['start_date', 'created_at', 'name']
    ordering = ['-start_date']

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
            return RecurringPatternListSerializer
        elif self.action == 'retrieve':
            return RecurringPatternDetailSerializer
        elif self.action == 'create':
            return RecurringPatternCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return RecurringPatternUpdateSerializer
        return RecurringPatternSerializer

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        """Create a new recurring pattern."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        generate_bookings = data.pop('generate_bookings', True)
        generate_until = data.pop('generate_until', None)

        # Create the pattern
        pattern = RecurringPattern.objects.create(
            created_by=request.user.id if hasattr(request, 'user') else None,
            **data
        )

        # Generate bookings if requested
        bookings_created = 0
        if generate_bookings:
            bookings_created = self._generate_pattern_bookings(
                pattern,
                until_date=generate_until
            )

        output_serializer = RecurringPatternDetailSerializer(pattern)
        response_data = output_serializer.data
        response_data['bookings_created'] = bookings_created

        return Response(response_data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        """Update a recurring pattern."""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()

        serializer = self.get_serializer(
            instance, data=request.data, partial=partial
        )
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        apply_to_future = data.pop('apply_to_future', False)

        # Update pattern fields
        for field, value in data.items():
            setattr(instance, field, value)
        instance.save()

        # Update future bookings if requested
        updated_count = 0
        if apply_to_future:
            updated_count = self._update_future_bookings(instance, data)

        output_serializer = RecurringPatternDetailSerializer(instance)
        response_data = output_serializer.data
        response_data['bookings_updated'] = updated_count

        return Response(response_data)

    @action(detail=True, methods=['post'])
    def pause(self, request, pk=None):
        """Pause a recurring pattern."""
        pattern = self.get_object()

        if pattern.status != RecurringPattern.Status.ACTIVE:
            return Response(
                {'error': 'Only active patterns can be paused'},
                status=status.HTTP_400_BAD_REQUEST
            )

        pattern.status = RecurringPattern.Status.PAUSED
        pattern.save()

        serializer = RecurringPatternDetailSerializer(pattern)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def resume(self, request, pk=None):
        """Resume a paused recurring pattern."""
        pattern = self.get_object()

        if pattern.status != RecurringPattern.Status.PAUSED:
            return Response(
                {'error': 'Only paused patterns can be resumed'},
                status=status.HTTP_400_BAD_REQUEST
            )

        pattern.status = RecurringPattern.Status.ACTIVE
        pattern.save()

        serializer = RecurringPatternDetailSerializer(pattern)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel a recurring pattern."""
        pattern = self.get_object()
        cancel_future_bookings = request.data.get('cancel_future_bookings', False)

        if pattern.status in [RecurringPattern.Status.CANCELLED, RecurringPattern.Status.COMPLETED]:
            return Response(
                {'error': 'Pattern is already cancelled or completed'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Cancel future bookings if requested
        cancelled_count = 0
        if cancel_future_bookings:
            cancelled_count = self._cancel_future_bookings(pattern)

        pattern.status = RecurringPattern.Status.CANCELLED
        pattern.save()

        serializer = RecurringPatternDetailSerializer(pattern)
        response_data = serializer.data
        response_data['bookings_cancelled'] = cancelled_count

        return Response(response_data)

    @action(detail=True, methods=['get'])
    def occurrences(self, request, pk=None):
        """Get all occurrences for a pattern."""
        pattern = self.get_object()
        limit = int(request.query_params.get('limit', 20))

        # Get upcoming occurrences
        upcoming = pattern.get_next_occurrences(limit)

        # Get existing bookings for this pattern
        existing_bookings = {
            b.scheduled_start.date(): b
            for b in pattern.bookings.filter(
                scheduled_start__date__gte=timezone.now().date()
            ).exclude(status=Booking.Status.CANCELLED)
        }

        occurrences = []
        for occ_date in upcoming:
            booking = existing_bookings.get(occ_date)
            is_exception = occ_date in (pattern.exception_dates or [])
            modification = (pattern.modified_dates or {}).get(occ_date.isoformat())

            occurrence_data = {
                'date': occ_date,
                'start_time': modification.get('start_time', pattern.start_time) if modification else pattern.start_time,
                'end_time': modification.get('end_time', pattern.end_time) if modification else pattern.end_time,
                'status': 'exception' if is_exception else ('modified' if modification else 'scheduled'),
                'booking_id': booking.id if booking else None,
                'booking_number': booking.booking_number if booking else None,
                'modification': modification,
            }
            occurrences.append(occurrence_data)

        serializer = RecurringPatternOccurrenceSerializer(occurrences, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def add_exception(self, request, pk=None):
        """Add an exception date to the pattern."""
        pattern = self.get_object()
        exception_date_str = request.data.get('date')
        reason = request.data.get('reason')
        cancel_booking = request.data.get('cancel_booking', True)

        if not exception_date_str:
            return Response(
                {'error': 'Date is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            exception_date = datetime.strptime(exception_date_str, '%Y-%m-%d').date()
        except ValueError:
            return Response(
                {'error': 'Invalid date format. Use YYYY-MM-DD'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Add to exception dates
        if not pattern.exception_dates:
            pattern.exception_dates = []

        if exception_date not in pattern.exception_dates:
            pattern.exception_dates.append(exception_date)
            pattern.save()

        # Cancel booking for this date if requested
        cancelled_booking = None
        if cancel_booking:
            booking = pattern.bookings.filter(
                scheduled_start__date=exception_date
            ).exclude(status=Booking.Status.CANCELLED).first()

            if booking:
                booking.cancel(reason or 'Pattern exception')
                cancelled_booking = booking.booking_number

        return Response({
            'success': True,
            'exception_date': exception_date.isoformat(),
            'cancelled_booking': cancelled_booking,
        })

    @action(detail=True, methods=['post'])
    def remove_exception(self, request, pk=None):
        """Remove an exception date from the pattern."""
        pattern = self.get_object()
        exception_date_str = request.data.get('date')

        if not exception_date_str:
            return Response(
                {'error': 'Date is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            exception_date = datetime.strptime(exception_date_str, '%Y-%m-%d').date()
        except ValueError:
            return Response(
                {'error': 'Invalid date format. Use YYYY-MM-DD'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if pattern.exception_dates and exception_date in pattern.exception_dates:
            pattern.exception_dates.remove(exception_date)
            pattern.save()

        return Response({
            'success': True,
            'removed_date': exception_date.isoformat(),
        })

    @action(detail=True, methods=['post'])
    def generate_bookings(self, request, pk=None):
        """Generate bookings for a pattern."""
        pattern = self.get_object()
        until_date_str = request.data.get('until_date')
        max_count = request.data.get('max_count', 10)

        until_date = None
        if until_date_str:
            try:
                until_date = datetime.strptime(until_date_str, '%Y-%m-%d').date()
            except ValueError:
                return Response(
                    {'error': 'Invalid date format. Use YYYY-MM-DD'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        created_count = self._generate_pattern_bookings(
            pattern,
            until_date=until_date,
            max_count=max_count
        )

        return Response({
            'success': True,
            'bookings_created': created_count,
        })

    @action(detail=True, methods=['get'])
    def bookings(self, request, pk=None):
        """Get all bookings created from this pattern."""
        pattern = self.get_object()
        include_past = request.query_params.get('include_past', 'false').lower() == 'true'
        include_cancelled = request.query_params.get('include_cancelled', 'false').lower() == 'true'

        bookings = pattern.bookings.all()

        if not include_past:
            bookings = bookings.filter(scheduled_start__gte=timezone.now())

        if not include_cancelled:
            bookings = bookings.exclude(status=Booking.Status.CANCELLED)

        bookings = bookings.order_by('scheduled_start')

        from apps.api.serializers import BookingListSerializer
        serializer = BookingListSerializer(bookings, many=True)
        return Response(serializer.data)

    def _generate_pattern_bookings(
        self,
        pattern: RecurringPattern,
        until_date: date = None,
        max_count: int = 10
    ) -> int:
        """Generate bookings from a recurring pattern."""
        if not pattern.is_active:
            return 0

        occurrences = pattern.get_next_occurrences(max_count)
        created_count = 0

        for occ_date in occurrences:
            if until_date and occ_date > until_date:
                break

            # Check if booking already exists for this date
            existing = pattern.bookings.filter(
                scheduled_start__date=occ_date
            ).exclude(status=Booking.Status.CANCELLED).exists()

            if existing:
                continue

            try:
                # Create booking for this occurrence
                start_dt = timezone.make_aware(
                    datetime.combine(occ_date, pattern.start_time)
                )
                end_dt = timezone.make_aware(
                    datetime.combine(occ_date, pattern.end_time)
                )

                booking = self.booking_service.create_booking(
                    organization_id=pattern.organization_id,
                    location_id=pattern.location_id,
                    scheduled_start=start_dt,
                    scheduled_end=end_dt,
                    booking_type=pattern.booking_type,
                    training_type=pattern.training_type,
                    aircraft_id=pattern.aircraft_id,
                    instructor_id=pattern.instructor_id,
                    student_id=pattern.student_id,
                    preflight_minutes=pattern.preflight_minutes,
                    postflight_minutes=pattern.postflight_minutes,
                    route=pattern.route,
                    remarks=pattern.notes,
                    recurring_pattern_id=pattern.id,
                    created_by=pattern.created_by,
                    skip_conflict_check=False,
                )

                pattern.occurrences_created += 1
                created_count += 1

            except Exception as e:
                logger.warning(
                    f"Failed to create booking for pattern {pattern.id} "
                    f"on {occ_date}: {e}"
                )

        pattern.save()
        return created_count

    def _update_future_bookings(
        self,
        pattern: RecurringPattern,
        updates: dict
    ) -> int:
        """Update future bookings from a pattern with new values."""
        future_bookings = pattern.bookings.filter(
            scheduled_start__gte=timezone.now()
        ).exclude(
            status__in=[Booking.Status.CANCELLED, Booking.Status.COMPLETED]
        )

        updated_count = 0
        update_fields = {}

        if 'aircraft_id' in updates:
            update_fields['aircraft_id'] = updates['aircraft_id']
        if 'instructor_id' in updates:
            update_fields['instructor_id'] = updates['instructor_id']
        if 'preflight_minutes' in updates:
            update_fields['preflight_minutes'] = updates['preflight_minutes']
        if 'postflight_minutes' in updates:
            update_fields['postflight_minutes'] = updates['postflight_minutes']
        if 'route' in updates:
            update_fields['route'] = updates['route']

        if update_fields:
            updated_count = future_bookings.update(**update_fields)

        return updated_count

    def _cancel_future_bookings(self, pattern: RecurringPattern) -> int:
        """Cancel all future bookings from a pattern."""
        future_bookings = pattern.bookings.filter(
            scheduled_start__gte=timezone.now()
        ).exclude(
            status__in=[Booking.Status.CANCELLED, Booking.Status.COMPLETED]
        )

        cancelled_count = 0
        for booking in future_bookings:
            try:
                booking.cancel('Recurring pattern cancelled')
                cancelled_count += 1
            except Exception as e:
                logger.warning(
                    f"Failed to cancel booking {booking.id}: {e}"
                )

        return cancelled_count
