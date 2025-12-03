# shared/common/events.py
"""
Event Bus and Event Handling for Microservices Communication
"""

import json
import uuid
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Callable, Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from django.conf import settings

logger = logging.getLogger(__name__)


# =============================================================================
# EVENT DATA CLASSES
# =============================================================================

@dataclass
class Event:
    """Base event class"""
    event_type: str
    data: Dict[str, Any]
    event_id: str = None
    timestamp: str = None
    source_service: str = None
    correlation_id: str = None
    version: str = "1.0"

    def __post_init__(self):
        if not self.event_id:
            self.event_id = str(uuid.uuid4())
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat()
        if not self.source_service:
            self.source_service = getattr(settings, 'SERVICE_NAME', 'unknown')

    def to_dict(self) -> Dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: Dict) -> 'Event':
        return cls(**data)

    @classmethod
    def from_json(cls, json_str: str) -> 'Event':
        return cls.from_dict(json.loads(json_str))


# =============================================================================
# EVENT TYPES
# =============================================================================

class EventTypes:
    """Event type constants"""

    # User Events
    USER_CREATED = 'user.created'
    USER_UPDATED = 'user.updated'
    USER_DELETED = 'user.deleted'
    USER_ACTIVATED = 'user.activated'
    USER_DEACTIVATED = 'user.deactivated'
    USER_LOGGED_IN = 'user.logged_in'
    USER_LOGGED_OUT = 'user.logged_out'
    USER_PASSWORD_CHANGED = 'user.password_changed'
    USER_PASSWORD_RESET = 'user.password_reset'

    # Organization Events
    ORGANIZATION_CREATED = 'organization.created'
    ORGANIZATION_UPDATED = 'organization.updated'
    ORGANIZATION_DELETED = 'organization.deleted'
    ORGANIZATION_SETTINGS_UPDATED = 'organization.settings_updated'

    # Aircraft Events
    AIRCRAFT_CREATED = 'aircraft.created'
    AIRCRAFT_UPDATED = 'aircraft.updated'
    AIRCRAFT_DELETED = 'aircraft.deleted'
    AIRCRAFT_STATUS_CHANGED = 'aircraft.status_changed'
    AIRCRAFT_GROUNDED = 'aircraft.grounded'
    AIRCRAFT_RELEASED = 'aircraft.released'
    AIRCRAFT_HOURS_UPDATED = 'aircraft.hours_updated'

    # Maintenance Events
    MAINTENANCE_SCHEDULED = 'maintenance.scheduled'
    MAINTENANCE_STARTED = 'maintenance.started'
    MAINTENANCE_COMPLETED = 'maintenance.completed'
    MAINTENANCE_CANCELLED = 'maintenance.cancelled'
    MAINTENANCE_DUE = 'maintenance.due'
    MAINTENANCE_OVERDUE = 'maintenance.overdue'
    SQUAWK_CREATED = 'maintenance.squawk_created'
    SQUAWK_RESOLVED = 'maintenance.squawk_resolved'

    # Booking Events
    BOOKING_CREATED = 'booking.created'
    BOOKING_UPDATED = 'booking.updated'
    BOOKING_CANCELLED = 'booking.cancelled'
    BOOKING_CONFIRMED = 'booking.confirmed'
    BOOKING_CHECKED_IN = 'booking.checked_in'
    BOOKING_COMPLETED = 'booking.completed'
    BOOKING_NO_SHOW = 'booking.no_show'

    # Flight Events
    FLIGHT_CREATED = 'flight.created'
    FLIGHT_UPDATED = 'flight.updated'
    FLIGHT_STARTED = 'flight.started'
    FLIGHT_COMPLETED = 'flight.completed'
    FLIGHT_APPROVED = 'flight.approved'
    FLIGHT_REJECTED = 'flight.rejected'

    # Training Events
    TRAINING_ENROLLED = 'training.enrolled'
    TRAINING_STARTED = 'training.started'
    TRAINING_COMPLETED = 'training.completed'
    LESSON_COMPLETED = 'training.lesson_completed'
    EXERCISE_EVALUATED = 'training.exercise_evaluated'
    PROGRESS_UPDATED = 'training.progress_updated'

    # Theory Events
    THEORY_ENROLLED = 'theory.enrolled'
    THEORY_COMPLETED = 'theory.completed'
    EXAM_SCHEDULED = 'theory.exam_scheduled'
    EXAM_COMPLETED = 'theory.exam_completed'
    EXAM_PASSED = 'theory.exam_passed'
    EXAM_FAILED = 'theory.exam_failed'

    # Certificate Events
    CERTIFICATE_CREATED = 'certificate.created'
    CERTIFICATE_UPDATED = 'certificate.updated'
    CERTIFICATE_EXPIRING = 'certificate.expiring'
    CERTIFICATE_EXPIRED = 'certificate.expired'
    CERTIFICATE_RENEWED = 'certificate.renewed'
    CERTIFICATE_REVOKED = 'certificate.revoked'

    # Finance Events
    PAYMENT_RECEIVED = 'finance.payment_received'
    PAYMENT_FAILED = 'finance.payment_failed'
    PAYMENT_REFUNDED = 'finance.payment_refunded'
    INVOICE_CREATED = 'finance.invoice_created'
    INVOICE_SENT = 'finance.invoice_sent'
    INVOICE_PAID = 'finance.invoice_paid'
    INVOICE_OVERDUE = 'finance.invoice_overdue'
    BALANCE_LOW = 'finance.balance_low'
    BALANCE_UPDATED = 'finance.balance_updated'

    # Document Events
    DOCUMENT_UPLOADED = 'document.uploaded'
    DOCUMENT_UPDATED = 'document.updated'
    DOCUMENT_DELETED = 'document.deleted'
    DOCUMENT_SHARED = 'document.shared'

    # Notification Events
    NOTIFICATION_CREATED = 'notification.created'
    NOTIFICATION_SENT = 'notification.sent'
    NOTIFICATION_READ = 'notification.read'


# =============================================================================
# EVENT BUS
# =============================================================================

class EventBus:
    """
    Event Bus for publishing and subscribing to events using RabbitMQ.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.connection = None
        self.channel = None
        self._connect()
        self._initialized = True

    def _connect(self):
        """Establish connection to RabbitMQ"""
        try:
            import pika

            credentials = pika.PlainCredentials(
                getattr(settings, 'RABBITMQ_USER', 'guest'),
                getattr(settings, 'RABBITMQ_PASSWORD', 'guest')
            )
            parameters = pika.ConnectionParameters(
                host=getattr(settings, 'RABBITMQ_HOST', 'localhost'),
                port=getattr(settings, 'RABBITMQ_PORT', 5672),
                virtual_host=getattr(settings, 'RABBITMQ_VHOST', '/'),
                credentials=credentials,
                heartbeat=600,
                blocked_connection_timeout=300
            )
            self.connection = pika.BlockingConnection(parameters)
            self.channel = self.connection.channel()

            # Declare exchange
            exchange_name = getattr(settings, 'EVENT_BUS', {}).get(
                'EXCHANGE_NAME', 'flight_training_events'
            )
            self.channel.exchange_declare(
                exchange=exchange_name,
                exchange_type='topic',
                durable=True
            )
            logger.info("Connected to RabbitMQ event bus")
        except ImportError:
            logger.warning("pika not installed, event bus disabled")
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")

    def publish(
        self,
        event_type: str,
        data: Dict[str, Any],
        correlation_id: str = None
    ) -> bool:
        """Publish event to the event bus"""
        try:
            if not self.channel:
                logger.warning("Event bus not connected, skipping publish")
                return False

            import pika

            event = Event(
                event_type=event_type,
                data=data,
                correlation_id=correlation_id or str(uuid.uuid4())
            )

            exchange_name = getattr(settings, 'EVENT_BUS', {}).get(
                'EXCHANGE_NAME', 'flight_training_events'
            )

            self.channel.basic_publish(
                exchange=exchange_name,
                routing_key=event_type,
                body=event.to_json(),
                properties=pika.BasicProperties(
                    delivery_mode=2,  # Persistent
                    content_type='application/json',
                    correlation_id=event.correlation_id,
                    message_id=event.event_id,
                )
            )

            logger.info(
                f"Event published: {event_type}",
                extra={
                    'event_id': event.event_id,
                    'event_type': event_type,
                    'correlation_id': event.correlation_id,
                }
            )
            return True

        except Exception as e:
            logger.error(f"Failed to publish event: {e}")
            return False

    def subscribe(
        self,
        event_types: List[str],
        callback: Callable[[Event], None],
        queue_name: str = None
    ):
        """Subscribe to events"""
        try:
            if not self.channel:
                logger.warning("Event bus not connected, skipping subscribe")
                return

            import pika

            queue_name = queue_name or f"{getattr(settings, 'SERVICE_NAME', 'service')}_queue"
            exchange_name = getattr(settings, 'EVENT_BUS', {}).get(
                'EXCHANGE_NAME', 'flight_training_events'
            )

            # Declare queue
            self.channel.queue_declare(queue=queue_name, durable=True)

            # Bind queue to exchange for each event type
            for event_type in event_types:
                self.channel.queue_bind(
                    exchange=exchange_name,
                    queue=queue_name,
                    routing_key=event_type
                )

            def on_message(ch, method, properties, body):
                try:
                    event = Event.from_json(body.decode('utf-8'))
                    logger.info(
                        f"Event received: {event.event_type}",
                        extra={
                            'event_id': event.event_id,
                            'event_type': event.event_type,
                        }
                    )
                    callback(event)
                    ch.basic_ack(delivery_tag=method.delivery_tag)
                except Exception as e:
                    logger.error(f"Error processing event: {e}")
                    ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

            self.channel.basic_qos(prefetch_count=1)
            self.channel.basic_consume(
                queue=queue_name,
                on_message_callback=on_message
            )

            logger.info(f"Subscribed to events: {event_types}")
            self.channel.start_consuming()

        except Exception as e:
            logger.error(f"Failed to subscribe to events: {e}")

    def close(self):
        """Close connection"""
        if self.connection:
            self.connection.close()
            logger.info("Event bus connection closed")


# =============================================================================
# EVENT HANDLERS
# =============================================================================

class BaseEventHandler(ABC):
    """Base class for event handlers"""

    @abstractmethod
    def handle(self, event: Event):
        """Handle the event"""
        pass


class EventDispatcher:
    """
    Dispatches events to registered handlers.
    """

    def __init__(self):
        self.handlers: Dict[str, List[BaseEventHandler]] = {}

    def register(self, event_type: str, handler: BaseEventHandler):
        """Register a handler for an event type"""
        if event_type not in self.handlers:
            self.handlers[event_type] = []
        self.handlers[event_type].append(handler)
        logger.info(f"Registered handler {handler.__class__.__name__} for {event_type}")

    def unregister(self, event_type: str, handler: BaseEventHandler):
        """Unregister a handler"""
        if event_type in self.handlers:
            self.handlers[event_type].remove(handler)

    def dispatch(self, event: Event):
        """Dispatch event to all registered handlers"""
        event_type = event.event_type

        if event_type not in self.handlers:
            logger.debug(f"No handlers registered for {event_type}")
            return

        for handler in self.handlers[event_type]:
            try:
                handler.handle(event)
            except Exception as e:
                logger.error(
                    f"Error in handler {handler.__class__.__name__}: {e}",
                    extra={'event_type': event_type, 'event_id': event.event_id}
                )


# =============================================================================
# DECORATORS
# =============================================================================

def publish_event(event_type: str):
    """
    Decorator that publishes an event after function execution.

    Usage:
        @publish_event(EventTypes.USER_CREATED)
        def create_user(data):
            user = User.objects.create(**data)
            return {'user_id': str(user.id), 'email': user.email}
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            try:
                bus = EventBus()
                bus.publish(event_type, result if isinstance(result, dict) else {'result': result})
            except Exception as e:
                logger.error(f"Failed to publish event {event_type}: {e}")
            return result
        return wrapper
    return decorator


def handle_event(*event_types: str):
    """
    Decorator to mark a function as an event handler.

    Usage:
        @handle_event(EventTypes.USER_CREATED, EventTypes.USER_UPDATED)
        def on_user_change(event: Event):
            # Handle the event
            pass
    """
    def decorator(func):
        func._event_types = event_types
        return func
    return decorator
