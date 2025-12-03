# services/booking-service/src/apps/api/views/waitlist_views.py
"""
Waitlist API Views

Views for managing booking waitlists.
"""

import logging
from datetime import datetime, date

from django.db import transaction
from django.utils import timezone
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend

from apps.core.models import WaitlistEntry, Booking
from apps.core.services import WaitlistService, WaitlistError, AvailabilityService
from apps.api.serializers import (
    WaitlistEntrySerializer,
    WaitlistEntryListSerializer,
    WaitlistEntryDetailSerializer,
    WaitlistEntryCreateSerializer,
    WaitlistEntryUpdateSerializer,
    WaitlistOfferSerializer,
    WaitlistOfferResponseSerializer,
    WaitlistCancelSerializer,
    WaitlistStatisticsSerializer,
)
from .pagination import StandardResultsSetPagination

logger = logging.getLogger(__name__)


class WaitlistEntryViewSet(viewsets.ModelViewSet):
    """
    ViewSet for waitlist entry management.

    Manages waitlist entries and offer workflow.
    """

    queryset = WaitlistEntry.objects.all()
    serializer_class = WaitlistEntrySerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['status', 'user_id', 'aircraft_id', 'instructor_id', 'requested_date']
    ordering_fields = ['priority', 'created_at', 'requested_date']
    ordering = ['-priority', 'created_at']

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.waitlist_service = WaitlistService()
        self.availability_service = AvailabilityService()

    def get_queryset(self):
        """Filter queryset by organization and active status."""
        queryset = super().get_queryset()
        organization_id = self.request.headers.get('X-Organization-ID')

        if organization_id:
            queryset = queryset.filter(organization_id=organization_id)

        # Filter by active status
        active_only = self.request.query_params.get('active_only', 'true').lower() == 'true'
        if active_only:
            queryset = queryset.filter(
                status__in=[
                    WaitlistEntry.Status.WAITING,
                    WaitlistEntry.Status.OFFERED
                ]
            )

        return queryset

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return WaitlistEntryListSerializer
        elif self.action == 'retrieve':
            return WaitlistEntryDetailSerializer
        elif self.action == 'create':
            return WaitlistEntryCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return WaitlistEntryUpdateSerializer
        return WaitlistEntrySerializer

    def create(self, request, *args, **kwargs):
        """Add to waitlist."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        check_availability = data.pop('check_availability', True)

        # Check for immediate availability first
        if check_availability:
            slots = self.availability_service.get_available_slots(
                organization_id=data['organization_id'],
                target_date=data['requested_date'],
                duration_minutes=data.get('duration_minutes', 60),
                aircraft_id=data.get('aircraft_id') if not data.get('any_aircraft') else None,
                instructor_id=data.get('instructor_id') if not data.get('any_instructor') else None,
                location_id=data.get('location_id'),
            )

            if slots:
                return Response({
                    'added_to_waitlist': False,
                    'message': 'Slots are currently available',
                    'available_slots': slots[:5],
                }, status=status.HTTP_200_OK)

        try:
            entry = self.waitlist_service.add_to_waitlist(**data)

            output_serializer = WaitlistEntryDetailSerializer(entry)
            return Response(
                output_serializer.data,
                status=status.HTTP_201_CREATED
            )

        except WaitlistError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def send_offer(self, request, pk=None):
        """Send an offer to a waitlist entry."""
        serializer = WaitlistOfferSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data

        try:
            entry = self.waitlist_service.send_offer(
                entry_id=pk,
                booking_id=data['booking_id'],
                message=data.get('message'),
                expires_in_hours=data.get('expires_in_hours', 4)
            )

            output_serializer = WaitlistEntryDetailSerializer(entry)
            return Response(output_serializer.data)

        except WaitlistError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def respond_to_offer(self, request, pk=None):
        """Respond to an offer (accept or decline)."""
        serializer = WaitlistOfferResponseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        action_type = data['action']

        try:
            if action_type == 'accept':
                entry = self.waitlist_service.accept_offer(
                    entry_id=pk,
                    notes=data.get('notes')
                )
            else:
                entry = self.waitlist_service.decline_offer(
                    entry_id=pk,
                    notes=data.get('notes')
                )

            output_serializer = WaitlistEntryDetailSerializer(entry)
            return Response(output_serializer.data)

        except WaitlistError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def accept(self, request, pk=None):
        """Accept an offer."""
        notes = request.data.get('notes')

        try:
            entry = self.waitlist_service.accept_offer(
                entry_id=pk,
                notes=notes
            )
            output_serializer = WaitlistEntryDetailSerializer(entry)
            return Response(output_serializer.data)

        except WaitlistError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def decline(self, request, pk=None):
        """Decline an offer."""
        notes = request.data.get('notes')

        try:
            entry = self.waitlist_service.decline_offer(
                entry_id=pk,
                notes=notes
            )
            output_serializer = WaitlistEntryDetailSerializer(entry)
            return Response(output_serializer.data)

        except WaitlistError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel a waitlist entry."""
        serializer = WaitlistCancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        reason = serializer.validated_data.get('reason')

        try:
            entry = self.waitlist_service.cancel_entry(
                entry_id=pk,
                reason=reason
            )
            output_serializer = WaitlistEntryDetailSerializer(entry)
            return Response(output_serializer.data)

        except WaitlistError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['get'])
    def my_entries(self, request):
        """Get current user's waitlist entries."""
        user_id = request.headers.get('X-User-ID')
        organization_id = request.headers.get('X-Organization-ID')

        if not user_id:
            return Response(
                {'error': 'User ID required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        entries = self.waitlist_service.list_entries(
            organization_id=organization_id,
            user_id=user_id,
            active_only=True
        )

        serializer = WaitlistEntryListSerializer(entries, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def for_date(self, request):
        """Get waitlist entries for a specific date."""
        organization_id = request.headers.get('X-Organization-ID')
        date_str = request.query_params.get('date')

        if not date_str:
            return Response(
                {'error': 'date is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            requested_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return Response(
                {'error': 'Invalid date format. Use YYYY-MM-DD'},
                status=status.HTTP_400_BAD_REQUEST
            )

        entries = self.waitlist_service.list_entries(
            organization_id=organization_id,
            requested_date=requested_date,
            active_only=True
        )

        serializer = WaitlistEntryListSerializer(entries, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def process_cancellation(self, request):
        """Process a booking cancellation and notify waitlist."""
        booking_id = request.data.get('booking_id')
        auto_offer = request.data.get('auto_offer', True)

        if not booking_id:
            return Response(
                {'error': 'booking_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            booking = Booking.objects.get(id=booking_id)
        except Booking.DoesNotExist:
            return Response(
                {'error': 'Booking not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        if auto_offer:
            self.waitlist_service.process_cancellation(booking)

        return Response({
            'success': True,
            'message': 'Waitlist processed for cancellation',
        })

    @action(detail=False, methods=['post'])
    def process_expired(self, request):
        """Process expired entries and offers."""
        organization_id = request.headers.get('X-Organization-ID')

        expired_entries = self.waitlist_service.process_expired_entries(organization_id)
        expired_offers = self.waitlist_service.process_expired_offers(organization_id)

        return Response({
            'expired_entries': expired_entries,
            'expired_offers': expired_offers,
        })

    @action(detail=False, methods=['get'])
    def matching_slots(self, request):
        """Find available slots matching waitlist entries."""
        organization_id = request.headers.get('X-Organization-ID')
        entry_id = request.query_params.get('entry_id')

        if not entry_id:
            return Response(
                {'error': 'entry_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            entry = WaitlistEntry.objects.get(id=entry_id)
        except WaitlistEntry.DoesNotExist:
            return Response(
                {'error': 'Entry not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Find matching slots
        slots = self.availability_service.get_available_slots(
            organization_id=organization_id,
            target_date=entry.requested_date,
            duration_minutes=entry.duration_minutes or 60,
            aircraft_id=entry.aircraft_id if not entry.any_aircraft else None,
            instructor_id=entry.instructor_id if not entry.any_instructor else None,
            location_id=entry.location_id,
        )

        # Also check flexible dates
        flexible_slots = []
        if entry.flexibility_days > 0:
            for delta in range(1, entry.flexibility_days + 1):
                for date_offset in [delta, -delta]:
                    flex_date = entry.requested_date + timedelta(days=date_offset)
                    if flex_date < timezone.now().date():
                        continue

                    flex_slots = self.availability_service.get_available_slots(
                        organization_id=organization_id,
                        target_date=flex_date,
                        duration_minutes=entry.duration_minutes or 60,
                        aircraft_id=entry.aircraft_id if not entry.any_aircraft else None,
                        instructor_id=entry.instructor_id if not entry.any_instructor else None,
                        location_id=entry.location_id,
                    )
                    for slot in flex_slots:
                        slot['is_flexible_date'] = True
                    flexible_slots.extend(flex_slots)

        return Response({
            'entry_id': str(entry.id),
            'requested_date': entry.requested_date.isoformat(),
            'primary_slots': slots,
            'flexible_slots': flexible_slots[:10],
        })


class WaitlistStatisticsView(APIView):
    """View for waitlist statistics."""

    permission_classes = [IsAuthenticated]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.waitlist_service = WaitlistService()

    def get(self, request):
        """Get waitlist statistics."""
        organization_id = request.headers.get('X-Organization-ID')
        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')

        if not organization_id:
            return Response(
                {'error': 'Organization ID required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        start_date = None
        end_date = None

        if start_date_str:
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            except ValueError:
                pass

        if end_date_str:
            try:
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            except ValueError:
                pass

        statistics = self.waitlist_service.get_statistics(
            organization_id=organization_id,
            start_date=start_date,
            end_date=end_date
        )

        # Calculate average wait time
        from django.db.models import Avg, F
        from django.db.models.functions import Extract

        avg_wait = WaitlistEntry.objects.filter(
            organization_id=organization_id,
            status__in=[WaitlistEntry.Status.ACCEPTED, WaitlistEntry.Status.FULFILLED]
        )

        if start_date:
            avg_wait = avg_wait.filter(requested_date__gte=start_date)
        if end_date:
            avg_wait = avg_wait.filter(requested_date__lte=end_date)

        # This is a simplified calculation
        avg_wait_days = 0  # Would need proper calculation based on offer times

        statistics['average_wait_days'] = avg_wait_days

        serializer = WaitlistStatisticsSerializer(statistics)
        return Response(serializer.data)


# Import at the end to avoid circular imports
from datetime import timedelta
