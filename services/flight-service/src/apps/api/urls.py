# services/flight-service/src/apps/api/urls.py
"""
Flight Service API URL Configuration

Defines URL patterns for all flight service endpoints.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.api.views import (
    FlightViewSet,
    ApproachViewSet,
    HoldViewSet,
    FuelRecordViewSet,
    OilRecordViewSet,
    LogbookViewSet,
    StatisticsViewSet,
    CurrencyViewSet,
)

app_name = 'api'

# Create router and register viewsets
router = DefaultRouter()
router.register(r'flights', FlightViewSet, basename='flight')
router.register(r'approaches', ApproachViewSet, basename='approach')
router.register(r'holds', HoldViewSet, basename='hold')
router.register(r'fuel-records', FuelRecordViewSet, basename='fuel-record')
router.register(r'oil-records', OilRecordViewSet, basename='oil-record')
router.register(r'logbook', LogbookViewSet, basename='logbook')
router.register(r'statistics', StatisticsViewSet, basename='statistics')
router.register(r'currency', CurrencyViewSet, basename='currency')

urlpatterns = [
    # Router URLs
    path('', include(router.urls)),
]

# =============================================================================
# API Endpoint Summary
# =============================================================================
#
# Flights:
#   GET    /api/v1/flights/                      - List flights
#   POST   /api/v1/flights/                      - Create flight
#   GET    /api/v1/flights/{id}/                 - Get flight details
#   PUT    /api/v1/flights/{id}/                 - Update flight
#   PATCH  /api/v1/flights/{id}/                 - Partial update
#   DELETE /api/v1/flights/{id}/                 - Delete flight
#   POST   /api/v1/flights/{id}/submit/          - Submit for approval
#   POST   /api/v1/flights/{id}/approve/         - Approve flight
#   POST   /api/v1/flights/{id}/reject/          - Reject flight
#   POST   /api/v1/flights/{id}/cancel/          - Cancel flight
#   POST   /api/v1/flights/{id}/sign/            - Sign flight
#   POST   /api/v1/flights/{id}/add_squawk/      - Add squawk
#   POST   /api/v1/flights/bulk_action/          - Bulk actions
#   GET    /api/v1/flights/pending_approval/     - Pending approval
#   GET    /api/v1/flights/pending_signature/    - Pending signature
#   GET    /api/v1/flights/by_pilot/             - Flights by pilot
#   GET    /api/v1/flights/by_aircraft/          - Flights by aircraft
#
# Approaches:
#   GET    /api/v1/approaches/                   - List approaches
#   POST   /api/v1/approaches/                   - Create approach
#   GET    /api/v1/approaches/{id}/              - Get approach
#   PUT    /api/v1/approaches/{id}/              - Update approach
#   DELETE /api/v1/approaches/{id}/              - Delete approach
#   POST   /api/v1/approaches/bulk_create/       - Bulk create
#   GET    /api/v1/approaches/statistics/        - Approach statistics
#   GET    /api/v1/approaches/by_flight/         - By flight
#
# Holds:
#   GET    /api/v1/holds/                        - List holds
#   POST   /api/v1/holds/                        - Create hold
#   GET    /api/v1/holds/{id}/                   - Get hold
#   PUT    /api/v1/holds/{id}/                   - Update hold
#   DELETE /api/v1/holds/{id}/                   - Delete hold
#   GET    /api/v1/holds/by_flight/              - By flight
#
# Fuel Records:
#   GET    /api/v1/fuel-records/                 - List fuel records
#   POST   /api/v1/fuel-records/                 - Create fuel record
#   GET    /api/v1/fuel-records/{id}/            - Get fuel record
#   PUT    /api/v1/fuel-records/{id}/            - Update fuel record
#   DELETE /api/v1/fuel-records/{id}/            - Delete fuel record
#   GET    /api/v1/fuel-records/by_flight/       - By flight
#   GET    /api/v1/fuel-records/by_aircraft/     - By aircraft
#   GET    /api/v1/fuel-records/statistics/      - Fuel statistics
#
# Oil Records:
#   GET    /api/v1/oil-records/                  - List oil records
#   POST   /api/v1/oil-records/                  - Create oil record
#   GET    /api/v1/oil-records/{id}/             - Get oil record
#   PUT    /api/v1/oil-records/{id}/             - Update oil record
#   DELETE /api/v1/oil-records/{id}/             - Delete oil record
#   GET    /api/v1/oil-records/by_flight/        - By flight
#   GET    /api/v1/oil-records/by_aircraft/      - By aircraft
#
# Logbook:
#   GET    /api/v1/logbook/                      - List logbook entries
#   GET    /api/v1/logbook/{flight_id}/          - Get logbook entry
#   GET    /api/v1/logbook/summary/              - Get summary
#   POST   /api/v1/logbook/recalculate/          - Recalculate summary
#   PATCH  /api/v1/logbook/{id}/remarks/         - Update remarks
#   POST   /api/v1/logbook/{id}/sign/            - Sign entry
#   GET    /api/v1/logbook/export/               - Export logbook
#   POST   /api/v1/logbook/recalculate_all/      - Recalculate all
#   GET    /api/v1/logbook/for_pilot/            - For specific pilot
#
# Statistics:
#   GET    /api/v1/statistics/dashboard/         - Dashboard stats
#   GET    /api/v1/statistics/pilot/             - Pilot stats
#   GET    /api/v1/statistics/pilot_approaches/  - Pilot approach stats
#   GET    /api/v1/statistics/aircraft/          - Aircraft stats
#   GET    /api/v1/statistics/aircraft_fuel/     - Aircraft fuel stats
#   GET    /api/v1/statistics/organization/      - Organization stats
#   GET    /api/v1/statistics/training/          - Training stats
#   POST   /api/v1/statistics/compare/           - Period comparison
#   GET    /api/v1/statistics/summary_report/    - Summary report
#
# Currency:
#   GET    /api/v1/currency/status/              - Currency status
#   GET    /api/v1/currency/check/               - Check all currency
#   POST   /api/v1/currency/validate_for_flight/ - Validate for flight
#   GET    /api/v1/currency/organization/        - Organization currency
#   GET    /api/v1/currency/expiring/            - Expiring currency
#   GET    /api/v1/currency/day_vfr/             - Day VFR details
#   GET    /api/v1/currency/night_vfr/           - Night VFR details
#   GET    /api/v1/currency/ifr/                 - IFR details
#
# =============================================================================
