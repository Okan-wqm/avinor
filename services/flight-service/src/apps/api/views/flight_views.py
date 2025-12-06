# services/flight-service/src/apps/api/views/flight_views.py
"""
Flight Views

REST API views for flight management operations.
"""

import logging
from uuid import UUID

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.services import FlightService
from apps.core.services.exceptions import FlightValidationError
from apps.api.serializers import (
    FlightListSerializer,
    FlightDetailSerializer,
    FlightCreateSerializer,
    FlightUpdateSerializer,
    FlightSubmitSerializer,
    FlightApproveSerializer,
    FlightRejectSerializer,
    FlightSignatureSerializer,
)
from apps.api.serializers.flight_serializers import (
    FlightCancelSerializer,
    FlightSquawkSerializer,
    FlightBulkActionSerializer,
    FlightFilterSerializer,
)
from .base import BaseFlightViewSet, PaginationMixin, FilterMixin

logger = logging.getLogger(__name__)


class FlightViewSet(BaseFlightViewSet, PaginationMixin, FilterMixin):
    """
    ViewSet for flight operations.

    Provides CRUD operations, state transitions, and related actions.
    """

    # ==========================================================================
    # List and Retrieve
    # ==========================================================================

    def list(self, request):
        """
        List flights with filtering and pagination.

        GET /api/v1/flights/
        """
        organization_id = self.get_organization_id()
        page, page_size = self.get_pagination_params()
        filters = self.get_filters(FlightFilterSerializer)

        # Get order_by parameter
        order_by = request.query_params.get('order_by', '-flight_date')

        result = FlightService.list_flights(
            organization_id=organization_id,
            filters=filters,
            page=page,
            page_size=page_size,
            order_by=order_by
        )

        serializer = FlightListSerializer(result['flights'], many=True)
        return Response({
            'results': serializer.data,
            'total': result['total'],
            'page': result['page'],
            'page_size': result['page_size'],
            'total_pages': result['total_pages'],
            'has_next': result['has_next'],
            'has_previous': result['has_previous'],
        })

    def retrieve(self, request, pk=None):
        """
        Retrieve a single flight with all details.

        GET /api/v1/flights/{id}/
        """
        organization_id = self.get_organization_id()
        flight_id = UUID(pk)

        result = FlightService.get_flight_with_details(
            flight_id=flight_id,
            organization_id=organization_id
        )

        serializer = FlightDetailSerializer(result['flight'])
        return Response({
            'flight': serializer.data,
            'approaches': [
                {
                    'id': str(a.id),
                    'approach_type': a.approach_type,
                    'airport_icao': a.airport_icao,
                    'runway': a.runway,
                    'result': a.result,
                    'in_imc': a.in_imc,
                    'to_minimums': a.to_minimums,
                }
                for a in result['approaches']
            ],
            'holds': [
                {
                    'id': str(h.id),
                    'fix_name': h.fix_name,
                    'turns': h.turns,
                    'in_imc': h.in_imc,
                }
                for h in result['holds']
            ],
            'fuel_records': [
                {
                    'id': str(f.id),
                    'record_type': f.record_type,
                    'quantity_liters': float(f.quantity_liters),
                    'total_cost': float(f.total_cost) if f.total_cost else None,
                }
                for f in result['fuel_records']
            ],
            'crew_logs': [
                {
                    'id': str(c.id),
                    'user_id': str(c.user_id),
                    'role': c.role,
                    'flight_time': float(c.flight_time) if c.flight_time else None,
                }
                for c in result['crew_logs']
            ],
        })

    # ==========================================================================
    # Create and Update
    # ==========================================================================

    def create(self, request):
        """
        Create a new flight.

        POST /api/v1/flights/
        """
        organization_id = self.get_organization_id()
        user_id = self.get_user_id()

        serializer = FlightCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Extract nested data
        approaches = serializer.validated_data.pop('approaches', None)
        holds = serializer.validated_data.pop('holds', None)
        fuel_records = serializer.validated_data.pop('fuel_records', None)

        flight = FlightService.create_flight(
            organization_id=organization_id,
            created_by=user_id,
            flight_data=serializer.validated_data,
            approaches=approaches,
            holds=holds,
            fuel_records=fuel_records,
        )

        response_serializer = FlightDetailSerializer(flight)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, pk=None):
        """
        Update an existing flight.

        PUT /api/v1/flights/{id}/
        """
        organization_id = self.get_organization_id()
        user_id = self.get_user_id()
        flight_id = UUID(pk)

        serializer = FlightUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Extract nested data
        approaches = serializer.validated_data.pop('approaches', None)
        holds = serializer.validated_data.pop('holds', None)

        flight = FlightService.update_flight(
            flight_id=flight_id,
            organization_id=organization_id,
            updated_by=user_id,
            flight_data=serializer.validated_data,
            approaches=approaches,
            holds=holds,
        )

        response_serializer = FlightDetailSerializer(flight)
        return Response(response_serializer.data)

    def partial_update(self, request, pk=None):
        """
        Partially update a flight.

        PATCH /api/v1/flights/{id}/
        """
        organization_id = self.get_organization_id()
        user_id = self.get_user_id()
        flight_id = UUID(pk)

        serializer = FlightUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        approaches = serializer.validated_data.pop('approaches', None)
        holds = serializer.validated_data.pop('holds', None)

        flight = FlightService.update_flight(
            flight_id=flight_id,
            organization_id=organization_id,
            updated_by=user_id,
            flight_data=serializer.validated_data,
            approaches=approaches,
            holds=holds,
        )

        response_serializer = FlightDetailSerializer(flight)
        return Response(response_serializer.data)

    def destroy(self, request, pk=None):
        """
        Delete a flight (soft delete).

        DELETE /api/v1/flights/{id}/
        """
        organization_id = self.get_organization_id()
        user_id = self.get_user_id()
        flight_id = UUID(pk)

        FlightService.delete_flight(
            flight_id=flight_id,
            organization_id=organization_id,
            deleted_by=user_id
        )

        return Response(status=status.HTTP_204_NO_CONTENT)

    # ==========================================================================
    # State Transitions
    # ==========================================================================

    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        """
        Submit a flight for approval.

        POST /api/v1/flights/{id}/submit/
        """
        organization_id = self.get_organization_id()
        user_id = self.get_user_id()
        flight_id = UUID(pk)

        flight = FlightService.submit_flight(
            flight_id=flight_id,
            organization_id=organization_id,
            submitted_by=user_id
        )

        serializer = FlightDetailSerializer(flight)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """
        Approve a submitted flight.

        POST /api/v1/flights/{id}/approve/
        """
        organization_id = self.get_organization_id()
        user_id = self.get_user_id()
        flight_id = UUID(pk)

        serializer = FlightApproveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        flight = FlightService.approve_flight(
            flight_id=flight_id,
            organization_id=organization_id,
            approved_by=user_id,
            remarks=serializer.validated_data.get('remarks')
        )

        response_serializer = FlightDetailSerializer(flight)
        return Response(response_serializer.data)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """
        Reject a submitted flight.

        POST /api/v1/flights/{id}/reject/
        """
        organization_id = self.get_organization_id()
        user_id = self.get_user_id()
        flight_id = UUID(pk)

        serializer = FlightRejectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        flight = FlightService.reject_flight(
            flight_id=flight_id,
            organization_id=organization_id,
            rejected_by=user_id,
            reason=serializer.validated_data['reason']
        )

        response_serializer = FlightDetailSerializer(flight)
        return Response(response_serializer.data)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """
        Cancel a flight.

        POST /api/v1/flights/{id}/cancel/
        """
        organization_id = self.get_organization_id()
        user_id = self.get_user_id()
        flight_id = UUID(pk)

        serializer = FlightCancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        flight = FlightService.cancel_flight(
            flight_id=flight_id,
            organization_id=organization_id,
            cancelled_by=user_id,
            reason=serializer.validated_data.get('reason')
        )

        response_serializer = FlightDetailSerializer(flight)
        return Response(response_serializer.data)

    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """
        Start a flight - marks the flight as in progress.

        POST /api/v1/flights/{id}/start/

        Updates flight status to 'in_progress' and records actual departure time.
        """
        organization_id = self.get_organization_id()
        user_id = self.get_user_id()
        flight_id = UUID(pk)

        try:
            flight = FlightService.start_flight(
                flight_id=flight_id,
                organization_id=organization_id,
                started_by=user_id,
                hobbs_start=request.data.get('hobbs_start'),
                tach_start=request.data.get('tach_start'),
                actual_departure=request.data.get('actual_departure'),
            )

            response_serializer = FlightDetailSerializer(flight)
            return Response(response_serializer.data)
        except FlightValidationError as e:
            return Response(
                {'error': str(e), 'field': getattr(e, 'field', None)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """
        Complete a flight - marks the flight as completed.

        POST /api/v1/flights/{id}/complete/

        Updates flight status to 'completed' and records actual arrival time,
        ending Hobbs/Tach readings, and final flight time calculations.
        """
        organization_id = self.get_organization_id()
        user_id = self.get_user_id()
        flight_id = UUID(pk)

        try:
            flight = FlightService.complete_flight(
                flight_id=flight_id,
                organization_id=organization_id,
                completed_by=user_id,
                hobbs_end=request.data.get('hobbs_end'),
                tach_end=request.data.get('tach_end'),
                actual_arrival=request.data.get('actual_arrival'),
                fuel_used=request.data.get('fuel_used'),
                remarks=request.data.get('remarks'),
            )

            response_serializer = FlightDetailSerializer(flight)
            return Response(response_serializer.data)
        except FlightValidationError as e:
            return Response(
                {'error': str(e), 'field': getattr(e, 'field', None)},
                status=status.HTTP_400_BAD_REQUEST
            )

    # ==========================================================================
    # Signatures
    # ==========================================================================

    @action(detail=True, methods=['post'])
    def sign(self, request, pk=None):
        """
        Sign a flight.

        POST /api/v1/flights/{id}/sign/
        """
        organization_id = self.get_organization_id()
        user_id = self.get_user_id()
        flight_id = UUID(pk)

        serializer = FlightSignatureSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        role = serializer.validated_data['role']
        signature_data = serializer.validated_data['signature_data']
        endorsements = serializer.validated_data.get('endorsements')

        if role == 'pic':
            flight = FlightService.sign_as_pic(
                flight_id=flight_id,
                organization_id=organization_id,
                signer_id=user_id,
                signature_data=signature_data
            )
        elif role == 'instructor':
            flight = FlightService.sign_as_instructor(
                flight_id=flight_id,
                organization_id=organization_id,
                signer_id=user_id,
                signature_data=signature_data,
                endorsements=endorsements
            )
        elif role == 'student':
            flight = FlightService.sign_as_student(
                flight_id=flight_id,
                organization_id=organization_id,
                signer_id=user_id,
                signature_data=signature_data
            )
        else:
            raise FlightValidationError(
                message=f"Invalid role: {role}",
                field="role"
            )

        response_serializer = FlightDetailSerializer(flight)
        return Response(response_serializer.data)

    # ==========================================================================
    # Related Records
    # ==========================================================================

    @action(detail=True, methods=['post'])
    def add_squawk(self, request, pk=None):
        """
        Add a squawk to a flight.

        POST /api/v1/flights/{id}/add_squawk/
        """
        organization_id = self.get_organization_id()
        flight_id = UUID(pk)

        serializer = FlightSquawkSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        flight = FlightService.add_squawk(
            flight_id=flight_id,
            organization_id=organization_id,
            squawk_id=serializer.validated_data['squawk_id']
        )

        response_serializer = FlightDetailSerializer(flight)
        return Response(response_serializer.data)

    # ==========================================================================
    # Bulk Operations
    # ==========================================================================

    @action(detail=False, methods=['post'])
    def bulk_action(self, request):
        """
        Perform bulk actions on flights.

        POST /api/v1/flights/bulk_action/
        """
        organization_id = self.get_organization_id()
        user_id = self.get_user_id()

        serializer = FlightBulkActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        flight_ids = serializer.validated_data['flight_ids']
        action_type = serializer.validated_data['action']
        reason = serializer.validated_data.get('reason')

        results = {'success': [], 'failed': []}

        for fid in flight_ids:
            try:
                if action_type == 'submit':
                    FlightService.submit_flight(fid, organization_id, user_id)
                elif action_type == 'approve':
                    FlightService.approve_flight(fid, organization_id, user_id)
                elif action_type == 'reject':
                    FlightService.reject_flight(fid, organization_id, user_id, reason)
                elif action_type == 'cancel':
                    FlightService.cancel_flight(fid, organization_id, user_id, reason)

                results['success'].append(str(fid))
            except Exception as e:
                results['failed'].append({
                    'flight_id': str(fid),
                    'error': str(e)
                })

        return Response(results)

    # ==========================================================================
    # Specialized Queries
    # ==========================================================================

    @action(detail=False, methods=['get'])
    def pending_approval(self, request):
        """
        Get flights pending approval.

        GET /api/v1/flights/pending_approval/
        """
        organization_id = self.get_organization_id()
        page, page_size = self.get_pagination_params()

        result = FlightService.get_pending_approval(
            organization_id=organization_id,
            page=page,
            page_size=page_size
        )

        serializer = FlightListSerializer(result['flights'], many=True)
        return Response({
            'results': serializer.data,
            'total': result['total'],
            'page': result['page'],
            'page_size': result['page_size'],
            'total_pages': result['total_pages'],
        })

    @action(detail=False, methods=['get'])
    def pending_signature(self, request):
        """
        Get flights pending user's signature.

        GET /api/v1/flights/pending_signature/
        """
        organization_id = self.get_organization_id()
        user_id = self.get_user_id()

        flights = FlightService.get_pending_signature(
            organization_id=organization_id,
            user_id=user_id
        )

        serializer = FlightListSerializer(flights, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def by_pilot(self, request):
        """
        Get flights for a specific pilot.

        GET /api/v1/flights/by_pilot/?pilot_id={uuid}
        """
        organization_id = self.get_organization_id()

        pilot_id = request.query_params.get('pilot_id')
        if not pilot_id:
            raise FlightValidationError(
                message="pilot_id is required",
                field="pilot_id"
            )

        pilot_id = UUID(pilot_id)
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        flight_status = request.query_params.get('status')

        if start_date:
            from datetime import datetime
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        if end_date:
            from datetime import datetime
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()

        flights = FlightService.get_flights_for_pilot(
            organization_id=organization_id,
            pilot_id=pilot_id,
            start_date=start_date,
            end_date=end_date,
            status=flight_status
        )

        serializer = FlightListSerializer(flights, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def by_aircraft(self, request):
        """
        Get flights for a specific aircraft.

        GET /api/v1/flights/by_aircraft/?aircraft_id={uuid}
        """
        organization_id = self.get_organization_id()

        aircraft_id = request.query_params.get('aircraft_id')
        if not aircraft_id:
            raise FlightValidationError(
                message="aircraft_id is required",
                field="aircraft_id"
            )

        aircraft_id = UUID(aircraft_id)
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        if start_date:
            from datetime import datetime
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        if end_date:
            from datetime import datetime
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()

        flights = FlightService.get_flights_for_aircraft(
            organization_id=organization_id,
            aircraft_id=aircraft_id,
            start_date=start_date,
            end_date=end_date
        )

        serializer = FlightListSerializer(flights, many=True)
        return Response(serializer.data)
