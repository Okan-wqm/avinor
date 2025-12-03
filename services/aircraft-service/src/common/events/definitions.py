# services/aircraft-service/src/common/events/definitions.py
"""
Aircraft Service Event Definitions

All event types that can be published by the Aircraft Service.
"""

from enum import Enum


class AircraftEvents(str, Enum):
    """
    Event types for the Aircraft Service.

    Naming convention: ENTITY_ACTION
    """

    # ==========================================================================
    # Aircraft Events
    # ==========================================================================

    AIRCRAFT_CREATED = 'aircraft.created'
    AIRCRAFT_UPDATED = 'aircraft.updated'
    AIRCRAFT_DELETED = 'aircraft.deleted'
    AIRCRAFT_GROUNDED = 'aircraft.grounded'
    AIRCRAFT_UNGROUNDED = 'aircraft.ungrounded'
    AIRCRAFT_STATUS_CHANGED = 'aircraft.status_changed'
    AIRCRAFT_LOCATION_CHANGED = 'aircraft.location_changed'

    # ==========================================================================
    # Counter Events
    # ==========================================================================

    COUNTERS_UPDATED = 'aircraft.counters_updated'
    COUNTERS_ADJUSTED = 'aircraft.counters_adjusted'
    FLIGHT_TIME_ADDED = 'aircraft.flight_time_added'

    # ==========================================================================
    # Squawk Events
    # ==========================================================================

    SQUAWK_CREATED = 'squawk.created'
    SQUAWK_UPDATED = 'squawk.updated'
    SQUAWK_RESOLVED = 'squawk.resolved'
    SQUAWK_CLOSED = 'squawk.closed'
    SQUAWK_CANCELLED = 'squawk.cancelled'
    SQUAWK_DEFERRED = 'squawk.deferred'
    SQUAWK_WORK_STARTED = 'squawk.work_started'
    GROUNDING_SQUAWK_REPORTED = 'squawk.grounding_reported'

    # ==========================================================================
    # Document Events
    # ==========================================================================

    DOCUMENT_ADDED = 'document.added'
    DOCUMENT_UPDATED = 'document.updated'
    DOCUMENT_DELETED = 'document.deleted'
    DOCUMENT_EXPIRED = 'document.expired'
    DOCUMENT_EXPIRING_SOON = 'document.expiring_soon'

    # ==========================================================================
    # Engine/Propeller Events
    # ==========================================================================

    ENGINE_ADDED = 'engine.added'
    ENGINE_UPDATED = 'engine.updated'
    ENGINE_REMOVED = 'engine.removed'
    ENGINE_OVERHAUL_RECORDED = 'engine.overhaul_recorded'
    ENGINE_TBO_WARNING = 'engine.tbo_warning'
    ENGINE_TBO_EXCEEDED = 'engine.tbo_exceeded'

    PROPELLER_ADDED = 'propeller.added'
    PROPELLER_REMOVED = 'propeller.removed'

    # ==========================================================================
    # Airworthiness Events
    # ==========================================================================

    ARC_EXPIRING = 'airworthiness.arc_expiring'
    ARC_EXPIRED = 'airworthiness.arc_expired'
    INSURANCE_EXPIRING = 'airworthiness.insurance_expiring'
    INSURANCE_EXPIRED = 'airworthiness.insurance_expired'
    AIRWORTHINESS_STATUS_CHANGED = 'airworthiness.status_changed'


# Event schemas for validation and documentation
EVENT_SCHEMAS = {
    AircraftEvents.AIRCRAFT_CREATED: {
        'required': ['aircraft_id', 'organization_id', 'registration'],
        'optional': ['aircraft_type', 'category', 'created_by'],
    },
    AircraftEvents.AIRCRAFT_UPDATED: {
        'required': ['aircraft_id', 'organization_id'],
        'optional': ['changed_fields', 'updated_by'],
    },
    AircraftEvents.AIRCRAFT_DELETED: {
        'required': ['aircraft_id', 'organization_id', 'registration'],
        'optional': ['deleted_by'],
    },
    AircraftEvents.AIRCRAFT_GROUNDED: {
        'required': ['aircraft_id', 'organization_id', 'registration', 'reason'],
        'optional': ['grounded_by'],
    },
    AircraftEvents.AIRCRAFT_UNGROUNDED: {
        'required': ['aircraft_id', 'organization_id', 'registration'],
        'optional': ['ungrounded_by'],
    },
    AircraftEvents.COUNTERS_UPDATED: {
        'required': ['aircraft_id', 'organization_id'],
        'optional': ['hobbs_time', 'tach_time', 'total_time', 'landings', 'cycles'],
    },
    AircraftEvents.FLIGHT_TIME_ADDED: {
        'required': ['aircraft_id', 'organization_id', 'flight_id', 'hobbs_time'],
        'optional': ['tach_time', 'landings', 'cycles', 'flight_date'],
    },
    AircraftEvents.SQUAWK_CREATED: {
        'required': ['squawk_id', 'aircraft_id', 'organization_id', 'squawk_number'],
        'optional': ['title', 'severity', 'is_grounding', 'reported_by'],
    },
    AircraftEvents.SQUAWK_RESOLVED: {
        'required': ['squawk_id', 'aircraft_id', 'organization_id'],
        'optional': ['resolved_by', 'resolution'],
    },
    AircraftEvents.GROUNDING_SQUAWK_REPORTED: {
        'required': ['squawk_id', 'aircraft_id', 'organization_id', 'registration'],
        'optional': ['title', 'reported_by'],
    },
    AircraftEvents.DOCUMENT_EXPIRING_SOON: {
        'required': ['document_id', 'aircraft_id', 'organization_id', 'document_type'],
        'optional': ['expiry_date', 'days_until_expiry'],
    },
    AircraftEvents.ENGINE_TBO_WARNING: {
        'required': ['engine_id', 'aircraft_id', 'organization_id'],
        'optional': ['hours_remaining', 'tbo_percentage'],
    },
}
