"""Flight Service Views."""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.utils import timezone
from django.db.models import Sum, Count

from .models import Flight, FlightTrack, LogbookEntry, PilotTotals
from .serializers import (
    FlightSerializer, FlightListSerializer, FlightTrackSerializer,
    LogbookEntrySerializer, PilotTotalsSerializer
)


class FlightViewSet(viewsets.ModelViewSet):
    queryset = Flight.objects.filter(is_deleted=False)
    serializer_class = FlightSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'flight_type', 'aircraft_id', 'pic_id', 'instructor_id', 'organization_id']
    search_fields = ['departure_airport', 'arrival_airport', 'remarks']
    ordering_fields = ['actual_departure', 'scheduled_departure', 'flight_time']
    ordering = ['-actual_departure']

    def get_serializer_class(self):
        if self.action == 'list':
            return FlightListSerializer
        return FlightSerializer

    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """Start a flight."""
        flight = self.get_object()
        flight.status = Flight.Status.IN_PROGRESS
        flight.actual_departure = timezone.now()
        flight.save()
        return Response(FlightSerializer(flight).data)

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Complete a flight."""
        flight = self.get_object()
        flight.status = Flight.Status.COMPLETED
        flight.actual_arrival = timezone.now()

        # Update times from request
        for field in ['block_time', 'flight_time', 'hobbs_end', 'tach_end',
                      'time_pic', 'time_dual_received', 'time_dual_given',
                      'landings_day', 'landings_night', 'fuel_used_liters']:
            if field in request.data:
                setattr(flight, field, request.data[field])

        flight.save()
        return Response(FlightSerializer(flight).data)

    @action(detail=True, methods=['get'])
    def track(self, request, pk=None):
        """Get flight track points."""
        flight = self.get_object()
        tracks = flight.track_points.all()
        return Response(FlightTrackSerializer(tracks, many=True).data)

    @action(detail=True, methods=['post'])
    def add_track_point(self, request, pk=None):
        """Add track point to flight."""
        flight = self.get_object()
        data = request.data.copy()
        data['flight'] = flight.id
        serializer = FlightTrackSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class LogbookViewSet(viewsets.ModelViewSet):
    queryset = LogbookEntry.objects.all()
    serializer_class = LogbookEntrySerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['pilot_id', 'aircraft_type']
    ordering = ['-date']

    @action(detail=False, methods=['get'])
    def my_logbook(self, request):
        """Get current user's logbook entries."""
        entries = self.queryset.filter(pilot_id=request.user.id)
        page = self.paginate_queryset(entries)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    @action(detail=False, methods=['get'])
    def totals(self, request):
        """Get pilot totals."""
        pilot_id = request.query_params.get('pilot_id', request.user.id)
        totals, created = PilotTotals.objects.get_or_create(pilot_id=pilot_id)
        return Response(PilotTotalsSerializer(totals).data)

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get logbook summary for a period."""
        pilot_id = request.query_params.get('pilot_id', request.user.id)
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        entries = self.queryset.filter(pilot_id=pilot_id)
        if start_date:
            entries = entries.filter(date__gte=start_date)
        if end_date:
            entries = entries.filter(date__lte=end_date)

        summary = entries.aggregate(
            total_time=Sum('total_time'),
            pic_time=Sum('pic_time'),
            dual_received=Sum('dual_received'),
            cross_country=Sum('cross_country'),
            night_time=Sum('night_time'),
            instrument_time=Sum('actual_instrument') + Sum('simulated_instrument'),
            total_landings=Sum('day_landings') + Sum('night_landings'),
            flight_count=Count('id')
        )

        return Response(summary)
