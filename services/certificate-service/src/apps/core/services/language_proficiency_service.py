# services/certificate-service/src/apps/core/services/language_proficiency_service.py
"""
Language Proficiency Service

Business logic for ICAO language proficiency management.
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
    LanguageProficiency,
    LanguageTestHistory,
    LanguageCode,
    ProficiencyLevel,
    LanguageProficiencyStatus,
)

logger = logging.getLogger(__name__)


class LanguageProficiencyService:
    """
    Service class for language proficiency operations.

    Handles ICAO language proficiency requirements per Doc 9835.
    """

    # ==========================================================================
    # CREATE OPERATIONS
    # ==========================================================================

    @staticmethod
    @transaction.atomic
    def record_test_result(
        organization_id: UUID,
        user_id: UUID,
        language: str,
        test_date: date,
        test_center: str,
        examiner_name: str,
        pronunciation_level: int,
        structure_level: int,
        vocabulary_level: int,
        fluency_level: int,
        comprehension_level: int,
        interaction_level: int,
        test_center_code: str = None,
        examiner_id: UUID = None,
        examiner_number: str = None,
        issuing_authority: str = None,
        certificate_number: str = None,
        notes: str = None,
        examiner_comments: str = None,
        areas_for_improvement: str = None,
    ) -> Dict[str, Any]:
        """
        Record a language proficiency test result.

        Args:
            organization_id: Organization UUID
            user_id: User UUID
            language: Language code
            test_date: Date of test
            test_center: Test center name
            examiner_name: Examiner name
            *_level: Component level scores (1-6)
            ... additional optional fields

        Returns:
            Dictionary with test result and proficiency record
        """
        # Calculate overall level (minimum of all components)
        overall_level = min(
            pronunciation_level,
            structure_level,
            vocabulary_level,
            fluency_level,
            comprehension_level,
            interaction_level
        )

        # Determine if test is passed (Level 4 or above is operational)
        passed = overall_level >= 4

        # Create test history record
        test_history = LanguageTestHistory.objects.create(
            organization_id=organization_id,
            user_id=user_id,
            language=language,
            test_date=test_date,
            test_center=test_center,
            examiner_name=examiner_name,
            passed=passed,
            overall_level=overall_level,
            pronunciation_level=pronunciation_level,
            structure_level=structure_level,
            vocabulary_level=vocabulary_level,
            fluency_level=fluency_level,
            comprehension_level=comprehension_level,
            interaction_level=interaction_level,
            examiner_comments=examiner_comments,
            areas_for_improvement=areas_for_improvement,
        )

        proficiency = None
        if passed:
            # Create or update proficiency record
            proficiency = LanguageProficiency.objects.create(
                organization_id=organization_id,
                user_id=user_id,
                language=language,
                proficiency_level=overall_level,
                pronunciation_level=pronunciation_level,
                structure_level=structure_level,
                vocabulary_level=vocabulary_level,
                fluency_level=fluency_level,
                comprehension_level=comprehension_level,
                interaction_level=interaction_level,
                test_date=test_date,
                test_center=test_center,
                test_center_code=test_center_code,
                examiner_name=examiner_name,
                examiner_id=examiner_id,
                examiner_number=examiner_number,
                issue_date=test_date,
                issuing_authority=issuing_authority or 'Unknown',
                certificate_number=certificate_number,
                status=LanguageProficiencyStatus.ACTIVE,
                notes=notes,
            )

            # Link proficiency to test history
            test_history.proficiency = proficiency
            test_history.save(update_fields=['proficiency'])

            # Expire any previous proficiencies for same language
            LanguageProficiency.objects.filter(
                organization_id=organization_id,
                user_id=user_id,
                language=language,
                status=LanguageProficiencyStatus.ACTIVE,
            ).exclude(
                id=proficiency.id
            ).update(
                status=LanguageProficiencyStatus.EXPIRED
            )

        logger.info(
            f"Language test recorded for user {user_id}: "
            f"{language} Level {overall_level} ({'PASS' if passed else 'FAIL'})"
        )

        return {
            'test_history': {
                'id': str(test_history.id),
                'language': language,
                'test_date': test_date.isoformat(),
                'passed': passed,
                'overall_level': overall_level,
            },
            'proficiency': proficiency.get_validity_info() if proficiency else None,
        }

    # ==========================================================================
    # READ OPERATIONS
    # ==========================================================================

    @staticmethod
    def get_user_proficiencies(
        organization_id: UUID,
        user_id: UUID,
        language: str = None,
        include_expired: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Get all language proficiencies for a user.

        Args:
            organization_id: Organization UUID
            user_id: User UUID
            language: Optional language filter
            include_expired: Include expired proficiencies

        Returns:
            List of proficiency information dictionaries
        """
        query = LanguageProficiency.objects.filter(
            organization_id=organization_id,
            user_id=user_id,
        )

        if language:
            query = query.filter(language=language)

        if not include_expired:
            query = query.filter(status=LanguageProficiencyStatus.ACTIVE)

        return [p.get_validity_info() for p in query.order_by('-test_date')]

    @staticmethod
    def get_english_proficiency(
        organization_id: UUID,
        user_id: UUID,
    ) -> Optional[Dict[str, Any]]:
        """
        Get current English language proficiency.

        Required for international operations.

        Args:
            organization_id: Organization UUID
            user_id: User UUID

        Returns:
            Proficiency information or None
        """
        proficiency = LanguageProficiency.objects.filter(
            organization_id=organization_id,
            user_id=user_id,
            language=LanguageCode.ENGLISH,
            status=LanguageProficiencyStatus.ACTIVE,
        ).order_by('-test_date').first()

        if not proficiency:
            return None

        # Check if expired
        if proficiency.is_expired:
            proficiency.update_status()
            return None

        return proficiency.get_validity_info()

    @staticmethod
    def get_test_history(
        organization_id: UUID,
        user_id: UUID,
        language: str = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Get language test history for a user.

        Args:
            organization_id: Organization UUID
            user_id: User UUID
            language: Optional language filter
            limit: Maximum number of records

        Returns:
            List of test history records
        """
        query = LanguageTestHistory.objects.filter(
            organization_id=organization_id,
            user_id=user_id,
        )

        if language:
            query = query.filter(language=language)

        tests = query.order_by('-test_date')[:limit]

        return [
            {
                'id': str(t.id),
                'language': t.language,
                'language_name': t.get_language_display(),
                'test_date': t.test_date.isoformat(),
                'test_center': t.test_center,
                'examiner_name': t.examiner_name,
                'passed': t.passed,
                'overall_level': t.overall_level,
                'component_levels': {
                    'pronunciation': t.pronunciation_level,
                    'structure': t.structure_level,
                    'vocabulary': t.vocabulary_level,
                    'fluency': t.fluency_level,
                    'comprehension': t.comprehension_level,
                    'interaction': t.interaction_level,
                },
                'examiner_comments': t.examiner_comments,
                'areas_for_improvement': t.areas_for_improvement,
            }
            for t in tests
        ]

    # ==========================================================================
    # VALIDATION OPERATIONS
    # ==========================================================================

    @staticmethod
    def check_proficiency_validity(
        organization_id: UUID,
        user_id: UUID,
        language: str = 'en',
        min_level: int = 4,
    ) -> Dict[str, Any]:
        """
        Check if user has valid language proficiency.

        Args:
            organization_id: Organization UUID
            user_id: User UUID
            language: Required language
            min_level: Minimum required level (default 4 = Operational)

        Returns:
            Validity check result
        """
        proficiency = LanguageProficiency.objects.filter(
            organization_id=organization_id,
            user_id=user_id,
            language=language,
            status=LanguageProficiencyStatus.ACTIVE,
        ).order_by('-test_date').first()

        if not proficiency:
            return {
                'is_valid': False,
                'error_code': 'NO_PROFICIENCY',
                'message': f'No language proficiency record found for {language.upper()}',
                'proficiency': None,
            }

        if proficiency.is_expired:
            proficiency.update_status()
            return {
                'is_valid': False,
                'error_code': 'EXPIRED',
                'message': f'Language proficiency expired on {proficiency.expiry_date}',
                'proficiency': proficiency.get_validity_info(),
            }

        if proficiency.proficiency_level < min_level:
            return {
                'is_valid': False,
                'error_code': 'INSUFFICIENT_LEVEL',
                'message': f'Level {proficiency.proficiency_level} below required Level {min_level}',
                'proficiency': proficiency.get_validity_info(),
            }

        result = {
            'is_valid': True,
            'proficiency': proficiency.get_validity_info(),
        }

        # Add warning if expiring soon
        if proficiency.is_expiring_soon:
            result['warning'] = f'Language proficiency expires in {proficiency.days_until_expiry} days'

        return result

    # ==========================================================================
    # EXPIRY MANAGEMENT
    # ==========================================================================

    @staticmethod
    def get_expiring_proficiencies(
        organization_id: UUID = None,
        days_ahead: int = 180,
    ) -> List[Dict[str, Any]]:
        """
        Get proficiencies expiring within specified days.

        Args:
            organization_id: Optional organization filter
            days_ahead: Days to look ahead

        Returns:
            List of expiring proficiencies
        """
        today = date.today()
        threshold = today + timedelta(days=days_ahead)

        query = LanguageProficiency.objects.filter(
            status=LanguageProficiencyStatus.ACTIVE,
            expiry_date__isnull=False,
            expiry_date__gte=today,
            expiry_date__lte=threshold,
        )

        if organization_id:
            query = query.filter(organization_id=organization_id)

        return [
            {
                **p.get_validity_info(),
                'urgency': 'critical' if p.days_until_expiry <= 30 else
                          'warning' if p.days_until_expiry <= 90 else 'info',
            }
            for p in query.order_by('expiry_date')
        ]

    @staticmethod
    @transaction.atomic
    def update_expired_statuses() -> int:
        """
        Update status of expired proficiencies.

        Returns:
            Number of records updated
        """
        count = LanguageProficiency.objects.filter(
            status=LanguageProficiencyStatus.ACTIVE,
            expiry_date__lt=date.today(),
        ).update(status=LanguageProficiencyStatus.EXPIRED)

        if count > 0:
            logger.info(f"Updated {count} expired language proficiencies")

        return count

    # ==========================================================================
    # VERIFICATION
    # ==========================================================================

    @staticmethod
    @transaction.atomic
    def verify_proficiency(
        proficiency_id: UUID,
        verified_by: UUID,
        notes: str = None,
    ) -> Dict[str, Any]:
        """
        Verify a language proficiency record.

        Args:
            proficiency_id: Proficiency UUID
            verified_by: Verifying user UUID
            notes: Verification notes

        Returns:
            Updated proficiency information
        """
        proficiency = LanguageProficiency.objects.get(id=proficiency_id)
        proficiency.verified = True
        proficiency.verified_at = timezone.now()
        proficiency.verified_by = verified_by
        if notes:
            proficiency.notes = f"{proficiency.notes or ''}\nVerification: {notes}".strip()
        proficiency.save()

        logger.info(f"Language proficiency {proficiency_id} verified by {verified_by}")

        return proficiency.get_validity_info()

    # ==========================================================================
    # STATISTICS
    # ==========================================================================

    @staticmethod
    def get_organization_statistics(
        organization_id: UUID,
    ) -> Dict[str, Any]:
        """
        Get language proficiency statistics for organization.

        Args:
            organization_id: Organization UUID

        Returns:
            Statistics dictionary
        """
        from django.db.models import Count

        today = date.today()

        # Total active proficiencies
        total_active = LanguageProficiency.objects.filter(
            organization_id=organization_id,
            status=LanguageProficiencyStatus.ACTIVE,
        ).count()

        # By level
        by_level = LanguageProficiency.objects.filter(
            organization_id=organization_id,
            status=LanguageProficiencyStatus.ACTIVE,
        ).values('proficiency_level').annotate(count=Count('id'))

        # Expiring soon (next 180 days)
        expiring = LanguageProficiency.objects.filter(
            organization_id=organization_id,
            status=LanguageProficiencyStatus.ACTIVE,
            expiry_date__gte=today,
            expiry_date__lte=today + timedelta(days=180),
        ).count()

        # Non-operational (below Level 4)
        non_operational = LanguageProficiency.objects.filter(
            organization_id=organization_id,
            status=LanguageProficiencyStatus.ACTIVE,
            proficiency_level__lt=4,
        ).count()

        # English proficiency specifically
        english_valid = LanguageProficiency.objects.filter(
            organization_id=organization_id,
            language=LanguageCode.ENGLISH,
            status=LanguageProficiencyStatus.ACTIVE,
            proficiency_level__gte=4,
        ).count()

        return {
            'total_active': total_active,
            'by_level': {item['proficiency_level']: item['count'] for item in by_level},
            'expiring_180_days': expiring,
            'non_operational': non_operational,
            'english_operational': english_valid,
        }
