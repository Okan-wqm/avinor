# services/certificate-service/src/apps/core/services/validity_service.py
"""
Validity Service

Comprehensive pilot validity checking service.
"""

import logging
from datetime import date, timedelta
from typing import List, Dict, Any, Optional
from uuid import UUID

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
)
from .currency_service import CurrencyService

logger = logging.getLogger(__name__)


class ValidityService:
    """
    Service for comprehensive pilot validity checking.

    Validates all requirements for pilot to conduct operations.
    """

    @staticmethod
    def check_pilot_validity(
        organization_id: str,
        user_id: str,
        operation_type: Optional[str] = None,
        aircraft_icao: Optional[str] = None,
        night_operation: bool = False,
        ifr_operation: bool = False,
        passenger_carrying: bool = False
    ) -> Dict[str, Any]:
        """
        Comprehensive check of pilot validity for operations.

        Args:
            organization_id: Organization ID
            user_id: Pilot user ID
            operation_type: Type of operation
            aircraft_icao: Aircraft type if applicable
            night_operation: Whether night operation
            ifr_operation: Whether IFR operation
            passenger_carrying: Whether carrying passengers

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
            'issues': issues,
            'warnings': warnings,
            'certificates': certificates,
            'ratings': ratings_info,
            'currency': currency_check.get('statuses', []),
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
