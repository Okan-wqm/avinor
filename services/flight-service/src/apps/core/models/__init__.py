# services/flight-service/src/apps/core/models/__init__.py
"""
Flight Service Models

Database models for flight operations including:
- Flight records and logbook entries
- Crew logs and fuel records
- Approach tracking
- Flight planning with weather/NOTAM integration
- Risk assessment tools
"""

from .flight import Flight
from .pilot_logbook import PilotLogbookSummary
from .flight_crew_log import FlightCrewLog
from .fuel_record import FuelRecord
from .approach import Approach
from .flight_planning import (
    WeatherBriefing,
    NOTAMBriefing,
    FlightPlan,
    FlightPlanWaypoint,
    FlightRiskAssessment,
    WeatherMinima,
    PersonalMinima,
    SavedRoute,
)

__all__ = [
    # Core Flight Models
    'Flight',
    'PilotLogbookSummary',
    'FlightCrewLog',
    'FuelRecord',
    'Approach',

    # Flight Planning Models
    'WeatherBriefing',
    'NOTAMBriefing',
    'FlightPlan',
    'FlightPlanWaypoint',
    'FlightRiskAssessment',
    'WeatherMinima',
    'PersonalMinima',
    'SavedRoute',
]
