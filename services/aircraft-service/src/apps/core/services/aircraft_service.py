# services/aircraft-service/src/apps/core/services/aircraft_service.py
"""
Aircraft Service

Core business logic for aircraft management.
"""

import re
import logging
from decimal import Decimal
from datetime import date, datetime
from typing import Optional, List, Dict, Any
from uuid import UUID

from django.db import transaction
from django.db.models import Q
from django.core.cache import cache
from django.utils import timezone
from django.utils.text import slugify

from apps.core.models import (
    Aircraft,
    AircraftType,
    AircraftEngine,
    AircraftPropeller,
    AircraftTimeLog,
)

logger = logging.getLogger(__name__)

# Cache timeouts
AIRCRAFT_CACHE_TTL = 300  # 5 minutes
AIRCRAFT_LIST_CACHE_TTL = 60  # 1 minute


class AircraftService:
    """
    Service class for aircraft management operations.

    Handles:
    - Aircraft CRUD operations
    - Status management (ground/unground)
    - Availability checking
    - Counter management
    - Engine/propeller management
    """

    # ==========================================================================
    # Registration Validation Patterns
    # ==========================================================================

    REGISTRATION_PATTERNS = [
        r'^TC-[A-Z]{3}$',           # Turkey: TC-XXX
        r'^N\d{1,5}[A-Z]{0,2}$',    # USA: N12345, N1234A, N123AB
        r'^G-[A-Z]{4}$',            # UK: G-XXXX
        r'^D-[A-Z]{4}$',            # Germany: D-XXXX
        r'^F-[A-Z]{4}$',            # France: F-XXXX
        r'^I-[A-Z]{4}$',            # Italy: I-XXXX
        r'^EC-[A-Z]{3}$',           # Spain: EC-XXX
        r'^PH-[A-Z]{3}$',           # Netherlands: PH-XXX
        r'^SE-[A-Z]{3}$',           # Sweden: SE-XXX
        r'^LN-[A-Z]{3}$',           # Norway: LN-XXX
        r'^OE-[A-Z]{3,4}$',         # Austria: OE-XXX(X)
        r'^HB-[A-Z]{3}$',           # Switzerland: HB-XXX
        r'^C-[A-Z]{4}$',            # Canada: C-XXXX
        r'^VH-[A-Z]{3}$',           # Australia: VH-XXX
        r'^ZK-[A-Z]{3}$',           # New Zealand: ZK-XXX
        r'^[A-Z]{2}-[A-Z]{3,4}$',   # Generic: XX-XXX(X)
    ]

    # ==========================================================================
    # CRUD Operations
    # ==========================================================================

    def create_aircraft(
        self,
        organization_id: UUID,
        registration: str,
        created_by_user_id: UUID,
        **kwargs
    ) -> Aircraft:
        """
        Create a new aircraft.

        Args:
            organization_id: Organization UUID
            registration: Aircraft registration
            created_by_user_id: User creating the aircraft
            **kwargs: Additional aircraft fields

        Returns:
            Created Aircraft instance

        Raises:
            AircraftValidationError: If validation fails
            AircraftConflictError: If registration already exists
        """
        from apps.core.services import AircraftValidationError, AircraftConflictError

        # Normalize and validate registration
        registration = registration.upper().strip()
        self._validate_registration(registration)

        # Check for duplicate
        if Aircraft.objects.filter(
            organization_id=organization_id,
            registration=registration,
            deleted_at__isnull=True
        ).exists():
            raise AircraftConflictError(
                f"Aircraft with registration {registration} already exists"
            )

        # Apply type defaults if aircraft_type is provided
        aircraft_type_id = kwargs.pop('aircraft_type_id', None)
        if aircraft_type_id:
            try:
                aircraft_type = AircraftType.objects.get(id=aircraft_type_id)
                kwargs = self._apply_type_defaults(aircraft_type, kwargs)
                kwargs['aircraft_type'] = aircraft_type
            except AircraftType.DoesNotExist:
                pass

        with transaction.atomic():
            aircraft = Aircraft.objects.create(
                organization_id=organization_id,
                registration=registration,
                created_by=created_by_user_id,
                **kwargs
            )

            # Create initial time log entry
            AircraftTimeLog.objects.create(
                aircraft=aircraft,
                source_type=AircraftTimeLog.SourceType.INITIAL,
                log_date=date.today(),
                hobbs_after=aircraft.hobbs_time,
                tach_after=aircraft.tach_time,
                total_time_after=aircraft.total_time_hours,
                landings_after=aircraft.total_landings,
                cycles_after=aircraft.total_cycles,
                created_by=created_by_user_id,
                notes='Initial aircraft entry'
            )

            # Invalidate cache
            self._invalidate_list_cache(organization_id)

            logger.info(f"Aircraft created: {registration} for org {organization_id}")

        return aircraft

    def get_aircraft(
        self,
        aircraft_id: UUID,
        organization_id: UUID = None
    ) -> Optional[Aircraft]:
        """
        Get aircraft by ID.

        Args:
            aircraft_id: Aircraft UUID
            organization_id: Optional org filter for security

        Returns:
            Aircraft instance or None
        """
        cache_key = f"aircraft:{aircraft_id}"
        aircraft = cache.get(cache_key)

        if aircraft is None:
            try:
                queryset = Aircraft.objects.select_related('aircraft_type')

                if organization_id:
                    queryset = queryset.filter(organization_id=organization_id)

                aircraft = queryset.get(
                    id=aircraft_id,
                    deleted_at__isnull=True
                )
                cache.set(cache_key, aircraft, AIRCRAFT_CACHE_TTL)
            except Aircraft.DoesNotExist:
                return None

        return aircraft

    def get_aircraft_by_registration(
        self,
        organization_id: UUID,
        registration: str
    ) -> Optional[Aircraft]:
        """Get aircraft by registration within organization."""
        try:
            return Aircraft.objects.get(
                organization_id=organization_id,
                registration=registration.upper().strip(),
                deleted_at__isnull=True
            )
        except Aircraft.DoesNotExist:
            return None

    def list_aircraft(
        self,
        organization_id: UUID,
        status: str = None,
        category: str = None,
        location_id: UUID = None,
        available_only: bool = False,
        search: str = None,
        include_deleted: bool = False
    ) -> List[Aircraft]:
        """
        List aircraft with filters.

        Args:
            organization_id: Organization UUID
            status: Filter by status
            category: Filter by category
            location_id: Filter by location
            available_only: Only available aircraft
            search: Search in registration/model
            include_deleted: Include soft-deleted

        Returns:
            List of Aircraft
        """
        queryset = Aircraft.objects.filter(
            organization_id=organization_id
        ).select_related('aircraft_type')

        if not include_deleted:
            queryset = queryset.filter(deleted_at__isnull=True)

        if status:
            queryset = queryset.filter(status=status)

        if category:
            queryset = queryset.filter(category=category)

        if location_id:
            queryset = queryset.filter(
                Q(home_base_id=location_id) |
                Q(current_location_id=location_id)
            )

        if available_only:
            queryset = queryset.filter(
                status=Aircraft.Status.ACTIVE,
                operational_status=Aircraft.OperationalStatus.AVAILABLE,
                is_airworthy=True,
                has_grounding_squawks=False
            )

        if search:
            queryset = queryset.filter(
                Q(registration__icontains=search) |
                Q(model__icontains=search) |
                Q(manufacturer__icontains=search) |
                Q(serial_number__icontains=search)
            )

        return list(queryset.order_by('display_order', 'registration'))

    def update_aircraft(
        self,
        aircraft_id: UUID,
        organization_id: UUID,
        updated_by_user_id: UUID,
        **kwargs
    ) -> Aircraft:
        """
        Update aircraft.

        Args:
            aircraft_id: Aircraft UUID
            organization_id: Organization UUID for security
            updated_by_user_id: User making update
            **kwargs: Fields to update

        Returns:
            Updated Aircraft

        Raises:
            AircraftNotFoundError: If not found
        """
        from apps.core.services import AircraftNotFoundError

        aircraft = self.get_aircraft(aircraft_id, organization_id)
        if not aircraft:
            raise AircraftNotFoundError(f"Aircraft {aircraft_id} not found")

        # Validate registration if being changed
        new_registration = kwargs.get('registration')
        if new_registration and new_registration.upper() != aircraft.registration:
            new_registration = new_registration.upper().strip()
            self._validate_registration(new_registration)

            # Check for conflict
            from apps.core.services import AircraftConflictError
            if Aircraft.objects.filter(
                organization_id=organization_id,
                registration=new_registration,
                deleted_at__isnull=True
            ).exclude(id=aircraft_id).exists():
                raise AircraftConflictError(
                    f"Aircraft with registration {new_registration} already exists"
                )
            kwargs['registration'] = new_registration

        # Update fields
        kwargs['updated_by'] = updated_by_user_id
        for field, value in kwargs.items():
            if hasattr(aircraft, field):
                setattr(aircraft, field, value)

        aircraft.save()

        # Invalidate caches
        self._invalidate_cache(aircraft_id)
        self._invalidate_list_cache(organization_id)

        logger.info(f"Aircraft updated: {aircraft.registration}")

        return aircraft

    def delete_aircraft(
        self,
        aircraft_id: UUID,
        organization_id: UUID,
        deleted_by_user_id: UUID
    ) -> None:
        """
        Soft delete aircraft.

        Args:
            aircraft_id: Aircraft UUID
            organization_id: Organization UUID
            deleted_by_user_id: User deleting
        """
        from apps.core.services import AircraftNotFoundError

        aircraft = self.get_aircraft(aircraft_id, organization_id)
        if not aircraft:
            raise AircraftNotFoundError(f"Aircraft {aircraft_id} not found")

        aircraft.soft_delete()

        # Invalidate caches
        self._invalidate_cache(aircraft_id)
        self._invalidate_list_cache(organization_id)

        logger.info(f"Aircraft deleted: {aircraft.registration}")

    # ==========================================================================
    # Status Management
    # ==========================================================================

    def get_aircraft_status(
        self,
        aircraft_id: UUID,
        organization_id: UUID = None
    ) -> Dict[str, Any]:
        """
        Get comprehensive aircraft status.

        Returns status including:
        - Current operational status
        - Airworthiness info
        - Open squawks
        - Certificate expiry warnings
        - Counter values
        """
        from apps.core.services import AircraftNotFoundError

        aircraft = self.get_aircraft(aircraft_id, organization_id)
        if not aircraft:
            raise AircraftNotFoundError(f"Aircraft {aircraft_id} not found")

        warnings = []
        blockers = []

        # Squawk checks
        if aircraft.has_grounding_squawks:
            blockers.append({
                'type': 'squawk',
                'message': 'Grounding squawk(s) exist',
                'count': aircraft.open_squawk_count
            })
        elif aircraft.has_open_squawks:
            warnings.append({
                'type': 'squawk',
                'message': f'{aircraft.open_squawk_count} open squawk(s)',
                'count': aircraft.open_squawk_count
            })

        # ARC expiry check
        if aircraft.arc_expiry_date:
            days = aircraft.arc_days_remaining
            if days is not None:
                if days < 0:
                    blockers.append({
                        'type': 'arc',
                        'message': 'ARC has expired',
                        'expiry_date': aircraft.arc_expiry_date.isoformat()
                    })
                elif days <= 30:
                    warnings.append({
                        'type': 'arc',
                        'message': f'ARC expires in {days} days',
                        'expiry_date': aircraft.arc_expiry_date.isoformat(),
                        'days_remaining': days
                    })

        # Insurance expiry check
        if aircraft.insurance_expiry_date:
            days = aircraft.insurance_days_remaining
            if days is not None:
                if days < 0:
                    blockers.append({
                        'type': 'insurance',
                        'message': 'Insurance has expired',
                        'expiry_date': aircraft.insurance_expiry_date.isoformat()
                    })
                elif days <= 30:
                    warnings.append({
                        'type': 'insurance',
                        'message': f'Insurance expires in {days} days',
                        'expiry_date': aircraft.insurance_expiry_date.isoformat(),
                        'days_remaining': days
                    })

        # Engine TBO checks
        for engine in aircraft.engines.all():
            if engine.is_tbo_exceeded:
                warnings.append({
                    'type': 'engine_tbo',
                    'message': f'Engine #{engine.position} TBO exceeded',
                    'engine_position': engine.position,
                    'tsmoh': float(engine.tsmoh),
                    'tbo': engine.tbo_hours
                })
            elif engine.hours_until_tbo and engine.hours_until_tbo < Decimal('50'):
                warnings.append({
                    'type': 'engine_tbo',
                    'message': f'Engine #{engine.position}: {engine.hours_until_tbo:.1f}h until TBO',
                    'engine_position': engine.position,
                    'hours_until_tbo': float(engine.hours_until_tbo)
                })

        return {
            'aircraft_id': str(aircraft.id),
            'registration': aircraft.registration,
            'status': aircraft.status,
            'operational_status': aircraft.operational_status,
            'is_airworthy': aircraft.is_airworthy,
            'is_available': aircraft.is_available and len(blockers) == 0,
            'grounded_reason': aircraft.grounded_reason,
            'grounded_at': aircraft.grounded_at.isoformat() if aircraft.grounded_at else None,
            'counters': {
                'total_time': float(aircraft.total_time_hours),
                'hobbs': float(aircraft.hobbs_time),
                'tach': float(aircraft.tach_time),
                'landings': aircraft.total_landings,
                'cycles': aircraft.total_cycles
            },
            'warnings': warnings,
            'blockers': blockers,
            'last_updated': aircraft.updated_at.isoformat()
        }

    def ground_aircraft(
        self,
        aircraft_id: UUID,
        organization_id: UUID,
        reason: str,
        grounded_by_user_id: UUID
    ) -> Aircraft:
        """Ground an aircraft."""
        from apps.core.services import AircraftNotFoundError

        aircraft = self.get_aircraft(aircraft_id, organization_id)
        if not aircraft:
            raise AircraftNotFoundError(f"Aircraft {aircraft_id} not found")

        aircraft.ground(reason, grounded_by_user_id)

        self._invalidate_cache(aircraft_id)
        self._invalidate_list_cache(organization_id)

        logger.info(f"Aircraft grounded: {aircraft.registration} - {reason}")

        return aircraft

    def unground_aircraft(
        self,
        aircraft_id: UUID,
        organization_id: UUID,
        ungrounded_by_user_id: UUID
    ) -> Aircraft:
        """Remove ground status from aircraft."""
        from apps.core.services import AircraftNotFoundError

        aircraft = self.get_aircraft(aircraft_id, organization_id)
        if not aircraft:
            raise AircraftNotFoundError(f"Aircraft {aircraft_id} not found")

        # Check for grounding squawks
        if aircraft.has_grounding_squawks:
            from apps.core.services import AircraftValidationError
            raise AircraftValidationError(
                "Cannot unground: grounding squawk(s) still exist"
            )

        aircraft.unground()

        self._invalidate_cache(aircraft_id)
        self._invalidate_list_cache(organization_id)

        logger.info(f"Aircraft ungrounded: {aircraft.registration}")

        return aircraft

    # ==========================================================================
    # Availability
    # ==========================================================================

    def check_availability(
        self,
        aircraft_id: UUID,
        organization_id: UUID,
        start_time: datetime,
        end_time: datetime,
        exclude_booking_id: UUID = None
    ) -> Dict[str, Any]:
        """
        Check aircraft availability for a time period.

        Returns:
            Dict with availability status and any conflicts
        """
        status = self.get_aircraft_status(aircraft_id, organization_id)

        if not status['is_available']:
            return {
                'available': False,
                'reason': 'aircraft_not_available',
                'blockers': status['blockers']
            }

        # TODO: Integrate with booking-service to check conflicts
        # This would be an inter-service call

        return {
            'available': True,
            'warnings': status['warnings'],
            'aircraft': {
                'id': status['aircraft_id'],
                'registration': status['registration'],
                'counters': status['counters']
            }
        }

    # ==========================================================================
    # Engine & Propeller Management
    # ==========================================================================

    def add_engine(
        self,
        aircraft_id: UUID,
        organization_id: UUID,
        position: int,
        **kwargs
    ) -> AircraftEngine:
        """Add engine to aircraft."""
        from apps.core.services import AircraftNotFoundError

        aircraft = self.get_aircraft(aircraft_id, organization_id)
        if not aircraft:
            raise AircraftNotFoundError(f"Aircraft {aircraft_id} not found")

        engine = AircraftEngine.objects.create(
            aircraft=aircraft,
            position=position,
            **kwargs
        )

        logger.info(f"Engine added to {aircraft.registration} at position {position}")

        return engine

    def add_propeller(
        self,
        aircraft_id: UUID,
        organization_id: UUID,
        position: int,
        engine_id: UUID = None,
        **kwargs
    ) -> AircraftPropeller:
        """Add propeller to aircraft."""
        from apps.core.services import AircraftNotFoundError

        aircraft = self.get_aircraft(aircraft_id, organization_id)
        if not aircraft:
            raise AircraftNotFoundError(f"Aircraft {aircraft_id} not found")

        engine = None
        if engine_id:
            try:
                engine = AircraftEngine.objects.get(
                    id=engine_id,
                    aircraft=aircraft
                )
            except AircraftEngine.DoesNotExist:
                pass

        propeller = AircraftPropeller.objects.create(
            aircraft=aircraft,
            engine=engine,
            position=position,
            **kwargs
        )

        logger.info(f"Propeller added to {aircraft.registration} at position {position}")

        return propeller

    # ==========================================================================
    # Helper Methods
    # ==========================================================================

    def _validate_registration(self, registration: str) -> None:
        """Validate registration format."""
        from apps.core.services import AircraftValidationError

        for pattern in self.REGISTRATION_PATTERNS:
            if re.match(pattern, registration):
                return

        raise AircraftValidationError(
            f"Invalid registration format: {registration}"
        )

    def _apply_type_defaults(
        self,
        aircraft_type: AircraftType,
        kwargs: dict
    ) -> dict:
        """Apply defaults from aircraft type."""
        defaults = {
            'manufacturer': aircraft_type.manufacturer,
            'model': aircraft_type.model,
            'variant': aircraft_type.variant,
            'category': aircraft_type.category,
            'aircraft_class': aircraft_type.aircraft_class,
            'is_complex': aircraft_type.is_complex,
            'is_high_performance': aircraft_type.is_high_performance,
            'engine_count': aircraft_type.engine_count,
            'engine_type': aircraft_type.engine_type,
        }

        if aircraft_type.default_seat_count:
            defaults['seat_count'] = aircraft_type.default_seat_count
        if aircraft_type.default_fuel_capacity:
            defaults['fuel_capacity_liters'] = aircraft_type.default_fuel_capacity
        if aircraft_type.default_fuel_burn:
            defaults['fuel_consumption_lph'] = aircraft_type.default_fuel_burn
        if aircraft_type.default_cruise_speed:
            defaults['cruise_speed_kts'] = aircraft_type.default_cruise_speed

        # Only apply defaults if not already provided
        for key, value in defaults.items():
            if key not in kwargs or kwargs[key] is None:
                kwargs[key] = value

        return kwargs

    def _invalidate_cache(self, aircraft_id: UUID) -> None:
        """Invalidate aircraft cache."""
        cache.delete(f"aircraft:{aircraft_id}")

    def _invalidate_list_cache(self, organization_id: UUID) -> None:
        """Invalidate list cache for organization."""
        cache.delete(f"aircraft_list:{organization_id}")
