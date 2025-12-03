# services/theory-service/src/apps/core/events/__init__.py
"""
Theory Service Events

Event publishing and handling for theory service.
"""

from .publishers import (
    publish_course_enrolled,
    publish_module_completed,
    publish_course_completed,
    publish_exam_started,
    publish_exam_completed,
    publish_certificate_issued,
)
from .handlers import dispatch_event, EVENT_HANDLERS

__all__ = [
    # Publishers
    'publish_course_enrolled',
    'publish_module_completed',
    'publish_course_completed',
    'publish_exam_started',
    'publish_exam_completed',
    'publish_certificate_issued',
    # Handlers
    'dispatch_event',
    'EVENT_HANDLERS',
]
