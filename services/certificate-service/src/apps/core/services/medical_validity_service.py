# services/certificate-service/src/apps/core/services/medical_validity_service.py
"""
Medical Validity Service

EASA Part-MED Medical Certificate Validity Calculations.
Comprehensive age-based validity and renewal tracking.
"""

import logging
from datetime import date, timedelta
from decimal import Decimal
from typing import List, Dict, Any, Optional, Tuple
from uuid import UUID
from dateutil.relativedelta import relativedelta
import calendar

from django.db import transaction
from django.db.models import Q

from ..models import (
    MedicalCertificate,
    MedicalClass,
    MedicalStatus,
)

logger = logging.getLogger(__name__)


# =============================================================================
# EASA Part-MED Validity Rules
# =============================================================================
class EASAMedicalRules:
    """
    EASA Part-MED Medical Certificate Validity Rules.

    MED.A.045 - Validity, revalidation and renewal of medical certificates

    Class 1:
    - < 40 years: 12 months
    - 40-59 years: 6 months (12 months if engaged only in single pilot
                             commercial operations not carrying passengers)
    - >= 60 years: 6 months

    Class 2:
    - < 40 years: 60 months (until 42nd birthday)
    - 40-49 years: 24 months (until 51st birthday)
    - >= 50 years: 12 months

    LAPL Medical:
    - < 40 years: 60 months (until 42nd birthday)
    - >= 40 years: 24 months
    """

    @staticmethod
    def get_class1_validity(age: int, single_pilot_no_pax: bool = False) -> int:
        """
        Get Class 1 validity period in months.

        Args:
            age: Pilot's age at examination
            single_pilot_no_pax: If engaged only in SP ops not carrying passengers

        Returns:
            Validity period in months
        """
        if age < 40:
            return 12
        elif age < 60:
            # 12 months if single pilot non-pax commercial only
            return 12 if single_pilot_no_pax else 6
        else:
            return 6

    @staticmethod
    def get_class2_validity(age: int) -> int:
        """Get Class 2 validity period in months."""
        if age < 40:
            return 60
        elif age < 50:
            return 24
        else:
            return 12

    @staticmethod
    def get_lapl_validity(age: int) -> int:
        """Get LAPL medical validity period in months."""
        if age < 40:
            return 60
        else:
            return 24

    @staticmethod
    def get_class3_validity(age: int) -> int:
        """Get Class 3 (ATC) validity period in months."""
        if age < 40:
            return 24
        else:
            return 12


class FAAMedicalRules:
    """
    FAA Medical Certificate Validity Rules (14 CFR 61.23).

    First Class:
    - < 40 years: 12 months
    - >= 40 years: 6 months

    Second Class:
    - All ages: 12 months

    Third Class:
    - < 40 years: 60 months
    - >= 40 years: 24 months

    BasicMed:
    - 48 months (with conditions)
    """

    @staticmethod
    def get_first_class_validity(age: int) -> int:
        """Get First Class validity in months."""
        return 12 if age < 40 else 6

    @staticmethod
    def get_second_class_validity(age: int) -> int:
        """Get Second Class validity in months."""
        return 12

    @staticmethod
    def get_third_class_validity(age: int) -> int:
        """Get Third Class validity in months."""
        return 60 if age < 40 else 24

    @staticmethod
    def get_basicmed_validity() -> int:
        """Get BasicMed validity in months."""
        return 48


class MedicalValidityService:
    """
    Service for medical certificate validity calculations and management.

    Handles:
    - Age-based validity calculation
    - Expiry date calculation
    - Renewal tracking
    - Downgrade rules
    - Validity status checks
    """

    # ==========================================================================
    # Validity Calculation
    # ==========================================================================

    @staticmethod
    def calculate_validity_period(
        medical_class: str,
        age: int,
        authority: str = 'EASA',
        special_conditions: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Calculate medical validity period in months.

        Args:
            medical_class: Medical class (class_1, class_2, lapl, etc.)
            age: Pilot's age at examination
            authority: Issuing authority (EASA, FAA, SHGM, etc.)
            special_conditions: Additional conditions affecting validity

        Returns:
            Validity period in months
        """
        authority_upper = authority.upper()
        conditions = special_conditions or {}

        if authority_upper in ['EASA', 'SHGM', 'LBA', 'CAA', 'ENAC', 'DGAC']:
            # EASA rules
            if medical_class == MedicalClass.CLASS_1:
                single_pilot_no_pax = conditions.get('single_pilot_no_pax', False)
                return EASAMedicalRules.get_class1_validity(age, single_pilot_no_pax)
            elif medical_class == MedicalClass.CLASS_2:
                return EASAMedicalRules.get_class2_validity(age)
            elif medical_class == MedicalClass.LAPL:
                return EASAMedicalRules.get_lapl_validity(age)
            elif medical_class == MedicalClass.CLASS_3:
                return EASAMedicalRules.get_class3_validity(age)

        elif authority_upper == 'FAA':
            # FAA rules
            if medical_class == MedicalClass.CLASS_1:
                return FAAMedicalRules.get_first_class_validity(age)
            elif medical_class == MedicalClass.CLASS_2:
                return FAAMedicalRules.get_second_class_validity(age)
            elif medical_class == MedicalClass.CLASS_3:
                return FAAMedicalRules.get_third_class_validity(age)
            elif medical_class == MedicalClass.BASICMED:
                return FAAMedicalRules.get_basicmed_validity()

        # Default to 12 months
        return 12

    @staticmethod
    def calculate_expiry_date(
        issue_date: date,
        validity_months: int,
        end_of_month: bool = True
    ) -> date:
        """
        Calculate medical certificate expiry date.

        EASA MED.A.045(c): Validity period ends at the end of the month.

        Args:
            issue_date: Date of issue
            validity_months: Validity period in months
            end_of_month: Whether expiry is at end of month (EASA rule)

        Returns:
            Expiry date
        """
        # Add validity period
        expiry = issue_date + relativedelta(months=validity_months)

        if end_of_month:
            # EASA: Validity ends at end of month
            _, last_day = calendar.monthrange(expiry.year, expiry.month)
            return date(expiry.year, expiry.month, last_day)
        else:
            # FAA: Calendar months from date of examination
            return expiry

    @staticmethod
    def calculate_age_at_date(birth_date: date, target_date: date) -> int:
        """Calculate age at a specific date."""
        age = target_date.year - birth_date.year
        if (target_date.month, target_date.day) < (birth_date.month, birth_date.day):
            age -= 1
        return age

    # ==========================================================================
    # Medical Certificate Management
    # ==========================================================================

    @staticmethod
    @transaction.atomic
    def create_medical_with_auto_validity(
        organization_id: str,
        user_id: str,
        medical_class: str,
        examination_date: date,
        pilot_birth_date: date,
        issuing_authority: str,
        ame_name: Optional[str] = None,
        ame_license_number: Optional[str] = None,
        certificate_number: Optional[str] = None,
        limitations: Optional[List[str]] = None,
        limitation_codes: Optional[List[str]] = None,
        special_conditions: Optional[Dict[str, Any]] = None,
        created_by: Optional[str] = None
    ) -> MedicalCertificate:
        """
        Create medical certificate with auto-calculated validity.

        Args:
            organization_id: Organization ID
            user_id: Pilot user ID
            medical_class: Medical class
            examination_date: Date of examination
            pilot_birth_date: Pilot's birth date
            issuing_authority: Issuing authority
            ame_name: AME name
            ame_license_number: AME license number
            certificate_number: Certificate number
            limitations: Limitations text list
            limitation_codes: Standard limitation codes
            special_conditions: Conditions affecting validity
            created_by: User creating the record

        Returns:
            Created MedicalCertificate
        """
        # Calculate age at examination
        age = MedicalValidityService.calculate_age_at_date(
            pilot_birth_date, examination_date
        )

        # Get validity period
        validity_months = MedicalValidityService.calculate_validity_period(
            medical_class, age, issuing_authority, special_conditions
        )

        # Calculate expiry date
        # EASA/SHGM use end of month
        end_of_month = issuing_authority.upper() in [
            'EASA', 'SHGM', 'LBA', 'CAA', 'ENAC', 'DGAC', 'FOCA'
        ]
        expiry_date = MedicalValidityService.calculate_expiry_date(
            examination_date, validity_months, end_of_month
        )

        medical = MedicalCertificate.objects.create(
            organization_id=organization_id,
            user_id=user_id,
            medical_class=medical_class,
            examination_date=examination_date,
            issue_date=examination_date,
            expiry_date=expiry_date,
            pilot_birth_date=pilot_birth_date,
            pilot_age_at_exam=age,
            issuing_authority=issuing_authority,
            ame_name=ame_name,
            ame_license_number=ame_license_number,
            certificate_number=certificate_number,
            limitations=limitations or [],
            limitation_codes=limitation_codes or [],
            status=MedicalStatus.ACTIVE,
            metadata={
                'validity_months': validity_months,
                'end_of_month_rule': end_of_month,
                'special_conditions': special_conditions or {},
            },
            created_by=created_by,
        )

        logger.info(
            f"Created medical certificate {medical.id} with {validity_months} months validity",
            extra={
                'medical_id': str(medical.id),
                'user_id': user_id,
                'age': age,
                'validity_months': validity_months,
            }
        )

        return medical

    @staticmethod
    def get_medical_status(
        organization_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Get comprehensive medical status for a pilot.

        Args:
            organization_id: Organization ID
            user_id: User ID

        Returns:
            Medical status summary
        """
        medicals = MedicalCertificate.objects.filter(
            organization_id=organization_id,
            user_id=user_id
        ).order_by('-expiry_date')

        if not medicals.exists():
            return {
                'user_id': user_id,
                'has_medical': False,
                'message': 'No medical certificate on record',
            }

        # Get highest class valid medical
        valid_medicals = [m for m in medicals if m.is_valid]
        if not valid_medicals:
            expired = medicals.first()
            return {
                'user_id': user_id,
                'has_medical': True,
                'has_valid_medical': False,
                'highest_class': None,
                'last_medical': {
                    'id': str(expired.id),
                    'class': expired.medical_class,
                    'expired_date': expired.expiry_date.isoformat(),
                    'days_expired': abs(expired.days_until_expiry),
                },
                'message': f'Medical expired {abs(expired.days_until_expiry)} days ago',
            }

        # Class priority
        class_priority = {
            MedicalClass.CLASS_1: 1,
            MedicalClass.CLASS_2: 2,
            MedicalClass.CLASS_3: 3,
            MedicalClass.LAPL: 4,
            MedicalClass.BASICMED: 5,
        }

        highest = min(valid_medicals, key=lambda m: class_priority.get(m.medical_class, 99))

        # Check for expiring soon
        expiring_soon = [m for m in valid_medicals if m.is_expiring_soon]

        result = {
            'user_id': user_id,
            'has_medical': True,
            'has_valid_medical': True,
            'highest_class': highest.medical_class,
            'current_medical': highest.get_validity_info(),
            'all_valid_medicals': [m.get_validity_info() for m in valid_medicals],
            'message': 'Valid medical certificate on record',
        }

        if expiring_soon:
            soonest = min(expiring_soon, key=lambda m: m.days_until_expiry)
            result['expiring_soon'] = True
            result['expiring_warning'] = (
                f'{soonest.get_medical_class_display()} expires in '
                f'{soonest.days_until_expiry} days'
            )

        return result

    @staticmethod
    def check_validity_for_operation(
        organization_id: str,
        user_id: str,
        operation_type: str
    ) -> Dict[str, Any]:
        """
        Check if pilot has valid medical for specific operation type.

        Args:
            organization_id: Organization ID
            user_id: User ID
            operation_type: Type of operation (commercial, private, atpl, etc.)

        Returns:
            Validity check result
        """
        # Define required medical class by operation
        operation_requirements = {
            'atpl_commercial': [MedicalClass.CLASS_1],
            'cpl_commercial': [MedicalClass.CLASS_1],
            'ppl_private': [MedicalClass.CLASS_1, MedicalClass.CLASS_2],
            'lapl_private': [MedicalClass.CLASS_1, MedicalClass.CLASS_2, MedicalClass.LAPL],
            'student_solo': [MedicalClass.CLASS_1, MedicalClass.CLASS_2, MedicalClass.LAPL],
            'atc': [MedicalClass.CLASS_3],
        }

        required_classes = operation_requirements.get(operation_type, [MedicalClass.CLASS_2])

        medicals = MedicalCertificate.objects.filter(
            organization_id=organization_id,
            user_id=user_id,
            status=MedicalStatus.ACTIVE,
            medical_class__in=required_classes,
            expiry_date__gte=date.today()
        )

        if not medicals.exists():
            return {
                'is_valid': False,
                'operation_type': operation_type,
                'required_classes': required_classes,
                'message': f'No valid medical for {operation_type} operations',
                'recommendation': f'Obtain {required_classes[0]} medical certificate',
            }

        valid_medical = medicals.first()
        return {
            'is_valid': True,
            'operation_type': operation_type,
            'medical_class': valid_medical.medical_class,
            'expiry_date': valid_medical.expiry_date.isoformat(),
            'days_valid': valid_medical.days_until_expiry,
            'limitations': valid_medical.limitations,
        }

    @staticmethod
    def get_renewal_requirements(
        medical: MedicalCertificate,
        pilot_birth_date: date
    ) -> Dict[str, Any]:
        """
        Get renewal requirements for a medical certificate.

        Args:
            medical: Current medical certificate
            pilot_birth_date: Pilot's birth date

        Returns:
            Renewal requirements
        """
        # Calculate age at renewal
        renewal_date = date.today()
        age_at_renewal = MedicalValidityService.calculate_age_at_date(
            pilot_birth_date, renewal_date
        )

        # Get new validity period
        new_validity = MedicalValidityService.calculate_validity_period(
            medical.medical_class,
            age_at_renewal,
            medical.issuing_authority
        )

        # Compare with current validity
        current_validity = medical.metadata.get('validity_months', 12)

        return {
            'current_medical': {
                'id': str(medical.id),
                'class': medical.medical_class,
                'expiry_date': medical.expiry_date.isoformat(),
                'validity_months': current_validity,
            },
            'renewal_info': {
                'age_at_renewal': age_at_renewal,
                'new_validity_months': new_validity,
                'validity_changed': new_validity != current_validity,
            },
            'recommendations': MedicalValidityService._get_renewal_recommendations(
                medical.medical_class, age_at_renewal, current_validity, new_validity
            ),
        }

    @staticmethod
    def _get_renewal_recommendations(
        medical_class: str,
        age: int,
        old_validity: int,
        new_validity: int
    ) -> List[str]:
        """Get recommendations for medical renewal."""
        recommendations = []

        if new_validity < old_validity:
            recommendations.append(
                f'Validity period will decrease from {old_validity} to {new_validity} months due to age'
            )

        # Age threshold warnings
        if medical_class == MedicalClass.CLASS_1:
            if age == 39:
                recommendations.append(
                    'Next renewal after age 40 will reduce validity to 6 months'
                )
            if age == 59:
                recommendations.append(
                    'Class 1 validity is 6 months from age 60'
                )
            if age >= 60:
                recommendations.append(
                    'Consider multi-crew operations only per FCL.065'
                )
                recommendations.append(
                    'Age 65 is maximum for commercial operations with passengers'
                )

        if medical_class == MedicalClass.CLASS_2:
            if age == 39:
                recommendations.append(
                    'Next renewal after age 40 will reduce validity to 24 months'
                )
            if age == 49:
                recommendations.append(
                    'Next renewal after age 50 will reduce validity to 12 months'
                )

        return recommendations

    # ==========================================================================
    # Expiration Monitoring
    # ==========================================================================

    @staticmethod
    def get_expiring_medicals(
        organization_id: str,
        days_ahead: int = 90
    ) -> List[Dict[str, Any]]:
        """Get medicals expiring within specified days."""
        threshold = date.today() + timedelta(days=days_ahead)

        medicals = MedicalCertificate.objects.filter(
            organization_id=organization_id,
            status=MedicalStatus.ACTIVE,
            expiry_date__lte=threshold,
            expiry_date__gte=date.today()
        ).order_by('expiry_date')

        results = []
        for medical in medicals:
            results.append({
                'medical_id': str(medical.id),
                'user_id': str(medical.user_id),
                'medical_class': medical.medical_class,
                'expiry_date': medical.expiry_date.isoformat(),
                'days_until_expiry': medical.days_until_expiry,
                'urgency': (
                    'critical' if medical.days_until_expiry <= 7
                    else 'warning' if medical.days_until_expiry <= 30
                    else 'notice'
                ),
                'limitations': medical.limitations,
            })

        return results

    @staticmethod
    def update_expired_statuses(organization_id: str) -> int:
        """Update status of expired medical certificates."""
        updated = MedicalCertificate.objects.filter(
            organization_id=organization_id,
            status=MedicalStatus.ACTIVE,
            expiry_date__lt=date.today()
        ).update(status=MedicalStatus.EXPIRED)

        if updated > 0:
            logger.info(f"Updated {updated} expired medical certificates")

        return updated

    # ==========================================================================
    # Downgrade Rules
    # ==========================================================================

    @staticmethod
    def check_medical_downgrade(medical: MedicalCertificate) -> Dict[str, Any]:
        """
        Check if expired medical can be used at lower privilege level.

        EASA rules allow using expired Class 1 as Class 2 for a period.

        Args:
            medical: Medical certificate to check

        Returns:
            Downgrade eligibility info
        """
        if medical.is_valid:
            return {
                'downgrade_applicable': False,
                'reason': 'Medical is still valid',
            }

        if medical.medical_class != MedicalClass.CLASS_1:
            return {
                'downgrade_applicable': False,
                'reason': 'Downgrade only applies to Class 1 medicals',
            }

        # Class 1 can be used as Class 2 when expired
        # Calculate remaining Class 2 validity
        original_validity = medical.metadata.get('validity_months', 12)
        age_at_exam = medical.pilot_age_at_exam

        if age_at_exam:
            class2_validity = EASAMedicalRules.get_class2_validity(age_at_exam)
            class2_expiry = MedicalValidityService.calculate_expiry_date(
                medical.issue_date, class2_validity, end_of_month=True
            )

            if date.today() <= class2_expiry:
                return {
                    'downgrade_applicable': True,
                    'downgraded_class': MedicalClass.CLASS_2,
                    'downgraded_expiry': class2_expiry.isoformat(),
                    'days_remaining': (class2_expiry - date.today()).days,
                    'privileges': MedicalCertificate(
                        medical_class=MedicalClass.CLASS_2
                    ).get_applicable_privileges(),
                }

        return {
            'downgrade_applicable': False,
            'reason': 'Downgraded validity also expired',
        }
