# services/simulator-service/src/apps/core/services/fstd_service.py
"""
FSTD Device Service - Business Logic
"""

from typing import Optional, Dict, Any, List
from decimal import Decimal
from datetime import date, timedelta
from django.utils import timezone
from django.db.models import QuerySet, Sum, Count, Avg

from apps.core.models import FSTDevice


class FSTDService:
    """Service for FSTD device management"""

    @staticmethod
    def get_available_devices(
        organization_id: str,
        device_type: Optional[str] = None,
        date_required: Optional[date] = None
    ) -> QuerySet:
        """Get available FSTD devices"""
        queryset = FSTDevice.objects.filter(
            organization_id=organization_id,
            status='active',
            qualification_expiry__gte=timezone.now().date()
        )

        if device_type:
            queryset = queryset.filter(fstd_type=device_type)

        return queryset

    @staticmethod
    def get_expiring_qualifications(
        organization_id: str,
        days: int = 90
    ) -> QuerySet:
        """Get devices with qualifications expiring within specified days"""
        threshold = timezone.now().date() + timedelta(days=days)

        return FSTDevice.objects.filter(
            organization_id=organization_id,
            status='active',
            qualification_expiry__lte=threshold,
            qualification_expiry__gte=timezone.now().date()
        ).order_by('qualification_expiry')

    @staticmethod
    def get_fleet_statistics(organization_id: str) -> Dict[str, Any]:
        """Get fleet-wide FSTD statistics"""
        devices = FSTDevice.objects.filter(organization_id=organization_id)

        stats = devices.aggregate(
            total_devices=Count('id'),
            total_hours=Sum('total_hours'),
            total_sessions=Sum('total_sessions'),
            avg_hourly_rate=Avg('hourly_rate'),
        )

        by_type = list(
            devices.values('fstd_type').annotate(
                count=Count('id'),
                hours=Sum('total_hours')
            )
        )

        by_status = list(
            devices.values('status').annotate(count=Count('id'))
        )

        by_qualification = list(
            devices.values('qualification_level').annotate(count=Count('id'))
        )

        return {
            'summary': stats,
            'by_type': by_type,
            'by_status': by_status,
            'by_qualification_level': by_qualification,
        }

    @staticmethod
    def calculate_training_credit(
        device: FSTDevice,
        session_type: str,
        duration_hours: Decimal
    ) -> Dict[str, Decimal]:
        """Calculate training credit based on device type and session"""
        credit_rules = device.training_credit_rules or {}

        # Default credit is 1:1
        credit_rate = Decimal('1.0')

        # Apply device-type specific rules
        if session_type in credit_rules:
            credit_rate = Decimal(str(credit_rules[session_type]))
        elif 'default' in credit_rules:
            credit_rate = Decimal(str(credit_rules['default']))

        credited_hours = duration_hours * credit_rate

        return {
            'actual_hours': duration_hours,
            'credit_rate': credit_rate,
            'credited_hours': credited_hours,
        }

    @staticmethod
    def set_maintenance_mode(
        device: FSTDevice,
        notes: str = '',
        next_maintenance_date: Optional[date] = None,
        user_id: Optional[str] = None
    ) -> FSTDevice:
        """Set device to maintenance mode"""
        device.status = 'maintenance'
        device.maintenance_notes = notes
        device.next_maintenance_date = next_maintenance_date
        if user_id:
            device.updated_by = user_id
        device.save()
        return device

    @staticmethod
    def activate_after_maintenance(
        device: FSTDevice,
        maintenance_date: Optional[date] = None,
        user_id: Optional[str] = None
    ) -> FSTDevice:
        """Activate device after maintenance"""
        device.status = 'active'
        device.last_maintenance_date = maintenance_date or timezone.now().date()
        device.maintenance_notes = ''
        if user_id:
            device.updated_by = user_id
        device.save()
        return device

    @staticmethod
    def update_qualification(
        device: FSTDevice,
        certificate_number: str,
        authority: str,
        qualification_date: date,
        expiry_date: date,
        level: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> FSTDevice:
        """Update device qualification/certification"""
        device.qualification_certificate_number = certificate_number
        device.qualification_authority = authority
        device.qualification_date = qualification_date
        device.qualification_expiry = expiry_date
        device.hours_since_qualification = Decimal('0.00')

        if level:
            device.qualification_level = level

        if user_id:
            device.updated_by = user_id

        device.save()
        return device
