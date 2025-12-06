# services/simulator-service/src/apps/core/services/session_service.py
"""
FSTD Session Service - Business Logic
"""

from typing import Optional, Dict, Any, List
from decimal import Decimal
from datetime import date, timedelta
from django.utils import timezone
from django.db.models import QuerySet, Sum, Count, Avg

from apps.core.models import FSTDSession, FSTDevice


class SessionService:
    """Service for FSTD session management"""

    @staticmethod
    def get_trainee_sessions(
        trainee_id: str,
        organization_id: Optional[str] = None,
        session_type: Optional[str] = None,
        status: Optional[str] = None,
    ) -> QuerySet:
        """Get all sessions for a trainee"""
        queryset = FSTDSession.objects.filter(trainee_id=trainee_id)

        if organization_id:
            queryset = queryset.filter(organization_id=organization_id)
        if session_type:
            queryset = queryset.filter(session_type=session_type)
        if status:
            queryset = queryset.filter(status=status)

        return queryset.order_by('-session_date', '-scheduled_start')

    @staticmethod
    def get_trainee_statistics(
        trainee_id: str,
        organization_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get summary statistics for a trainee"""
        queryset = FSTDSession.objects.filter(
            trainee_id=trainee_id,
            status='completed'
        )

        if organization_id:
            queryset = queryset.filter(organization_id=organization_id)

        totals = queryset.aggregate(
            total_sessions=Count('id'),
            total_minutes=Sum('actual_duration_minutes'),
        )

        by_type = list(
            queryset.values('session_type').annotate(
                count=Count('id'),
                total_minutes=Sum('actual_duration_minutes')
            )
        )

        by_result = list(
            queryset.values('assessment_result').annotate(count=Count('id'))
        )

        by_device = list(
            queryset.values('fstd_device_id', 'fstd_device_name').annotate(
                count=Count('id'),
                total_minutes=Sum('actual_duration_minutes')
            )
        )

        # Calculate total hours
        total_minutes = totals.get('total_minutes') or 0
        total_hours = Decimal(total_minutes) / Decimal(60)

        return {
            'trainee_id': trainee_id,
            'total_sessions': totals.get('total_sessions') or 0,
            'total_hours': str(total_hours.quantize(Decimal('0.01'))),
            'total_minutes': total_minutes,
            'by_session_type': by_type,
            'by_assessment_result': by_result,
            'by_device': by_device,
        }

    @staticmethod
    def get_instructor_sessions(
        instructor_id: str,
        organization_id: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> QuerySet:
        """Get all sessions for an instructor"""
        queryset = FSTDSession.objects.filter(instructor_id=instructor_id)

        if organization_id:
            queryset = queryset.filter(organization_id=organization_id)
        if start_date:
            queryset = queryset.filter(session_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(session_date__lte=end_date)

        return queryset.order_by('-session_date', '-scheduled_start')

    @staticmethod
    def get_device_sessions(
        device_id: str,
        organization_id: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> QuerySet:
        """Get all sessions for a device"""
        queryset = FSTDSession.objects.filter(fstd_device_id=device_id)

        if organization_id:
            queryset = queryset.filter(organization_id=organization_id)
        if start_date:
            queryset = queryset.filter(session_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(session_date__lte=end_date)

        return queryset.order_by('-session_date', '-scheduled_start')

    @staticmethod
    def calculate_session_charges(
        device: FSTDevice,
        duration_hours: Decimal,
        session_type: str,
        include_instructor: bool = True
    ) -> Dict[str, Decimal]:
        """Calculate charges for a session"""
        device_rate = device.hourly_rate or Decimal('0.00')
        device_charge = device_rate * duration_hours

        # Instructor rate could come from user service or be configurable
        instructor_charge = Decimal('0.00')

        total_charge = device_charge + instructor_charge

        return {
            'device_charge': device_charge.quantize(Decimal('0.01')),
            'instructor_charge': instructor_charge.quantize(Decimal('0.01')),
            'total_charge': total_charge.quantize(Decimal('0.01')),
            'duration_hours': duration_hours,
            'device_hourly_rate': device_rate,
        }

    @staticmethod
    def create_session(
        organization_id: str,
        fstd_device_id: str,
        trainee_id: str,
        session_date: date,
        scheduled_start: str,
        scheduled_end: str,
        session_type: str,
        instructor_id: Optional[str] = None,
        **kwargs
    ) -> FSTDSession:
        """Create a new FSTD session"""
        # Get device info for denormalization
        try:
            device = FSTDevice.objects.get(id=fstd_device_id)
            device_name = device.name
        except FSTDevice.DoesNotExist:
            device_name = ''

        session = FSTDSession.objects.create(
            organization_id=organization_id,
            fstd_device_id=fstd_device_id,
            fstd_device_name=device_name,
            trainee_id=trainee_id,
            instructor_id=instructor_id,
            session_date=session_date,
            scheduled_start=scheduled_start,
            scheduled_end=scheduled_end,
            session_type=session_type,
            status='scheduled',
            **kwargs
        )

        return session

    @staticmethod
    def get_upcoming_sessions(
        organization_id: str,
        days: int = 7,
        device_id: Optional[str] = None,
        instructor_id: Optional[str] = None,
    ) -> QuerySet:
        """Get upcoming sessions"""
        today = timezone.now().date()
        end_date = today + timedelta(days=days)

        queryset = FSTDSession.objects.filter(
            organization_id=organization_id,
            session_date__gte=today,
            session_date__lte=end_date,
            status__in=['scheduled', 'confirmed']
        )

        if device_id:
            queryset = queryset.filter(fstd_device_id=device_id)
        if instructor_id:
            queryset = queryset.filter(instructor_id=instructor_id)

        return queryset.order_by('session_date', 'scheduled_start')

    @staticmethod
    def get_today_sessions(organization_id: str) -> QuerySet:
        """Get today's sessions"""
        today = timezone.now().date()

        return FSTDSession.objects.filter(
            organization_id=organization_id,
            session_date=today
        ).order_by('scheduled_start')
