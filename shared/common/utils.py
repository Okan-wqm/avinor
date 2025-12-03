# shared/common/utils.py
"""
Common Utility Functions and Classes
"""

import uuid
import hashlib
import secrets
import re
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Union
from django.utils import timezone
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# UUID UTILITIES
# =============================================================================

def generate_uuid() -> str:
    """Generate a new UUID4 string"""
    return str(uuid.uuid4())


def is_valid_uuid(value: str) -> bool:
    """Check if string is a valid UUID"""
    try:
        uuid.UUID(str(value))
        return True
    except (ValueError, AttributeError):
        return False


def uuid_to_short(uuid_str: str) -> str:
    """Convert UUID to short base62 string"""
    import base64
    uuid_bytes = uuid.UUID(uuid_str).bytes
    return base64.urlsafe_b64encode(uuid_bytes).rstrip(b'=').decode('ascii')


def short_to_uuid(short: str) -> str:
    """Convert short base62 string back to UUID"""
    import base64
    padding = 4 - len(short) % 4
    if padding != 4:
        short += '=' * padding
    uuid_bytes = base64.urlsafe_b64decode(short)
    return str(uuid.UUID(bytes=uuid_bytes))


# =============================================================================
# STRING UTILITIES
# =============================================================================

def slugify(text: str, separator: str = '-') -> str:
    """Convert text to URL-friendly slug"""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_-]+', separator, text)
    return text


def truncate(text: str, length: int, suffix: str = '...') -> str:
    """Truncate text to specified length"""
    if len(text) <= length:
        return text
    return text[:length - len(suffix)].rsplit(' ', 1)[0] + suffix


def generate_random_string(length: int = 32) -> str:
    """Generate a random alphanumeric string"""
    return secrets.token_urlsafe(length)[:length]


def generate_code(prefix: str = '', length: int = 8) -> str:
    """Generate a unique code with optional prefix"""
    code = secrets.token_hex(length // 2).upper()
    return f"{prefix}{code}" if prefix else code


def mask_string(text: str, visible_chars: int = 4, mask_char: str = '*') -> str:
    """Mask a string, showing only last few characters"""
    if len(text) <= visible_chars:
        return text
    return mask_char * (len(text) - visible_chars) + text[-visible_chars:]


def mask_email(email: str) -> str:
    """Mask an email address for privacy"""
    if '@' not in email:
        return email
    local, domain = email.split('@')
    if len(local) <= 2:
        return f"{local[0]}{'*' * (len(local) - 1)}@{domain}"
    return f"{local[0]}{'*' * (len(local) - 2)}{local[-1]}@{domain}"


# =============================================================================
# DATE/TIME UTILITIES
# =============================================================================

def utc_now() -> datetime:
    """Get current UTC datetime"""
    return timezone.now()


def local_now() -> datetime:
    """Get current local datetime"""
    return timezone.localtime()


def date_to_datetime(d: date) -> datetime:
    """Convert date to datetime at midnight"""
    return datetime.combine(d, datetime.min.time())


def start_of_day(dt: datetime = None) -> datetime:
    """Get start of day for given datetime"""
    dt = dt or utc_now()
    return dt.replace(hour=0, minute=0, second=0, microsecond=0)


def end_of_day(dt: datetime = None) -> datetime:
    """Get end of day for given datetime"""
    dt = dt or utc_now()
    return dt.replace(hour=23, minute=59, second=59, microsecond=999999)


def start_of_week(dt: datetime = None) -> datetime:
    """Get start of week (Monday) for given datetime"""
    dt = dt or utc_now()
    days_since_monday = dt.weekday()
    return start_of_day(dt - timedelta(days=days_since_monday))


def end_of_week(dt: datetime = None) -> datetime:
    """Get end of week (Sunday) for given datetime"""
    dt = dt or utc_now()
    days_until_sunday = 6 - dt.weekday()
    return end_of_day(dt + timedelta(days=days_until_sunday))


def start_of_month(dt: datetime = None) -> datetime:
    """Get start of month for given datetime"""
    dt = dt or utc_now()
    return start_of_day(dt.replace(day=1))


def end_of_month(dt: datetime = None) -> datetime:
    """Get end of month for given datetime"""
    dt = dt or utc_now()
    if dt.month == 12:
        next_month = dt.replace(year=dt.year + 1, month=1, day=1)
    else:
        next_month = dt.replace(month=dt.month + 1, day=1)
    return end_of_day(next_month - timedelta(days=1))


def format_duration(minutes: int) -> str:
    """Format duration in minutes to human readable string"""
    if minutes < 60:
        return f"{minutes}m"
    hours = minutes // 60
    mins = minutes % 60
    if mins == 0:
        return f"{hours}h"
    return f"{hours}h {mins}m"


def parse_duration(duration_str: str) -> int:
    """Parse duration string to minutes"""
    total_minutes = 0

    # Match hours
    hours_match = re.search(r'(\d+)\s*h', duration_str, re.IGNORECASE)
    if hours_match:
        total_minutes += int(hours_match.group(1)) * 60

    # Match minutes
    mins_match = re.search(r'(\d+)\s*m', duration_str, re.IGNORECASE)
    if mins_match:
        total_minutes += int(mins_match.group(1))

    return total_minutes


def is_weekend(dt: datetime = None) -> bool:
    """Check if datetime is on weekend"""
    dt = dt or utc_now()
    return dt.weekday() >= 5


# =============================================================================
# VALIDATION UTILITIES
# =============================================================================

def is_valid_email(email: str) -> bool:
    """Validate email address"""
    try:
        validate_email(email)
        return True
    except ValidationError:
        return False


def is_valid_phone(phone: str) -> bool:
    """Validate phone number (basic validation)"""
    phone = re.sub(r'[\s\-\(\)]', '', phone)
    return bool(re.match(r'^\+?[\d]{10,15}$', phone))


def normalize_phone(phone: str) -> str:
    """Normalize phone number to standard format"""
    phone = re.sub(r'[\s\-\(\)]', '', phone)
    if not phone.startswith('+'):
        phone = '+' + phone
    return phone


# =============================================================================
# HASH UTILITIES
# =============================================================================

def hash_string(text: str, algorithm: str = 'sha256') -> str:
    """Hash a string using specified algorithm"""
    hasher = hashlib.new(algorithm)
    hasher.update(text.encode('utf-8'))
    return hasher.hexdigest()


def hash_file(file_obj, algorithm: str = 'sha256') -> str:
    """Hash file contents"""
    hasher = hashlib.new(algorithm)
    for chunk in iter(lambda: file_obj.read(8192), b''):
        hasher.update(chunk)
    file_obj.seek(0)
    return hasher.hexdigest()


# =============================================================================
# NUMBER UTILITIES
# =============================================================================

def round_decimal(value: Union[Decimal, float], places: int = 2) -> Decimal:
    """Round to specified decimal places"""
    if not isinstance(value, Decimal):
        value = Decimal(str(value))
    return value.quantize(Decimal(10) ** -places)


def format_currency(amount: Union[Decimal, float], currency: str = 'USD') -> str:
    """Format amount as currency string"""
    symbols = {
        'USD': '$',
        'EUR': '€',
        'GBP': '£',
        'TRY': '₺',
    }
    symbol = symbols.get(currency, currency + ' ')
    return f"{symbol}{amount:,.2f}"


def percentage(part: float, whole: float) -> float:
    """Calculate percentage"""
    if whole == 0:
        return 0.0
    return (part / whole) * 100


# =============================================================================
# DICT UTILITIES
# =============================================================================

def deep_get(dictionary: Dict, keys: str, default: Any = None) -> Any:
    """
    Get nested dictionary value using dot notation.
    Example: deep_get(data, 'user.address.city')
    """
    keys_list = keys.split('.')
    value = dictionary

    for key in keys_list:
        if isinstance(value, dict):
            value = value.get(key, default)
        else:
            return default

    return value


def deep_set(dictionary: Dict, keys: str, value: Any) -> Dict:
    """
    Set nested dictionary value using dot notation.
    Example: deep_set(data, 'user.address.city', 'New York')
    """
    keys_list = keys.split('.')
    current = dictionary

    for key in keys_list[:-1]:
        if key not in current or not isinstance(current[key], dict):
            current[key] = {}
        current = current[key]

    current[keys_list[-1]] = value
    return dictionary


def flatten_dict(dictionary: Dict, parent_key: str = '', separator: str = '.') -> Dict:
    """Flatten nested dictionary"""
    items = []
    for key, value in dictionary.items():
        new_key = f"{parent_key}{separator}{key}" if parent_key else key
        if isinstance(value, dict):
            items.extend(flatten_dict(value, new_key, separator).items())
        else:
            items.append((new_key, value))
    return dict(items)


def remove_none_values(dictionary: Dict) -> Dict:
    """Remove keys with None values from dictionary"""
    return {k: v for k, v in dictionary.items() if v is not None}


# =============================================================================
# LIST UTILITIES
# =============================================================================

def chunk_list(lst: List, chunk_size: int) -> List[List]:
    """Split list into chunks of specified size"""
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]


def unique(lst: List) -> List:
    """Return unique items while preserving order"""
    seen = set()
    return [x for x in lst if not (x in seen or seen.add(x))]


def find_duplicates(lst: List) -> List:
    """Find duplicate items in list"""
    seen = set()
    duplicates = set()
    for item in lst:
        if item in seen:
            duplicates.add(item)
        else:
            seen.add(item)
    return list(duplicates)


# =============================================================================
# FLIGHT-SPECIFIC UTILITIES
# =============================================================================

def decimal_hours_to_time(decimal_hours: float) -> str:
    """Convert decimal hours to HH:MM format"""
    hours = int(decimal_hours)
    minutes = int((decimal_hours - hours) * 60)
    return f"{hours:02d}:{minutes:02d}"


def time_to_decimal_hours(time_str: str) -> float:
    """Convert HH:MM to decimal hours"""
    parts = time_str.split(':')
    hours = int(parts[0])
    minutes = int(parts[1]) if len(parts) > 1 else 0
    return hours + (minutes / 60)


def calculate_block_time(
    off_block: datetime,
    on_block: datetime
) -> float:
    """Calculate block time in decimal hours"""
    delta = on_block - off_block
    return delta.total_seconds() / 3600


def calculate_flight_time(
    takeoff: datetime,
    landing: datetime
) -> float:
    """Calculate flight time in decimal hours"""
    delta = landing - takeoff
    return delta.total_seconds() / 3600


def format_hobbs(hours: float) -> str:
    """Format Hobbs meter reading"""
    return f"{hours:.1f}"


def validate_icao_code(code: str) -> bool:
    """Validate ICAO airport code (4 letters)"""
    return bool(re.match(r'^[A-Z]{4}$', code.upper()))


def validate_iata_code(code: str) -> bool:
    """Validate IATA airport code (3 letters)"""
    return bool(re.match(r'^[A-Z]{3}$', code.upper()))


def validate_aircraft_registration(registration: str) -> bool:
    """Validate aircraft registration (basic validation)"""
    return bool(re.match(r'^[A-Z0-9\-]{2,10}$', registration.upper()))


# =============================================================================
# CACHING UTILITIES
# =============================================================================

def make_cache_key(*args, prefix: str = '') -> str:
    """Generate a cache key from arguments"""
    key_parts = [str(arg) for arg in args]
    key = ':'.join(key_parts)
    if prefix:
        key = f"{prefix}:{key}"
    return key


def invalidate_cache_pattern(pattern: str, cache_backend: str = 'default'):
    """Invalidate all cache keys matching pattern"""
    from django.core.cache import caches
    cache = caches[cache_backend]

    if hasattr(cache, 'delete_pattern'):
        cache.delete_pattern(pattern)
    else:
        logger.warning(f"Cache backend does not support pattern deletion: {pattern}")
