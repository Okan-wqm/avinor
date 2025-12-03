# services/flight-service/src/apps/core/services/logbook_service.py
"""
Logbook Service

Business logic for pilot logbook operations.
"""

import uuid
import logging
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import List, Dict, Any, Optional, Tuple

from django.db import transaction
from django.db.models import Q, Sum, Count, F
from django.utils import timezone
from django.core.paginator import Paginator

from ..models import (
    Flight,
    FlightCrewLog,
    PilotLogbookSummary,
    Approach,
    Hold,
)
from .exceptions import LogbookError

logger = logging.getLogger(__name__)


class LogbookService:
    """
    Service class for pilot logbook operations.

    Handles logbook entries, summaries, and exports.
    """

    # ==========================================================================
    # Logbook Summary Operations
    # ==========================================================================

    @classmethod
    def get_or_create_summary(
        cls,
        organization_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> PilotLogbookSummary:
        """
        Get or create a pilot's logbook summary.

        Args:
            organization_id: Organization UUID
            user_id: Pilot user UUID

        Returns:
            PilotLogbookSummary instance
        """
        summary, created = PilotLogbookSummary.objects.get_or_create(
            organization_id=organization_id,
            user_id=user_id,
            defaults={'last_updated': timezone.now()}
        )

        if created:
            logger.info(f"Created logbook summary for user {user_id}")

        return summary

    @classmethod
    @transaction.atomic
    def update_summary_from_flight(
        cls,
        flight: Flight,
        user_id: uuid.UUID,
        role: str
    ) -> PilotLogbookSummary:
        """
        Update pilot's logbook summary after a flight is approved.

        Args:
            flight: Approved Flight instance
            user_id: Pilot user UUID
            role: Pilot's role on the flight

        Returns:
            Updated PilotLogbookSummary instance
        """
        summary = cls.get_or_create_summary(flight.organization_id, user_id)

        # Get the crew log for this user
        try:
            crew_log = FlightCrewLog.objects.get(
                flight_id=flight.id,
                user_id=user_id
            )
        except FlightCrewLog.DoesNotExist:
            raise LogbookError(
                message=f"No crew log found for user {user_id} on flight {flight.id}",
                user_id=str(user_id)
            )

        # Update totals
        summary.total_time += crew_log.flight_time or Decimal('0')
        summary.total_pic += crew_log.time_pic
        summary.total_sic += crew_log.time_sic
        summary.total_dual_received += crew_log.time_dual_received
        summary.total_dual_given += crew_log.time_dual_given
        summary.total_solo += crew_log.time_solo

        # Condition times
        summary.total_day += crew_log.time_day
        summary.total_night += crew_log.time_night
        summary.total_ifr += crew_log.time_ifr
        summary.total_actual_instrument += crew_log.time_actual_instrument
        summary.total_simulated_instrument += crew_log.time_simulated_instrument
        summary.total_cross_country += crew_log.time_cross_country

        # Landings
        summary.total_landings_day += crew_log.landings_day
        summary.total_landings_night += crew_log.landings_night
        summary.total_full_stop_day += crew_log.full_stop_day
        summary.total_full_stop_night += crew_log.full_stop_night

        # Approaches and holds
        summary.total_approaches += crew_log.approaches
        summary.total_holds += crew_log.holds

        # Flight count
        summary.total_flights += 1

        # Update last flight date
        if not summary.last_flight_date or flight.flight_date > summary.last_flight_date:
            summary.last_flight_date = flight.flight_date

        summary.last_updated = timezone.now()
        summary.save()

        # Recalculate currency
        cls.recalculate_currency(summary)

        logger.info(f"Updated logbook summary for user {user_id} from flight {flight.id}")
        return summary

    @classmethod
    @transaction.atomic
    def recalculate_summary(
        cls,
        organization_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> PilotLogbookSummary:
        """
        Fully recalculate a pilot's logbook summary from all flights.

        Args:
            organization_id: Organization UUID
            user_id: Pilot user UUID

        Returns:
            Recalculated PilotLogbookSummary instance
        """
        summary = cls.get_or_create_summary(organization_id, user_id)

        # Reset all totals
        summary.total_time = Decimal('0')
        summary.total_pic = Decimal('0')
        summary.total_sic = Decimal('0')
        summary.total_dual_received = Decimal('0')
        summary.total_dual_given = Decimal('0')
        summary.total_solo = Decimal('0')
        summary.total_day = Decimal('0')
        summary.total_night = Decimal('0')
        summary.total_ifr = Decimal('0')
        summary.total_actual_instrument = Decimal('0')
        summary.total_simulated_instrument = Decimal('0')
        summary.total_cross_country = Decimal('0')
        summary.total_landings_day = 0
        summary.total_landings_night = 0
        summary.total_full_stop_day = 0
        summary.total_full_stop_night = 0
        summary.total_approaches = 0
        summary.total_holds = 0
        summary.total_flights = 0
        summary.last_flight_date = None

        # Aggregate from all crew logs
        crew_logs = FlightCrewLog.objects.filter(
            organization_id=organization_id,
            user_id=user_id
        ).select_related()

        # Get approved flight IDs
        approved_flight_ids = set(
            Flight.objects.filter(
                organization_id=organization_id,
                flight_status=Flight.Status.APPROVED
            ).values_list('id', flat=True)
        )

        for log in crew_logs:
            if log.flight_id not in approved_flight_ids:
                continue

            summary.total_time += log.flight_time or Decimal('0')
            summary.total_pic += log.time_pic
            summary.total_sic += log.time_sic
            summary.total_dual_received += log.time_dual_received
            summary.total_dual_given += log.time_dual_given
            summary.total_solo += log.time_solo
            summary.total_day += log.time_day
            summary.total_night += log.time_night
            summary.total_ifr += log.time_ifr
            summary.total_actual_instrument += log.time_actual_instrument
            summary.total_simulated_instrument += log.time_simulated_instrument
            summary.total_cross_country += log.time_cross_country
            summary.total_landings_day += log.landings_day
            summary.total_landings_night += log.landings_night
            summary.total_full_stop_day += log.full_stop_day
            summary.total_full_stop_night += log.full_stop_night
            summary.total_approaches += log.approaches
            summary.total_holds += log.holds
            summary.total_flights += 1

        # Get last flight date
        last_flight = Flight.objects.filter(
            organization_id=organization_id,
            flight_status=Flight.Status.APPROVED
        ).filter(
            Q(pic_id=user_id) | Q(sic_id=user_id) | Q(student_id=user_id)
        ).order_by('-flight_date').first()

        if last_flight:
            summary.last_flight_date = last_flight.flight_date

        summary.last_updated = timezone.now()
        summary.save()

        # Recalculate currency
        cls.recalculate_currency(summary)

        logger.info(f"Recalculated logbook summary for user {user_id}")
        return summary

    @classmethod
    def recalculate_currency(cls, summary: PilotLogbookSummary) -> None:
        """Recalculate currency values for a logbook summary."""
        today = date.today()
        ninety_days_ago = today - timedelta(days=90)
        six_months_ago = today - timedelta(days=180)

        # Get recent flights for this user
        recent_flights = FlightCrewLog.objects.filter(
            organization_id=summary.organization_id,
            user_id=summary.user_id,
        ).select_related()

        # Get approved flight IDs and dates
        flight_data = {
            str(f.id): f.flight_date
            for f in Flight.objects.filter(
                organization_id=summary.organization_id,
                flight_status=Flight.Status.APPROVED,
                flight_date__gte=six_months_ago
            )
        }

        # Calculate day landings in last 90 days
        day_landings_90 = 0
        night_landings_90 = 0
        ifr_approaches_6mo = 0

        for log in recent_flights:
            flight_date = flight_data.get(str(log.flight_id))
            if not flight_date:
                continue

            if flight_date >= ninety_days_ago:
                day_landings_90 += log.full_stop_day
                night_landings_90 += log.full_stop_night

            if flight_date >= six_months_ago:
                ifr_approaches_6mo += log.approaches

        summary.landings_last_90_days = day_landings_90
        summary.night_landings_last_90_days = night_landings_90
        summary.ifr_approaches_last_6_months = ifr_approaches_6mo
        summary.last_currency_check = timezone.now()
        summary.save()

    # ==========================================================================
    # Logbook Entry Operations
    # ==========================================================================

    @classmethod
    def get_logbook_entries(
        cls,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        start_date: date = None,
        end_date: date = None,
        page: int = 1,
        page_size: int = 50
    ) -> Dict[str, Any]:
        """
        Get paginated logbook entries for a pilot.

        Args:
            organization_id: Organization UUID
            user_id: Pilot user UUID
            start_date: Optional start date filter
            end_date: Optional end date filter
            page: Page number
            page_size: Items per page

        Returns:
            Dictionary with entries and pagination info
        """
        # Get crew logs for this user
        crew_logs = FlightCrewLog.objects.filter(
            organization_id=organization_id,
            user_id=user_id
        ).order_by('-created_at')

        # Get approved flight IDs
        flight_query = Flight.objects.filter(
            organization_id=organization_id,
            flight_status=Flight.Status.APPROVED
        )

        if start_date:
            flight_query = flight_query.filter(flight_date__gte=start_date)
        if end_date:
            flight_query = flight_query.filter(flight_date__lte=end_date)

        approved_flights = {
            str(f.id): f for f in flight_query
        }

        # Filter crew logs to approved flights
        valid_logs = [
            log for log in crew_logs
            if str(log.flight_id) in approved_flights
        ]

        # Paginate
        paginator = Paginator(valid_logs, page_size)
        page_obj = paginator.get_page(page)

        # Build entries with flight data
        entries = []
        for log in page_obj.object_list:
            flight = approved_flights.get(str(log.flight_id))
            if flight:
                entries.append(log.to_logbook_entry({
                    'flight_date': flight.flight_date.isoformat(),
                    'aircraft_registration': flight.aircraft_registration,
                    'aircraft_type': flight.aircraft_type,
                    'departure_airport': flight.departure_airport,
                    'arrival_airport': flight.arrival_airport,
                    'route': flight.route,
                }))

        return {
            'entries': entries,
            'total': paginator.count,
            'page': page,
            'page_size': page_size,
            'total_pages': paginator.num_pages,
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous(),
        }

    @classmethod
    def get_logbook_entry(
        cls,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        flight_id: uuid.UUID
    ) -> Optional[Dict[str, Any]]:
        """
        Get a specific logbook entry for a flight.

        Args:
            organization_id: Organization UUID
            user_id: Pilot user UUID
            flight_id: Flight UUID

        Returns:
            Logbook entry dictionary or None
        """
        try:
            crew_log = FlightCrewLog.objects.get(
                organization_id=organization_id,
                user_id=user_id,
                flight_id=flight_id
            )

            flight = Flight.objects.get(
                id=flight_id,
                organization_id=organization_id,
                flight_status=Flight.Status.APPROVED
            )

            return crew_log.to_logbook_entry({
                'flight_date': flight.flight_date.isoformat(),
                'aircraft_registration': flight.aircraft_registration,
                'aircraft_type': flight.aircraft_type,
                'departure_airport': flight.departure_airport,
                'arrival_airport': flight.arrival_airport,
                'route': flight.route,
            })

        except (FlightCrewLog.DoesNotExist, Flight.DoesNotExist):
            return None

    @classmethod
    @transaction.atomic
    def update_logbook_remarks(
        cls,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        flight_id: uuid.UUID,
        remarks: str
    ) -> FlightCrewLog:
        """
        Update personal remarks for a logbook entry.

        Args:
            organization_id: Organization UUID
            user_id: Pilot user UUID
            flight_id: Flight UUID
            remarks: New remarks text

        Returns:
            Updated FlightCrewLog instance
        """
        try:
            crew_log = FlightCrewLog.objects.get(
                organization_id=organization_id,
                user_id=user_id,
                flight_id=flight_id
            )

            crew_log.remarks = remarks
            crew_log.save()

            return crew_log

        except FlightCrewLog.DoesNotExist:
            raise LogbookError(
                message=f"Logbook entry not found for flight {flight_id}",
                user_id=str(user_id)
            )

    @classmethod
    @transaction.atomic
    def sign_logbook_entry(
        cls,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        flight_id: uuid.UUID,
        signature_data: Dict[str, Any]
    ) -> FlightCrewLog:
        """
        Sign a logbook entry.

        Args:
            organization_id: Organization UUID
            user_id: Pilot user UUID
            flight_id: Flight UUID
            signature_data: Signature data

        Returns:
            Updated FlightCrewLog instance
        """
        try:
            crew_log = FlightCrewLog.objects.get(
                organization_id=organization_id,
                user_id=user_id,
                flight_id=flight_id
            )

            crew_log.sign(signature_data)
            return crew_log

        except FlightCrewLog.DoesNotExist:
            raise LogbookError(
                message=f"Logbook entry not found for flight {flight_id}",
                user_id=str(user_id)
            )

    # ==========================================================================
    # Logbook Export Operations
    # ==========================================================================

    @classmethod
    def export_logbook(
        cls,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        format: str = 'json',
        start_date: date = None,
        end_date: date = None
    ) -> Dict[str, Any]:
        """
        Export pilot logbook in various formats.

        Args:
            organization_id: Organization UUID
            user_id: Pilot user UUID
            format: Export format ('json', 'csv', 'pdf')
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            Export data dictionary
        """
        # Get all entries (no pagination for export)
        all_entries = cls._get_all_entries(
            organization_id, user_id, start_date, end_date
        )

        # Get summary
        summary = cls.get_or_create_summary(organization_id, user_id)

        export_data = {
            'pilot_id': str(user_id),
            'organization_id': str(organization_id),
            'exported_at': timezone.now().isoformat(),
            'date_range': {
                'start': start_date.isoformat() if start_date else None,
                'end': end_date.isoformat() if end_date else None,
            },
            'summary': {
                'total_time': float(summary.total_time),
                'total_pic': float(summary.total_pic),
                'total_sic': float(summary.total_sic),
                'total_dual_received': float(summary.total_dual_received),
                'total_dual_given': float(summary.total_dual_given),
                'total_solo': float(summary.total_solo),
                'total_day': float(summary.total_day),
                'total_night': float(summary.total_night),
                'total_ifr': float(summary.total_ifr),
                'total_cross_country': float(summary.total_cross_country),
                'total_landings_day': summary.total_landings_day,
                'total_landings_night': summary.total_landings_night,
                'total_approaches': summary.total_approaches,
                'total_flights': summary.total_flights,
            },
            'entries': all_entries,
        }

        return export_data

    @classmethod
    def _get_all_entries(
        cls,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        start_date: date = None,
        end_date: date = None
    ) -> List[Dict[str, Any]]:
        """Get all logbook entries without pagination."""
        # Get approved flights
        flight_query = Flight.objects.filter(
            organization_id=organization_id,
            flight_status=Flight.Status.APPROVED
        )

        if start_date:
            flight_query = flight_query.filter(flight_date__gte=start_date)
        if end_date:
            flight_query = flight_query.filter(flight_date__lte=end_date)

        approved_flights = {str(f.id): f for f in flight_query}

        # Get crew logs
        crew_logs = FlightCrewLog.objects.filter(
            organization_id=organization_id,
            user_id=user_id
        ).order_by('created_at')

        entries = []
        for log in crew_logs:
            flight = approved_flights.get(str(log.flight_id))
            if flight:
                entries.append(log.to_logbook_entry({
                    'flight_date': flight.flight_date.isoformat(),
                    'aircraft_registration': flight.aircraft_registration,
                    'aircraft_type': flight.aircraft_type,
                    'departure_airport': flight.departure_airport,
                    'arrival_airport': flight.arrival_airport,
                    'route': flight.route,
                }))

        return entries

    # ==========================================================================
    # Batch Operations
    # ==========================================================================

    @classmethod
    @transaction.atomic
    def recalculate_all_summaries(
        cls,
        organization_id: uuid.UUID
    ) -> int:
        """
        Recalculate all pilot logbook summaries for an organization.

        Args:
            organization_id: Organization UUID

        Returns:
            Number of summaries recalculated
        """
        # Get all unique user IDs from crew logs
        user_ids = FlightCrewLog.objects.filter(
            organization_id=organization_id
        ).values_list('user_id', flat=True).distinct()

        count = 0
        for user_id in user_ids:
            cls.recalculate_summary(organization_id, user_id)
            count += 1

        logger.info(f"Recalculated {count} logbook summaries for organization {organization_id}")
        return count
