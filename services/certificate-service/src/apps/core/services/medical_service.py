# services/certificate-service/src/apps/core/services/medical_service.py
"""
Medical Service

Business logic for medical certificate management.
"""

import logging
from datetime import date, timedelta
from typing import List, Dict, Any, Optional
from uuid import UUID

from django.db import transaction
from django.db.models import Q, Count
from django.utils import timezone

from ..models import (
    MedicalCertificate,
    MedicalClass,
    MedicalStatus,
)

logger = logging.getLogger(__name__)


class MedicalService:
    """Service for managing medical certificates."""

    @staticmethod
    def create_medical(
        organization_id: str,
        user_id: str,
        medical_class: str,
        issuing_authority: str,
        examination_date: date,
        issue_date: date,
        expiry_date: date,
        created_by: Optional[str] = None,
        **kwargs
    ) -> MedicalCertificate:
        """
        Create a new medical certificate.

        Args:
            organization_id: Organization ID
            user_id: User ID (pilot)
            medical_class: Medical class (class_1, class_2, etc.)
            issuing_authority: Issuing authority
            examination_date: Date of medical examination
            issue_date: Issue date
            expiry_date: Expiry date
            created_by: User creating the record
            **kwargs: Additional fields

        Returns:
            Created MedicalCertificate instance
        """
        medical = MedicalCertificate.objects.create(
            organization_id=organization_id,
            user_id=user_id,
            medical_class=medical_class,
            issuing_authority=issuing_authority,
            examination_date=examination_date,
            issue_date=issue_date,
            expiry_date=expiry_date,
            created_by=created_by,
            **kwargs
        )

        logger.info(
            f"Created medical certificate {medical.id} for user {user_id}",
            extra={'medical_id': str(medical.id), 'class': medical_class}
        )

        return medical

    @staticmethod
    def get_medical(
        organization_id: str,
        medical_id: str
    ) -> MedicalCertificate:
        """
        Get a medical certificate by ID.

        Args:
            organization_id: Organization ID
            medical_id: Medical certificate ID

        Returns:
            MedicalCertificate instance

        Raises:
            ValueError: If not found
        """
        try:
            return MedicalCertificate.objects.get(
                id=medical_id,
                organization_id=organization_id
            )
        except MedicalCertificate.DoesNotExist:
            raise ValueError(f'Medical certificate {medical_id} not found')

    @staticmethod
    def list_medicals(
        organization_id: str,
        user_id: Optional[str] = None,
        medical_class: Optional[str] = None,
        status: Optional[str] = None,
        expiring_within_days: Optional[int] = None
    ) -> List[MedicalCertificate]:
        """
        List medical certificates with filters.

        Args:
            organization_id: Organization ID
            user_id: Filter by user
            medical_class: Filter by class
            status: Filter by status
            expiring_within_days: Filter by days until expiry

        Returns:
            List of MedicalCertificate instances
        """
        queryset = MedicalCertificate.objects.filter(organization_id=organization_id)

        if user_id:
            queryset = queryset.filter(user_id=user_id)
        if medical_class:
            queryset = queryset.filter(medical_class=medical_class)
        if status:
            queryset = queryset.filter(status=status)
        if expiring_within_days:
            expiry_date = date.today() + timedelta(days=expiring_within_days)
            queryset = queryset.filter(
                expiry_date__lte=expiry_date,
                expiry_date__gte=date.today()
            )

        return list(queryset.order_by('-expiry_date'))

    @staticmethod
    def update_medical(
        organization_id: str,
        medical_id: str,
        **updates
    ) -> MedicalCertificate:
        """
        Update a medical certificate.

        Args:
            organization_id: Organization ID
            medical_id: Medical certificate ID
            **updates: Fields to update

        Returns:
            Updated MedicalCertificate instance
        """
        medical = MedicalService.get_medical(organization_id, medical_id)

        if medical.status == MedicalStatus.REVOKED:
            raise ValueError('Cannot update revoked medical certificate')

        for field, value in updates.items():
            if hasattr(medical, field):
                setattr(medical, field, value)

        medical.save()

        logger.info(f"Updated medical certificate {medical_id}")

        return medical

    @staticmethod
    def delete_medical(
        organization_id: str,
        medical_id: str
    ) -> bool:
        """
        Delete a medical certificate.

        Args:
            organization_id: Organization ID
            medical_id: Medical certificate ID

        Returns:
            True if deleted
        """
        medical = MedicalService.get_medical(organization_id, medical_id)
        medical.delete()

        logger.info(f"Deleted medical certificate {medical_id}")

        return True

    @staticmethod
    def get_user_current_medical(
        organization_id: str,
        user_id: str
    ) -> Optional[MedicalCertificate]:
        """
        Get user's current valid medical certificate.

        Args:
            organization_id: Organization ID
            user_id: User ID

        Returns:
            Current MedicalCertificate or None
        """
        return MedicalCertificate.objects.filter(
            organization_id=organization_id,
            user_id=user_id,
            status=MedicalStatus.ACTIVE,
            expiry_date__gte=date.today()
        ).order_by('-expiry_date').first()

    @staticmethod
    def get_user_medical_history(
        organization_id: str,
        user_id: str
    ) -> List[MedicalCertificate]:
        """
        Get user's medical certificate history.

        Args:
            organization_id: Organization ID
            user_id: User ID

        Returns:
            List of MedicalCertificate instances ordered by date
        """
        return list(
            MedicalCertificate.objects.filter(
                organization_id=organization_id,
                user_id=user_id
            ).order_by('-issue_date')
        )

    @staticmethod
    def check_medical_validity(
        organization_id: str,
        user_id: str,
        required_class: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Check if user has valid medical certificate.

        Args:
            organization_id: Organization ID
            user_id: User ID
            required_class: Minimum required medical class

        Returns:
            Validity status dict
        """
        medical = MedicalService.get_user_current_medical(organization_id, user_id)

        if not medical:
            return {
                'is_valid': False,
                'message': 'No valid medical certificate found',
                'medical': None,
            }

        # Check class hierarchy if required
        class_hierarchy = [
            MedicalClass.CLASS_1,
            MedicalClass.CLASS_2,
            MedicalClass.CLASS_3,
            MedicalClass.LAPL,
        ]

        if required_class:
            required_index = class_hierarchy.index(required_class) if required_class in class_hierarchy else -1
            current_index = class_hierarchy.index(medical.medical_class) if medical.medical_class in class_hierarchy else -1

            if current_index > required_index:
                return {
                    'is_valid': False,
                    'message': f'Medical class {medical.medical_class} insufficient. Required: {required_class}',
                    'medical': medical.get_validity_info(),
                }

        return {
            'is_valid': True,
            'message': 'Valid medical certificate',
            'medical': medical.get_validity_info(),
            'days_until_expiry': medical.days_until_expiry,
        }

    @staticmethod
    def get_expiring_medicals(
        organization_id: str,
        days_ahead: int = 90
    ) -> List[Dict[str, Any]]:
        """
        Get medical certificates expiring soon.

        Args:
            organization_id: Organization ID
            days_ahead: Days to look ahead

        Returns:
            List of expiring medical info dicts
        """
        expiry_date = date.today() + timedelta(days=days_ahead)

        medicals = MedicalCertificate.objects.filter(
            organization_id=organization_id,
            status=MedicalStatus.ACTIVE,
            expiry_date__lte=expiry_date,
            expiry_date__gte=date.today()
        ).order_by('expiry_date')

        return [
            {
                'medical_id': str(med.id),
                'user_id': str(med.user_id),
                'medical_class': med.medical_class,
                'expiry_date': med.expiry_date.isoformat(),
                'days_remaining': med.days_until_expiry,
            }
            for med in medicals
        ]

    @staticmethod
    def calculate_next_expiry_date(
        medical_class: str,
        pilot_age: int,
        issue_date: date,
        issuing_authority: str = 'easa'
    ) -> date:
        """
        Calculate expected expiry date based on class and age.

        Args:
            medical_class: Medical class
            pilot_age: Pilot age at examination
            issue_date: Issue date
            issuing_authority: Authority (affects validity rules)

        Returns:
            Calculated expiry date
        """
        validity_months = MedicalCertificate.calculate_validity_period(
            medical_class,
            pilot_age,
            issuing_authority
        )

        # Calculate expiry date (end of month)
        expiry = issue_date + timedelta(days=validity_months * 30)
        import calendar
        _, last_day = calendar.monthrange(expiry.year, expiry.month)
        return date(expiry.year, expiry.month, last_day)

    @staticmethod
    def get_medical_statistics(
        organization_id: str
    ) -> Dict[str, Any]:
        """
        Get medical certificate statistics.

        Args:
            organization_id: Organization ID

        Returns:
            Statistics dict
        """
        medicals = MedicalCertificate.objects.filter(organization_id=organization_id)

        total = medicals.count()
        by_class = medicals.values('medical_class').annotate(count=Count('id'))
        by_status = medicals.values('status').annotate(count=Count('id'))

        expiring_30 = medicals.filter(
            expiry_date__lte=date.today() + timedelta(days=30),
            expiry_date__gte=date.today(),
            status=MedicalStatus.ACTIVE
        ).count()

        expiring_90 = medicals.filter(
            expiry_date__lte=date.today() + timedelta(days=90),
            expiry_date__gte=date.today(),
            status=MedicalStatus.ACTIVE
        ).count()

        return {
            'total_medicals': total,
            'by_class': {c['medical_class']: c['count'] for c in by_class},
            'by_status': {s['status']: s['count'] for s in by_status},
            'expiring_in_30_days': expiring_30,
            'expiring_in_90_days': expiring_90,
            'active_count': medicals.filter(
                status=MedicalStatus.ACTIVE,
                expiry_date__gte=date.today()
            ).count(),
        }

    @staticmethod
    def update_medical_statuses(organization_id: str) -> int:
        """
        Batch update medical certificate statuses.

        Args:
            organization_id: Organization ID

        Returns:
            Number of certificates updated
        """
        # Mark expired medicals
        updated = MedicalCertificate.objects.filter(
            organization_id=organization_id,
            status=MedicalStatus.ACTIVE,
            expiry_date__lt=date.today()
        ).update(status=MedicalStatus.EXPIRED)

        if updated > 0:
            logger.info(f"Updated {updated} medical statuses to expired")

        return updated

    @staticmethod
    def send_expiry_reminders(organization_id: str) -> int:
        """
        Send expiry reminders for medical certificates.

        Args:
            organization_id: Organization ID

        Returns:
            Number of reminders sent
        """
        reminders_sent = 0
        reminder_days = [90, 60, 30, 14, 7]

        for days in reminder_days:
            medicals = MedicalCertificate.objects.filter(
                organization_id=organization_id,
                status=MedicalStatus.ACTIVE,
                expiry_date=date.today() + timedelta(days=days),
                **{f'reminder_sent_{days}_days': False}
            )

            for medical in medicals:
                # Send notification (would integrate with notification service)
                logger.info(
                    f"Sending {days}-day expiry reminder for medical {medical.id}"
                )
                medical.mark_reminder_sent(days)
                reminders_sent += 1

        return reminders_sent
