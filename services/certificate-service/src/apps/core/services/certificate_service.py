# services/certificate-service/src/apps/core/services/certificate_service.py
"""
Certificate Service

Business logic for certificate/license management.
"""

import logging
from datetime import date, timedelta
from typing import List, Dict, Any, Optional
from uuid import UUID

from django.db import transaction
from django.db.models import Q, Count
from django.utils import timezone

from ..models import (
    Certificate,
    CertificateType,
    CertificateStatus,
    IssuingAuthority,
)

logger = logging.getLogger(__name__)


class CertificateService:
    """Service for managing certificates and licenses."""

    @staticmethod
    def create_certificate(
        organization_id: str,
        user_id: str,
        certificate_type: str,
        issuing_authority: str,
        certificate_number: str,
        issue_date: date,
        expiry_date: Optional[date] = None,
        created_by: Optional[str] = None,
        **kwargs
    ) -> Certificate:
        """
        Create a new certificate.

        Args:
            organization_id: Organization ID
            user_id: User ID (certificate holder)
            certificate_type: Type of certificate
            issuing_authority: Issuing authority
            certificate_number: Certificate number
            issue_date: Issue date
            expiry_date: Optional expiry date
            created_by: User creating the certificate
            **kwargs: Additional fields

        Returns:
            Created Certificate instance
        """
        certificate = Certificate.objects.create(
            organization_id=organization_id,
            user_id=user_id,
            certificate_type=certificate_type,
            issuing_authority=issuing_authority,
            certificate_number=certificate_number,
            issue_date=issue_date,
            expiry_date=expiry_date,
            created_by=created_by,
            status=CertificateStatus.PENDING_VERIFICATION,
            **kwargs
        )

        logger.info(
            f"Created certificate {certificate.id} for user {user_id}",
            extra={'certificate_id': str(certificate.id)}
        )

        return certificate

    @staticmethod
    def get_certificate(
        organization_id: str,
        certificate_id: str
    ) -> Certificate:
        """
        Get a certificate by ID.

        Args:
            organization_id: Organization ID
            certificate_id: Certificate ID

        Returns:
            Certificate instance

        Raises:
            ValueError: If certificate not found
        """
        try:
            return Certificate.objects.get(
                id=certificate_id,
                organization_id=organization_id
            )
        except Certificate.DoesNotExist:
            raise ValueError(f'Certificate {certificate_id} not found')

    @staticmethod
    def list_certificates(
        organization_id: str,
        user_id: Optional[str] = None,
        certificate_type: Optional[str] = None,
        status: Optional[str] = None,
        issuing_authority: Optional[str] = None,
        expiring_within_days: Optional[int] = None,
        verified_only: bool = False
    ) -> List[Certificate]:
        """
        List certificates with filters.

        Args:
            organization_id: Organization ID
            user_id: Filter by user
            certificate_type: Filter by type
            status: Filter by status
            issuing_authority: Filter by authority
            expiring_within_days: Filter expiring within N days
            verified_only: Only return verified certificates

        Returns:
            List of Certificate instances
        """
        queryset = Certificate.objects.filter(organization_id=organization_id)

        if user_id:
            queryset = queryset.filter(user_id=user_id)
        if certificate_type:
            queryset = queryset.filter(certificate_type=certificate_type)
        if status:
            queryset = queryset.filter(status=status)
        if issuing_authority:
            queryset = queryset.filter(issuing_authority=issuing_authority)
        if verified_only:
            queryset = queryset.filter(verified=True)
        if expiring_within_days:
            expiry_date = date.today() + timedelta(days=expiring_within_days)
            queryset = queryset.filter(
                expiry_date__isnull=False,
                expiry_date__lte=expiry_date,
                expiry_date__gte=date.today()
            )

        return list(queryset.order_by('-issue_date'))

    @staticmethod
    def update_certificate(
        organization_id: str,
        certificate_id: str,
        **updates
    ) -> Certificate:
        """
        Update a certificate.

        Args:
            organization_id: Organization ID
            certificate_id: Certificate ID
            **updates: Fields to update

        Returns:
            Updated Certificate instance
        """
        certificate = CertificateService.get_certificate(
            organization_id, certificate_id
        )

        # Prevent updating revoked certificates
        if certificate.status == CertificateStatus.REVOKED:
            raise ValueError('Cannot update revoked certificate')

        for field, value in updates.items():
            if hasattr(certificate, field):
                setattr(certificate, field, value)

        certificate.save()

        logger.info(
            f"Updated certificate {certificate_id}",
            extra={'certificate_id': certificate_id, 'updates': list(updates.keys())}
        )

        return certificate

    @staticmethod
    def delete_certificate(
        organization_id: str,
        certificate_id: str
    ) -> bool:
        """
        Delete a certificate (soft delete by marking revoked).

        Args:
            organization_id: Organization ID
            certificate_id: Certificate ID

        Returns:
            True if deleted successfully
        """
        certificate = CertificateService.get_certificate(
            organization_id, certificate_id
        )

        # Actually delete draft/pending certificates
        if certificate.status in [
            CertificateStatus.PENDING_VERIFICATION,
        ]:
            certificate.delete()
        else:
            # Soft delete by revoking
            certificate.revoke('Deleted by user')

        logger.info(f"Deleted certificate {certificate_id}")

        return True

    @staticmethod
    def verify_certificate(
        organization_id: str,
        certificate_id: str,
        verified_by: str,
        method: str,
        notes: Optional[str] = None
    ) -> Certificate:
        """
        Verify a certificate.

        Args:
            organization_id: Organization ID
            certificate_id: Certificate ID
            verified_by: User performing verification
            method: Verification method
            notes: Optional notes

        Returns:
            Verified Certificate instance
        """
        certificate = CertificateService.get_certificate(
            organization_id, certificate_id
        )

        certificate.verify(
            verified_by=UUID(verified_by),
            method=method,
            notes=notes
        )

        logger.info(
            f"Verified certificate {certificate_id}",
            extra={
                'certificate_id': certificate_id,
                'verified_by': verified_by,
                'method': method
            }
        )

        return certificate

    @staticmethod
    def suspend_certificate(
        organization_id: str,
        certificate_id: str,
        reason: str
    ) -> Certificate:
        """
        Suspend a certificate.

        Args:
            organization_id: Organization ID
            certificate_id: Certificate ID
            reason: Suspension reason

        Returns:
            Suspended Certificate instance
        """
        certificate = CertificateService.get_certificate(
            organization_id, certificate_id
        )

        certificate.suspend(reason)

        logger.warning(
            f"Suspended certificate {certificate_id}",
            extra={'certificate_id': certificate_id, 'reason': reason}
        )

        return certificate

    @staticmethod
    def revoke_certificate(
        organization_id: str,
        certificate_id: str,
        reason: str
    ) -> Certificate:
        """
        Revoke a certificate.

        Args:
            organization_id: Organization ID
            certificate_id: Certificate ID
            reason: Revocation reason

        Returns:
            Revoked Certificate instance
        """
        certificate = CertificateService.get_certificate(
            organization_id, certificate_id
        )

        certificate.revoke(reason)

        logger.warning(
            f"Revoked certificate {certificate_id}",
            extra={'certificate_id': certificate_id, 'reason': reason}
        )

        return certificate

    @staticmethod
    def reinstate_certificate(
        organization_id: str,
        certificate_id: str
    ) -> Certificate:
        """
        Reinstate a suspended certificate.

        Args:
            organization_id: Organization ID
            certificate_id: Certificate ID

        Returns:
            Reinstated Certificate instance
        """
        certificate = CertificateService.get_certificate(
            organization_id, certificate_id
        )

        certificate.reinstate()

        logger.info(f"Reinstated certificate {certificate_id}")

        return certificate

    @staticmethod
    def renew_certificate(
        organization_id: str,
        certificate_id: str,
        new_expiry_date: date,
        new_certificate_number: Optional[str] = None
    ) -> Certificate:
        """
        Renew a certificate with new expiry date.

        Args:
            organization_id: Organization ID
            certificate_id: Certificate ID
            new_expiry_date: New expiry date
            new_certificate_number: New certificate number if changed

        Returns:
            Renewed Certificate instance
        """
        certificate = CertificateService.get_certificate(
            organization_id, certificate_id
        )

        if certificate.status == CertificateStatus.REVOKED:
            raise ValueError('Cannot renew revoked certificate')

        certificate.expiry_date = new_expiry_date
        if new_certificate_number:
            certificate.certificate_number = new_certificate_number
        certificate.status = CertificateStatus.ACTIVE
        certificate.save()

        logger.info(
            f"Renewed certificate {certificate_id} until {new_expiry_date}",
            extra={'certificate_id': certificate_id}
        )

        return certificate

    @staticmethod
    def get_expiring_certificates(
        organization_id: str,
        days_ahead: int = 90
    ) -> List[Dict[str, Any]]:
        """
        Get certificates expiring within specified days.

        Args:
            organization_id: Organization ID
            days_ahead: Days to look ahead

        Returns:
            List of expiring certificate info dicts
        """
        expiry_date = date.today() + timedelta(days=days_ahead)

        certificates = Certificate.objects.filter(
            organization_id=organization_id,
            status__in=[CertificateStatus.ACTIVE, CertificateStatus.PENDING_RENEWAL],
            expiry_date__isnull=False,
            expiry_date__lte=expiry_date,
            expiry_date__gte=date.today()
        ).order_by('expiry_date')

        return [
            {
                'certificate_id': str(cert.id),
                'user_id': str(cert.user_id),
                'certificate_type': cert.certificate_type,
                'certificate_number': cert.certificate_number,
                'expiry_date': cert.expiry_date.isoformat(),
                'days_remaining': cert.days_until_expiry,
                'status': cert.status,
            }
            for cert in certificates
        ]

    @staticmethod
    def get_user_certificates(
        organization_id: str,
        user_id: str,
        active_only: bool = False
    ) -> List[Certificate]:
        """
        Get all certificates for a user.

        Args:
            organization_id: Organization ID
            user_id: User ID
            active_only: Only return active certificates

        Returns:
            List of Certificate instances
        """
        queryset = Certificate.objects.filter(
            organization_id=organization_id,
            user_id=user_id
        )

        if active_only:
            queryset = queryset.filter(
                status=CertificateStatus.ACTIVE,
                verified=True
            ).exclude(
                expiry_date__lt=date.today()
            )

        return list(queryset.order_by('certificate_type', '-issue_date'))

    @staticmethod
    def get_certificate_statistics(
        organization_id: str
    ) -> Dict[str, Any]:
        """
        Get certificate statistics for organization.

        Args:
            organization_id: Organization ID

        Returns:
            Statistics dict
        """
        certificates = Certificate.objects.filter(organization_id=organization_id)

        total = certificates.count()
        by_type = certificates.values('certificate_type').annotate(
            count=Count('id')
        )
        by_status = certificates.values('status').annotate(
            count=Count('id')
        )

        expiring_30 = certificates.filter(
            expiry_date__lte=date.today() + timedelta(days=30),
            expiry_date__gte=date.today()
        ).count()

        expiring_90 = certificates.filter(
            expiry_date__lte=date.today() + timedelta(days=90),
            expiry_date__gte=date.today()
        ).count()

        return {
            'total_certificates': total,
            'by_type': {t['certificate_type']: t['count'] for t in by_type},
            'by_status': {s['status']: s['count'] for s in by_status},
            'expiring_in_30_days': expiring_30,
            'expiring_in_90_days': expiring_90,
            'verified_count': certificates.filter(verified=True).count(),
            'pending_verification': certificates.filter(
                status=CertificateStatus.PENDING_VERIFICATION
            ).count(),
        }

    @staticmethod
    def update_certificate_statuses(organization_id: str) -> int:
        """
        Batch update certificate statuses.

        Args:
            organization_id: Organization ID

        Returns:
            Number of certificates updated
        """
        updated = 0

        # Mark expired certificates
        expired_count = Certificate.objects.filter(
            organization_id=organization_id,
            status__in=[CertificateStatus.ACTIVE, CertificateStatus.PENDING_RENEWAL],
            expiry_date__lt=date.today()
        ).update(status=CertificateStatus.EXPIRED)
        updated += expired_count

        # Mark certificates needing renewal (within 90 days)
        renewal_date = date.today() + timedelta(days=90)
        renewal_count = Certificate.objects.filter(
            organization_id=organization_id,
            status=CertificateStatus.ACTIVE,
            expiry_date__isnull=False,
            expiry_date__lte=renewal_date,
            expiry_date__gte=date.today()
        ).update(status=CertificateStatus.PENDING_RENEWAL)
        updated += renewal_count

        if updated > 0:
            logger.info(
                f"Updated {updated} certificate statuses for org {organization_id}",
                extra={'expired': expired_count, 'pending_renewal': renewal_count}
            )

        return updated
