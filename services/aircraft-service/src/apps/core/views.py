"""
Aircraft Service Views.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.db.models import Q

from shared.common.permissions import IsAdmin
from .models import AircraftType, Aircraft, AircraftDocument, Squawk, FuelLog
from .serializers import (
    AircraftTypeSerializer, AircraftTypeListSerializer,
    AircraftSerializer, AircraftListSerializer,
    AircraftDocumentSerializer, SquawkSerializer, SquawkListSerializer,
    FuelLogSerializer,
)


class AircraftTypeViewSet(viewsets.ModelViewSet):
    queryset = AircraftType.objects.all()
    serializer_class = AircraftTypeSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['category', 'is_active', 'requires_type_rating']
    search_fields = ['manufacturer', 'model', 'icao_designator']
    ordering_fields = ['manufacturer', 'model']
    ordering = ['manufacturer', 'model']

    def get_serializer_class(self):
        if self.action == 'list':
            return AircraftTypeListSerializer
        return AircraftTypeSerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdmin()]
        return super().get_permissions()


class AircraftViewSet(viewsets.ModelViewSet):
    queryset = Aircraft.objects.filter(is_deleted=False)
    serializer_class = AircraftSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'aircraft_type', 'organization_id', 'home_base_id']
    search_fields = ['registration', 'name', 'callsign', 'serial_number']
    ordering_fields = ['registration', 'total_time_hours', 'created_at']
    ordering = ['registration']

    def get_serializer_class(self):
        if self.action == 'list':
            return AircraftListSerializer
        return AircraftSerializer

    @action(detail=True, methods=['get'])
    def documents(self, request, pk=None):
        aircraft = self.get_object()
        documents = aircraft.documents.filter(is_current=True)
        serializer = AircraftDocumentSerializer(documents, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def squawks(self, request, pk=None):
        aircraft = self.get_object()
        status_filter = request.query_params.get('status', None)
        squawks = aircraft.squawks.all()
        if status_filter:
            squawks = squawks.filter(status=status_filter)
        serializer = SquawkListSerializer(squawks, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def fuel_history(self, request, pk=None):
        aircraft = self.get_object()
        fuel_logs = aircraft.fuel_logs.all()[:50]
        serializer = FuelLogSerializer(fuel_logs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def available(self, request):
        """Get all available aircraft."""
        aircraft = self.queryset.filter(status=Aircraft.Status.AVAILABLE)
        org_id = request.query_params.get('organization_id')
        if org_id:
            aircraft = aircraft.filter(organization_id=org_id)
        serializer = AircraftListSerializer(aircraft, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        """Update aircraft status."""
        aircraft = self.get_object()
        new_status = request.data.get('status')
        if new_status not in dict(Aircraft.Status.choices):
            return Response(
                {'error': 'Invalid status'},
                status=status.HTTP_400_BAD_REQUEST
            )
        aircraft.status = new_status
        aircraft.save(update_fields=['status', 'updated_at'])
        return Response({'status': aircraft.status})


class AircraftDocumentViewSet(viewsets.ModelViewSet):
    queryset = AircraftDocument.objects.all()
    serializer_class = AircraftDocumentSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['aircraft', 'document_type', 'is_current']
    search_fields = ['title', 'description']
    ordering = ['-created_at']

    @action(detail=False, methods=['get'])
    def expiring_soon(self, request):
        """Get documents expiring within specified days."""
        from django.utils import timezone
        from datetime import timedelta

        days = int(request.query_params.get('days', 30))
        cutoff = timezone.now().date() + timedelta(days=days)

        documents = self.queryset.filter(
            is_current=True,
            expiry_date__isnull=False,
            expiry_date__lte=cutoff
        ).order_by('expiry_date')

        serializer = self.get_serializer(documents, many=True)
        return Response(serializer.data)


class SquawkViewSet(viewsets.ModelViewSet):
    queryset = Squawk.objects.all()
    serializer_class = SquawkSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['aircraft', 'severity', 'status', 'reported_by_id']
    search_fields = ['title', 'description']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action == 'list':
            return SquawkListSerializer
        return SquawkSerializer

    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        """Resolve a squawk."""
        from django.utils import timezone

        squawk = self.get_object()
        squawk.status = Squawk.Status.RESOLVED
        squawk.resolved_at = timezone.now()
        squawk.resolved_by_id = request.user.id
        squawk.resolution_notes = request.data.get('resolution_notes', '')
        squawk.save()
        return Response(SquawkSerializer(squawk).data)

    @action(detail=False, methods=['get'])
    def open_critical(self, request):
        """Get all open critical squawks."""
        squawks = self.queryset.filter(
            status__in=[Squawk.Status.OPEN, Squawk.Status.IN_PROGRESS],
            severity=Squawk.Severity.CRITICAL
        )
        serializer = SquawkListSerializer(squawks, many=True)
        return Response(serializer.data)


class FuelLogViewSet(viewsets.ModelViewSet):
    queryset = FuelLog.objects.all()
    serializer_class = FuelLogSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['aircraft', 'transaction_type', 'recorded_by_id']
    ordering = ['-created_at']
