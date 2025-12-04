# services/finance-service/src/apps/core/tasks/payment_tasks.py
"""
Payment Celery Tasks

Background tasks for payment operations.
"""

import logging
from celery import shared_task
from datetime import date
from dateutil.relativedelta import relativedelta

logger = logging.getLogger(__name__)


@shared_task(name='finance.expire_payment_methods')
def expire_payment_methods():
    """
    Mark expired payment methods.

    Runs daily to update status of expired cards.
    """
    from ..services.payment_service import PaymentService

    expired_count = PaymentService.update_expired_cards()

    logger.info(f"Marked {expired_count} payment methods as expired")

    return {'expired': expired_count}


@shared_task(name='finance.notify_expiring_cards')
def notify_expiring_cards():
    """
    Notify users about expiring cards.

    Runs daily to send notifications for cards expiring soon.
    """
    from ..models.payment import PaymentMethod, PaymentMethodType, PaymentMethodStatus
    from ..events.publishers import publish_payment_method_expiring

    today = date.today()
    notification_days = [30, 14, 7]  # Days before expiry to notify

    notified_count = 0

    for days in notification_days:
        check_date = today + relativedelta(days=days)

        # Find cards expiring on this date
        expiring = PaymentMethod.objects.filter(
            method_type__in=[PaymentMethodType.CREDIT_CARD, PaymentMethodType.DEBIT_CARD],
            status=PaymentMethodStatus.ACTIVE,
            card_exp_year=check_date.year,
            card_exp_month=check_date.month
        ).select_related('account')

        for pm in expiring:
            publish_payment_method_expiring(
                payment_method_id=str(pm.id),
                account_id=str(pm.account_id),
                expiry_month=pm.card_exp_month,
                expiry_year=pm.card_exp_year,
                days_until_expiry=days,
                organization_id=str(pm.organization_id)
            )
            notified_count += 1

    logger.info(f"Sent {notified_count} expiring card notifications")

    return {'notified': notified_count}


@shared_task(name='finance.retry_failed_payments')
def retry_failed_payments():
    """
    Retry failed automatic payments.

    Runs periodically to retry failed auto-pay transactions.
    """
    from ..models.transaction import Transaction, TransactionStatus
    from ..services.payment_service import PaymentService

    # Find failed payment transactions from last 24 hours
    # that haven't been retried yet
    # Implementation would depend on retry policy

    retry_count = 0
    success_count = 0
    fail_count = 0

    logger.info(
        f"Payment retry: {retry_count} attempted, "
        f"{success_count} succeeded, {fail_count} failed"
    )

    return {
        'retried': retry_count,
        'succeeded': success_count,
        'failed': fail_count
    }
