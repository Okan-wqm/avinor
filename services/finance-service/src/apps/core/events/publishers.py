# services/finance-service/src/apps/core/events/publishers.py
"""
Finance Service Event Publishers

Publishes events to Redis pub/sub for inter-service communication.
"""

import json
import logging
from typing import Dict, Any
from datetime import datetime
from django.conf import settings

logger = logging.getLogger(__name__)


def get_redis_client():
    """Get Redis client for publishing events."""
    try:
        import redis
        return redis.from_url(settings.REDIS_URL)
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")
        return None


def publish_event(channel: str, event_type: str, data: Dict[str, Any]) -> bool:
    """
    Publish event to Redis channel.

    Args:
        channel: Redis channel name
        event_type: Event type identifier
        data: Event payload

    Returns:
        True if published successfully
    """
    client = get_redis_client()
    if not client:
        return False

    try:
        message = {
            'event_type': event_type,
            'timestamp': datetime.utcnow().isoformat(),
            'service': 'finance-service',
            'data': data,
        }

        client.publish(channel, json.dumps(message, default=str))

        logger.info(
            f"Published event: {event_type}",
            extra={'channel': channel, 'event_type': event_type}
        )

        return True
    except Exception as e:
        logger.error(f"Failed to publish event: {e}")
        return False


# ==================== ACCOUNT EVENTS ====================

def publish_account_created(account_id: str, owner_id: str, account_type: str, organization_id: str):
    """Publish account created event."""
    return publish_event(
        channel='finance.accounts',
        event_type='account.created',
        data={
            'account_id': account_id,
            'owner_id': owner_id,
            'account_type': account_type,
            'organization_id': organization_id,
        }
    )


def publish_account_updated(account_id: str, changes: Dict[str, Any], organization_id: str):
    """Publish account updated event."""
    return publish_event(
        channel='finance.accounts',
        event_type='account.updated',
        data={
            'account_id': account_id,
            'changes': changes,
            'organization_id': organization_id,
        }
    )


def publish_account_suspended(account_id: str, reason: str, organization_id: str):
    """Publish account suspended event."""
    return publish_event(
        channel='finance.accounts',
        event_type='account.suspended',
        data={
            'account_id': account_id,
            'reason': reason,
            'organization_id': organization_id,
        }
    )


def publish_account_closed(account_id: str, reason: str, organization_id: str):
    """Publish account closed event."""
    return publish_event(
        channel='finance.accounts',
        event_type='account.closed',
        data={
            'account_id': account_id,
            'reason': reason,
            'organization_id': organization_id,
        }
    )


# ==================== TRANSACTION EVENTS ====================

def publish_transaction_created(
    transaction_id: str,
    transaction_type: str,
    amount: float,
    account_id: str,
    reference_type: str = None,
    reference_id: str = None,
    organization_id: str = None
):
    """Publish transaction created event."""
    return publish_event(
        channel='finance.transactions',
        event_type='transaction.created',
        data={
            'transaction_id': transaction_id,
            'transaction_type': transaction_type,
            'amount': amount,
            'account_id': account_id,
            'reference_type': reference_type,
            'reference_id': reference_id,
            'organization_id': organization_id,
        }
    )


def publish_payment_processed(
    transaction_id: str,
    amount: float,
    account_id: str,
    payment_method: str,
    gateway_transaction_id: str = None,
    organization_id: str = None
):
    """Publish payment processed event."""
    return publish_event(
        channel='finance.payments',
        event_type='payment.processed',
        data={
            'transaction_id': transaction_id,
            'amount': amount,
            'account_id': account_id,
            'payment_method': payment_method,
            'gateway_transaction_id': gateway_transaction_id,
            'organization_id': organization_id,
        }
    )


def publish_payment_failed(
    account_id: str,
    amount: float,
    payment_method: str,
    error_message: str,
    organization_id: str = None
):
    """Publish payment failed event."""
    return publish_event(
        channel='finance.payments',
        event_type='payment.failed',
        data={
            'account_id': account_id,
            'amount': amount,
            'payment_method': payment_method,
            'error_message': error_message,
            'organization_id': organization_id,
        }
    )


def publish_refund_processed(
    transaction_id: str,
    original_transaction_id: str,
    amount: float,
    account_id: str,
    organization_id: str = None
):
    """Publish refund processed event."""
    return publish_event(
        channel='finance.payments',
        event_type='refund.processed',
        data={
            'transaction_id': transaction_id,
            'original_transaction_id': original_transaction_id,
            'amount': amount,
            'account_id': account_id,
            'organization_id': organization_id,
        }
    )


# ==================== INVOICE EVENTS ====================

def publish_invoice_created(
    invoice_id: str,
    invoice_number: str,
    total_amount: float,
    account_id: str,
    organization_id: str = None
):
    """Publish invoice created event."""
    return publish_event(
        channel='finance.invoices',
        event_type='invoice.created',
        data={
            'invoice_id': invoice_id,
            'invoice_number': invoice_number,
            'total_amount': total_amount,
            'account_id': account_id,
            'organization_id': organization_id,
        }
    )


def publish_invoice_sent(
    invoice_id: str,
    invoice_number: str,
    sent_to: str,
    organization_id: str = None
):
    """Publish invoice sent event."""
    return publish_event(
        channel='finance.invoices',
        event_type='invoice.sent',
        data={
            'invoice_id': invoice_id,
            'invoice_number': invoice_number,
            'sent_to': sent_to,
            'organization_id': organization_id,
        }
    )


def publish_invoice_paid(
    invoice_id: str,
    invoice_number: str,
    total_amount: float,
    account_id: str,
    organization_id: str = None
):
    """Publish invoice paid event."""
    return publish_event(
        channel='finance.invoices',
        event_type='invoice.paid',
        data={
            'invoice_id': invoice_id,
            'invoice_number': invoice_number,
            'total_amount': total_amount,
            'account_id': account_id,
            'organization_id': organization_id,
        }
    )


def publish_invoice_overdue(
    invoice_id: str,
    invoice_number: str,
    amount_due: float,
    days_overdue: int,
    account_id: str,
    organization_id: str = None
):
    """Publish invoice overdue event."""
    return publish_event(
        channel='finance.invoices',
        event_type='invoice.overdue',
        data={
            'invoice_id': invoice_id,
            'invoice_number': invoice_number,
            'amount_due': amount_due,
            'days_overdue': days_overdue,
            'account_id': account_id,
            'organization_id': organization_id,
        }
    )


# ==================== PACKAGE EVENTS ====================

def publish_package_purchased(
    user_package_id: str,
    package_id: str,
    user_id: str,
    price: float,
    organization_id: str = None
):
    """Publish package purchased event."""
    return publish_event(
        channel='finance.packages',
        event_type='package.purchased',
        data={
            'user_package_id': user_package_id,
            'package_id': package_id,
            'user_id': user_id,
            'price': price,
            'organization_id': organization_id,
        }
    )


def publish_package_used(
    user_package_id: str,
    user_id: str,
    amount_used: float,
    amount_remaining: float,
    usage_type: str,
    reference_type: str = None,
    reference_id: str = None,
    organization_id: str = None
):
    """Publish package used event."""
    return publish_event(
        channel='finance.packages',
        event_type='package.used',
        data={
            'user_package_id': user_package_id,
            'user_id': user_id,
            'amount_used': amount_used,
            'amount_remaining': amount_remaining,
            'usage_type': usage_type,
            'reference_type': reference_type,
            'reference_id': reference_id,
            'organization_id': organization_id,
        }
    )


def publish_package_expired(
    user_package_id: str,
    package_id: str,
    user_id: str,
    credit_remaining: float,
    hours_remaining: float,
    organization_id: str = None
):
    """Publish package expired event."""
    return publish_event(
        channel='finance.packages',
        event_type='package.expired',
        data={
            'user_package_id': user_package_id,
            'package_id': package_id,
            'user_id': user_id,
            'credit_remaining': credit_remaining,
            'hours_remaining': hours_remaining,
            'organization_id': organization_id,
        }
    )


# ==================== PAYMENT METHOD EVENTS ====================

def publish_payment_method_added(
    payment_method_id: str,
    account_id: str,
    method_type: str,
    is_default: bool,
    organization_id: str = None
):
    """Publish payment method added event."""
    return publish_event(
        channel='finance.payment-methods',
        event_type='payment_method.added',
        data={
            'payment_method_id': payment_method_id,
            'account_id': account_id,
            'method_type': method_type,
            'is_default': is_default,
            'organization_id': organization_id,
        }
    )


def publish_payment_method_expiring(
    payment_method_id: str,
    account_id: str,
    expiry_month: int,
    expiry_year: int,
    days_until_expiry: int,
    organization_id: str = None
):
    """Publish payment method expiring event."""
    return publish_event(
        channel='finance.payment-methods',
        event_type='payment_method.expiring',
        data={
            'payment_method_id': payment_method_id,
            'account_id': account_id,
            'expiry_month': expiry_month,
            'expiry_year': expiry_year,
            'days_until_expiry': days_until_expiry,
            'organization_id': organization_id,
        }
    )
