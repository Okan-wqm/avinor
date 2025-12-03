# services/aircraft-service/src/apps/core/models/__init__.py
"""
Aircraft Service Models

This module exports all models for the Aircraft Service.
"""

from .aircraft_type import AircraftType
from .aircraft import Aircraft
from .engine import AircraftEngine
from .propeller import AircraftPropeller
from .squawk import AircraftSquawk
from .document import AircraftDocument
from .time_log import AircraftTimeLog

__all__ = [
    'AircraftType',
    'Aircraft',
    'AircraftEngine',
    'AircraftPropeller',
    'AircraftSquawk',
    'AircraftDocument',
    'AircraftTimeLog',
]
