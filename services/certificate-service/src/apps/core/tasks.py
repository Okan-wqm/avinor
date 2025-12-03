# services/certificate-service/src/apps/core/tasks.py
"""
Certificate Service Celery Tasks

Background tasks for certificate management and maintenance.
"""

import logging
from datetime import date, timedelta
from typing import Optional
from uuid import UUID

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def check_expiring_certificates(self, days_ahead: int = 30, organization_id: Optional[str] = None):
    """
    Check for certificates expiring soon and send notifications.

    Args:
        days_ahead: Number of days to look ahead
        organization_id: Optional organization filter
    """
    try:
        from .services import CertificateService
        from .events import event_publisher

        service = CertificateService()
        org_id = UUID(organization_id) if organization_id else None

        expiring = service.get_expiring_certificates(
            organization_id=org_id,
            days_ahead=days_ahead
        )

        for cert in expiring:
            # Publish expiring event
            event_publisher.certificate_expiring(
                certificate_id=cert['certificate_id'],
                user_id=cert['user_id'],
                expiry_date=cert['expiry_date'],
                days_remaining=cert['days_remaining'],
                certificate_type=cert['certificate_type'],
                organization_id=org_id
            )

        logger.info(f"Checked expiring certificates: {len(expiring)} expiring in {days_ahead} days")
        return {'expiring_count': len(expiring)}

    except Exception as e:
        logger.error(f"Error checking expiring certificates: {e}")
        self.retry(countdown=60, exc=e)


@shared_task(bind=True, max_retries=3)
def check_expiring_medicals(self, days_ahead: int = 30, organization_id: Optional[str] = None):
    """
    Check for medical certificates expiring soon and send notifications.

    Args:
        days_ahead: Number of days to look ahead
        organization_id: Optional organization filter
    """
    try:
        from .services import MedicalService
        from .events import event_publisher

        service = MedicalService()
        org_id = UUID(organization_id) if organization_id else None

        expiring = service.get_expiring_medicals(
            organization_id=org_id,
            days_ahead=days_ahead
        )

        for medical in expiring:
            days_remaining = (medical.expiry_date - date.today()).days
            event_publisher.medical_expiring(
                medical_id=medical.id,
                user_id=medical.user_id,
                expiry_date=medical.expiry_date,
                days_remaining=days_remaining,
                medical_class=medical.medical_class,
                organization_id=org_id
            )

        logger.info(f"Checked expiring medicals: {len(expiring)} expiring in {days_ahead} days")
        return {'expiring_count': len(expiring)}

    except Exception as e:
        logger.error(f"Error checking expiring medicals: {e}")
        self.retry(countdown=60, exc=e)


@shared_task(bind=True, max_retries=3)
def check_expiring_ratings(self, days_ahead: int = 30, organization_id: Optional[str] = None):
    """
    Check for ratings expiring soon.

    Args:
        days_ahead: Number of days to look ahead
        organization_id: Optional organization filter
    """
    try:
        from .services import RatingService

        service = RatingService()
        org_id = UUID(organization_id) if organization_id else None

        expiring = service.get_expiring_ratings(
            organization_id=org_id,
            days_ahead=days_ahead
        )

        logger.info(f"Checked expiring ratings: {len(expiring)} expiring in {days_ahead} days")
        return {'expiring_count': len(expiring)}

    except Exception as e:
        logger.error(f"Error checking expiring ratings: {e}")
        self.retry(countdown=60, exc=e)


@shared_task(bind=True, max_retries=3)
def check_proficiency_due(self, days_ahead: int = 30, organization_id: Optional[str] = None):
    """
    Check for ratings with proficiency checks due.

    Args:
        days_ahead: Number of days to look ahead
        organization_id: Optional organization filter
    """
    try:
        from .services import RatingService

        service = RatingService()
        org_id = UUID(organization_id) if organization_id else None

        due = service.get_proficiency_due(
            organization_id=org_id,
            days_ahead=days_ahead
        )

        logger.info(f"Checked proficiency due: {len(due)} due in {days_ahead} days")
        return {'due_count': len(due)}

    except Exception as e:
        logger.error(f"Error checking proficiency due: {e}")
        self.retry(countdown=60, exc=e)


@shared_task(bind=True, max_retries=3)
def check_expiring_endorsements(self, days_ahead: int = 30, organization_id: Optional[str] = None):
    """
    Check for endorsements expiring soon.

    Args:
        days_ahead: Number of days to look ahead
        organization_id: Optional organization filter
    """
    try:
        from .services import EndorsementService

        service = EndorsementService()
        org_id = UUID(organization_id) if organization_id else None

        expiring = service.get_expiring_endorsements(
            organization_id=org_id,
            days_ahead=days_ahead
        )

        logger.info(f"Checked expiring endorsements: {len(expiring)} expiring in {days_ahead} days")
        return {'expiring_count': len(expiring)}

    except Exception as e:
        logger.error(f"Error checking expiring endorsements: {e}")
        self.retry(countdown=60, exc=e)


@shared_task(bind=True, max_retries=3)
def check_expiring_currency(self, days_ahead: int = 30, organization_id: Optional[str] = None):
    """
    Check for currency statuses expiring soon.

    Args:
        days_ahead: Number of days to look ahead
        organization_id: Optional organization filter
    """
    try:
        from .services import CurrencyService
        from .events import event_publisher

        service = CurrencyService()
        org_id = UUID(organization_id) if organization_id else None

        expiring = service.get_expiring_currency(
            organization_id=org_id,
            days_ahead=days_ahead
        )

        for status in expiring:
            days_remaining = (status.expiry_date - date.today()).days if status.expiry_date else 0
            event_publisher.currency_updated(
                user_id=status.user_id,
                currency_type=status.requirement.currency_type,
                status='expiring',
                expiry_date=status.expiry_date,
                days_remaining=days_remaining,
                organization_id=org_id
            )

        logger.info(f"Checked expiring currency: {len(expiring)} expiring in {days_ahead} days")
        return {'expiring_count': len(expiring)}

    except Exception as e:
        logger.error(f"Error checking expiring currency: {e}")
        self.retry(countdown=60, exc=e)


@shared_task(bind=True, max_retries=3)
def update_expired_items(self, organization_id: Optional[str] = None):
    """
    Update status of expired certificates, medicals, ratings, endorsements.

    Args:
        organization_id: Optional organization filter
    """
    try:
        from .models import (
            Certificate, CertificateStatus,
            MedicalCertificate, MedicalStatus,
            Rating, RatingStatus,
            Endorsement, EndorsementStatus,
            UserCurrencyStatus, CurrencyStatus,
        )

        today = date.today()
        org_id = UUID(organization_id) if organization_id else None

        # Update expired certificates
        cert_filter = {'expiry_date__lt': today, 'status': CertificateStatus.ACTIVE}
        if org_id:
            cert_filter['organization_id'] = org_id

        expired_certs = Certificate.objects.filter(**cert_filter).update(
            status=CertificateStatus.EXPIRED,
            updated_at=timezone.now()
        )

        # Update expired medicals
        med_filter = {'expiry_date__lt': today, 'status': MedicalStatus.ACTIVE}
        if org_id:
            med_filter['organization_id'] = org_id

        expired_meds = MedicalCertificate.objects.filter(**med_filter).update(
            status=MedicalStatus.EXPIRED,
            updated_at=timezone.now()
        )

        # Update expired ratings
        rating_filter = {'expiry_date__lt': today, 'status': RatingStatus.ACTIVE}
        if org_id:
            rating_filter['organization_id'] = org_id

        expired_ratings = Rating.objects.filter(**rating_filter).update(
            status=RatingStatus.EXPIRED,
            updated_at=timezone.now()
        )

        # Update expired endorsements
        end_filter = {
            'expiry_date__lt': today,
            'status': EndorsementStatus.ACTIVE,
            'is_permanent': False
        }
        if org_id:
            end_filter['organization_id'] = org_id

        expired_ends = Endorsement.objects.filter(**end_filter).update(
            status=EndorsementStatus.EXPIRED,
            updated_at=timezone.now()
        )

        # Update expired currency
        curr_filter = {'expiry_date__lt': today, 'status': CurrencyStatus.CURRENT}
        if org_id:
            curr_filter['organization_id'] = org_id

        expired_curr = UserCurrencyStatus.objects.filter(**curr_filter).update(
            status=CurrencyStatus.EXPIRED,
            updated_at=timezone.now()
        )

        result = {
            'expired_certificates': expired_certs,
            'expired_medicals': expired_meds,
            'expired_ratings': expired_ratings,
            'expired_endorsements': expired_ends,
            'expired_currency': expired_curr,
        }

        logger.info(f"Updated expired items: {result}")
        return result

    except Exception as e:
        logger.error(f"Error updating expired items: {e}")
        self.retry(countdown=60, exc=e)


@shared_task(bind=True, max_retries=3)
def recalculate_user_currency(self, user_id: str, organization_id: Optional[str] = None):
    """
    Recalculate all currency statuses for a user.

    Args:
        user_id: User ID
        organization_id: Organization ID
    """
    try:
        from .services import CurrencyService

        service = CurrencyService()
        result = service.recalculate_user_currency(
            user_id=UUID(user_id)
        )

        logger.info(f"Recalculated currency for user {user_id}")
        return result

    except Exception as e:
        logger.error(f"Error recalculating currency for user {user_id}: {e}")
        self.retry(countdown=60, exc=e)


@shared_task(bind=True, max_retries=3)
def generate_compliance_report(self, organization_id: str):
    """
    Generate organization-wide compliance report.

    Args:
        organization_id: Organization ID
    """
    try:
        from .services import ValidityService

        service = ValidityService()
        report = service.get_organization_compliance(
            organization_id=UUID(organization_id)
        )

        logger.info(f"Generated compliance report for organization {organization_id}")
        return report

    except Exception as e:
        logger.error(f"Error generating compliance report: {e}")
        self.retry(countdown=60, exc=e)


@shared_task(bind=True, max_retries=3)
def send_expiration_notifications(self, days_ahead: int = 30, organization_id: Optional[str] = None):
    """
    Send notifications for expiring items.

    Args:
        days_ahead: Number of days to look ahead
        organization_id: Optional organization filter
    """
    try:
        from .services import ValidityService

        service = ValidityService()
        org_id = UUID(organization_id) if organization_id else None

        alerts = service.get_expiration_alerts(
            organization_id=org_id,
            days_ahead=days_ahead
        )

        # Group alerts by user for batch notification
        user_alerts = {}
        for alert in alerts:
            user_id = str(alert.get('user_id'))
            if user_id not in user_alerts:
                user_alerts[user_id] = []
            user_alerts[user_id].append(alert)

        # Send notifications (would integrate with notification service)
        for user_id, user_alert_list in user_alerts.items():
            # This would call a notification service
            logger.info(f"Would send {len(user_alert_list)} expiration alerts to user {user_id}")

        logger.info(f"Processed {len(alerts)} expiration alerts for {len(user_alerts)} users")
        return {'alert_count': len(alerts), 'user_count': len(user_alerts)}

    except Exception as e:
        logger.error(f"Error sending expiration notifications: {e}")
        self.retry(countdown=60, exc=e)


@shared_task
def daily_maintenance():
    """
    Daily maintenance task - runs all checks and updates.
    """
    logger.info("Starting daily certificate maintenance")

    # Update expired items
    update_expired_items.delay()

    # Check expiring items (30 days ahead)
    check_expiring_certificates.delay(days_ahead=30)
    check_expiring_medicals.delay(days_ahead=30)
    check_expiring_ratings.delay(days_ahead=30)
    check_proficiency_due.delay(days_ahead=30)
    check_expiring_endorsements.delay(days_ahead=30)
    check_expiring_currency.delay(days_ahead=30)

    # Send notifications
    send_expiration_notifications.delay(days_ahead=30)

    logger.info("Daily certificate maintenance tasks queued")
    return {'status': 'queued'}


@shared_task
def weekly_compliance_reports():
    """
    Weekly task - generate compliance reports for all organizations.
    """
    from .models import Certificate

    # Get unique organization IDs
    org_ids = Certificate.objects.values_list(
        'organization_id', flat=True
    ).distinct()

    for org_id in org_ids:
        if org_id:
            generate_compliance_report.delay(str(org_id))

    logger.info(f"Queued compliance reports for {len(org_ids)} organizations")
    return {'organization_count': len(org_ids)}
