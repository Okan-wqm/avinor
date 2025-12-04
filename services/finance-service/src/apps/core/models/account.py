# services/finance-service/src/apps/core/models/account.py
"""
Account Model

Financial account management for users and organizations.
"""

import uuid
from decimal import Decimal
from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator


class AccountType(models.TextChoices):
    """Account type choices."""
    STUDENT = 'student', 'Student'
    PILOT = 'pilot', 'Pilot'
    INSTRUCTOR = 'instructor', 'Instructor'
    COMPANY = 'company', 'Company'
    ORGANIZATION = 'organization', 'Organization'


class AccountStatus(models.TextChoices):
    """Account status choices."""
    ACTIVE = 'active', 'Active'
    SUSPENDED = 'suspended', 'Suspended'
    CLOSED = 'closed', 'Closed'
    PENDING = 'pending', 'Pending Approval'


class Account(models.Model):
    """
    Financial account model.

    Tracks balances, credit limits, and financial settings
    for users and organizations.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    organization_id = models.UUIDField(
        db_index=True,
        help_text='Organization this account belongs to'
    )

    # Account Owner
    account_type = models.CharField(
        max_length=20,
        choices=AccountType.choices,
        default=AccountType.STUDENT
    )
    owner_id = models.UUIDField(
        db_index=True,
        help_text='User or company ID'
    )
    owner_type = models.CharField(
        max_length=20,
        default='user',
        help_text='user or company'
    )
    owner_name = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )
    owner_email = models.EmailField(
        blank=True,
        null=True
    )

    # Account Number
    account_number = models.CharField(
        max_length=50,
        unique=True,
        db_index=True
    )

    # Balance
    balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text='Current account balance (positive = credit, negative = debt)'
    )
    credit_limit = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text='Maximum credit allowed'
    )
    pending_charges = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text='Pending charges not yet finalized'
    )

    # Currency
    currency = models.CharField(
        max_length=3,
        default='USD'
    )

    # Status
    status = models.CharField(
        max_length=20,
        choices=AccountStatus.choices,
        default=AccountStatus.ACTIVE,
        db_index=True
    )

    # Settings
    auto_charge = models.BooleanField(
        default=True,
        help_text='Automatically charge after flights'
    )
    require_prepayment = models.BooleanField(
        default=False,
        help_text='Require positive balance before booking'
    )
    minimum_balance = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text='Minimum balance to maintain'
    )
    low_balance_alert = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('100.00'),
        help_text='Alert threshold for low balance'
    )

    # Payment Terms
    payment_terms_days = models.IntegerField(
        default=30,
        help_text='Default invoice payment terms in days'
    )
    default_payment_method_id = models.UUIDField(
        blank=True,
        null=True,
        help_text='Default payment method for this account'
    )

    # Statistics
    total_charged = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )
    total_paid = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )
    total_refunded = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )
    total_credits = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text='Total credits/adjustments received'
    )

    # Activity Tracking
    last_transaction_at = models.DateTimeField(
        blank=True,
        null=True
    )
    last_payment_at = models.DateTimeField(
        blank=True,
        null=True
    )
    last_charge_at = models.DateTimeField(
        blank=True,
        null=True
    )

    # Billing Address
    billing_address_line1 = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )
    billing_address_line2 = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )
    billing_city = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )
    billing_state = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )
    billing_postal_code = models.CharField(
        max_length=20,
        blank=True,
        null=True
    )
    billing_country = models.CharField(
        max_length=2,
        default='US'
    )
    tax_id = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text='Tax identification number'
    )

    # Notes
    notes = models.TextField(
        blank=True,
        null=True
    )
    internal_notes = models.TextField(
        blank=True,
        null=True,
        help_text='Internal notes not visible to account holder'
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'accounts'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organization_id', 'owner_id']),
            models.Index(fields=['organization_id', 'status']),
            models.Index(fields=['balance']),
        ]

    def __str__(self):
        return f"{self.account_number} - {self.owner_name or self.owner_id}"

    @property
    def available_balance(self) -> Decimal:
        """Calculate available balance including credit limit."""
        return self.balance + self.credit_limit - self.pending_charges

    @property
    def is_low_balance(self) -> bool:
        """Check if balance is below alert threshold."""
        return self.balance < self.low_balance_alert

    @property
    def is_overdrawn(self) -> bool:
        """Check if account is overdrawn beyond credit limit."""
        return self.balance < -self.credit_limit

    @property
    def outstanding_balance(self) -> Decimal:
        """Calculate outstanding balance (negative balance)."""
        if self.balance < Decimal('0'):
            return abs(self.balance)
        return Decimal('0.00')

    @property
    def available_credit(self) -> Decimal:
        """Calculate remaining available credit."""
        if self.balance < Decimal('0'):
            return max(Decimal('0'), self.credit_limit + self.balance)
        return self.credit_limit

    def can_charge(self, amount: Decimal) -> bool:
        """Check if amount can be charged to account."""
        return self.available_balance >= amount

    def charge(self, amount: Decimal) -> None:
        """Deduct amount from account balance."""
        self.balance -= amount
        self.total_charged += amount
        self.last_charge_at = timezone.now()
        self.last_transaction_at = timezone.now()

    def credit(self, amount: Decimal) -> None:
        """Add amount to account balance."""
        self.balance += amount
        self.total_paid += amount
        self.last_payment_at = timezone.now()
        self.last_transaction_at = timezone.now()

    def add_credit(self, amount: Decimal) -> None:
        """Add credit/adjustment to account."""
        self.balance += amount
        self.total_credits += amount
        self.last_transaction_at = timezone.now()

    def refund(self, amount: Decimal) -> None:
        """Process refund to account."""
        self.balance += amount
        self.total_refunded += amount
        self.last_transaction_at = timezone.now()

    def add_pending_charge(self, amount: Decimal) -> None:
        """Add pending charge (not yet finalized)."""
        self.pending_charges += amount

    def finalize_pending_charge(self, amount: Decimal) -> None:
        """Convert pending charge to actual charge."""
        self.pending_charges -= amount
        self.charge(amount)

    def release_pending_charge(self, amount: Decimal) -> None:
        """Release pending charge (cancelled)."""
        self.pending_charges = max(Decimal('0'), self.pending_charges - amount)

    def get_billing_address(self) -> dict:
        """Get formatted billing address."""
        return {
            'line1': self.billing_address_line1,
            'line2': self.billing_address_line2,
            'city': self.billing_city,
            'state': self.billing_state,
            'postal_code': self.billing_postal_code,
            'country': self.billing_country,
        }

    @classmethod
    def generate_account_number(cls, organization_id) -> str:
        """Generate unique account number."""
        count = cls.objects.filter(organization_id=organization_id).count() + 1
        return f"ACC-{count:08d}"
