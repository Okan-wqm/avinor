# services/training-service/src/apps/core/events/publishers.py
"""
Event Publishers

Functions for publishing training service events to message broker.
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from uuid import UUID

logger = logging.getLogger(__name__)


class EventPublisher:
    """
    Event publisher for training service.

    Publishes events to message broker (RabbitMQ/Redis).
    """

    def __init__(self, connection=None):
        """Initialize publisher with connection."""
        self.connection = connection
        self.exchange = 'training_events'

    def publish(
        self,
        event_type: str,
        data: Dict[str, Any],
        routing_key: str = None
    ) -> bool:
        """
        Publish an event to the message broker.

        Args:
            event_type: Type of event
            data: Event data
            routing_key: Optional routing key

        Returns:
            True if published successfully
        """
        event = {
            'event_type': event_type,
            'timestamp': datetime.utcnow().isoformat(),
            'service': 'training-service',
            'data': data,
        }

        # Serialize UUIDs
        event_json = json.dumps(event, default=str)

        try:
            # TODO: Implement actual message broker publishing
            # For now, just log the event
            logger.info(
                f"Publishing event: {event_type}",
                extra={'event': event}
            )
            return True

        except Exception as e:
            logger.error(
                f"Failed to publish event {event_type}: {e}",
                extra={'event': event}
            )
            return False


# Global publisher instance
_publisher = EventPublisher()


def get_publisher() -> EventPublisher:
    """Get the global event publisher instance."""
    return _publisher


# =============================================================================
# Enrollment Events
# =============================================================================

def publish_enrollment_created(
    enrollment_id: UUID,
    organization_id: UUID,
    student_id: UUID,
    program_id: UUID,
    enrollment_number: str
) -> bool:
    """
    Publish enrollment created event.

    Args:
        enrollment_id: Enrollment UUID
        organization_id: Organization UUID
        student_id: Student UUID
        program_id: Program UUID
        enrollment_number: Enrollment number

    Returns:
        True if published successfully
    """
    return get_publisher().publish(
        event_type='training.enrollment.created',
        data={
            'enrollment_id': enrollment_id,
            'organization_id': organization_id,
            'student_id': student_id,
            'program_id': program_id,
            'enrollment_number': enrollment_number,
        },
        routing_key='training.enrollment.created'
    )


def publish_enrollment_activated(
    enrollment_id: UUID,
    organization_id: UUID,
    student_id: UUID,
    program_id: UUID,
    start_date: str
) -> bool:
    """
    Publish enrollment activated event.

    Args:
        enrollment_id: Enrollment UUID
        organization_id: Organization UUID
        student_id: Student UUID
        program_id: Program UUID
        start_date: Training start date

    Returns:
        True if published successfully
    """
    return get_publisher().publish(
        event_type='training.enrollment.activated',
        data={
            'enrollment_id': enrollment_id,
            'organization_id': organization_id,
            'student_id': student_id,
            'program_id': program_id,
            'start_date': start_date,
        },
        routing_key='training.enrollment.activated'
    )


def publish_enrollment_completed(
    enrollment_id: UUID,
    organization_id: UUID,
    student_id: UUID,
    program_id: UUID,
    program_code: str,
    completion_date: str,
    total_flight_hours: float,
    average_grade: Optional[float]
) -> bool:
    """
    Publish enrollment completed event.

    Args:
        enrollment_id: Enrollment UUID
        organization_id: Organization UUID
        student_id: Student UUID
        program_id: Program UUID
        program_code: Program code
        completion_date: Completion date
        total_flight_hours: Total flight hours
        average_grade: Average grade

    Returns:
        True if published successfully
    """
    return get_publisher().publish(
        event_type='training.enrollment.completed',
        data={
            'enrollment_id': enrollment_id,
            'organization_id': organization_id,
            'student_id': student_id,
            'program_id': program_id,
            'program_code': program_code,
            'completion_date': completion_date,
            'total_flight_hours': total_flight_hours,
            'average_grade': average_grade,
        },
        routing_key='training.enrollment.completed'
    )


def publish_enrollment_withdrawn(
    enrollment_id: UUID,
    organization_id: UUID,
    student_id: UUID,
    program_id: UUID,
    reason: str,
    withdrawal_date: str
) -> bool:
    """
    Publish enrollment withdrawn event.

    Args:
        enrollment_id: Enrollment UUID
        organization_id: Organization UUID
        student_id: Student UUID
        program_id: Program UUID
        reason: Withdrawal reason
        withdrawal_date: Withdrawal date

    Returns:
        True if published successfully
    """
    return get_publisher().publish(
        event_type='training.enrollment.withdrawn',
        data={
            'enrollment_id': enrollment_id,
            'organization_id': organization_id,
            'student_id': student_id,
            'program_id': program_id,
            'reason': reason,
            'withdrawal_date': withdrawal_date,
        },
        routing_key='training.enrollment.withdrawn'
    )


# =============================================================================
# Lesson Events
# =============================================================================

def publish_lesson_completed(
    completion_id: UUID,
    enrollment_id: UUID,
    organization_id: UUID,
    student_id: UUID,
    lesson_id: UUID,
    lesson_code: str,
    instructor_id: Optional[UUID],
    grade: Optional[float],
    result: str,
    flight_hours: float,
    ground_hours: float
) -> bool:
    """
    Publish lesson completed event.

    Args:
        completion_id: Completion UUID
        enrollment_id: Enrollment UUID
        organization_id: Organization UUID
        student_id: Student UUID
        lesson_id: Lesson UUID
        lesson_code: Lesson code
        instructor_id: Instructor UUID
        grade: Lesson grade
        result: Pass/Fail result
        flight_hours: Flight hours logged
        ground_hours: Ground hours logged

    Returns:
        True if published successfully
    """
    return get_publisher().publish(
        event_type='training.lesson.completed',
        data={
            'completion_id': completion_id,
            'enrollment_id': enrollment_id,
            'organization_id': organization_id,
            'student_id': student_id,
            'lesson_id': lesson_id,
            'lesson_code': lesson_code,
            'instructor_id': instructor_id,
            'grade': grade,
            'result': result,
            'flight_hours': flight_hours,
            'ground_hours': ground_hours,
        },
        routing_key='training.lesson.completed'
    )


# =============================================================================
# Stage Check Events
# =============================================================================

def publish_stage_check_passed(
    check_id: UUID,
    enrollment_id: UUID,
    organization_id: UUID,
    student_id: UUID,
    stage_id: UUID,
    stage_name: str,
    examiner_id: Optional[UUID],
    overall_grade: Optional[float],
    check_date: str
) -> bool:
    """
    Publish stage check passed event.

    Args:
        check_id: Stage check UUID
        enrollment_id: Enrollment UUID
        organization_id: Organization UUID
        student_id: Student UUID
        stage_id: Stage UUID
        stage_name: Stage name
        examiner_id: Examiner UUID
        overall_grade: Overall grade
        check_date: Check date

    Returns:
        True if published successfully
    """
    return get_publisher().publish(
        event_type='training.stage_check.passed',
        data={
            'check_id': check_id,
            'enrollment_id': enrollment_id,
            'organization_id': organization_id,
            'student_id': student_id,
            'stage_id': stage_id,
            'stage_name': stage_name,
            'examiner_id': examiner_id,
            'overall_grade': overall_grade,
            'check_date': check_date,
        },
        routing_key='training.stage_check.passed'
    )


def publish_stage_check_failed(
    check_id: UUID,
    enrollment_id: UUID,
    organization_id: UUID,
    student_id: UUID,
    stage_id: UUID,
    stage_name: str,
    examiner_id: Optional[UUID],
    attempt_number: int,
    can_retry: bool,
    check_date: str
) -> bool:
    """
    Publish stage check failed event.

    Args:
        check_id: Stage check UUID
        enrollment_id: Enrollment UUID
        organization_id: Organization UUID
        student_id: Student UUID
        stage_id: Stage UUID
        stage_name: Stage name
        examiner_id: Examiner UUID
        attempt_number: Attempt number
        can_retry: Whether student can retry
        check_date: Check date

    Returns:
        True if published successfully
    """
    return get_publisher().publish(
        event_type='training.stage_check.failed',
        data={
            'check_id': check_id,
            'enrollment_id': enrollment_id,
            'organization_id': organization_id,
            'student_id': student_id,
            'stage_id': stage_id,
            'stage_name': stage_name,
            'examiner_id': examiner_id,
            'attempt_number': attempt_number,
            'can_retry': can_retry,
            'check_date': check_date,
        },
        routing_key='training.stage_check.failed'
    )


# =============================================================================
# Progress Events
# =============================================================================

def publish_progress_updated(
    enrollment_id: UUID,
    organization_id: UUID,
    student_id: UUID,
    program_id: UUID,
    completion_percentage: float,
    lessons_completed: int,
    lessons_total: int,
    current_stage_id: Optional[UUID],
    total_flight_hours: float
) -> bool:
    """
    Publish progress updated event.

    Args:
        enrollment_id: Enrollment UUID
        organization_id: Organization UUID
        student_id: Student UUID
        program_id: Program UUID
        completion_percentage: Completion percentage
        lessons_completed: Lessons completed count
        lessons_total: Total lessons count
        current_stage_id: Current stage UUID
        total_flight_hours: Total flight hours

    Returns:
        True if published successfully
    """
    return get_publisher().publish(
        event_type='training.progress.updated',
        data={
            'enrollment_id': enrollment_id,
            'organization_id': organization_id,
            'student_id': student_id,
            'program_id': program_id,
            'completion_percentage': completion_percentage,
            'lessons_completed': lessons_completed,
            'lessons_total': lessons_total,
            'current_stage_id': current_stage_id,
            'total_flight_hours': total_flight_hours,
        },
        routing_key='training.progress.updated'
    )
