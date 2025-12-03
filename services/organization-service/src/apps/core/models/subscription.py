# services/organization-service/src/apps/core/models/subscription.py
"""
Subscription Models

Subscription plans and history for organization billing.
"""

import uuid
from decimal import Decimal
from django.db import models
from django.utils import timezone


class SubscriptionPlan(models.Model):
    """
    Subscription plan model defining features and limits.

    Plans are used to determine what features and limits
    organizations have access to.
    """

    # Primary Key
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    # Identification
    code = models.CharField(
        max_length=50,
        unique=True,
        help_text="Unique plan code (e.g., 'starter', 'professional')"
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)

    # Pricing
    price_monthly = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Monthly price"
    )
    price_yearly = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Yearly price (usually discounted)"
    )
    currency = models.CharField(max_length=3, default='USD')

    # Limits (-1 means unlimited)
    max_users = models.IntegerField(
        null=True,
        help_text="Maximum users (-1 for unlimited)"
    )
    max_aircraft = models.IntegerField(
        null=True,
        help_text="Maximum aircraft (-1 for unlimited)"
    )
    max_students = models.IntegerField(
        null=True,
        help_text="Maximum students (-1 for unlimited)"
    )
    max_locations = models.IntegerField(
        null=True,
        help_text="Maximum locations (-1 for unlimited)"
    )
    storage_limit_gb = models.IntegerField(
        null=True,
        help_text="Storage limit in GB (-1 for unlimited)"
    )

    # Features
    features = models.JSONField(
        default=dict,
        blank=True,
        help_text="""Feature flags:
        {
            "api_access": true,
            "white_label": false,
            "advanced_reporting": true,
            "custom_domain": false,
            "priority_support": false,
            "sla_uptime": 99.5
        }"""
    )

    # Status
    is_active = models.BooleanField(
        default=True,
        help_text="Whether plan is currently available"
    )
    is_public = models.BooleanField(
        default=True,
        help_text="Whether plan is publicly visible"
    )

    # Trial Settings
    trial_days = models.IntegerField(
        default=14,
        help_text="Number of trial days"
    )

    # Display
    display_order = models.IntegerField(default=0)
    badge_text = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Badge text (e.g., 'Popular', 'Best Value')"
    )
    badge_color = models.CharField(
        max_length=7,
        blank=True,
        null=True,
        help_text="Badge color in hex"
    )

    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'subscription_plans'
        ordering = ['display_order', 'price_monthly']

    def __str__(self):
        return f"{self.name} (${self.price_monthly}/mo)"

    @property
    def yearly_savings(self) -> Decimal:
        """Calculate yearly savings compared to monthly."""
        if not self.price_yearly:
            return Decimal('0.00')
        monthly_total = self.price_monthly * 12
        return monthly_total - self.price_yearly

    @property
    def yearly_discount_percent(self) -> Decimal:
        """Calculate yearly discount percentage."""
        if not self.price_yearly or self.price_monthly == 0:
            return Decimal('0.00')
        monthly_total = self.price_monthly * 12
        return ((monthly_total - self.price_yearly) / monthly_total * 100).quantize(
            Decimal('0.01')
        )

    def has_feature(self, feature_name: str) -> bool:
        """Check if plan has a specific feature."""
        return self.features.get(feature_name, False)

    def get_limit(self, resource: str) -> int:
        """Get limit for a specific resource."""
        limits = {
            'users': self.max_users,
            'aircraft': self.max_aircraft,
            'students': self.max_students,
            'locations': self.max_locations,
            'storage': self.storage_limit_gb,
        }
        return limits.get(resource, 0) or -1

    @classmethod
    def get_trial_plan(cls):
        """Get the default trial plan."""
        return cls.objects.filter(code='trial', is_active=True).first()

    @classmethod
    def get_public_plans(cls):
        """Get all public, active plans."""
        return cls.objects.filter(is_active=True, is_public=True).order_by('display_order')


class SubscriptionHistory(models.Model):
    """
    Subscription history for tracking plan changes.

    Maintains a complete history of subscription changes
    for billing and audit purposes.
    """

    class ChangeType(models.TextChoices):
        CREATED = 'created', 'Subscription Created'
        UPGRADED = 'upgraded', 'Plan Upgraded'
        DOWNGRADED = 'downgraded', 'Plan Downgraded'
        RENEWED = 'renewed', 'Subscription Renewed'
        CANCELLED = 'cancelled', 'Subscription Cancelled'
        REACTIVATED = 'reactivated', 'Subscription Reactivated'
        TRIAL_STARTED = 'trial_started', 'Trial Started'
        TRIAL_ENDED = 'trial_ended', 'Trial Ended'
        TRIAL_CONVERTED = 'trial_converted', 'Trial Converted to Paid'

    # Primary Key
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    # References
    organization = models.ForeignKey(
        'Organization',
        on_delete=models.CASCADE,
        related_name='subscription_history'
    )
    from_plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+'
    )
    to_plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+'
    )

    # Change Details
    change_type = models.CharField(
        max_length=20,
        choices=ChangeType.choices
    )
    reason = models.TextField(blank=True, null=True)

    # Billing
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    currency = models.CharField(max_length=3, default='USD')
    billing_period_start = models.DateTimeField(blank=True, null=True)
    billing_period_end = models.DateTimeField(blank=True, null=True)

    # Payment Reference
    payment_reference = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="External payment reference (Stripe ID, etc.)"
    )

    # Metadata
    metadata = models.JSONField(default=dict, blank=True)

    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.UUIDField(blank=True, null=True)

    class Meta:
        db_table = 'subscription_history'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organization', '-created_at']),
            models.Index(fields=['change_type', 'created_at']),
        ]

    def __str__(self):
        return f"{self.organization.name} - {self.change_type} at {self.created_at}"

    @classmethod
    def log_change(
        cls,
        organization,
        change_type: str,
        from_plan=None,
        to_plan=None,
        reason: str = None,
        amount: Decimal = Decimal('0.00'),
        created_by: uuid.UUID = None,
        **metadata
    ):
        """Create a subscription history entry."""
        return cls.objects.create(
            organization=organization,
            change_type=change_type,
            from_plan=from_plan,
            to_plan=to_plan,
            reason=reason,
            amount=amount,
            created_by=created_by,
            metadata=metadata
        )
