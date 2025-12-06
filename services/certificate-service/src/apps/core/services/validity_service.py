# services/certificate-service/src/apps/core/services/validity_service.py
"""
Validity Service

Comprehensive pilot validity checking service.
Includes pilot age limits per EASA FCL.065 and FAA Part 121.
"""

import logging
from datetime import date, timedelta
from typing import List, Dict, Any, Optional
from uuid import UUID
from dateutil.relativedelta import relativedelta

from django.db.models import Q
from django.utils import timezone

from ..models import (
    Certificate,
    CertificateType,
    CertificateStatus,
    MedicalCertificate,
    MedicalStatus,
    MedicalClass,
    Rating,
    RatingStatus,
    Endorsement,
    EndorsementStatus,
    UserCurrencyStatus,
    LanguageProficiency,
    LanguageProficiencyStatus,
    ProficiencyLevel,
    FlightReview,
    FlightReviewStatus,
)
from .currency_service import CurrencyService

logger = logging.getLogger(__name__)


# =============================================================================
# Pilot Age Limit Constants (EASA FCL.065 / FAA Part 121)
# =============================================================================
class AgeLimit:
    """
    Pilot age limit constants per regulatory requirements.

    EASA FCL.065:
    - Under 60: Single-pilot commercial operations allowed
    - 60-64: Multi-pilot only with younger co-pilot
    - 65: Maximum age for commercial operations

    FAA Part 121:
    - 65: Mandatory retirement age for Part 121 (airline) operations
    - No age limit for Part 91 (private) or Part 135 (charter)
    """

    # EASA Age Limits
    EASA_SINGLE_PILOT_MAX = 60  # Single-pilot commercial
    EASA_MULTI_PILOT_MAX = 65   # Multi-pilot commercial
    EASA_HARD_LIMIT = 65        # No commercial flying after 65

    # FAA Age Limits
    FAA_PART_121_MAX = 65       # Part 121 airline operations
    FAA_PART_135_MAX = None     # No limit for Part 135
    FAA_PART_91_MAX = None      # No limit for Part 91

    # Instructor Age (varies by authority)
    INSTRUCTOR_RECOMMENDED_MAX = 70  # Advisory only

    # Medical considerations by age
    MEDICAL_ENHANCED_REVIEW_AGE = 40  # More frequent medicals
    MEDICAL_ANNUAL_REQUIRED_AGE = 60  # Annual medical required


class ValidityService:
    """
    Service for comprehensive pilot validity checking.

    Validates all requirements for pilot to conduct operations.
    Includes age limits, language proficiency, BFR, and FTL checks.
    """

    # =========================================================================
    # Pilot Age Limit Methods
    # =========================================================================

    @staticmethod
    def calculate_age(birth_date: date, reference_date: date = None) -> int:
        """
        Calculate pilot age.

        Args:
            birth_date: Pilot's date of birth
            reference_date: Date to calculate age at (default: today)

        Returns:
            Age in years
        """
        if reference_date is None:
            reference_date = date.today()

        age = relativedelta(reference_date, birth_date)
        return age.years

    @staticmethod
    def check_age_limits(
        birth_date: date,
        operation_type: str = 'private',
        regulatory_authority: str = 'EASA',
        is_multi_pilot: bool = False,
        co_pilot_age: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Check pilot age against regulatory limits.

        Args:
            birth_date: Pilot's date of birth
            operation_type: Type of operation (private, commercial, airline)
            regulatory_authority: EASA or FAA
            is_multi_pilot: Whether multi-pilot operation
            co_pilot_age: Age of co-pilot if applicable

        Returns:
            Age limit check result dict
        """
        issues = []
        warnings = []
        age = ValidityService.calculate_age(birth_date)

        result = {
            'pilot_age': age,
            'birth_date': birth_date.isoformat(),
            'operation_type': operation_type,
            'regulatory_authority': regulatory_authority,
            'is_compliant': True,
            'issues': [],
            'warnings': [],
            'restrictions': []
        }

        if regulatory_authority.upper() == 'EASA':
            # EASA FCL.065 Age Limits
            if operation_type in ['commercial', 'airline']:
                if age >= AgeLimit.EASA_HARD_LIMIT:
                    issues.append({
                        'type': 'age_limit',
                        'code': 'EASA_AGE_EXCEEDED',
                        'message': f'Pilot age {age} exceeds EASA maximum of {AgeLimit.EASA_HARD_LIMIT} for commercial operations',
                        'severity': 'error'
                    })
                    result['is_compliant'] = False

                elif age >= AgeLimit.EASA_SINGLE_PILOT_MAX:
                    # 60-64: Multi-pilot only with age restriction
                    result['restrictions'].append({
                        'code': 'MULTI_PILOT_ONLY',
                        'description': 'Single-pilot commercial operations not permitted for pilots aged 60+'
                    })

                    if not is_multi_pilot:
                        issues.append({
                            'type': 'age_limit',
                            'code': 'SINGLE_PILOT_AGE_EXCEEDED',
                            'message': f'Pilot age {age} exceeds EASA limit of {AgeLimit.EASA_SINGLE_PILOT_MAX} for single-pilot commercial',
                            'severity': 'error'
                        })
                        result['is_compliant'] = False

                    # Check OML requirement (Other pilot must be under 60)
                    if is_multi_pilot and co_pilot_age and co_pilot_age >= AgeLimit.EASA_SINGLE_PILOT_MAX:
                        issues.append({
                            'type': 'age_limit',
                            'code': 'OML_VIOLATION',
                            'message': f'Both pilots are 60+. One pilot must be under {AgeLimit.EASA_SINGLE_PILOT_MAX} per EASA OML',
                            'severity': 'error'
                        })
                        result['is_compliant'] = False

                # Warnings for approaching limits
                if 58 <= age < 60:
                    warnings.append({
                        'type': 'age_limit',
                        'code': 'APPROACHING_SINGLE_PILOT_LIMIT',
                        'message': f'Pilot will reach single-pilot commercial limit in {60 - age} years',
                        'severity': 'warning'
                    })
                elif 63 <= age < 65:
                    warnings.append({
                        'type': 'age_limit',
                        'code': 'APPROACHING_MAX_AGE',
                        'message': f'Pilot will reach maximum commercial age in {65 - age} years',
                        'severity': 'warning'
                    })

        elif regulatory_authority.upper() == 'FAA':
            # FAA Age Limits
            if operation_type == 'airline':
                # Part 121 operations
                if age >= AgeLimit.FAA_PART_121_MAX:
                    issues.append({
                        'type': 'age_limit',
                        'code': 'FAA_121_AGE_EXCEEDED',
                        'message': f'Pilot age {age} exceeds FAA Part 121 limit of {AgeLimit.FAA_PART_121_MAX}',
                        'severity': 'error'
                    })
                    result['is_compliant'] = False

                elif 63 <= age < 65:
                    warnings.append({
                        'type': 'age_limit',
                        'code': 'APPROACHING_121_LIMIT',
                        'message': f'Pilot will reach Part 121 retirement age in {65 - age} years',
                        'severity': 'warning'
                    })

            # No age limits for Part 91 (private) or Part 135 (charter)

        # Medical frequency warnings based on age
        if age >= AgeLimit.MEDICAL_ANNUAL_REQUIRED_AGE:
            result['restrictions'].append({
                'code': 'ANNUAL_MEDICAL_REQUIRED',
                'description': f'Annual medical examination required for pilots over {AgeLimit.MEDICAL_ANNUAL_REQUIRED_AGE}'
            })

        result['issues'] = issues
        result['warnings'] = warnings

        return result

    @staticmethod
    def check_language_proficiency(
        organization_id: str,
        user_id: str,
        required_language: str = 'en'
    ) -> Dict[str, Any]:
        """
        Check pilot's ICAO language proficiency.

        Args:
            organization_id: Organization ID
            user_id: User ID
            required_language: Required language code (default: English)

        Returns:
            Language proficiency check result
        """
        issues = []
        warnings = []

        proficiency = LanguageProficiency.objects.filter(
            organization_id=organization_id,
            user_id=user_id,
            language=required_language.lower(),
            status=LanguageProficiencyStatus.ACTIVE
        ).order_by('-expiry_date').first()

        if not proficiency:
            issues.append({
                'type': 'language_proficiency',
                'code': 'NO_PROFICIENCY',
                'message': f'No valid language proficiency found for {required_language.upper()}',
                'severity': 'error'
            })
            return {
                'is_valid': False,
                'proficiency': None,
                'issues': issues,
                'warnings': warnings
            }

        # Check if expired
        if proficiency.is_expired:
            issues.append({
                'type': 'language_proficiency',
                'code': 'PROFICIENCY_EXPIRED',
                'message': f'Language proficiency expired on {proficiency.expiry_date}',
                'severity': 'error'
            })
            return {
                'is_valid': False,
                'proficiency': proficiency.get_validity_info(),
                'issues': issues,
                'warnings': warnings
            }

        # Check minimum level (Level 4 - Operational)
        if proficiency.overall_level < ProficiencyLevel.OPERATIONAL:
            issues.append({
                'type': 'language_proficiency',
                'code': 'INSUFFICIENT_LEVEL',
                'message': f'Language proficiency level {proficiency.overall_level} below minimum operational (4)',
                'severity': 'error'
            })

        # Warning for expiring soon
        if proficiency.is_expiring_soon:
            warnings.append({
                'type': 'language_proficiency',
                'code': 'EXPIRING_SOON',
                'message': f'Language proficiency expires in {proficiency.days_until_expiry} days',
                'days_remaining': proficiency.days_until_expiry,
                'severity': 'warning'
            })

        return {
            'is_valid': len([i for i in issues if i['severity'] == 'error']) == 0,
            'proficiency': proficiency.get_validity_info(),
            'level': proficiency.overall_level,
            'issues': issues,
            'warnings': warnings
        }

    @staticmethod
    def check_flight_review(
        organization_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Check pilot's flight review (BFR) status.

        Args:
            organization_id: Organization ID
            user_id: User ID

        Returns:
            Flight review check result
        """
        issues = []
        warnings = []

        # Get most recent completed flight review
        review = FlightReview.objects.filter(
            organization_id=organization_id,
            user_id=user_id,
            status=FlightReviewStatus.COMPLETED
        ).order_by('-expiry_date').first()

        if not review:
            issues.append({
                'type': 'flight_review',
                'code': 'NO_FLIGHT_REVIEW',
                'message': 'No valid flight review (BFR) found',
                'severity': 'error'
            })
            return {
                'is_valid': False,
                'review': None,
                'issues': issues,
                'warnings': warnings
            }

        # Check if expired
        if review.is_expired:
            issues.append({
                'type': 'flight_review',
                'code': 'REVIEW_EXPIRED',
                'message': f'Flight review expired on {review.expiry_date}',
                'severity': 'error'
            })

        # Warning for expiring soon (within 90 days)
        if review.is_expiring_soon:
            warnings.append({
                'type': 'flight_review',
                'code': 'EXPIRING_SOON',
                'message': f'Flight review expires in {review.days_until_expiry} days',
                'days_remaining': review.days_until_expiry,
                'severity': 'warning'
            })

        return {
            'is_valid': len([i for i in issues if i['severity'] == 'error']) == 0,
            'review': {
                'id': str(review.id),
                'review_type': review.review_type,
                'review_date': review.review_date.isoformat(),
                'expiry_date': review.expiry_date.isoformat() if review.expiry_date else None,
                'days_remaining': review.days_until_expiry,
            },
            'issues': issues,
            'warnings': warnings
        }

    @staticmethod
    def check_pilot_validity(
        organization_id: str,
        user_id: str,
        operation_type: Optional[str] = None,
        aircraft_icao: Optional[str] = None,
        night_operation: bool = False,
        ifr_operation: bool = False,
        passenger_carrying: bool = False,
        birth_date: Optional[date] = None,
        regulatory_authority: str = 'EASA',
        is_multi_pilot: bool = False,
        co_pilot_age: Optional[int] = None,
        international_flight: bool = False
    ) -> Dict[str, Any]:
        """
        Comprehensive check of pilot validity for operations.

        Args:
            organization_id: Organization ID
            user_id: Pilot user ID
            operation_type: Type of operation (private, commercial, airline)
            aircraft_icao: Aircraft type if applicable
            night_operation: Whether night operation
            ifr_operation: Whether IFR operation
            passenger_carrying: Whether carrying passengers
            birth_date: Pilot date of birth for age limit checks
            regulatory_authority: EASA or FAA
            is_multi_pilot: Whether multi-pilot operation
            co_pilot_age: Age of co-pilot if applicable
            international_flight: Whether international operation

        Returns:
            Comprehensive validity status dict
        """
        issues = []
        warnings = []
        certificates = {}
        ratings_info = {}

        # 1. Check Pilot License
        pilot_license = Certificate.objects.filter(
            organization_id=organization_id,
            user_id=user_id,
            certificate_type=CertificateType.PILOT_LICENSE,
            status=CertificateStatus.ACTIVE,
            verified=True
        ).exclude(expiry_date__lt=date.today()).first()

        if not pilot_license:
            issues.append({
                'type': 'pilot_license',
                'code': 'NO_LICENSE',
                'message': 'No valid pilot license found',
                'severity': 'error'
            })
        else:
            certificates['pilot_license'] = pilot_license.get_validity_info()

            if pilot_license.is_expiring_soon:
                days = pilot_license.days_until_expiry
                warnings.append({
                    'type': 'pilot_license',
                    'code': 'EXPIRING_SOON',
                    'message': f'Pilot license expires in {days} days',
                    'days_remaining': days,
                    'severity': 'warning'
                })

        # 2. Check Medical Certificate
        medical = MedicalCertificate.objects.filter(
            organization_id=organization_id,
            user_id=user_id,
            status=MedicalStatus.ACTIVE,
            expiry_date__gte=date.today()
        ).order_by('-expiry_date').first()

        if not medical:
            issues.append({
                'type': 'medical',
                'code': 'NO_MEDICAL',
                'message': 'No valid medical certificate found',
                'severity': 'error'
            })
        else:
            certificates['medical'] = medical.get_validity_info()

            # Check medical class for operation type
            if operation_type == 'commercial' and medical.medical_class not in [
                MedicalClass.CLASS_1
            ]:
                issues.append({
                    'type': 'medical',
                    'code': 'INSUFFICIENT_CLASS',
                    'message': f'Class 1 medical required for commercial operations',
                    'severity': 'error'
                })

            if medical.is_expiring_soon:
                days = medical.days_until_expiry
                warnings.append({
                    'type': 'medical',
                    'code': 'EXPIRING_SOON',
                    'message': f'Medical certificate expires in {days} days',
                    'days_remaining': days,
                    'severity': 'warning'
                })

        # 3. Check Type Rating (if aircraft specified)
        if aircraft_icao:
            type_rating = Rating.objects.filter(
                organization_id=organization_id,
                user_id=user_id,
                aircraft_icao=aircraft_icao,
                status=RatingStatus.ACTIVE
            ).exclude(expiry_date__lt=date.today()).first()

            # Some aircraft don't require type rating (SEP, etc.)
            # This is a simplified check
            if type_rating:
                ratings_info['type_rating'] = type_rating.get_validity_info()

                if type_rating.is_proficiency_due:
                    issues.append({
                        'type': 'rating',
                        'code': 'PROFICIENCY_DUE',
                        'message': f'Proficiency check overdue for {aircraft_icao}',
                        'severity': 'error'
                    })

        # 4. Check Night Rating (if night operation)
        if night_operation:
            night_rating = Rating.objects.filter(
                organization_id=organization_id,
                user_id=user_id,
                rating_type='night',
                status=RatingStatus.ACTIVE
            ).first()

            if not night_rating:
                issues.append({
                    'type': 'rating',
                    'code': 'NO_NIGHT_RATING',
                    'message': 'Night rating required for night operations',
                    'severity': 'error'
                })
            else:
                ratings_info['night'] = night_rating.get_validity_info()

        # 5. Check Instrument Rating (if IFR)
        if ifr_operation:
            ir_rating = Rating.objects.filter(
                organization_id=organization_id,
                user_id=user_id,
                rating_type__in=['instrument', 'instrument_eir'],
                status=RatingStatus.ACTIVE
            ).exclude(expiry_date__lt=date.today()).first()

            if not ir_rating:
                issues.append({
                    'type': 'rating',
                    'code': 'NO_IR',
                    'message': 'Instrument rating required for IFR operations',
                    'severity': 'error'
                })
            else:
                ratings_info['instrument'] = ir_rating.get_validity_info()

        # 6. Check Currency
        currency_check = CurrencyService.check_currency(
            organization_id=organization_id,
            user_id=user_id,
            operation_type='passenger' if passenger_carrying else None
        )

        for issue in currency_check.get('issues', []):
            issues.append(issue)

        for warning in currency_check.get('warnings', []):
            warnings.append(warning)

        # Check specific currency requirements
        if passenger_carrying:
            # Day currency check
            day_currency = UserCurrencyStatus.objects.filter(
                organization_id=organization_id,
                user_id=user_id,
                requirement__code='DAY_VFR',
                is_current=True
            ).first()

            if not day_currency:
                issues.append({
                    'type': 'currency',
                    'code': 'NO_DAY_CURRENCY',
                    'message': 'Day VFR currency required for passenger carrying',
                    'severity': 'error'
                })

            # Night currency check if night operation
            if night_operation:
                night_currency = UserCurrencyStatus.objects.filter(
                    organization_id=organization_id,
                    user_id=user_id,
                    requirement__code='NIGHT_VFR',
                    is_current=True
                ).first()

                if not night_currency:
                    issues.append({
                        'type': 'currency',
                        'code': 'NO_NIGHT_CURRENCY',
                        'message': 'Night currency required for night passenger flights',
                        'severity': 'error'
                    })

        # IFR currency check
        if ifr_operation:
            ifr_currency = UserCurrencyStatus.objects.filter(
                organization_id=organization_id,
                user_id=user_id,
                requirement__code='IFR',
                is_current=True
            ).first()

            if not ifr_currency:
                issues.append({
                    'type': 'currency',
                    'code': 'NO_IFR_CURRENCY',
                    'message': 'IFR currency required for IFR operations',
                    'severity': 'error'
                })

        # 7. Check Pilot Age Limits (if birth date provided)
        age_info = None
        if birth_date:
            age_check = ValidityService.check_age_limits(
                birth_date=birth_date,
                operation_type=operation_type or 'private',
                regulatory_authority=regulatory_authority,
                is_multi_pilot=is_multi_pilot,
                co_pilot_age=co_pilot_age
            )
            age_info = age_check

            for issue in age_check.get('issues', []):
                issues.append(issue)
            for warning in age_check.get('warnings', []):
                warnings.append(warning)

        # 8. Check Flight Review (BFR)
        bfr_check = ValidityService.check_flight_review(
            organization_id=organization_id,
            user_id=user_id
        )

        if not bfr_check['is_valid']:
            for issue in bfr_check.get('issues', []):
                issues.append(issue)
        for warning in bfr_check.get('warnings', []):
            warnings.append(warning)

        # 9. Check Language Proficiency (for international or IFR)
        language_info = None
        if international_flight or ifr_operation:
            lang_check = ValidityService.check_language_proficiency(
                organization_id=organization_id,
                user_id=user_id,
                required_language='en'
            )
            language_info = lang_check

            if not lang_check['is_valid']:
                for issue in lang_check.get('issues', []):
                    issues.append(issue)
            for warning in lang_check.get('warnings', []):
                warnings.append(warning)

        # Calculate overall validity
        has_errors = len([i for i in issues if i.get('severity') == 'error']) > 0
        is_valid = not has_errors

        return {
            'user_id': user_id,
            'is_valid': is_valid,
            'can_fly': is_valid,
            'operation_type': operation_type,
            'aircraft_icao': aircraft_icao,
            'night_operation': night_operation,
            'ifr_operation': ifr_operation,
            'passenger_carrying': passenger_carrying,
            'international_flight': international_flight,
            'regulatory_authority': regulatory_authority,
            'is_multi_pilot': is_multi_pilot,
            'issues': issues,
            'warnings': warnings,
            'certificates': certificates,
            'ratings': ratings_info,
            'currency': currency_check.get('statuses', []),
            'age_check': age_info,
            'flight_review': bfr_check.get('review'),
            'language_proficiency': language_info,
            'checked_at': timezone.now().isoformat()
        }

    @staticmethod
    def get_user_summary(
        organization_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Get comprehensive summary of user's certificates and validity.

        Args:
            organization_id: Organization ID
            user_id: User ID

        Returns:
            Summary dict with all certificates, ratings, and status
        """
        # Certificates
        certificates = Certificate.objects.filter(
            organization_id=organization_id,
            user_id=user_id
        ).order_by('certificate_type', '-issue_date')

        # Medicals
        medicals = MedicalCertificate.objects.filter(
            organization_id=organization_id,
            user_id=user_id
        ).order_by('-expiry_date')

        # Ratings
        ratings = Rating.objects.filter(
            organization_id=organization_id,
            user_id=user_id
        ).order_by('rating_type')

        # Endorsements
        endorsements = Endorsement.objects.filter(
            organization_id=organization_id,
            student_id=user_id,
            status=EndorsementStatus.ACTIVE
        ).order_by('-issue_date')

        # Currency
        currency_statuses = CurrencyService.get_user_currency_status(
            organization_id=organization_id,
            user_id=user_id
        )

        # Calculate overall status
        validity_check = ValidityService.check_pilot_validity(
            organization_id=organization_id,
            user_id=user_id,
            passenger_carrying=True
        )

        # Find expiring items
        expiring_soon = []
        today = date.today()
        threshold = today + timedelta(days=90)

        for cert in certificates:
            if cert.expiry_date and today <= cert.expiry_date <= threshold:
                expiring_soon.append({
                    'type': 'certificate',
                    'subtype': cert.certificate_type,
                    'name': cert.get_certificate_type_display(),
                    'expiry_date': cert.expiry_date.isoformat(),
                    'days_remaining': cert.days_until_expiry
                })

        for med in medicals:
            if med.status == MedicalStatus.ACTIVE and today <= med.expiry_date <= threshold:
                expiring_soon.append({
                    'type': 'medical',
                    'subtype': med.medical_class,
                    'name': med.get_medical_class_display(),
                    'expiry_date': med.expiry_date.isoformat(),
                    'days_remaining': med.days_until_expiry
                })

        for rating in ratings:
            if rating.expiry_date and today <= rating.expiry_date <= threshold:
                expiring_soon.append({
                    'type': 'rating',
                    'subtype': rating.rating_type,
                    'name': rating.rating_name,
                    'expiry_date': rating.expiry_date.isoformat(),
                    'days_remaining': rating.days_until_expiry
                })

        return {
            'user_id': user_id,
            'is_valid': validity_check['is_valid'],
            'can_fly_passengers': validity_check['is_valid'],
            'summary': {
                'certificates_count': certificates.count(),
                'active_certificates': certificates.filter(
                    status=CertificateStatus.ACTIVE
                ).count(),
                'ratings_count': ratings.count(),
                'active_ratings': ratings.filter(status=RatingStatus.ACTIVE).count(),
                'endorsements_count': endorsements.count(),
            },
            'certificates': [c.get_validity_info() for c in certificates],
            'medical': medicals.first().get_validity_info() if medicals.exists() else None,
            'medical_history': [m.get_validity_info() for m in medicals],
            'ratings': [r.get_validity_info() for r in ratings],
            'endorsements': [e.get_validity_info() for e in endorsements],
            'currency': currency_statuses,
            'expiring_soon': sorted(
                expiring_soon,
                key=lambda x: x.get('days_remaining', 999)
            ),
            'issues': validity_check['issues'],
            'warnings': validity_check['warnings'],
            'checked_at': timezone.now().isoformat()
        }

    @staticmethod
    def check_instructor_validity(
        organization_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Check if user is valid to act as instructor.

        Args:
            organization_id: Organization ID
            user_id: User ID

        Returns:
            Instructor validity dict
        """
        issues = []
        warnings = []

        # Check instructor certificate
        instructor_cert = Certificate.objects.filter(
            organization_id=organization_id,
            user_id=user_id,
            certificate_type=CertificateType.INSTRUCTOR_CERTIFICATE,
            status=CertificateStatus.ACTIVE,
            verified=True
        ).exclude(expiry_date__lt=date.today()).first()

        if not instructor_cert:
            issues.append({
                'type': 'instructor_certificate',
                'code': 'NO_CFI',
                'message': 'No valid instructor certificate found',
                'severity': 'error'
            })
            return {
                'user_id': user_id,
                'is_valid_instructor': False,
                'issues': issues,
                'warnings': warnings,
            }

        if instructor_cert.is_expiring_soon:
            warnings.append({
                'type': 'instructor_certificate',
                'code': 'EXPIRING_SOON',
                'message': f'Instructor certificate expires in {instructor_cert.days_until_expiry} days',
                'severity': 'warning'
            })

        # Check basic pilot validity
        pilot_validity = ValidityService.check_pilot_validity(
            organization_id=organization_id,
            user_id=user_id
        )

        # Instructor must also be valid as pilot
        if not pilot_validity['is_valid']:
            issues.extend(pilot_validity['issues'])
            warnings.extend(pilot_validity['warnings'])

        # Get instructor ratings
        instructor_ratings = Rating.objects.filter(
            organization_id=organization_id,
            user_id=user_id,
            rating_type='instructor',
            status=RatingStatus.ACTIVE
        )

        has_errors = len([i for i in issues if i.get('severity') == 'error']) > 0

        return {
            'user_id': user_id,
            'is_valid_instructor': not has_errors,
            'instructor_certificate': instructor_cert.get_validity_info(),
            'instructor_ratings': [r.get_validity_info() for r in instructor_ratings],
            'pilot_validity': pilot_validity,
            'issues': issues,
            'warnings': warnings,
            'checked_at': timezone.now().isoformat()
        }

    @staticmethod
    def get_validity_statistics(
        organization_id: str
    ) -> Dict[str, Any]:
        """
        Get validity statistics for organization.

        Args:
            organization_id: Organization ID

        Returns:
            Statistics dict
        """
        # Count pilots with valid status
        users_with_certificates = Certificate.objects.filter(
            organization_id=organization_id
        ).values('user_id').distinct()

        total_pilots = users_with_certificates.count()

        # Valid pilots (have active license and medical)
        valid_count = 0
        for user in users_with_certificates:
            validity = ValidityService.check_pilot_validity(
                organization_id=organization_id,
                user_id=str(user['user_id'])
            )
            if validity['is_valid']:
                valid_count += 1

        # Expiring items
        today = date.today()
        threshold_30 = today + timedelta(days=30)
        threshold_90 = today + timedelta(days=90)

        expiring_30_certs = Certificate.objects.filter(
            organization_id=organization_id,
            status=CertificateStatus.ACTIVE,
            expiry_date__gte=today,
            expiry_date__lte=threshold_30
        ).count()

        expiring_90_certs = Certificate.objects.filter(
            organization_id=organization_id,
            status=CertificateStatus.ACTIVE,
            expiry_date__gte=today,
            expiry_date__lte=threshold_90
        ).count()

        expiring_30_medical = MedicalCertificate.objects.filter(
            organization_id=organization_id,
            status=MedicalStatus.ACTIVE,
            expiry_date__gte=today,
            expiry_date__lte=threshold_30
        ).count()

        return {
            'total_pilots': total_pilots,
            'valid_pilots': valid_count,
            'validity_rate': (valid_count / total_pilots * 100) if total_pilots > 0 else 0,
            'certificates_expiring_30_days': expiring_30_certs,
            'certificates_expiring_90_days': expiring_90_certs,
            'medicals_expiring_30_days': expiring_30_medical,
        }
