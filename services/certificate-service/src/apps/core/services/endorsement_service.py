# services/certificate-service/src/apps/core/services/endorsement_service.py
"""
Endorsement Service

Business logic for endorsement management.
"""

import logging
from datetime import date, timedelta
from typing import List, Dict, Any, Optional
from uuid import UUID

from django.db import transaction
from django.db.models import Q, Count
from django.utils import timezone

from ..models import (
    Endorsement,
    EndorsementType,
    EndorsementStatus,
    Certificate,
    CertificateType,
    CertificateStatus,
)

logger = logging.getLogger(__name__)


class EndorsementService:
    """Service for managing endorsements."""

    @staticmethod
    def create_endorsement(
        organization_id: str,
        student_id: str,
        instructor_id: str,
        endorsement_type: str,
        issue_date: date,
        **kwargs
    ) -> Endorsement:
        """
        Create a new endorsement.

        Args:
            organization_id: Organization ID
            student_id: Student user ID
            instructor_id: Instructor user ID
            endorsement_type: Type of endorsement
            issue_date: Issue date
            **kwargs: Additional fields

        Returns:
            Created Endorsement instance

        Raises:
            ValueError: If instructor not authorized
        """
        # Verify instructor has valid instructor certificate
        instructor_cert = Certificate.objects.filter(
            organization_id=organization_id,
            user_id=instructor_id,
            certificate_type=CertificateType.INSTRUCTOR_CERTIFICATE,
            status=CertificateStatus.ACTIVE,
            verified=True
        ).exclude(expiry_date__lt=date.today()).first()

        if not instructor_cert:
            raise ValueError('Instructor does not have valid instructor certificate')

        endorsement = Endorsement.objects.create(
            organization_id=organization_id,
            student_id=student_id,
            instructor_id=instructor_id,
            endorsement_type=endorsement_type,
            issue_date=issue_date,
            instructor_certificate_number=instructor_cert.certificate_number,
            instructor_certificate_expiry=instructor_cert.expiry_date,
            status=EndorsementStatus.PENDING,
            **kwargs
        )

        logger.info(
            f"Created endorsement {endorsement.id}",
            extra={
                'endorsement_id': str(endorsement.id),
                'student_id': student_id,
                'instructor_id': instructor_id,
                'type': endorsement_type
            }
        )

        return endorsement

    @staticmethod
    def get_endorsement(
        organization_id: str,
        endorsement_id: str
    ) -> Endorsement:
        """
        Get an endorsement by ID.

        Args:
            organization_id: Organization ID
            endorsement_id: Endorsement ID

        Returns:
            Endorsement instance

        Raises:
            ValueError: If not found
        """
        try:
            return Endorsement.objects.get(
                id=endorsement_id,
                organization_id=organization_id
            )
        except Endorsement.DoesNotExist:
            raise ValueError(f'Endorsement {endorsement_id} not found')

    @staticmethod
    def list_endorsements(
        organization_id: str,
        student_id: Optional[str] = None,
        instructor_id: Optional[str] = None,
        endorsement_type: Optional[str] = None,
        status: Optional[str] = None,
        active_only: bool = False
    ) -> List[Endorsement]:
        """
        List endorsements with filters.

        Args:
            organization_id: Organization ID
            student_id: Filter by student
            instructor_id: Filter by instructor
            endorsement_type: Filter by type
            status: Filter by status
            active_only: Only return active/valid endorsements

        Returns:
            List of Endorsement instances
        """
        queryset = Endorsement.objects.filter(organization_id=organization_id)

        if student_id:
            queryset = queryset.filter(student_id=student_id)
        if instructor_id:
            queryset = queryset.filter(instructor_id=instructor_id)
        if endorsement_type:
            queryset = queryset.filter(endorsement_type=endorsement_type)
        if status:
            queryset = queryset.filter(status=status)
        if active_only:
            queryset = queryset.filter(status=EndorsementStatus.ACTIVE)
            # Exclude expired non-permanent endorsements
            queryset = queryset.filter(
                Q(is_permanent=True) |
                Q(expiry_date__isnull=True) |
                Q(expiry_date__gte=date.today())
            )

        return list(queryset.order_by('-issue_date'))

    @staticmethod
    def update_endorsement(
        organization_id: str,
        endorsement_id: str,
        **updates
    ) -> Endorsement:
        """
        Update an endorsement.

        Args:
            organization_id: Organization ID
            endorsement_id: Endorsement ID
            **updates: Fields to update

        Returns:
            Updated Endorsement instance
        """
        endorsement = EndorsementService.get_endorsement(
            organization_id, endorsement_id
        )

        if endorsement.status == EndorsementStatus.REVOKED:
            raise ValueError('Cannot update revoked endorsement')

        if endorsement.is_signed:
            # Limited updates allowed after signing
            allowed_fields = ['notes', 'metadata']
            for field in list(updates.keys()):
                if field not in allowed_fields:
                    del updates[field]

        for field, value in updates.items():
            if hasattr(endorsement, field):
                setattr(endorsement, field, value)

        endorsement.save()

        logger.info(f"Updated endorsement {endorsement_id}")

        return endorsement

    @staticmethod
    def delete_endorsement(
        organization_id: str,
        endorsement_id: str
    ) -> bool:
        """
        Delete an endorsement (only if pending).

        Args:
            organization_id: Organization ID
            endorsement_id: Endorsement ID

        Returns:
            True if deleted

        Raises:
            ValueError: If endorsement is signed/active
        """
        endorsement = EndorsementService.get_endorsement(
            organization_id, endorsement_id
        )

        if endorsement.status != EndorsementStatus.PENDING:
            raise ValueError('Can only delete pending endorsements')

        endorsement.delete()

        logger.info(f"Deleted endorsement {endorsement_id}")

        return True

    @staticmethod
    def sign_endorsement(
        organization_id: str,
        endorsement_id: str,
        instructor_id: str,
        signature_data: Dict[str, Any]
    ) -> Endorsement:
        """
        Sign an endorsement.

        Args:
            organization_id: Organization ID
            endorsement_id: Endorsement ID
            instructor_id: Instructor signing
            signature_data: Digital signature data

        Returns:
            Signed Endorsement instance

        Raises:
            ValueError: If instructor mismatch or already signed
        """
        endorsement = EndorsementService.get_endorsement(
            organization_id, endorsement_id
        )

        if str(endorsement.instructor_id) != instructor_id:
            raise ValueError('Only the assigned instructor can sign')

        if endorsement.is_signed:
            raise ValueError('Endorsement already signed')

        # Get instructor certificate info
        instructor_cert = Certificate.objects.filter(
            organization_id=organization_id,
            user_id=instructor_id,
            certificate_type=CertificateType.INSTRUCTOR_CERTIFICATE,
            status=CertificateStatus.ACTIVE,
        ).first()

        if not instructor_cert:
            raise ValueError('Instructor certificate not found')

        endorsement.sign(
            instructor_id=UUID(instructor_id),
            signature_data=signature_data,
            certificate_number=instructor_cert.certificate_number,
            certificate_expiry=instructor_cert.expiry_date
        )

        logger.info(
            f"Signed endorsement {endorsement_id}",
            extra={
                'endorsement_id': endorsement_id,
                'instructor_id': instructor_id
            }
        )

        return endorsement

    @staticmethod
    def revoke_endorsement(
        organization_id: str,
        endorsement_id: str,
        reason: str,
        revoked_by: str
    ) -> Endorsement:
        """
        Revoke an endorsement.

        Args:
            organization_id: Organization ID
            endorsement_id: Endorsement ID
            reason: Revocation reason
            revoked_by: User revoking

        Returns:
            Revoked Endorsement instance
        """
        endorsement = EndorsementService.get_endorsement(
            organization_id, endorsement_id
        )

        endorsement.revoke(reason)

        logger.warning(
            f"Revoked endorsement {endorsement_id}",
            extra={
                'endorsement_id': endorsement_id,
                'reason': reason,
                'revoked_by': revoked_by
            }
        )

        return endorsement

    @staticmethod
    def get_student_endorsements(
        organization_id: str,
        student_id: str,
        active_only: bool = True
    ) -> List[Endorsement]:
        """
        Get all endorsements for a student.

        Args:
            organization_id: Organization ID
            student_id: Student ID
            active_only: Only return active endorsements

        Returns:
            List of Endorsement instances
        """
        return EndorsementService.list_endorsements(
            organization_id=organization_id,
            student_id=student_id,
            active_only=active_only
        )

    @staticmethod
    def check_solo_authorization(
        organization_id: str,
        student_id: str,
        aircraft_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Check if student is authorized for solo flight.

        Args:
            organization_id: Organization ID
            student_id: Student ID
            aircraft_type: Optional specific aircraft type

        Returns:
            Authorization status dict
        """
        solo_endorsements = Endorsement.objects.filter(
            organization_id=organization_id,
            student_id=student_id,
            endorsement_type=EndorsementType.SOLO_FLIGHT,
            status=EndorsementStatus.ACTIVE
        ).filter(
            Q(is_permanent=True) |
            Q(expiry_date__isnull=True) |
            Q(expiry_date__gte=date.today())
        )

        if aircraft_type:
            solo_endorsements = solo_endorsements.filter(
                Q(aircraft_type__isnull=True) |
                Q(aircraft_type=aircraft_type)
            )

        endorsement = solo_endorsements.order_by('-issue_date').first()

        if not endorsement:
            return {
                'authorized': False,
                'message': 'No valid solo endorsement found',
                'endorsement': None,
            }

        return {
            'authorized': True,
            'message': 'Solo flight authorized',
            'endorsement': endorsement.get_validity_info(),
            'conditions': endorsement.conditions,
            'limitations': endorsement.limitations,
            'airports': endorsement.airports,
        }

    @staticmethod
    def create_solo_endorsement(
        organization_id: str,
        student_id: str,
        student_name: str,
        instructor_id: str,
        instructor_name: str,
        aircraft_type: str,
        validity_days: int = 90,
        airports: Optional[List[str]] = None,
        conditions: Optional[List[str]] = None,
        weather_minimums: Optional[Dict[str, Any]] = None,
    ) -> Endorsement:
        """
        Create a solo flight endorsement.

        Args:
            organization_id: Organization ID
            student_id: Student ID
            student_name: Student name
            instructor_id: Instructor ID
            instructor_name: Instructor name
            aircraft_type: Aircraft make/model
            validity_days: Days endorsement is valid
            airports: Authorized airports
            conditions: Endorsement conditions
            weather_minimums: Weather limitations

        Returns:
            Created Endorsement instance
        """
        # Generate endorsement text
        endorsement_text = Endorsement.generate_endorsement_text(
            endorsement_type=EndorsementType.SOLO_FLIGHT,
            student_name=student_name,
            aircraft_type=aircraft_type,
            validity_days=validity_days
        )

        return EndorsementService.create_endorsement(
            organization_id=organization_id,
            student_id=student_id,
            instructor_id=instructor_id,
            endorsement_type=EndorsementType.SOLO_FLIGHT,
            issue_date=date.today(),
            student_name=student_name,
            instructor_name=instructor_name,
            aircraft_type=aircraft_type,
            validity_days=validity_days,
            airports=airports or [],
            conditions=conditions or [],
            weather_minimums=weather_minimums or {},
            endorsement_text=endorsement_text,
            day_night_restriction='day_only',
        )

    @staticmethod
    def get_expiring_endorsements(
        organization_id: str,
        days_ahead: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Get endorsements expiring soon.

        Args:
            organization_id: Organization ID
            days_ahead: Days to look ahead

        Returns:
            List of expiring endorsement info dicts
        """
        expiry_date = date.today() + timedelta(days=days_ahead)

        endorsements = Endorsement.objects.filter(
            organization_id=organization_id,
            status=EndorsementStatus.ACTIVE,
            is_permanent=False,
            expiry_date__isnull=False,
            expiry_date__lte=expiry_date,
            expiry_date__gte=date.today()
        ).order_by('expiry_date')

        return [
            {
                'endorsement_id': str(e.id),
                'student_id': str(e.student_id),
                'student_name': e.student_name,
                'endorsement_type': e.endorsement_type,
                'expiry_date': e.expiry_date.isoformat(),
                'days_remaining': e.days_until_expiry,
            }
            for e in endorsements
        ]

    @staticmethod
    def get_endorsement_statistics(
        organization_id: str
    ) -> Dict[str, Any]:
        """
        Get endorsement statistics for organization.

        Args:
            organization_id: Organization ID

        Returns:
            Statistics dict
        """
        endorsements = Endorsement.objects.filter(organization_id=organization_id)

        total = endorsements.count()
        by_type = endorsements.values('endorsement_type').annotate(count=Count('id'))
        by_status = endorsements.values('status').annotate(count=Count('id'))

        return {
            'total_endorsements': total,
            'by_type': {t['endorsement_type']: t['count'] for t in by_type},
            'by_status': {s['status']: s['count'] for s in by_status},
            'active_count': endorsements.filter(status=EndorsementStatus.ACTIVE).count(),
            'pending_signature': endorsements.filter(status=EndorsementStatus.PENDING).count(),
        }
