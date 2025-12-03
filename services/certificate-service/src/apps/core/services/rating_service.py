# services/certificate-service/src/apps/core/services/rating_service.py
"""
Rating Service

Business logic for rating/privilege management.
"""

import logging
from datetime import date, timedelta
from typing import List, Dict, Any, Optional
from uuid import UUID

from django.db import transaction
from django.db.models import Q, Count
from django.utils import timezone

from ..models import (
    Rating,
    RatingType,
    RatingStatus,
)

logger = logging.getLogger(__name__)


class RatingService:
    """Service for managing ratings and privileges."""

    @staticmethod
    def create_rating(
        organization_id: str,
        user_id: str,
        rating_type: str,
        rating_name: str,
        issue_date: date,
        expiry_date: Optional[date] = None,
        created_by: Optional[str] = None,
        **kwargs
    ) -> Rating:
        """
        Create a new rating.

        Args:
            organization_id: Organization ID
            user_id: User ID (pilot)
            rating_type: Type of rating
            rating_name: Rating name/description
            issue_date: Issue date
            expiry_date: Optional expiry date
            created_by: User creating the rating
            **kwargs: Additional fields

        Returns:
            Created Rating instance
        """
        rating = Rating.objects.create(
            organization_id=organization_id,
            user_id=user_id,
            rating_type=rating_type,
            rating_name=rating_name,
            issue_date=issue_date,
            expiry_date=expiry_date,
            created_by=created_by,
            **kwargs
        )

        logger.info(
            f"Created rating {rating.id} for user {user_id}",
            extra={'rating_id': str(rating.id), 'type': rating_type}
        )

        return rating

    @staticmethod
    def get_rating(
        organization_id: str,
        rating_id: str
    ) -> Rating:
        """
        Get a rating by ID.

        Args:
            organization_id: Organization ID
            rating_id: Rating ID

        Returns:
            Rating instance

        Raises:
            ValueError: If not found
        """
        try:
            return Rating.objects.get(
                id=rating_id,
                organization_id=organization_id
            )
        except Rating.DoesNotExist:
            raise ValueError(f'Rating {rating_id} not found')

    @staticmethod
    def list_ratings(
        organization_id: str,
        user_id: Optional[str] = None,
        rating_type: Optional[str] = None,
        status: Optional[str] = None,
        certificate_id: Optional[str] = None,
        aircraft_icao: Optional[str] = None
    ) -> List[Rating]:
        """
        List ratings with filters.

        Args:
            organization_id: Organization ID
            user_id: Filter by user
            rating_type: Filter by type
            status: Filter by status
            certificate_id: Filter by associated certificate
            aircraft_icao: Filter by aircraft type

        Returns:
            List of Rating instances
        """
        queryset = Rating.objects.filter(organization_id=organization_id)

        if user_id:
            queryset = queryset.filter(user_id=user_id)
        if rating_type:
            queryset = queryset.filter(rating_type=rating_type)
        if status:
            queryset = queryset.filter(status=status)
        if certificate_id:
            queryset = queryset.filter(certificate_id=certificate_id)
        if aircraft_icao:
            queryset = queryset.filter(aircraft_icao=aircraft_icao)

        return list(queryset.order_by('rating_type', '-issue_date'))

    @staticmethod
    def update_rating(
        organization_id: str,
        rating_id: str,
        **updates
    ) -> Rating:
        """
        Update a rating.

        Args:
            organization_id: Organization ID
            rating_id: Rating ID
            **updates: Fields to update

        Returns:
            Updated Rating instance
        """
        rating = RatingService.get_rating(organization_id, rating_id)

        for field, value in updates.items():
            if hasattr(rating, field):
                setattr(rating, field, value)

        rating.save()

        logger.info(f"Updated rating {rating_id}")

        return rating

    @staticmethod
    def delete_rating(
        organization_id: str,
        rating_id: str
    ) -> bool:
        """
        Delete a rating.

        Args:
            organization_id: Organization ID
            rating_id: Rating ID

        Returns:
            True if deleted
        """
        rating = RatingService.get_rating(organization_id, rating_id)
        rating.delete()

        logger.info(f"Deleted rating {rating_id}")

        return True

    @staticmethod
    def get_user_ratings(
        organization_id: str,
        user_id: str,
        active_only: bool = False
    ) -> List[Rating]:
        """
        Get all ratings for a user.

        Args:
            organization_id: Organization ID
            user_id: User ID
            active_only: Only return active ratings

        Returns:
            List of Rating instances
        """
        queryset = Rating.objects.filter(
            organization_id=organization_id,
            user_id=user_id
        )

        if active_only:
            queryset = queryset.filter(status=RatingStatus.ACTIVE)
            queryset = queryset.exclude(
                expiry_date__lt=date.today()
            )

        return list(queryset.order_by('rating_type'))

    @staticmethod
    def check_type_rating(
        organization_id: str,
        user_id: str,
        aircraft_icao: str
    ) -> Dict[str, Any]:
        """
        Check if user has valid type rating for aircraft.

        Args:
            organization_id: Organization ID
            user_id: User ID
            aircraft_icao: ICAO aircraft type designator

        Returns:
            Validity status dict
        """
        rating = Rating.objects.filter(
            organization_id=organization_id,
            user_id=user_id,
            rating_type=RatingType.AIRCRAFT_TYPE,
            aircraft_icao=aircraft_icao,
            status=RatingStatus.ACTIVE
        ).first()

        if not rating:
            return {
                'has_rating': False,
                'message': f'No type rating found for {aircraft_icao}',
                'rating': None,
            }

        if rating.is_expired:
            return {
                'has_rating': True,
                'is_valid': False,
                'message': f'Type rating for {aircraft_icao} expired',
                'rating': rating.get_validity_info(),
            }

        if rating.is_proficiency_due:
            return {
                'has_rating': True,
                'is_valid': False,
                'message': f'Proficiency check overdue for {aircraft_icao}',
                'rating': rating.get_validity_info(),
            }

        return {
            'has_rating': True,
            'is_valid': True,
            'message': f'Valid type rating for {aircraft_icao}',
            'rating': rating.get_validity_info(),
        }

    @staticmethod
    def record_proficiency_check(
        organization_id: str,
        rating_id: str,
        check_date: date,
        examiner_id: str,
        examiner_name: str,
        passed: bool = True,
        notes: Optional[str] = None
    ) -> Rating:
        """
        Record a proficiency check for a rating.

        Args:
            organization_id: Organization ID
            rating_id: Rating ID
            check_date: Date of proficiency check
            examiner_id: Examiner user ID
            examiner_name: Examiner name
            passed: Whether check was passed
            notes: Optional notes

        Returns:
            Updated Rating instance
        """
        rating = RatingService.get_rating(organization_id, rating_id)

        rating.record_proficiency_check(
            check_date=check_date,
            examiner_id=UUID(examiner_id),
            examiner_name=examiner_name,
            passed=passed
        )

        if notes:
            rating.notes = f"{rating.notes or ''}\n{check_date}: {notes}".strip()
            rating.save()

        logger.info(
            f"Recorded proficiency check for rating {rating_id}",
            extra={
                'rating_id': rating_id,
                'passed': passed,
                'examiner': examiner_name
            }
        )

        return rating

    @staticmethod
    def renew_rating(
        organization_id: str,
        rating_id: str,
        new_expiry_date: date,
        proficiency_date: Optional[date] = None
    ) -> Rating:
        """
        Renew a rating with new expiry date.

        Args:
            organization_id: Organization ID
            rating_id: Rating ID
            new_expiry_date: New expiry date
            proficiency_date: Date of proficiency check if applicable

        Returns:
            Renewed Rating instance
        """
        rating = RatingService.get_rating(organization_id, rating_id)

        rating.renew(
            new_expiry_date=new_expiry_date,
            proficiency_check_date=proficiency_date
        )

        logger.info(f"Renewed rating {rating_id} until {new_expiry_date}")

        return rating

    @staticmethod
    def get_expiring_ratings(
        organization_id: str,
        days_ahead: int = 90
    ) -> List[Dict[str, Any]]:
        """
        Get ratings expiring soon.

        Args:
            organization_id: Organization ID
            days_ahead: Days to look ahead

        Returns:
            List of expiring rating info dicts
        """
        expiry_date = date.today() + timedelta(days=days_ahead)

        # Expiring by date
        expiring_by_date = Rating.objects.filter(
            organization_id=organization_id,
            status=RatingStatus.ACTIVE,
            expiry_date__isnull=False,
            expiry_date__lte=expiry_date,
            expiry_date__gte=date.today()
        )

        # Proficiency due
        proficiency_due = Rating.objects.filter(
            organization_id=organization_id,
            status=RatingStatus.ACTIVE,
            next_proficiency_date__isnull=False,
            next_proficiency_date__lte=expiry_date
        )

        results = []

        for rating in expiring_by_date:
            results.append({
                'rating_id': str(rating.id),
                'user_id': str(rating.user_id),
                'rating_type': rating.rating_type,
                'rating_name': rating.rating_name,
                'aircraft_icao': rating.aircraft_icao,
                'issue_type': 'expiry',
                'date': rating.expiry_date.isoformat(),
                'days_remaining': rating.days_until_expiry,
            })

        for rating in proficiency_due:
            results.append({
                'rating_id': str(rating.id),
                'user_id': str(rating.user_id),
                'rating_type': rating.rating_type,
                'rating_name': rating.rating_name,
                'aircraft_icao': rating.aircraft_icao,
                'issue_type': 'proficiency',
                'date': rating.next_proficiency_date.isoformat(),
                'days_remaining': rating.days_until_proficiency,
            })

        return sorted(results, key=lambda x: x.get('days_remaining') or 0)

    @staticmethod
    def get_rating_statistics(
        organization_id: str
    ) -> Dict[str, Any]:
        """
        Get rating statistics for organization.

        Args:
            organization_id: Organization ID

        Returns:
            Statistics dict
        """
        ratings = Rating.objects.filter(organization_id=organization_id)

        total = ratings.count()
        by_type = ratings.values('rating_type').annotate(count=Count('id'))
        by_status = ratings.values('status').annotate(count=Count('id'))

        type_ratings = ratings.filter(rating_type=RatingType.AIRCRAFT_TYPE)
        unique_types = type_ratings.values('aircraft_icao').distinct().count()

        return {
            'total_ratings': total,
            'by_type': {t['rating_type']: t['count'] for t in by_type},
            'by_status': {s['status']: s['count'] for s in by_status},
            'unique_aircraft_types': unique_types,
            'active_count': ratings.filter(status=RatingStatus.ACTIVE).count(),
        }
