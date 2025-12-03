# services/certificate-service/src/apps/core/services/verification_service.py
"""
Verification Service

Business logic for certificate verification.
"""

import logging
import hashlib
from datetime import date, timedelta
from typing import List, Dict, Any, Optional
from uuid import UUID

from django.db import transaction
from django.db.models import Count
from django.utils import timezone

from ..models import (
    Certificate,
    CertificateVerification,
    VerificationMethod,
    VerificationStatus,
)

logger = logging.getLogger(__name__)


class VerificationService:
    """Service for managing certificate verification."""

    @staticmethod
    def create_verification_request(
        organization_id: str,
        certificate_id: str,
        verification_method: str,
        requested_by: Optional[str] = None,
        **kwargs
    ) -> CertificateVerification:
        """
        Create a new verification request.

        Args:
            organization_id: Organization ID
            certificate_id: Certificate to verify
            verification_method: Method of verification
            requested_by: User requesting verification
            **kwargs: Additional fields

        Returns:
            Created CertificateVerification instance
        """
        # Get certificate info
        try:
            certificate = Certificate.objects.get(
                id=certificate_id,
                organization_id=organization_id
            )
        except Certificate.DoesNotExist:
            raise ValueError(f'Certificate {certificate_id} not found')

        verification = CertificateVerification.objects.create(
            organization_id=organization_id,
            certificate_id=certificate_id,
            certificate_type=certificate.certificate_type,
            certificate_number=certificate.certificate_number,
            user_id=certificate.user_id,
            verification_method=verification_method,
            status=VerificationStatus.PENDING,
            **kwargs
        )

        logger.info(
            f"Created verification request {verification.id}",
            extra={
                'verification_id': str(verification.id),
                'certificate_id': certificate_id,
                'method': verification_method
            }
        )

        return verification

    @staticmethod
    def get_verification(
        organization_id: str,
        verification_id: str
    ) -> CertificateVerification:
        """
        Get a verification by ID.

        Args:
            organization_id: Organization ID
            verification_id: Verification ID

        Returns:
            CertificateVerification instance

        Raises:
            ValueError: If not found
        """
        try:
            return CertificateVerification.objects.get(
                id=verification_id,
                organization_id=organization_id
            )
        except CertificateVerification.DoesNotExist:
            raise ValueError(f'Verification {verification_id} not found')

    @staticmethod
    def list_verifications(
        organization_id: str,
        certificate_id: Optional[str] = None,
        user_id: Optional[str] = None,
        status: Optional[str] = None,
        method: Optional[str] = None
    ) -> List[CertificateVerification]:
        """
        List verifications with filters.

        Args:
            organization_id: Organization ID
            certificate_id: Filter by certificate
            user_id: Filter by user
            status: Filter by status
            method: Filter by method

        Returns:
            List of CertificateVerification instances
        """
        queryset = CertificateVerification.objects.filter(
            organization_id=organization_id
        )

        if certificate_id:
            queryset = queryset.filter(certificate_id=certificate_id)
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        if status:
            queryset = queryset.filter(status=status)
        if method:
            queryset = queryset.filter(verification_method=method)

        return list(queryset.order_by('-requested_at'))

    @staticmethod
    def start_verification(
        organization_id: str,
        verification_id: str,
        verifier_id: str,
        verifier_name: str
    ) -> CertificateVerification:
        """
        Start a verification process.

        Args:
            organization_id: Organization ID
            verification_id: Verification ID
            verifier_id: User performing verification
            verifier_name: Verifier name

        Returns:
            Updated CertificateVerification instance
        """
        verification = VerificationService.get_verification(
            organization_id, verification_id
        )

        if verification.status != VerificationStatus.PENDING:
            raise ValueError('Verification already in progress or completed')

        verification.start_verification(
            verifier_id=UUID(verifier_id),
            verifier_name=verifier_name
        )

        logger.info(
            f"Started verification {verification_id}",
            extra={'verification_id': verification_id, 'verifier': verifier_name}
        )

        return verification

    @staticmethod
    def complete_verification(
        organization_id: str,
        verification_id: str,
        is_valid: bool,
        validity_date: Optional[date] = None,
        issues: Optional[List[Dict[str, Any]]] = None,
        notes: Optional[str] = None
    ) -> CertificateVerification:
        """
        Complete a verification with result.

        Args:
            organization_id: Organization ID
            verification_id: Verification ID
            is_valid: Whether certificate is valid
            validity_date: Verified validity date
            issues: List of issues found
            notes: Verification notes

        Returns:
            Completed CertificateVerification instance
        """
        verification = VerificationService.get_verification(
            organization_id, verification_id
        )

        if verification.status not in [
            VerificationStatus.PENDING,
            VerificationStatus.IN_PROGRESS
        ]:
            raise ValueError('Verification already completed')

        verification.complete_verification(
            is_valid=is_valid,
            validity_date=validity_date,
            issues=issues,
            notes=notes
        )

        # Update certificate verification status
        if is_valid:
            try:
                certificate = Certificate.objects.get(id=verification.certificate_id)
                certificate.verify(
                    verified_by=verification.verified_by,
                    method=verification.verification_method,
                    notes=notes
                )
            except Certificate.DoesNotExist:
                pass

        logger.info(
            f"Completed verification {verification_id}",
            extra={
                'verification_id': verification_id,
                'is_valid': is_valid,
                'issues': len(issues) if issues else 0
            }
        )

        return verification

    @staticmethod
    def fail_verification(
        organization_id: str,
        verification_id: str,
        reason: str,
        issues: Optional[List[Dict[str, Any]]] = None
    ) -> CertificateVerification:
        """
        Fail a verification.

        Args:
            organization_id: Organization ID
            verification_id: Verification ID
            reason: Failure reason
            issues: List of issues found

        Returns:
            Failed CertificateVerification instance
        """
        verification = VerificationService.get_verification(
            organization_id, verification_id
        )

        verification.fail_verification(reason=reason, issues=issues)

        logger.warning(
            f"Failed verification {verification_id}",
            extra={'verification_id': verification_id, 'reason': reason}
        )

        return verification

    @staticmethod
    def verify_document(
        organization_id: str,
        certificate_id: str,
        document_content: bytes,
        verifier_id: str,
        verifier_name: str
    ) -> CertificateVerification:
        """
        Verify a certificate by document check.

        Args:
            organization_id: Organization ID
            certificate_id: Certificate ID
            document_content: Document file content
            verifier_id: User performing verification
            verifier_name: Verifier name

        Returns:
            CertificateVerification instance
        """
        # Create verification request
        verification = VerificationService.create_verification_request(
            organization_id=organization_id,
            certificate_id=certificate_id,
            verification_method=VerificationMethod.DOCUMENT_CHECK
        )

        # Start verification
        verification.start_verification(
            verifier_id=UUID(verifier_id),
            verifier_name=verifier_name
        )

        # Calculate document hash
        document_hash = hashlib.sha256(document_content).hexdigest()
        verification.document_hash = document_hash
        verification.save()

        # Document verification would typically involve:
        # 1. OCR extraction
        # 2. Data validation against certificate record
        # 3. Visual inspection (if human-in-the-loop)

        return verification

    @staticmethod
    def get_certificate_verifications(
        organization_id: str,
        certificate_id: str
    ) -> List[CertificateVerification]:
        """
        Get all verifications for a certificate.

        Args:
            organization_id: Organization ID
            certificate_id: Certificate ID

        Returns:
            List of CertificateVerification instances
        """
        return list(
            CertificateVerification.objects.filter(
                organization_id=organization_id,
                certificate_id=certificate_id
            ).order_by('-requested_at')
        )

    @staticmethod
    def get_latest_verification(
        organization_id: str,
        certificate_id: str
    ) -> Optional[CertificateVerification]:
        """
        Get the latest verification for a certificate.

        Args:
            organization_id: Organization ID
            certificate_id: Certificate ID

        Returns:
            Latest CertificateVerification or None
        """
        return CertificateVerification.objects.filter(
            organization_id=organization_id,
            certificate_id=certificate_id,
            status=VerificationStatus.VERIFIED
        ).order_by('-completed_at').first()

    @staticmethod
    def get_pending_verifications(
        organization_id: str
    ) -> List[CertificateVerification]:
        """
        Get all pending verifications.

        Args:
            organization_id: Organization ID

        Returns:
            List of pending CertificateVerification instances
        """
        return list(
            CertificateVerification.objects.filter(
                organization_id=organization_id,
                status__in=[VerificationStatus.PENDING, VerificationStatus.IN_PROGRESS]
            ).order_by('requested_at')
        )

    @staticmethod
    def get_verification_statistics(
        organization_id: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get verification statistics.

        Args:
            organization_id: Organization ID
            days: Days to look back

        Returns:
            Statistics dict
        """
        return CertificateVerification.get_verification_statistics(
            organization_id=UUID(organization_id),
            days=days
        )

    @staticmethod
    def auto_verify_certificate(
        organization_id: str,
        certificate_id: str
    ) -> Optional[CertificateVerification]:
        """
        Attempt automatic verification of certificate.

        This would typically integrate with external authority APIs.

        Args:
            organization_id: Organization ID
            certificate_id: Certificate ID

        Returns:
            CertificateVerification instance or None if not possible
        """
        try:
            certificate = Certificate.objects.get(
                id=certificate_id,
                organization_id=organization_id
            )
        except Certificate.DoesNotExist:
            return None

        # Create automatic verification request
        verification = VerificationService.create_verification_request(
            organization_id=organization_id,
            certificate_id=certificate_id,
            verification_method=VerificationMethod.AUTOMATIC
        )

        verification.status = VerificationStatus.IN_PROGRESS
        verification.started_at = timezone.now()
        verification.save()

        # Here would integrate with authority APIs based on issuing_authority
        # For now, basic validation checks
        issues = []

        # Check expiry
        if certificate.is_expired:
            issues.append({
                'code': 'EXPIRED',
                'message': 'Certificate has expired',
                'severity': 'error'
            })

        # Check certificate number format (basic validation)
        if not certificate.certificate_number or len(certificate.certificate_number) < 3:
            issues.append({
                'code': 'INVALID_NUMBER',
                'message': 'Certificate number appears invalid',
                'severity': 'error'
            })

        is_valid = len([i for i in issues if i['severity'] == 'error']) == 0

        verification.complete_verification(
            is_valid=is_valid,
            validity_date=certificate.expiry_date if not certificate.is_expired else None,
            issues=issues,
            notes='Automatic verification completed'
        )

        if is_valid:
            certificate.verify(
                verified_by=None,
                method=VerificationMethod.AUTOMATIC,
                notes='Auto-verified'
            )

        logger.info(
            f"Auto-verification completed for certificate {certificate_id}",
            extra={'is_valid': is_valid}
        )

        return verification
