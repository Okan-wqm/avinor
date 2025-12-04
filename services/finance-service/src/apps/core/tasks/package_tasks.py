# services/finance-service/src/apps/core/tasks/package_tasks.py
"""
Package Celery Tasks

Background tasks for credit package operations.
"""

import logging
from celery import shared_task
from datetime import timedelta
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(name='finance.expire_packages')
def expire_packages():
    """
    Expire packages past their expiration date.

    Runs daily to update package status.
    """
    from ..services.package_service import PackageService
    from ..events.publishers import publish_package_expired
    from ..models.package import UserPackage, UserPackageStatus

    # Get packages that need to be expired
    now = timezone.now()
    expiring = UserPackage.objects.filter(
        status=UserPackageStatus.ACTIVE,
        expires_at__lt=now
    ).select_related('package')

    expired_count = 0

    for user_package in expiring:
        # Expire the package
        user_package.expire()
        user_package.save()

        # Publish event
        publish_package_expired(
            user_package_id=str(user_package.id),
            package_id=str(user_package.package_id),
            user_id=str(user_package.user_id),
            credit_remaining=float(user_package.credit_remaining),
            hours_remaining=float(user_package.hours_remaining),
            organization_id=str(user_package.organization_id)
        )

        expired_count += 1

    logger.info(f"Expired {expired_count} user packages")

    return {'expired': expired_count}


@shared_task(name='finance.notify_expiring_packages')
def notify_expiring_packages():
    """
    Notify users about expiring packages.

    Runs daily to send notifications for packages expiring soon.
    """
    from ..models.package import UserPackage, UserPackageStatus

    now = timezone.now()
    notification_days = [30, 14, 7, 1]  # Days before expiry to notify

    notified_count = 0

    for days in notification_days:
        check_date = now + timedelta(days=days)
        check_date_start = check_date.replace(hour=0, minute=0, second=0, microsecond=0)
        check_date_end = check_date.replace(hour=23, minute=59, second=59, microsecond=999999)

        # Find packages expiring on this date
        expiring = UserPackage.objects.filter(
            status=UserPackageStatus.ACTIVE,
            expires_at__range=(check_date_start, check_date_end)
        ).select_related('package')

        for user_package in expiring:
            # Send notification (via email or push notification service)
            # This would integrate with notification service

            notified_count += 1

    logger.info(f"Sent {notified_count} expiring package notifications")

    return {'notified': notified_count}
