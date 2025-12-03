# services/organization-service/src/apps/core/middleware/tenant.py
"""
Multi-Tenant Middleware

Handles organization context for multi-tenant requests.
Extracts organization from URL path, headers, or custom domain.
"""

import logging
import threading
from typing import Optional, Any
from contextlib import contextmanager
from dataclasses import dataclass
from uuid import UUID

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

# Thread-local storage for organization context
_thread_locals = threading.local()


# =============================================================================
# Organization Context Data
# =============================================================================

@dataclass
class OrganizationContext:
    """Container for organization context data."""

    organization_id: Optional[UUID] = None
    organization_slug: Optional[str] = None
    organization_name: Optional[str] = None
    subscription_status: Optional[str] = None
    features: Optional[dict] = None
    limits: Optional[dict] = None
    is_active: bool = True

    def has_feature(self, feature: str) -> bool:
        """Check if organization has a specific feature."""
        if not self.features:
            return False
        return self.features.get(feature, False)

    def get_limit(self, limit_name: str, default: int = 0) -> int:
        """Get a specific limit value."""
        if not self.limits:
            return default
        return self.limits.get(limit_name, default)


# =============================================================================
# Thread-Local Organization Context Functions
# =============================================================================

def get_current_organization() -> Optional[OrganizationContext]:
    """Get current organization context from thread-local storage."""
    return getattr(_thread_locals, 'organization', None)


def set_current_organization(context: OrganizationContext) -> None:
    """Set current organization context in thread-local storage."""
    _thread_locals.organization = context


def clear_current_organization() -> None:
    """Clear current organization context from thread-local storage."""
    if hasattr(_thread_locals, 'organization'):
        del _thread_locals.organization


def get_current_organization_id() -> Optional[UUID]:
    """Get current organization ID from context."""
    context = get_current_organization()
    return context.organization_id if context else None


@contextmanager
def organization_context(org_id: UUID, **kwargs):
    """
    Context manager for organization context.

    Usage:
        with organization_context(org_id) as ctx:
            # Code runs with organization context
            pass
    """
    context = OrganizationContext(organization_id=org_id, **kwargs)
    set_current_organization(context)
    try:
        yield context
    finally:
        clear_current_organization()


# =============================================================================
# Multi-Tenant Middleware
# =============================================================================

class TenantMiddleware:
    """
    Middleware for handling multi-tenant organization context.

    Extracts organization from:
    1. URL path parameter (e.g., /organizations/{org_id}/...)
    2. X-Organization-ID header
    3. Custom domain lookup

    Sets organization context in thread-local storage for use throughout
    the request lifecycle.
    """

    # Paths that don't require organization context
    EXEMPT_PATHS = [
        '/health/',
        '/api/v1/subscription-plans/',
        '/api/v1/invitations/accept/',
        '/api/v1/invitations/validate/',
        '/admin/',
    ]

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        """Process request with organization context."""
        # Clear any previous context
        clear_current_organization()

        # Check if path is exempt
        if self._is_exempt_path(request.path):
            return self.get_response(request)

        # Try to extract organization context
        context = self._extract_organization_context(request)

        if context:
            # Set context for this request
            set_current_organization(context)

            # Add to request for easy access
            request.organization = context

            # Validate organization is active
            if not context.is_active:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Organization is not active',
                    'code': 'ORGANIZATION_INACTIVE',
                }, status=403)

        try:
            response = self.get_response(request)
            return response
        finally:
            # Clean up context after request
            clear_current_organization()

    def _is_exempt_path(self, path: str) -> bool:
        """Check if path is exempt from organization context."""
        for exempt in self.EXEMPT_PATHS:
            if path.startswith(exempt):
                return True
        return False

    def _extract_organization_context(self, request: HttpRequest) -> Optional[OrganizationContext]:
        """
        Extract organization context from request.

        Priority:
        1. URL path parameter
        2. X-Organization-ID header
        3. Custom domain
        """
        org_id = None

        # 1. Try URL path parameter
        org_id = self._extract_from_url(request)

        # 2. Try header
        if not org_id:
            org_id = self._extract_from_header(request)

        # 3. Try custom domain
        if not org_id:
            org_id = self._extract_from_domain(request)

        if not org_id:
            return None

        # Load organization data
        return self._load_organization_context(org_id)

    def _extract_from_url(self, request: HttpRequest) -> Optional[str]:
        """Extract organization ID from URL path."""
        # Pattern: /api/v1/organizations/{org_id}/...
        path_parts = request.path.split('/')

        try:
            if 'organizations' in path_parts:
                org_index = path_parts.index('organizations')
                if len(path_parts) > org_index + 1:
                    potential_id = path_parts[org_index + 1]
                    # Validate UUID format
                    UUID(potential_id)
                    return potential_id
        except (ValueError, IndexError):
            pass

        return None

    def _extract_from_header(self, request: HttpRequest) -> Optional[str]:
        """Extract organization ID from header."""
        org_id = request.META.get('HTTP_X_ORGANIZATION_ID')
        if org_id:
            try:
                UUID(org_id)
                return org_id
            except ValueError:
                logger.warning(f"Invalid organization ID in header: {org_id}")
        return None

    def _extract_from_domain(self, request: HttpRequest) -> Optional[str]:
        """Extract organization ID from custom domain."""
        host = request.get_host()

        # Skip standard domains
        standard_domains = getattr(settings, 'STANDARD_DOMAINS', [])
        if host in standard_domains:
            return None

        # Look up custom domain
        cache_key = f"custom_domain:{host}"
        org_id = cache.get(cache_key)

        if org_id is None:
            # Query database
            from apps.core.models import Organization
            try:
                org = Organization.objects.filter(
                    custom_domain=host,
                    custom_domain_verified=True,
                    deleted_at__isnull=True
                ).values('id').first()

                if org:
                    org_id = str(org['id'])
                    cache.set(cache_key, org_id, timeout=3600)
                else:
                    cache.set(cache_key, '', timeout=300)  # Cache negative result
            except Exception as e:
                logger.error(f"Error looking up custom domain {host}: {e}")
                return None

        return org_id if org_id else None

    def _load_organization_context(self, org_id: str) -> Optional[OrganizationContext]:
        """Load full organization context."""
        cache_key = f"org_context:{org_id}"
        cached = cache.get(cache_key)

        if cached:
            return OrganizationContext(**cached)

        # Load from database
        from apps.core.models import Organization
        try:
            org = Organization.objects.select_related(
                'subscription_plan'
            ).get(
                id=org_id,
                deleted_at__isnull=True
            )

            # Build context
            context_data = {
                'organization_id': org.id,
                'organization_slug': org.slug,
                'organization_name': org.name,
                'subscription_status': org.subscription_status,
                'features': org.features or {},
                'limits': {
                    'max_users': org.max_users,
                    'max_aircraft': org.max_aircraft,
                    'max_students': org.max_students,
                    'max_locations': org.max_locations,
                    'storage_limit_gb': org.storage_limit_gb,
                },
                'is_active': org.status == Organization.Status.ACTIVE,
            }

            # Cache for 5 minutes
            cache.set(cache_key, context_data, timeout=300)

            return OrganizationContext(**context_data)

        except Organization.DoesNotExist:
            logger.warning(f"Organization not found: {org_id}")
            return None
        except Exception as e:
            logger.error(f"Error loading organization context {org_id}: {e}")
            return None


# =============================================================================
# Organization-Scoped QuerySet Mixin
# =============================================================================

class OrganizationScopedQuerySetMixin:
    """
    Mixin for QuerySets to automatically filter by current organization.

    Usage:
        class MyModel(models.Model):
            organization = models.ForeignKey(Organization, ...)

            objects = OrganizationScopedManager()

        class OrganizationScopedManager(models.Manager):
            def get_queryset(self):
                return OrganizationScopedQuerySet(self.model, using=self._db)

        class OrganizationScopedQuerySet(OrganizationScopedQuerySetMixin, models.QuerySet):
            pass
    """

    def for_current_organization(self):
        """Filter queryset by current organization context."""
        org_context = get_current_organization()
        if org_context and org_context.organization_id:
            return self.filter(organization_id=org_context.organization_id)
        return self.none()

    def for_organization(self, org_id: UUID):
        """Filter queryset by specific organization."""
        return self.filter(organization_id=org_id)
