# services/organization-service/src/apps/core/services/subscription_service.py
"""
Subscription Service

Business logic for subscription management including:
- Plan changes (upgrade/downgrade)
- Trial management
- Usage limit checking
- Subscription history
"""

import logging
from typing import Optional, List, Dict, Any
from decimal import Decimal
from datetime import timedelta
from uuid import UUID

from django.db import transaction
from django.utils import timezone
from django.core.cache import cache

from apps.core.models import (
    Organization,
    SubscriptionPlan,
    SubscriptionHistory,
)

logger = logging.getLogger(__name__)


# ==================== EXCEPTIONS ====================

class SubscriptionError(Exception):
    """Base exception for subscription errors."""
    pass


class PlanNotFoundError(SubscriptionError):
    """Raised when subscription plan is not found."""
    pass


class SubscriptionLimitError(SubscriptionError):
    """Raised when subscription limit prevents action."""
    pass


class DowngradeNotAllowedError(SubscriptionError):
    """Raised when downgrade is not allowed due to usage."""
    pass


# ==================== SERVICE ====================

class SubscriptionService:
    """
    Service for subscription management.

    Handles plan changes, trial management, and limit checking.
    """

    CACHE_TTL = 300  # 5 minutes
    CACHE_PREFIX = 'subscription'

    def __init__(self):
        self._event_publisher = None

    # ==================== PLAN MANAGEMENT ====================

    def get_plan(self, plan_id: UUID) -> Optional[SubscriptionPlan]:
        """Get subscription plan by ID."""
        try:
            return SubscriptionPlan.objects.get(id=plan_id)
        except SubscriptionPlan.DoesNotExist:
            return None

    def get_plan_by_code(self, code: str) -> Optional[SubscriptionPlan]:
        """Get subscription plan by code."""
        cache_key = f"{self.CACHE_PREFIX}:plan:{code}"
        cached = cache.get(cache_key)
        if cached:
            return cached

        try:
            plan = SubscriptionPlan.objects.get(code=code, is_active=True)
            cache.set(cache_key, plan, self.CACHE_TTL)
            return plan
        except SubscriptionPlan.DoesNotExist:
            return None

    def list_public_plans(self) -> List[SubscriptionPlan]:
        """Get all public, active plans."""
        cache_key = f"{self.CACHE_PREFIX}:public_plans"
        cached = cache.get(cache_key)
        if cached:
            return cached

        plans = list(SubscriptionPlan.get_public_plans())
        cache.set(cache_key, plans, self.CACHE_TTL)
        return plans

    # ==================== SUBSCRIPTION OPERATIONS ====================

    def change_plan(
        self,
        organization_id: UUID,
        plan_code: str,
        changed_by: UUID,
        payment_reference: str = None,
        billing_cycle: str = 'monthly'
    ) -> Organization:
        """
        Change organization's subscription plan.

        Args:
            organization_id: Organization UUID
            plan_code: New plan code
            changed_by: User making the change
            payment_reference: External payment reference
            billing_cycle: 'monthly' or 'yearly'

        Returns:
            Updated Organization instance

        Raises:
            PlanNotFoundError: If plan doesn't exist
            DowngradeNotAllowedError: If downgrade exceeds limits
        """
        # Get organization
        try:
            org = Organization.objects.get(id=organization_id, deleted_at__isnull=True)
        except Organization.DoesNotExist:
            raise SubscriptionError(f"Organization {organization_id} not found")

        # Get new plan
        new_plan = self.get_plan_by_code(plan_code)
        if not new_plan:
            raise PlanNotFoundError(f"Plan {plan_code} not found")

        # Get current plan
        old_plan = org.subscription_plan

        # Determine change type
        change_type = self._determine_change_type(old_plan, new_plan)

        # Check if downgrade is allowed
        if change_type == 'downgraded':
            self._check_downgrade_allowed(org, new_plan)

        with transaction.atomic():
            # Calculate billing amount
            amount = (
                new_plan.price_yearly if billing_cycle == 'yearly'
                else new_plan.price_monthly
            )

            # Update organization
            org.subscription_plan = new_plan
            org.subscription_status = Organization.SubscriptionStatus.ACTIVE
            org.subscription_started_at = timezone.now()

            # Set subscription end date
            if billing_cycle == 'yearly':
                org.subscription_ends_at = timezone.now() + timedelta(days=365)
            else:
                org.subscription_ends_at = timezone.now() + timedelta(days=30)

            # Update limits from plan
            org.max_users = new_plan.max_users if new_plan.max_users else -1
            org.max_aircraft = new_plan.max_aircraft if new_plan.max_aircraft else -1
            org.max_students = new_plan.max_students if new_plan.max_students else -1
            org.max_locations = new_plan.max_locations if new_plan.max_locations else -1
            org.storage_limit_gb = new_plan.storage_limit_gb if new_plan.storage_limit_gb else -1
            org.features = new_plan.features

            # Clear trial if converting
            if org.subscription_status == Organization.SubscriptionStatus.TRIAL:
                org.trial_ends_at = None

            org.save()

            # Log history
            SubscriptionHistory.log_change(
                organization=org,
                change_type=change_type,
                from_plan=old_plan,
                to_plan=new_plan,
                amount=amount,
                created_by=changed_by,
                billing_cycle=billing_cycle,
                payment_reference=payment_reference,
            )

            logger.info(
                f"Changed subscription for {org.name}: "
                f"{old_plan.code if old_plan else 'none'} -> {new_plan.code}"
            )

            # Publish event
            self._publish_event('organization.subscription_changed', {
                'organization_id': str(org.id),
                'old_plan': old_plan.code if old_plan else None,
                'new_plan': new_plan.code,
                'change_type': change_type,
                'changed_by': str(changed_by),
            })

            return org

    def cancel_subscription(
        self,
        organization_id: UUID,
        cancelled_by: UUID,
        reason: str = None,
        end_immediately: bool = False
    ) -> Organization:
        """
        Cancel organization's subscription.

        Args:
            organization_id: Organization UUID
            cancelled_by: User cancelling
            reason: Cancellation reason
            end_immediately: Whether to end immediately or at period end

        Returns:
            Updated Organization instance
        """
        try:
            org = Organization.objects.get(id=organization_id, deleted_at__isnull=True)
        except Organization.DoesNotExist:
            raise SubscriptionError(f"Organization {organization_id} not found")

        with transaction.atomic():
            old_plan = org.subscription_plan

            if end_immediately:
                org.subscription_status = Organization.SubscriptionStatus.CANCELLED
                org.subscription_ends_at = timezone.now()
            else:
                # Keep access until end of billing period
                org.subscription_status = Organization.SubscriptionStatus.CANCELLED

            org.save()

            # Log history
            SubscriptionHistory.log_change(
                organization=org,
                change_type=SubscriptionHistory.ChangeType.CANCELLED,
                from_plan=old_plan,
                reason=reason,
                created_by=cancelled_by,
            )

            logger.info(f"Cancelled subscription for {org.name}")

            self._publish_event('organization.subscription_cancelled', {
                'organization_id': str(org.id),
                'plan': old_plan.code if old_plan else None,
                'reason': reason,
                'cancelled_by': str(cancelled_by),
                'immediate': end_immediately,
            })

            return org

    def reactivate_subscription(
        self,
        organization_id: UUID,
        reactivated_by: UUID,
        plan_code: str = None
    ) -> Organization:
        """
        Reactivate a cancelled subscription.

        Args:
            organization_id: Organization UUID
            reactivated_by: User reactivating
            plan_code: Optional new plan code

        Returns:
            Updated Organization instance
        """
        try:
            org = Organization.objects.get(id=organization_id, deleted_at__isnull=True)
        except Organization.DoesNotExist:
            raise SubscriptionError(f"Organization {organization_id} not found")

        if org.subscription_status not in [
            Organization.SubscriptionStatus.CANCELLED,
            Organization.SubscriptionStatus.SUSPENDED
        ]:
            raise SubscriptionError("Subscription is not cancelled or suspended")

        # Get plan
        if plan_code:
            plan = self.get_plan_by_code(plan_code)
            if not plan:
                raise PlanNotFoundError(f"Plan {plan_code} not found")
        else:
            plan = org.subscription_plan

        with transaction.atomic():
            org.subscription_plan = plan
            org.subscription_status = Organization.SubscriptionStatus.ACTIVE
            org.subscription_started_at = timezone.now()
            org.subscription_ends_at = timezone.now() + timedelta(days=30)

            # Update limits
            if plan:
                org.max_users = plan.max_users if plan.max_users else -1
                org.max_aircraft = plan.max_aircraft if plan.max_aircraft else -1
                org.max_students = plan.max_students if plan.max_students else -1
                org.max_locations = plan.max_locations if plan.max_locations else -1
                org.storage_limit_gb = plan.storage_limit_gb if plan.storage_limit_gb else -1
                org.features = plan.features

            org.save()

            # Log history
            SubscriptionHistory.log_change(
                organization=org,
                change_type=SubscriptionHistory.ChangeType.REACTIVATED,
                to_plan=plan,
                created_by=reactivated_by,
            )

            logger.info(f"Reactivated subscription for {org.name}")

            self._publish_event('organization.subscription_reactivated', {
                'organization_id': str(org.id),
                'plan': plan.code if plan else None,
                'reactivated_by': str(reactivated_by),
            })

            return org

    # ==================== TRIAL MANAGEMENT ====================

    def start_trial(
        self,
        organization_id: UUID,
        trial_days: int = 14
    ) -> Organization:
        """
        Start or restart trial for an organization.

        Args:
            organization_id: Organization UUID
            trial_days: Number of trial days

        Returns:
            Updated Organization instance
        """
        try:
            org = Organization.objects.get(id=organization_id, deleted_at__isnull=True)
        except Organization.DoesNotExist:
            raise SubscriptionError(f"Organization {organization_id} not found")

        trial_plan = SubscriptionPlan.get_trial_plan()

        with transaction.atomic():
            org.subscription_plan = trial_plan
            org.subscription_status = Organization.SubscriptionStatus.TRIAL
            org.trial_ends_at = timezone.now() + timedelta(days=trial_days)

            if trial_plan:
                org.max_users = trial_plan.max_users if trial_plan.max_users else 5
                org.max_aircraft = trial_plan.max_aircraft if trial_plan.max_aircraft else 2
                org.max_students = trial_plan.max_students if trial_plan.max_students else 10
                org.max_locations = trial_plan.max_locations if trial_plan.max_locations else 1
                org.storage_limit_gb = trial_plan.storage_limit_gb if trial_plan.storage_limit_gb else 5
                org.features = trial_plan.features

            org.save()

            # Log history
            SubscriptionHistory.log_change(
                organization=org,
                change_type=SubscriptionHistory.ChangeType.TRIAL_STARTED,
                to_plan=trial_plan,
                trial_days=trial_days,
            )

            logger.info(f"Started trial for {org.name}: {trial_days} days")

            return org

    def extend_trial(
        self,
        organization_id: UUID,
        extra_days: int,
        extended_by: UUID,
        reason: str = None
    ) -> Organization:
        """
        Extend trial period for an organization.

        Args:
            organization_id: Organization UUID
            extra_days: Number of days to add
            extended_by: User extending
            reason: Reason for extension

        Returns:
            Updated Organization instance
        """
        try:
            org = Organization.objects.get(id=organization_id, deleted_at__isnull=True)
        except Organization.DoesNotExist:
            raise SubscriptionError(f"Organization {organization_id} not found")

        if org.subscription_status != Organization.SubscriptionStatus.TRIAL:
            raise SubscriptionError("Organization is not on trial")

        with transaction.atomic():
            if org.trial_ends_at:
                org.trial_ends_at = org.trial_ends_at + timedelta(days=extra_days)
            else:
                org.trial_ends_at = timezone.now() + timedelta(days=extra_days)

            org.save()

            # Log in metadata
            SubscriptionHistory.log_change(
                organization=org,
                change_type=SubscriptionHistory.ChangeType.TRIAL_STARTED,
                reason=f"Trial extended by {extra_days} days: {reason}",
                created_by=extended_by,
                extra_days=extra_days,
            )

            logger.info(f"Extended trial for {org.name} by {extra_days} days")

            return org

    def convert_trial(
        self,
        organization_id: UUID,
        plan_code: str,
        converted_by: UUID,
        payment_reference: str = None
    ) -> Organization:
        """
        Convert trial to paid subscription.

        Args:
            organization_id: Organization UUID
            plan_code: Plan to convert to
            converted_by: User converting
            payment_reference: Payment reference

        Returns:
            Updated Organization instance
        """
        try:
            org = Organization.objects.get(id=organization_id, deleted_at__isnull=True)
        except Organization.DoesNotExist:
            raise SubscriptionError(f"Organization {organization_id} not found")

        if org.subscription_status != Organization.SubscriptionStatus.TRIAL:
            raise SubscriptionError("Organization is not on trial")

        # Use change_plan for the actual conversion
        org = self.change_plan(
            organization_id=organization_id,
            plan_code=plan_code,
            changed_by=converted_by,
            payment_reference=payment_reference
        )

        # Log conversion specifically
        SubscriptionHistory.log_change(
            organization=org,
            change_type=SubscriptionHistory.ChangeType.TRIAL_CONVERTED,
            to_plan=org.subscription_plan,
            created_by=converted_by,
        )

        logger.info(f"Converted trial to {plan_code} for {org.name}")

        self._publish_event('organization.trial_converted', {
            'organization_id': str(org.id),
            'plan': plan_code,
            'converted_by': str(converted_by),
        })

        return org

    # ==================== SUBSCRIPTION STATUS ====================

    def get_subscription_status(self, organization_id: UUID) -> Dict[str, Any]:
        """
        Get detailed subscription status.

        Args:
            organization_id: Organization UUID

        Returns:
            Dict with subscription details
        """
        try:
            org = Organization.objects.select_related('subscription_plan').get(
                id=organization_id,
                deleted_at__isnull=True
            )
        except Organization.DoesNotExist:
            raise SubscriptionError(f"Organization {organization_id} not found")

        plan = org.subscription_plan

        status = {
            'organization_id': str(org.id),
            'status': org.subscription_status,
            'plan': {
                'code': plan.code if plan else None,
                'name': plan.name if plan else None,
                'features': plan.features if plan else {},
            } if plan else None,
            'is_trial': org.is_trial,
            'is_active': org.is_subscription_active,
            'limits': {
                'users': org.max_users,
                'aircraft': org.max_aircraft,
                'students': org.max_students,
                'locations': org.max_locations,
                'storage_gb': org.storage_limit_gb,
            },
            'features': org.features,
            'dates': {
                'started_at': org.subscription_started_at.isoformat() if org.subscription_started_at else None,
                'ends_at': org.subscription_ends_at.isoformat() if org.subscription_ends_at else None,
                'trial_ends_at': org.trial_ends_at.isoformat() if org.trial_ends_at else None,
            },
        }

        # Add trial-specific info
        if org.is_trial:
            status['trial'] = {
                'days_remaining': org.days_until_trial_end,
                'is_expired': org.is_trial_expired,
            }

        return status

    def get_subscription_history(
        self,
        organization_id: UUID,
        limit: int = 50
    ) -> List[SubscriptionHistory]:
        """
        Get subscription history for an organization.

        Args:
            organization_id: Organization UUID
            limit: Maximum records to return

        Returns:
            List of SubscriptionHistory instances
        """
        return list(
            SubscriptionHistory.objects.filter(
                organization_id=organization_id
            ).select_related(
                'from_plan', 'to_plan'
            ).order_by('-created_at')[:limit]
        )

    # ==================== PRIVATE METHODS ====================

    def _determine_change_type(
        self,
        old_plan: SubscriptionPlan,
        new_plan: SubscriptionPlan
    ) -> str:
        """Determine the type of plan change."""
        if not old_plan:
            return SubscriptionHistory.ChangeType.CREATED

        if old_plan.code == 'trial':
            return SubscriptionHistory.ChangeType.TRIAL_CONVERTED

        old_price = old_plan.price_monthly
        new_price = new_plan.price_monthly

        if new_price > old_price:
            return SubscriptionHistory.ChangeType.UPGRADED
        elif new_price < old_price:
            return SubscriptionHistory.ChangeType.DOWNGRADED
        else:
            return SubscriptionHistory.ChangeType.RENEWED

    def _check_downgrade_allowed(
        self,
        org: Organization,
        new_plan: SubscriptionPlan
    ) -> None:
        """Check if downgrade is allowed based on current usage."""
        # In production, would check actual usage from other services
        # For now, just check location count

        from apps.core.models import Location
        location_count = Location.objects.filter(
            organization_id=org.id,
            is_active=True
        ).count()

        if new_plan.max_locations and new_plan.max_locations != -1:
            if location_count > new_plan.max_locations:
                raise DowngradeNotAllowedError(
                    f"Cannot downgrade: You have {location_count} locations "
                    f"but the new plan only allows {new_plan.max_locations}. "
                    "Please deactivate some locations first."
                )

        # Similar checks would be done for users, aircraft, etc.

    def _publish_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Publish an event."""
        try:
            from apps.core.events import publish_event
            publish_event(event_type, data)
        except Exception as e:
            logger.error(f"Failed to publish event {event_type}: {e}")
