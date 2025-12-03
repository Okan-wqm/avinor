# services/aircraft-service/src/apps/api/serializers/__init__.py
"""
Aircraft Service API Serializers

All serializers for the Aircraft Service API.
"""

from .aircraft_serializers import (
    AircraftTypeSerializer,
    AircraftListSerializer,
    AircraftDetailSerializer,
    AircraftCreateSerializer,
    AircraftUpdateSerializer,
    AircraftStatusSerializer,
    AircraftAvailabilitySerializer,
    GroundAircraftSerializer,
)

from .engine_serializers import (
    AircraftEngineSerializer,
    AircraftEngineCreateSerializer,
    AircraftEngineUpdateSerializer,
    EngineOverhaulSerializer,
)

from .propeller_serializers import (
    AircraftPropellerSerializer,
    AircraftPropellerCreateSerializer,
)

from .squawk_serializers import (
    SquawkListSerializer,
    SquawkDetailSerializer,
    SquawkCreateSerializer,
    SquawkUpdateSerializer,
    SquawkResolveSerializer,
    SquawkDeferSerializer,
    SquawkStatisticsSerializer,
)

from .document_serializers import (
    DocumentListSerializer,
    DocumentDetailSerializer,
    DocumentCreateSerializer,
    DocumentUpdateSerializer,
    DocumentComplianceSerializer,
)

from .counter_serializers import (
    CounterSerializer,
    CounterUpdateSerializer,
    CounterAdjustmentSerializer,
    TimeLogSerializer,
    UtilizationStatsSerializer,
)

__all__ = [
    # Aircraft
    'AircraftTypeSerializer',
    'AircraftListSerializer',
    'AircraftDetailSerializer',
    'AircraftCreateSerializer',
    'AircraftUpdateSerializer',
    'AircraftStatusSerializer',
    'AircraftAvailabilitySerializer',
    'GroundAircraftSerializer',

    # Engine
    'AircraftEngineSerializer',
    'AircraftEngineCreateSerializer',
    'AircraftEngineUpdateSerializer',
    'EngineOverhaulSerializer',

    # Propeller
    'AircraftPropellerSerializer',
    'AircraftPropellerCreateSerializer',

    # Squawk
    'SquawkListSerializer',
    'SquawkDetailSerializer',
    'SquawkCreateSerializer',
    'SquawkUpdateSerializer',
    'SquawkResolveSerializer',
    'SquawkDeferSerializer',
    'SquawkStatisticsSerializer',

    # Document
    'DocumentListSerializer',
    'DocumentDetailSerializer',
    'DocumentCreateSerializer',
    'DocumentUpdateSerializer',
    'DocumentComplianceSerializer',

    # Counter
    'CounterSerializer',
    'CounterUpdateSerializer',
    'CounterAdjustmentSerializer',
    'TimeLogSerializer',
    'UtilizationStatsSerializer',
]
