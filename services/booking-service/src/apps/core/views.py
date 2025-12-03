"""Booking Service Views."""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.utils import timezone
from django.db.models import Q

from .models import Booking, BookingResource, Schedule, WaitlistEntry
from .serializers import (
    BookingSerializer, BookingListSerializer, BookingCreateSerializer,
    ScheduleSerializer, WaitlistEntrySerializer
)


class BookingViewSet(viewsets.ModelViewSet):
    queryset = Booking.objects.filter(is_deleted=False)
    serializer_class = BookingSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'booking_type', 'aircraft_id', 'pilot_id', 'instructor_id', 'organization_id']
    search_fields = ['title', 'description']
    ordering_fields = ['start_time', 'created_at']
    ordering = ['-start_time']

    def get_serializer_class(self):
        if self.action == 'list':
            return BookingListSerializer
        elif self.action == 'create':
            return BookingCreateSerializer
        return BookingSerializer

    @action(detail=False, methods=['get'])
    def upcoming(self, request):
        """Get upcoming bookings."""
        bookings = self.queryset.filter(
            start_time__gte=timezone.now(),
            status__in=['pending', 'confirmed']
        )[:20]
        serializer = BookingListSerializer(bookings, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def today(self, request):
        """Get today's bookings."""
        today = timezone.now().date()
        bookings = self.queryset.filter(
            start_time__date=today
        )
        serializer = BookingListSerializer(bookings, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        """Confirm a booking."""
        booking = self.get_object()
        booking.status = Booking.Status.CONFIRMED
        booking.confirmed_at = timezone.now()
        booking.confirmed_by_id = request.user.id
        booking.save()
        return Response(BookingSerializer(booking).data)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel a booking."""
        booking = self.get_object()
        booking.status = Booking.Status.CANCELLED
        booking.cancelled_at = timezone.now()
        booking.cancelled_by_id = request.user.id
        booking.cancellation_reason = request.data.get('reason', '')
        booking.save()
        return Response(BookingSerializer(booking).data)

    @action(detail=True, methods=['post'])
    def check_in(self, request, pk=None):
        """Check in for a booking."""
        booking = self.get_object()
        booking.status = Booking.Status.CHECKED_IN
        booking.actual_start_time = timezone.now()
        booking.save()
        return Response(BookingSerializer(booking).data)

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Complete a booking."""
        booking = self.get_object()
        booking.status = Booking.Status.COMPLETED
        booking.actual_end_time = timezone.now()
        booking.actual_hours = request.data.get('actual_hours')
        booking.actual_cost = request.data.get('actual_cost')
        booking.save()
        return Response(BookingSerializer(booking).data)

    @action(detail=False, methods=['get'])
    def check_availability(self, request):
        """Check availability for a time slot."""
        aircraft_id = request.query_params.get('aircraft_id')
        instructor_id = request.query_params.get('instructor_id')
        start_time = request.query_params.get('start_time')
        end_time = request.query_params.get('end_time')

        conflicts = self.queryset.filter(
            status__in=['pending', 'confirmed', 'checked_in', 'in_progress']
        ).filter(
            Q(start_time__lt=end_time) & Q(end_time__gt=start_time)
        )

        if aircraft_id:
            conflicts = conflicts.filter(aircraft_id=aircraft_id)
        if instructor_id:
            conflicts = conflicts.filter(instructor_id=instructor_id)

        return Response({
            'available': not conflicts.exists(),
            'conflicts': BookingListSerializer(conflicts, many=True).data
        })


class ScheduleViewSet(viewsets.ModelViewSet):
    queryset = Schedule.objects.all()
    serializer_class = ScheduleSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['user_id', 'aircraft_id', 'schedule_type', 'organization_id']
    ordering = ['start_time']

    @action(detail=False, methods=['get'])
    def instructor_availability(self, request):
        """Get instructor availability."""
        instructor_id = request.query_params.get('instructor_id')
        date = request.query_params.get('date')

        schedules = self.queryset.filter(
            user_id=instructor_id,
            start_time__date=date
        )
        return Response(ScheduleSerializer(schedules, many=True).data)


class WaitlistViewSet(viewsets.ModelViewSet):
    queryset = WaitlistEntry.objects.all()
    serializer_class = WaitlistEntrySerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['user_id', 'status', 'organization_id']
    ordering = ['created_at']
