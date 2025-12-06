"""
Shared Validators Module.

Common validation utilities used across all microservices.
"""
import re
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import List, Optional, Any
from uuid import UUID

from django.core.exceptions import ValidationError


# =============================================================================
# UUID VALIDATORS
# =============================================================================

def validate_uuid(value: Any, field_name: str = "value") -> UUID:
    """Validate and convert a value to UUID."""
    if isinstance(value, UUID):
        return value
    try:
        return UUID(str(value))
    except (ValueError, TypeError):
        raise ValidationError(f"Invalid UUID format for {field_name}")


def validate_uuid_list(values: List, field_name: str = "values") -> List[UUID]:
    """Validate and convert a list of values to UUIDs."""
    if not isinstance(values, (list, tuple)):
        raise ValidationError(f"{field_name} must be a list")
    return [validate_uuid(v, field_name) for v in values]


# =============================================================================
# DATE/TIME VALIDATORS
# =============================================================================

def validate_date_range(
    start_date: datetime,
    end_date: datetime,
    max_days: int = 365,
    field_name: str = "date range"
) -> None:
    """Validate that a date range is valid."""
    if start_date > end_date:
        raise ValidationError(f"Start date must be before end date for {field_name}")

    if (end_date - start_date).days > max_days:
        raise ValidationError(f"{field_name} cannot exceed {max_days} days")


def validate_future_date(
    value: datetime,
    allow_today: bool = True,
    field_name: str = "date"
) -> None:
    """Validate that a date is in the future."""
    now = datetime.now(value.tzinfo) if value.tzinfo else datetime.now()
    compare = now.date() if allow_today else now.date() + timedelta(days=1)

    if value.date() < compare:
        msg = "must be today or in the future" if allow_today else "must be in the future"
        raise ValidationError(f"{field_name} {msg}")


def validate_past_date(
    value: datetime,
    allow_today: bool = True,
    max_years: int = 100,
    field_name: str = "date"
) -> None:
    """Validate that a date is in the past."""
    now = datetime.now(value.tzinfo) if value.tzinfo else datetime.now()
    compare = now.date() if allow_today else now.date() - timedelta(days=1)

    if value.date() > compare:
        msg = "must be today or in the past" if allow_today else "must be in the past"
        raise ValidationError(f"{field_name} {msg}")

    min_date = now.date() - timedelta(days=max_years * 365)
    if value.date() < min_date:
        raise ValidationError(f"{field_name} cannot be more than {max_years} years ago")


def validate_time_slot(
    start_time: datetime,
    end_time: datetime,
    min_duration_minutes: int = 15,
    max_duration_hours: int = 24,
) -> None:
    """Validate a time slot."""
    if start_time >= end_time:
        raise ValidationError("Start time must be before end time")

    duration = end_time - start_time
    min_delta = timedelta(minutes=min_duration_minutes)
    max_delta = timedelta(hours=max_duration_hours)

    if duration < min_delta:
        raise ValidationError(f"Duration must be at least {min_duration_minutes} minutes")

    if duration > max_delta:
        raise ValidationError(f"Duration cannot exceed {max_duration_hours} hours")


# =============================================================================
# STRING VALIDATORS
# =============================================================================

def validate_phone_number(value: str, field_name: str = "phone") -> str:
    """Validate phone number format."""
    cleaned = re.sub(r'[^\d+]', '', value)

    if not cleaned:
        raise ValidationError(f"{field_name} is required")

    # Basic validation: 10-15 digits, optionally starting with +
    pattern = r'^\+?\d{10,15}$'
    if not re.match(pattern, cleaned):
        raise ValidationError(f"Invalid {field_name} format")

    return cleaned


def validate_email(value: str, field_name: str = "email") -> str:
    """Validate email format."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, value):
        raise ValidationError(f"Invalid {field_name} format")
    return value.lower()


def validate_registration_number(value: str, field_name: str = "registration") -> str:
    """Validate aircraft registration number."""
    cleaned = value.upper().strip()

    # Basic validation: 2-10 alphanumeric characters with optional hyphen
    pattern = r'^[A-Z0-9]{1,3}-?[A-Z0-9]{1,7}$'
    if not re.match(pattern, cleaned):
        raise ValidationError(f"Invalid {field_name} format")

    return cleaned


def validate_icao_code(value: str, field_name: str = "ICAO code") -> str:
    """Validate ICAO airport/airline code."""
    cleaned = value.upper().strip()

    if len(cleaned) != 4 or not cleaned.isalpha():
        raise ValidationError(f"{field_name} must be exactly 4 letters")

    return cleaned


def validate_iata_code(value: str, field_name: str = "IATA code") -> str:
    """Validate IATA airport/airline code."""
    cleaned = value.upper().strip()

    if len(cleaned) != 3 or not cleaned.isalpha():
        raise ValidationError(f"{field_name} must be exactly 3 letters")

    return cleaned


# =============================================================================
# NUMERIC VALIDATORS
# =============================================================================

def validate_positive_decimal(
    value: Decimal,
    max_value: Optional[Decimal] = None,
    field_name: str = "value"
) -> Decimal:
    """Validate a positive decimal value."""
    if not isinstance(value, (Decimal, int, float)):
        raise ValidationError(f"{field_name} must be a number")

    value = Decimal(str(value))

    if value < 0:
        raise ValidationError(f"{field_name} must be positive")

    if max_value is not None and value > max_value:
        raise ValidationError(f"{field_name} cannot exceed {max_value}")

    return value


def validate_range(
    value: int,
    min_value: int,
    max_value: int,
    field_name: str = "value"
) -> int:
    """Validate that a value is within a range."""
    if not isinstance(value, int):
        raise ValidationError(f"{field_name} must be an integer")

    if value < min_value or value > max_value:
        raise ValidationError(f"{field_name} must be between {min_value} and {max_value}")

    return value


def validate_percentage(value: Decimal, field_name: str = "percentage") -> Decimal:
    """Validate a percentage value (0-100)."""
    value = Decimal(str(value))

    if value < 0 or value > 100:
        raise ValidationError(f"{field_name} must be between 0 and 100")

    return value


# =============================================================================
# FLIGHT-SPECIFIC VALIDATORS
# =============================================================================

def validate_flight_hours(
    value: Decimal,
    max_hours: Decimal = Decimal("24.0"),
    field_name: str = "flight hours"
) -> Decimal:
    """Validate flight hours."""
    value = Decimal(str(value))

    if value < 0:
        raise ValidationError(f"{field_name} cannot be negative")

    if value > max_hours:
        raise ValidationError(f"{field_name} cannot exceed {max_hours} hours")

    return value.quantize(Decimal("0.1"))


def validate_hobbs_time(
    start: Decimal,
    end: Decimal,
    field_name: str = "Hobbs time"
) -> None:
    """Validate Hobbs meter readings."""
    if end < start:
        raise ValidationError(f"End {field_name} must be greater than or equal to start")

    if end - start > Decimal("24.0"):
        raise ValidationError(f"{field_name} change cannot exceed 24 hours in a single entry")


def validate_fuel_quantity(
    value: Decimal,
    max_quantity: Decimal,
    unit: str = "gallons",
    field_name: str = "fuel quantity"
) -> Decimal:
    """Validate fuel quantity."""
    value = Decimal(str(value))

    if value < 0:
        raise ValidationError(f"{field_name} cannot be negative")

    if value > max_quantity:
        raise ValidationError(f"{field_name} cannot exceed {max_quantity} {unit}")

    return value


def validate_weight(
    value: Decimal,
    max_weight: Decimal,
    unit: str = "lbs",
    field_name: str = "weight"
) -> Decimal:
    """Validate weight value."""
    value = Decimal(str(value))

    if value < 0:
        raise ValidationError(f"{field_name} cannot be negative")

    if value > max_weight:
        raise ValidationError(f"{field_name} cannot exceed {max_weight} {unit}")

    return value


# =============================================================================
# LIST VALIDATORS
# =============================================================================

def validate_list_not_empty(value: List, field_name: str = "list") -> List:
    """Validate that a list is not empty."""
    if not isinstance(value, (list, tuple)):
        raise ValidationError(f"{field_name} must be a list")

    if len(value) == 0:
        raise ValidationError(f"{field_name} cannot be empty")

    return list(value)


def validate_list_max_length(
    value: List,
    max_length: int,
    field_name: str = "list"
) -> List:
    """Validate that a list doesn't exceed max length."""
    if not isinstance(value, (list, tuple)):
        raise ValidationError(f"{field_name} must be a list")

    if len(value) > max_length:
        raise ValidationError(f"{field_name} cannot have more than {max_length} items")

    return list(value)


def validate_unique_list(value: List, field_name: str = "list") -> List:
    """Validate that a list has unique values."""
    if not isinstance(value, (list, tuple)):
        raise ValidationError(f"{field_name} must be a list")

    if len(value) != len(set(value)):
        raise ValidationError(f"{field_name} must contain unique values")

    return list(value)


# =============================================================================
# JSON VALIDATORS
# =============================================================================

def validate_json_structure(
    value: dict,
    required_keys: List[str],
    field_name: str = "data"
) -> dict:
    """Validate that a JSON object has required keys."""
    if not isinstance(value, dict):
        raise ValidationError(f"{field_name} must be an object")

    missing = set(required_keys) - set(value.keys())
    if missing:
        raise ValidationError(f"{field_name} is missing required keys: {', '.join(missing)}")

    return value


# =============================================================================
# BUSINESS RULE VALIDATORS
# =============================================================================

def validate_currency_code(value: str, field_name: str = "currency") -> str:
    """Validate ISO 4217 currency code."""
    cleaned = value.upper().strip()

    if len(cleaned) != 3 or not cleaned.isalpha():
        raise ValidationError(f"{field_name} must be a valid 3-letter currency code")

    return cleaned


def validate_country_code(value: str, field_name: str = "country") -> str:
    """Validate ISO 3166-1 alpha-2 country code."""
    cleaned = value.upper().strip()

    if len(cleaned) != 2 or not cleaned.isalpha():
        raise ValidationError(f"{field_name} must be a valid 2-letter country code")

    return cleaned


def validate_language_code(value: str, field_name: str = "language") -> str:
    """Validate ISO 639-1 language code."""
    cleaned = value.lower().strip()

    if len(cleaned) != 2 or not cleaned.isalpha():
        raise ValidationError(f"{field_name} must be a valid 2-letter language code")

    return cleaned


def validate_timezone(value: str, field_name: str = "timezone") -> str:
    """Validate timezone string."""
    import pytz

    try:
        pytz.timezone(value)
        return value
    except pytz.UnknownTimeZoneError:
        raise ValidationError(f"Invalid {field_name}: {value}")
