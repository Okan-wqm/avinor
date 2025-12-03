# services/aircraft-service/src/common/events/publisher.py
"""
Event Publisher

Publishes events to message broker for inter-service communication.
"""

import json
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from django.conf import settings

from .definitions import AircraftEvents, EVENT_SCHEMAS

logger = logging.getLogger(__name__)


class EventPublisher:
    """
    Publisher for aircraft service events.

    Supports multiple backends:
    - Redis Pub/Sub
    - RabbitMQ
    - Kafka
    - In-memory (for testing)
    """

    def __init__(self, backend: str = None):
        self.backend = backend or getattr(settings, 'EVENT_BACKEND', 'redis')
        self._client = None
        self._initialize_client()

    def _initialize_client(self):
        """Initialize the message broker client."""
        if self.backend == 'redis':
            self._init_redis()
        elif self.backend == 'rabbitmq':
            self._init_rabbitmq()
        elif self.backend == 'kafka':
            self._init_kafka()
        elif self.backend == 'memory':
            self._init_memory()
        else:
            logger.warning(f"Unknown event backend: {self.backend}, using memory")
            self._init_memory()

    def _init_redis(self):
        """Initialize Redis client."""
        try:
            import redis
            redis_url = getattr(settings, 'REDIS_URL', 'redis://localhost:6379/0')
            self._client = redis.from_url(redis_url)
            logger.info("Redis event publisher initialized")
        except ImportError:
            logger.warning("Redis not installed, falling back to memory backend")
            self._init_memory()
        except Exception as e:
            logger.error(f"Failed to initialize Redis: {e}")
            self._init_memory()

    def _init_rabbitmq(self):
        """Initialize RabbitMQ client."""
        try:
            import pika
            rabbitmq_url = getattr(settings, 'RABBITMQ_URL', 'amqp://localhost')
            params = pika.URLParameters(rabbitmq_url)
            self._connection = pika.BlockingConnection(params)
            self._client = self._connection.channel()
            self._client.exchange_declare(
                exchange='aircraft_events',
                exchange_type='topic',
                durable=True
            )
            logger.info("RabbitMQ event publisher initialized")
        except ImportError:
            logger.warning("Pika not installed, falling back to memory backend")
            self._init_memory()
        except Exception as e:
            logger.error(f"Failed to initialize RabbitMQ: {e}")
            self._init_memory()

    def _init_kafka(self):
        """Initialize Kafka client."""
        try:
            from kafka import KafkaProducer
            kafka_servers = getattr(settings, 'KAFKA_BOOTSTRAP_SERVERS', ['localhost:9092'])
            self._client = KafkaProducer(
                bootstrap_servers=kafka_servers,
                value_serializer=lambda v: json.dumps(v).encode('utf-8')
            )
            logger.info("Kafka event publisher initialized")
        except ImportError:
            logger.warning("Kafka not installed, falling back to memory backend")
            self._init_memory()
        except Exception as e:
            logger.error(f"Failed to initialize Kafka: {e}")
            self._init_memory()

    def _init_memory(self):
        """Initialize in-memory event store (for testing)."""
        self._client = []
        self.backend = 'memory'
        logger.info("In-memory event publisher initialized")

    def publish(
        self,
        event_type: AircraftEvents,
        data: Dict[str, Any],
        correlation_id: str = None,
        metadata: Dict[str, Any] = None
    ) -> bool:
        """
        Publish an event.

        Args:
            event_type: Type of event from AircraftEvents enum
            data: Event payload data
            correlation_id: Optional correlation ID for tracing
            metadata: Optional additional metadata

        Returns:
            True if event was published successfully
        """
        # Build event envelope
        event = self._build_event(event_type, data, correlation_id, metadata)

        # Validate event data
        if not self._validate_event(event_type, data):
            logger.warning(f"Event validation failed for {event_type}")

        try:
            if self.backend == 'redis':
                return self._publish_redis(event_type, event)
            elif self.backend == 'rabbitmq':
                return self._publish_rabbitmq(event_type, event)
            elif self.backend == 'kafka':
                return self._publish_kafka(event_type, event)
            else:
                return self._publish_memory(event)
        except Exception as e:
            logger.error(f"Failed to publish event {event_type}: {e}")
            return False

    def _build_event(
        self,
        event_type: AircraftEvents,
        data: Dict[str, Any],
        correlation_id: str = None,
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Build the event envelope."""
        return {
            'event_id': str(uuid.uuid4()),
            'event_type': event_type.value,
            'source': 'aircraft-service',
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'correlation_id': correlation_id or str(uuid.uuid4()),
            'data': data,
            'metadata': metadata or {},
        }

    def _validate_event(self, event_type: AircraftEvents, data: Dict[str, Any]) -> bool:
        """Validate event data against schema."""
        schema = EVENT_SCHEMAS.get(event_type)
        if not schema:
            return True  # No schema defined, allow all

        required = schema.get('required', [])
        for field in required:
            if field not in data:
                logger.warning(f"Missing required field '{field}' for event {event_type}")
                return False

        return True

    def _publish_redis(self, event_type: AircraftEvents, event: Dict[str, Any]) -> bool:
        """Publish to Redis Pub/Sub."""
        channel = f"aircraft:{event_type.value}"
        message = json.dumps(event)
        self._client.publish(channel, message)
        logger.debug(f"Published event to Redis channel {channel}")
        return True

    def _publish_rabbitmq(self, event_type: AircraftEvents, event: Dict[str, Any]) -> bool:
        """Publish to RabbitMQ."""
        import pika
        routing_key = event_type.value.replace('.', '_')
        self._client.basic_publish(
            exchange='aircraft_events',
            routing_key=routing_key,
            body=json.dumps(event),
            properties=pika.BasicProperties(
                delivery_mode=2,  # Persistent
                content_type='application/json',
            )
        )
        logger.debug(f"Published event to RabbitMQ with routing key {routing_key}")
        return True

    def _publish_kafka(self, event_type: AircraftEvents, event: Dict[str, Any]) -> bool:
        """Publish to Kafka."""
        topic = 'aircraft-events'
        future = self._client.send(topic, event)
        future.get(timeout=10)  # Wait for confirmation
        logger.debug(f"Published event to Kafka topic {topic}")
        return True

    def _publish_memory(self, event: Dict[str, Any]) -> bool:
        """Store event in memory (for testing)."""
        self._client.append(event)
        logger.debug(f"Stored event in memory: {event['event_type']}")
        return True

    def get_memory_events(self) -> list:
        """Get all events stored in memory (for testing)."""
        if self.backend == 'memory':
            return self._client
        return []

    def clear_memory_events(self):
        """Clear memory events (for testing)."""
        if self.backend == 'memory':
            self._client.clear()

    def close(self):
        """Close the connection."""
        if self.backend == 'rabbitmq' and hasattr(self, '_connection'):
            self._connection.close()
        elif self.backend == 'kafka' and self._client:
            self._client.close()


# Global publisher instance
_publisher: Optional[EventPublisher] = None


def get_publisher() -> EventPublisher:
    """Get the global event publisher instance."""
    global _publisher
    if _publisher is None:
        _publisher = EventPublisher()
    return _publisher


def publish_event(
    event_type: AircraftEvents,
    data: Dict[str, Any],
    correlation_id: str = None
) -> bool:
    """Convenience function to publish an event."""
    return get_publisher().publish(event_type, data, correlation_id)
