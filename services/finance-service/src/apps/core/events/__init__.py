# services/finance-service/src/apps/core/events/__init__.py
"""
Finance Service Events

Event definitions and publishers for inter-service communication.
"""

from .publishers import (
    publish_account_created,
    publish_account_updated,
    publish_account_suspended,
    publish_account_closed,
    publish_transaction_created,
    publish_payment_processed,
    publish_payment_failed,
    publish_refund_processed,
    publish_invoice_created,
    publish_invoice_sent,
    publish_invoice_paid,
    publish_invoice_overdue,
    publish_package_purchased,
    publish_package_used,
    publish_package_expired,
    publish_payment_method_added,
    publish_payment_method_expiring,
)

from .handlers import (
    handle_flight_completed,
    handle_booking_created,
    handle_booking_cancelled,
    handle_user_created,
    handle_membership_changed,
)

__all__ = [
    # Publishers
    'publish_account_created',
    'publish_account_updated',
    'publish_account_suspended',
    'publish_account_closed',
    'publish_transaction_created',
    'publish_payment_processed',
    'publish_payment_failed',
    'publish_refund_processed',
    'publish_invoice_created',
    'publish_invoice_sent',
    'publish_invoice_paid',
    'publish_invoice_overdue',
    'publish_package_purchased',
    'publish_package_used',
    'publish_package_expired',
    'publish_payment_method_added',
    'publish_payment_method_expiring',

    # Handlers
    'handle_flight_completed',
    'handle_booking_created',
    'handle_booking_cancelled',
    'handle_user_created',
    'handle_membership_changed',
]
