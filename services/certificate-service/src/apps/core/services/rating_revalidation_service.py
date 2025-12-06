# services/certificate-service/src/apps/core/services/rating_revalidation_service.py
"""
Rating Revalidation Service

EASA FCL.740/745 Rating Revalidation Business Logic.
Handles proficiency checks, experience-based revalidation, and renewal.
"""

import logging
from datetime import date, timedelta
from decimal import Decimal
from typing import List, Dict, Any, Optional, Tuple
from uuid import UUID
from dateutil.relativedelta import relativedelta

from django.db import transaction
from django.db.models import Sum, Count, Q
from django.utils import timezone

from ..models import (
    Rating,
    RatingStatus,
)
from ..models.rating_revalidation import (
    RatingRevalidationRule,
    RatingRevalidation,
    RatingExperienceLog,
    RatingCategory,
    RevalidationType,
    RevalidationStatus,
    FCL740Requirements,
    DEFAULT_REVALIDATION_RULES,
)

logger = logging.getLogger(__name__)


class RatingRevalidationService:
    """
    Service for managing rating revalidation per EASA FCL.740/745.

    Supports:
    - Proficiency check revalidation
    - Experience-based revalidation (FCL.745.A for SEP/MEP)
    - Renewal after lapse
    - Automatic expiry tracking
    """

    # ==========================================================================
    # Revalidation Rule Management
    # ==========================================================================

    @staticmethod
    def get_revalidation_rule(
        rating_category: str,
        organization_id: Optional[str] = None
    ) -> Optional[RatingRevalidationRule]:
        """
        Get revalidation rule for rating category.

        Args:
            rating_category: Rating category
            organization_id: Optional organization for custom rules

        Returns:
            RatingRevalidationRule or None
        """
        # Check for organization-specific rule first
        if organization_id:
            rule = RatingRevalidationRule.objects.filter(
                rating_category=rating_category,
                organization_id=organization_id,
                is_active=True
            ).first()
            if rule:
                return rule

        # Fall back to global rule
        return RatingRevalidationRule.objects.filter(
            rating_category=rating_category,
            organization_id__isnull=True,
            is_active=True
        ).first()

    @staticmethod
    def initialize_default_rules() -> int:
        """
        Initialize default EASA FCL.740/745 revalidation rules.

        Returns:
            Number of rules created
        """
        created = 0
        for rule_data in DEFAULT_REVALIDATION_RULES:
            rule, was_created = RatingRevalidationRule.objects.get_or_create(
                rating_category=rule_data['rating_category'],
                organization_id=None,
                defaults=rule_data
            )
            if was_created:
                created += 1
                logger.info(f"Created revalidation rule: {rule.rating_category}")

        return created

    # ==========================================================================
    # Revalidation Status Check
    # ==========================================================================

    @staticmethod
    def get_rating_revalidation_status(
        organization_id: str,
        rating_id: str
    ) -> Dict[str, Any]:
        """
        Get comprehensive revalidation status for a rating.

        Args:
            organization_id: Organization ID
            rating_id: Rating ID

        Returns:
            Revalidation status dict with all relevant info
        """
        try:
            rating = Rating.objects.get(
                id=rating_id,
                organization_id=organization_id
            )
        except Rating.DoesNotExist:
            raise ValueError(f"Rating {rating_id} not found")

        # Determine rating category
        category = RatingRevalidationService._determine_category(rating)
        rule = RatingRevalidationService.get_revalidation_rule(
            category, organization_id
        )

        if not rule:
            return {
                'rating_id': str(rating.id),
                'category': category,
                'status': 'no_rule',
                'message': 'No revalidation rule defined for this category',
            }

        # Calculate status
        today = date.today()
        expiry = rating.expiry_date

        if not expiry:
            if rule.validity_months == 0:
                return {
                    'rating_id': str(rating.id),
                    'category': category,
                    'status': RevalidationStatus.VALID,
                    'message': 'No expiry - rating valid indefinitely',
                    'rule': rule.regulatory_reference,
                }
            return {
                'rating_id': str(rating.id),
                'category': category,
                'status': 'unknown',
                'message': 'No expiry date set',
            }

        # Check status
        days_until_expiry = (expiry - today).days
        revalidation_window_start = expiry - relativedelta(
            months=rule.revalidation_window_months
        )
        lapse_date = expiry + relativedelta(months=rule.lapse_period_months)

        # Determine revalidation options
        options = RatingRevalidationService._get_revalidation_options(rule)

        if today > lapse_date:
            status = RevalidationStatus.LAPSED
            message = f'Rating lapsed. Renewal with training required per {rule.regulatory_reference}'
        elif today > expiry:
            status = RevalidationStatus.EXPIRED
            message = f'Rating expired {abs(days_until_expiry)} days ago. Revalidation needed.'
        elif today >= revalidation_window_start:
            status = RevalidationStatus.EXPIRING_SOON
            message = f'Within revalidation window. Expires in {days_until_expiry} days.'
        else:
            status = RevalidationStatus.VALID
            message = f'Rating valid. Expires in {days_until_expiry} days.'

        # Get experience if experience-based revalidation allowed
        experience = None
        if rule.proficiency_check_can_be_replaced:
            experience = RatingRevalidationService.get_experience_summary(
                organization_id,
                str(rating.user_id),
                str(rating.id),
                expiry - relativedelta(months=24)  # Look back 24 months
            )

        return {
            'rating_id': str(rating.id),
            'user_id': str(rating.user_id),
            'rating_name': rating.rating_name,
            'category': category,
            'status': status,
            'message': message,
            'expiry_date': expiry.isoformat(),
            'days_until_expiry': days_until_expiry,
            'revalidation_window_start': revalidation_window_start.isoformat(),
            'in_revalidation_window': today >= revalidation_window_start,
            'revalidation_options': options,
            'rule': {
                'reference': rule.regulatory_reference,
                'validity_months': rule.validity_months,
                'window_months': rule.revalidation_window_months,
                'requires_proficiency_check': rule.requires_proficiency_check,
                'can_use_experience': rule.proficiency_check_can_be_replaced,
                'min_flight_hours': float(rule.min_flight_hours) if rule.min_flight_hours else None,
                'min_training_hours': float(rule.min_training_hours) if rule.min_training_hours else None,
            },
            'experience': experience,
        }

    @staticmethod
    def _determine_category(rating: Rating) -> str:
        """Determine rating category for revalidation rules."""
        rating_type = rating.rating_type

        # Map rating type to category
        type_category_map = {
            'instrument_single': RatingCategory.IR_SE,
            'instrument_multi': RatingCategory.IR_ME,
            'type_single': RatingCategory.TYPE_SP,
            'type_multi': RatingCategory.TYPE_MP,
            'class_sep_land': RatingCategory.SEP_LAND,
            'class_sep_sea': RatingCategory.SEP_SEA,
            'class_mep_land': RatingCategory.MEP_LAND,
            'class_mep_sea': RatingCategory.MEP_SEA,
            'tmg': RatingCategory.TMG,
            'night': RatingCategory.NIGHT,
            'aerobatic': RatingCategory.AEROBATIC,
            'towing': RatingCategory.TOWING,
            'mountain': RatingCategory.MOUNTAIN,
        }

        return type_category_map.get(rating_type, RatingCategory.SEP_LAND)

    @staticmethod
    def _get_revalidation_options(rule: RatingRevalidationRule) -> List[Dict[str, Any]]:
        """Get available revalidation options for a rule."""
        options = []

        if rule.requires_proficiency_check:
            options.append({
                'type': RevalidationType.PROFICIENCY_CHECK,
                'description': 'Proficiency check with examiner',
                'required': not rule.proficiency_check_can_be_replaced,
            })

        if rule.proficiency_check_can_be_replaced:
            exp_desc = []
            if rule.min_flight_hours:
                exp_desc.append(f"{rule.min_flight_hours}h flight time")
            if rule.min_training_hours:
                exp_desc.append(f"{rule.min_training_hours}h with instructor")
            if rule.min_takeoffs_landings:
                exp_desc.append(f"{rule.min_takeoffs_landings} T/O & landings")

            options.append({
                'type': RevalidationType.EXPERIENCE_BASED,
                'description': ' + '.join(exp_desc),
                'requirements': {
                    'flight_hours': float(rule.min_flight_hours) if rule.min_flight_hours else None,
                    'training_hours': float(rule.min_training_hours) if rule.min_training_hours else None,
                    'takeoffs_landings': rule.min_takeoffs_landings,
                },
            })

        return options

    # ==========================================================================
    # Experience Tracking (FCL.745.A)
    # ==========================================================================

    @staticmethod
    def log_flight_experience(
        organization_id: str,
        user_id: str,
        rating_id: str,
        flight_data: Dict[str, Any]
    ) -> RatingExperienceLog:
        """
        Log flight experience for revalidation tracking.

        Args:
            organization_id: Organization ID
            user_id: Pilot user ID
            rating_id: Rating ID
            flight_data: Flight details

        Returns:
            Created RatingExperienceLog
        """
        log = RatingExperienceLog.objects.create(
            organization_id=organization_id,
            user_id=user_id,
            rating_id=rating_id,
            flight_id=flight_data.get('flight_id'),
            flight_date=flight_data['flight_date'],
            aircraft_registration=flight_data['aircraft_registration'],
            aircraft_type=flight_data['aircraft_type'],
            aircraft_class=flight_data.get('aircraft_class'),
            flight_time=Decimal(str(flight_data['flight_time'])),
            pic_time=Decimal(str(flight_data.get('pic_time', 0))),
            dual_time=Decimal(str(flight_data.get('dual_time', 0))),
            takeoffs=flight_data.get('takeoffs', 0),
            landings=flight_data.get('landings', 0),
            departure=flight_data.get('departure'),
            arrival=flight_data.get('arrival'),
            instructor_id=flight_data.get('instructor_id'),
            instructor_name=flight_data.get('instructor_name'),
        )

        logger.info(
            f"Logged experience for rating {rating_id}: {flight_data['flight_time']}h",
            extra={'rating_id': rating_id, 'user_id': user_id}
        )

        return log

    @staticmethod
    def get_experience_summary(
        organization_id: str,
        user_id: str,
        rating_id: str,
        from_date: date
    ) -> Dict[str, Any]:
        """
        Get experience summary for revalidation period.

        Args:
            organization_id: Organization ID
            user_id: User ID
            rating_id: Rating ID
            from_date: Start date for experience period

        Returns:
            Experience summary dict
        """
        logs = RatingExperienceLog.objects.filter(
            organization_id=organization_id,
            user_id=user_id,
            rating_id=rating_id,
            flight_date__gte=from_date,
            counts_for_revalidation=True
        )

        totals = logs.aggregate(
            total_time=Sum('flight_time'),
            pic_time=Sum('pic_time'),
            dual_time=Sum('dual_time'),
            total_takeoffs=Sum('takeoffs'),
            total_landings=Sum('landings'),
            flight_count=Count('id'),
        )

        # Get training flights (with instructor)
        training_flights = logs.filter(dual_time__gt=0)
        training_time = training_flights.aggregate(
            total=Sum('dual_time')
        )['total'] or Decimal('0')

        return {
            'from_date': from_date.isoformat(),
            'total_flight_time': float(totals['total_time'] or 0),
            'pic_time': float(totals['pic_time'] or 0),
            'training_time': float(training_time),
            'takeoffs': totals['total_takeoffs'] or 0,
            'landings': totals['total_landings'] or 0,
            'flight_count': totals['flight_count'] or 0,
        }

    @staticmethod
    def check_experience_requirements(
        organization_id: str,
        user_id: str,
        rating_id: str,
        rule: RatingRevalidationRule
    ) -> Dict[str, Any]:
        """
        Check if pilot meets experience-based revalidation requirements.

        Per FCL.745.A for SEP/MEP:
        - 12 hours flight time in class
        - 12 takeoffs and landings
        - 1 hour training flight with instructor (within last 3 months)

        Args:
            organization_id: Organization ID
            user_id: User ID
            rating_id: Rating ID
            rule: Revalidation rule

        Returns:
            Requirements check result
        """
        try:
            rating = Rating.objects.get(id=rating_id)
        except Rating.DoesNotExist:
            raise ValueError(f"Rating {rating_id} not found")

        expiry = rating.expiry_date or date.today()
        period_start = expiry - relativedelta(months=24)
        training_period_start = expiry - relativedelta(months=3)

        # Get experience summary
        experience = RatingRevalidationService.get_experience_summary(
            organization_id, user_id, rating_id, period_start
        )

        # Get recent training specifically
        recent_training = RatingExperienceLog.objects.filter(
            organization_id=organization_id,
            user_id=user_id,
            rating_id=rating_id,
            flight_date__gte=training_period_start,
            dual_time__gt=0,
            counts_for_revalidation=True
        ).aggregate(total=Sum('dual_time'))['total'] or Decimal('0')

        # Check requirements
        flight_hours_met = (
            Decimal(str(experience['total_flight_time'])) >=
            (rule.min_flight_hours or Decimal('0'))
        )
        training_hours_met = (
            recent_training >= (rule.min_training_hours or Decimal('0'))
        )
        takeoffs_landings_met = (
            min(experience['takeoffs'], experience['landings']) >=
            (rule.min_takeoffs_landings or 0)
        )

        all_met = flight_hours_met and training_hours_met and takeoffs_landings_met

        return {
            'eligible': all_met,
            'flight_hours': {
                'required': float(rule.min_flight_hours or 0),
                'logged': experience['total_flight_time'],
                'met': flight_hours_met,
            },
            'training_hours': {
                'required': float(rule.min_training_hours or 0),
                'logged': float(recent_training),
                'met': training_hours_met,
                'period': f'Last 3 months (since {training_period_start.isoformat()})',
            },
            'takeoffs_landings': {
                'required': rule.min_takeoffs_landings or 0,
                'takeoffs': experience['takeoffs'],
                'landings': experience['landings'],
                'met': takeoffs_landings_met,
            },
            'message': (
                'All requirements met - eligible for experience-based revalidation'
                if all_met else
                'Requirements not met - proficiency check required'
            ),
        }

    # ==========================================================================
    # Revalidation Processing
    # ==========================================================================

    @staticmethod
    @transaction.atomic
    def revalidate_by_proficiency_check(
        organization_id: str,
        rating_id: str,
        check_date: date,
        examiner_id: str,
        examiner_name: str,
        examiner_certificate: Optional[str] = None,
        aircraft_registration: Optional[str] = None,
        aircraft_type: Optional[str] = None,
        simulator_used: bool = False,
        simulator_id: Optional[str] = None,
        proficiency_sections: Optional[List[str]] = None,
        passed: bool = True,
        notes: Optional[str] = None,
        created_by: Optional[str] = None
    ) -> RatingRevalidation:
        """
        Revalidate rating by proficiency check.

        Per FCL.740.A - Most ratings can be revalidated by proficiency check.

        Args:
            organization_id: Organization ID
            rating_id: Rating ID
            check_date: Date of proficiency check
            examiner_id: Examiner user ID
            examiner_name: Examiner name
            examiner_certificate: Examiner certificate number (FE/TRE)
            aircraft_registration: Aircraft used (if applicable)
            aircraft_type: Aircraft type
            simulator_used: Whether simulator was used
            simulator_id: FSTD identifier
            proficiency_sections: Sections completed
            passed: Whether check was passed
            notes: Additional notes
            created_by: User creating the record

        Returns:
            Created RatingRevalidation
        """
        try:
            rating = Rating.objects.get(
                id=rating_id,
                organization_id=organization_id
            )
        except Rating.DoesNotExist:
            raise ValueError(f"Rating {rating_id} not found")

        if not passed:
            # Record failed check without revalidating
            return RatingRevalidation.objects.create(
                organization_id=organization_id,
                user_id=rating.user_id,
                rating_id=rating.id,
                rating_category=RatingRevalidationService._determine_category(rating),
                revalidation_type=RevalidationType.PROFICIENCY_CHECK,
                revalidation_date=check_date,
                previous_expiry_date=rating.expiry_date,
                new_expiry_date=rating.expiry_date,  # No change
                status=RevalidationStatus.PENDING,
                examiner_id=examiner_id,
                examiner_name=examiner_name,
                examiner_certificate=examiner_certificate,
                aircraft_registration=aircraft_registration,
                aircraft_type=aircraft_type,
                simulator_used=simulator_used,
                simulator_id=simulator_id,
                proficiency_sections=proficiency_sections or [],
                proficiency_result='fail',
                notes=notes,
                created_by=created_by,
            )

        # Get rule to determine new validity
        category = RatingRevalidationService._determine_category(rating)
        rule = RatingRevalidationService.get_revalidation_rule(
            category, organization_id
        )

        if not rule:
            raise ValueError(f"No revalidation rule for category {category}")

        # Calculate new expiry per FCL.740
        # If revalidated within window, new expiry is from old expiry + validity
        # If outside window, new expiry is from check date + validity
        previous_expiry = rating.expiry_date
        window_start = (
            previous_expiry - relativedelta(months=rule.revalidation_window_months)
            if previous_expiry else None
        )

        if previous_expiry and window_start and window_start <= check_date <= previous_expiry:
            # Within window - extend from original expiry
            new_expiry = previous_expiry + relativedelta(months=rule.validity_months)
        else:
            # Outside window or no previous expiry
            new_expiry = check_date + relativedelta(months=rule.validity_months)

        # Create revalidation record
        revalidation = RatingRevalidation.objects.create(
            organization_id=organization_id,
            user_id=rating.user_id,
            rating_id=rating.id,
            rating_category=category,
            revalidation_type=RevalidationType.PROFICIENCY_CHECK,
            revalidation_date=check_date,
            previous_expiry_date=previous_expiry,
            new_expiry_date=new_expiry,
            status=RevalidationStatus.VALID,
            examiner_id=examiner_id,
            examiner_name=examiner_name,
            examiner_certificate=examiner_certificate,
            aircraft_registration=aircraft_registration,
            aircraft_type=aircraft_type,
            simulator_used=simulator_used,
            simulator_id=simulator_id,
            proficiency_sections=proficiency_sections or [],
            proficiency_result='pass',
            notes=notes,
            created_by=created_by,
        )

        # Update rating
        rating.expiry_date = new_expiry
        rating.last_proficiency_date = check_date
        rating.next_proficiency_date = new_expiry - relativedelta(
            months=rule.revalidation_window_months
        )
        rating.status = RatingStatus.ACTIVE
        rating.save()

        logger.info(
            f"Revalidated rating {rating_id} by proficiency check until {new_expiry}",
            extra={'rating_id': rating_id, 'examiner': examiner_name}
        )

        return revalidation

    @staticmethod
    @transaction.atomic
    def revalidate_by_experience(
        organization_id: str,
        rating_id: str,
        revalidation_date: date,
        instructor_id: str,
        instructor_name: str,
        instructor_certificate: Optional[str] = None,
        training_hours: Decimal = Decimal('1'),
        training_maneuvers: Optional[List[str]] = None,
        aircraft_registration: Optional[str] = None,
        aircraft_type: Optional[str] = None,
        notes: Optional[str] = None,
        created_by: Optional[str] = None
    ) -> RatingRevalidation:
        """
        Revalidate rating by experience per FCL.745.A.

        For SEP/MEP class ratings:
        - 12 hours flight time in preceding 12 months
        - 12 takeoffs and landings
        - 1 hour training flight with instructor

        Args:
            organization_id: Organization ID
            rating_id: Rating ID
            revalidation_date: Date of training flight
            instructor_id: Instructor user ID
            instructor_name: Instructor name
            instructor_certificate: Instructor certificate (FI/CRI)
            training_hours: Hours of training flight
            training_maneuvers: Maneuvers completed
            aircraft_registration: Aircraft used
            aircraft_type: Aircraft type
            notes: Additional notes
            created_by: User creating the record

        Returns:
            Created RatingRevalidation
        """
        try:
            rating = Rating.objects.get(
                id=rating_id,
                organization_id=organization_id
            )
        except Rating.DoesNotExist:
            raise ValueError(f"Rating {rating_id} not found")

        category = RatingRevalidationService._determine_category(rating)
        rule = RatingRevalidationService.get_revalidation_rule(
            category, organization_id
        )

        if not rule:
            raise ValueError(f"No revalidation rule for category {category}")

        if not rule.proficiency_check_can_be_replaced:
            raise ValueError(
                f"Experience-based revalidation not allowed for {category}. "
                f"Proficiency check required per {rule.regulatory_reference}."
            )

        # Verify experience requirements
        experience_check = RatingRevalidationService.check_experience_requirements(
            organization_id, str(rating.user_id), rating_id, rule
        )

        if not experience_check['eligible']:
            raise ValueError(
                f"Experience requirements not met: {experience_check['message']}"
            )

        # Get experience summary for record
        period_start = rating.expiry_date - relativedelta(months=24) if rating.expiry_date else date.today() - relativedelta(months=24)
        experience = RatingRevalidationService.get_experience_summary(
            organization_id, str(rating.user_id), rating_id, period_start
        )

        # Calculate new expiry
        previous_expiry = rating.expiry_date
        window_start = (
            previous_expiry - relativedelta(months=rule.revalidation_window_months)
            if previous_expiry else None
        )

        if previous_expiry and window_start and window_start <= revalidation_date <= previous_expiry:
            new_expiry = previous_expiry + relativedelta(months=rule.validity_months)
        else:
            new_expiry = revalidation_date + relativedelta(months=rule.validity_months)

        # Create revalidation record
        revalidation = RatingRevalidation.objects.create(
            organization_id=organization_id,
            user_id=rating.user_id,
            rating_id=rating.id,
            rating_category=category,
            revalidation_type=RevalidationType.EXPERIENCE_BASED,
            revalidation_date=revalidation_date,
            previous_expiry_date=previous_expiry,
            new_expiry_date=new_expiry,
            status=RevalidationStatus.VALID,
            instructor_id=instructor_id,
            instructor_name=instructor_name,
            instructor_certificate=instructor_certificate,
            flight_hours_logged=Decimal(str(experience['total_flight_time'])),
            training_hours=training_hours,
            takeoffs_landings=min(experience['takeoffs'], experience['landings']),
            aircraft_registration=aircraft_registration,
            aircraft_type=aircraft_type,
            training_maneuvers=training_maneuvers or [],
            notes=notes,
            created_by=created_by,
        )

        # Update rating
        rating.expiry_date = new_expiry
        rating.status = RatingStatus.ACTIVE
        rating.save()

        logger.info(
            f"Revalidated rating {rating_id} by experience until {new_expiry}",
            extra={'rating_id': rating_id, 'instructor': instructor_name}
        )

        return revalidation

    @staticmethod
    @transaction.atomic
    def renew_lapsed_rating(
        organization_id: str,
        rating_id: str,
        renewal_date: date,
        proficiency_check_passed: bool,
        examiner_id: str,
        examiner_name: str,
        training_completed: bool = True,
        training_hours: Optional[Decimal] = None,
        training_provider: Optional[str] = None,
        aircraft_registration: Optional[str] = None,
        notes: Optional[str] = None,
        created_by: Optional[str] = None
    ) -> RatingRevalidation:
        """
        Renew a lapsed rating per FCL.740.

        After rating has lapsed (expired > lapse period), renewal requires:
        - Refresher training
        - Proficiency check

        Args:
            organization_id: Organization ID
            rating_id: Rating ID
            renewal_date: Date of renewal
            proficiency_check_passed: Whether proficiency check passed
            examiner_id: Examiner ID
            examiner_name: Examiner name
            training_completed: Whether training was completed
            training_hours: Hours of refresher training
            training_provider: ATO that provided training
            aircraft_registration: Aircraft used
            notes: Additional notes
            created_by: User creating record

        Returns:
            Created RatingRevalidation
        """
        try:
            rating = Rating.objects.get(
                id=rating_id,
                organization_id=organization_id
            )
        except Rating.DoesNotExist:
            raise ValueError(f"Rating {rating_id} not found")

        category = RatingRevalidationService._determine_category(rating)
        rule = RatingRevalidationService.get_revalidation_rule(
            category, organization_id
        )

        if not rule:
            raise ValueError(f"No revalidation rule for category {category}")

        if not training_completed and rule.renewal_requires_training:
            raise ValueError(
                f"Refresher training required for renewal per {rule.regulatory_reference}"
            )

        if not proficiency_check_passed:
            raise ValueError("Proficiency check must be passed for renewal")

        # Calculate new expiry from renewal date
        new_expiry = renewal_date + relativedelta(months=rule.validity_months)

        revalidation = RatingRevalidation.objects.create(
            organization_id=organization_id,
            user_id=rating.user_id,
            rating_id=rating.id,
            rating_category=category,
            revalidation_type=RevalidationType.RENEWAL,
            revalidation_date=renewal_date,
            previous_expiry_date=rating.expiry_date,
            new_expiry_date=new_expiry,
            status=RevalidationStatus.VALID,
            examiner_id=examiner_id,
            examiner_name=examiner_name,
            training_hours=training_hours,
            aircraft_registration=aircraft_registration,
            proficiency_result='pass',
            notes=notes,
            metadata={
                'renewal': True,
                'training_completed': training_completed,
                'training_provider': training_provider,
            },
            created_by=created_by,
        )

        # Update rating
        rating.expiry_date = new_expiry
        rating.status = RatingStatus.ACTIVE
        rating.save()

        logger.info(
            f"Renewed lapsed rating {rating_id} until {new_expiry}",
            extra={'rating_id': rating_id}
        )

        return revalidation

    # ==========================================================================
    # Queries and Reports
    # ==========================================================================

    @staticmethod
    def get_revalidation_history(
        organization_id: str,
        rating_id: str
    ) -> List[Dict[str, Any]]:
        """Get revalidation history for a rating."""
        revalidations = RatingRevalidation.objects.filter(
            organization_id=organization_id,
            rating_id=rating_id
        ).order_by('-revalidation_date')

        return [r.get_summary() for r in revalidations]

    @staticmethod
    def get_expiring_ratings(
        organization_id: str,
        days_ahead: int = 90
    ) -> List[Dict[str, Any]]:
        """Get ratings expiring within specified days."""
        expiry_date = date.today() + timedelta(days=days_ahead)

        ratings = Rating.objects.filter(
            organization_id=organization_id,
            status=RatingStatus.ACTIVE,
            expiry_date__isnull=False,
            expiry_date__lte=expiry_date,
            expiry_date__gte=date.today()
        ).select_related()

        results = []
        for rating in ratings:
            category = RatingRevalidationService._determine_category(rating)
            rule = RatingRevalidationService.get_revalidation_rule(
                category, organization_id
            )

            days_until_expiry = (rating.expiry_date - date.today()).days
            in_window = False
            if rule:
                window_start = rating.expiry_date - relativedelta(
                    months=rule.revalidation_window_months
                )
                in_window = date.today() >= window_start

            results.append({
                'rating_id': str(rating.id),
                'user_id': str(rating.user_id),
                'rating_name': rating.rating_name,
                'rating_type': rating.rating_type,
                'category': category,
                'expiry_date': rating.expiry_date.isoformat(),
                'days_until_expiry': days_until_expiry,
                'in_revalidation_window': in_window,
                'revalidation_options': (
                    RatingRevalidationService._get_revalidation_options(rule)
                    if rule else []
                ),
            })

        return sorted(results, key=lambda x: x['days_until_expiry'])

    @staticmethod
    def get_pilot_ratings_summary(
        organization_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """Get comprehensive ratings summary for a pilot."""
        ratings = Rating.objects.filter(
            organization_id=organization_id,
            user_id=user_id
        )

        today = date.today()

        summary = {
            'user_id': user_id,
            'total_ratings': ratings.count(),
            'active': [],
            'expiring_soon': [],
            'expired': [],
            'lapsed': [],
        }

        for rating in ratings:
            category = RatingRevalidationService._determine_category(rating)
            rule = RatingRevalidationService.get_revalidation_rule(
                category, organization_id
            )

            info = {
                'rating_id': str(rating.id),
                'name': rating.rating_name,
                'type': rating.rating_type,
                'category': category,
                'expiry_date': rating.expiry_date.isoformat() if rating.expiry_date else None,
            }

            if not rating.expiry_date or (rule and rule.validity_months == 0):
                # No expiry
                summary['active'].append(info)
            elif rating.expiry_date < today:
                # Check if lapsed
                if rule:
                    lapse_date = rating.expiry_date + relativedelta(
                        months=rule.lapse_period_months
                    )
                    if today > lapse_date:
                        summary['lapsed'].append(info)
                    else:
                        summary['expired'].append(info)
                else:
                    summary['expired'].append(info)
            else:
                days = (rating.expiry_date - today).days
                if days <= 90:
                    info['days_remaining'] = days
                    summary['expiring_soon'].append(info)
                else:
                    summary['active'].append(info)

        return summary
