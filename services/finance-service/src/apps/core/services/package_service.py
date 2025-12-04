# services/finance-service/src/apps/core/services/package_service.py
"""
Package Service

Business logic for credit packages and prepaid services.
"""

import uuid
import logging
from decimal import Decimal
from typing import Optional, Dict, Any, List
from datetime import date, timedelta
from django.db import transaction
from django.db.models import Sum, Q
from django.utils import timezone

from ..models.account import Account
from ..models.package import (
    CreditPackage, UserPackage, PackageType, PackageStatus, UserPackageStatus
)
from ..models.transaction import TransactionType, TransactionSubtype

logger = logging.getLogger(__name__)


class PackageServiceError(Exception):
    """Base exception for package service errors."""
    pass


class PackageNotFoundError(PackageServiceError):
    """Raised when package is not found."""
    pass


class InsufficientCreditsError(PackageServiceError):
    """Raised when user doesn't have enough credits."""
    pass


class PackageExpiredError(PackageServiceError):
    """Raised when package has expired."""
    pass


class PackageService:
    """
    Service for managing credit packages.

    Handles package creation, purchases, usage tracking,
    and expiration management.
    """

    # ==================== PACKAGE MANAGEMENT ====================

    @staticmethod
    def create_package(
        organization_id: uuid.UUID,
        name: str,
        package_type: str,
        price: Decimal,
        currency: str = 'USD',
        credit_amount: Decimal = None,
        hours_amount: Decimal = None,
        description: str = None,
        features: List[str] = None,
        validity_days: int = 365,
        bonus_percent: Decimal = None,
        discount_percent: Decimal = None,
        max_purchases_per_user: int = None,
        applicable_aircraft_ids: List[uuid.UUID] = None,
        applicable_instructor_ids: List[uuid.UUID] = None,
        is_promotional: bool = False,
        promotion_start: date = None,
        promotion_end: date = None,
        metadata: Dict = None,
        created_by: uuid.UUID = None
    ) -> CreditPackage:
        """
        Create a new credit package.

        Args:
            organization_id: Organization UUID
            name: Package name
            package_type: Type of package
            price: Package price
            currency: Currency code
            credit_amount: Credit value (for credit packages)
            hours_amount: Hours included (for hour packages)
            description: Description
            features: List of features/benefits
            validity_days: Days until expiration
            bonus_percent: Bonus percentage added
            discount_percent: Discount from regular price
            max_purchases_per_user: Max purchases per user
            applicable_aircraft_ids: Applicable aircraft
            applicable_instructor_ids: Applicable instructors
            is_promotional: Is promotional package
            promotion_start: Promotion start date
            promotion_end: Promotion end date
            metadata: Additional metadata
            created_by: User who created

        Returns:
            Created CreditPackage instance
        """
        # Calculate effective value
        effective_credit = credit_amount or Decimal('0')
        if bonus_percent and credit_amount:
            effective_credit = credit_amount * (1 + bonus_percent / 100)

        package = CreditPackage.objects.create(
            organization_id=organization_id,
            name=name,
            description=description,
            package_type=package_type,
            price=price,
            currency=currency,
            credit_amount=credit_amount,
            hours_amount=hours_amount,
            effective_credit_amount=effective_credit,
            features=features or [],
            validity_days=validity_days,
            bonus_percent=bonus_percent,
            discount_percent=discount_percent,
            max_purchases_per_user=max_purchases_per_user,
            applicable_aircraft_ids=applicable_aircraft_ids,
            applicable_instructor_ids=applicable_instructor_ids,
            is_promotional=is_promotional,
            promotion_start=promotion_start,
            promotion_end=promotion_end,
            metadata=metadata or {},
            created_by=created_by,
            status=PackageStatus.ACTIVE
        )

        logger.info(
            f"Created package: {name}",
            extra={
                'package_id': str(package.id),
                'organization_id': str(organization_id),
                'price': float(price)
            }
        )

        return package

    @staticmethod
    def update_package(
        package_id: uuid.UUID,
        organization_id: uuid.UUID = None,
        updated_by: uuid.UUID = None,
        **updates
    ) -> CreditPackage:
        """
        Update a credit package.

        Args:
            package_id: Package UUID
            organization_id: Optional organization filter
            updated_by: User who updated
            **updates: Fields to update

        Returns:
            Updated CreditPackage instance
        """
        package = PackageService.get_package(package_id, organization_id)

        protected_fields = {'id', 'organization_id', 'created_at', 'created_by'}

        for field, value in updates.items():
            if field not in protected_fields:
                setattr(package, field, value)

        package.updated_by = updated_by
        package.save()

        logger.info(
            f"Updated package: {package.name}",
            extra={
                'package_id': str(package_id),
                'updates': list(updates.keys())
            }
        )

        return package

    @staticmethod
    def get_package(
        package_id: uuid.UUID,
        organization_id: uuid.UUID = None
    ) -> CreditPackage:
        """
        Get package by ID.

        Args:
            package_id: Package UUID
            organization_id: Optional organization filter

        Returns:
            CreditPackage instance

        Raises:
            PackageNotFoundError: If not found
        """
        queryset = CreditPackage.objects.filter(id=package_id)

        if organization_id:
            queryset = queryset.filter(organization_id=organization_id)

        package = queryset.first()

        if not package:
            raise PackageNotFoundError(f"Package {package_id} not found")

        return package

    @staticmethod
    def list_packages(
        organization_id: uuid.UUID,
        package_type: str = None,
        is_active: bool = True,
        is_available: bool = None,
        search: str = None,
        order_by: str = '-sort_order',
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        List packages with filtering.

        Args:
            organization_id: Organization UUID
            package_type: Filter by type
            is_active: Filter by active status
            is_available: Filter by availability
            search: Search in name and description
            order_by: Order by field
            limit: Max results
            offset: Result offset

        Returns:
            Dict with packages and pagination info
        """
        queryset = CreditPackage.objects.filter(organization_id=organization_id)

        if package_type:
            queryset = queryset.filter(package_type=package_type)

        if is_active is not None:
            if is_active:
                queryset = queryset.filter(status=PackageStatus.ACTIVE)
            else:
                queryset = queryset.exclude(status=PackageStatus.ACTIVE)

        if is_available is not None:
            today = date.today()
            if is_available:
                queryset = queryset.filter(
                    status=PackageStatus.ACTIVE,
                    Q(available_from__isnull=True) | Q(available_from__lte=today),
                    Q(available_to__isnull=True) | Q(available_to__gte=today)
                )

        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(description__icontains=search)
            )

        total = queryset.count()
        packages = queryset.order_by(order_by)[offset:offset + limit]

        return {
            'packages': [
                PackageService._package_to_dict(pkg)
                for pkg in packages
            ],
            'total': total,
            'limit': limit,
            'offset': offset,
        }

    # ==================== USER PACKAGE MANAGEMENT ====================

    @staticmethod
    @transaction.atomic
    def purchase_package(
        organization_id: uuid.UUID,
        package_id: uuid.UUID,
        user_id: uuid.UUID,
        account_id: uuid.UUID,
        payment_method: str = 'account',
        payment_reference: str = None,
        purchased_by: uuid.UUID = None,
        metadata: Dict = None
    ) -> UserPackage:
        """
        Purchase a package for a user.

        Args:
            organization_id: Organization UUID
            package_id: Package to purchase
            user_id: User UUID
            account_id: Account to charge
            payment_method: Payment method
            payment_reference: Payment reference
            purchased_by: User who made purchase
            metadata: Additional metadata

        Returns:
            Created UserPackage instance
        """
        package = PackageService.get_package(package_id, organization_id)

        # Validate package is purchasable
        if not package.is_purchasable:
            raise PackageServiceError(f"Package {package.name} is not available for purchase")

        # Check max purchases
        if package.max_purchases_per_user:
            existing_count = UserPackage.objects.filter(
                user_id=user_id,
                package=package
            ).exclude(status=UserPackageStatus.CANCELLED).count()

            if existing_count >= package.max_purchases_per_user:
                raise PackageServiceError(
                    f"Maximum purchases ({package.max_purchases_per_user}) reached for this package"
                )

        # Calculate expiry
        expires_at = None
        if package.validity_days:
            expires_at = timezone.now() + timedelta(days=package.validity_days)

        # Create user package
        user_package = UserPackage.objects.create(
            organization_id=organization_id,
            user_id=user_id,
            package=package,
            purchase_price=package.price,
            currency=package.currency,
            credit_remaining=package.effective_credit_amount or Decimal('0'),
            hours_remaining=package.hours_amount or Decimal('0'),
            expires_at=expires_at,
            payment_method=payment_method,
            payment_reference=payment_reference,
            metadata=metadata or {},
            status=UserPackageStatus.ACTIVE
        )

        # Update package stats
        package.total_sold += 1
        package.total_revenue += package.price
        package.save(update_fields=['total_sold', 'total_revenue', 'updated_at'])

        # Create transaction for payment
        from .transaction_service import TransactionService

        TransactionService.create_payment(
            organization_id=organization_id,
            account_id=account_id,
            amount=package.price,
            payment_method=payment_method,
            subtype=TransactionSubtype.PACKAGE_CREDIT,
            description=f"Package purchase: {package.name}",
            reference_type='package',
            reference_id=user_package.id,
            payment_reference=payment_reference,
            created_by=purchased_by
        )

        logger.info(
            f"User {user_id} purchased package {package.name}",
            extra={
                'user_package_id': str(user_package.id),
                'package_id': str(package_id),
                'price': float(package.price)
            }
        )

        return user_package

    @staticmethod
    def get_user_package(
        user_package_id: uuid.UUID,
        organization_id: uuid.UUID = None
    ) -> UserPackage:
        """
        Get user package by ID.

        Args:
            user_package_id: UserPackage UUID
            organization_id: Optional organization filter

        Returns:
            UserPackage instance

        Raises:
            PackageNotFoundError: If not found
        """
        queryset = UserPackage.objects.filter(id=user_package_id)

        if organization_id:
            queryset = queryset.filter(organization_id=organization_id)

        user_package = queryset.select_related('package').first()

        if not user_package:
            raise PackageNotFoundError(f"User package {user_package_id} not found")

        return user_package

    @staticmethod
    def get_user_packages(
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        status: str = None,
        include_expired: bool = False
    ) -> List[UserPackage]:
        """
        Get all packages for a user.

        Args:
            organization_id: Organization UUID
            user_id: User UUID
            status: Filter by status
            include_expired: Include expired packages

        Returns:
            List of UserPackage instances
        """
        queryset = UserPackage.objects.filter(
            organization_id=organization_id,
            user_id=user_id
        ).select_related('package')

        if status:
            queryset = queryset.filter(status=status)

        if not include_expired:
            queryset = queryset.exclude(status=UserPackageStatus.EXPIRED)

        return list(queryset.order_by('-purchased_at'))

    @staticmethod
    def get_active_packages(
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        package_type: str = None
    ) -> List[UserPackage]:
        """
        Get active packages for a user.

        Args:
            organization_id: Organization UUID
            user_id: User UUID
            package_type: Filter by package type

        Returns:
            List of active UserPackage instances
        """
        queryset = UserPackage.objects.filter(
            organization_id=organization_id,
            user_id=user_id,
            status=UserPackageStatus.ACTIVE
        ).select_related('package')

        if package_type:
            queryset = queryset.filter(package__package_type=package_type)

        # Filter expired
        now = timezone.now()
        queryset = queryset.filter(
            Q(expires_at__isnull=True) | Q(expires_at__gt=now)
        )

        return list(queryset.order_by('expires_at'))

    @staticmethod
    @transaction.atomic
    def use_package_credit(
        user_package_id: uuid.UUID,
        amount: Decimal,
        description: str = None,
        reference_type: str = None,
        reference_id: uuid.UUID = None,
        used_by: uuid.UUID = None
    ) -> Dict[str, Any]:
        """
        Use credit from a user package.

        Args:
            user_package_id: UserPackage UUID
            amount: Credit amount to use
            description: Usage description
            reference_type: Reference type
            reference_id: Reference UUID
            used_by: User who used the credit

        Returns:
            Dict with usage details

        Raises:
            InsufficientCreditsError: If not enough credits
            PackageExpiredError: If package is expired
        """
        user_package = UserPackage.objects.select_for_update().get(id=user_package_id)

        # Check status
        if user_package.status != UserPackageStatus.ACTIVE:
            raise PackageServiceError(f"Package is not active: {user_package.status}")

        # Check expiry
        if user_package.is_expired:
            user_package.expire()
            user_package.save()
            raise PackageExpiredError("Package has expired")

        # Check balance
        if user_package.credit_remaining < amount:
            raise InsufficientCreditsError(
                f"Insufficient credit. Available: {user_package.credit_remaining}, Required: {amount}"
            )

        # Use credit
        credit_before = user_package.credit_remaining
        user_package.use_credit(amount, description, reference_type, str(reference_id) if reference_id else None)
        user_package.save()

        logger.info(
            f"Used {amount} credit from package",
            extra={
                'user_package_id': str(user_package_id),
                'amount': float(amount),
                'credit_remaining': float(user_package.credit_remaining)
            }
        )

        return {
            'user_package_id': str(user_package_id),
            'amount_used': float(amount),
            'credit_before': float(credit_before),
            'credit_remaining': float(user_package.credit_remaining),
            'description': description,
            'reference_type': reference_type,
            'reference_id': str(reference_id) if reference_id else None,
        }

    @staticmethod
    @transaction.atomic
    def use_package_hours(
        user_package_id: uuid.UUID,
        hours: Decimal,
        description: str = None,
        reference_type: str = None,
        reference_id: uuid.UUID = None,
        used_by: uuid.UUID = None
    ) -> Dict[str, Any]:
        """
        Use hours from a user package.

        Args:
            user_package_id: UserPackage UUID
            hours: Hours to use
            description: Usage description
            reference_type: Reference type
            reference_id: Reference UUID
            used_by: User who used the hours

        Returns:
            Dict with usage details
        """
        user_package = UserPackage.objects.select_for_update().get(id=user_package_id)

        # Check status
        if user_package.status != UserPackageStatus.ACTIVE:
            raise PackageServiceError(f"Package is not active: {user_package.status}")

        # Check expiry
        if user_package.is_expired:
            user_package.expire()
            user_package.save()
            raise PackageExpiredError("Package has expired")

        # Check hours
        if user_package.hours_remaining < hours:
            raise InsufficientCreditsError(
                f"Insufficient hours. Available: {user_package.hours_remaining}, Required: {hours}"
            )

        # Use hours
        hours_before = user_package.hours_remaining
        user_package.use_hours(hours, description, reference_type, str(reference_id) if reference_id else None)
        user_package.save()

        logger.info(
            f"Used {hours} hours from package",
            extra={
                'user_package_id': str(user_package_id),
                'hours': float(hours),
                'hours_remaining': float(user_package.hours_remaining)
            }
        )

        return {
            'user_package_id': str(user_package_id),
            'hours_used': float(hours),
            'hours_before': float(hours_before),
            'hours_remaining': float(user_package.hours_remaining),
            'description': description,
            'reference_type': reference_type,
            'reference_id': str(reference_id) if reference_id else None,
        }

    @staticmethod
    def get_available_credit(
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        package_type: str = None
    ) -> Decimal:
        """
        Get total available credit for a user.

        Args:
            organization_id: Organization UUID
            user_id: User UUID
            package_type: Optional package type filter

        Returns:
            Total available credit
        """
        active_packages = PackageService.get_active_packages(
            organization_id=organization_id,
            user_id=user_id,
            package_type=package_type
        )

        return sum(
            pkg.credit_remaining
            for pkg in active_packages
            if pkg.credit_remaining > 0
        )

    @staticmethod
    def get_available_hours(
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        package_type: str = None
    ) -> Decimal:
        """
        Get total available hours for a user.

        Args:
            organization_id: Organization UUID
            user_id: User UUID
            package_type: Optional package type filter

        Returns:
            Total available hours
        """
        active_packages = PackageService.get_active_packages(
            organization_id=organization_id,
            user_id=user_id,
            package_type=package_type
        )

        return sum(
            pkg.hours_remaining
            for pkg in active_packages
            if pkg.hours_remaining > 0
        )

    @staticmethod
    @transaction.atomic
    def cancel_user_package(
        user_package_id: uuid.UUID,
        reason: str = None,
        refund_amount: Decimal = None,
        cancelled_by: uuid.UUID = None
    ) -> UserPackage:
        """
        Cancel a user package.

        Args:
            user_package_id: UserPackage UUID
            reason: Cancellation reason
            refund_amount: Amount to refund
            cancelled_by: User who cancelled

        Returns:
            Updated UserPackage instance
        """
        user_package = UserPackage.objects.select_for_update().get(id=user_package_id)

        if user_package.status == UserPackageStatus.CANCELLED:
            raise PackageServiceError("Package already cancelled")

        user_package.cancel(reason)
        user_package.save()

        # Process refund if specified
        if refund_amount and refund_amount > 0:
            from .transaction_service import TransactionService

            # Get account from original purchase
            # This would need to be stored or looked up
            pass

        logger.info(
            f"Cancelled user package",
            extra={
                'user_package_id': str(user_package_id),
                'reason': reason
            }
        )

        return user_package

    @staticmethod
    def expire_packages() -> int:
        """
        Expire all packages past their expiration date.

        Returns:
            Number of packages expired
        """
        now = timezone.now()

        expired = UserPackage.objects.filter(
            status=UserPackageStatus.ACTIVE,
            expires_at__lt=now
        )

        count = expired.count()

        for user_package in expired:
            user_package.expire()
            user_package.save()

        if count > 0:
            logger.info(f"Expired {count} user packages")

        return count

    @staticmethod
    def get_package_usage_stats(
        user_package_id: uuid.UUID
    ) -> Dict[str, Any]:
        """
        Get usage statistics for a user package.

        Args:
            user_package_id: UserPackage UUID

        Returns:
            Dict with usage statistics
        """
        user_package = PackageService.get_user_package(user_package_id)

        return {
            'user_package_id': str(user_package_id),
            'package_name': user_package.package.name,
            'credit': {
                'initial': float(user_package.package.effective_credit_amount or 0),
                'used': float(user_package.credit_used),
                'remaining': float(user_package.credit_remaining),
                'usage_percent': user_package.credit_usage_percent,
            },
            'hours': {
                'initial': float(user_package.package.hours_amount or 0),
                'used': float(user_package.hours_used),
                'remaining': float(user_package.hours_remaining),
                'usage_percent': user_package.hours_usage_percent,
            },
            'usage_history': user_package.usage_history,
            'usage_count': user_package.usage_count,
            'last_used_at': user_package.last_used_at.isoformat() if user_package.last_used_at else None,
            'purchased_at': user_package.purchased_at.isoformat(),
            'expires_at': user_package.expires_at.isoformat() if user_package.expires_at else None,
            'days_until_expiry': user_package.days_until_expiry,
            'status': user_package.status,
        }

    @staticmethod
    def _package_to_dict(package: CreditPackage) -> Dict[str, Any]:
        """Convert package to dictionary."""
        return {
            'id': str(package.id),
            'name': package.name,
            'description': package.description,
            'package_type': package.package_type,
            'price': float(package.price),
            'currency': package.currency,
            'credit_amount': float(package.credit_amount) if package.credit_amount else None,
            'hours_amount': float(package.hours_amount) if package.hours_amount else None,
            'effective_credit_amount': float(package.effective_credit_amount) if package.effective_credit_amount else None,
            'features': package.features,
            'validity_days': package.validity_days,
            'bonus_percent': float(package.bonus_percent) if package.bonus_percent else None,
            'discount_percent': float(package.discount_percent) if package.discount_percent else None,
            'is_promotional': package.is_promotional,
            'is_purchasable': package.is_purchasable,
            'status': package.status,
            'total_sold': package.total_sold,
            'created_at': package.created_at.isoformat(),
        }
