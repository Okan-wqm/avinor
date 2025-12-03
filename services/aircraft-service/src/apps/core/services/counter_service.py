# services/aircraft-service/src/apps/core/services/counter_service.py
"""
Counter Service

Manages aircraft time counters, adjustments, and history.
"""

import uuid
import logging
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Optional, Dict, Any, List

from django.db import transaction
from django.db.models import Sum, Avg, Max, Min
from django.core.cache import cache

from apps.core.models import Aircraft, AircraftTimeLog, AircraftEngine

logger = logging.getLogger(__name__)


class CounterService:
    """
    Service for managing aircraft counters and time tracking.

    Handles:
    - Counter retrieval
    - Flight time additions
    - Manual adjustments with audit trail
    - Counter history and reporting
    """

    CACHE_TTL = 60  # 1 minute cache

    # ==========================================================================
    # Counter Retrieval
    # ==========================================================================

    def get_counters(self, aircraft_id: uuid.UUID) -> Dict[str, Any]:
        """
        Get current counter values for an aircraft.

        Returns all counter values and their status.
        """
        cache_key = f"aircraft_counters:{aircraft_id}"
        cached = cache.get(cache_key)
        if cached:
            return cached

        try:
            aircraft = Aircraft.objects.select_related('aircraft_type').get(
                id=aircraft_id,
                deleted_at__isnull=True
            )
        except Aircraft.DoesNotExist:
            from . import AircraftNotFoundError
            raise AircraftNotFoundError(f"Aircraft {aircraft_id} not found")

        counters = {
            'aircraft_id': str(aircraft.id),
            'registration': aircraft.registration,

            # Primary Counters
            'hobbs_time': float(aircraft.hobbs_time or 0),
            'tach_time': float(aircraft.tach_time or 0),
            'total_time_hours': float(aircraft.total_time_hours or 0),
            'total_landings': aircraft.total_landings or 0,
            'total_cycles': aircraft.total_cycles or 0,

            # Billing
            'billing_time_source': aircraft.billing_time_source,

            # Engine Times
            'engines': self._get_engine_counters(aircraft),

            # Last Update
            'last_hobbs_update': aircraft.last_hobbs_update.isoformat() if aircraft.last_hobbs_update else None,
            'updated_at': aircraft.updated_at.isoformat(),
        }

        cache.set(cache_key, counters, self.CACHE_TTL)
        return counters

    def _get_engine_counters(self, aircraft: Aircraft) -> List[Dict[str, Any]]:
        """Get engine-specific counters."""
        engines = aircraft.engines.filter(is_active=True).order_by('position')

        return [
            {
                'position': engine.position,
                'serial_number': engine.serial_number,
                'tsn': float(engine.tsn or 0),
                'tso': float(engine.tso or 0),
                'tbo': float(engine.tbo_hours or 0),
                'hours_until_tbo': float(engine.hours_until_tbo) if engine.hours_until_tbo else None,
                'tbo_percentage': float(engine.tbo_percentage) if engine.tbo_percentage else None,
            }
            for engine in engines
        ]

    # ==========================================================================
    # Flight Time Addition
    # ==========================================================================

    @transaction.atomic
    def add_flight_time(
        self,
        aircraft_id: uuid.UUID,
        flight_id: uuid.UUID,
        hobbs_time: Decimal,
        tach_time: Decimal = None,
        landings: int = 0,
        cycles: int = 0,
        flight_date: date = None,
        engine_times: Dict[int, Decimal] = None,
        created_by: uuid.UUID = None,
        notes: str = None
    ) -> Dict[str, Any]:
        """
        Add flight time to aircraft counters.

        Creates a time log entry and updates all counters.
        """
        try:
            aircraft = Aircraft.objects.select_for_update().get(
                id=aircraft_id,
                deleted_at__isnull=True
            )
        except Aircraft.DoesNotExist:
            from . import AircraftNotFoundError
            raise AircraftNotFoundError(f"Aircraft {aircraft_id} not found")

        # Validate time values
        if hobbs_time < 0:
            from . import CounterError
            raise CounterError("Hobbs time cannot be negative")

        if tach_time is not None and tach_time < 0:
            from . import CounterError
            raise CounterError("Tach time cannot be negative")

        # Create time log entry
        time_log = AircraftTimeLog.create_from_flight(
            aircraft=aircraft,
            flight_id=flight_id,
            hobbs_change=hobbs_time,
            tach_change=tach_time,
            landings=landings,
            cycles=cycles,
            flight_date=flight_date or date.today(),
            created_by=created_by,
            notes=notes
        )

        # Update aircraft counters
        aircraft.update_counters(
            hobbs_time=hobbs_time,
            tach_time=tach_time,
            landings=landings,
            cycles=cycles
        )

        # Update engine times if provided
        if engine_times:
            self._update_engine_times(aircraft, engine_times, time_log)

        # Clear cache
        self._invalidate_cache(aircraft_id)

        logger.info(
            f"Added flight time to aircraft {aircraft.registration}: "
            f"hobbs={hobbs_time}, tach={tach_time}, landings={landings}"
        )

        return {
            'time_log_id': str(time_log.id),
            'new_counters': self.get_counters(aircraft_id)
        }

    def _update_engine_times(
        self,
        aircraft: Aircraft,
        engine_times: Dict[int, Decimal],
        time_log: AircraftTimeLog
    ) -> None:
        """Update individual engine times."""
        engine_log_data = {}

        for position, hours in engine_times.items():
            try:
                engine = aircraft.engines.get(position=position, is_active=True)
                before = engine.tsn
                engine.add_hours(hours)
                engine_log_data[str(position)] = {
                    'before': float(before),
                    'after': float(engine.tsn),
                    'change': float(hours)
                }
            except AircraftEngine.DoesNotExist:
                logger.warning(
                    f"Engine at position {position} not found for aircraft {aircraft.registration}"
                )

        # Update time log with engine data
        if engine_log_data:
            time_log.engine_times = engine_log_data
            time_log.save(update_fields=['engine_times'])

    # ==========================================================================
    # Manual Adjustments
    # ==========================================================================

    @transaction.atomic
    def adjust_counter(
        self,
        aircraft_id: uuid.UUID,
        field: str,
        new_value: Decimal,
        reason: str,
        created_by: uuid.UUID,
        created_by_name: str = None
    ) -> Dict[str, Any]:
        """
        Make a manual adjustment to a counter.

        Requires a reason and creates an audit trail.
        """
        valid_fields = [
            'hobbs_time', 'tach_time', 'total_time_hours',
            'total_landings', 'total_cycles'
        ]

        if field not in valid_fields:
            from . import CounterError
            raise CounterError(f"Invalid field: {field}. Must be one of {valid_fields}")

        if not reason or len(reason.strip()) < 10:
            from . import CounterError
            raise CounterError("Adjustment reason must be at least 10 characters")

        try:
            aircraft = Aircraft.objects.select_for_update().get(
                id=aircraft_id,
                deleted_at__isnull=True
            )
        except Aircraft.DoesNotExist:
            from . import AircraftNotFoundError
            raise AircraftNotFoundError(f"Aircraft {aircraft_id} not found")

        # Get current value
        current_value = getattr(aircraft, field) or 0

        # Create adjustment log
        time_log = AircraftTimeLog.create_adjustment(
            aircraft=aircraft,
            field=field,
            new_value=new_value,
            reason=reason,
            created_by=created_by,
            created_by_name=created_by_name
        )

        # Update the field
        setattr(aircraft, field, new_value)
        aircraft.save(update_fields=[field, 'updated_at'])

        # Clear cache
        self._invalidate_cache(aircraft_id)

        logger.info(
            f"Counter adjustment on {aircraft.registration}: "
            f"{field} changed from {current_value} to {new_value}. "
            f"Reason: {reason}"
        )

        return {
            'time_log_id': str(time_log.id),
            'field': field,
            'previous_value': float(current_value) if isinstance(current_value, Decimal) else current_value,
            'new_value': float(new_value) if isinstance(new_value, Decimal) else new_value,
            'change': float(new_value - Decimal(str(current_value))),
            'reason': reason,
            'adjusted_by': str(created_by),
            'adjusted_at': time_log.created_at.isoformat()
        }

    @transaction.atomic
    def adjust_engine_counter(
        self,
        aircraft_id: uuid.UUID,
        engine_position: int,
        field: str,
        new_value: Decimal,
        reason: str,
        created_by: uuid.UUID
    ) -> Dict[str, Any]:
        """Adjust an engine-specific counter."""
        valid_fields = ['tsn', 'tso', 'tbo_hours']

        if field not in valid_fields:
            from . import CounterError
            raise CounterError(f"Invalid field: {field}")

        try:
            aircraft = Aircraft.objects.get(
                id=aircraft_id,
                deleted_at__isnull=True
            )
            engine = aircraft.engines.select_for_update().get(
                position=engine_position,
                is_active=True
            )
        except Aircraft.DoesNotExist:
            from . import AircraftNotFoundError
            raise AircraftNotFoundError(f"Aircraft {aircraft_id} not found")
        except AircraftEngine.DoesNotExist:
            from . import CounterError
            raise CounterError(f"Engine at position {engine_position} not found")

        current_value = getattr(engine, field) or 0

        # Update engine
        setattr(engine, field, new_value)
        engine.save(update_fields=[field, 'updated_at'])

        # Create a time log entry for engine adjustment
        time_log = AircraftTimeLog.objects.create(
            aircraft=aircraft,
            source_type=AircraftTimeLog.SourceType.ADJUSTMENT,
            log_date=date.today(),
            adjustment_reason=f"Engine {engine_position} {field}: {reason}",
            created_by=created_by,
            engine_times={
                str(engine_position): {
                    'field': field,
                    'before': float(current_value),
                    'after': float(new_value),
                    'change': float(new_value - Decimal(str(current_value)))
                }
            }
        )

        self._invalidate_cache(aircraft_id)

        return {
            'time_log_id': str(time_log.id),
            'engine_position': engine_position,
            'field': field,
            'previous_value': float(current_value),
            'new_value': float(new_value)
        }

    # ==========================================================================
    # Counter History
    # ==========================================================================

    def get_time_logs(
        self,
        aircraft_id: uuid.UUID,
        start_date: date = None,
        end_date: date = None,
        source_type: str = None,
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """Get time log history for an aircraft."""
        logs = AircraftTimeLog.get_history(
            aircraft_id=aircraft_id,
            start_date=start_date,
            end_date=end_date,
            source_type=source_type,
            limit=limit + offset
        )[offset:offset + limit]

        return {
            'logs': [
                {
                    'id': str(log.id),
                    'source_type': log.source_type,
                    'source_id': str(log.source_id) if log.source_id else None,
                    'source_reference': log.source_reference,
                    'log_date': log.log_date.isoformat(),
                    'hobbs_change': float(log.hobbs_change),
                    'tach_change': float(log.tach_change),
                    'total_time_change': float(log.total_time_change),
                    'landings_change': log.landings_change,
                    'cycles_change': log.cycles_change,
                    'engine_times': log.engine_times,
                    'notes': log.notes,
                    'adjustment_reason': log.adjustment_reason,
                    'created_at': log.created_at.isoformat(),
                    'created_by': str(log.created_by) if log.created_by else None,
                    'created_by_name': log.created_by_name,
                }
                for log in logs
            ],
            'count': len(logs),
            'filters': {
                'start_date': start_date.isoformat() if start_date else None,
                'end_date': end_date.isoformat() if end_date else None,
                'source_type': source_type,
            }
        }

    def get_period_summary(
        self,
        aircraft_id: uuid.UUID,
        start_date: date,
        end_date: date
    ) -> Dict[str, Any]:
        """Get counter totals for a time period."""
        totals = AircraftTimeLog.get_totals_for_period(
            aircraft_id=aircraft_id,
            start_date=start_date,
            end_date=end_date
        )

        # Get flight count
        flight_count = AircraftTimeLog.objects.filter(
            aircraft_id=aircraft_id,
            source_type=AircraftTimeLog.SourceType.FLIGHT,
            log_date__gte=start_date,
            log_date__lte=end_date
        ).count()

        totals['flight_count'] = flight_count
        return totals

    def get_utilization_stats(
        self,
        aircraft_id: uuid.UUID,
        period_days: int = 30
    ) -> Dict[str, Any]:
        """Get utilization statistics for an aircraft."""
        end_date = date.today()
        start_date = end_date - timedelta(days=period_days)

        logs = AircraftTimeLog.objects.filter(
            aircraft_id=aircraft_id,
            source_type=AircraftTimeLog.SourceType.FLIGHT,
            log_date__gte=start_date,
            log_date__lte=end_date
        )

        stats = logs.aggregate(
            total_hobbs=Sum('hobbs_change'),
            total_landings=Sum('landings_change'),
            total_cycles=Sum('cycles_change'),
            avg_flight_time=Avg('hobbs_change'),
            max_flight_time=Max('hobbs_change'),
            min_flight_time=Min('hobbs_change'),
        )

        flight_count = logs.count()

        # Calculate daily average
        daily_avg = float(stats['total_hobbs'] or 0) / period_days if period_days > 0 else 0

        return {
            'period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat(),
                'days': period_days,
            },
            'totals': {
                'hobbs': float(stats['total_hobbs'] or 0),
                'landings': stats['total_landings'] or 0,
                'cycles': stats['total_cycles'] or 0,
                'flights': flight_count,
            },
            'averages': {
                'per_day': round(daily_avg, 2),
                'per_flight': float(stats['avg_flight_time'] or 0),
            },
            'ranges': {
                'max_flight': float(stats['max_flight_time'] or 0),
                'min_flight': float(stats['min_flight_time'] or 0),
            }
        }

    # ==========================================================================
    # Bulk Operations
    # ==========================================================================

    @transaction.atomic
    def bulk_import_counters(
        self,
        aircraft_id: uuid.UUID,
        counters: Dict[str, Any],
        import_date: date = None,
        created_by: uuid.UUID = None,
        notes: str = None
    ) -> Dict[str, Any]:
        """
        Import initial counter values (e.g., from data migration).

        Creates an INITIAL type time log entry.
        """
        try:
            aircraft = Aircraft.objects.select_for_update().get(
                id=aircraft_id,
                deleted_at__isnull=True
            )
        except Aircraft.DoesNotExist:
            from . import AircraftNotFoundError
            raise AircraftNotFoundError(f"Aircraft {aircraft_id} not found")

        log_date = import_date or date.today()

        # Create initial time log
        time_log = AircraftTimeLog.objects.create(
            aircraft=aircraft,
            source_type=AircraftTimeLog.SourceType.INITIAL,
            log_date=log_date,
            hobbs_before=aircraft.hobbs_time,
            hobbs_after=Decimal(str(counters.get('hobbs_time', aircraft.hobbs_time or 0))),
            hobbs_change=Decimal(str(counters.get('hobbs_time', 0))) - (aircraft.hobbs_time or 0),
            tach_before=aircraft.tach_time,
            tach_after=Decimal(str(counters.get('tach_time', aircraft.tach_time or 0))),
            tach_change=Decimal(str(counters.get('tach_time', 0))) - (aircraft.tach_time or 0),
            total_time_before=aircraft.total_time_hours,
            total_time_after=Decimal(str(counters.get('total_time_hours', aircraft.total_time_hours or 0))),
            total_time_change=Decimal(str(counters.get('total_time_hours', 0))) - (aircraft.total_time_hours or 0),
            landings_before=aircraft.total_landings,
            landings_after=counters.get('total_landings', aircraft.total_landings or 0),
            landings_change=counters.get('total_landings', 0) - (aircraft.total_landings or 0),
            cycles_before=aircraft.total_cycles,
            cycles_after=counters.get('total_cycles', aircraft.total_cycles or 0),
            cycles_change=counters.get('total_cycles', 0) - (aircraft.total_cycles or 0),
            notes=notes or "Initial counter import",
            created_by=created_by,
        )

        # Update aircraft
        for field in ['hobbs_time', 'tach_time', 'total_time_hours', 'total_landings', 'total_cycles']:
            if field in counters:
                value = counters[field]
                if field in ['hobbs_time', 'tach_time', 'total_time_hours']:
                    value = Decimal(str(value))
                setattr(aircraft, field, value)

        aircraft.save()

        self._invalidate_cache(aircraft_id)

        logger.info(f"Imported counters for aircraft {aircraft.registration}")

        return {
            'time_log_id': str(time_log.id),
            'imported_counters': counters,
            'new_counters': self.get_counters(aircraft_id)
        }

    # ==========================================================================
    # Cache Management
    # ==========================================================================

    def _invalidate_cache(self, aircraft_id: uuid.UUID) -> None:
        """Invalidate counter cache for an aircraft."""
        cache.delete(f"aircraft_counters:{aircraft_id}")
        cache.delete(f"aircraft:{aircraft_id}")
        cache.delete(f"aircraft_status:{aircraft_id}")
