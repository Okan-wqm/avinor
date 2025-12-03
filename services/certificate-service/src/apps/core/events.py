# services/certificate-service/src/apps/core/events.py
"""
Certificate Service Events

Event definitions and handlers for certificate service.
Uses Redis pub/sub for inter-service communication.
"""

import json
import logging
from datetime import datetime, date
from decimal import Decimal
from typing import Any, Dict, Optional
from uuid import UUID

from django.conf import settings

logger = logging.getLogger(__name__)


class DateTimeEncoder(json.JSONEncoder):
    """JSON encoder for datetime and UUID objects."""

    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, date):
            return obj.isoformat()
        if isinstance(obj, UUID):
            return str(obj)
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)


class EventTypes:
    """Certificate service event type definitions."""

    # Certificate events
    CERTIFICATE_CREATED = 'certificate.created'
    CERTIFICATE_UPDATED = 'certificate.updated'
    CERTIFICATE_VERIFIED = 'certificate.verified'
    CERTIFICATE_SUSPENDED = 'certificate.suspended'
    CERTIFICATE_REVOKED = 'certificate.revoked'
    CERTIFICATE_REINSTATED = 'certificate.reinstated'
    CERTIFICATE_RENEWED = 'certificate.renewed'
    CERTIFICATE_EXPIRING = 'certificate.expiring'
    CERTIFICATE_EXPIRED = 'certificate.expired'

    # Medical certificate events
    MEDICAL_CREATED = 'medical.created'
    MEDICAL_UPDATED = 'medical.updated'
    MEDICAL_EXPIRING = 'medical.expiring'
    MEDICAL_EXPIRED = 'medical.expired'
    MEDICAL_SUSPENDED = 'medical.suspended'

    # Rating events
    RATING_CREATED = 'rating.created'
    RATING_UPDATED = 'rating.updated'
    RATING_PROFICIENCY_RECORDED = 'rating.proficiency_recorded'
    RATING_RENEWED = 'rating.renewed'
    RATING_SUSPENDED = 'rating.suspended'
    RATING_EXPIRING = 'rating.expiring'
    RATING_PROFICIENCY_DUE = 'rating.proficiency_due'

    # Endorsement events
    ENDORSEMENT_CREATED = 'endorsement.created'
    ENDORSEMENT_SIGNED = 'endorsement.signed'
    ENDORSEMENT_REVOKED = 'endorsement.revoked'
    ENDORSEMENT_EXPIRING = 'endorsement.expiring'
    ENDORSEMENT_EXPIRED = 'endorsement.expired'

    # Currency events
    CURRENCY_UPDATED = 'currency.updated'
    CURRENCY_CURRENT = 'currency.current'
    CURRENCY_EXPIRING = 'currency.expiring'
    CURRENCY_EXPIRED = 'currency.expired'

    # Validity events
    VALIDITY_CHECK_PASSED = 'validity.check_passed'
    VALIDITY_CHECK_FAILED = 'validity.check_failed'
    PILOT_GROUNDED = 'validity.pilot_grounded'
    PILOT_CLEARED = 'validity.pilot_cleared'

    # Compliance events
    COMPLIANCE_ISSUE_DETECTED = 'compliance.issue_detected'
    COMPLIANCE_ISSUE_RESOLVED = 'compliance.issue_resolved'


class EventPublisher:
    """
    Event publisher for certificate service.

    Publishes events to Redis pub/sub for inter-service communication.
    """

    def __init__(self):
        self._redis_client = None
        self._channel_prefix = 'certificate_service'

    @property
    def redis_client(self):
        """Lazy load Redis client."""
        if self._redis_client is None:
            try:
                import redis
                self._redis_client = redis.from_url(
                    settings.REDIS_URL,
                    decode_responses=True
                )
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {e}")
                self._redis_client = None
        return self._redis_client

    def publish(
        self,
        event_type: str,
        data: Dict[str, Any],
        organization_id: Optional[UUID] = None
    ) -> bool:
        """
        Publish an event to Redis.

        Args:
            event_type: Type of event
            data: Event data
            organization_id: Optional organization context

        Returns:
            bool: True if published successfully
        """
        try:
            event = {
                'event_type': event_type,
                'timestamp': datetime.utcnow().isoformat(),
                'service': 'certificate-service',
                'organization_id': str(organization_id) if organization_id else None,
                'data': data
            }

            channel = f"{self._channel_prefix}:{event_type}"
            message = json.dumps(event, cls=DateTimeEncoder)

            if self.redis_client:
                self.redis_client.publish(channel, message)
                logger.info(f"Published event: {event_type}")
                return True
            else:
                logger.warning(f"Redis not available, event not published: {event_type}")
                return False

        except Exception as e:
            logger.error(f"Failed to publish event {event_type}: {e}")
            return False

    # Certificate event publishers
    def certificate_created(self, certificate_id: UUID, user_id: UUID, certificate_type: str, **kwargs):
        """Publish certificate created event."""
        return self.publish(
            EventTypes.CERTIFICATE_CREATED,
            {
                'certificate_id': str(certificate_id),
                'user_id': str(user_id),
                'certificate_type': certificate_type,
                **kwargs
            },
            organization_id=kwargs.get('organization_id')
        )

    def certificate_verified(self, certificate_id: UUID, user_id: UUID, verified_by: UUID, **kwargs):
        """Publish certificate verified event."""
        return self.publish(
            EventTypes.CERTIFICATE_VERIFIED,
            {
                'certificate_id': str(certificate_id),
                'user_id': str(user_id),
                'verified_by': str(verified_by),
                **kwargs
            },
            organization_id=kwargs.get('organization_id')
        )

    def certificate_suspended(self, certificate_id: UUID, user_id: UUID, reason: str, **kwargs):
        """Publish certificate suspended event."""
        return self.publish(
            EventTypes.CERTIFICATE_SUSPENDED,
            {
                'certificate_id': str(certificate_id),
                'user_id': str(user_id),
                'reason': reason,
                **kwargs
            },
            organization_id=kwargs.get('organization_id')
        )

    def certificate_expiring(self, certificate_id: UUID, user_id: UUID, expiry_date: date, days_remaining: int, **kwargs):
        """Publish certificate expiring event."""
        return self.publish(
            EventTypes.CERTIFICATE_EXPIRING,
            {
                'certificate_id': str(certificate_id),
                'user_id': str(user_id),
                'expiry_date': expiry_date.isoformat(),
                'days_remaining': days_remaining,
                **kwargs
            },
            organization_id=kwargs.get('organization_id')
        )

    # Medical event publishers
    def medical_created(self, medical_id: UUID, user_id: UUID, medical_class: str, **kwargs):
        """Publish medical certificate created event."""
        return self.publish(
            EventTypes.MEDICAL_CREATED,
            {
                'medical_id': str(medical_id),
                'user_id': str(user_id),
                'medical_class': medical_class,
                **kwargs
            },
            organization_id=kwargs.get('organization_id')
        )

    def medical_expiring(self, medical_id: UUID, user_id: UUID, expiry_date: date, days_remaining: int, **kwargs):
        """Publish medical expiring event."""
        return self.publish(
            EventTypes.MEDICAL_EXPIRING,
            {
                'medical_id': str(medical_id),
                'user_id': str(user_id),
                'expiry_date': expiry_date.isoformat(),
                'days_remaining': days_remaining,
                **kwargs
            },
            organization_id=kwargs.get('organization_id')
        )

    # Rating event publishers
    def rating_created(self, rating_id: UUID, user_id: UUID, rating_type: str, **kwargs):
        """Publish rating created event."""
        return self.publish(
            EventTypes.RATING_CREATED,
            {
                'rating_id': str(rating_id),
                'user_id': str(user_id),
                'rating_type': rating_type,
                **kwargs
            },
            organization_id=kwargs.get('organization_id')
        )

    def rating_proficiency_recorded(self, rating_id: UUID, user_id: UUID, check_date: date, passed: bool, **kwargs):
        """Publish rating proficiency check recorded event."""
        return self.publish(
            EventTypes.RATING_PROFICIENCY_RECORDED,
            {
                'rating_id': str(rating_id),
                'user_id': str(user_id),
                'check_date': check_date.isoformat(),
                'passed': passed,
                **kwargs
            },
            organization_id=kwargs.get('organization_id')
        )

    # Endorsement event publishers
    def endorsement_created(self, endorsement_id: UUID, student_id: UUID, instructor_id: UUID, endorsement_type: str, **kwargs):
        """Publish endorsement created event."""
        return self.publish(
            EventTypes.ENDORSEMENT_CREATED,
            {
                'endorsement_id': str(endorsement_id),
                'student_id': str(student_id),
                'instructor_id': str(instructor_id),
                'endorsement_type': endorsement_type,
                **kwargs
            },
            organization_id=kwargs.get('organization_id')
        )

    def endorsement_signed(self, endorsement_id: UUID, student_id: UUID, instructor_id: UUID, **kwargs):
        """Publish endorsement signed event."""
        return self.publish(
            EventTypes.ENDORSEMENT_SIGNED,
            {
                'endorsement_id': str(endorsement_id),
                'student_id': str(student_id),
                'instructor_id': str(instructor_id),
                **kwargs
            },
            organization_id=kwargs.get('organization_id')
        )

    # Currency event publishers
    def currency_updated(self, user_id: UUID, currency_type: str, status: str, expiry_date: Optional[date], **kwargs):
        """Publish currency updated event."""
        return self.publish(
            EventTypes.CURRENCY_UPDATED,
            {
                'user_id': str(user_id),
                'currency_type': currency_type,
                'status': status,
                'expiry_date': expiry_date.isoformat() if expiry_date else None,
                **kwargs
            },
            organization_id=kwargs.get('organization_id')
        )

    def currency_expired(self, user_id: UUID, currency_type: str, **kwargs):
        """Publish currency expired event."""
        return self.publish(
            EventTypes.CURRENCY_EXPIRED,
            {
                'user_id': str(user_id),
                'currency_type': currency_type,
                **kwargs
            },
            organization_id=kwargs.get('organization_id')
        )

    # Validity event publishers
    def validity_check_failed(self, user_id: UUID, reason: str, failed_checks: list, **kwargs):
        """Publish validity check failed event."""
        return self.publish(
            EventTypes.VALIDITY_CHECK_FAILED,
            {
                'user_id': str(user_id),
                'reason': reason,
                'failed_checks': failed_checks,
                **kwargs
            },
            organization_id=kwargs.get('organization_id')
        )

    def pilot_grounded(self, user_id: UUID, reason: str, grounding_items: list, **kwargs):
        """Publish pilot grounded event."""
        return self.publish(
            EventTypes.PILOT_GROUNDED,
            {
                'user_id': str(user_id),
                'reason': reason,
                'grounding_items': grounding_items,
                **kwargs
            },
            organization_id=kwargs.get('organization_id')
        )


class EventHandler:
    """
    Event handler for processing incoming events from other services.
    """

    def __init__(self):
        self._handlers = {}
        self._register_handlers()

    def _register_handlers(self):
        """Register event handlers."""
        # Flight service events
        self._handlers['flight.completed'] = self._handle_flight_completed
        self._handlers['flight.logged'] = self._handle_flight_logged

        # User service events
        self._handlers['user.updated'] = self._handle_user_updated

        # Training service events
        self._handlers['training.completed'] = self._handle_training_completed
        self._handlers['checkride.passed'] = self._handle_checkride_passed

    def handle(self, event_type: str, data: Dict[str, Any]) -> bool:
        """
        Handle an incoming event.

        Args:
            event_type: Type of event
            data: Event data

        Returns:
            bool: True if handled successfully
        """
        handler = self._handlers.get(event_type)
        if handler:
            try:
                handler(data)
                logger.info(f"Handled event: {event_type}")
                return True
            except Exception as e:
                logger.error(f"Failed to handle event {event_type}: {e}")
                return False
        else:
            logger.debug(f"No handler for event: {event_type}")
            return False

    def _handle_flight_completed(self, data: Dict[str, Any]):
        """Handle flight completed event - update currency."""
        from .services import CurrencyService

        user_id = UUID(data['user_id'])
        flight_id = UUID(data['flight_id'])
        flight_date = data['flight_date']

        service = CurrencyService()
        service.update_currency_from_flight(
            user_id=user_id,
            flight_id=flight_id,
            flight_date=flight_date,
            **data.get('currency_data', {})
        )

    def _handle_flight_logged(self, data: Dict[str, Any]):
        """Handle flight logged event - update currency."""
        # Similar to flight completed
        self._handle_flight_completed(data)

    def _handle_user_updated(self, data: Dict[str, Any]):
        """Handle user updated event."""
        # Update user info in certificates if needed
        pass

    def _handle_training_completed(self, data: Dict[str, Any]):
        """Handle training completed event."""
        # May create endorsements automatically
        pass

    def _handle_checkride_passed(self, data: Dict[str, Any]):
        """Handle checkride passed event - create certificate."""
        # May create/update certificates
        pass


# Global instances
event_publisher = EventPublisher()
event_handler = EventHandler()
