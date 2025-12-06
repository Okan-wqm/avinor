"""
Report Service Validators.

Custom validators for the report service.
"""
from datetime import datetime, timedelta
from django.core.exceptions import ValidationError
from django.utils import timezone

from .constants import (
    DATA_SOURCES,
    MAX_REPORT_ROWS,
    REPORT_RETENTION_DAYS,
    CHART_TYPE_BAR,
    CHART_TYPE_LINE,
    CHART_TYPE_PIE,
    CHART_TYPE_DOUGHNUT,
    CHART_TYPE_AREA,
    CHART_TYPE_SCATTER,
)


VALID_CHART_TYPES = [
    CHART_TYPE_BAR,
    CHART_TYPE_LINE,
    CHART_TYPE_PIE,
    CHART_TYPE_DOUGHNUT,
    CHART_TYPE_AREA,
    CHART_TYPE_SCATTER,
]


def validate_data_source(value: str) -> None:
    """Validate that the data source is a known service."""
    if value not in DATA_SOURCES:
        raise ValidationError(
            f"Invalid data source: {value}. Must be one of: {', '.join(DATA_SOURCES)}"
        )


def validate_chart_type(value: str) -> None:
    """Validate that the chart type is supported."""
    if value and value not in VALID_CHART_TYPES:
        raise ValidationError(
            f"Invalid chart type: {value}. Must be one of: {', '.join(VALID_CHART_TYPES)}"
        )


def validate_date_range(start_date: datetime, end_date: datetime) -> None:
    """Validate that the date range is valid."""
    if start_date > end_date:
        raise ValidationError("Start date must be before end date.")

    # Check if range is too large (more than 2 years)
    max_range = timedelta(days=730)
    if end_date - start_date > max_range:
        raise ValidationError("Date range cannot exceed 2 years.")


def validate_query_config(config: dict) -> None:
    """Validate query configuration structure."""
    if not isinstance(config, dict):
        raise ValidationError("Query configuration must be a dictionary.")

    # Validate filters if present
    if 'filters' in config:
        if not isinstance(config['filters'], list):
            raise ValidationError("Filters must be a list.")
        for filter_item in config['filters']:
            validate_filter(filter_item)

    # Validate aggregations if present
    if 'aggregations' in config:
        if not isinstance(config['aggregations'], list):
            raise ValidationError("Aggregations must be a list.")
        for agg in config['aggregations']:
            validate_aggregation(agg)

    # Validate limit
    if 'limit' in config:
        limit = config['limit']
        if not isinstance(limit, int) or limit < 1 or limit > MAX_REPORT_ROWS:
            raise ValidationError(
                f"Limit must be between 1 and {MAX_REPORT_ROWS}."
            )


def validate_filter(filter_item: dict) -> None:
    """Validate a single filter configuration."""
    required_keys = ['field', 'operator']
    for key in required_keys:
        if key not in filter_item:
            raise ValidationError(f"Filter missing required key: {key}")

    valid_operators = ['eq', 'ne', 'gt', 'gte', 'lt', 'lte', 'in', 'contains', 'between']
    if filter_item['operator'] not in valid_operators:
        raise ValidationError(
            f"Invalid filter operator: {filter_item['operator']}. "
            f"Must be one of: {', '.join(valid_operators)}"
        )


def validate_aggregation(agg: dict) -> None:
    """Validate an aggregation configuration."""
    required_keys = ['field', 'function']
    for key in required_keys:
        if key not in agg:
            raise ValidationError(f"Aggregation missing required key: {key}")

    valid_functions = ['sum', 'avg', 'count', 'min', 'max', 'first', 'last']
    if agg['function'] not in valid_functions:
        raise ValidationError(
            f"Invalid aggregation function: {agg['function']}. "
            f"Must be one of: {', '.join(valid_functions)}"
        )


def validate_columns(columns: list) -> None:
    """Validate column definitions."""
    if not isinstance(columns, list):
        raise ValidationError("Columns must be a list.")

    if len(columns) == 0:
        raise ValidationError("At least one column is required.")

    if len(columns) > 50:
        raise ValidationError("Maximum 50 columns allowed.")

    for column in columns:
        if not isinstance(column, dict):
            raise ValidationError("Each column must be a dictionary.")
        if 'field' not in column:
            raise ValidationError("Each column must have a 'field' key.")


def validate_visualization_config(config: dict, chart_type: str) -> None:
    """Validate visualization configuration based on chart type."""
    if not isinstance(config, dict):
        raise ValidationError("Visualization configuration must be a dictionary.")

    if chart_type in [CHART_TYPE_PIE, CHART_TYPE_DOUGHNUT]:
        if 'labels_field' not in config:
            raise ValidationError(
                f"{chart_type.title()} chart requires 'labels_field' in visualization config."
            )


def validate_schedule_time(frequency: str, day_of_week: int = None, day_of_month: int = None) -> None:
    """Validate schedule timing configuration."""
    if frequency == 'weekly' and day_of_week is None:
        raise ValidationError("Weekly schedules require day_of_week (0-6).")

    if frequency in ['monthly', 'quarterly', 'yearly'] and day_of_month is None:
        raise ValidationError(
            f"{frequency.title()} schedules require day_of_month (1-31)."
        )

    if day_of_week is not None and (day_of_week < 0 or day_of_week > 6):
        raise ValidationError("day_of_week must be between 0 (Monday) and 6 (Sunday).")

    if day_of_month is not None and (day_of_month < 1 or day_of_month > 31):
        raise ValidationError("day_of_month must be between 1 and 31.")


def validate_recipients(user_ids: list, emails: list) -> None:
    """Validate that at least one recipient is specified."""
    if not user_ids and not emails:
        raise ValidationError("At least one recipient (user_id or email) is required.")

    # Validate email format
    import re
    email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    for email in emails:
        if not email_pattern.match(email):
            raise ValidationError(f"Invalid email address: {email}")


def validate_widget_position(x: int, y: int, width: int, height: int) -> None:
    """Validate widget position and size."""
    if x < 0 or y < 0:
        raise ValidationError("Widget position cannot be negative.")

    if width < 1 or width > 12:
        raise ValidationError("Widget width must be between 1 and 12.")

    if height < 1 or height > 12:
        raise ValidationError("Widget height must be between 1 and 12.")

    if x + width > 12:
        raise ValidationError("Widget exceeds grid width (12 columns).")


def validate_refresh_interval(interval: int) -> None:
    """Validate widget refresh interval."""
    min_interval = 10  # 10 seconds minimum
    max_interval = 86400  # 24 hours maximum

    if interval < min_interval:
        raise ValidationError(f"Refresh interval must be at least {min_interval} seconds.")

    if interval > max_interval:
        raise ValidationError(f"Refresh interval cannot exceed {max_interval} seconds.")


def validate_output_formats(formats: list) -> None:
    """Validate output format list."""
    valid_formats = ['pdf', 'excel', 'csv', 'json', 'html']

    if not formats:
        raise ValidationError("At least one output format is required.")

    for fmt in formats:
        if fmt not in valid_formats:
            raise ValidationError(
                f"Invalid output format: {fmt}. Must be one of: {', '.join(valid_formats)}"
            )
