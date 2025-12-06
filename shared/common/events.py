# shared/common/events.py
"""
Event Bus and Event Handling for Microservices Communication
Using NATS as the message broker with JetStream for persistence.
"""

import json
import uuid
import logging
import asyncio
import threading
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Callable, Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from functools import wraps
from concurrent.futures import ThreadPoolExecutor

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
# NATS CONFIGURATION
# =============================================================================

class NATSConfig:
    """NATS connection configuration"""

    def __init__(self):
        self.servers = getattr(settings, 'NATS_SERVERS', ['nats://localhost:4222'])
        self.user = getattr(settings, 'NATS_USER', None)
        self.password = getattr(settings, 'NATS_PASSWORD', None)
        self.token = getattr(settings, 'NATS_TOKEN', None)
        self.connect_timeout = getattr(settings, 'NATS_CONNECT_TIMEOUT', 10)
        self.reconnect_time_wait = getattr(settings, 'NATS_RECONNECT_TIME_WAIT', 2)
        self.max_reconnect_attempts = getattr(settings, 'NATS_MAX_RECONNECT_ATTEMPTS', 60)
        self.stream_name = getattr(settings, 'NATS_STREAM_NAME', 'FTMS_EVENTS')
        self.stream_subjects = getattr(settings, 'NATS_STREAM_SUBJECTS', ['ftms.>'])

    def get_connect_options(self) -> Dict[str, Any]:
        """Get NATS connection options"""
        options = {
            'servers': self.servers,
            'connect_timeout': self.connect_timeout,
            'reconnect_time_wait': self.reconnect_time_wait,
            'max_reconnect_attempts': self.max_reconnect_attempts,
            'error_cb': self._error_callback,
            'disconnected_cb': self._disconnected_callback,
            'reconnected_cb': self._reconnected_callback,
            'closed_cb': self._closed_callback,
        }

        if self.user and self.password:
            options['user'] = self.user
            options['password'] = self.password
        elif self.token:
            options['token'] = self.token

        return options

    async def _error_callback(self, error):
        logger.error(f"NATS error: {error}")

    async def _disconnected_callback(self):
        logger.warning("Disconnected from NATS")

    async def _reconnected_callback(self):
        logger.info("Reconnected to NATS")

    async def _closed_callback(self):
        logger.info("NATS connection closed")


# =============================================================================
# NATS EVENT BUS
# =============================================================================

class EventBus:
    """
    Event Bus for publishing and subscribing to events using NATS with JetStream.

    NATS provides:
    - High performance (millions of messages per second)
    - Low latency (sub-millisecond)
    - At-most-once and at-least-once delivery via JetStream
    - Subject-based addressing with wildcards
    - Built-in load balancing
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._nc = None  # NATS connection
        self._js = None  # JetStream context
        self._loop = None
        self._executor = ThreadPoolExecutor(max_workers=4)
        self._config = NATSConfig()
        self._subscriptions = []
        self._initialized = True

    def _get_or_create_loop(self):
        """Get existing event loop or create a new one"""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop

    async def _connect_async(self):
        """Establish async connection to NATS"""
        try:
            import nats
            from nats.js.api import StreamConfig, RetentionPolicy, StorageType

            if self._nc is not None and self._nc.is_connected:
                return True

            self._nc = await nats.connect(**self._config.get_connect_options())

            # Create JetStream context
            self._js = self._nc.jetstream()

            # Create or update stream for persistent messaging
            try:
                await self._js.add_stream(
                    config=StreamConfig(
                        name=self._config.stream_name,
                        subjects=self._config.stream_subjects,
                        retention=RetentionPolicy.LIMITS,
                        storage=StorageType.FILE,
                        max_msgs=1000000,
                        max_bytes=1024 * 1024 * 1024,  # 1GB
                        max_age=7 * 24 * 60 * 60,  # 7 days in seconds
                        max_msg_size=1024 * 1024,  # 1MB per message
                        duplicate_window=120,  # 2 minutes dedup window
                        num_replicas=1,
                    )
                )
                logger.info(f"Created/updated JetStream stream: {self._config.stream_name}")
            except Exception as e:
                # Stream might already exist with different config
                logger.debug(f"Stream setup note: {e}")

            logger.info(f"Connected to NATS at {self._config.servers}")
            return True

        except ImportError:
            logger.warning("nats-py not installed, event bus disabled. Install with: pip install nats-py")
            return False
        except Exception as e:
            logger.error(f"Failed to connect to NATS: {e}")
            return False

    def _connect(self):
        """Synchronous connection wrapper"""
        loop = self._get_or_create_loop()
        try:
            if loop.is_running():
                future = asyncio.run_coroutine_threadsafe(self._connect_async(), loop)
                return future.result(timeout=30)
            else:
                return loop.run_until_complete(self._connect_async())
        except Exception as e:
            logger.error(f"Failed to connect to NATS: {e}")
            return False

    def _event_type_to_subject(self, event_type: str) -> str:
        """Convert event type to NATS subject format"""
        # user.created -> ftms.user.created
        return f"ftms.{event_type}"

    def _subject_to_event_type(self, subject: str) -> str:
        """Convert NATS subject to event type format"""
        # ftms.user.created -> user.created
        if subject.startswith("ftms."):
            return subject[5:]
        return subject

    async def _publish_async(
        self,
        event_type: str,
        data: Dict[str, Any],
        correlation_id: str = None
    ) -> bool:
        """Publish event asynchronously"""
        try:
            if not await self._connect_async():
                logger.warning("Event bus not connected, skipping publish")
                return False

            event = Event(
                event_type=event_type,
                data=data,
                correlation_id=correlation_id or str(uuid.uuid4())
            )

            subject = self._event_type_to_subject(event_type)

            # Publish to JetStream for persistence
            ack = await self._js.publish(
                subject,
                event.to_json().encode('utf-8'),
                headers={
                    'Nats-Msg-Id': event.event_id,  # For deduplication
                    'correlation-id': event.correlation_id,
                    'source-service': event.source_service,
                }
            )

            logger.info(
                f"Event published: {event_type}",
                extra={
                    'event_id': event.event_id,
                    'event_type': event_type,
                    'correlation_id': event.correlation_id,
                    'stream': ack.stream,
                    'seq': ack.seq,
                }
            )
            return True

        except Exception as e:
            logger.error(f"Failed to publish event: {e}")
            return False

    def publish(
        self,
        event_type: str,
        data: Dict[str, Any],
        correlation_id: str = None
    ) -> bool:
        """Publish event to the event bus (synchronous wrapper)"""
        loop = self._get_or_create_loop()
        try:
            if loop.is_running():
                future = asyncio.run_coroutine_threadsafe(
                    self._publish_async(event_type, data, correlation_id),
                    loop
                )
                return future.result(timeout=30)
            else:
                return loop.run_until_complete(
                    self._publish_async(event_type, data, correlation_id)
                )
        except Exception as e:
            logger.error(f"Failed to publish event: {e}")
            return False

    async def _subscribe_async(
        self,
        event_types: List[str],
        callback: Callable[[Event], None],
        queue_name: str = None,
        durable_name: str = None
    ):
        """Subscribe to events asynchronously with JetStream"""
        try:
            if not await self._connect_async():
                logger.warning("Event bus not connected, skipping subscribe")
                return

            from nats.js.api import ConsumerConfig, AckPolicy, DeliverPolicy

            service_name = getattr(settings, 'SERVICE_NAME', 'service')
            queue_name = queue_name or f"{service_name}_queue"
            durable_name = durable_name or f"{service_name}_consumer"

            async def message_handler(msg):
                try:
                    event = Event.from_json(msg.data.decode('utf-8'))
                    logger.info(
                        f"Event received: {event.event_type}",
                        extra={
                            'event_id': event.event_id,
                            'event_type': event.event_type,
                            'subject': msg.subject,
                        }
                    )

                    # Call the callback
                    if asyncio.iscoroutinefunction(callback):
                        await callback(event)
                    else:
                        await asyncio.get_event_loop().run_in_executor(
                            self._executor, callback, event
                        )

                    # Acknowledge the message
                    await msg.ack()

                except Exception as e:
                    logger.error(f"Error processing event: {e}")
                    # Negative acknowledge - will be redelivered
                    await msg.nak(delay=5)  # Retry after 5 seconds

            # Subscribe to each event type
            for event_type in event_types:
                subject = self._event_type_to_subject(event_type)

                # Create durable consumer for each event type
                consumer_name = f"{durable_name}_{event_type.replace('.', '_')}"

                try:
                    sub = await self._js.subscribe(
                        subject,
                        queue=queue_name,
                        durable=consumer_name,
                        cb=message_handler,
                        config=ConsumerConfig(
                            ack_policy=AckPolicy.EXPLICIT,
                            deliver_policy=DeliverPolicy.ALL,
                            max_deliver=5,  # Max redelivery attempts
                            ack_wait=30,  # 30 seconds to acknowledge
                        )
                    )
                    self._subscriptions.append(sub)
                    logger.info(f"Subscribed to: {subject} (queue: {queue_name})")

                except Exception as e:
                    logger.error(f"Failed to subscribe to {subject}: {e}")

            logger.info(f"Subscribed to events: {event_types}")

        except Exception as e:
            logger.error(f"Failed to subscribe to events: {e}")

    def subscribe(
        self,
        event_types: List[str],
        callback: Callable[[Event], None],
        queue_name: str = None
    ):
        """Subscribe to events (synchronous wrapper that starts consuming)"""
        loop = self._get_or_create_loop()
        try:
            if loop.is_running():
                future = asyncio.run_coroutine_threadsafe(
                    self._subscribe_async(event_types, callback, queue_name),
                    loop
                )
                future.result(timeout=30)
            else:
                loop.run_until_complete(
                    self._subscribe_async(event_types, callback, queue_name)
                )
                # Keep running to process messages
                loop.run_forever()
        except Exception as e:
            logger.error(f"Failed to subscribe to events: {e}")

    async def _request_async(
        self,
        event_type: str,
        data: Dict[str, Any],
        timeout: float = 10.0
    ) -> Optional[Event]:
        """
        Request-Reply pattern for synchronous communication.
        Useful for queries or RPC-style calls.
        """
        try:
            if not await self._connect_async():
                return None

            event = Event(
                event_type=event_type,
                data=data,
            )

            subject = self._event_type_to_subject(event_type)

            response = await self._nc.request(
                subject,
                event.to_json().encode('utf-8'),
                timeout=timeout
            )

            return Event.from_json(response.data.decode('utf-8'))

        except Exception as e:
            logger.error(f"Request failed: {e}")
            return None

    def request(
        self,
        event_type: str,
        data: Dict[str, Any],
        timeout: float = 10.0
    ) -> Optional[Event]:
        """Request-Reply pattern (synchronous wrapper)"""
        loop = self._get_or_create_loop()
        try:
            if loop.is_running():
                future = asyncio.run_coroutine_threadsafe(
                    self._request_async(event_type, data, timeout),
                    loop
                )
                return future.result(timeout=timeout + 5)
            else:
                return loop.run_until_complete(
                    self._request_async(event_type, data, timeout)
                )
        except Exception as e:
            logger.error(f"Request failed: {e}")
            return None

    async def _close_async(self):
        """Close connection asynchronously"""
        try:
            # Unsubscribe from all subscriptions
            for sub in self._subscriptions:
                await sub.unsubscribe()
            self._subscriptions.clear()

            # Drain and close connection
            if self._nc:
                await self._nc.drain()
                logger.info("Event bus connection closed")
        except Exception as e:
            logger.error(f"Error closing connection: {e}")

    def close(self):
        """Close connection"""
        loop = self._get_or_create_loop()
        try:
            if loop.is_running():
                future = asyncio.run_coroutine_threadsafe(self._close_async(), loop)
                future.result(timeout=10)
            else:
                loop.run_until_complete(self._close_async())
        except Exception as e:
            logger.error(f"Error closing connection: {e}")


# =============================================================================
# ASYNC EVENT BUS (for async Django views and Celery tasks)
# =============================================================================

class AsyncEventBus:
    """
    Async-native Event Bus for use in async contexts.
    Use this directly in async views, Celery tasks, or management commands.
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
        self._nc = None
        self._js = None
        self._config = NATSConfig()
        self._subscriptions = []
        self._initialized = True

    async def connect(self) -> bool:
        """Connect to NATS"""
        try:
            import nats
            from nats.js.api import StreamConfig, RetentionPolicy, StorageType

            if self._nc is not None and self._nc.is_connected:
                return True

            self._nc = await nats.connect(**self._config.get_connect_options())
            self._js = self._nc.jetstream()

            # Ensure stream exists
            try:
                await self._js.add_stream(
                    config=StreamConfig(
                        name=self._config.stream_name,
                        subjects=self._config.stream_subjects,
                        retention=RetentionPolicy.LIMITS,
                        storage=StorageType.FILE,
                        max_msgs=1000000,
                        max_bytes=1024 * 1024 * 1024,
                        max_age=7 * 24 * 60 * 60,
                        num_replicas=1,
                    )
                )
            except Exception:
                pass  # Stream exists

            logger.info("AsyncEventBus connected to NATS")
            return True

        except ImportError:
            logger.warning("nats-py not installed")
            return False
        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            return False

    async def publish(
        self,
        event_type: str,
        data: Dict[str, Any],
        correlation_id: str = None
    ) -> bool:
        """Publish event"""
        if not await self.connect():
            return False

        try:
            event = Event(
                event_type=event_type,
                data=data,
                correlation_id=correlation_id or str(uuid.uuid4())
            )

            subject = f"ftms.{event_type}"

            await self._js.publish(
                subject,
                event.to_json().encode('utf-8'),
                headers={'Nats-Msg-Id': event.event_id}
            )

            logger.info(f"Event published: {event_type}")
            return True

        except Exception as e:
            logger.error(f"Publish failed: {e}")
            return False

    async def close(self):
        """Close connection"""
        if self._nc:
            await self._nc.drain()


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
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            try:
                bus = EventBus()
                bus.publish(event_type, result if isinstance(result, dict) else {'result': result})
            except Exception as e:
                logger.error(f"Failed to publish event {event_type}: {e}")
            return result

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)
            try:
                bus = AsyncEventBus()
                await bus.publish(event_type, result if isinstance(result, dict) else {'result': result})
            except Exception as e:
                logger.error(f"Failed to publish event {event_type}: {e}")
            return result

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
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


# =============================================================================
# MANAGEMENT COMMAND HELPER
# =============================================================================

def run_event_consumer(
    event_types: List[str],
    handler: Callable[[Event], None],
    queue_name: str = None
):
    """
    Helper function to run an event consumer.
    Use this in Django management commands.

    Usage:
        # In management/commands/consume_events.py
        from shared.common.events import run_event_consumer, EventTypes

        class Command(BaseCommand):
            def handle(self, *args, **options):
                def handler(event):
                    print(f"Received: {event.event_type}")

                run_event_consumer(
                    [EventTypes.USER_CREATED, EventTypes.USER_UPDATED],
                    handler
                )
    """
    async def run():
        import nats
        from nats.js.api import ConsumerConfig, AckPolicy

        config = NATSConfig()
        nc = await nats.connect(**config.get_connect_options())
        js = nc.jetstream()

        service_name = getattr(settings, 'SERVICE_NAME', 'service')
        queue = queue_name or f"{service_name}_queue"

        async def message_handler(msg):
            try:
                event = Event.from_json(msg.data.decode('utf-8'))
                logger.info(f"Processing: {event.event_type}")

                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)

                await msg.ack()
            except Exception as e:
                logger.error(f"Error: {e}")
                await msg.nak(delay=5)

        for event_type in event_types:
            subject = f"ftms.{event_type}"
            durable = f"{service_name}_{event_type.replace('.', '_')}"

            await js.subscribe(
                subject,
                queue=queue,
                durable=durable,
                cb=message_handler,
                config=ConsumerConfig(
                    ack_policy=AckPolicy.EXPLICIT,
                    max_deliver=5,
                    ack_wait=30,
                )
            )
            logger.info(f"Subscribed to: {subject}")

        logger.info(f"Consumer started. Listening for: {event_types}")

        # Keep running
        while True:
            await asyncio.sleep(1)

    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        logger.info("Consumer stopped")
