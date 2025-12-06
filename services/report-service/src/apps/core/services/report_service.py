"""
Report Service.

Business logic for generating and managing reports.
"""
import logging
import time
from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime, timedelta
from decimal import Decimal

from django.db import transaction
from django.db.models import QuerySet
from django.utils import timezone

from ..models import Report, ReportTemplate
from ..exceptions import (
    ReportNotFound,
    ReportGenerationFailed,
    InvalidReportParameters,
    ReportTimeoutError,
    ReportSizeLimitExceeded,
)
from ..constants import (
    STATUS_GENERATING,
    STATUS_COMPLETED,
    STATUS_FAILED,
    MAX_REPORT_ROWS,
    REPORT_GENERATION_TIMEOUT,
    REPORT_RETENTION_DAYS,
)
from ..validators import validate_date_range
from .report_template_service import ReportTemplateService
from .data_fetcher_service import DataFetcherService
from .export_service import ExportService

logger = logging.getLogger(__name__)


class ReportService:
    """Service for generating and managing reports."""

    @staticmethod
    def get_by_id(report_id: UUID, organization_id: UUID) -> Report:
        """
        Get a report by ID.

        Args:
            report_id: Report UUID
            organization_id: Organization UUID

        Returns:
            Report instance

        Raises:
            ReportNotFound: If report doesn't exist
        """
        try:
            return Report.objects.select_related('template').get(
                id=report_id,
                organization_id=organization_id
            )
        except Report.DoesNotExist:
            raise ReportNotFound(detail=f"Report with ID {report_id} not found.")

    @staticmethod
    def get_list(
        organization_id: UUID,
        template_id: Optional[UUID] = None,
        generated_by_id: Optional[UUID] = None,
        status: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> QuerySet[Report]:
        """
        Get list of reports with filters.

        Args:
            organization_id: Organization UUID
            template_id: Filter by template
            generated_by_id: Filter by generator
            status: Filter by status
            start_date: Filter by start date
            end_date: Filter by end date

        Returns:
            QuerySet of Report
        """
        queryset = Report.objects.filter(
            organization_id=organization_id
        ).select_related('template')

        if template_id:
            queryset = queryset.filter(template_id=template_id)

        if generated_by_id:
            queryset = queryset.filter(generated_by_id=generated_by_id)

        if status:
            queryset = queryset.filter(status=status)

        if start_date:
            queryset = queryset.filter(generated_at__gte=start_date)

        if end_date:
            queryset = queryset.filter(generated_at__lte=end_date)

        return queryset.order_by('-generated_at')

    @staticmethod
    @transaction.atomic
    def generate(
        template_id: UUID,
        organization_id: UUID,
        generated_by_id: UUID,
        parameters: Dict[str, Any],
        title: Optional[str] = None,
        description: str = "",
        output_format: str = "pdf",
    ) -> Report:
        """
        Generate a new report.

        Args:
            template_id: Template UUID to use
            organization_id: Organization UUID
            generated_by_id: User UUID generating
            parameters: Report parameters (date range, filters, etc.)
            title: Report title (defaults to template name + date)
            description: Report description
            output_format: Output format (pdf, excel, csv, json, html)

        Returns:
            Generated Report

        Raises:
            ReportGenerationFailed: If generation fails
            InvalidReportParameters: If parameters invalid
        """
        start_time = time.time()

        # Get template
        template = ReportTemplateService.get_by_id(template_id, organization_id)

        # Validate parameters
        ReportService._validate_parameters(parameters)

        # Create report record
        report = Report.objects.create(
            template=template,
            organization_id=organization_id,
            title=title or f"{template.name} - {timezone.now().strftime('%Y-%m-%d')}",
            description=description,
            parameters=parameters,
            generated_by_id=generated_by_id,
            output_format=output_format,
            status=STATUS_GENERATING,
            expires_at=timezone.now() + timedelta(days=REPORT_RETENTION_DAYS),
        )

        try:
            # Fetch data from source service
            data = DataFetcherService.fetch_data(
                data_source=template.data_source,
                query_config=template.query_config,
                parameters=parameters,
                organization_id=organization_id,
            )

            # Validate data size
            if len(data) > MAX_REPORT_ROWS:
                raise ReportSizeLimitExceeded(
                    detail=f"Report exceeds maximum {MAX_REPORT_ROWS} rows."
                )

            # Apply transformations (grouping, sorting)
            processed_data = ReportService._process_data(
                data=data,
                columns=template.columns,
                grouping=template.grouping,
                sorting=template.sorting,
            )

            # Export to requested format
            export_result = ExportService.export(
                data=processed_data,
                columns=template.columns,
                format=output_format,
                title=report.title,
                chart_type=template.chart_type,
                visualization_config=template.visualization_config,
            )

            # Update report with results
            processing_time = time.time() - start_time

            report.data = processed_data[:1000]  # Store first 1000 rows for preview
            report.row_count = len(processed_data)
            report.file_url = export_result.get('file_url', '')
            report.file_size_bytes = export_result.get('file_size', 0)
            report.status = STATUS_COMPLETED
            report.processing_time_seconds = Decimal(str(round(processing_time, 2)))
            report.save()

            logger.info(
                f"Generated report: {report.id}",
                extra={
                    'report_id': str(report.id),
                    'template_id': str(template_id),
                    'row_count': report.row_count,
                    'processing_time': processing_time,
                }
            )

            return report

        except ReportSizeLimitExceeded:
            raise
        except Exception as e:
            # Mark report as failed
            report.status = STATUS_FAILED
            report.error_message = str(e)
            report.processing_time_seconds = Decimal(str(round(time.time() - start_time, 2)))
            report.save()

            logger.error(
                f"Report generation failed: {report.id}",
                extra={
                    'report_id': str(report.id),
                    'error': str(e),
                },
                exc_info=True
            )

            raise ReportGenerationFailed(detail=str(e))

    @staticmethod
    def _validate_parameters(parameters: Dict[str, Any]) -> None:
        """Validate report parameters."""
        # Validate date range if present
        if 'start_date' in parameters and 'end_date' in parameters:
            try:
                start_date = datetime.fromisoformat(parameters['start_date'].replace('Z', '+00:00'))
                end_date = datetime.fromisoformat(parameters['end_date'].replace('Z', '+00:00'))
                validate_date_range(start_date, end_date)
            except (ValueError, TypeError) as e:
                raise InvalidReportParameters(detail=f"Invalid date format: {e}")

    @staticmethod
    def _process_data(
        data: List[Dict],
        columns: List[Dict],
        grouping: List,
        sorting: List,
    ) -> List[Dict]:
        """
        Process data with grouping and sorting.

        Args:
            data: Raw data rows
            columns: Column definitions
            grouping: Grouping configuration
            sorting: Sorting configuration

        Returns:
            Processed data rows
        """
        if not data:
            return []

        # Extract only requested columns
        column_fields = {col['field'] for col in columns}
        processed = []
        for row in data:
            processed_row = {
                field: row.get(field)
                for field in column_fields
                if field in row
            }
            processed.append(processed_row)

        # Apply grouping if configured
        if grouping:
            processed = ReportService._apply_grouping(processed, grouping)

        # Apply sorting
        if sorting:
            processed = ReportService._apply_sorting(processed, sorting)

        return processed

    @staticmethod
    def _apply_grouping(data: List[Dict], grouping: List) -> List[Dict]:
        """Apply grouping to data."""
        if not grouping:
            return data

        # Simple grouping implementation
        grouped = {}
        for row in data:
            key = tuple(row.get(g.get('field')) for g in grouping if g.get('field'))
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(row)

        # Aggregate grouped data
        result = []
        for key, rows in grouped.items():
            aggregated = dict(zip([g.get('field') for g in grouping], key))
            aggregated['_count'] = len(rows)
            result.append(aggregated)

        return result

    @staticmethod
    def _apply_sorting(data: List[Dict], sorting: List) -> List[Dict]:
        """Apply sorting to data."""
        if not sorting:
            return data

        for sort_config in reversed(sorting):
            field = sort_config.get('field')
            direction = sort_config.get('direction', 'asc')
            if field:
                data = sorted(
                    data,
                    key=lambda x: (x.get(field) is None, x.get(field)),
                    reverse=(direction == 'desc')
                )

        return data

    @staticmethod
    def regenerate(
        report_id: UUID,
        organization_id: UUID,
        user_id: UUID
    ) -> Report:
        """
        Regenerate an existing report with fresh data.

        Args:
            report_id: Report UUID
            organization_id: Organization UUID
            user_id: User regenerating

        Returns:
            New Report instance
        """
        original = ReportService.get_by_id(report_id, organization_id)

        return ReportService.generate(
            template_id=original.template_id,
            organization_id=organization_id,
            generated_by_id=user_id,
            parameters=original.parameters,
            title=f"{original.title} (Regenerated)",
            description=original.description,
            output_format=original.output_format,
        )

    @staticmethod
    @transaction.atomic
    def delete(report_id: UUID, organization_id: UUID) -> None:
        """
        Delete a report.

        Args:
            report_id: Report UUID
            organization_id: Organization UUID
        """
        report = ReportService.get_by_id(report_id, organization_id)
        report.delete()

        logger.info(f"Deleted report: {report_id}")

    @staticmethod
    def cleanup_expired() -> int:
        """
        Clean up expired reports.

        Returns:
            Number of reports deleted
        """
        expired = Report.objects.filter(
            expires_at__lt=timezone.now()
        )
        count = expired.count()
        expired.delete()

        logger.info(f"Cleaned up {count} expired reports")
        return count
