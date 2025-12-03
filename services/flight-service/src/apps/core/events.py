# services/flight-service/src/apps/core/events.py
"""
Flight Service Events

Event definitions for flight service domain events.
These events are published to the message broker for other services to consume.
"""

import uuid
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from dataclasses import dataclass, field, asdict
from enum import Enum

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """Flight service event types."""

    # Flight lifecycle
    FLIGHT_CREATED = 'flight.created'
    FLIGHT_UPDATED = 'flight.updated'
    FLIGHT_SUBMITTED = 'flight.submitted'
    FLIGHT_APPROVED = 'flight.approved'
    FLIGHT_REJECTED = 'flight.rejected'
    FLIGHT_CANCELLED = 'flight.cancelled'

    # Signatures
    FLIGHT_SIGNED_PIC = 'flight.signed.pic'
    FLIGHT_SIGNED_INSTRUCTOR = 'flight.signed.instructor'
    FLIGHT_SIGNED_STUDENT = 'flight.signed.student'

    # Logbook
    LOGBOOK_ENTRY_CREATED = 'logbook.entry.created'
    LOGBOOK_ENTRY_SIGNED = 'logbook.entry.signed'
    LOGBOOK_SUMMARY_UPDATED = 'logbook.summary.updated'

    # Currency
    CURRENCY_STATUS_CHANGED = 'currency.status.changed'
    CURRENCY_EXPIRING_SOON = 'currency.expiring_soon'
    CURRENCY_EXPIRED = 'currency.expired'

    # Squawks
    FLIGHT_SQUAWK_ADDED = 'flight.squawk.added'

    # Fuel
    FUEL_RECORD_CREATED = 'fuel.record.created'

    # Billing
    FLIGHT_BILLING_READY = 'flight.billing.ready'


@dataclass
class BaseEvent:
    """Base class for all events."""

    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str = ''
    event_version: str = '1.0'
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    source: str = 'flight-service'
    correlation_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary."""
        return asdict(self)

    def to_json(self) -> str:
        """Convert event to JSON string."""
        return json.dumps(self.to_dict(), default=str)


@dataclass
class FlightCreatedEvent(BaseEvent):
    """Event published when a flight is created."""

    event_type: str = EventType.FLIGHT_CREATED.value

    flight_id: str = ''
    organization_id: str = ''
    created_by: str = ''
    flight_date: str = ''
    aircraft_id: str = ''
    aircraft_registration: str = ''
    departure_airport: str = ''
    arrival_airport: str = ''
    flight_type: str = ''
    pic_id: Optional[str] = None
    sic_id: Optional[str] = None
    instructor_id: Optional[str] = None
    student_id: Optional[str] = None
    booking_id: Optional[str] = None


@dataclass
class FlightUpdatedEvent(BaseEvent):
    """Event published when a flight is updated."""

    event_type: str = EventType.FLIGHT_UPDATED.value

    flight_id: str = ''
    organization_id: str = ''
    updated_by: str = ''
    updated_fields: list = field(default_factory=list)


@dataclass
class FlightSubmittedEvent(BaseEvent):
    """Event published when a flight is submitted for approval."""

    event_type: str = EventType.FLIGHT_SUBMITTED.value

    flight_id: str = ''
    organization_id: str = ''
    submitted_by: str = ''
    flight_date: str = ''
    aircraft_registration: str = ''
    departure_airport: str = ''
    arrival_airport: str = ''
    flight_time: float = 0.0


@dataclass
class FlightApprovedEvent(BaseEvent):
    """Event published when a flight is approved."""

    event_type: str = EventType.FLIGHT_APPROVED.value

    flight_id: str = ''
    organization_id: str = ''
    approved_by: str = ''
    flight_date: str = ''
    aircraft_id: str = ''
    aircraft_registration: str = ''
    departure_airport: str = ''
    arrival_airport: str = ''
    flight_time: float = 0.0
    block_time: float = 0.0
    hobbs_time: float = 0.0
    tach_time: float = 0.0
    landings: int = 0
    pic_id: Optional[str] = None
    sic_id: Optional[str] = None
    instructor_id: Optional[str] = None
    student_id: Optional[str] = None
    fuel_added_liters: float = 0.0
    fuel_cost: float = 0.0
    booking_id: Optional[str] = None


@dataclass
class FlightRejectedEvent(BaseEvent):
    """Event published when a flight is rejected."""

    event_type: str = EventType.FLIGHT_REJECTED.value

    flight_id: str = ''
    organization_id: str = ''
    rejected_by: str = ''
    rejection_reason: str = ''


@dataclass
class FlightCancelledEvent(BaseEvent):
    """Event published when a flight is cancelled."""

    event_type: str = EventType.FLIGHT_CANCELLED.value

    flight_id: str = ''
    organization_id: str = ''
    cancelled_by: str = ''
    cancellation_reason: Optional[str] = None
    was_approved: bool = False


@dataclass
class FlightSignedEvent(BaseEvent):
    """Event published when a flight is signed."""

    flight_id: str = ''
    organization_id: str = ''
    signer_id: str = ''
    signer_role: str = ''  # 'pic', 'instructor', 'student'


@dataclass
class FlightSignedPICEvent(FlightSignedEvent):
    """Event for PIC signature."""

    event_type: str = EventType.FLIGHT_SIGNED_PIC.value
    signer_role: str = 'pic'


@dataclass
class FlightSignedInstructorEvent(FlightSignedEvent):
    """Event for instructor signature."""

    event_type: str = EventType.FLIGHT_SIGNED_INSTRUCTOR.value
    signer_role: str = 'instructor'
    endorsements: list = field(default_factory=list)


@dataclass
class FlightSignedStudentEvent(FlightSignedEvent):
    """Event for student signature."""

    event_type: str = EventType.FLIGHT_SIGNED_STUDENT.value
    signer_role: str = 'student'


@dataclass
class LogbookEntryCreatedEvent(BaseEvent):
    """Event published when a logbook entry is created."""

    event_type: str = EventType.LOGBOOK_ENTRY_CREATED.value

    entry_id: str = ''
    flight_id: str = ''
    organization_id: str = ''
    user_id: str = ''
    role: str = ''
    flight_date: str = ''
    flight_time: float = 0.0
    landings: int = 0
    approaches: int = 0


@dataclass
class LogbookEntrySignedEvent(BaseEvent):
    """Event published when a logbook entry is signed."""

    event_type: str = EventType.LOGBOOK_ENTRY_SIGNED.value

    entry_id: str = ''
    flight_id: str = ''
    organization_id: str = ''
    user_id: str = ''


@dataclass
class LogbookSummaryUpdatedEvent(BaseEvent):
    """Event published when a logbook summary is updated."""

    event_type: str = EventType.LOGBOOK_SUMMARY_UPDATED.value

    summary_id: str = ''
    organization_id: str = ''
    user_id: str = ''
    total_time: float = 0.0
    total_flights: int = 0


@dataclass
class CurrencyStatusChangedEvent(BaseEvent):
    """Event published when currency status changes."""

    event_type: str = EventType.CURRENCY_STATUS_CHANGED.value

    organization_id: str = ''
    user_id: str = ''
    currency_type: str = ''
    old_status: str = ''
    new_status: str = ''
    expires_on: Optional[str] = None


@dataclass
class CurrencyExpiringSoonEvent(BaseEvent):
    """Event published when currency is expiring soon."""

    event_type: str = EventType.CURRENCY_EXPIRING_SOON.value

    organization_id: str = ''
    user_id: str = ''
    currency_type: str = ''
    days_remaining: int = 0
    expires_on: str = ''


@dataclass
class CurrencyExpiredEvent(BaseEvent):
    """Event published when currency has expired."""

    event_type: str = EventType.CURRENCY_EXPIRED.value

    organization_id: str = ''
    user_id: str = ''
    currency_type: str = ''
    expired_on: str = ''


@dataclass
class FlightSquawkAddedEvent(BaseEvent):
    """Event published when a squawk is added to a flight."""

    event_type: str = EventType.FLIGHT_SQUAWK_ADDED.value

    flight_id: str = ''
    organization_id: str = ''
    squawk_id: str = ''
    aircraft_id: str = ''


@dataclass
class FuelRecordCreatedEvent(BaseEvent):
    """Event published when a fuel record is created."""

    event_type: str = EventType.FUEL_RECORD_CREATED.value

    record_id: str = ''
    flight_id: str = ''
    organization_id: str = ''
    aircraft_id: str = ''
    record_type: str = ''
    quantity_liters: float = 0.0
    total_cost: Optional[float] = None
    location_icao: Optional[str] = None


@dataclass
class FlightBillingReadyEvent(BaseEvent):
    """Event published when a flight is ready for billing."""

    event_type: str = EventType.FLIGHT_BILLING_READY.value

    flight_id: str = ''
    organization_id: str = ''
    booking_id: Optional[str] = None
    aircraft_id: str = ''
    aircraft_registration: str = ''
    flight_date: str = ''
    flight_time: float = 0.0
    block_time: float = 0.0
    hobbs_time: float = 0.0
    tach_time: float = 0.0
    landings: int = 0
    fuel_added_liters: float = 0.0
    fuel_cost: float = 0.0
    pic_id: Optional[str] = None
    instructor_id: Optional[str] = None
    student_id: Optional[str] = None
    flight_type: str = ''


# =============================================================================
# Event Publisher
# =============================================================================

class EventPublisher:
    """
    Event publisher for flight service.

    Publishes events to message broker (RabbitMQ, Redis, etc.)
    """

    def __init__(self, broker_url: str = None):
        """Initialize event publisher."""
        self.broker_url = broker_url
        self._connected = False

    def connect(self):
        """Connect to message broker."""
        # Implementation depends on chosen broker
        # For now, just log events
        self._connected = True
        logger.info("Event publisher connected")

    def disconnect(self):
        """Disconnect from message broker."""
        self._connected = False
        logger.info("Event publisher disconnected")

    def publish(self, event: BaseEvent, routing_key: str = None):
        """
        Publish an event.

        Args:
            event: Event to publish
            routing_key: Optional routing key (defaults to event_type)
        """
        if routing_key is None:
            routing_key = event.event_type

        try:
            # In production, this would publish to actual broker
            # For now, just log the event
            logger.info(
                f"Publishing event: {event.event_type}",
                extra={
                    'event_id': event.event_id,
                    'event_type': event.event_type,
                    'routing_key': routing_key,
                }
            )

            # Example implementation for different brokers:
            # self._publish_to_rabbitmq(event, routing_key)
            # self._publish_to_redis(event, routing_key)
            # self._publish_to_kafka(event, routing_key)

            return True

        except Exception as e:
            logger.error(
                f"Failed to publish event: {event.event_type}",
                exc_info=True,
                extra={
                    'event_id': event.event_id,
                    'error': str(e),
                }
            )
            return False

    def publish_flight_created(self, flight) -> bool:
        """Publish flight created event."""
        event = FlightCreatedEvent(
            flight_id=str(flight.id),
            organization_id=str(flight.organization_id),
            created_by=str(flight.created_by),
            flight_date=flight.flight_date.isoformat(),
            aircraft_id=str(flight.aircraft_id),
            aircraft_registration=flight.aircraft_registration,
            departure_airport=flight.departure_airport,
            arrival_airport=flight.arrival_airport or '',
            flight_type=flight.flight_type,
            pic_id=str(flight.pic_id) if flight.pic_id else None,
            sic_id=str(flight.sic_id) if flight.sic_id else None,
            instructor_id=str(flight.instructor_id) if flight.instructor_id else None,
            student_id=str(flight.student_id) if flight.student_id else None,
            booking_id=str(flight.booking_id) if flight.booking_id else None,
        )
        return self.publish(event)

    def publish_flight_approved(self, flight) -> bool:
        """Publish flight approved event."""
        event = FlightApprovedEvent(
            flight_id=str(flight.id),
            organization_id=str(flight.organization_id),
            approved_by=str(flight.approved_by),
            flight_date=flight.flight_date.isoformat(),
            aircraft_id=str(flight.aircraft_id),
            aircraft_registration=flight.aircraft_registration,
            departure_airport=flight.departure_airport,
            arrival_airport=flight.arrival_airport or '',
            flight_time=float(flight.flight_time or 0),
            block_time=float(flight.block_time or 0),
            hobbs_time=float(
                (flight.hobbs_end or 0) - (flight.hobbs_start or 0)
            ),
            tach_time=float(
                (flight.tach_end or 0) - (flight.tach_start or 0)
            ),
            landings=flight.total_landings,
            pic_id=str(flight.pic_id) if flight.pic_id else None,
            sic_id=str(flight.sic_id) if flight.sic_id else None,
            instructor_id=str(flight.instructor_id) if flight.instructor_id else None,
            student_id=str(flight.student_id) if flight.student_id else None,
            fuel_added_liters=float(flight.fuel_added_liters or 0),
            fuel_cost=float(flight.fuel_cost or 0),
            booking_id=str(flight.booking_id) if flight.booking_id else None,
        )
        return self.publish(event)

    def publish_flight_billing_ready(self, flight) -> bool:
        """Publish flight billing ready event."""
        event = FlightBillingReadyEvent(
            flight_id=str(flight.id),
            organization_id=str(flight.organization_id),
            booking_id=str(flight.booking_id) if flight.booking_id else None,
            aircraft_id=str(flight.aircraft_id),
            aircraft_registration=flight.aircraft_registration,
            flight_date=flight.flight_date.isoformat(),
            flight_time=float(flight.flight_time or 0),
            block_time=float(flight.block_time or 0),
            hobbs_time=float(
                (flight.hobbs_end or 0) - (flight.hobbs_start or 0)
            ),
            tach_time=float(
                (flight.tach_end or 0) - (flight.tach_start or 0)
            ),
            landings=flight.total_landings,
            fuel_added_liters=float(flight.fuel_added_liters or 0),
            fuel_cost=float(flight.fuel_cost or 0),
            pic_id=str(flight.pic_id) if flight.pic_id else None,
            instructor_id=str(flight.instructor_id) if flight.instructor_id else None,
            student_id=str(flight.student_id) if flight.student_id else None,
            flight_type=flight.flight_type,
        )
        return self.publish(event)


# Global event publisher instance
event_publisher = EventPublisher()
