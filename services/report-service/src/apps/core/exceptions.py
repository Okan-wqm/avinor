"""
Report Service Exceptions.

Custom exceptions for the report service.
"""
from rest_framework import status
from rest_framework.exceptions import APIException


class ReportServiceException(APIException):
    """Base exception for report service."""
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = "An error occurred in the report service."
    default_code = "report_service_error"


class ReportTemplateNotFound(ReportServiceException):
    """Raised when a report template is not found."""
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = "Report template not found."
    default_code = "template_not_found"


class ReportNotFound(ReportServiceException):
    """Raised when a report is not found."""
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = "Report not found."
    default_code = "report_not_found"


class DashboardNotFound(ReportServiceException):
    """Raised when a dashboard is not found."""
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = "Dashboard not found."
    default_code = "dashboard_not_found"


class WidgetNotFound(ReportServiceException):
    """Raised when a widget is not found."""
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = "Widget not found."
    default_code = "widget_not_found"


class ScheduleNotFound(ReportServiceException):
    """Raised when a schedule is not found."""
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = "Report schedule not found."
    default_code = "schedule_not_found"


class ReportGenerationFailed(ReportServiceException):
    """Raised when report generation fails."""
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = "Failed to generate report."
    default_code = "generation_failed"


class InvalidReportParameters(ReportServiceException):
    """Raised when report parameters are invalid."""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Invalid report parameters."
    default_code = "invalid_parameters"


class DataSourceUnavailable(ReportServiceException):
    """Raised when a data source service is unavailable."""
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = "Data source service is unavailable."
    default_code = "data_source_unavailable"


class ReportExportFailed(ReportServiceException):
    """Raised when report export fails."""
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = "Failed to export report."
    default_code = "export_failed"


class InvalidQueryConfiguration(ReportServiceException):
    """Raised when query configuration is invalid."""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Invalid query configuration."
    default_code = "invalid_query_config"


class WidgetRefreshFailed(ReportServiceException):
    """Raised when widget data refresh fails."""
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = "Failed to refresh widget data."
    default_code = "widget_refresh_failed"


class ScheduleExecutionFailed(ReportServiceException):
    """Raised when scheduled report execution fails."""
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = "Failed to execute scheduled report."
    default_code = "schedule_execution_failed"


class ReportSizeLimitExceeded(ReportServiceException):
    """Raised when report exceeds size limits."""
    status_code = status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
    default_detail = "Report exceeds maximum size limit."
    default_code = "size_limit_exceeded"


class ReportTimeoutError(ReportServiceException):
    """Raised when report generation times out."""
    status_code = status.HTTP_504_GATEWAY_TIMEOUT
    default_detail = "Report generation timed out."
    default_code = "generation_timeout"


class PermissionDenied(ReportServiceException):
    """Raised when user lacks permission for the operation."""
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "You do not have permission to perform this action."
    default_code = "permission_denied"


class DuplicateTemplateError(ReportServiceException):
    """Raised when trying to create a duplicate template."""
    status_code = status.HTTP_409_CONFLICT
    default_detail = "A template with this name already exists."
    default_code = "duplicate_template"


class InvalidDateRange(ReportServiceException):
    """Raised when date range is invalid."""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Invalid date range specified."
    default_code = "invalid_date_range"
