# services/flight-service/src/apps/core/services/flight_service.py
"""
Flight Service

Core business logic for flight management operations.
"""

import uuid
import logging
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import List, Dict, Any, Optional, Tuple

from django.db import transaction
from django.db.models import Q, Sum, Count, Avg, F
from django.utils import timezone
from django.core.paginator import Paginator

from ..models import (
    Flight,
    FlightCrewLog,
    FuelRecord,
    OilRecord,
    Approach,
    Hold,
    PilotLogbookSummary,
)
from .exceptions import (
    FlightNotFoundError,
    FlightValidationError,
    FlightStateError,
    FlightPermissionError,
    SignatureError,
)

logger = logging.getLogger(__name__)


class FlightService:
    """
    Service class for flight management operations.

    Handles flight CRUD, state transitions, approvals, and related operations.
    """

    # ==========================================================================
    # Flight CRUD Operations
    # ==========================================================================

    @classmethod
    @transaction.atomic
    def create_flight(
        cls,
        organization_id: uuid.UUID,
        created_by: uuid.UUID,
        flight_data: Dict[str, Any],
        approaches: List[Dict[str, Any]] = None,
        holds: List[Dict[str, Any]] = None,
        fuel_records: List[Dict[str, Any]] = None,
    ) -> Flight:
        """
        Create a new flight with all related records.

        Args:
            organization_id: Organization UUID
            created_by: User UUID creating the flight
            flight_data: Flight data dictionary
            approaches: Optional list of approach data
            holds: Optional list of hold data
            fuel_records: Optional list of fuel record data

        Returns:
            Created Flight instance

        Raises:
            FlightValidationError: If validation fails
        """
        logger.info(
            f"Creating flight for organization {organization_id} by user {created_by}"
        )

        # Validate required fields
        cls._validate_flight_data(flight_data)

        # Set organization and creator
        flight_data['organization_id'] = organization_id
        flight_data['created_by'] = created_by

        # Create flight
        flight = Flight.objects.create(**flight_data)

        # Create related records
        if approaches:
            cls._create_approaches(flight, approaches)

        if holds:
            cls._create_holds(flight, holds)

        if fuel_records:
            cls._create_fuel_records(flight, fuel_records, created_by)

        # Calculate times
        flight.calculate_times()
        flight.save()

        logger.info(f"Flight {flight.id} created successfully")
        return flight

    @classmethod
    def get_flight(
        cls,
        flight_id: uuid.UUID,
        organization_id: uuid.UUID = None
    ) -> Flight:
        """
        Get a flight by ID.

        Args:
            flight_id: Flight UUID
            organization_id: Optional organization filter

        Returns:
            Flight instance

        Raises:
            FlightNotFoundError: If flight not found
        """
        try:
            query = Flight.objects.filter(id=flight_id)
            if organization_id:
                query = query.filter(organization_id=organization_id)
            return query.get()
        except Flight.DoesNotExist:
            raise FlightNotFoundError(flight_id=str(flight_id))

    @classmethod
    def get_flight_with_details(
        cls,
        flight_id: uuid.UUID,
        organization_id: uuid.UUID = None
    ) -> Dict[str, Any]:
        """
        Get flight with all related data.

        Args:
            flight_id: Flight UUID
            organization_id: Optional organization filter

        Returns:
            Dictionary with flight and related data
        """
        flight = cls.get_flight(flight_id, organization_id)

        # Get related records
        approaches = Approach.objects.filter(flight_id=flight.id)
        holds = Hold.objects.filter(flight_id=flight.id)
        fuel_records = FuelRecord.objects.filter(flight_id=flight.id)
        oil_records = OilRecord.objects.filter(flight_id=flight.id)
        crew_logs = FlightCrewLog.objects.filter(flight_id=flight.id)

        return {
            'flight': flight,
            'approaches': list(approaches),
            'holds': list(holds),
            'fuel_records': list(fuel_records),
            'oil_records': list(oil_records),
            'crew_logs': list(crew_logs),
        }

    @classmethod
    @transaction.atomic
    def update_flight(
        cls,
        flight_id: uuid.UUID,
        organization_id: uuid.UUID,
        updated_by: uuid.UUID,
        flight_data: Dict[str, Any],
        approaches: List[Dict[str, Any]] = None,
        holds: List[Dict[str, Any]] = None,
    ) -> Flight:
        """
        Update an existing flight.

        Args:
            flight_id: Flight UUID
            organization_id: Organization UUID
            updated_by: User UUID performing update
            flight_data: Updated flight data
            approaches: Optional updated approaches
            holds: Optional updated holds

        Returns:
            Updated Flight instance

        Raises:
            FlightNotFoundError: If flight not found
            FlightStateError: If flight cannot be edited
        """
        flight = cls.get_flight(flight_id, organization_id)

        # Check if flight can be edited
        if flight.flight_status not in [Flight.Status.DRAFT, Flight.Status.REJECTED]:
            raise FlightStateError(
                current_state=flight.flight_status,
                target_state="editing",
                message="Only draft or rejected flights can be edited"
            )

        # Update fields
        for key, value in flight_data.items():
            if hasattr(flight, key) and key not in ['id', 'organization_id', 'created_by', 'created_at']:
                setattr(flight, key, value)

        # Update approaches if provided
        if approaches is not None:
            Approach.objects.filter(flight_id=flight.id).delete()
            cls._create_approaches(flight, approaches)

        # Update holds if provided
        if holds is not None:
            Hold.objects.filter(flight_id=flight.id).delete()
            cls._create_holds(flight, holds)

        # Recalculate times
        flight.calculate_times()
        flight.save()

        logger.info(f"Flight {flight.id} updated by user {updated_by}")
        return flight

    @classmethod
    @transaction.atomic
    def delete_flight(
        cls,
        flight_id: uuid.UUID,
        organization_id: uuid.UUID,
        deleted_by: uuid.UUID
    ) -> bool:
        """
        Delete a flight (soft delete via status change to cancelled).

        Args:
            flight_id: Flight UUID
            organization_id: Organization UUID
            deleted_by: User UUID performing deletion

        Returns:
            True if deleted successfully

        Raises:
            FlightNotFoundError: If flight not found
            FlightStateError: If flight cannot be deleted
        """
        flight = cls.get_flight(flight_id, organization_id)

        # Only draft flights can be deleted
        if flight.flight_status not in [Flight.Status.DRAFT]:
            raise FlightStateError(
                current_state=flight.flight_status,
                target_state=Flight.Status.CANCELLED,
                message="Only draft flights can be deleted. Submitted flights must be cancelled."
            )

        # Soft delete
        flight.flight_status = Flight.Status.CANCELLED
        flight.cancelled_at = timezone.now()
        flight.cancelled_by = deleted_by
        flight.save()

        logger.info(f"Flight {flight.id} deleted by user {deleted_by}")
        return True

    # ==========================================================================
    # Flight Listing and Search
    # ==========================================================================

    @classmethod
    def list_flights(
        cls,
        organization_id: uuid.UUID,
        filters: Dict[str, Any] = None,
        page: int = 1,
        page_size: int = 20,
        order_by: str = '-flight_date'
    ) -> Dict[str, Any]:
        """
        List flights with filtering and pagination.

        Args:
            organization_id: Organization UUID
            filters: Optional filter dictionary
            page: Page number (1-indexed)
            page_size: Items per page
            order_by: Field to order by

        Returns:
            Dictionary with flights and pagination info
        """
        queryset = Flight.objects.filter(organization_id=organization_id)

        # Apply filters
        if filters:
            queryset = cls._apply_filters(queryset, filters)

        # Order
        queryset = queryset.order_by(order_by)

        # Paginate
        paginator = Paginator(queryset, page_size)
        page_obj = paginator.get_page(page)

        return {
            'flights': list(page_obj.object_list),
            'total': paginator.count,
            'page': page,
            'page_size': page_size,
            'total_pages': paginator.num_pages,
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous(),
        }

    @classmethod
    def _apply_filters(cls, queryset, filters: Dict[str, Any]):
        """Apply filters to queryset."""
        # Date range
        if 'start_date' in filters:
            queryset = queryset.filter(flight_date__gte=filters['start_date'])
        if 'end_date' in filters:
            queryset = queryset.filter(flight_date__lte=filters['end_date'])

        # Status
        if 'status' in filters:
            if isinstance(filters['status'], list):
                queryset = queryset.filter(flight_status__in=filters['status'])
            else:
                queryset = queryset.filter(flight_status=filters['status'])

        # Aircraft
        if 'aircraft_id' in filters:
            queryset = queryset.filter(aircraft_id=filters['aircraft_id'])

        # Pilot
        if 'pilot_id' in filters:
            pilot_id = filters['pilot_id']
            queryset = queryset.filter(
                Q(pic_id=pilot_id) |
                Q(sic_id=pilot_id) |
                Q(student_id=pilot_id)
            )

        # Flight type
        if 'flight_type' in filters:
            queryset = queryset.filter(flight_type=filters['flight_type'])

        # Flight rules
        if 'flight_rules' in filters:
            queryset = queryset.filter(flight_rules=filters['flight_rules'])

        # Airports
        if 'departure_airport' in filters:
            queryset = queryset.filter(departure_airport=filters['departure_airport'])
        if 'arrival_airport' in filters:
            queryset = queryset.filter(arrival_airport=filters['arrival_airport'])

        # Booking
        if 'booking_id' in filters:
            queryset = queryset.filter(booking_id=filters['booking_id'])

        # Billing status
        if 'billing_status' in filters:
            queryset = queryset.filter(billing_status=filters['billing_status'])

        # Search
        if 'search' in filters:
            search = filters['search']
            queryset = queryset.filter(
                Q(aircraft_registration__icontains=search) |
                Q(departure_airport__icontains=search) |
                Q(arrival_airport__icontains=search) |
                Q(route__icontains=search) |
                Q(remarks__icontains=search)
            )

        return queryset

    @classmethod
    def get_flights_for_pilot(
        cls,
        organization_id: uuid.UUID,
        pilot_id: uuid.UUID,
        start_date: date = None,
        end_date: date = None,
        status: str = None
    ) -> List[Flight]:
        """Get all flights for a specific pilot."""
        queryset = Flight.objects.filter(
            organization_id=organization_id
        ).filter(
            Q(pic_id=pilot_id) |
            Q(sic_id=pilot_id) |
            Q(student_id=pilot_id)
        )

        if start_date:
            queryset = queryset.filter(flight_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(flight_date__lte=end_date)
        if status:
            queryset = queryset.filter(flight_status=status)

        return list(queryset.order_by('-flight_date'))

    @classmethod
    def get_flights_for_aircraft(
        cls,
        organization_id: uuid.UUID,
        aircraft_id: uuid.UUID,
        start_date: date = None,
        end_date: date = None
    ) -> List[Flight]:
        """Get all flights for a specific aircraft."""
        queryset = Flight.objects.filter(
            organization_id=organization_id,
            aircraft_id=aircraft_id
        )

        if start_date:
            queryset = queryset.filter(flight_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(flight_date__lte=end_date)

        return list(queryset.order_by('-flight_date'))

    # ==========================================================================
    # Flight State Transitions
    # ==========================================================================

    @classmethod
    @transaction.atomic
    def submit_flight(
        cls,
        flight_id: uuid.UUID,
        organization_id: uuid.UUID,
        submitted_by: uuid.UUID
    ) -> Flight:
        """
        Submit a flight for approval.

        Args:
            flight_id: Flight UUID
            organization_id: Organization UUID
            submitted_by: User UUID submitting

        Returns:
            Updated Flight instance

        Raises:
            FlightStateError: If flight cannot be submitted
            FlightValidationError: If flight is incomplete
        """
        flight = cls.get_flight(flight_id, organization_id)

        if flight.flight_status not in [Flight.Status.DRAFT, Flight.Status.REJECTED]:
            raise FlightStateError(
                current_state=flight.flight_status,
                target_state=Flight.Status.SUBMITTED,
                message="Only draft or rejected flights can be submitted"
            )

        # Validate flight is complete
        validation_errors = cls._validate_flight_for_submission(flight)
        if validation_errors:
            raise FlightValidationError(
                message="Flight is incomplete",
                details={"errors": validation_errors}
            )

        flight.flight_status = Flight.Status.SUBMITTED
        flight.submitted_at = timezone.now()
        flight.submitted_by = submitted_by
        flight.save()

        logger.info(f"Flight {flight.id} submitted by user {submitted_by}")
        return flight

    @classmethod
    @transaction.atomic
    def approve_flight(
        cls,
        flight_id: uuid.UUID,
        organization_id: uuid.UUID,
        approved_by: uuid.UUID,
        remarks: str = None
    ) -> Flight:
        """
        Approve a submitted flight.

        Args:
            flight_id: Flight UUID
            organization_id: Organization UUID
            approved_by: User UUID approving
            remarks: Optional approval remarks

        Returns:
            Updated Flight instance

        Raises:
            FlightStateError: If flight cannot be approved
        """
        flight = cls.get_flight(flight_id, organization_id)

        if flight.flight_status not in [Flight.Status.SUBMITTED, Flight.Status.PENDING_REVIEW]:
            raise FlightStateError(
                current_state=flight.flight_status,
                target_state=Flight.Status.APPROVED,
                message="Only submitted or pending review flights can be approved"
            )

        flight.flight_status = Flight.Status.APPROVED
        flight.approved_at = timezone.now()
        flight.approved_by = approved_by

        if remarks:
            flight.approval_remarks = remarks

        flight.save()

        # Create crew log entries for approved flight
        cls._create_crew_logs(flight)

        logger.info(f"Flight {flight.id} approved by user {approved_by}")
        return flight

    @classmethod
    @transaction.atomic
    def reject_flight(
        cls,
        flight_id: uuid.UUID,
        organization_id: uuid.UUID,
        rejected_by: uuid.UUID,
        reason: str
    ) -> Flight:
        """
        Reject a submitted flight.

        Args:
            flight_id: Flight UUID
            organization_id: Organization UUID
            rejected_by: User UUID rejecting
            reason: Rejection reason (required)

        Returns:
            Updated Flight instance

        Raises:
            FlightStateError: If flight cannot be rejected
            FlightValidationError: If reason not provided
        """
        if not reason:
            raise FlightValidationError(
                message="Rejection reason is required",
                field="reason"
            )

        flight = cls.get_flight(flight_id, organization_id)

        if flight.flight_status not in [Flight.Status.SUBMITTED, Flight.Status.PENDING_REVIEW]:
            raise FlightStateError(
                current_state=flight.flight_status,
                target_state=Flight.Status.REJECTED,
                message="Only submitted or pending review flights can be rejected"
            )

        flight.flight_status = Flight.Status.REJECTED
        flight.rejected_at = timezone.now()
        flight.rejected_by = rejected_by
        flight.rejection_reason = reason
        flight.save()

        logger.info(f"Flight {flight.id} rejected by user {rejected_by}: {reason}")
        return flight

    @classmethod
    @transaction.atomic
    def cancel_flight(
        cls,
        flight_id: uuid.UUID,
        organization_id: uuid.UUID,
        cancelled_by: uuid.UUID,
        reason: str = None
    ) -> Flight:
        """
        Cancel a flight.

        Args:
            flight_id: Flight UUID
            organization_id: Organization UUID
            cancelled_by: User UUID cancelling
            reason: Optional cancellation reason

        Returns:
            Updated Flight instance
        """
        flight = cls.get_flight(flight_id, organization_id)

        if flight.flight_status == Flight.Status.CANCELLED:
            raise FlightStateError(
                current_state=flight.flight_status,
                target_state=Flight.Status.CANCELLED,
                message="Flight is already cancelled"
            )

        # If approved, we may need to reverse logbook entries
        was_approved = flight.flight_status == Flight.Status.APPROVED

        flight.flight_status = Flight.Status.CANCELLED
        flight.cancelled_at = timezone.now()
        flight.cancelled_by = cancelled_by
        if reason:
            flight.cancellation_reason = reason
        flight.save()

        # Remove crew logs if flight was approved
        if was_approved:
            FlightCrewLog.objects.filter(flight_id=flight.id).delete()

        logger.info(f"Flight {flight.id} cancelled by user {cancelled_by}")
        return flight

    @classmethod
    @transaction.atomic
    def start_flight(
        cls,
        flight_id: uuid.UUID,
        organization_id: uuid.UUID,
        started_by: uuid.UUID,
        hobbs_start: float = None,
        tach_start: float = None,
        actual_departure: str = None,
    ) -> Flight:
        """
        Start a flight - transition to in_progress status.

        Args:
            flight_id: Flight UUID
            organization_id: Organization UUID
            started_by: User UUID starting the flight
            hobbs_start: Starting Hobbs meter reading
            tach_start: Starting Tach meter reading
            actual_departure: Actual departure datetime string

        Returns:
            Updated Flight instance
        """
        flight = cls.get_flight(flight_id, organization_id)

        # Validate state transition
        valid_states = [Flight.Status.DRAFT, Flight.Status.SCHEDULED, Flight.Status.PLANNED]
        if flight.flight_status not in valid_states:
            raise FlightStateError(
                current_state=flight.flight_status,
                target_state=Flight.Status.IN_PROGRESS,
                message=f"Cannot start flight from {flight.flight_status} status"
            )

        flight.flight_status = Flight.Status.IN_PROGRESS
        flight.started_at = timezone.now()
        flight.started_by = started_by

        if hobbs_start is not None:
            flight.hobbs_start = hobbs_start
        if tach_start is not None:
            flight.tach_start = tach_start
        if actual_departure:
            from datetime import datetime
            if isinstance(actual_departure, str):
                flight.actual_departure_time = datetime.fromisoformat(actual_departure.replace('Z', '+00:00'))
            else:
                flight.actual_departure_time = actual_departure

        flight.save()

        logger.info(f"Flight {flight.id} started by user {started_by}")
        return flight

    @classmethod
    @transaction.atomic
    def complete_flight(
        cls,
        flight_id: uuid.UUID,
        organization_id: uuid.UUID,
        completed_by: uuid.UUID,
        hobbs_end: float = None,
        tach_end: float = None,
        actual_arrival: str = None,
        fuel_used: float = None,
        remarks: str = None,
    ) -> Flight:
        """
        Complete a flight - transition to completed status.

        Args:
            flight_id: Flight UUID
            organization_id: Organization UUID
            completed_by: User UUID completing the flight
            hobbs_end: Ending Hobbs meter reading
            tach_end: Ending Tach meter reading
            actual_arrival: Actual arrival datetime string
            fuel_used: Fuel used during flight (liters)
            remarks: Post-flight remarks

        Returns:
            Updated Flight instance
        """
        flight = cls.get_flight(flight_id, organization_id)

        # Validate state transition
        if flight.flight_status != Flight.Status.IN_PROGRESS:
            raise FlightStateError(
                current_state=flight.flight_status,
                target_state=Flight.Status.COMPLETED,
                message=f"Cannot complete flight from {flight.flight_status} status. Flight must be in progress."
            )

        flight.flight_status = Flight.Status.COMPLETED
        flight.completed_at = timezone.now()
        flight.completed_by = completed_by

        if hobbs_end is not None:
            flight.hobbs_end = hobbs_end
            # Calculate flight time if both readings available
            if flight.hobbs_start is not None:
                flight.total_hobbs_time = hobbs_end - flight.hobbs_start

        if tach_end is not None:
            flight.tach_end = tach_end
            # Calculate tach time if both readings available
            if flight.tach_start is not None:
                flight.total_tach_time = tach_end - flight.tach_start

        if actual_arrival:
            from datetime import datetime
            if isinstance(actual_arrival, str):
                flight.actual_arrival_time = datetime.fromisoformat(actual_arrival.replace('Z', '+00:00'))
            else:
                flight.actual_arrival_time = actual_arrival

        if fuel_used is not None:
            flight.fuel_used = fuel_used

        if remarks:
            if flight.remarks:
                flight.remarks = f"{flight.remarks}\n\nPost-flight: {remarks}"
            else:
                flight.remarks = f"Post-flight: {remarks}"

        flight.save()

        logger.info(f"Flight {flight.id} completed by user {completed_by}")
        return flight

    # ==========================================================================
    # Signature Operations
    # ==========================================================================

    @classmethod
    @transaction.atomic
    def sign_as_pic(
        cls,
        flight_id: uuid.UUID,
        organization_id: uuid.UUID,
        signer_id: uuid.UUID,
        signature_data: Dict[str, Any]
    ) -> Flight:
        """
        Sign flight as PIC.

        Args:
            flight_id: Flight UUID
            organization_id: Organization UUID
            signer_id: PIC user UUID
            signature_data: Signature data (SVG, image, etc.)

        Returns:
            Updated Flight instance

        Raises:
            SignatureError: If signing fails
        """
        flight = cls.get_flight(flight_id, organization_id)

        # Verify signer is PIC
        if flight.pic_id != signer_id:
            raise SignatureError(
                message="Only the PIC can sign as PIC",
                signer_role="pic"
            )

        flight.pic_signature = {
            'data': signature_data,
            'signed_at': timezone.now().isoformat(),
            'signer_id': str(signer_id),
        }
        flight.pic_signed_at = timezone.now()
        flight.save()

        logger.info(f"Flight {flight.id} signed by PIC {signer_id}")
        return flight

    @classmethod
    @transaction.atomic
    def sign_as_instructor(
        cls,
        flight_id: uuid.UUID,
        organization_id: uuid.UUID,
        signer_id: uuid.UUID,
        signature_data: Dict[str, Any],
        endorsements: List[str] = None
    ) -> Flight:
        """
        Sign flight as instructor.

        Args:
            flight_id: Flight UUID
            organization_id: Organization UUID
            signer_id: Instructor user UUID
            signature_data: Signature data
            endorsements: Optional endorsements to add

        Returns:
            Updated Flight instance
        """
        flight = cls.get_flight(flight_id, organization_id)

        # Verify signer is instructor
        if flight.instructor_id != signer_id:
            raise SignatureError(
                message="Only the assigned instructor can sign as instructor",
                signer_role="instructor"
            )

        flight.instructor_signature = {
            'data': signature_data,
            'signed_at': timezone.now().isoformat(),
            'signer_id': str(signer_id),
            'endorsements': endorsements or [],
        }
        flight.instructor_signed_at = timezone.now()
        flight.save()

        logger.info(f"Flight {flight.id} signed by instructor {signer_id}")
        return flight

    @classmethod
    @transaction.atomic
    def sign_as_student(
        cls,
        flight_id: uuid.UUID,
        organization_id: uuid.UUID,
        signer_id: uuid.UUID,
        signature_data: Dict[str, Any]
    ) -> Flight:
        """Sign flight as student."""
        flight = cls.get_flight(flight_id, organization_id)

        if flight.student_id != signer_id:
            raise SignatureError(
                message="Only the assigned student can sign as student",
                signer_role="student"
            )

        flight.student_signature = {
            'data': signature_data,
            'signed_at': timezone.now().isoformat(),
            'signer_id': str(signer_id),
        }
        flight.student_signed_at = timezone.now()
        flight.save()

        logger.info(f"Flight {flight.id} signed by student {signer_id}")
        return flight

    # ==========================================================================
    # Approach and Hold Operations
    # ==========================================================================

    @classmethod
    def add_approach(
        cls,
        flight_id: uuid.UUID,
        organization_id: uuid.UUID,
        approach_data: Dict[str, Any]
    ) -> Approach:
        """Add an approach to a flight."""
        flight = cls.get_flight(flight_id, organization_id)

        if flight.flight_status == Flight.Status.APPROVED:
            raise FlightStateError(
                current_state=flight.flight_status,
                target_state="editing",
                message="Cannot add approaches to approved flights"
            )

        # Get next sequence number
        last_approach = Approach.objects.filter(
            flight_id=flight.id
        ).order_by('-sequence_number').first()

        sequence = (last_approach.sequence_number + 1) if last_approach else 1

        approach = Approach.objects.create(
            flight_id=flight.id,
            organization_id=organization_id,
            sequence_number=sequence,
            **approach_data
        )

        # Update flight approach count
        flight.approach_count = Approach.objects.filter(flight_id=flight.id).count()
        flight.save()

        return approach

    @classmethod
    def add_hold(
        cls,
        flight_id: uuid.UUID,
        organization_id: uuid.UUID,
        hold_data: Dict[str, Any]
    ) -> Hold:
        """Add a hold to a flight."""
        flight = cls.get_flight(flight_id, organization_id)

        if flight.flight_status == Flight.Status.APPROVED:
            raise FlightStateError(
                current_state=flight.flight_status,
                target_state="editing",
                message="Cannot add holds to approved flights"
            )

        hold = Hold.objects.create(
            flight_id=flight.id,
            organization_id=organization_id,
            **hold_data
        )

        # Update flight hold count
        flight.holds = Hold.objects.filter(flight_id=flight.id).count()
        flight.save()

        return hold

    # ==========================================================================
    # Fuel Operations
    # ==========================================================================

    @classmethod
    def add_fuel_record(
        cls,
        flight_id: uuid.UUID,
        organization_id: uuid.UUID,
        created_by: uuid.UUID,
        fuel_data: Dict[str, Any]
    ) -> FuelRecord:
        """Add a fuel record to a flight."""
        flight = cls.get_flight(flight_id, organization_id)

        fuel_record = FuelRecord.objects.create(
            flight_id=flight.id,
            organization_id=organization_id,
            aircraft_id=flight.aircraft_id,
            created_by=created_by,
            **fuel_data
        )

        # Update flight fuel totals
        cls._update_flight_fuel_totals(flight)

        return fuel_record

    @classmethod
    def add_oil_record(
        cls,
        flight_id: uuid.UUID,
        organization_id: uuid.UUID,
        created_by: uuid.UUID,
        oil_data: Dict[str, Any]
    ) -> OilRecord:
        """Add an oil record to a flight."""
        flight = cls.get_flight(flight_id, organization_id)

        return OilRecord.objects.create(
            flight_id=flight.id,
            organization_id=organization_id,
            aircraft_id=flight.aircraft_id,
            created_by=created_by,
            **oil_data
        )

    # ==========================================================================
    # Squawk Operations
    # ==========================================================================

    @classmethod
    def add_squawk(
        cls,
        flight_id: uuid.UUID,
        organization_id: uuid.UUID,
        squawk_id: uuid.UUID
    ) -> Flight:
        """Add a squawk reference to a flight."""
        flight = cls.get_flight(flight_id, organization_id)
        flight.add_squawk(squawk_id)
        return flight

    # ==========================================================================
    # Private Helper Methods
    # ==========================================================================

    @classmethod
    def _validate_flight_data(cls, flight_data: Dict[str, Any]) -> None:
        """Validate flight data for creation."""
        required_fields = ['flight_date', 'aircraft_id', 'departure_airport']

        missing = [f for f in required_fields if f not in flight_data]
        if missing:
            raise FlightValidationError(
                message=f"Missing required fields: {', '.join(missing)}",
                details={"missing_fields": missing}
            )

    @classmethod
    def _validate_flight_for_submission(cls, flight: Flight) -> List[str]:
        """Validate flight is complete for submission."""
        errors = []

        if not flight.aircraft_id:
            errors.append("Aircraft is required")

        if not flight.departure_airport:
            errors.append("Departure airport is required")

        if not flight.pic_id and not flight.student_id:
            errors.append("PIC or student is required")

        if not flight.block_off:
            errors.append("Block off time is required")

        if not flight.block_on:
            errors.append("Block on time is required")

        return errors

    @classmethod
    def _create_approaches(cls, flight: Flight, approaches: List[Dict[str, Any]]) -> None:
        """Create approach records for a flight."""
        for i, approach_data in enumerate(approaches, 1):
            Approach.objects.create(
                flight_id=flight.id,
                organization_id=flight.organization_id,
                sequence_number=i,
                **approach_data
            )

        flight.approach_count = len(approaches)

    @classmethod
    def _create_holds(cls, flight: Flight, holds: List[Dict[str, Any]]) -> None:
        """Create hold records for a flight."""
        for hold_data in holds:
            Hold.objects.create(
                flight_id=flight.id,
                organization_id=flight.organization_id,
                **hold_data
            )

        flight.holds = len(holds)

    @classmethod
    def _create_fuel_records(
        cls,
        flight: Flight,
        fuel_records: List[Dict[str, Any]],
        created_by: uuid.UUID
    ) -> None:
        """Create fuel records for a flight."""
        for fuel_data in fuel_records:
            FuelRecord.objects.create(
                flight_id=flight.id,
                organization_id=flight.organization_id,
                aircraft_id=flight.aircraft_id,
                created_by=created_by,
                **fuel_data
            )

        cls._update_flight_fuel_totals(flight)

    @classmethod
    def _update_flight_fuel_totals(cls, flight: Flight) -> None:
        """Update flight fuel totals from fuel records."""
        uplifts = FuelRecord.objects.filter(
            flight_id=flight.id,
            record_type=FuelRecord.RecordType.UPLIFT
        ).aggregate(
            total_liters=Sum('quantity_liters'),
            total_cost=Sum('total_cost')
        )

        flight.fuel_added_liters = uplifts['total_liters'] or Decimal('0')
        flight.fuel_cost = uplifts['total_cost'] or Decimal('0')
        flight.save()

    @classmethod
    def _create_crew_logs(cls, flight: Flight) -> None:
        """Create crew log entries for an approved flight."""
        # PIC log
        if flight.pic_id:
            FlightCrewLog.create_from_flight(
                flight=flight,
                user_id=flight.pic_id,
                role=FlightCrewLog.Role.PIC,
                time_pic=flight.flight_time or Decimal('0'),
            )

        # SIC log
        if flight.sic_id:
            FlightCrewLog.create_from_flight(
                flight=flight,
                user_id=flight.sic_id,
                role=FlightCrewLog.Role.SIC,
                time_sic=flight.flight_time or Decimal('0'),
            )

        # Instructor log
        if flight.instructor_id:
            FlightCrewLog.create_from_flight(
                flight=flight,
                user_id=flight.instructor_id,
                role=FlightCrewLog.Role.INSTRUCTOR,
                time_dual_given=flight.time_dual_received or Decimal('0'),
            )

        # Student log
        if flight.student_id:
            FlightCrewLog.create_from_flight(
                flight=flight,
                user_id=flight.student_id,
                role=FlightCrewLog.Role.STUDENT,
                time_dual_received=flight.time_dual_received or Decimal('0'),
            )

        # Examiner log
        if flight.examiner_id:
            FlightCrewLog.create_from_flight(
                flight=flight,
                user_id=flight.examiner_id,
                role=FlightCrewLog.Role.EXAMINER,
            )

    # ==========================================================================
    # Pending Approval Operations
    # ==========================================================================

    @classmethod
    def get_pending_approval(
        cls,
        organization_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """Get flights pending approval."""
        return cls.list_flights(
            organization_id=organization_id,
            filters={'status': [Flight.Status.SUBMITTED, Flight.Status.PENDING_REVIEW]},
            page=page,
            page_size=page_size,
            order_by='submitted_at'
        )

    @classmethod
    def get_pending_signature(
        cls,
        organization_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> List[Flight]:
        """Get flights pending user's signature."""
        return list(Flight.objects.filter(
            organization_id=organization_id,
            flight_status__in=[Flight.Status.DRAFT, Flight.Status.SUBMITTED]
        ).filter(
            Q(pic_id=user_id, pic_signed_at__isnull=True) |
            Q(instructor_id=user_id, instructor_signed_at__isnull=True) |
            Q(student_id=user_id, student_signed_at__isnull=True)
        ).order_by('-flight_date'))
