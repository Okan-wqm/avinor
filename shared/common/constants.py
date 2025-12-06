"""
Shared Constants Module.

Common constants used across all microservices in the Flight Training Management System.
"""
from enum import Enum
from typing import Dict, List

# =============================================================================
# SYSTEM CONSTANTS
# =============================================================================

# API Version
API_VERSION = "v1"
API_PREFIX = f"/api/{API_VERSION}"

# Pagination
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100
MIN_PAGE_SIZE = 1

# Cache TTL (seconds)
CACHE_TTL_SHORT = 60  # 1 minute
CACHE_TTL_MEDIUM = 300  # 5 minutes
CACHE_TTL_LONG = 3600  # 1 hour
CACHE_TTL_DAY = 86400  # 24 hours

# Rate Limiting
RATE_LIMIT_ANONYMOUS = "100/hour"
RATE_LIMIT_AUTHENTICATED = "1000/hour"
RATE_LIMIT_ADMIN = "5000/hour"


# =============================================================================
# USER & AUTHENTICATION
# =============================================================================

class UserRole(str, Enum):
    """User roles in the system."""
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    MANAGER = "manager"
    INSTRUCTOR = "instructor"
    STUDENT = "student"
    DISPATCHER = "dispatcher"
    MAINTENANCE = "maintenance"
    FINANCE = "finance"
    GUEST = "guest"


class UserStatus(str, Enum):
    """User account status."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING = "pending"


# JWT Token Settings
JWT_ACCESS_TOKEN_LIFETIME_MINUTES = 60
JWT_REFRESH_TOKEN_LIFETIME_DAYS = 7
JWT_ALGORITHM = "HS256"


# =============================================================================
# ORGANIZATION
# =============================================================================

class OrganizationType(str, Enum):
    """Types of flight training organizations."""
    PART_61 = "part_61"
    PART_141 = "part_141"
    PART_135 = "part_135"
    EASA_ATO = "easa_ato"
    OTHER = "other"


class OrganizationStatus(str, Enum):
    """Organization status."""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    INACTIVE = "inactive"
    TRIAL = "trial"


# =============================================================================
# AIRCRAFT
# =============================================================================

class AircraftCategory(str, Enum):
    """Aircraft categories."""
    AIRPLANE = "airplane"
    ROTORCRAFT = "rotorcraft"
    GLIDER = "glider"
    LIGHTER_THAN_AIR = "lighter_than_air"
    POWERED_LIFT = "powered_lift"
    POWERED_PARACHUTE = "powered_parachute"
    WEIGHT_SHIFT = "weight_shift"


class AircraftClass(str, Enum):
    """Aircraft class ratings."""
    SINGLE_ENGINE_LAND = "sel"
    SINGLE_ENGINE_SEA = "ses"
    MULTI_ENGINE_LAND = "mel"
    MULTI_ENGINE_SEA = "mes"


class AircraftStatus(str, Enum):
    """Aircraft operational status."""
    AVAILABLE = "available"
    IN_MAINTENANCE = "in_maintenance"
    RESERVED = "reserved"
    IN_FLIGHT = "in_flight"
    GROUNDED = "grounded"
    SOLD = "sold"


class FuelType(str, Enum):
    """Aircraft fuel types."""
    AVGAS_100LL = "100ll"
    AVGAS_100 = "100"
    JET_A = "jet_a"
    JET_A1 = "jet_a1"
    MOGAS = "mogas"


# =============================================================================
# BOOKING & SCHEDULING
# =============================================================================

class BookingStatus(str, Enum):
    """Booking status."""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"


class BookingType(str, Enum):
    """Types of bookings."""
    TRAINING_FLIGHT = "training_flight"
    SOLO_FLIGHT = "solo_flight"
    CHECK_RIDE = "check_ride"
    MAINTENANCE = "maintenance"
    GROUND_SCHOOL = "ground_school"
    SIMULATOR = "simulator"
    CHARTER = "charter"
    RENTAL = "rental"


class ResourceType(str, Enum):
    """Bookable resource types."""
    AIRCRAFT = "aircraft"
    INSTRUCTOR = "instructor"
    SIMULATOR = "simulator"
    CLASSROOM = "classroom"
    BRIEFING_ROOM = "briefing_room"


# =============================================================================
# FLIGHT OPERATIONS
# =============================================================================

class FlightStatus(str, Enum):
    """Flight status."""
    SCHEDULED = "scheduled"
    PREFLIGHT = "preflight"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    DIVERTED = "diverted"


class FlightType(str, Enum):
    """Types of flights."""
    TRAINING = "training"
    SOLO = "solo"
    CHECK_RIDE = "check_ride"
    CROSS_COUNTRY = "cross_country"
    NIGHT = "night"
    INSTRUMENT = "instrument"
    MAINTENANCE = "maintenance"
    FERRY = "ferry"


class FlightRules(str, Enum):
    """Flight rules."""
    VFR = "vfr"
    IFR = "ifr"
    SVFR = "svfr"


# =============================================================================
# TRAINING & CERTIFICATES
# =============================================================================

class CertificateType(str, Enum):
    """Pilot certificate types."""
    STUDENT = "student"
    SPORT = "sport"
    RECREATIONAL = "recreational"
    PRIVATE = "private"
    COMMERCIAL = "commercial"
    ATP = "atp"
    FLIGHT_INSTRUCTOR = "cfi"
    GROUND_INSTRUCTOR = "ground_instructor"


class MedicalClass(str, Enum):
    """FAA medical certificate classes."""
    FIRST = "first"
    SECOND = "second"
    THIRD = "third"
    BASIC_MED = "basic_med"


class RatingType(str, Enum):
    """Additional ratings."""
    INSTRUMENT = "instrument"
    MULTI_ENGINE = "multi_engine"
    COMPLEX = "complex"
    HIGH_PERFORMANCE = "high_performance"
    TAILWHEEL = "tailwheel"
    HIGH_ALTITUDE = "high_altitude"
    TYPE_RATING = "type_rating"


class TrainingStatus(str, Enum):
    """Training program status."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    DISCONTINUED = "discontinued"


# =============================================================================
# MAINTENANCE
# =============================================================================

class MaintenanceType(str, Enum):
    """Types of maintenance."""
    SCHEDULED = "scheduled"
    UNSCHEDULED = "unscheduled"
    INSPECTION = "inspection"
    REPAIR = "repair"
    OVERHAUL = "overhaul"
    AD_COMPLIANCE = "ad_compliance"


class MaintenanceStatus(str, Enum):
    """Maintenance work order status."""
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    AWAITING_PARTS = "awaiting_parts"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class SquawkSeverity(str, Enum):
    """Aircraft squawk severity levels."""
    GROUNDING = "grounding"
    MAJOR = "major"
    MINOR = "minor"
    COSMETIC = "cosmetic"


# =============================================================================
# FINANCE
# =============================================================================

class TransactionType(str, Enum):
    """Financial transaction types."""
    CHARGE = "charge"
    PAYMENT = "payment"
    REFUND = "refund"
    CREDIT = "credit"
    ADJUSTMENT = "adjustment"
    TRANSFER = "transfer"


class PaymentMethod(str, Enum):
    """Payment methods."""
    CASH = "cash"
    CHECK = "check"
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    BANK_TRANSFER = "bank_transfer"
    ACCOUNT_CREDIT = "account_credit"


class InvoiceStatus(str, Enum):
    """Invoice status."""
    DRAFT = "draft"
    SENT = "sent"
    PAID = "paid"
    PARTIALLY_PAID = "partially_paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"


class Currency(str, Enum):
    """Supported currencies."""
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    NOK = "NOK"
    TRY = "TRY"


# =============================================================================
# NOTIFICATIONS
# =============================================================================

class NotificationChannel(str, Enum):
    """Notification delivery channels."""
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    IN_APP = "in_app"


class NotificationPriority(str, Enum):
    """Notification priority levels."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class NotificationCategory(str, Enum):
    """Notification categories."""
    SYSTEM = "system"
    BOOKING = "booking"
    FLIGHT = "flight"
    TRAINING = "training"
    MAINTENANCE = "maintenance"
    FINANCE = "finance"
    MARKETING = "marketing"


# =============================================================================
# WEATHER
# =============================================================================

class WeatherCategory(str, Enum):
    """Flight category based on weather."""
    VFR = "vfr"
    MVFR = "mvfr"
    IFR = "ifr"
    LIFR = "lifr"


# =============================================================================
# DOCUMENT TYPES
# =============================================================================

class DocumentType(str, Enum):
    """Types of documents in the system."""
    PILOT_LICENSE = "pilot_license"
    MEDICAL_CERTIFICATE = "medical_certificate"
    AIRCRAFT_REGISTRATION = "aircraft_registration"
    AIRWORTHINESS_CERTIFICATE = "airworthiness_certificate"
    INSURANCE = "insurance"
    MAINTENANCE_LOG = "maintenance_log"
    TRAINING_RECORD = "training_record"
    ENDORSEMENT = "endorsement"
    OTHER = "other"


# =============================================================================
# UNITS
# =============================================================================

class DistanceUnit(str, Enum):
    """Distance measurement units."""
    NAUTICAL_MILES = "nm"
    STATUTE_MILES = "sm"
    KILOMETERS = "km"
    FEET = "ft"
    METERS = "m"


class SpeedUnit(str, Enum):
    """Speed measurement units."""
    KNOTS = "kt"
    MPH = "mph"
    KPH = "kph"


class FuelUnit(str, Enum):
    """Fuel measurement units."""
    GALLONS = "gal"
    LITERS = "l"
    POUNDS = "lbs"
    KILOGRAMS = "kg"


class TemperatureUnit(str, Enum):
    """Temperature units."""
    CELSIUS = "C"
    FAHRENHEIT = "F"


# =============================================================================
# SERVICE PORTS
# =============================================================================

SERVICE_PORTS: Dict[str, int] = {
    "user-service": 8001,
    "organization-service": 8002,
    "aircraft-service": 8003,
    "booking-service": 8004,
    "flight-service": 8005,
    "weather-service": 8006,
    "training-service": 8007,
    "theory-service": 8008,
    "certificate-service": 8009,
    "finance-service": 8010,
    "document-service": 8011,
    "maintenance-service": 8012,
    "report-service": 8013,
    "notification-service": 8014,
}


# =============================================================================
# ERROR CODES
# =============================================================================

ERROR_CODES: Dict[str, str] = {
    "VALIDATION_ERROR": "E001",
    "AUTHENTICATION_FAILED": "E002",
    "PERMISSION_DENIED": "E003",
    "RESOURCE_NOT_FOUND": "E004",
    "RESOURCE_CONFLICT": "E005",
    "RATE_LIMITED": "E006",
    "SERVICE_UNAVAILABLE": "E007",
    "INTERNAL_ERROR": "E500",
}
