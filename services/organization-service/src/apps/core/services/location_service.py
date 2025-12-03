# services/organization-service/src/apps/core/services/location_service.py
"""
Location Service

Business logic for location management including:
- Location CRUD operations
- Operating hours management
- Facility management
- Weather integration
"""

import logging
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.core.cache import cache

from apps.core.models import Location, Organization

logger = logging.getLogger(__name__)


# ==================== EXCEPTIONS ====================

class LocationError(Exception):
    """Base exception for location errors."""
    pass


class LocationNotFoundError(LocationError):
    """Raised when location is not found."""
    pass


class LocationValidationError(LocationError):
    """Raised when location validation fails."""
    pass


# ==================== SERVICE ====================

class LocationService:
    """
    Service for location management.

    Provides comprehensive location management including
    CRUD operations, operating hours, and weather integration.
    """

    CACHE_TTL = 300  # 5 minutes
    CACHE_PREFIX = 'location'

    def __init__(self):
        self._event_publisher = None

    # ==================== CRUD OPERATIONS ====================

    def create_location(
        self,
        organization_id: UUID,
        name: str,
        location_type: str = 'base',
        **kwargs
    ) -> Location:
        """
        Create a new location.

        Args:
            organization_id: Organization UUID
            name: Location name
            location_type: Type of location
            **kwargs: Additional location fields

        Returns:
            Created Location instance

        Raises:
            LocationValidationError: If validation fails
        """
        # Check organization exists
        try:
            org = Organization.objects.get(id=organization_id, deleted_at__isnull=True)
        except Organization.DoesNotExist:
            raise LocationValidationError(f"Organization {organization_id} not found")

        # Check location limit
        current_count = Location.objects.filter(
            organization_id=organization_id,
            is_active=True
        ).count()

        if org.max_locations != -1 and current_count >= org.max_locations:
            raise LocationValidationError(
                f"Location limit reached ({org.max_locations}). "
                "Upgrade your plan to add more locations."
            )

        # Validate ICAO code if provided
        if kwargs.get('airport_icao'):
            self._validate_icao_code(kwargs['airport_icao'])

        with transaction.atomic():
            # Check if this is the first location
            is_first = not Location.objects.filter(organization_id=organization_id).exists()

            location = Location.objects.create(
                organization_id=organization_id,
                name=name,
                location_type=location_type,
                is_primary=is_first or kwargs.pop('is_primary', False),
                **kwargs
            )

            logger.info(f"Created location: {location.name} ({location.id})")

            # Publish event
            self._publish_event('location.created', {
                'location_id': str(location.id),
                'organization_id': str(organization_id),
                'name': location.name,
                'airport_icao': location.airport_icao,
            })

            return location

    def get_location(
        self,
        location_id: UUID,
        organization_id: UUID = None
    ) -> Optional[Location]:
        """
        Get location by ID.

        Args:
            location_id: Location UUID
            organization_id: Optional organization filter

        Returns:
            Location instance or None
        """
        cache_key = f"{self.CACHE_PREFIX}:{location_id}"
        cached = cache.get(cache_key)
        if cached:
            if organization_id and str(cached.organization_id) != str(organization_id):
                return None
            return cached

        try:
            queryset = Location.objects.select_related('organization')
            if organization_id:
                queryset = queryset.filter(organization_id=organization_id)

            location = queryset.get(id=location_id)
            cache.set(cache_key, location, self.CACHE_TTL)
            return location
        except Location.DoesNotExist:
            return None

    def update_location(
        self,
        location_id: UUID,
        organization_id: UUID,
        data: Dict[str, Any]
    ) -> Location:
        """
        Update location.

        Args:
            location_id: Location UUID
            organization_id: Organization UUID
            data: Fields to update

        Returns:
            Updated Location instance
        """
        location = self.get_location(location_id, organization_id)
        if not location:
            raise LocationNotFoundError(f"Location {location_id} not found")

        # Define allowed fields
        allowed_fields = {
            'name', 'code', 'description', 'location_type',
            'airport_icao', 'airport_iata', 'airport_name',
            'email', 'phone',
            'address_line1', 'address_line2', 'city', 'state_province',
            'postal_code', 'country_code',
            'latitude', 'longitude', 'elevation_ft',
            'is_active', 'operating_hours', 'timezone',
            'facilities', 'runways', 'frequencies',
            'weather_station_id', 'notes', 'pilot_notes',
            'photo_url', 'metadata', 'display_order'
        }

        # Filter and validate
        update_data = {k: v for k, v in data.items() if k in allowed_fields}

        if 'airport_icao' in update_data and update_data['airport_icao']:
            self._validate_icao_code(update_data['airport_icao'])

        # Apply updates
        changed_fields = []
        for field, value in update_data.items():
            if getattr(location, field) != value:
                changed_fields.append(field)
                setattr(location, field, value)

        if changed_fields:
            location.save()
            self._invalidate_cache(location)

            logger.info(f"Updated location {location.id}: {changed_fields}")

            self._publish_event('location.updated', {
                'location_id': str(location.id),
                'organization_id': str(organization_id),
                'changed_fields': changed_fields,
            })

        return location

    def delete_location(
        self,
        location_id: UUID,
        organization_id: UUID
    ) -> bool:
        """
        Delete a location.

        Args:
            location_id: Location UUID
            organization_id: Organization UUID

        Returns:
            True if deleted
        """
        location = self.get_location(location_id, organization_id)
        if not location:
            raise LocationNotFoundError(f"Location {location_id} not found")

        # Don't allow deleting the only location
        location_count = Location.objects.filter(
            organization_id=organization_id
        ).count()

        if location_count <= 1:
            raise LocationValidationError(
                "Cannot delete the only location. "
                "Create another location first."
            )

        # If deleting primary, make another one primary
        if location.is_primary:
            other_location = Location.objects.filter(
                organization_id=organization_id
            ).exclude(id=location_id).first()

            if other_location:
                other_location.is_primary = True
                other_location.save()

        location_name = location.name
        location.delete()

        self._invalidate_cache(location)

        logger.info(f"Deleted location: {location_name} ({location_id})")

        self._publish_event('location.deleted', {
            'location_id': str(location_id),
            'organization_id': str(organization_id),
            'name': location_name,
        })

        return True

    def list_locations(
        self,
        organization_id: UUID,
        is_active: bool = None,
        location_type: str = None,
        search: str = None
    ) -> List[Location]:
        """
        List locations for an organization.

        Args:
            organization_id: Organization UUID
            is_active: Filter by active status
            location_type: Filter by type
            search: Search in name, code, airport

        Returns:
            List of Location instances
        """
        queryset = Location.objects.filter(organization_id=organization_id)

        if is_active is not None:
            queryset = queryset.filter(is_active=is_active)
        if location_type:
            queryset = queryset.filter(location_type=location_type)
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(code__icontains=search) |
                Q(airport_icao__icontains=search) |
                Q(airport_name__icontains=search) |
                Q(city__icontains=search)
            )

        return list(queryset.order_by('display_order', 'name'))

    # ==================== PRIMARY LOCATION ====================

    def set_primary(
        self,
        organization_id: UUID,
        location_id: UUID
    ) -> Location:
        """
        Set a location as primary.

        Args:
            organization_id: Organization UUID
            location_id: Location UUID

        Returns:
            Updated Location instance
        """
        location = self.get_location(location_id, organization_id)
        if not location:
            raise LocationNotFoundError(f"Location {location_id} not found")

        with transaction.atomic():
            # Remove primary from all other locations
            Location.objects.filter(
                organization_id=organization_id,
                is_primary=True
            ).exclude(id=location_id).update(is_primary=False)

            # Set this one as primary
            location.is_primary = True
            location.save()

        self._invalidate_org_locations_cache(organization_id)

        logger.info(f"Set primary location: {location.name} ({location.id})")

        return location

    def get_primary_location(self, organization_id: UUID) -> Optional[Location]:
        """Get the primary location for an organization."""
        cache_key = f"{self.CACHE_PREFIX}:primary:{organization_id}"
        cached = cache.get(cache_key)
        if cached:
            return cached

        location = Location.objects.filter(
            organization_id=organization_id,
            is_primary=True
        ).first()

        if location:
            cache.set(cache_key, location, self.CACHE_TTL)

        return location

    # ==================== OPERATING HOURS ====================

    def update_operating_hours(
        self,
        location_id: UUID,
        organization_id: UUID,
        operating_hours: Dict[str, Any]
    ) -> Location:
        """
        Update location operating hours.

        Args:
            location_id: Location UUID
            organization_id: Organization UUID
            operating_hours: Operating hours dict

        Returns:
            Updated Location instance
        """
        location = self.get_location(location_id, organization_id)
        if not location:
            raise LocationNotFoundError(f"Location {location_id} not found")

        # Validate operating hours format
        self._validate_operating_hours(operating_hours)

        location.operating_hours = operating_hours
        location.save()

        self._invalidate_cache(location)

        return location

    def is_location_open(
        self,
        location_id: UUID,
        check_time: datetime = None
    ) -> Dict[str, Any]:
        """
        Check if location is open at a specific time.

        Args:
            location_id: Location UUID
            check_time: Time to check (defaults to now)

        Returns:
            Dict with open status and details
        """
        location = self.get_location(location_id)
        if not location:
            raise LocationNotFoundError(f"Location {location_id} not found")

        if check_time is None:
            check_time = timezone.now()

        # Convert to location timezone if set
        if location.timezone:
            import pytz
            tz = pytz.timezone(location.timezone)
            check_time = check_time.astimezone(tz)

        is_open = location.is_open_at(check_time)

        # Get today's hours
        day_name = check_time.strftime('%A').lower()
        day_hours = location.operating_hours.get(day_name, {})

        return {
            'is_open': is_open,
            'checked_at': check_time.isoformat(),
            'day': day_name,
            'hours': day_hours,
            'timezone': location.effective_timezone,
        }

    # ==================== FACILITIES ====================

    def update_facilities(
        self,
        location_id: UUID,
        organization_id: UUID,
        facilities: List[str]
    ) -> Location:
        """
        Update location facilities.

        Args:
            location_id: Location UUID
            organization_id: Organization UUID
            facilities: List of facility names

        Returns:
            Updated Location instance
        """
        location = self.get_location(location_id, organization_id)
        if not location:
            raise LocationNotFoundError(f"Location {location_id} not found")

        # Normalize facility names
        facilities = [f.lower().strip() for f in facilities]

        location.facilities = facilities
        location.save()

        self._invalidate_cache(location)

        return location

    # ==================== RUNWAY & FREQUENCY ====================

    def update_runways(
        self,
        location_id: UUID,
        organization_id: UUID,
        runways: List[Dict[str, Any]]
    ) -> Location:
        """
        Update location runway information.

        Args:
            location_id: Location UUID
            organization_id: Organization UUID
            runways: List of runway dicts

        Returns:
            Updated Location instance
        """
        location = self.get_location(location_id, organization_id)
        if not location:
            raise LocationNotFoundError(f"Location {location_id} not found")

        # Validate runway format
        for runway in runways:
            if 'designator' not in runway:
                raise LocationValidationError("Runway must have a designator")

        location.runways = runways
        location.save()

        self._invalidate_cache(location)

        return location

    def update_frequencies(
        self,
        location_id: UUID,
        organization_id: UUID,
        frequencies: List[Dict[str, Any]]
    ) -> Location:
        """
        Update location radio frequencies.

        Args:
            location_id: Location UUID
            organization_id: Organization UUID
            frequencies: List of frequency dicts

        Returns:
            Updated Location instance
        """
        location = self.get_location(location_id, organization_id)
        if not location:
            raise LocationNotFoundError(f"Location {location_id} not found")

        # Validate frequency format
        for freq in frequencies:
            if 'type' not in freq or 'frequency' not in freq:
                raise LocationValidationError(
                    "Frequency must have 'type' and 'frequency'"
                )

        location.frequencies = frequencies
        location.save()

        self._invalidate_cache(location)

        return location

    # ==================== WEATHER ====================

    def get_weather(self, location_id: UUID) -> Optional[Dict[str, Any]]:
        """
        Get weather information for a location.

        Args:
            location_id: Location UUID

        Returns:
            Dict with METAR/TAF information or None
        """
        location = self.get_location(location_id)
        if not location:
            raise LocationNotFoundError(f"Location {location_id} not found")

        if not location.airport_icao:
            return None

        # Try cache first
        cache_key = f"weather:{location.airport_icao}"
        cached = cache.get(cache_key)
        if cached:
            return cached

        # In production, this would call an external weather API
        # For now, return placeholder
        weather = {
            'icao': location.airport_icao,
            'metar': None,  # Would be fetched from API
            'taf': None,  # Would be fetched from API
            'fetched_at': timezone.now().isoformat(),
            'source': 'placeholder',
        }

        # Cache for 15 minutes
        cache.set(cache_key, weather, 900)

        return weather

    # ==================== PRIVATE METHODS ====================

    def _validate_icao_code(self, code: str) -> None:
        """Validate ICAO airport code."""
        import re
        if not re.match(r'^[A-Z]{4}$', code.upper()):
            raise LocationValidationError(
                f"Invalid ICAO code: {code}. Must be 4 uppercase letters."
            )

    def _validate_operating_hours(self, hours: Dict[str, Any]) -> None:
        """Validate operating hours format."""
        import re
        time_pattern = r'^([01]\d|2[0-3]):([0-5]\d)$'

        valid_days = [
            'monday', 'tuesday', 'wednesday', 'thursday',
            'friday', 'saturday', 'sunday'
        ]

        for day, day_hours in hours.items():
            if day == 'holidays':
                # Validate holidays format
                if not isinstance(day_hours, list):
                    raise LocationValidationError("holidays must be a list")
                continue

            if day not in valid_days:
                raise LocationValidationError(f"Invalid day: {day}")

            if not isinstance(day_hours, dict):
                raise LocationValidationError(f"Hours for {day} must be a dict")

            if day_hours.get('closed'):
                continue

            open_time = day_hours.get('open')
            close_time = day_hours.get('close')

            if open_time and not re.match(time_pattern, open_time):
                raise LocationValidationError(
                    f"Invalid open time for {day}: {open_time}"
                )
            if close_time and not re.match(time_pattern, close_time):
                raise LocationValidationError(
                    f"Invalid close time for {day}: {close_time}"
                )

    def _invalidate_cache(self, location: Location) -> None:
        """Invalidate caches for a location."""
        cache.delete(f"{self.CACHE_PREFIX}:{location.id}")
        cache.delete(f"{self.CACHE_PREFIX}:primary:{location.organization_id}")

    def _invalidate_org_locations_cache(self, organization_id: UUID) -> None:
        """Invalidate all location caches for an organization."""
        cache.delete(f"{self.CACHE_PREFIX}:primary:{organization_id}")
        # Would need to track and clear individual location caches

    def _publish_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Publish an event."""
        try:
            from apps.core.events import publish_event
            publish_event(event_type, data)
        except Exception as e:
            logger.error(f"Failed to publish event {event_type}: {e}")
