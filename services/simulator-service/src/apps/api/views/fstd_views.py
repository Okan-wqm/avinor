# services/simulator-service/src/apps/api/views/fstd_views.py
"""
FSTD Device ViewSet
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from apps.core.models import FSTDevice
from apps.api.serializers import (
    FSTDeviceSerializer,
    FSTDeviceListSerializer,
)
from apps.api.serializers.fstd_serializers import FSTDeviceCreateSerializer


class FSTDeviceViewSet(viewsets.ModelViewSet):
    """
    ViewSet for FSTD Device management

    Endpoints:
    - GET /api/v1/devices/ - List all devices
    - POST /api/v1/devices/ - Create new device
    - GET /api/v1/devices/{id}/ - Get device details
    - PUT /api/v1/devices/{id}/ - Update device
    - DELETE /api/v1/devices/{id}/ - Delete device
    - GET /api/v1/devices/available/ - List available devices
    - GET /api/v1/devices/{id}/availability/ - Get device availability
    - POST /api/v1/devices/{id}/maintenance/ - Set maintenance status
    """

    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['fstd_type', 'qualification_level', 'status', 'aircraft_type_simulated']
    search_fields = ['name', 'device_id', 'aircraft_type_simulated', 'manufacturer']
    ordering_fields = ['name', 'created_at', 'qualification_expiry', 'hourly_rate']
    ordering = ['name']

    def get_queryset(self):
        """Filter by organization"""
        queryset = FSTDevice.objects.all()

        # Filter by organization if available in request
        organization_id = getattr(self.request, 'organization_id', None)
        if organization_id:
            queryset = queryset.filter(organization_id=organization_id)

        return queryset

    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'list':
            return FSTDeviceListSerializer
        elif self.action == 'create':
            return FSTDeviceCreateSerializer
        return FSTDeviceSerializer

    @action(detail=False, methods=['get'])
    def available(self, request):
        """Get list of available devices"""
        queryset = self.get_queryset().filter(
            status='active'
        )

        # Filter qualified only
        from django.utils import timezone
        queryset = queryset.filter(
            qualification_expiry__gte=timezone.now().date()
        )

        serializer = FSTDeviceListSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def availability(self, request, pk=None):
        """Get device availability for scheduling"""
        device = self.get_object()
        date_str = request.query_params.get('date')

        # Return available time slots
        # This would check against existing bookings/sessions
        available_slots = device.get_available_slots(date_str) if date_str else []

        return Response({
            'device_id': str(device.id),
            'device_name': device.name,
            'status': device.status,
            'is_available': device.is_available,
            'operating_hours': {
                'start': str(device.operating_hours_start) if device.operating_hours_start else None,
                'end': str(device.operating_hours_end) if device.operating_hours_end else None,
            },
            'slots': available_slots,
        })

    @action(detail=True, methods=['post'])
    def maintenance(self, request, pk=None):
        """Set device to maintenance status"""
        device = self.get_object()

        device.status = 'maintenance'
        device.maintenance_notes = request.data.get('notes', '')
        device.next_maintenance_date = request.data.get('next_maintenance_date')
        device.save()

        return Response({
            'status': 'success',
            'message': f'Device {device.name} set to maintenance mode'
        })

    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Activate device after maintenance"""
        device = self.get_object()

        device.status = 'active'
        device.last_maintenance_date = request.data.get('maintenance_date')
        device.hours_since_qualification = 0  # Reset if recertified
        device.save()

        return Response({
            'status': 'success',
            'message': f'Device {device.name} activated'
        })

    @action(detail=False, methods=['get'])
    def expiring(self, request):
        """Get devices with expiring qualifications"""
        from django.utils import timezone
        from datetime import timedelta

        days = int(request.query_params.get('days', 90))
        threshold_date = timezone.now().date() + timedelta(days=days)

        queryset = self.get_queryset().filter(
            qualification_expiry__lte=threshold_date,
            qualification_expiry__gte=timezone.now().date(),
            status='active'
        ).order_by('qualification_expiry')

        serializer = FSTDeviceListSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get fleet-wide statistics"""
        from django.db.models import Sum, Count, Avg

        queryset = self.get_queryset()

        stats = queryset.aggregate(
            total_devices=Count('id'),
            total_hours=Sum('total_hours'),
            total_sessions=Sum('total_sessions'),
            avg_hourly_rate=Avg('hourly_rate'),
        )

        # Count by type
        by_type = queryset.values('fstd_type').annotate(
            count=Count('id'),
            hours=Sum('total_hours')
        )

        # Count by status
        by_status = queryset.values('status').annotate(count=Count('id'))

        return Response({
            'summary': stats,
            'by_type': list(by_type),
            'by_status': list(by_status),
        })
