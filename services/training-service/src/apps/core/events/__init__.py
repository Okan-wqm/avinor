# services/training-service/src/apps/core/events/__init__.py
"""
Training Service Events

Event definitions and handlers for training service.
"""

from .publishers import (
    publish_enrollment_created,
    publish_enrollment_activated,
    publish_enrollment_completed,
    publish_enrollment_withdrawn,
    publish_lesson_completed,
    publish_stage_check_passed,
    publish_stage_check_failed,
    publish_progress_updated,
)

from .handlers import (
    handle_flight_completed,
    handle_booking_confirmed,
    handle_user_created,
)

__all__ = [
    # Publishers
    'publish_enrollment_created',
    'publish_enrollment_activated',
    'publish_enrollment_completed',
    'publish_enrollment_withdrawn',
    'publish_lesson_completed',
    'publish_stage_check_passed',
    'publish_stage_check_failed',
    'publish_progress_updated',

    # Handlers
    'handle_flight_completed',
    'handle_booking_confirmed',
    'handle_user_created',
]
