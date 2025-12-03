# services/organization-service/src/apps/core/urls.py
"""
Organization Service URL Configuration

Defines all API routes for the Organization Service.
Uses nested routers for organization-scoped resources.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers as nested_routers

from apps.core.views import (
    OrganizationViewSet,
    OrganizationSettingsViewSet,
    LocationViewSet,
    SubscriptionPlanViewSet,
    SubscriptionViewSet,
    InvitationViewSet,
)

# =============================================================================
# Main Router - Top-level resources
# =============================================================================
router = DefaultRouter()
router.register(r'organizations', OrganizationViewSet, basename='organization')
router.register(r'subscription-plans', SubscriptionPlanViewSet, basename='subscription-plan')

# =============================================================================
# Nested Router - Organization-scoped resources
# =============================================================================
organizations_router = nested_routers.NestedDefaultRouter(
    router, r'organizations', lookup='organization'
)

# /organizations/{org_id}/locations/
organizations_router.register(
    r'locations',
    LocationViewSet,
    basename='organization-location'
)

# /organizations/{org_id}/settings/
organizations_router.register(
    r'settings',
    OrganizationSettingsViewSet,
    basename='organization-setting'
)

# /organizations/{org_id}/subscription/
organizations_router.register(
    r'subscription',
    SubscriptionViewSet,
    basename='organization-subscription'
)

# /organizations/{org_id}/invitations/
organizations_router.register(
    r'invitations',
    InvitationViewSet,
    basename='organization-invitation'
)

# =============================================================================
# App name for URL namespacing
# =============================================================================
app_name = 'core'

# =============================================================================
# URL Patterns
# =============================================================================
urlpatterns = [
    # Main routes from router
    path('', include(router.urls)),

    # Nested organization routes
    path('', include(organizations_router.urls)),

    # =========================================================================
    # Public invitation endpoints (not organization-scoped)
    # =========================================================================
    path(
        'invitations/accept/',
        InvitationViewSet.as_view({'post': 'accept'}),
        name='invitation-accept'
    ),
    path(
        'invitations/validate/<str:token>/',
        InvitationViewSet.as_view({'get': 'validate_token'}),
        name='invitation-validate'
    ),

    # =========================================================================
    # Organization lookup by slug (alternative to ID)
    # =========================================================================
    path(
        'organizations/by-slug/<str:slug>/',
        OrganizationViewSet.as_view({'get': 'get_by_slug'}),
        name='organization-by-slug'
    ),
]

# =============================================================================
# API Endpoints Summary:
# =============================================================================
#
# Organizations:
#   GET    /organizations/                          - List organizations
#   POST   /organizations/                          - Create organization
#   GET    /organizations/{id}/                     - Get organization
#   PUT    /organizations/{id}/                     - Update organization
#   DELETE /organizations/{id}/                     - Delete organization
#   PUT    /organizations/{id}/branding/            - Update branding
#   GET    /organizations/{id}/usage/               - Get usage stats
#   POST   /organizations/{id}/custom-domain/       - Setup custom domain
#   POST   /organizations/{id}/verify-domain/       - Verify domain
#   POST   /organizations/{id}/activate/            - Activate organization
#   POST   /organizations/{id}/suspend/             - Suspend organization
#   GET    /organizations/by-slug/{slug}/           - Get by slug
#
# Locations:
#   GET    /organizations/{id}/locations/           - List locations
#   POST   /organizations/{id}/locations/           - Create location
#   GET    /organizations/{id}/locations/{lid}/     - Get location
#   PUT    /organizations/{id}/locations/{lid}/     - Update location
#   DELETE /organizations/{id}/locations/{lid}/     - Delete location
#   PUT    /organizations/{id}/locations/{lid}/primary/         - Set primary
#   PUT    /organizations/{id}/locations/{lid}/operating-hours/ - Update hours
#   GET    /organizations/{id}/locations/{lid}/weather/         - Get weather
#   PUT    /organizations/{id}/locations/{lid}/facilities/      - Update facilities
#   PUT    /organizations/{id}/locations/{lid}/runways/         - Update runways
#   PUT    /organizations/{id}/locations/{lid}/frequencies/     - Update frequencies
#   POST   /organizations/{id}/locations/reorder/               - Reorder locations
#
# Settings:
#   GET    /organizations/{id}/settings/            - List all settings
#   POST   /organizations/{id}/settings/            - Create/update setting
#   PUT    /organizations/{id}/settings/{key}/      - Update settings
#   DELETE /organizations/{id}/settings/{key}/      - Delete setting
#
# Subscription:
#   GET    /organizations/{id}/subscription/                    - Get status
#   POST   /organizations/{id}/subscription/change/             - Change plan
#   POST   /organizations/{id}/subscription/cancel/             - Cancel
#   POST   /organizations/{id}/subscription/reactivate/         - Reactivate
#   GET    /organizations/{id}/subscription/history/            - Get history
#   GET    /organizations/{id}/subscription/limits/             - Get limits
#   POST   /organizations/{id}/subscription/start-trial/        - Start trial
#   POST   /organizations/{id}/subscription/extend-trial/       - Extend trial
#   POST   /organizations/{id}/subscription/convert-trial/      - Convert trial
#   GET    /organizations/{id}/subscription/can-upgrade/{code}/ - Check upgrade
#   GET    /organizations/{id}/subscription/check-limit/{res}/  - Check limit
#
# Subscription Plans:
#   GET    /subscription-plans/                     - List plans
#   GET    /subscription-plans/{id}/                - Get plan
#   GET    /subscription-plans/by-code/{code}/      - Get by code
#   GET    /subscription-plans/compare/             - Compare plans
#
# Invitations:
#   GET    /organizations/{id}/invitations/         - List invitations
#   POST   /organizations/{id}/invitations/         - Create invitation
#   POST   /organizations/{id}/invitations/bulk/    - Bulk create
#   GET    /organizations/{id}/invitations/{iid}/   - Get invitation
#   DELETE /organizations/{id}/invitations/{iid}/   - Cancel invitation
#   POST   /organizations/{id}/invitations/{iid}/resend/  - Resend
#   POST   /organizations/{id}/invitations/{iid}/revoke/  - Revoke
#   POST   /organizations/{id}/invitations/{iid}/extend/  - Extend
#   GET    /organizations/{id}/invitations/statistics/    - Get stats
#   GET    /organizations/{id}/invitations/pending-for-email/ - Pending by email
#   POST   /organizations/{id}/invitations/cleanup-expired/   - Cleanup
#
# Public Invitation Endpoints:
#   POST   /invitations/accept/                     - Accept invitation
#   GET    /invitations/validate/{token}/           - Validate token
# =============================================================================
