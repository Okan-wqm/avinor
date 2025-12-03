# services/organization-service/src/apps/core/events/publisher.py
"""
Event Publisher

Handles publishing events to message broker (RabbitMQ/Redis).
Supports multiple backends with fallback to local/async processing.
"""

import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Callable
from functools import lru_cache
from enum import Enum

from django.conf import settings

from .definitions import CloudEvent

logger = logging.getLogger(__name__)


# =============================================================================
# Publisher Backend Enum
# =============================================================================

class PublisherBackend(str, Enum):
    """Supported event publisher backends."""

    RABBITMQ = 'rabbitmq'
    REDIS = 'redis'
    KAFKA = 'kafka'
    MEMORY = 'memory'  # For testing
    LOGGING = 'logging'  # Log only, no actual publishing


# =============================================================================
# Abstract Publisher Interface
# =============================================================================

class BaseEventPublisher(ABC):
    """Abstract base class for event publishers."""

    @abstractmethod
    def publish(self, event: CloudEvent, routing_key: Optional[str] = None) -> bool:
        """
        Publish a single event.

        Args:
            event: CloudEvent to publish
            routing_key: Optional routing key override

        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    def publish_batch(self, events: List[CloudEvent], routing_key: Optional[str] = None) -> int:
        """
        Publish multiple events.

        Args:
            events: List of CloudEvents to publish
            routing_key: Optional routing key override

        Returns:
            Number of successfully published events
        """
        pass

    @abstractmethod
    def close(self) -> None:
        """Close connection and cleanup resources."""
        pass


# =============================================================================
# RabbitMQ Publisher
# =============================================================================

class RabbitMQPublisher(BaseEventPublisher):
    """Event publisher using RabbitMQ."""

    def __init__(self):
        self.connection = None
        self.channel = None
        self.exchange = getattr(settings, 'RABBITMQ_EXCHANGE', 'organization_events')
        self._connect()

    def _connect(self) -> None:
        """Establish connection to RabbitMQ."""
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
                blocked_connection_timeout=300,
            )

            self.connection = pika.BlockingConnection(parameters)
            self.channel = self.connection.channel()

            # Declare exchange
            self.channel.exchange_declare(
                exchange=self.exchange,
                exchange_type='topic',
                durable=True
            )

            logger.info(f"Connected to RabbitMQ exchange: {self.exchange}")

        except ImportError:
            logger.error("pika library not installed. Install with: pip install pika")
            raise
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            raise

    def publish(self, event: CloudEvent, routing_key: Optional[str] = None) -> bool:
        """Publish event to RabbitMQ."""
        try:
            import pika

            if not routing_key:
                routing_key = event.type

            message = json.dumps(event.to_dict())

            self.channel.basic_publish(
                exchange=self.exchange,
                routing_key=routing_key,
                body=message,
                properties=pika.BasicProperties(
                    delivery_mode=2,  # Persistent
                    content_type='application/json',
                    message_id=event.id,
                )
            )

            logger.debug(f"Published event {event.id} to {routing_key}")
            return True

        except Exception as e:
            logger.error(f"Failed to publish event {event.id}: {e}")
            return False

    def publish_batch(self, events: List[CloudEvent], routing_key: Optional[str] = None) -> int:
        """Publish multiple events to RabbitMQ."""
        success_count = 0
        for event in events:
            if self.publish(event, routing_key):
                success_count += 1
        return success_count

    def close(self) -> None:
        """Close RabbitMQ connection."""
        if self.connection and not self.connection.is_closed:
            self.connection.close()
            logger.info("RabbitMQ connection closed")


# =============================================================================
# Redis Publisher
# =============================================================================

class RedisPublisher(BaseEventPublisher):
    """Event publisher using Redis Pub/Sub."""

    def __init__(self):
        self.client = None
        self.channel_prefix = getattr(settings, 'REDIS_EVENT_CHANNEL_PREFIX', 'org_events')
        self._connect()

    def _connect(self) -> None:
        """Establish connection to Redis."""
        try:
            import redis

            self.client = redis.Redis(
                host=getattr(settings, 'REDIS_HOST', 'localhost'),
                port=getattr(settings, 'REDIS_PORT', 6379),
                db=getattr(settings, 'REDIS_EVENT_DB', 1),
                password=getattr(settings, 'REDIS_PASSWORD', None),
                decode_responses=True,
            )

            # Test connection
            self.client.ping()
            logger.info("Connected to Redis for event publishing")

        except ImportError:
            logger.error("redis library not installed. Install with: pip install redis")
            raise
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    def publish(self, event: CloudEvent, routing_key: Optional[str] = None) -> bool:
        """Publish event to Redis channel."""
        try:
            channel = routing_key or f"{self.channel_prefix}:{event.type}"
            message = json.dumps(event.to_dict())

            self.client.publish(channel, message)

            logger.debug(f"Published event {event.id} to channel {channel}")
            return True

        except Exception as e:
            logger.error(f"Failed to publish event {event.id}: {e}")
            return False

    def publish_batch(self, events: List[CloudEvent], routing_key: Optional[str] = None) -> int:
        """Publish multiple events to Redis."""
        success_count = 0
        pipeline = self.client.pipeline()

        for event in events:
            try:
                channel = routing_key or f"{self.channel_prefix}:{event.type}"
                message = json.dumps(event.to_dict())
                pipeline.publish(channel, message)
                success_count += 1
            except Exception as e:
                logger.error(f"Failed to add event {event.id} to pipeline: {e}")

        try:
            pipeline.execute()
        except Exception as e:
            logger.error(f"Failed to execute pipeline: {e}")
            return 0

        return success_count

    def close(self) -> None:
        """Close Redis connection."""
        if self.client:
            self.client.close()
            logger.info("Redis connection closed")


# =============================================================================
# Logging Publisher (for development/debugging)
# =============================================================================

class LoggingPublisher(BaseEventPublisher):
    """Event publisher that logs events (for development)."""

    def publish(self, event: CloudEvent, routing_key: Optional[str] = None) -> bool:
        """Log event details."""
        logger.info(
            f"EVENT: {event.type} | "
            f"ID: {event.id} | "
            f"Subject: {event.subject} | "
            f"Data: {json.dumps(event.data)[:500]}"
        )
        return True

    def publish_batch(self, events: List[CloudEvent], routing_key: Optional[str] = None) -> int:
        """Log multiple events."""
        for event in events:
            self.publish(event, routing_key)
        return len(events)

    def close(self) -> None:
        """No-op for logging publisher."""
        pass


# =============================================================================
# In-Memory Publisher (for testing)
# =============================================================================

class MemoryPublisher(BaseEventPublisher):
    """In-memory event publisher for testing."""

    def __init__(self):
        self.events: List[CloudEvent] = []
        self.handlers: Dict[str, List[Callable]] = {}

    def publish(self, event: CloudEvent, routing_key: Optional[str] = None) -> bool:
        """Store event in memory and call handlers."""
        self.events.append(event)

        # Call registered handlers
        key = routing_key or event.type
        for handler in self.handlers.get(key, []):
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Handler error for {key}: {e}")

        return True

    def publish_batch(self, events: List[CloudEvent], routing_key: Optional[str] = None) -> int:
        """Store multiple events in memory."""
        for event in events:
            self.publish(event, routing_key)
        return len(events)

    def subscribe(self, event_type: str, handler: Callable) -> None:
        """Subscribe to events of a specific type."""
        if event_type not in self.handlers:
            self.handlers[event_type] = []
        self.handlers[event_type].append(handler)

    def get_events(self, event_type: Optional[str] = None) -> List[CloudEvent]:
        """Get published events, optionally filtered by type."""
        if event_type:
            return [e for e in self.events if e.type == event_type]
        return self.events

    def clear(self) -> None:
        """Clear all stored events."""
        self.events.clear()

    def close(self) -> None:
        """Clear events on close."""
        self.clear()


# =============================================================================
# Publisher Factory
# =============================================================================

class EventPublisher:
    """
    High-level event publisher with automatic backend selection.

    Usage:
        publisher = EventPublisher()
        publisher.publish(event)
    """

    _instance: Optional['EventPublisher'] = None

    def __init__(self, backend: Optional[PublisherBackend] = None):
        """
        Initialize publisher with specified or configured backend.

        Args:
            backend: Optional backend override
        """
        if backend is None:
            backend_name = getattr(settings, 'EVENT_PUBLISHER_BACKEND', 'logging')
            backend = PublisherBackend(backend_name)

        self.backend_type = backend
        self._publisher = self._create_publisher(backend)

    def _create_publisher(self, backend: PublisherBackend) -> BaseEventPublisher:
        """Create publisher instance for specified backend."""
        publishers = {
            PublisherBackend.RABBITMQ: RabbitMQPublisher,
            PublisherBackend.REDIS: RedisPublisher,
            PublisherBackend.MEMORY: MemoryPublisher,
            PublisherBackend.LOGGING: LoggingPublisher,
        }

        publisher_class = publishers.get(backend)
        if not publisher_class:
            logger.warning(f"Unknown backend {backend}, falling back to logging")
            publisher_class = LoggingPublisher

        try:
            return publisher_class()
        except Exception as e:
            logger.error(f"Failed to create {backend} publisher: {e}. Falling back to logging.")
            return LoggingPublisher()

    def publish(self, event: CloudEvent, routing_key: Optional[str] = None) -> bool:
        """Publish event."""
        return self._publisher.publish(event, routing_key)

    def publish_batch(self, events: List[CloudEvent], routing_key: Optional[str] = None) -> int:
        """Publish multiple events."""
        return self._publisher.publish_batch(events, routing_key)

    def close(self) -> None:
        """Close publisher connection."""
        self._publisher.close()


# =============================================================================
# Global Publisher Access
# =============================================================================

_global_publisher: Optional[EventPublisher] = None


def get_event_publisher() -> EventPublisher:
    """Get or create global event publisher instance."""
    global _global_publisher
    if _global_publisher is None:
        _global_publisher = EventPublisher()
    return _global_publisher


def publish_event(event: CloudEvent, routing_key: Optional[str] = None) -> bool:
    """
    Convenience function to publish an event using global publisher.

    Args:
        event: CloudEvent to publish
        routing_key: Optional routing key

    Returns:
        True if successful
    """
    return get_event_publisher().publish(event, routing_key)


def close_publisher() -> None:
    """Close global publisher."""
    global _global_publisher
    if _global_publisher:
        _global_publisher.close()
        _global_publisher = None
