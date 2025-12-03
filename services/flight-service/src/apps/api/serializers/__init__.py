# services/flight-service/src/apps/api/serializers/__init__.py
"""
Flight Service API Serializers

REST API serializers for flight management.
"""

from .flight_serializers import (
    FlightListSerializer,
    FlightDetailSerializer,
    FlightCreateSerializer,
    FlightUpdateSerializer,
    FlightSubmitSerializer,
    FlightApproveSerializer,
    FlightRejectSerializer,
    FlightSignatureSerializer,
)

from .approach_serializers import (
    ApproachSerializer,
    ApproachCreateSerializer,
    HoldSerializer,
    HoldCreateSerializer,
)

from .fuel_serializers import (
    FuelRecordSerializer,
    FuelRecordCreateSerializer,
    OilRecordSerializer,
    OilRecordCreateSerializer,
)

from .logbook_serializers import (
    FlightCrewLogSerializer,
    LogbookEntrySerializer,
    LogbookSummarySerializer,
    LogbookExportSerializer,
)

from .statistics_serializers import (
    PilotStatisticsSerializer,
    AircraftStatisticsSerializer,
    OrganizationStatisticsSerializer,
    DashboardStatisticsSerializer,
    CurrencyStatusSerializer,
)

__all__ = [
    # Flight
    'FlightListSerializer',
    'FlightDetailSerializer',
    'FlightCreateSerializer',
    'FlightUpdateSerializer',
    'FlightSubmitSerializer',
    'FlightApproveSerializer',
    'FlightRejectSerializer',
    'FlightSignatureSerializer',
    # Approach
    'ApproachSerializer',
    'ApproachCreateSerializer',
    'HoldSerializer',
    'HoldCreateSerializer',
    # Fuel
    'FuelRecordSerializer',
    'FuelRecordCreateSerializer',
    'OilRecordSerializer',
    'OilRecordCreateSerializer',
    # Logbook
    'FlightCrewLogSerializer',
    'LogbookEntrySerializer',
    'LogbookSummarySerializer',
    'LogbookExportSerializer',
    # Statistics
    'PilotStatisticsSerializer',
    'AircraftStatisticsSerializer',
    'OrganizationStatisticsSerializer',
    'DashboardStatisticsSerializer',
    'CurrencyStatusSerializer',
]
