# services/theory-service/src/apps/core/events/publishers.py
"""
Event Publishers

Functions for publishing events to other services.
"""

import logging
from typing import Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


def _publish_event(event_type: str, data: Dict[str, Any]) -> None:
    """
    Publish an event to the message broker.

    Args:
        event_type: Type of event
        data: Event data payload
    """
    # Add metadata
    event = {
        'type': event_type,
        'timestamp': datetime.utcnow().isoformat(),
        'service': 'theory-service',
        'data': data
    }

    # In production, this would publish to RabbitMQ/Kafka
    # For now, just log the event
    logger.info(f"Publishing event: {event_type}", extra={'event_data': event})

    # TODO: Implement actual message broker publishing
    # Example with RabbitMQ:
    # channel.basic_publish(
    #     exchange='events',
    #     routing_key=event_type,
    #     body=json.dumps(event)
    # )


def publish_course_enrolled(
    organization_id: str,
    enrollment_id: str,
    user_id: str,
    course_id: str
) -> None:
    """
    Publish course enrolled event.

    Args:
        organization_id: Organization ID
        enrollment_id: Enrollment ID
        user_id: User ID
        course_id: Course ID
    """
    _publish_event('theory.course_enrolled', {
        'organization_id': organization_id,
        'enrollment_id': enrollment_id,
        'user_id': user_id,
        'course_id': course_id
    })


def publish_module_completed(
    organization_id: str,
    enrollment_id: str,
    module_id: str,
    user_id: str,
    course_id: str
) -> None:
    """
    Publish module completed event.

    Args:
        organization_id: Organization ID
        enrollment_id: Enrollment ID
        module_id: Module ID
        user_id: User ID
        course_id: Course ID
    """
    _publish_event('theory.module_completed', {
        'organization_id': organization_id,
        'enrollment_id': enrollment_id,
        'module_id': module_id,
        'user_id': user_id,
        'course_id': course_id
    })


def publish_course_completed(
    organization_id: str,
    enrollment_id: str,
    user_id: str,
    course_id: str,
    score: float
) -> None:
    """
    Publish course completed event.

    Args:
        organization_id: Organization ID
        enrollment_id: Enrollment ID
        user_id: User ID
        course_id: Course ID
        score: Final score
    """
    _publish_event('theory.course_completed', {
        'organization_id': organization_id,
        'enrollment_id': enrollment_id,
        'user_id': user_id,
        'course_id': course_id,
        'score': score
    })


def publish_exam_started(
    organization_id: str,
    attempt_id: str,
    user_id: str,
    exam_id: str
) -> None:
    """
    Publish exam started event.

    Args:
        organization_id: Organization ID
        attempt_id: Attempt ID
        user_id: User ID
        exam_id: Exam ID
    """
    _publish_event('theory.exam_started', {
        'organization_id': organization_id,
        'attempt_id': attempt_id,
        'user_id': user_id,
        'exam_id': exam_id
    })


def publish_exam_completed(
    organization_id: str,
    attempt_id: str,
    user_id: str,
    exam_id: str,
    passed: bool,
    score: float
) -> None:
    """
    Publish exam completed event.

    Args:
        organization_id: Organization ID
        attempt_id: Attempt ID
        user_id: User ID
        exam_id: Exam ID
        passed: Whether passed
        score: Score percentage
    """
    _publish_event('theory.exam_completed', {
        'organization_id': organization_id,
        'attempt_id': attempt_id,
        'user_id': user_id,
        'exam_id': exam_id,
        'passed': passed,
        'score': score
    })


def publish_exam_passed(
    organization_id: str,
    attempt_id: str,
    user_id: str,
    exam_id: str,
    course_id: str,
    score: float
) -> None:
    """
    Publish exam passed event (for final exams).

    Args:
        organization_id: Organization ID
        attempt_id: Attempt ID
        user_id: User ID
        exam_id: Exam ID
        course_id: Course ID
        score: Score percentage
    """
    _publish_event('theory.exam_passed', {
        'organization_id': organization_id,
        'attempt_id': attempt_id,
        'user_id': user_id,
        'exam_id': exam_id,
        'course_id': course_id,
        'score': score
    })


def publish_certificate_issued(
    organization_id: str,
    certificate_id: str,
    user_id: str,
    course_id: str
) -> None:
    """
    Publish certificate issued event.

    Args:
        organization_id: Organization ID
        certificate_id: Certificate ID
        user_id: User ID
        course_id: Course ID
    """
    _publish_event('theory.certificate_issued', {
        'organization_id': organization_id,
        'certificate_id': certificate_id,
        'user_id': user_id,
        'course_id': course_id
    })


def publish_certificate_revoked(
    organization_id: str,
    certificate_id: str,
    user_id: str,
    reason: str
) -> None:
    """
    Publish certificate revoked event.

    Args:
        organization_id: Organization ID
        certificate_id: Certificate ID
        user_id: User ID
        reason: Revocation reason
    """
    _publish_event('theory.certificate_revoked', {
        'organization_id': organization_id,
        'certificate_id': certificate_id,
        'user_id': user_id,
        'reason': reason
    })


def publish_question_flagged(
    organization_id: str,
    question_id: str,
    flagged_by: str,
    reason: str
) -> None:
    """
    Publish question flagged event.

    Args:
        organization_id: Organization ID
        question_id: Question ID
        flagged_by: User ID who flagged
        reason: Flag reason
    """
    _publish_event('theory.question_flagged', {
        'organization_id': organization_id,
        'question_id': question_id,
        'flagged_by': flagged_by,
        'reason': reason
    })
