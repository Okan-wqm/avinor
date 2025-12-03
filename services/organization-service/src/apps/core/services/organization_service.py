# services/organization-service/src/apps/core/services/organization_service.py
"""
Organization Service

Business logic for organization management including:
- Organization CRUD operations
- Branding management
- Settings management
- Usage statistics
- Feature checking
"""

import logging
import re
from typing import Optional, List, Dict, Any
from datetime import timedelta
from uuid import UUID

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.text import slugify
from django.core.cache import cache

from apps.core.models import (
    Organization,
    OrganizationSetting,
    SubscriptionPlan,
    Location,
)

logger = logging.getLogger(__name__)


# ==================== EXCEPTIONS ====================

class OrganizationError(Exception):
    """Base exception for organization errors."""
    pass


class OrganizationNotFoundError(OrganizationError):
    """Raised when organization is not found."""
    pass


class OrganizationValidationError(OrganizationError):
    """Raised when organization validation fails."""
    pass


class OrganizationLimitExceededError(OrganizationError):
    """Raised when organization limit is exceeded."""
    pass


class SlugAlreadyExistsError(OrganizationError):
    """Raised when slug already exists."""
    pass


class DomainAlreadyExistsError(OrganizationError):
    """Raised when custom domain already exists."""
    pass


# ==================== SERVICE ====================

class OrganizationService:
    """
    Service for organization management.

    Provides comprehensive organization management including
    creation, updates, settings, branding, and usage tracking.
    """

    CACHE_TTL = 300  # 5 minutes
    CACHE_PREFIX = 'org'

    def __init__(self):
        self._event_publisher = None

    @property
    def event_publisher(self):
        """Lazy load event publisher."""
        if self._event_publisher is None:
            from apps.core.events import get_publisher
            self._event_publisher = get_publisher()
        return self._event_publisher

    # ==================== CRUD OPERATIONS ====================

    def create_organization(
        self,
        name: str,
        email: str,
        country_code: str,
        admin_user_id: UUID,
        organization_type: str = 'flight_school',
        regulatory_authority: str = 'EASA',
        **kwargs
    ) -> Organization:
        """
        Create a new organization.

        Args:
            name: Organization name
            email: Primary contact email
            country_code: ISO 2-letter country code
            admin_user_id: User ID of the admin creating the org
            organization_type: Type of organization
            regulatory_authority: Regulatory authority
            **kwargs: Additional organization fields

        Returns:
            Created Organization instance

        Raises:
            OrganizationValidationError: If validation fails
            SlugAlreadyExistsError: If slug already exists
        """
        # Validate inputs
        self._validate_email(email)
        self._validate_country_code(country_code)

        # Generate unique slug
        slug = self._generate_unique_slug(name)

        # Get trial plan
        trial_plan = SubscriptionPlan.get_trial_plan()

        with transaction.atomic():
            # Create organization
            org = Organization.objects.create(
                name=name,
                slug=slug,
                email=email,
                country_code=country_code.upper(),
                organization_type=organization_type,
                regulatory_authority=regulatory_authority,
                subscription_plan=trial_plan,
                subscription_status=Organization.SubscriptionStatus.TRIAL,
                trial_ends_at=timezone.now() + timedelta(days=trial_plan.trial_days if trial_plan else 14),
                max_users=trial_plan.max_users if trial_plan else 5,
                max_aircraft=trial_plan.max_aircraft if trial_plan else 2,
                max_students=trial_plan.max_students if trial_plan else 10,
                max_locations=trial_plan.max_locations if trial_plan else 1,
                storage_limit_gb=trial_plan.storage_limit_gb if trial_plan else 5,
                features=trial_plan.features if trial_plan else {},
                status=Organization.Status.ACTIVE,
                created_by=admin_user_id,
                **kwargs
            )

            # Create default settings
            self._create_default_settings(org)

            logger.info(f"Created organization: {org.name} ({org.id})")

            # Publish event
            self._publish_event('organization.created', {
                'organization_id': str(org.id),
                'name': org.name,
                'slug': org.slug,
                'admin_user_id': str(admin_user_id),
            })

            return org

    def get_organization(
        self,
        organization_id: UUID,
        include_deleted: bool = False
    ) -> Optional[Organization]:
        """
        Get organization by ID.

        Args:
            organization_id: Organization UUID
            include_deleted: Whether to include soft-deleted organizations

        Returns:
            Organization instance or None
        """
        # Try cache first
        cache_key = f"{self.CACHE_PREFIX}:{organization_id}"
        cached = cache.get(cache_key)
        if cached and not include_deleted:
            return cached

        try:
            queryset = Organization.objects.all()
            if not include_deleted:
                queryset = queryset.filter(deleted_at__isnull=True)

            org = queryset.get(id=organization_id)

            # Cache if not deleted
            if not org.is_deleted:
                cache.set(cache_key, org, self.CACHE_TTL)

            return org
        except Organization.DoesNotExist:
            return None

    def get_organization_by_slug(self, slug: str) -> Optional[Organization]:
        """Get organization by slug."""
        cache_key = f"{self.CACHE_PREFIX}:slug:{slug}"
        cached = cache.get(cache_key)
        if cached:
            return cached

        try:
            org = Organization.objects.get(slug=slug, deleted_at__isnull=True)
            cache.set(cache_key, org, self.CACHE_TTL)
            return org
        except Organization.DoesNotExist:
            return None

    def get_organization_by_domain(self, domain: str) -> Optional[Organization]:
        """Get organization by custom domain."""
        cache_key = f"{self.CACHE_PREFIX}:domain:{domain}"
        cached = cache.get(cache_key)
        if cached:
            return cached

        try:
            org = Organization.objects.get(
                custom_domain=domain,
                custom_domain_verified=True,
                deleted_at__isnull=True
            )
            cache.set(cache_key, org, self.CACHE_TTL)
            return org
        except Organization.DoesNotExist:
            return None

    def update_organization(
        self,
        organization_id: UUID,
        data: Dict[str, Any],
        updated_by: UUID
    ) -> Organization:
        """
        Update organization.

        Args:
            organization_id: Organization UUID
            data: Fields to update
            updated_by: User ID making the update

        Returns:
            Updated Organization instance

        Raises:
            OrganizationNotFoundError: If organization not found
            OrganizationValidationError: If validation fails
        """
        org = self.get_organization(organization_id)
        if not org:
            raise OrganizationNotFoundError(f"Organization {organization_id} not found")

        # Define allowed fields
        allowed_fields = {
            'name', 'legal_name', 'email', 'phone', 'fax', 'website',
            'address_line1', 'address_line2', 'city', 'state_province',
            'postal_code', 'country_code', 'latitude', 'longitude',
            'timezone', 'date_format', 'time_format', 'currency_code', 'language',
            'fiscal_year_start_month', 'week_start_day',
            'default_booking_duration_minutes', 'min_booking_notice_hours',
            'max_booking_advance_days', 'cancellation_notice_hours',
            'late_cancellation_fee_percent', 'no_show_fee_percent',
            'default_preflight_minutes', 'default_postflight_minutes',
            'time_tracking_method', 'auto_charge_flights',
            'require_positive_balance', 'minimum_balance_warning',
            'payment_terms_days', 'regulatory_authority',
            'ato_certificate_number', 'ato_certificate_expiry', 'ato_approval_type',
            'metadata'
        }

        # Filter to allowed fields
        update_data = {k: v for k, v in data.items() if k in allowed_fields}

        # Validate specific fields
        if 'email' in update_data:
            self._validate_email(update_data['email'])
        if 'country_code' in update_data:
            self._validate_country_code(update_data['country_code'])
            update_data['country_code'] = update_data['country_code'].upper()

        # Track changed fields
        changed_fields = []
        for field, value in update_data.items():
            if getattr(org, field) != value:
                changed_fields.append(field)
                setattr(org, field, value)

        if changed_fields:
            org.updated_by = updated_by
            org.save()

            # Invalidate cache
            self._invalidate_cache(org)

            logger.info(f"Updated organization {org.id}: {changed_fields}")

            # Publish event
            self._publish_event('organization.updated', {
                'organization_id': str(org.id),
                'changed_fields': changed_fields,
                'updated_by': str(updated_by),
            })

        return org

    def soft_delete_organization(
        self,
        organization_id: UUID,
        deleted_by: UUID,
        reason: str = None
    ) -> Organization:
        """
        Soft delete an organization.

        Args:
            organization_id: Organization UUID
            deleted_by: User ID performing deletion
            reason: Optional deletion reason

        Returns:
            Deleted Organization instance
        """
        org = self.get_organization(organization_id)
        if not org:
            raise OrganizationNotFoundError(f"Organization {organization_id} not found")

        org.soft_delete(deleted_by)

        # Invalidate cache
        self._invalidate_cache(org)

        logger.info(f"Soft deleted organization: {org.name} ({org.id})")

        # Publish event
        self._publish_event('organization.deleted', {
            'organization_id': str(org.id),
            'name': org.name,
            'deleted_by': str(deleted_by),
            'reason': reason,
        })

        return org

    def list_organizations(
        self,
        status: str = None,
        country_code: str = None,
        subscription_status: str = None,
        search: str = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Organization]:
        """
        List organizations with filtering.

        Args:
            status: Filter by status
            country_code: Filter by country
            subscription_status: Filter by subscription status
            search: Search in name and email
            limit: Maximum results
            offset: Result offset

        Returns:
            List of Organization instances
        """
        queryset = Organization.objects.filter(deleted_at__isnull=True)

        if status:
            queryset = queryset.filter(status=status)
        if country_code:
            queryset = queryset.filter(country_code=country_code.upper())
        if subscription_status:
            queryset = queryset.filter(subscription_status=subscription_status)
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(email__icontains=search) |
                Q(slug__icontains=search)
            )

        return list(queryset.order_by('name')[offset:offset + limit])

    # ==================== BRANDING ====================

    def update_branding(
        self,
        organization_id: UUID,
        logo_url: str = None,
        logo_dark_url: str = None,
        favicon_url: str = None,
        primary_color: str = None,
        secondary_color: str = None,
        accent_color: str = None,
        updated_by: UUID = None
    ) -> Organization:
        """
        Update organization branding.

        Args:
            organization_id: Organization UUID
            logo_url: URL to logo image
            logo_dark_url: URL to dark mode logo
            favicon_url: URL to favicon
            primary_color: Primary brand color (hex)
            secondary_color: Secondary brand color (hex)
            accent_color: Accent color (hex)
            updated_by: User ID making the update

        Returns:
            Updated Organization instance
        """
        org = self.get_organization(organization_id)
        if not org:
            raise OrganizationNotFoundError(f"Organization {organization_id} not found")

        # Validate colors
        for color_name, color_value in [
            ('primary_color', primary_color),
            ('secondary_color', secondary_color),
            ('accent_color', accent_color)
        ]:
            if color_value:
                self._validate_hex_color(color_value)

        # Update fields
        if logo_url is not None:
            org.logo_url = logo_url
        if logo_dark_url is not None:
            org.logo_dark_url = logo_dark_url
        if favicon_url is not None:
            org.favicon_url = favicon_url
        if primary_color is not None:
            org.primary_color = primary_color
        if secondary_color is not None:
            org.secondary_color = secondary_color
        if accent_color is not None:
            org.accent_color = accent_color

        if updated_by:
            org.updated_by = updated_by

        org.save()
        self._invalidate_cache(org)

        logger.info(f"Updated branding for organization: {org.id}")

        return org

    def setup_custom_domain(
        self,
        organization_id: UUID,
        domain: str,
        updated_by: UUID
    ) -> Dict[str, Any]:
        """
        Set up custom domain for organization.

        Args:
            organization_id: Organization UUID
            domain: Custom domain to set up
            updated_by: User ID making the update

        Returns:
            Dict with verification instructions
        """
        org = self.get_organization(organization_id)
        if not org:
            raise OrganizationNotFoundError(f"Organization {organization_id} not found")

        # Check if domain is already taken
        existing = Organization.objects.filter(
            custom_domain=domain,
            deleted_at__isnull=True
        ).exclude(id=organization_id).first()

        if existing:
            raise DomainAlreadyExistsError(f"Domain {domain} is already in use")

        # Set domain (unverified)
        org.custom_domain = domain
        org.custom_domain_verified = False
        org.updated_by = updated_by
        org.save()

        self._invalidate_cache(org)

        # Generate verification token
        verification_token = f"avinor-verify={org.id}"

        return {
            'domain': domain,
            'verified': False,
            'verification_instructions': {
                'method': 'DNS TXT Record',
                'record_type': 'TXT',
                'record_name': '_avinor-verification',
                'record_value': verification_token,
                'alternative_method': {
                    'method': 'CNAME',
                    'record_name': domain,
                    'record_value': f'{org.slug}.app.avinor.com'
                }
            }
        }

    def verify_custom_domain(self, organization_id: UUID) -> bool:
        """
        Verify custom domain DNS configuration.

        Args:
            organization_id: Organization UUID

        Returns:
            True if verified successfully
        """
        org = self.get_organization(organization_id)
        if not org or not org.custom_domain:
            return False

        # In production, this would perform actual DNS lookup
        # For now, we'll mark as verified
        org.custom_domain_verified = True
        org.save()

        self._invalidate_cache(org)

        logger.info(f"Verified custom domain for organization: {org.id}")

        return True

    # ==================== SETTINGS ====================

    def get_settings(
        self,
        organization_id: UUID,
        category: str = None,
        include_secrets: bool = False
    ) -> Dict[str, Any]:
        """
        Get organization settings.

        Args:
            organization_id: Organization UUID
            category: Optional category filter
            include_secrets: Whether to include secret values

        Returns:
            Dict of settings grouped by category
        """
        cache_key = f"{self.CACHE_PREFIX}:settings:{organization_id}"
        if category:
            cache_key += f":{category}"

        if not include_secrets:
            cached = cache.get(cache_key)
            if cached:
                return cached

        queryset = OrganizationSetting.objects.filter(
            organization_id=organization_id
        )
        if category:
            queryset = queryset.filter(category=category)

        settings = {}
        for setting in queryset:
            if setting.category not in settings:
                settings[setting.category] = {}

            if setting.is_secret and not include_secrets:
                settings[setting.category][setting.key] = '********'
            else:
                settings[setting.category][setting.key] = setting.value

        if not include_secrets:
            cache.set(cache_key, settings, self.CACHE_TTL)

        return settings

    def update_setting(
        self,
        organization_id: UUID,
        category: str,
        key: str,
        value: Any,
        description: str = None,
        is_secret: bool = False
    ) -> OrganizationSetting:
        """
        Update or create a setting.

        Args:
            organization_id: Organization UUID
            category: Setting category
            key: Setting key
            value: Setting value
            description: Optional description
            is_secret: Whether value is sensitive

        Returns:
            OrganizationSetting instance
        """
        org = self.get_organization(organization_id)
        if not org:
            raise OrganizationNotFoundError(f"Organization {organization_id} not found")

        setting, created = OrganizationSetting.objects.update_or_create(
            organization_id=organization_id,
            category=category,
            key=key,
            defaults={
                'value': value,
                'description': description,
                'is_secret': is_secret,
            }
        )

        # Invalidate settings cache
        cache.delete(f"{self.CACHE_PREFIX}:settings:{organization_id}")
        cache.delete(f"{self.CACHE_PREFIX}:settings:{organization_id}:{category}")

        logger.info(f"Updated setting {category}.{key} for organization {organization_id}")

        return setting

    def delete_setting(
        self,
        organization_id: UUID,
        category: str,
        key: str
    ) -> bool:
        """Delete a setting."""
        deleted, _ = OrganizationSetting.objects.filter(
            organization_id=organization_id,
            category=category,
            key=key
        ).delete()

        if deleted:
            cache.delete(f"{self.CACHE_PREFIX}:settings:{organization_id}")
            cache.delete(f"{self.CACHE_PREFIX}:settings:{organization_id}:{category}")

        return deleted > 0

    # ==================== USAGE & LIMITS ====================

    def get_usage_statistics(self, organization_id: UUID) -> Dict[str, Any]:
        """
        Get organization usage statistics.

        Args:
            organization_id: Organization UUID

        Returns:
            Dict with usage statistics
        """
        org = self.get_organization(organization_id)
        if not org:
            raise OrganizationNotFoundError(f"Organization {organization_id} not found")

        # Get counts (in production, these would come from other services)
        location_count = Location.objects.filter(
            organization_id=organization_id,
            is_active=True
        ).count()

        # Placeholder counts - in production, query other services
        user_count = 0  # Would query user-service
        aircraft_count = 0  # Would query fleet-service
        student_count = 0  # Would query user-service
        storage_used_gb = 0  # Would query document-service

        return {
            'users': {
                'current': user_count,
                'limit': org.max_users,
                'percentage': self._calculate_percentage(user_count, org.max_users),
                'available': max(0, org.max_users - user_count) if org.max_users != -1 else -1,
            },
            'aircraft': {
                'current': aircraft_count,
                'limit': org.max_aircraft,
                'percentage': self._calculate_percentage(aircraft_count, org.max_aircraft),
                'available': max(0, org.max_aircraft - aircraft_count) if org.max_aircraft != -1 else -1,
            },
            'students': {
                'current': student_count,
                'limit': org.max_students,
                'percentage': self._calculate_percentage(student_count, org.max_students),
                'available': max(0, org.max_students - student_count) if org.max_students != -1 else -1,
            },
            'locations': {
                'current': location_count,
                'limit': org.max_locations,
                'percentage': self._calculate_percentage(location_count, org.max_locations),
                'available': max(0, org.max_locations - location_count) if org.max_locations != -1 else -1,
            },
            'storage': {
                'used_gb': storage_used_gb,
                'limit_gb': org.storage_limit_gb,
                'percentage': self._calculate_percentage(storage_used_gb, org.storage_limit_gb),
                'available_gb': max(0, org.storage_limit_gb - storage_used_gb) if org.storage_limit_gb != -1 else -1,
            },
        }

    def check_limit(
        self,
        organization_id: UUID,
        resource_type: str,
        current_count: int = None
    ) -> Dict[str, Any]:
        """
        Check if organization can add more of a resource.

        Args:
            organization_id: Organization UUID
            resource_type: Type of resource (user, aircraft, student, location)
            current_count: Current count (if known)

        Returns:
            Dict with limit check result
        """
        org = self.get_organization(organization_id)
        if not org:
            raise OrganizationNotFoundError(f"Organization {organization_id} not found")

        limit_map = {
            'user': org.max_users,
            'aircraft': org.max_aircraft,
            'student': org.max_students,
            'location': org.max_locations,
        }

        limit = limit_map.get(resource_type)
        if limit is None:
            return {'allowed': True, 'reason': 'Unknown resource type'}

        if limit == -1:
            return {'allowed': True, 'reason': 'Unlimited'}

        if current_count is None:
            # Would need to query actual count
            return {'allowed': True, 'reason': 'Count not provided'}

        allowed = current_count < limit

        return {
            'allowed': allowed,
            'current': current_count,
            'limit': limit,
            'reason': None if allowed else f'{resource_type.title()} limit reached ({limit})',
        }

    # ==================== PRIVATE METHODS ====================

    def _generate_unique_slug(self, name: str) -> str:
        """Generate a unique slug for the organization."""
        base_slug = slugify(name)[:90]  # Leave room for counter
        slug = base_slug
        counter = 1

        while Organization.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1

        return slug

    def _validate_email(self, email: str) -> None:
        """Validate email format."""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(pattern, email):
            raise OrganizationValidationError(f"Invalid email format: {email}")

    def _validate_country_code(self, code: str) -> None:
        """Validate country code."""
        if not code or len(code) != 2 or not code.isalpha():
            raise OrganizationValidationError(f"Invalid country code: {code}")

    def _validate_hex_color(self, color: str) -> None:
        """Validate hex color format."""
        if not re.match(r'^#[0-9A-Fa-f]{6}$', color):
            raise OrganizationValidationError(f"Invalid hex color: {color}")

    def _calculate_percentage(self, current: int, limit: int) -> float:
        """Calculate usage percentage."""
        if limit == -1 or limit == 0:
            return 0.0
        return round((current / limit) * 100, 2)

    def _invalidate_cache(self, org: Organization) -> None:
        """Invalidate all caches for an organization."""
        cache.delete(f"{self.CACHE_PREFIX}:{org.id}")
        cache.delete(f"{self.CACHE_PREFIX}:slug:{org.slug}")
        if org.custom_domain:
            cache.delete(f"{self.CACHE_PREFIX}:domain:{org.custom_domain}")
        cache.delete(f"{self.CACHE_PREFIX}:settings:{org.id}")

    def _create_default_settings(self, org: Organization) -> None:
        """Create default settings for a new organization."""
        default_settings = [
            # Booking settings
            ('booking', 'allow_student_self_booking', True, 'Allow students to make their own bookings'),
            ('booking', 'require_instructor_approval', False, 'Require instructor approval for bookings'),
            ('booking', 'max_concurrent_bookings', 3, 'Maximum concurrent bookings per user'),
            ('booking', 'booking_slot_duration', 30, 'Booking slot duration in minutes'),
            ('booking', 'buffer_between_bookings', 15, 'Buffer time between bookings in minutes'),

            # Flight settings
            ('flight', 'require_dual_signature', True, 'Require both student and instructor signature'),
            ('flight', 'auto_calculate_times', True, 'Automatically calculate flight times'),
            ('flight', 'fuel_unit', 'liters', 'Fuel measurement unit'),
            ('flight', 'distance_unit', 'nm', 'Distance measurement unit'),

            # Finance settings
            ('finance', 'tax_rate', 0, 'Tax rate percentage'),
            ('finance', 'tax_name', 'VAT', 'Tax name'),
            ('finance', 'invoice_prefix', 'INV', 'Invoice number prefix'),
            ('finance', 'invoice_footer', '', 'Invoice footer text'),

            # Notification settings
            ('notification', 'booking_reminder_hours', [24, 2], 'Hours before booking to send reminders'),
            ('notification', 'certificate_expiry_days', [90, 60, 30, 7], 'Days before expiry to notify'),
            ('notification', 'low_balance_threshold', 500, 'Low balance warning threshold'),
        ]

        settings_to_create = [
            OrganizationSetting(
                organization=org,
                category=category,
                key=key,
                value=value,
                description=description
            )
            for category, key, value, description in default_settings
        ]

        OrganizationSetting.objects.bulk_create(settings_to_create)

    def _publish_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Publish an event."""
        try:
            from apps.core.events import publish_event
            publish_event(event_type, data)
        except Exception as e:
            logger.error(f"Failed to publish event {event_type}: {e}")
