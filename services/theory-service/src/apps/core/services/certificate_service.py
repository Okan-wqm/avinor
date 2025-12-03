# services/theory-service/src/apps/core/services/certificate_service.py
"""
Certificate Service

Business logic for certificate management.
"""

import logging
from typing import Dict, Any, List, Optional
from uuid import UUID
from decimal import Decimal
from datetime import date, timedelta

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from ..models import (
    Certificate,
    CourseEnrollment,
    Course,
    CertificateStatus,
)

logger = logging.getLogger(__name__)


class CertificateService:
    """Service for managing certificates."""

    @staticmethod
    def get_certificates(
        organization_id: str,
        user_id: str = None,
        course_id: str = None,
        status: str = None,
    ) -> List[Certificate]:
        """
        Get certificates with optional filtering.

        Args:
            organization_id: Organization ID
            user_id: Filter by user
            course_id: Filter by course
            status: Filter by status

        Returns:
            List of certificates
        """
        queryset = Certificate.objects.filter(organization_id=organization_id)

        if user_id:
            queryset = queryset.filter(user_id=user_id)

        if course_id:
            queryset = queryset.filter(course_id=course_id)

        if status:
            queryset = queryset.filter(status=status)

        return queryset.order_by('-issued_at')

    @staticmethod
    @transaction.atomic
    def generate_certificate(
        enrollment_id: str,
        organization_id: str,
        recipient_name: str,
        recipient_email: str = '',
        template_id: str = None,
        signed_by: str = '',
        signature_title: str = '',
        valid_years: int = None,
        issued_by: str = None,
    ) -> Certificate:
        """
        Generate a certificate for a completed enrollment.

        Args:
            enrollment_id: Enrollment ID
            organization_id: Organization ID
            recipient_name: Certificate recipient name
            recipient_email: Recipient email
            template_id: Certificate template ID
            signed_by: Signature name
            signature_title: Signature title
            valid_years: Years of validity (None for perpetual)
            issued_by: User ID who issued

        Returns:
            Generated certificate
        """
        enrollment = CourseEnrollment.objects.select_related(
            'course'
        ).get(
            id=enrollment_id,
            organization_id=organization_id
        )

        # Verify enrollment is completed
        if not enrollment.passed:
            raise ValueError("Cannot generate certificate for non-passed enrollment")

        # Check if certificate already exists
        existing = Certificate.objects.filter(
            enrollment=enrollment,
            status__in=[CertificateStatus.GENERATED, CertificateStatus.ISSUED]
        ).first()

        if existing:
            raise ValueError("Certificate already exists for this enrollment")

        course = enrollment.course

        # Generate certificate number and verification code
        certificate_number = Certificate.generate_certificate_number(
            str(organization_id),
            course.code
        )
        verification_code = Certificate.generate_verification_code()

        # Calculate validity
        valid_from = date.today()
        valid_until = None
        is_perpetual = True

        if valid_years:
            valid_until = valid_from + timedelta(days=valid_years * 365)
            is_perpetual = False

        # Create certificate
        certificate = Certificate.objects.create(
            organization_id=organization_id,
            course=course,
            enrollment=enrollment,
            user_id=enrollment.user_id,
            certificate_number=certificate_number,
            title=f"{course.name} Certificate",
            recipient_name=recipient_name,
            recipient_email=recipient_email,
            course_name=course.name,
            course_category=course.category,
            completion_date=enrollment.completed_at.date() if enrollment.completed_at else date.today(),
            score=enrollment.best_score,
            grade=CertificateService._calculate_grade(enrollment.best_score),
            hours_completed=Decimal(str(enrollment.total_time_spent_seconds / 3600)),
            valid_from=valid_from,
            valid_until=valid_until,
            is_perpetual=is_perpetual,
            status=CertificateStatus.GENERATED,
            template_id=template_id,
            verification_code=verification_code,
            signed_by=signed_by,
            signature_title=signature_title,
        )

        logger.info(f"Generated certificate: {certificate.id}")

        return certificate

    @staticmethod
    @transaction.atomic
    def issue_certificate(
        certificate_id: str,
        organization_id: str,
        issued_by: str = None
    ) -> Certificate:
        """
        Issue a generated certificate.

        Args:
            certificate_id: Certificate ID
            organization_id: Organization ID
            issued_by: User ID who issued

        Returns:
            Issued certificate
        """
        certificate = Certificate.objects.select_for_update().get(
            id=certificate_id,
            organization_id=organization_id
        )

        if certificate.status != CertificateStatus.GENERATED:
            raise ValueError("Certificate must be in GENERATED status to issue")

        certificate.issue(issued_by)

        # Publish event
        from ..events.publishers import publish_certificate_issued
        publish_certificate_issued(
            organization_id=str(organization_id),
            certificate_id=str(certificate.id),
            user_id=str(certificate.user_id),
            course_id=str(certificate.course_id)
        )

        logger.info(f"Issued certificate: {certificate.id}")

        return certificate

    @staticmethod
    @transaction.atomic
    def revoke_certificate(
        certificate_id: str,
        organization_id: str,
        reason: str,
        revoked_by: str = None
    ) -> Certificate:
        """
        Revoke a certificate.

        Args:
            certificate_id: Certificate ID
            organization_id: Organization ID
            reason: Revocation reason
            revoked_by: User ID who revoked

        Returns:
            Revoked certificate
        """
        certificate = Certificate.objects.select_for_update().get(
            id=certificate_id,
            organization_id=organization_id
        )

        certificate.revoke(reason, revoked_by)

        logger.info(f"Revoked certificate: {certificate.id}")

        return certificate

    @staticmethod
    def verify_certificate(
        verification_code: str = None,
        certificate_number: str = None
    ) -> Dict[str, Any]:
        """
        Verify a certificate.

        Args:
            verification_code: Verification code
            certificate_number: Certificate number

        Returns:
            Verification result
        """
        if not verification_code and not certificate_number:
            raise ValueError("Must provide verification_code or certificate_number")

        filters = {}
        if verification_code:
            filters['verification_code'] = verification_code
        if certificate_number:
            filters['certificate_number'] = certificate_number

        try:
            certificate = Certificate.objects.get(**filters)
            return certificate.verify()
        except Certificate.DoesNotExist:
            return {
                'valid': False,
                'error': 'Certificate not found'
            }

    @staticmethod
    def get_certificate(
        certificate_id: str,
        organization_id: str = None,
        user_id: str = None
    ) -> Certificate:
        """
        Get certificate by ID.

        Args:
            certificate_id: Certificate ID
            organization_id: Optional organization filter
            user_id: Optional user filter

        Returns:
            Certificate instance
        """
        filters = {'id': certificate_id}
        if organization_id:
            filters['organization_id'] = organization_id
        if user_id:
            filters['user_id'] = user_id

        return Certificate.objects.select_related('course', 'enrollment').get(**filters)

    @staticmethod
    @transaction.atomic
    def update_certificate_document(
        certificate_id: str,
        organization_id: str,
        pdf_url: str = None,
        thumbnail_url: str = None,
        qr_code_url: str = None,
        share_url: str = None,
        verification_url: str = None,
    ) -> Certificate:
        """
        Update certificate document URLs.

        Args:
            certificate_id: Certificate ID
            organization_id: Organization ID
            pdf_url: PDF document URL
            thumbnail_url: Thumbnail URL
            qr_code_url: QR code URL
            share_url: Share URL
            verification_url: Verification URL

        Returns:
            Updated certificate
        """
        certificate = Certificate.objects.select_for_update().get(
            id=certificate_id,
            organization_id=organization_id
        )

        if pdf_url:
            certificate.pdf_url = pdf_url
        if thumbnail_url:
            certificate.thumbnail_url = thumbnail_url
        if qr_code_url:
            certificate.qr_code_url = qr_code_url
        if share_url:
            certificate.share_url = share_url
        if verification_url:
            certificate.verification_url = verification_url

        certificate.save()

        return certificate

    @staticmethod
    def make_public(
        certificate_id: str,
        user_id: str
    ) -> Certificate:
        """
        Make certificate publicly shareable.

        Args:
            certificate_id: Certificate ID
            user_id: User ID (must be owner)

        Returns:
            Updated certificate
        """
        certificate = Certificate.objects.get(
            id=certificate_id,
            user_id=user_id
        )

        certificate.is_public = True
        certificate.save()

        return certificate

    @staticmethod
    def make_private(
        certificate_id: str,
        user_id: str
    ) -> Certificate:
        """
        Make certificate private.

        Args:
            certificate_id: Certificate ID
            user_id: User ID (must be owner)

        Returns:
            Updated certificate
        """
        certificate = Certificate.objects.get(
            id=certificate_id,
            user_id=user_id
        )

        certificate.is_public = False
        certificate.save()

        return certificate

    @staticmethod
    def record_linkedin_share(
        certificate_id: str,
        user_id: str
    ) -> Certificate:
        """
        Record that certificate was added to LinkedIn.

        Args:
            certificate_id: Certificate ID
            user_id: User ID

        Returns:
            Updated certificate
        """
        certificate = Certificate.objects.get(
            id=certificate_id,
            user_id=user_id
        )

        certificate.linkedin_added = True
        certificate.save()

        return certificate

    @staticmethod
    def get_public_certificate(
        certificate_id: str = None,
        verification_code: str = None
    ) -> Dict[str, Any]:
        """
        Get publicly accessible certificate data.

        Args:
            certificate_id: Certificate ID
            verification_code: Verification code

        Returns:
            Public certificate data
        """
        filters = {}
        if certificate_id:
            filters['id'] = certificate_id
        if verification_code:
            filters['verification_code'] = verification_code

        certificate = Certificate.objects.get(**filters)

        if not certificate.is_public:
            raise ValueError("Certificate is not public")

        certificate.record_view()

        return certificate.get_public_data()

    @staticmethod
    def get_user_certificates(
        user_id: str,
        organization_id: str = None
    ) -> List[Dict[str, Any]]:
        """
        Get all certificates for a user.

        Args:
            user_id: User ID
            organization_id: Optional organization filter

        Returns:
            List of certificate summaries
        """
        filters = {'user_id': user_id}
        if organization_id:
            filters['organization_id'] = organization_id

        certificates = Certificate.objects.filter(
            **filters,
            status=CertificateStatus.ISSUED
        ).select_related('course').order_by('-issued_at')

        return [
            {
                'id': str(cert.id),
                'certificate_number': cert.certificate_number,
                'title': cert.title,
                'course_name': cert.course_name,
                'completion_date': cert.completion_date.isoformat(),
                'score': float(cert.score) if cert.score else None,
                'grade': cert.grade,
                'is_valid': cert.is_valid,
                'pdf_url': cert.pdf_url,
                'verification_url': cert.verification_url,
                'is_public': cert.is_public,
            }
            for cert in certificates
        ]

    @staticmethod
    def check_expiring_certificates(
        organization_id: str,
        days_before: int = 30
    ) -> List[Certificate]:
        """
        Get certificates expiring within specified days.

        Args:
            organization_id: Organization ID
            days_before: Days before expiry to check

        Returns:
            List of expiring certificates
        """
        expiry_date = date.today() + timedelta(days=days_before)

        return Certificate.objects.filter(
            organization_id=organization_id,
            status=CertificateStatus.ISSUED,
            is_perpetual=False,
            valid_until__lte=expiry_date,
            valid_until__gt=date.today()
        ).order_by('valid_until')

    @staticmethod
    def _calculate_grade(score: Decimal) -> str:
        """Calculate grade letter from score."""
        if score is None:
            return ''

        score_float = float(score)

        if score_float >= 97:
            return 'A+'
        elif score_float >= 93:
            return 'A'
        elif score_float >= 90:
            return 'A-'
        elif score_float >= 87:
            return 'B+'
        elif score_float >= 83:
            return 'B'
        elif score_float >= 80:
            return 'B-'
        elif score_float >= 77:
            return 'C+'
        elif score_float >= 73:
            return 'C'
        elif score_float >= 70:
            return 'C-'
        elif score_float >= 60:
            return 'D'
        else:
            return 'F'
