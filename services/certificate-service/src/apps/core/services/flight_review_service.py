# services/certificate-service/src/apps/core/services/flight_review_service.py
"""
Flight Review Service

Business logic for BFR, proficiency checks, and skill tests.
"""

import logging
from datetime import date, timedelta
from decimal import Decimal
from typing import List, Dict, Any, Optional
from uuid import UUID

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from ..models import (
    FlightReview,
    FlightReviewType,
    FlightReviewResult,
    FlightReviewStatus,
    SkillTest,
)

logger = logging.getLogger(__name__)


class FlightReviewService:
    """
    Service class for flight review operations.

    Handles BFR (Biennial Flight Review), proficiency checks,
    and skill tests per FAA/EASA regulations.
    """

    # ==========================================================================
    # CREATE OPERATIONS
    # ==========================================================================

    @staticmethod
    @transaction.atomic
    def record_flight_review(
        organization_id: UUID,
        user_id: UUID,
        review_type: str,
        review_date: date,
        instructor_id: UUID,
        instructor_name: str,
        result: str = FlightReviewResult.PASSED,
        ground_time_hours: Decimal = Decimal('1.0'),
        flight_time_hours: Decimal = Decimal('1.0'),
        simulator_time_hours: Decimal = Decimal('0.0'),
        aircraft_type: str = None,
        aircraft_icao: str = None,
        aircraft_registration: str = None,
        aircraft_id: UUID = None,
        rating_id: UUID = None,
        certificate_id: UUID = None,
        instructor_certificate_number: str = None,
        topics_covered: List[str] = None,
        maneuvers_performed: List[str] = None,
        areas_satisfactory: List[str] = None,
        areas_for_improvement: List[str] = None,
        unsatisfactory_items: List[str] = None,
        instructor_comments: str = None,
        recommendations: str = None,
        regulatory_reference: str = None,
        flight_id: UUID = None,
        document_url: str = None,
    ) -> Dict[str, Any]:
        """
        Record a flight review result.

        Args:
            organization_id: Organization UUID
            user_id: Pilot user UUID
            review_type: Type of review
            review_date: Date of review
            instructor_id: Instructor UUID
            instructor_name: Instructor name
            ... additional fields

        Returns:
            Flight review information dictionary
        """
        review = FlightReview(
            organization_id=organization_id,
            user_id=user_id,
            review_type=review_type,
            review_date=review_date,
            instructor_id=instructor_id,
            instructor_name=instructor_name,
            result=result,
            status=FlightReviewStatus.ACTIVE if result == FlightReviewResult.PASSED else FlightReviewStatus.PENDING,
            ground_time_hours=ground_time_hours,
            flight_time_hours=flight_time_hours,
            simulator_time_hours=simulator_time_hours,
            aircraft_type=aircraft_type,
            aircraft_icao=aircraft_icao,
            aircraft_registration=aircraft_registration,
            aircraft_id=aircraft_id,
            rating_id=rating_id,
            certificate_id=certificate_id,
            instructor_certificate_number=instructor_certificate_number,
            topics_covered=topics_covered or [],
            maneuvers_performed=maneuvers_performed or [],
            areas_satisfactory=areas_satisfactory or [],
            areas_for_improvement=areas_for_improvement or [],
            unsatisfactory_items=unsatisfactory_items or [],
            instructor_comments=instructor_comments,
            recommendations=recommendations,
            regulatory_reference=regulatory_reference,
            flight_id=flight_id,
            document_url=document_url,
        )
        review.save()

        # If passed, expire previous reviews of same type
        if result == FlightReviewResult.PASSED:
            FlightReview.objects.filter(
                organization_id=organization_id,
                user_id=user_id,
                review_type=review_type,
                status=FlightReviewStatus.ACTIVE,
            ).exclude(
                id=review.id
            ).update(
                status=FlightReviewStatus.EXPIRED
            )

        logger.info(
            f"Flight review recorded for user {user_id}: "
            f"{review_type} - {result}"
        )

        return review.get_validity_info()

    @staticmethod
    @transaction.atomic
    def record_skill_test(
        organization_id: UUID,
        user_id: UUID,
        test_type: str,
        test_date: date,
        result: str,
        examiner_id: UUID,
        examiner_name: str,
        examiner_number: str,
        aircraft_type: str,
        aircraft_icao: str = None,
        aircraft_registration: str = None,
        is_simulator: bool = False,
        simulator_level: str = None,
        oral_time_hours: Decimal = Decimal('0.0'),
        flight_time_hours: Decimal = Decimal('0.0'),
        test_sections: Dict = None,
        failed_sections: List[str] = None,
        examiner_authority: str = None,
        application_number: str = None,
        iacra_number: str = None,
        examiner_comments: str = None,
        retest_requirements: str = None,
        document_url: str = None,
    ) -> Dict[str, Any]:
        """
        Record a skill test (checkride) result.

        Args:
            organization_id: Organization UUID
            user_id: Applicant user UUID
            test_type: Type of skill test
            test_date: Date of test
            result: Test result
            examiner_id: Examiner UUID
            ... additional fields

        Returns:
            Skill test information dictionary
        """
        skill_test = SkillTest.objects.create(
            organization_id=organization_id,
            user_id=user_id,
            test_type=test_type,
            test_date=test_date,
            result=result,
            examiner_id=examiner_id,
            examiner_name=examiner_name,
            examiner_number=examiner_number,
            examiner_authority=examiner_authority,
            aircraft_type=aircraft_type,
            aircraft_icao=aircraft_icao,
            aircraft_registration=aircraft_registration,
            is_simulator=is_simulator,
            simulator_level=simulator_level,
            oral_time_hours=oral_time_hours,
            flight_time_hours=flight_time_hours,
            test_sections=test_sections or {},
            failed_sections=failed_sections or [],
            application_number=application_number,
            iacra_number=iacra_number,
            examiner_comments=examiner_comments,
            retest_requirements=retest_requirements,
            document_url=document_url,
        )

        logger.info(
            f"Skill test recorded for user {user_id}: "
            f"{test_type} - {result}"
        )

        return skill_test.get_test_info()

    # ==========================================================================
    # READ OPERATIONS
    # ==========================================================================

    @staticmethod
    def get_user_reviews(
        organization_id: UUID,
        user_id: UUID,
        review_type: str = None,
        include_expired: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Get all flight reviews for a user.

        Args:
            organization_id: Organization UUID
            user_id: User UUID
            review_type: Optional type filter
            include_expired: Include expired reviews

        Returns:
            List of review information dictionaries
        """
        query = FlightReview.objects.filter(
            organization_id=organization_id,
            user_id=user_id,
        )

        if review_type:
            query = query.filter(review_type=review_type)

        if not include_expired:
            query = query.filter(status=FlightReviewStatus.ACTIVE)

        return [r.get_validity_info() for r in query.order_by('-review_date')]

    @staticmethod
    def get_current_bfr(
        organization_id: UUID,
        user_id: UUID,
    ) -> Optional[Dict[str, Any]]:
        """
        Get current valid BFR for a user.

        Args:
            organization_id: Organization UUID
            user_id: User UUID

        Returns:
            BFR information or None
        """
        bfr = FlightReview.objects.filter(
            organization_id=organization_id,
            user_id=user_id,
            review_type=FlightReviewType.BFR,
            result=FlightReviewResult.PASSED,
            status=FlightReviewStatus.ACTIVE,
        ).order_by('-review_date').first()

        if not bfr:
            return None

        if bfr.is_expired:
            bfr.update_status()
            return None

        return bfr.get_validity_info()

    @staticmethod
    def get_user_skill_tests(
        organization_id: UUID,
        user_id: UUID,
        test_type: str = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Get skill tests for a user.

        Args:
            organization_id: Organization UUID
            user_id: User UUID
            test_type: Optional type filter
            limit: Maximum number of records

        Returns:
            List of skill test information dictionaries
        """
        query = SkillTest.objects.filter(
            organization_id=organization_id,
            user_id=user_id,
        )

        if test_type:
            query = query.filter(test_type=test_type)

        tests = query.order_by('-test_date')[:limit]
        return [t.get_test_info() for t in tests]

    # ==========================================================================
    # VALIDATION OPERATIONS
    # ==========================================================================

    @staticmethod
    def check_bfr_validity(
        organization_id: UUID,
        user_id: UUID,
    ) -> Dict[str, Any]:
        """
        Check if user has valid BFR.

        Args:
            organization_id: Organization UUID
            user_id: User UUID

        Returns:
            Validity check result
        """
        bfr = FlightReview.objects.filter(
            organization_id=organization_id,
            user_id=user_id,
            review_type=FlightReviewType.BFR,
            result=FlightReviewResult.PASSED,
            status=FlightReviewStatus.ACTIVE,
        ).order_by('-review_date').first()

        if not bfr:
            return {
                'is_valid': False,
                'error_code': 'NO_BFR',
                'message': 'No flight review on file',
                'bfr': None,
            }

        if bfr.is_expired:
            bfr.update_status()
            return {
                'is_valid': False,
                'error_code': 'EXPIRED',
                'message': f'Flight review expired on {bfr.expiry_date}',
                'bfr': bfr.get_validity_info(),
            }

        result = {
            'is_valid': True,
            'bfr': bfr.get_validity_info(),
        }

        if bfr.is_expiring_soon:
            result['warning'] = f'Flight review expires in {bfr.days_until_expiry} days'

        return result

    @staticmethod
    def check_ipc_validity(
        organization_id: UUID,
        user_id: UUID,
    ) -> Dict[str, Any]:
        """
        Check if user has valid IPC (Instrument Proficiency Check).

        Args:
            organization_id: Organization UUID
            user_id: User UUID

        Returns:
            Validity check result
        """
        ipc = FlightReview.objects.filter(
            organization_id=organization_id,
            user_id=user_id,
            review_type=FlightReviewType.IPC,
            result=FlightReviewResult.PASSED,
            status=FlightReviewStatus.ACTIVE,
        ).order_by('-review_date').first()

        if not ipc:
            return {
                'is_valid': False,
                'error_code': 'NO_IPC',
                'message': 'No instrument proficiency check on file',
                'ipc': None,
            }

        if ipc.is_expired:
            ipc.update_status()
            return {
                'is_valid': False,
                'error_code': 'EXPIRED',
                'message': f'IPC expired on {ipc.expiry_date}',
                'ipc': ipc.get_validity_info(),
            }

        return {
            'is_valid': True,
            'ipc': ipc.get_validity_info(),
        }

    @staticmethod
    def get_comprehensive_review_status(
        organization_id: UUID,
        user_id: UUID,
    ) -> Dict[str, Any]:
        """
        Get comprehensive flight review status for a user.

        Args:
            organization_id: Organization UUID
            user_id: User UUID

        Returns:
            Comprehensive status dictionary
        """
        bfr_status = FlightReviewService.check_bfr_validity(organization_id, user_id)
        ipc_status = FlightReviewService.check_ipc_validity(organization_id, user_id)

        # Get proficiency checks
        proficiency_checks = FlightReview.objects.filter(
            organization_id=organization_id,
            user_id=user_id,
            review_type=FlightReviewType.PROFICIENCY_CHECK,
            status=FlightReviewStatus.ACTIVE,
        ).order_by('-review_date')

        issues = []
        warnings = []

        if not bfr_status['is_valid']:
            issues.append({
                'type': 'bfr',
                'code': bfr_status.get('error_code'),
                'message': bfr_status.get('message'),
            })
        elif bfr_status.get('warning'):
            warnings.append({
                'type': 'bfr',
                'message': bfr_status.get('warning'),
            })

        return {
            'user_id': str(user_id),
            'is_current': bfr_status['is_valid'],
            'bfr': bfr_status,
            'ipc': ipc_status,
            'proficiency_checks': [p.get_validity_info() for p in proficiency_checks],
            'issues': issues,
            'warnings': warnings,
            'checked_at': timezone.now().isoformat(),
        }

    # ==========================================================================
    # EXPIRY MANAGEMENT
    # ==========================================================================

    @staticmethod
    def get_expiring_reviews(
        organization_id: UUID = None,
        days_ahead: int = 90,
    ) -> List[Dict[str, Any]]:
        """
        Get flight reviews expiring within specified days.

        Args:
            organization_id: Optional organization filter
            days_ahead: Days to look ahead

        Returns:
            List of expiring reviews
        """
        today = date.today()
        threshold = today + timedelta(days=days_ahead)

        query = FlightReview.objects.filter(
            status=FlightReviewStatus.ACTIVE,
            result=FlightReviewResult.PASSED,
            expiry_date__gte=today,
            expiry_date__lte=threshold,
        )

        if organization_id:
            query = query.filter(organization_id=organization_id)

        return [
            {
                **r.get_validity_info(),
                'urgency': 'critical' if r.days_until_expiry <= 30 else
                          'warning' if r.days_until_expiry <= 60 else 'info',
            }
            for r in query.order_by('expiry_date')
        ]

    @staticmethod
    @transaction.atomic
    def update_expired_statuses() -> int:
        """
        Update status of expired flight reviews.

        Returns:
            Number of records updated
        """
        count = FlightReview.objects.filter(
            status=FlightReviewStatus.ACTIVE,
            expiry_date__lt=date.today(),
        ).update(status=FlightReviewStatus.EXPIRED)

        if count > 0:
            logger.info(f"Updated {count} expired flight reviews")

        return count

    # ==========================================================================
    # VERIFICATION
    # ==========================================================================

    @staticmethod
    @transaction.atomic
    def verify_review(
        review_id: UUID,
        verified_by: UUID,
        notes: str = None,
    ) -> Dict[str, Any]:
        """
        Verify a flight review record.

        Args:
            review_id: Review UUID
            verified_by: Verifying user UUID
            notes: Verification notes

        Returns:
            Updated review information
        """
        review = FlightReview.objects.get(id=review_id)
        review.verified = True
        review.verified_at = timezone.now()
        review.verified_by = verified_by
        review.save()

        logger.info(f"Flight review {review_id} verified by {verified_by}")

        return review.get_validity_info()

    # ==========================================================================
    # STATISTICS
    # ==========================================================================

    @staticmethod
    def get_instructor_statistics(
        organization_id: UUID,
        instructor_id: UUID,
        start_date: date = None,
        end_date: date = None,
    ) -> Dict[str, Any]:
        """
        Get flight review statistics for an instructor.

        Args:
            organization_id: Organization UUID
            instructor_id: Instructor UUID
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            Statistics dictionary
        """
        query = FlightReview.objects.filter(
            organization_id=organization_id,
            instructor_id=instructor_id,
        )

        if start_date:
            query = query.filter(review_date__gte=start_date)
        if end_date:
            query = query.filter(review_date__lte=end_date)

        total = query.count()
        by_type = {}
        by_result = {}

        for review in query:
            by_type[review.review_type] = by_type.get(review.review_type, 0) + 1
            by_result[review.result] = by_result.get(review.result, 0) + 1

        return {
            'instructor_id': str(instructor_id),
            'total_reviews': total,
            'by_type': by_type,
            'by_result': by_result,
            'period': {
                'start': start_date.isoformat() if start_date else None,
                'end': end_date.isoformat() if end_date else None,
            },
        }
