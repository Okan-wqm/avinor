"""
Report Service Constants.

Centralized constants for the report service.
"""

# Report Types
REPORT_TYPE_FINANCIAL = 'financial'
REPORT_TYPE_FLIGHT_ACTIVITY = 'flight_activity'
REPORT_TYPE_STUDENT_PROGRESS = 'student_progress'
REPORT_TYPE_AIRCRAFT_UTILIZATION = 'aircraft_utilization'
REPORT_TYPE_MAINTENANCE = 'maintenance'
REPORT_TYPE_INSTRUCTOR_ACTIVITY = 'instructor_activity'
REPORT_TYPE_CUSTOM = 'custom'

# Report Status
STATUS_GENERATING = 'generating'
STATUS_COMPLETED = 'completed'
STATUS_FAILED = 'failed'

# Output Formats
FORMAT_PDF = 'pdf'
FORMAT_EXCEL = 'excel'
FORMAT_CSV = 'csv'
FORMAT_JSON = 'json'
FORMAT_HTML = 'html'

# Schedule Frequencies
FREQUENCY_DAILY = 'daily'
FREQUENCY_WEEKLY = 'weekly'
FREQUENCY_MONTHLY = 'monthly'
FREQUENCY_QUARTERLY = 'quarterly'
FREQUENCY_YEARLY = 'yearly'

# Widget Types
WIDGET_TYPE_CHART = 'chart'
WIDGET_TYPE_METRIC = 'metric'
WIDGET_TYPE_TABLE = 'table'
WIDGET_TYPE_GAUGE = 'gauge'
WIDGET_TYPE_MAP = 'map'
WIDGET_TYPE_TEXT = 'text'

# Chart Types
CHART_TYPE_BAR = 'bar'
CHART_TYPE_LINE = 'line'
CHART_TYPE_PIE = 'pie'
CHART_TYPE_DOUGHNUT = 'doughnut'
CHART_TYPE_AREA = 'area'
CHART_TYPE_SCATTER = 'scatter'

# Data Sources (services that can be queried)
DATA_SOURCE_FLIGHT = 'flight-service'
DATA_SOURCE_BOOKING = 'booking-service'
DATA_SOURCE_TRAINING = 'training-service'
DATA_SOURCE_FINANCE = 'finance-service'
DATA_SOURCE_AIRCRAFT = 'aircraft-service'
DATA_SOURCE_MAINTENANCE = 'maintenance-service'
DATA_SOURCE_USER = 'user-service'

DATA_SOURCES = [
    DATA_SOURCE_FLIGHT,
    DATA_SOURCE_BOOKING,
    DATA_SOURCE_TRAINING,
    DATA_SOURCE_FINANCE,
    DATA_SOURCE_AIRCRAFT,
    DATA_SOURCE_MAINTENANCE,
    DATA_SOURCE_USER,
]

# Cache TTL (seconds)
CACHE_TTL_WIDGET_DATA = 60
CACHE_TTL_REPORT_DATA = 300
CACHE_TTL_DASHBOARD = 600

# Report Generation
MAX_REPORT_ROWS = 100000
DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 1000

# File Size Limits (bytes)
MAX_REPORT_FILE_SIZE = 100 * 1024 * 1024  # 100 MB

# Processing Timeouts (seconds)
REPORT_GENERATION_TIMEOUT = 300
WIDGET_QUERY_TIMEOUT = 30

# Retry Settings
MAX_RETRY_ATTEMPTS = 3
RETRY_DELAY_SECONDS = 5

# Pagination Defaults
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100

# Days to keep reports before cleanup
REPORT_RETENTION_DAYS = 90

# Error Messages
ERROR_TEMPLATE_NOT_FOUND = "Report template not found"
ERROR_REPORT_NOT_FOUND = "Report not found"
ERROR_DASHBOARD_NOT_FOUND = "Dashboard not found"
ERROR_WIDGET_NOT_FOUND = "Widget not found"
ERROR_SCHEDULE_NOT_FOUND = "Schedule not found"
ERROR_GENERATION_FAILED = "Report generation failed"
ERROR_INVALID_PARAMETERS = "Invalid report parameters"
ERROR_PERMISSION_DENIED = "Permission denied"
ERROR_DATA_SOURCE_UNAVAILABLE = "Data source unavailable"
