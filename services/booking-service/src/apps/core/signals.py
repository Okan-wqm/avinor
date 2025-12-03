# services/booking-service/src/apps/core/signals.py
"""
Django Signals for Booking Service

Handles post-save and post-delete signals for event publishing
and cross-entity updates.
"""

import logging
from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver

from .models import Booking, RecurringPattern, Availability, BookingRule, WaitlistEntry
from .events import (
    publish_booking_created,
    publish_booking_confirmed,
    publish_booking_cancelled,
    publish_booking_checked_in,
    publish_booking_dispatched,
    publish_booking_completed,
    publish_booking_no_show,
    publish_availability_changed,
    publish_waitlist_offer_sent,
    publish_waitlist_offer_accepted,
    publish_waitlist_offer_declined,
)

logger = logging.getLogger(__name__)


# ==========================================================================
# Booking Signals
# ==========================================================================

@receiver(post_save, sender=Booking)
def booking_post_save(sender, instance, created, **kwargs):
    """Handle booking post-save events."""
    if created:
        # New booking created
        publish_booking_created(instance, created_by=instance.created_by)
        logger.info(f"Booking created: {instance.booking_number}")


@receiver(pre_save, sender=Booking)
def booking_pre_save(sender, instance, **kwargs):
    """Track status changes before save."""
    if instance.pk:
        try:
            old_instance = Booking.objects.get(pk=instance.pk)
            instance._old_status = old_instance.status
        except Booking.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None


@receiver(post_save, sender=Booking)
def booking_status_change(sender, instance, created, **kwargs):
    """Handle booking status changes."""
    if created:
        return

    old_status = getattr(instance, '_old_status', None)
    new_status = instance.status

    if old_status == new_status:
        return

    # Status-specific event publishing
    if new_status == Booking.Status.CONFIRMED:
        publish_booking_confirmed(instance)
        logger.info(f"Booking confirmed: {instance.booking_number}")

    elif new_status == Booking.Status.CANCELLED:
        publish_booking_cancelled(
            instance,
            cancelled_by=instance.cancelled_by,
            cancellation_type=instance.cancellation_type,
            reason=instance.cancellation_reason
        )
        logger.info(f"Booking cancelled: {instance.booking_number}")

        # Trigger waitlist processing
        from .services import WaitlistService
        waitlist_service = WaitlistService()
        waitlist_service.process_cancellation(instance)

    elif new_status == Booking.Status.CHECKED_IN:
        publish_booking_checked_in(instance)
        logger.info(f"Booking checked in: {instance.booking_number}")

    elif new_status == Booking.Status.DISPATCHED:
        publish_booking_dispatched(
            instance,
            hobbs_out=instance.hobbs_start
        )
        logger.info(f"Booking dispatched: {instance.booking_number}")

    elif new_status == Booking.Status.COMPLETED:
        publish_booking_completed(
            instance,
            hobbs_in=instance.hobbs_end,
            flight_time=instance.actual_duration,
            actual_cost=instance.actual_cost
        )
        logger.info(f"Booking completed: {instance.booking_number}")

    elif new_status == Booking.Status.NO_SHOW:
        publish_booking_no_show(
            instance,
            fee=instance.no_show_fee
        )
        logger.info(f"Booking marked as no-show: {instance.booking_number}")


# ==========================================================================
# Availability Signals
# ==========================================================================

@receiver(post_save, sender=Availability)
def availability_post_save(sender, instance, created, **kwargs):
    """Handle availability post-save events."""
    action = 'created' if created else 'updated'
    publish_availability_changed(instance, action)

    if created:
        logger.info(
            f"Availability created for {instance.resource_type} "
            f"{instance.resource_id}: {instance.availability_type}"
        )


@receiver(post_delete, sender=Availability)
def availability_post_delete(sender, instance, **kwargs):
    """Handle availability deletion events."""
    publish_availability_changed(instance, 'deleted')
    logger.info(
        f"Availability deleted for {instance.resource_type} "
        f"{instance.resource_id}"
    )


# ==========================================================================
# Waitlist Signals
# ==========================================================================

@receiver(pre_save, sender=WaitlistEntry)
def waitlist_entry_pre_save(sender, instance, **kwargs):
    """Track status changes before save."""
    if instance.pk:
        try:
            old_instance = WaitlistEntry.objects.get(pk=instance.pk)
            instance._old_status = old_instance.status
        except WaitlistEntry.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None


@receiver(post_save, sender=WaitlistEntry)
def waitlist_entry_status_change(sender, instance, created, **kwargs):
    """Handle waitlist entry status changes."""
    old_status = getattr(instance, '_old_status', None)
    new_status = instance.status

    if old_status == new_status and not created:
        return

    # Status-specific event publishing
    if new_status == WaitlistEntry.Status.OFFERED and old_status == WaitlistEntry.Status.WAITING:
        publish_waitlist_offer_sent(instance, instance.offered_booking_id)
        logger.info(f"Waitlist offer sent to user {instance.user_id}")

    elif new_status == WaitlistEntry.Status.ACCEPTED:
        publish_waitlist_offer_accepted(instance)
        logger.info(f"Waitlist offer accepted by user {instance.user_id}")

    elif new_status == WaitlistEntry.Status.DECLINED:
        publish_waitlist_offer_declined(instance)
        logger.info(f"Waitlist offer declined by user {instance.user_id}")


# ==========================================================================
# Recurring Pattern Signals
# ==========================================================================

@receiver(post_save, sender=RecurringPattern)
def recurring_pattern_post_save(sender, instance, created, **kwargs):
    """Handle recurring pattern post-save events."""
    from .events import event_publisher, EventType

    if created:
        event_publisher.publish(
            EventType.RECURRING_PATTERN_CREATED,
            payload={
                'pattern_id': instance.id,
                'name': instance.name,
                'frequency': instance.frequency,
                'start_date': instance.start_date,
                'end_date': instance.end_date,
                'aircraft_id': instance.aircraft_id,
                'instructor_id': instance.instructor_id,
                'student_id': instance.student_id,
            },
            organization_id=instance.organization_id
        )
        logger.info(f"Recurring pattern created: {instance.name}")


@receiver(pre_save, sender=RecurringPattern)
def recurring_pattern_pre_save(sender, instance, **kwargs):
    """Track status changes before save."""
    if instance.pk:
        try:
            old_instance = RecurringPattern.objects.get(pk=instance.pk)
            instance._old_status = old_instance.status
        except RecurringPattern.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None


@receiver(post_save, sender=RecurringPattern)
def recurring_pattern_status_change(sender, instance, created, **kwargs):
    """Handle recurring pattern status changes."""
    if created:
        return

    from .events import event_publisher, EventType

    old_status = getattr(instance, '_old_status', None)
    new_status = instance.status

    if old_status == new_status:
        return

    if new_status == RecurringPattern.Status.CANCELLED:
        event_publisher.publish(
            EventType.RECURRING_PATTERN_CANCELLED,
            payload={
                'pattern_id': instance.id,
                'name': instance.name,
            },
            organization_id=instance.organization_id
        )
        logger.info(f"Recurring pattern cancelled: {instance.name}")

    elif new_status == RecurringPattern.Status.COMPLETED:
        event_publisher.publish(
            EventType.RECURRING_PATTERN_COMPLETED,
            payload={
                'pattern_id': instance.id,
                'name': instance.name,
                'occurrences_created': instance.occurrences_created,
            },
            organization_id=instance.organization_id
        )
        logger.info(f"Recurring pattern completed: {instance.name}")


# ==========================================================================
# Booking Rule Signals
# ==========================================================================

@receiver(post_save, sender=BookingRule)
def booking_rule_post_save(sender, instance, created, **kwargs):
    """Handle booking rule post-save events."""
    from .events import event_publisher, EventType

    event_type = EventType.BOOKING_RULE_CREATED if created else EventType.BOOKING_RULE_UPDATED

    event_publisher.publish(
        event_type,
        payload={
            'rule_id': instance.id,
            'name': instance.name,
            'rule_type': instance.rule_type,
            'target_type': instance.target_type,
            'target_id': instance.target_id,
            'is_active': instance.is_active,
            'priority': instance.priority,
        },
        organization_id=instance.organization_id
    )

    if created:
        logger.info(f"Booking rule created: {instance.name}")
    else:
        logger.info(f"Booking rule updated: {instance.name}")


@receiver(post_delete, sender=BookingRule)
def booking_rule_post_delete(sender, instance, **kwargs):
    """Handle booking rule deletion events."""
    from .events import event_publisher, EventType

    event_publisher.publish(
        EventType.BOOKING_RULE_DELETED,
        payload={
            'rule_id': instance.id,
            'name': instance.name,
        },
        organization_id=instance.organization_id
    )
    logger.info(f"Booking rule deleted: {instance.name}")
