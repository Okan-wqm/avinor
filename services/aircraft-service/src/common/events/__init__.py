# services/aircraft-service/src/common/events/__init__.py
"""
Aircraft Service Events

Event definitions and publisher for inter-service communication.
"""

from .definitions import AircraftEvents
from .publisher import EventPublisher

__all__ = [
    'AircraftEvents',
    'EventPublisher',
]
