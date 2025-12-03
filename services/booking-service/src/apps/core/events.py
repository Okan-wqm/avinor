# services/booking-service/src/apps/core/events.py
"""
Booking Service Events

Event definitions and publishing for the booking service.
Integrates with the event bus for cross-service communication.
"""

import json
import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Optional
from uuid import UUID

from django.conf import settings

logger = logging.getLogger(__name__)


class EventType:
    """Event type constants for booking service."""

    # Booking lifecycle events
    BOOKING_CREATED = 'booking.created'
    BOOKING_UPDATED = 'booking.updated'
    BOOKING_CONFIRMED = 'booking.confirmed'
    BOOKING_CANCELLED = 'booking.cancelled'
    BOOKING_CHECKED_IN = 'booking.checked_in'
    BOOKING_DISPATCHED = 'booking.dispatched'
    BOOKING_STARTED = 'booking.started'
    BOOKING_COMPLETED = 'booking.completed'
    BOOKING_NO_SHOW = 'booking.no_show'

    # Recurring pattern events
    RECURRING_PATTERN_CREATED = 'recurring_pattern.created'
    RECURRING_PATTERN_UPDATED = 'recurring_pattern.updated'
    RECURRING_PATTERN_CANCELLED = 'recurring_pattern.cancelled'
    RECURRING_PATTERN_COMPLETED = 'recurring_pattern.completed'

    # Availability events
    AVAILABILITY_CREATED = 'availability.created'
    AVAILABILITY_UPDATED = 'availability.updated'
    AVAILABILITY_DELETED = 'availability.deleted'

    # Waitlist events
    WAITLIST_ENTRY_CREATED = 'waitlist.entry_created'
    WAITLIST_OFFER_SENT = 'waitlist.offer_sent'
    WAITLIST_OFFER_ACCEPTED = 'waitlist.offer_accepted'
    WAITLIST_OFFER_DECLINED = 'waitlist.offer_declined'
    WAITLIST_OFFER_EXPIRED = 'waitlist.offer_expired'
    WAITLIST_ENTRY_FULFILLED = 'waitlist.entry_fulfilled'

    # Rule events
    BOOKING_RULE_CREATED = 'booking_rule.created'
    BOOKING_RULE_UPDATED = 'booking_rule.updated'
    BOOKING_RULE_DELETED = 'booking_rule.deleted'


class JSONEncoder(json.JSONEncoder):
    """Custom JSON encoder for event payloads."""

    def default(self, obj):
        if isinstance(obj, UUID):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)


class EventPublisher:
    """
    Event publisher for booking service.

    Publishes events to the message bus for consumption by other services.
    """

    def __init__(self):
        self.service_name = 'booking-service'
        self.enabled = getattr(settings, 'EVENT_PUBLISHING_ENABLED', True)

    def publish(
        self,
        event_type: str,
        payload: Dict[str, Any],
        organization_id: UUID = None,
        correlation_id: str = None,
        metadata: Dict[str, Any] = None
    ) -> bool:
        """
        Publish an event to the message bus.

        Args:
            event_type: Type of event (e.g., 'booking.created')
            payload: Event data
            organization_id: Organization context
            correlation_id: Optional correlation ID for tracing
            metadata: Additional metadata

        Returns:
            True if published successfully, False otherwise
        """
        if not self.enabled:
            logger.debug(f"Event publishing disabled, skipping: {event_type}")
            return False

        event = {
            'event_type': event_type,
            'service': self.service_name,
            'timestamp': datetime.utcnow().isoformat(),
            'organization_id': str(organization_id) if organization_id else None,
            'correlation_id': correlation_id,
            'payload': payload,
            'metadata': metadata or {},
        }

        try:
            # Serialize event
            event_json = json.dumps(event, cls=JSONEncoder)

            # In production, this would publish to RabbitMQ, Kafka, or Redis
            # For now, we log and potentially call a webhook
            logger.info(f"Publishing event: {event_type}", extra={
                'event_type': event_type,
                'organization_id': str(organization_id) if organization_id else None,
            })

            # Attempt to publish via configured backend
            self._publish_to_backend(event_type, event_json)

            return True

        except Exception as e:
            logger.error(f"Failed to publish event {event_type}: {e}")
            return False

    def _publish_to_backend(self, event_type: str, event_json: str):
        """Publish to the configured message backend."""
        backend = getattr(settings, 'EVENT_BACKEND', 'log')

        if backend == 'rabbitmq':
            self._publish_rabbitmq(event_type, event_json)
        elif backend == 'redis':
            self._publish_redis(event_type, event_json)
        elif backend == 'webhook':
            self._publish_webhook(event_type, event_json)
        else:
            # Default: just log
            logger.debug(f"Event payload: {event_json[:500]}...")

    def _publish_rabbitmq(self, event_type: str, event_json: str):
        """Publish to RabbitMQ."""
        try:
            import pika

            connection_params = pika.ConnectionParameters(
                host=getattr(settings, 'RABBITMQ_HOST', 'localhost'),
                port=getattr(settings, 'RABBITMQ_PORT', 5672),
                credentials=pika.PlainCredentials(
                    getattr(settings, 'RABBITMQ_USER', 'guest'),
                    getattr(settings, 'RABBITMQ_PASSWORD', 'guest')
                )
            )

            connection = pika.BlockingConnection(connection_params)
            channel = connection.channel()

            exchange = getattr(settings, 'RABBITMQ_EXCHANGE', 'avinor_events')
            channel.exchange_declare(exchange=exchange, exchange_type='topic', durable=True)

            channel.basic_publish(
                exchange=exchange,
                routing_key=event_type,
                body=event_json,
                properties=pika.BasicProperties(
                    delivery_mode=2,  # Persistent
                    content_type='application/json',
                )
            )

            connection.close()

        except ImportError:
            logger.warning("pika not installed, cannot publish to RabbitMQ")
        except Exception as e:
            logger.error(f"RabbitMQ publish error: {e}")

    def _publish_redis(self, event_type: str, event_json: str):
        """Publish to Redis pub/sub."""
        try:
            import redis

            r = redis.Redis(
                host=getattr(settings, 'REDIS_HOST', 'localhost'),
                port=getattr(settings, 'REDIS_PORT', 6379),
                db=getattr(settings, 'REDIS_DB', 0)
            )

            channel = f"events:{event_type}"
            r.publish(channel, event_json)

        except ImportError:
            logger.warning("redis not installed, cannot publish to Redis")
        except Exception as e:
            logger.error(f"Redis publish error: {e}")

    def _publish_webhook(self, event_type: str, event_json: str):
        """Publish via webhook."""
        try:
            import requests

            webhook_url = getattr(settings, 'EVENT_WEBHOOK_URL', None)
            if not webhook_url:
                return

            response = requests.post(
                webhook_url,
                data=event_json,
                headers={'Content-Type': 'application/json'},
                timeout=5
            )
            response.raise_for_status()

        except ImportError:
            logger.warning("requests not installed, cannot publish webhook")
        except Exception as e:
            logger.error(f"Webhook publish error: {e}")


# Global event publisher instance
event_publisher = EventPublisher()


# Convenience functions for publishing specific events
def publish_booking_created(booking, created_by: UUID = None):
    """Publish booking created event."""
    event_publisher.publish(
        EventType.BOOKING_CREATED,
        payload={
            'booking_id': booking.id,
            'booking_number': booking.booking_number,
            'booking_type': booking.booking_type,
            'status': booking.status,
            'aircraft_id': booking.aircraft_id,
            'instructor_id': booking.instructor_id,
            'student_id': booking.student_id,
            'scheduled_start': booking.scheduled_start,
            'scheduled_end': booking.scheduled_end,
            'location_id': booking.location_id,
            'created_by': created_by,
        },
        organization_id=booking.organization_id
    )


def publish_booking_confirmed(booking, confirmed_by: UUID = None):
    """Publish booking confirmed event."""
    event_publisher.publish(
        EventType.BOOKING_CONFIRMED,
        payload={
            'booking_id': booking.id,
            'booking_number': booking.booking_number,
            'aircraft_id': booking.aircraft_id,
            'instructor_id': booking.instructor_id,
            'student_id': booking.student_id,
            'scheduled_start': booking.scheduled_start,
            'scheduled_end': booking.scheduled_end,
            'confirmed_by': confirmed_by,
        },
        organization_id=booking.organization_id
    )


def publish_booking_cancelled(
    booking,
    cancelled_by: UUID = None,
    cancellation_type: str = None,
    reason: str = None,
    fee: Decimal = None
):
    """Publish booking cancelled event."""
    event_publisher.publish(
        EventType.BOOKING_CANCELLED,
        payload={
            'booking_id': booking.id,
            'booking_number': booking.booking_number,
            'aircraft_id': booking.aircraft_id,
            'instructor_id': booking.instructor_id,
            'student_id': booking.student_id,
            'scheduled_start': booking.scheduled_start,
            'cancelled_by': cancelled_by,
            'cancellation_type': cancellation_type,
            'reason': reason,
            'cancellation_fee': fee,
        },
        organization_id=booking.organization_id
    )


def publish_booking_checked_in(booking, checked_in_by: UUID = None):
    """Publish booking check-in event."""
    event_publisher.publish(
        EventType.BOOKING_CHECKED_IN,
        payload={
            'booking_id': booking.id,
            'booking_number': booking.booking_number,
            'aircraft_id': booking.aircraft_id,
            'checked_in_by': checked_in_by,
            'check_in_time': datetime.utcnow(),
        },
        organization_id=booking.organization_id
    )


def publish_booking_dispatched(booking, dispatched_by: UUID = None, hobbs_out: Decimal = None):
    """Publish booking dispatched event."""
    event_publisher.publish(
        EventType.BOOKING_DISPATCHED,
        payload={
            'booking_id': booking.id,
            'booking_number': booking.booking_number,
            'aircraft_id': booking.aircraft_id,
            'instructor_id': booking.instructor_id,
            'student_id': booking.student_id,
            'dispatched_by': dispatched_by,
            'dispatch_time': datetime.utcnow(),
            'hobbs_out': hobbs_out,
        },
        organization_id=booking.organization_id
    )


def publish_booking_completed(
    booking,
    completed_by: UUID = None,
    hobbs_in: Decimal = None,
    flight_time: Decimal = None,
    actual_cost: Decimal = None
):
    """Publish booking completed event."""
    event_publisher.publish(
        EventType.BOOKING_COMPLETED,
        payload={
            'booking_id': booking.id,
            'booking_number': booking.booking_number,
            'aircraft_id': booking.aircraft_id,
            'instructor_id': booking.instructor_id,
            'student_id': booking.student_id,
            'completed_by': completed_by,
            'completion_time': datetime.utcnow(),
            'actual_start': booking.actual_start,
            'actual_end': booking.actual_end,
            'hobbs_start': booking.hobbs_start,
            'hobbs_end': hobbs_in,
            'flight_time': flight_time,
            'actual_cost': actual_cost,
        },
        organization_id=booking.organization_id
    )


def publish_booking_no_show(booking, marked_by: UUID = None, fee: Decimal = None):
    """Publish booking no-show event."""
    event_publisher.publish(
        EventType.BOOKING_NO_SHOW,
        payload={
            'booking_id': booking.id,
            'booking_number': booking.booking_number,
            'aircraft_id': booking.aircraft_id,
            'instructor_id': booking.instructor_id,
            'student_id': booking.student_id,
            'marked_by': marked_by,
            'no_show_fee': fee,
        },
        organization_id=booking.organization_id
    )


def publish_waitlist_offer_sent(entry, booking_id: UUID):
    """Publish waitlist offer sent event."""
    event_publisher.publish(
        EventType.WAITLIST_OFFER_SENT,
        payload={
            'waitlist_entry_id': entry.id,
            'user_id': entry.user_id,
            'user_email': entry.user_email,
            'offered_booking_id': booking_id,
            'offer_expires_at': entry.offer_expires_at,
            'offer_message': entry.offer_message,
        },
        organization_id=entry.organization_id
    )


def publish_waitlist_offer_accepted(entry):
    """Publish waitlist offer accepted event."""
    event_publisher.publish(
        EventType.WAITLIST_OFFER_ACCEPTED,
        payload={
            'waitlist_entry_id': entry.id,
            'user_id': entry.user_id,
            'accepted_booking_id': entry.accepted_booking_id,
        },
        organization_id=entry.organization_id
    )


def publish_waitlist_offer_declined(entry):
    """Publish waitlist offer declined event."""
    event_publisher.publish(
        EventType.WAITLIST_OFFER_DECLINED,
        payload={
            'waitlist_entry_id': entry.id,
            'user_id': entry.user_id,
            'declined_booking_id': entry.offered_booking_id,
        },
        organization_id=entry.organization_id
    )


def publish_availability_changed(availability, action: str):
    """Publish availability changed event."""
    event_type = {
        'created': EventType.AVAILABILITY_CREATED,
        'updated': EventType.AVAILABILITY_UPDATED,
        'deleted': EventType.AVAILABILITY_DELETED,
    }.get(action, EventType.AVAILABILITY_UPDATED)

    event_publisher.publish(
        event_type,
        payload={
            'availability_id': availability.id,
            'resource_type': availability.resource_type,
            'resource_id': availability.resource_id,
            'availability_type': availability.availability_type,
            'start_datetime': availability.start_datetime,
            'end_datetime': availability.end_datetime,
            'reason': availability.reason,
        },
        organization_id=availability.organization_id
    )
