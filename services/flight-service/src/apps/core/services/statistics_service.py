# services/flight-service/src/apps/core/services/statistics_service.py
"""
Statistics Service

Business logic for flight statistics and analytics.
"""

import uuid
import logging
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict

from django.db import transaction
from django.db.models import Q, Sum, Count, Avg, F, Max, Min
from django.db.models.functions import TruncMonth, TruncWeek, TruncYear
from django.utils import timezone

from ..models import (
    Flight,
    FlightCrewLog,
    PilotLogbookSummary,
    Approach,
    Hold,
    FuelRecord,
)
from .exceptions import StatisticsError

logger = logging.getLogger(__name__)


class StatisticsService:
    """
    Service class for flight statistics and analytics.

    Provides comprehensive statistics for pilots, aircraft, and organizations.
    """

    # ==========================================================================
    # Pilot Statistics
    # ==========================================================================

    @classmethod
    def get_pilot_statistics(
        cls,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        start_date: date = None,
        end_date: date = None
    ) -> Dict[str, Any]:
        """
        Get comprehensive statistics for a pilot.

        Args:
            organization_id: Organization UUID
            user_id: Pilot user UUID
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            Dictionary with pilot statistics
        """
        # Build query
        query = Flight.objects.filter(
            organization_id=organization_id,
            flight_status=Flight.Status.APPROVED
        ).filter(
            Q(pic_id=user_id) | Q(sic_id=user_id) | Q(student_id=user_id)
        )

        if start_date:
            query = query.filter(flight_date__gte=start_date)
        if end_date:
            query = query.filter(flight_date__lte=end_date)

        # Get crew logs for this user
        crew_logs = FlightCrewLog.objects.filter(
            organization_id=organization_id,
            user_id=user_id,
            flight_id__in=query.values_list('id', flat=True)
        )

        # Aggregate times from crew logs
        time_stats = crew_logs.aggregate(
            total_time=Sum('flight_time'),
            total_pic=Sum('time_pic'),
            total_sic=Sum('time_sic'),
            total_dual_received=Sum('time_dual_received'),
            total_dual_given=Sum('time_dual_given'),
            total_solo=Sum('time_solo'),
            total_day=Sum('time_day'),
            total_night=Sum('time_night'),
            total_ifr=Sum('time_ifr'),
            total_actual_instrument=Sum('time_actual_instrument'),
            total_simulated_instrument=Sum('time_simulated_instrument'),
            total_cross_country=Sum('time_cross_country'),
            total_landings_day=Sum('landings_day'),
            total_landings_night=Sum('landings_night'),
            total_approaches=Sum('approaches'),
            total_holds=Sum('holds'),
        )

        # Flight counts
        flight_count = query.count()

        # Flights by type
        by_type = list(query.values('flight_type').annotate(
            count=Count('id'),
            total_time=Sum('flight_time')
        ).order_by('-count'))

        # Flights by rules
        by_rules = list(query.values('flight_rules').annotate(
            count=Count('id'),
            total_time=Sum('flight_time')
        ).order_by('-count'))

        # Aircraft statistics
        by_aircraft = list(query.values(
            'aircraft_id', 'aircraft_registration', 'aircraft_type'
        ).annotate(
            flights=Count('id'),
            total_time=Sum('flight_time')
        ).order_by('-total_time')[:10])

        # Airport statistics
        departures = list(query.values('departure_airport').annotate(
            count=Count('id')
        ).order_by('-count')[:10])

        arrivals = list(query.values('arrival_airport').annotate(
            count=Count('id')
        ).order_by('-count')[:10])

        # Monthly trend
        monthly_trend = cls._get_monthly_trend(query)

        return {
            'user_id': str(user_id),
            'period': {
                'start': start_date.isoformat() if start_date else None,
                'end': end_date.isoformat() if end_date else None,
            },
            'summary': {
                'total_flights': flight_count,
                'total_time': float(time_stats['total_time'] or 0),
                'total_pic': float(time_stats['total_pic'] or 0),
                'total_sic': float(time_stats['total_sic'] or 0),
                'total_dual_received': float(time_stats['total_dual_received'] or 0),
                'total_dual_given': float(time_stats['total_dual_given'] or 0),
                'total_solo': float(time_stats['total_solo'] or 0),
                'total_day': float(time_stats['total_day'] or 0),
                'total_night': float(time_stats['total_night'] or 0),
                'total_ifr': float(time_stats['total_ifr'] or 0),
                'total_instrument': float(
                    (time_stats['total_actual_instrument'] or 0) +
                    (time_stats['total_simulated_instrument'] or 0)
                ),
                'total_cross_country': float(time_stats['total_cross_country'] or 0),
                'total_landings': (
                    (time_stats['total_landings_day'] or 0) +
                    (time_stats['total_landings_night'] or 0)
                ),
                'total_approaches': time_stats['total_approaches'] or 0,
                'total_holds': time_stats['total_holds'] or 0,
            },
            'by_flight_type': by_type,
            'by_flight_rules': by_rules,
            'by_aircraft': by_aircraft,
            'top_departure_airports': departures,
            'top_arrival_airports': arrivals,
            'monthly_trend': monthly_trend,
        }

    @classmethod
    def get_pilot_approach_statistics(
        cls,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        start_date: date = None,
        end_date: date = None
    ) -> Dict[str, Any]:
        """Get detailed approach statistics for a pilot."""
        # Get flight IDs
        flight_query = Flight.objects.filter(
            organization_id=organization_id,
            flight_status=Flight.Status.APPROVED
        ).filter(
            Q(pic_id=user_id) | Q(student_id=user_id)
        )

        if start_date:
            flight_query = flight_query.filter(flight_date__gte=start_date)
        if end_date:
            flight_query = flight_query.filter(flight_date__lte=end_date)

        flight_ids = flight_query.values_list('id', flat=True)

        # Get approach statistics
        return Approach.get_approach_statistics(
            organization_id=organization_id,
            pilot_id=user_id,
            start_date=start_date,
            end_date=end_date
        )

    # ==========================================================================
    # Aircraft Statistics
    # ==========================================================================

    @classmethod
    def get_aircraft_statistics(
        cls,
        organization_id: uuid.UUID,
        aircraft_id: uuid.UUID,
        start_date: date = None,
        end_date: date = None
    ) -> Dict[str, Any]:
        """
        Get comprehensive statistics for an aircraft.

        Args:
            organization_id: Organization UUID
            aircraft_id: Aircraft UUID
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            Dictionary with aircraft statistics
        """
        query = Flight.objects.filter(
            organization_id=organization_id,
            aircraft_id=aircraft_id,
            flight_status=Flight.Status.APPROVED
        )

        if start_date:
            query = query.filter(flight_date__gte=start_date)
        if end_date:
            query = query.filter(flight_date__lte=end_date)

        # Aggregate statistics
        stats = query.aggregate(
            total_flights=Count('id'),
            total_flight_time=Sum('flight_time'),
            total_block_time=Sum('block_time'),
            total_hobbs=Sum('hobbs_end') - Sum('hobbs_start'),
            total_tach=Sum('tach_end') - Sum('tach_start'),
            total_landings=Sum('landings_day') + Sum('landings_night'),
            total_fuel=Sum('fuel_added_liters'),
            total_fuel_cost=Sum('fuel_cost'),
            avg_flight_time=Avg('flight_time'),
        )

        # By flight type
        by_type = list(query.values('flight_type').annotate(
            count=Count('id'),
            total_time=Sum('flight_time')
        ).order_by('-count'))

        # By pilot
        by_pilot = list(query.values('pic_id').annotate(
            flights=Count('id'),
            total_time=Sum('flight_time')
        ).order_by('-total_time')[:10])

        # Top routes
        top_routes = list(query.values(
            'departure_airport', 'arrival_airport'
        ).annotate(
            count=Count('id')
        ).order_by('-count')[:10])

        # Monthly utilization
        monthly = cls._get_monthly_trend(query)

        # Last flight info
        last_flight = query.order_by('-flight_date').first()

        return {
            'aircraft_id': str(aircraft_id),
            'period': {
                'start': start_date.isoformat() if start_date else None,
                'end': end_date.isoformat() if end_date else None,
            },
            'summary': {
                'total_flights': stats['total_flights'] or 0,
                'total_flight_time': float(stats['total_flight_time'] or 0),
                'total_block_time': float(stats['total_block_time'] or 0),
                'total_hobbs': float(stats['total_hobbs'] or 0),
                'total_tach': float(stats['total_tach'] or 0),
                'total_landings': stats['total_landings'] or 0,
                'total_fuel_liters': float(stats['total_fuel'] or 0),
                'total_fuel_cost': float(stats['total_fuel_cost'] or 0),
                'avg_flight_time': float(stats['avg_flight_time'] or 0),
            },
            'by_flight_type': by_type,
            'by_pilot': by_pilot,
            'top_routes': top_routes,
            'monthly_utilization': monthly,
            'last_flight': {
                'id': str(last_flight.id),
                'date': last_flight.flight_date.isoformat(),
                'flight_time': float(last_flight.flight_time or 0),
            } if last_flight else None,
        }

    @classmethod
    def get_aircraft_fuel_statistics(
        cls,
        organization_id: uuid.UUID,
        aircraft_id: uuid.UUID,
        start_date: date = None,
        end_date: date = None
    ) -> Dict[str, Any]:
        """Get detailed fuel statistics for an aircraft."""
        query = FuelRecord.objects.filter(
            organization_id=organization_id,
            aircraft_id=aircraft_id
        )

        if start_date:
            query = query.filter(recorded_at__date__gte=start_date)
        if end_date:
            query = query.filter(recorded_at__date__lte=end_date)

        # Uplift statistics
        uplifts = query.filter(record_type=FuelRecord.RecordType.UPLIFT)

        uplift_stats = uplifts.aggregate(
            total_quantity=Sum('quantity_liters'),
            total_cost=Sum('total_cost'),
            avg_price=Avg('price_per_liter'),
            count=Count('id'),
        )

        # By location
        by_location = list(uplifts.values('location_icao').annotate(
            total_quantity=Sum('quantity_liters'),
            total_cost=Sum('total_cost'),
            count=Count('id'),
            avg_price=Avg('price_per_liter')
        ).order_by('-total_quantity')[:10])

        # By fuel type
        by_type = list(uplifts.values('fuel_type').annotate(
            total_quantity=Sum('quantity_liters'),
            total_cost=Sum('total_cost'),
            count=Count('id')
        ).order_by('-total_quantity'))

        # Monthly trend
        monthly = list(uplifts.annotate(
            month=TruncMonth('recorded_at')
        ).values('month').annotate(
            total_quantity=Sum('quantity_liters'),
            total_cost=Sum('total_cost'),
            count=Count('id')
        ).order_by('month'))

        return {
            'aircraft_id': str(aircraft_id),
            'period': {
                'start': start_date.isoformat() if start_date else None,
                'end': end_date.isoformat() if end_date else None,
            },
            'summary': {
                'total_uplifts': uplift_stats['count'] or 0,
                'total_quantity_liters': float(uplift_stats['total_quantity'] or 0),
                'total_cost': float(uplift_stats['total_cost'] or 0),
                'avg_price_per_liter': float(uplift_stats['avg_price'] or 0),
            },
            'by_location': by_location,
            'by_fuel_type': by_type,
            'monthly_trend': monthly,
        }

    # ==========================================================================
    # Organization Statistics
    # ==========================================================================

    @classmethod
    def get_organization_statistics(
        cls,
        organization_id: uuid.UUID,
        start_date: date = None,
        end_date: date = None
    ) -> Dict[str, Any]:
        """
        Get comprehensive statistics for an organization.

        Args:
            organization_id: Organization UUID
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            Dictionary with organization statistics
        """
        query = Flight.objects.filter(
            organization_id=organization_id,
            flight_status=Flight.Status.APPROVED
        )

        if start_date:
            query = query.filter(flight_date__gte=start_date)
        if end_date:
            query = query.filter(flight_date__lte=end_date)

        # Overall statistics
        stats = query.aggregate(
            total_flights=Count('id'),
            total_flight_time=Sum('flight_time'),
            total_block_time=Sum('block_time'),
            total_landings=Sum('landings_day') + Sum('landings_night'),
            total_fuel=Sum('fuel_added_liters'),
            total_fuel_cost=Sum('fuel_cost'),
            avg_flight_time=Avg('flight_time'),
        )

        # By flight type
        by_type = list(query.values('flight_type').annotate(
            count=Count('id'),
            total_time=Sum('flight_time'),
            percentage=Count('id') * 100.0 / (query.count() or 1)
        ).order_by('-count'))

        # By aircraft
        by_aircraft = list(query.values(
            'aircraft_id', 'aircraft_registration', 'aircraft_type'
        ).annotate(
            flights=Count('id'),
            total_time=Sum('flight_time')
        ).order_by('-total_time')[:10])

        # By pilot (PIC)
        by_pilot = list(query.filter(pic_id__isnull=False).values('pic_id').annotate(
            flights=Count('id'),
            total_time=Sum('flight_time')
        ).order_by('-total_time')[:10])

        # By instructor
        by_instructor = list(query.filter(instructor_id__isnull=False).values(
            'instructor_id'
        ).annotate(
            flights=Count('id'),
            total_time=Sum('flight_time')
        ).order_by('-total_time')[:10])

        # Top routes
        top_routes = list(query.values(
            'departure_airport', 'arrival_airport'
        ).annotate(
            count=Count('id')
        ).order_by('-count')[:10])

        # Monthly trend
        monthly = cls._get_monthly_trend(query)

        # Active counts
        unique_pilots = query.values('pic_id').distinct().count()
        unique_aircraft = query.values('aircraft_id').distinct().count()

        return {
            'organization_id': str(organization_id),
            'period': {
                'start': start_date.isoformat() if start_date else None,
                'end': end_date.isoformat() if end_date else None,
            },
            'summary': {
                'total_flights': stats['total_flights'] or 0,
                'total_flight_time': float(stats['total_flight_time'] or 0),
                'total_block_time': float(stats['total_block_time'] or 0),
                'total_landings': stats['total_landings'] or 0,
                'total_fuel_liters': float(stats['total_fuel'] or 0),
                'total_fuel_cost': float(stats['total_fuel_cost'] or 0),
                'avg_flight_time': float(stats['avg_flight_time'] or 0),
                'active_pilots': unique_pilots,
                'active_aircraft': unique_aircraft,
            },
            'by_flight_type': by_type,
            'by_aircraft': by_aircraft,
            'by_pilot': by_pilot,
            'by_instructor': by_instructor,
            'top_routes': top_routes,
            'monthly_trend': monthly,
        }

    @classmethod
    def get_organization_training_statistics(
        cls,
        organization_id: uuid.UUID,
        start_date: date = None,
        end_date: date = None
    ) -> Dict[str, Any]:
        """Get training-specific statistics for an organization."""
        query = Flight.objects.filter(
            organization_id=organization_id,
            flight_status=Flight.Status.APPROVED,
            flight_type=Flight.FlightType.TRAINING
        )

        if start_date:
            query = query.filter(flight_date__gte=start_date)
        if end_date:
            query = query.filter(flight_date__lte=end_date)

        # Training type breakdown
        by_training_type = list(query.values('training_type').annotate(
            count=Count('id'),
            total_time=Sum('flight_time'),
            total_dual=Sum('time_dual_received')
        ).order_by('-count'))

        # By instructor
        by_instructor = list(query.filter(instructor_id__isnull=False).values(
            'instructor_id'
        ).annotate(
            flights=Count('id'),
            total_time=Sum('flight_time'),
            students=Count('student_id', distinct=True)
        ).order_by('-total_time'))

        # By student
        by_student = list(query.filter(student_id__isnull=False).values(
            'student_id'
        ).annotate(
            flights=Count('id'),
            total_time=Sum('flight_time'),
            total_dual=Sum('time_dual_received')
        ).order_by('-total_time'))

        # Training stats
        stats = query.aggregate(
            total_flights=Count('id'),
            total_time=Sum('flight_time'),
            total_dual=Sum('time_dual_received'),
            avg_flight_time=Avg('flight_time'),
        )

        return {
            'organization_id': str(organization_id),
            'period': {
                'start': start_date.isoformat() if start_date else None,
                'end': end_date.isoformat() if end_date else None,
            },
            'summary': {
                'total_training_flights': stats['total_flights'] or 0,
                'total_training_time': float(stats['total_time'] or 0),
                'total_dual_time': float(stats['total_dual'] or 0),
                'avg_flight_time': float(stats['avg_flight_time'] or 0),
                'active_instructors': query.values('instructor_id').distinct().count(),
                'active_students': query.values('student_id').distinct().count(),
            },
            'by_training_type': by_training_type,
            'by_instructor': by_instructor,
            'by_student': by_student,
        }

    # ==========================================================================
    # Dashboard Statistics
    # ==========================================================================

    @classmethod
    def get_dashboard_statistics(
        cls,
        organization_id: uuid.UUID,
        user_id: uuid.UUID = None
    ) -> Dict[str, Any]:
        """
        Get dashboard statistics for quick overview.

        Args:
            organization_id: Organization UUID
            user_id: Optional user UUID for user-specific stats

        Returns:
            Dictionary with dashboard statistics
        """
        today = date.today()
        thirty_days_ago = today - timedelta(days=30)
        seven_days_ago = today - timedelta(days=7)

        # Base query
        base_query = Flight.objects.filter(organization_id=organization_id)

        if user_id:
            base_query = base_query.filter(
                Q(pic_id=user_id) | Q(sic_id=user_id) | Q(student_id=user_id)
            )

        approved_query = base_query.filter(flight_status=Flight.Status.APPROVED)

        # Recent stats (30 days)
        recent_stats = approved_query.filter(
            flight_date__gte=thirty_days_ago
        ).aggregate(
            flights=Count('id'),
            flight_time=Sum('flight_time'),
            landings=Sum('landings_day') + Sum('landings_night'),
        )

        # This week stats
        week_stats = approved_query.filter(
            flight_date__gte=seven_days_ago
        ).aggregate(
            flights=Count('id'),
            flight_time=Sum('flight_time'),
        )

        # Pending items
        pending_approval = base_query.filter(
            flight_status__in=[Flight.Status.SUBMITTED, Flight.Status.PENDING_REVIEW]
        ).count()

        pending_signature = 0
        if user_id:
            pending_signature = base_query.filter(
                flight_status__in=[Flight.Status.DRAFT, Flight.Status.SUBMITTED]
            ).filter(
                Q(pic_id=user_id, pic_signed_at__isnull=True) |
                Q(instructor_id=user_id, instructor_signed_at__isnull=True) |
                Q(student_id=user_id, student_signed_at__isnull=True)
            ).count()

        # Recent flights
        recent_flights = list(approved_query.order_by('-flight_date')[:5].values(
            'id', 'flight_date', 'aircraft_registration',
            'departure_airport', 'arrival_airport', 'flight_time'
        ))

        return {
            'organization_id': str(organization_id),
            'user_id': str(user_id) if user_id else None,
            'generated_at': timezone.now().isoformat(),
            'last_30_days': {
                'flights': recent_stats['flights'] or 0,
                'flight_time': float(recent_stats['flight_time'] or 0),
                'landings': recent_stats['landings'] or 0,
            },
            'last_7_days': {
                'flights': week_stats['flights'] or 0,
                'flight_time': float(week_stats['flight_time'] or 0),
            },
            'pending': {
                'approval': pending_approval,
                'signature': pending_signature,
            },
            'recent_flights': recent_flights,
        }

    # ==========================================================================
    # Private Helper Methods
    # ==========================================================================

    @classmethod
    def _get_monthly_trend(cls, queryset) -> List[Dict[str, Any]]:
        """Get monthly trend data from queryset."""
        return list(queryset.annotate(
            month=TruncMonth('flight_date')
        ).values('month').annotate(
            flights=Count('id'),
            total_time=Sum('flight_time'),
            total_landings=Sum('landings_day') + Sum('landings_night'),
        ).order_by('month'))

    @classmethod
    def _get_weekly_trend(cls, queryset) -> List[Dict[str, Any]]:
        """Get weekly trend data from queryset."""
        return list(queryset.annotate(
            week=TruncWeek('flight_date')
        ).values('week').annotate(
            flights=Count('id'),
            total_time=Sum('flight_time'),
        ).order_by('week'))

    # ==========================================================================
    # Comparison Statistics
    # ==========================================================================

    @classmethod
    def get_period_comparison(
        cls,
        organization_id: uuid.UUID,
        period_1_start: date,
        period_1_end: date,
        period_2_start: date,
        period_2_end: date,
        user_id: uuid.UUID = None
    ) -> Dict[str, Any]:
        """
        Compare statistics between two periods.

        Args:
            organization_id: Organization UUID
            period_1_start: First period start date
            period_1_end: First period end date
            period_2_start: Second period start date
            period_2_end: Second period end date
            user_id: Optional user filter

        Returns:
            Dictionary with comparison data
        """
        def get_period_stats(start: date, end: date):
            query = Flight.objects.filter(
                organization_id=organization_id,
                flight_status=Flight.Status.APPROVED,
                flight_date__gte=start,
                flight_date__lte=end
            )

            if user_id:
                query = query.filter(
                    Q(pic_id=user_id) | Q(sic_id=user_id) | Q(student_id=user_id)
                )

            return query.aggregate(
                flights=Count('id'),
                flight_time=Sum('flight_time'),
                landings=Sum('landings_day') + Sum('landings_night'),
                fuel=Sum('fuel_added_liters'),
            )

        period_1 = get_period_stats(period_1_start, period_1_end)
        period_2 = get_period_stats(period_2_start, period_2_end)

        def calc_change(val1, val2):
            if not val1 or val1 == 0:
                return None
            return ((val2 or 0) - val1) / val1 * 100

        return {
            'organization_id': str(organization_id),
            'user_id': str(user_id) if user_id else None,
            'period_1': {
                'start': period_1_start.isoformat(),
                'end': period_1_end.isoformat(),
                'flights': period_1['flights'] or 0,
                'flight_time': float(period_1['flight_time'] or 0),
                'landings': period_1['landings'] or 0,
                'fuel': float(period_1['fuel'] or 0),
            },
            'period_2': {
                'start': period_2_start.isoformat(),
                'end': period_2_end.isoformat(),
                'flights': period_2['flights'] or 0,
                'flight_time': float(period_2['flight_time'] or 0),
                'landings': period_2['landings'] or 0,
                'fuel': float(period_2['fuel'] or 0),
            },
            'changes': {
                'flights': calc_change(period_1['flights'], period_2['flights']),
                'flight_time': calc_change(period_1['flight_time'], period_2['flight_time']),
                'landings': calc_change(period_1['landings'], period_2['landings']),
                'fuel': calc_change(period_1['fuel'], period_2['fuel']),
            }
        }
