# services/user-service/src/apps/core/events/publisher.py
"""
Event Publisher

Handles publishing events to the message broker (RabbitMQ/Kafka).
Provides reliable event delivery with retry logic and dead letter handling.
"""

import json
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

from django.conf import settings

from .types import BaseEvent

logger = logging.getLogger(__name__)


class EventPublisher:
    """
    Event publisher for inter-service communication.

    Supports multiple backends:
    - RabbitMQ (via pika)
    - Kafka (via kafka-python)
    - Redis Pub/Sub (for development)
    - In-memory (for testing)

    Usage:
        publisher = EventPublisher()
        event = UserCreatedEvent(user_id='123', email='test@example.com')
        publisher.publish(event)
    """

    # Topic/Exchange mappings
    TOPIC_MAP = {
        'user': 'user-events',
        'role': 'role-events',
        'permission': 'permission-events',
        'session': 'session-events',
    }

    def __init__(self, backend: Optional[str] = None):
        """
        Initialize the event publisher.

        Args:
            backend: The messaging backend to use. Defaults to settings.EVENT_BACKEND
        """
        self.backend = backend or getattr(settings, 'EVENT_BACKEND', 'rabbitmq')
        self._connection = None
        self._channel = None
        self._producer = None

    def publish(self, event: BaseEvent, topic: Optional[str] = None) -> bool:
        """
        Publish an event to the message broker.

        Args:
            event: The event to publish
            topic: Optional topic override

        Returns:
            True if event was published successfully
        """
        try:
            # Determine topic from event type
            if not topic:
                topic = self._get_topic_for_event(event)

            # Serialize event
            event_data = event.to_json_serializable()

            # Publish based on backend
            if self.backend == 'rabbitmq':
                return self._publish_rabbitmq(topic, event_data)
            elif self.backend == 'kafka':
                return self._publish_kafka(topic, event_data)
            elif self.backend == 'redis':
                return self._publish_redis(topic, event_data)
            elif self.backend == 'memory':
                return self._publish_memory(topic, event_data)
            else:
                logger.warning(f"Unknown backend: {self.backend}, using memory")
                return self._publish_memory(topic, event_data)

        except Exception as e:
            logger.error(f"Failed to publish event {event.event_type}: {e}")
            # Store in outbox for retry
            self._store_in_outbox(event, topic, str(e))
            return False

    def publish_batch(self, events: List[BaseEvent], topic: Optional[str] = None) -> int:
        """
        Publish multiple events.

        Args:
            events: List of events to publish
            topic: Optional topic override

        Returns:
            Number of events successfully published
        """
        success_count = 0
        for event in events:
            if self.publish(event, topic):
                success_count += 1
        return success_count

    def _get_topic_for_event(self, event: BaseEvent) -> str:
        """Determine the topic based on event type."""
        event_type = event.event_type
        prefix = event_type.split('.')[0] if '.' in event_type else 'default'
        return self.TOPIC_MAP.get(prefix, 'user-events')

    # ==================== RABBITMQ BACKEND ====================

    def _get_rabbitmq_connection(self):
        """Get or create RabbitMQ connection."""
        if self._connection and self._connection.is_open:
            return self._connection

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

            self._connection = pika.BlockingConnection(parameters)
            self._channel = self._connection.channel()

            # Declare exchanges
            for exchange_name in self.TOPIC_MAP.values():
                self._channel.exchange_declare(
                    exchange=exchange_name,
                    exchange_type='topic',
                    durable=True
                )

            return self._connection

        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            raise

    def _publish_rabbitmq(self, topic: str, event_data: Dict[str, Any]) -> bool:
        """Publish event to RabbitMQ."""
        try:
            import pika

            self._get_rabbitmq_connection()

            routing_key = event_data.get('event_type', 'unknown')
            message = json.dumps(event_data)

            self._channel.basic_publish(
                exchange=topic,
                routing_key=routing_key,
                body=message,
                properties=pika.BasicProperties(
                    delivery_mode=2,  # Persistent
                    content_type='application/json',
                    message_id=event_data.get('event_id'),
                    timestamp=int(datetime.utcnow().timestamp()),
                    headers={
                        'source': 'user-service',
                        'version': event_data.get('version', '1.0'),
                    }
                )
            )

            logger.info(f"Published event {routing_key} to {topic}")
            return True

        except Exception as e:
            logger.error(f"RabbitMQ publish failed: {e}")
            self._connection = None
            self._channel = None
            raise

    # ==================== KAFKA BACKEND ====================

    def _get_kafka_producer(self):
        """Get or create Kafka producer."""
        if self._producer:
            return self._producer

        try:
            from kafka import KafkaProducer

            self._producer = KafkaProducer(
                bootstrap_servers=getattr(
                    settings, 'KAFKA_BOOTSTRAP_SERVERS',
                    ['localhost:9092']
                ),
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                key_serializer=lambda k: k.encode('utf-8') if k else None,
                acks='all',
                retries=3,
                max_in_flight_requests_per_connection=1,
            )

            return self._producer

        except Exception as e:
            logger.error(f"Failed to create Kafka producer: {e}")
            raise

    def _publish_kafka(self, topic: str, event_data: Dict[str, Any]) -> bool:
        """Publish event to Kafka."""
        try:
            producer = self._get_kafka_producer()

            key = event_data.get('user_id') or event_data.get('role_id') or event_data.get('event_id')

            future = producer.send(
                topic,
                key=key,
                value=event_data,
                headers=[
                    ('source', b'user-service'),
                    ('event_type', event_data.get('event_type', '').encode()),
                    ('version', event_data.get('version', '1.0').encode()),
                ]
            )

            # Wait for send to complete
            future.get(timeout=10)

            logger.info(f"Published event {event_data.get('event_type')} to Kafka topic {topic}")
            return True

        except Exception as e:
            logger.error(f"Kafka publish failed: {e}")
            self._producer = None
            raise

    # ==================== REDIS BACKEND ====================

    def _publish_redis(self, topic: str, event_data: Dict[str, Any]) -> bool:
        """Publish event to Redis Pub/Sub."""
        try:
            from django.core.cache import cache

            # Get Redis client
            redis_client = cache.client.get_client()

            channel = f"events:{topic}"
            message = json.dumps(event_data)

            redis_client.publish(channel, message)

            logger.info(f"Published event {event_data.get('event_type')} to Redis channel {channel}")
            return True

        except Exception as e:
            logger.error(f"Redis publish failed: {e}")
            raise

    # ==================== IN-MEMORY BACKEND ====================

    # In-memory event store for testing
    _memory_events: List[Dict[str, Any]] = []

    def _publish_memory(self, topic: str, event_data: Dict[str, Any]) -> bool:
        """Store event in memory (for testing)."""
        self._memory_events.append({
            'topic': topic,
            'event': event_data,
            'timestamp': datetime.utcnow().isoformat(),
        })

        logger.info(f"Stored event {event_data.get('event_type')} in memory")
        return True

    @classmethod
    def get_memory_events(cls, topic: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get events from memory store (for testing)."""
        if topic:
            return [e for e in cls._memory_events if e['topic'] == topic]
        return cls._memory_events

    @classmethod
    def clear_memory_events(cls):
        """Clear memory event store (for testing)."""
        cls._memory_events = []

    # ==================== OUTBOX PATTERN ====================

    def _store_in_outbox(self, event: BaseEvent, topic: str, error: str) -> None:
        """Store failed event in outbox for later retry."""
        try:
            from apps.core.models import EventOutbox

            EventOutbox.objects.create(
                event_id=event.event_id,
                event_type=event.event_type,
                topic=topic,
                payload=event.to_json_serializable(),
                error=error,
            )

            logger.info(f"Stored event {event.event_id} in outbox for retry")

        except Exception as e:
            logger.error(f"Failed to store event in outbox: {e}")

    def close(self):
        """Close connections."""
        if self._connection:
            try:
                self._connection.close()
            except Exception:
                pass
            self._connection = None
            self._channel = None

        if self._producer:
            try:
                self._producer.close()
            except Exception:
                pass
            self._producer = None


# Singleton instance
_publisher: Optional[EventPublisher] = None


def get_publisher() -> EventPublisher:
    """Get the singleton event publisher instance."""
    global _publisher
    if _publisher is None:
        _publisher = EventPublisher()
    return _publisher


def publish_event(event: BaseEvent, topic: Optional[str] = None) -> bool:
    """Convenience function to publish an event."""
    return get_publisher().publish(event, topic)
