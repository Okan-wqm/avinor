# services/aircraft-service/src/apps/api/urls.py
"""
Aircraft Service API URL Configuration

All API endpoints for the Aircraft Service.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers

from .views import (
    AircraftTypeViewSet,
    AircraftViewSet,
    SquawkViewSet,
    DocumentViewSet,
    CounterViewSet,
)
from .views.document_views import OrganizationDocumentViewSet

# =============================================================================
# Main Router
# =============================================================================

router = DefaultRouter()
router.register(r'aircraft-types', AircraftTypeViewSet, basename='aircraft-type')
router.register(r'aircraft', AircraftViewSet, basename='aircraft')
router.register(r'squawks', SquawkViewSet, basename='squawk')

# =============================================================================
# Nested Routers for Aircraft
# =============================================================================

# /aircraft/{aircraft_pk}/squawks/
aircraft_router = routers.NestedDefaultRouter(router, r'aircraft', lookup='aircraft')
aircraft_router.register(r'squawks', SquawkViewSet, basename='aircraft-squawk')
aircraft_router.register(r'documents', DocumentViewSet, basename='aircraft-document')

# =============================================================================
# Custom Routes for Counter ViewSet
# =============================================================================

counter_urlpatterns = [
    # /aircraft/{aircraft_pk}/counters/
    path(
        'aircraft/<uuid:aircraft_pk>/counters/',
        CounterViewSet.as_view({
            'get': 'list',
        }),
        name='aircraft-counters-list'
    ),
    path(
        'aircraft/<uuid:aircraft_pk>/counters/flight/',
        CounterViewSet.as_view({
            'post': 'update_flight',
        }),
        name='aircraft-counters-flight'
    ),
    path(
        'aircraft/<uuid:aircraft_pk>/counters/adjustment/',
        CounterViewSet.as_view({
            'post': 'adjustment',
        }),
        name='aircraft-counters-adjustment'
    ),
    path(
        'aircraft/<uuid:aircraft_pk>/counters/engine-adjustment/',
        CounterViewSet.as_view({
            'post': 'engine_adjustment',
        }),
        name='aircraft-counters-engine-adjustment'
    ),
    path(
        'aircraft/<uuid:aircraft_pk>/counters/logs/',
        CounterViewSet.as_view({
            'get': 'logs',
        }),
        name='aircraft-counters-logs'
    ),
    path(
        'aircraft/<uuid:aircraft_pk>/counters/summary/',
        CounterViewSet.as_view({
            'get': 'summary',
        }),
        name='aircraft-counters-summary'
    ),
    path(
        'aircraft/<uuid:aircraft_pk>/counters/utilization/',
        CounterViewSet.as_view({
            'get': 'utilization',
        }),
        name='aircraft-counters-utilization'
    ),
    path(
        'aircraft/<uuid:aircraft_pk>/counters/import/',
        CounterViewSet.as_view({
            'post': 'bulk_import',
        }),
        name='aircraft-counters-import'
    ),
]

# =============================================================================
# Organization-wide Document Routes
# =============================================================================

document_org_urlpatterns = [
    path(
        'documents/expiring/',
        OrganizationDocumentViewSet.as_view({
            'get': 'expiring',
        }),
        name='documents-expiring'
    ),
    path(
        'documents/expired/',
        OrganizationDocumentViewSet.as_view({
            'get': 'expired',
        }),
        name='documents-expired'
    ),
    path(
        'documents/compliance-summary/',
        OrganizationDocumentViewSet.as_view({
            'get': 'compliance_summary',
        }),
        name='documents-compliance-summary'
    ),
    path(
        'documents/reminders/',
        OrganizationDocumentViewSet.as_view({
            'get': 'reminders',
        }),
        name='documents-reminders'
    ),
    path(
        'documents/reminders/<uuid:document_id>/mark-sent/',
        OrganizationDocumentViewSet.as_view({
            'post': 'mark_reminder_sent',
        }),
        name='documents-mark-reminder-sent'
    ),
]

# =============================================================================
# Combined URL Patterns
# =============================================================================

app_name = 'api'

urlpatterns = [
    # Main routes
    path('', include(router.urls)),

    # Nested routes
    path('', include(aircraft_router.urls)),

    # Counter routes
    *counter_urlpatterns,

    # Organization document routes
    *document_org_urlpatterns,
]
