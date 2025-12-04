# services/finance-service/src/apps/core/tasks/account_tasks.py
"""
Account Celery Tasks

Background tasks for account operations.
"""

import logging
from celery import shared_task
from decimal import Decimal

logger = logging.getLogger(__name__)


@shared_task(name='finance.check_low_balance_accounts')
def check_low_balance_accounts():
    """
    Check for accounts with low balance.

    Runs daily to notify users about low balance.
    """
    from ..models.account import Account, AccountStatus
    from django.db.models import F

    low_balance_accounts = Account.objects.filter(
        status=AccountStatus.ACTIVE,
        balance__lt=F('low_balance_threshold')
    )

    notified_count = 0

    for account in low_balance_accounts:
        # Send notification (via email or push notification service)
        # This would integrate with notification service

        notified_count += 1

    logger.info(f"Found {notified_count} low balance accounts")

    return {'count': notified_count}


@shared_task(name='finance.check_overdue_accounts')
def check_overdue_accounts():
    """
    Check for accounts with overdue balances.

    Runs daily to identify accounts needing attention.
    """
    from ..models.account import Account, AccountStatus
    from datetime import timedelta
    from django.utils import timezone

    # Find accounts with negative balance and no recent payment
    cutoff_date = timezone.now() - timedelta(days=30)

    overdue_accounts = Account.objects.filter(
        status=AccountStatus.ACTIVE,
        balance__lt=Decimal('0'),
        last_payment_at__lt=cutoff_date
    )

    overdue_count = overdue_accounts.count()

    # Could trigger various actions:
    # - Send reminder emails
    # - Flag for review
    # - Auto-suspend (based on policy)

    logger.info(f"Found {overdue_count} overdue accounts")

    return {'count': overdue_count}


@shared_task(name='finance.recalculate_account_balances')
def recalculate_account_balances():
    """
    Recalculate all account balances from transactions.

    Runs periodically as a consistency check.
    """
    from ..models.account import Account
    from ..services.account_service import AccountService

    accounts = Account.objects.all()
    recalculated_count = 0
    discrepancy_count = 0

    for account in accounts:
        old_balance = account.balance

        try:
            AccountService.recalculate_totals(account.id)
            account.refresh_from_db()

            if old_balance != account.balance:
                discrepancy_count += 1
                logger.warning(
                    f"Balance discrepancy for account {account.account_number}: "
                    f"was {old_balance}, now {account.balance}"
                )

            recalculated_count += 1
        except Exception as e:
            logger.error(
                f"Failed to recalculate account {account.id}: {e}"
            )

    logger.info(
        f"Recalculated {recalculated_count} accounts, "
        f"{discrepancy_count} discrepancies found"
    )

    return {
        'recalculated': recalculated_count,
        'discrepancies': discrepancy_count
    }
