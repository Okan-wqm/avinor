# services/flight-service/src/apps/api/views/logbook_views.py
"""
Logbook Views

REST API views for pilot logbook operations.
"""

import logging
from uuid import UUID

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.services import LogbookService
from apps.core.services.exceptions import FlightValidationError
from apps.api.serializers import (
    FlightCrewLogSerializer,
    LogbookEntrySerializer,
    LogbookSummarySerializer,
    LogbookExportSerializer,
)
from apps.api.serializers.logbook_serializers import (
    LogbookRemarksSerializer,
    LogbookSignatureSerializer,
    LogbookPaginatedSerializer,
    FlightCrewLogUpdateSerializer,
)
from .base import BaseFlightViewSet, PaginationMixin, DateRangeMixin

logger = logging.getLogger(__name__)


class LogbookViewSet(BaseFlightViewSet, PaginationMixin, DateRangeMixin):
    """
    ViewSet for pilot logbook operations.

    Handles logbook entries, summaries, and exports.
    """

    # ==========================================================================
    # Logbook Entries
    # ==========================================================================

    def list(self, request):
        """
        List logbook entries for a pilot.

        GET /api/v1/logbook/
        """
        organization_id = self.get_organization_id()
        user_id = self.get_user_id()
        page, page_size = self.get_pagination_params()
        start_date, end_date = self.get_date_range()

        result = LogbookService.get_logbook_entries(
            organization_id=organization_id,
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            page=page,
            page_size=page_size
        )

        return Response({
            'entries': result['entries'],
            'total': result['total'],
            'page': result['page'],
            'page_size': result['page_size'],
            'total_pages': result['total_pages'],
            'has_next': result['has_next'],
            'has_previous': result['has_previous'],
        })

    def retrieve(self, request, pk=None):
        """
        Retrieve a specific logbook entry.

        GET /api/v1/logbook/{flight_id}/
        """
        organization_id = self.get_organization_id()
        user_id = self.get_user_id()

        entry = LogbookService.get_logbook_entry(
            organization_id=organization_id,
            user_id=user_id,
            flight_id=UUID(pk)
        )

        if not entry:
            raise FlightValidationError(
                message=f"Logbook entry not found for flight: {pk}",
                field="flight_id"
            )

        return Response(entry)

    # ==========================================================================
    # Summary
    # ==========================================================================

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """
        Get pilot logbook summary.

        GET /api/v1/logbook/summary/
        """
        organization_id = self.get_organization_id()
        user_id = self.get_user_id()

        # Check for optional pilot_id parameter (for viewing other pilots)
        pilot_id = request.query_params.get('pilot_id')
        if pilot_id:
            pilot_id = UUID(pilot_id)
        else:
            pilot_id = user_id

        summary = LogbookService.get_or_create_summary(
            organization_id=organization_id,
            user_id=pilot_id
        )

        serializer = LogbookSummarySerializer(summary)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def recalculate(self, request):
        """
        Recalculate pilot logbook summary.

        POST /api/v1/logbook/recalculate/
        """
        organization_id = self.get_organization_id()
        user_id = self.get_user_id()

        # Check for optional pilot_id parameter
        pilot_id = request.data.get('pilot_id')
        if pilot_id:
            pilot_id = UUID(pilot_id)
        else:
            pilot_id = user_id

        summary = LogbookService.recalculate_summary(
            organization_id=organization_id,
            user_id=pilot_id
        )

        serializer = LogbookSummarySerializer(summary)
        return Response(serializer.data)

    # ==========================================================================
    # Remarks and Signatures
    # ==========================================================================

    @action(detail=True, methods=['patch'])
    def remarks(self, request, pk=None):
        """
        Update logbook entry remarks.

        PATCH /api/v1/logbook/{flight_id}/remarks/
        """
        organization_id = self.get_organization_id()
        user_id = self.get_user_id()

        serializer = LogbookRemarksSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        crew_log = LogbookService.update_logbook_remarks(
            organization_id=organization_id,
            user_id=user_id,
            flight_id=UUID(pk),
            remarks=serializer.validated_data['remarks']
        )

        response_serializer = FlightCrewLogSerializer(crew_log)
        return Response(response_serializer.data)

    @action(detail=True, methods=['post'])
    def sign(self, request, pk=None):
        """
        Sign a logbook entry.

        POST /api/v1/logbook/{flight_id}/sign/
        """
        organization_id = self.get_organization_id()
        user_id = self.get_user_id()

        serializer = LogbookSignatureSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        crew_log = LogbookService.sign_logbook_entry(
            organization_id=organization_id,
            user_id=user_id,
            flight_id=UUID(pk),
            signature_data=serializer.validated_data['signature_data']
        )

        response_serializer = FlightCrewLogSerializer(crew_log)
        return Response(response_serializer.data)

    # ==========================================================================
    # Export
    # ==========================================================================

    @action(detail=False, methods=['get'])
    def export(self, request):
        """
        Export pilot logbook.

        GET /api/v1/logbook/export/?format={json|csv|pdf}
        """
        organization_id = self.get_organization_id()
        user_id = self.get_user_id()

        serializer = LogbookExportSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        export_format = serializer.validated_data.get('format', 'json')
        start_date = serializer.validated_data.get('start_date')
        end_date = serializer.validated_data.get('end_date')

        export_data = LogbookService.export_logbook(
            organization_id=organization_id,
            user_id=user_id,
            format=export_format,
            start_date=start_date,
            end_date=end_date
        )

        if export_format == 'json':
            return Response(export_data)
        elif export_format == 'csv':
            # Generate CSV
            import csv
            from io import StringIO
            from django.http import HttpResponse

            output = StringIO()
            writer = csv.writer(output)

            # Header
            writer.writerow([
                'Date', 'Aircraft', 'Type', 'Departure', 'Arrival', 'Route',
                'Role', 'Total Time', 'PIC', 'SIC', 'Dual Received', 'Dual Given',
                'Solo', 'Day', 'Night', 'IFR', 'XC', 'Landings Day', 'Landings Night',
                'Approaches', 'Holds', 'Remarks'
            ])

            # Data rows
            for entry in export_data['entries']:
                writer.writerow([
                    entry['date'],
                    entry['aircraft'],
                    entry['aircraft_type'],
                    entry['departure'],
                    entry['arrival'],
                    entry.get('route', ''),
                    entry['role'],
                    entry['flight_time'],
                    entry['time_pic'],
                    entry['time_sic'],
                    entry['time_dual_received'],
                    entry['time_dual_given'],
                    entry['time_solo'],
                    entry['time_day'],
                    entry['time_night'],
                    entry['time_ifr'],
                    entry['time_cross_country'],
                    entry['landings_day'],
                    entry['landings_night'],
                    entry['approaches'],
                    entry['holds'],
                    entry.get('remarks', ''),
                ])

            response = HttpResponse(
                output.getvalue(),
                content_type='text/csv'
            )
            response['Content-Disposition'] = 'attachment; filename="logbook.csv"'
            return response

        elif export_format == 'pdf':
            # PDF generation would require additional library (reportlab, weasyprint, etc.)
            # For now, return JSON with a note
            return Response({
                'message': 'PDF export not yet implemented',
                'data': export_data
            })

        return Response(export_data)

    # ==========================================================================
    # Batch Operations
    # ==========================================================================

    @action(detail=False, methods=['post'])
    def recalculate_all(self, request):
        """
        Recalculate all logbook summaries for organization.

        POST /api/v1/logbook/recalculate_all/
        """
        organization_id = self.get_organization_id()

        count = LogbookService.recalculate_all_summaries(
            organization_id=organization_id
        )

        return Response({
            'message': f'Recalculated {count} logbook summaries',
            'count': count
        })

    # ==========================================================================
    # Other Pilot's Logbook (for instructors/admins)
    # ==========================================================================

    @action(detail=False, methods=['get'])
    def for_pilot(self, request):
        """
        Get logbook entries for a specific pilot.

        GET /api/v1/logbook/for_pilot/?pilot_id={uuid}
        """
        organization_id = self.get_organization_id()
        page, page_size = self.get_pagination_params()
        start_date, end_date = self.get_date_range()

        pilot_id = request.query_params.get('pilot_id')
        if not pilot_id:
            raise FlightValidationError(
                message="pilot_id is required",
                field="pilot_id"
            )

        result = LogbookService.get_logbook_entries(
            organization_id=organization_id,
            user_id=UUID(pilot_id),
            start_date=start_date,
            end_date=end_date,
            page=page,
            page_size=page_size
        )

        return Response({
            'pilot_id': pilot_id,
            'entries': result['entries'],
            'total': result['total'],
            'page': result['page'],
            'page_size': result['page_size'],
            'total_pages': result['total_pages'],
            'has_next': result['has_next'],
            'has_previous': result['has_previous'],
        })
