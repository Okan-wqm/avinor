# services/finance-service/src/apps/core/models/package.py
"""
Package Models

Credit packages and flight hour bundles for prepaid services.
"""

import uuid
from decimal import Decimal
from datetime import timedelta
from django.db import models
from django.utils import timezone
from django.contrib.postgres.fields import ArrayField


class PackageType(models.TextChoices):
    """Package type choices."""
    FLIGHT_HOURS = 'flight_hours', 'Flight Hours'
    CREDIT_AMOUNT = 'credit_amount', 'Credit Amount'
    BLOCK_HOURS = 'block_hours', 'Block Hours'
    INSTRUCTION_HOURS = 'instruction_hours', 'Instruction Hours'
    COMBO = 'combo', 'Combo Package'


class CreditPackage(models.Model):
    """
    Credit package definition model.

    Defines prepaid packages that users can purchase
    for discounted rates.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    organization_id = models.UUIDField(db_index=True)

    # Package Details
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    short_description = models.CharField(max_length=500, blank=True, null=True)

    # Package Type
    package_type = models.CharField(
        max_length=50,
        choices=PackageType.choices,
        db_index=True
    )

    # Content
    credit_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        help_text='Credit amount for credit_amount packages'
    )
    flight_hours = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        blank=True,
        null=True,
        help_text='Flight hours for flight_hours packages'
    )
    instruction_hours = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        blank=True,
        null=True,
        help_text='Instruction hours for instruction packages'
    )
    bonus_hours = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal('0'),
        help_text='Bonus hours included'
    )
    bonus_credit = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0'),
        help_text='Bonus credit included'
    )

    # Pricing
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text='Package purchase price'
    )
    original_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        help_text='Original price before discount'
    )
    currency = models.CharField(max_length=3, default='USD')

    # Savings
    savings_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True
    )
    savings_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True
    )

    # Applicability
    applicable_aircraft = ArrayField(
        models.UUIDField(),
        blank=True,
        null=True,
        help_text='Specific aircraft IDs (empty = all)'
    )
    applicable_aircraft_types = ArrayField(
        models.CharField(max_length=50),
        blank=True,
        null=True,
        help_text='Aircraft type codes'
    )
    applicable_services = ArrayField(
        models.CharField(max_length=50),
        blank=True,
        null=True,
        help_text='Service types this package can be used for'
    )
    excluded_services = ArrayField(
        models.CharField(max_length=50),
        blank=True,
        null=True,
        help_text='Service types excluded from this package'
    )

    # Validity
    validity_days = models.IntegerField(
        blank=True,
        null=True,
        help_text='Days from purchase until expiry'
    )
    validity_months = models.IntegerField(
        blank=True,
        null=True,
        help_text='Months from purchase until expiry'
    )
    fixed_expiry_date = models.DateField(
        blank=True,
        null=True,
        help_text='Fixed expiry date for all purchases'
    )

    # Restrictions
    min_purchase_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True
    )
    max_purchases_per_user = models.IntegerField(
        blank=True,
        null=True,
        help_text='Maximum times a user can purchase'
    )
    max_active_per_user = models.IntegerField(
        default=1,
        help_text='Maximum active packages per user'
    )
    total_available = models.IntegerField(
        blank=True,
        null=True,
        help_text='Total packages available for sale'
    )
    total_sold = models.IntegerField(default=0)

    # User Requirements
    required_membership_level = models.CharField(
        max_length=50,
        blank=True,
        null=True
    )
    required_user_types = ArrayField(
        models.CharField(max_length=50),
        blank=True,
        null=True,
        help_text='student, pilot, instructor'
    )
    new_users_only = models.BooleanField(
        default=False,
        help_text='Only available to new users'
    )

    # Status
    is_active = models.BooleanField(default=True, db_index=True)
    is_featured = models.BooleanField(default=False)
    is_promotional = models.BooleanField(default=False)

    # Display
    display_order = models.IntegerField(default=0)
    image_url = models.URLField(max_length=500, blank=True, null=True)
    badge_text = models.CharField(max_length=50, blank=True, null=True)
    badge_color = models.CharField(max_length=20, blank=True, null=True)

    # Sale Period
    sale_start_date = models.DateTimeField(blank=True, null=True)
    sale_end_date = models.DateTimeField(blank=True, null=True)

    # Terms
    terms_and_conditions = models.TextField(blank=True, null=True)
    cancellation_policy = models.TextField(blank=True, null=True)
    is_refundable = models.BooleanField(default=False)
    refund_policy = models.TextField(blank=True, null=True)

    # Metadata
    metadata = models.JSONField(default=dict, blank=True)

    # Audit
    created_by = models.UUIDField(blank=True, null=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'credit_packages'
        ordering = ['display_order', '-is_featured', 'name']
        indexes = [
            models.Index(fields=['organization_id', 'is_active']),
            models.Index(fields=['organization_id', 'package_type', 'is_active']),
        ]

    def __str__(self):
        return f"{self.name}: {self.price} {self.currency}"

    @property
    def is_available(self) -> bool:
        """Check if package is currently available for purchase."""
        if not self.is_active:
            return False

        now = timezone.now()
        if self.sale_start_date and now < self.sale_start_date:
            return False
        if self.sale_end_date and now > self.sale_end_date:
            return False

        if self.total_available and self.total_sold >= self.total_available:
            return False

        return True

    @property
    def remaining_quantity(self) -> int:
        """Get remaining quantity available."""
        if not self.total_available:
            return None
        return max(0, self.total_available - self.total_sold)

    @property
    def effective_hourly_rate(self) -> Decimal:
        """Calculate effective hourly rate for flight hours packages."""
        if self.flight_hours and self.flight_hours > 0:
            total_hours = self.flight_hours + (self.bonus_hours or Decimal('0'))
            return self.price / total_hours
        return None

    def get_expiry_date(self, purchase_date=None) -> date:
        """Calculate expiry date for a purchase."""
        if self.fixed_expiry_date:
            return self.fixed_expiry_date

        base_date = purchase_date or timezone.now().date()

        if self.validity_months:
            # Add months
            month = base_date.month + self.validity_months
            year = base_date.year + (month - 1) // 12
            month = ((month - 1) % 12) + 1
            day = min(base_date.day, [31, 29 if year % 4 == 0 else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1])
            return date(year, month, day)

        if self.validity_days:
            return base_date + timedelta(days=self.validity_days)

        # Default: 1 year
        return base_date + timedelta(days=365)

    def can_user_purchase(self, user_id: uuid.UUID, user_type: str = None, is_member: bool = False) -> tuple:
        """
        Check if user can purchase this package.

        Returns (can_purchase, reason).
        """
        if not self.is_available:
            return False, "Package is not available"

        if self.required_user_types and user_type not in self.required_user_types:
            return False, f"Package is only available to: {', '.join(self.required_user_types)}"

        if self.required_membership_level and not is_member:
            return False, f"Requires {self.required_membership_level} membership"

        # Check purchase limits
        if self.max_purchases_per_user:
            from .package import UserPackage
            purchase_count = UserPackage.objects.filter(
                package_id=self.id,
                account__owner_id=user_id
            ).count()
            if purchase_count >= self.max_purchases_per_user:
                return False, "Maximum purchase limit reached"

        if self.max_active_per_user:
            from .package import UserPackage, UserPackageStatus
            active_count = UserPackage.objects.filter(
                package_id=self.id,
                account__owner_id=user_id,
                status=UserPackageStatus.ACTIVE
            ).count()
            if active_count >= self.max_active_per_user:
                return False, "Maximum active packages limit reached"

        return True, None


class UserPackageStatus(models.TextChoices):
    """User package status choices."""
    ACTIVE = 'active', 'Active'
    DEPLETED = 'depleted', 'Depleted'
    EXPIRED = 'expired', 'Expired'
    CANCELLED = 'cancelled', 'Cancelled'
    SUSPENDED = 'suspended', 'Suspended'
    REFUNDED = 'refunded', 'Refunded'


class UserPackage(models.Model):
    """
    User package instance model.

    Tracks purchased packages and their usage.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    organization_id = models.UUIDField(db_index=True)

    account = models.ForeignKey(
        'Account',
        on_delete=models.PROTECT,
        related_name='packages'
    )
    package = models.ForeignKey(
        CreditPackage,
        on_delete=models.PROTECT,
        related_name='user_packages'
    )

    # Purchase Details
    purchase_date = models.DateTimeField(default=timezone.now)
    purchase_price = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )
    purchase_currency = models.CharField(max_length=3, default='USD')
    transaction_id = models.UUIDField(
        blank=True,
        null=True,
        db_index=True
    )

    # Package Content (copied at purchase time)
    package_type = models.CharField(
        max_length=50,
        choices=PackageType.choices
    )
    original_credit = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        help_text='Original credit amount'
    )
    original_hours = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        blank=True,
        null=True,
        help_text='Original flight hours'
    )
    original_instruction_hours = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        blank=True,
        null=True
    )

    # Balance
    remaining_credit = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True
    )
    remaining_hours = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        blank=True,
        null=True
    )
    remaining_instruction_hours = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        blank=True,
        null=True
    )

    # Validity
    expires_at = models.DateTimeField(db_index=True)

    # Status
    status = models.CharField(
        max_length=20,
        choices=UserPackageStatus.choices,
        default=UserPackageStatus.ACTIVE,
        db_index=True
    )
    status_changed_at = models.DateTimeField(blank=True, null=True)
    status_reason = models.TextField(blank=True, null=True)

    # Usage History
    usage_history = models.JSONField(
        default=list,
        help_text='History of usage deductions'
    )
    total_used_credit = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0')
    )
    total_used_hours = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal('0')
    )

    # Last Usage
    last_used_at = models.DateTimeField(blank=True, null=True)
    last_usage_reference_type = models.CharField(max_length=50, blank=True, null=True)
    last_usage_reference_id = models.UUIDField(blank=True, null=True)

    # Refund
    refunded_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0')
    )
    refund_transaction_id = models.UUIDField(blank=True, null=True)

    # Notes
    notes = models.TextField(blank=True, null=True)

    # Metadata
    metadata = models.JSONField(default=dict, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'user_packages'
        ordering = ['-purchase_date']
        indexes = [
            models.Index(fields=['organization_id', 'account_id', 'status']),
            models.Index(fields=['organization_id', 'expires_at']),
        ]

    def __str__(self):
        return f"{self.package.name} - {self.account.account_number}"

    @property
    def is_active(self) -> bool:
        """Check if package is active and usable."""
        if self.status != UserPackageStatus.ACTIVE:
            return False
        if timezone.now() > self.expires_at:
            return False
        return self.has_remaining_balance

    @property
    def is_expired(self) -> bool:
        """Check if package is expired."""
        return timezone.now() > self.expires_at

    @property
    def has_remaining_balance(self) -> bool:
        """Check if package has remaining balance."""
        if self.remaining_credit and self.remaining_credit > Decimal('0'):
            return True
        if self.remaining_hours and self.remaining_hours > Decimal('0'):
            return True
        if self.remaining_instruction_hours and self.remaining_instruction_hours > Decimal('0'):
            return True
        return False

    @property
    def usage_percentage(self) -> float:
        """Calculate usage percentage."""
        if self.package_type == PackageType.CREDIT_AMOUNT:
            if self.original_credit and self.original_credit > 0:
                used = self.original_credit - (self.remaining_credit or Decimal('0'))
                return float(used / self.original_credit * 100)
        elif self.package_type == PackageType.FLIGHT_HOURS:
            if self.original_hours and self.original_hours > 0:
                used = self.original_hours - (self.remaining_hours or Decimal('0'))
                return float(used / self.original_hours * 100)
        return 0

    @property
    def days_until_expiry(self) -> int:
        """Calculate days until expiry."""
        if self.expires_at:
            delta = self.expires_at - timezone.now()
            return max(0, delta.days)
        return 0

    def use_credit(
        self,
        amount: Decimal,
        reference_type: str = None,
        reference_id: uuid.UUID = None,
        description: str = None
    ) -> bool:
        """
        Use credit from package.

        Returns True if successful.
        """
        if not self.is_active:
            return False

        if self.remaining_credit is None or self.remaining_credit < amount:
            return False

        self.remaining_credit -= amount
        self.total_used_credit += amount
        self.last_used_at = timezone.now()
        self.last_usage_reference_type = reference_type
        self.last_usage_reference_id = reference_id

        # Add to history
        self.usage_history.append({
            'date': timezone.now().isoformat(),
            'type': 'credit',
            'amount': float(amount),
            'remaining': float(self.remaining_credit),
            'reference_type': reference_type,
            'reference_id': str(reference_id) if reference_id else None,
            'description': description,
        })

        # Check if depleted
        if self.remaining_credit <= Decimal('0'):
            self.status = UserPackageStatus.DEPLETED
            self.status_changed_at = timezone.now()
            self.status_reason = 'Credit depleted'

        return True

    def use_hours(
        self,
        hours: Decimal,
        reference_type: str = None,
        reference_id: uuid.UUID = None,
        description: str = None
    ) -> bool:
        """
        Use flight hours from package.

        Returns True if successful.
        """
        if not self.is_active:
            return False

        if self.remaining_hours is None or self.remaining_hours < hours:
            return False

        self.remaining_hours -= hours
        self.total_used_hours += hours
        self.last_used_at = timezone.now()
        self.last_usage_reference_type = reference_type
        self.last_usage_reference_id = reference_id

        # Add to history
        self.usage_history.append({
            'date': timezone.now().isoformat(),
            'type': 'hours',
            'amount': float(hours),
            'remaining': float(self.remaining_hours),
            'reference_type': reference_type,
            'reference_id': str(reference_id) if reference_id else None,
            'description': description,
        })

        # Check if depleted
        if self.remaining_hours <= Decimal('0'):
            self.status = UserPackageStatus.DEPLETED
            self.status_changed_at = timezone.now()
            self.status_reason = 'Hours depleted'

        return True

    def expire(self, reason: str = 'Package expired') -> None:
        """Mark package as expired."""
        self.status = UserPackageStatus.EXPIRED
        self.status_changed_at = timezone.now()
        self.status_reason = reason

    def cancel(self, reason: str = None) -> None:
        """Cancel package."""
        self.status = UserPackageStatus.CANCELLED
        self.status_changed_at = timezone.now()
        self.status_reason = reason
