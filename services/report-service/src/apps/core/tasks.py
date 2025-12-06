"""
Report Service Celery Tasks.

Background tasks for report generation, scheduling, and cleanup.
"""
import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from .models import Report, ReportSchedule
from .services import ReportService, ScheduleService
from .constants import STATUS_FAILED, REPORT_RETENTION_DAYS

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
)
def generate_report_async(self, template_id, organization_id, user_id, parameters, title, output_format):
    """
    Generate a report asynchronously.

    Args:
        template_id: Template UUID
        organization_id: Organization UUID
        user_id: User UUID
        parameters: Report parameters
        title: Report title
        output_format: Output format
    """
    try:
        logger.info(
            f"Starting async report generation",
            extra={
                'template_id': template_id,
                'organization_id': organization_id,
                'task_id': self.request.id,
            }
        )

        report = ReportService.generate(
            template_id=template_id,
            organization_id=organization_id,
            generated_by_id=user_id,
            parameters=parameters,
            title=title,
            output_format=output_format,
        )

        logger.info(f"Report generated: {report.id}")
        return str(report.id)

    except Exception as e:
        logger.error(f"Report generation failed: {e}", exc_info=True)
        raise


@shared_task
def process_scheduled_reports():
    """
    Process all scheduled reports that are due to run.

    This task should be run every minute by Celery Beat.
    """
    pending_schedules = ScheduleService.get_pending()
    processed = 0
    failed = 0

    for schedule in pending_schedules:
        try:
            logger.info(f"Processing scheduled report: {schedule.id}")

            # Generate report for each output format
            for output_format in schedule.output_formats:
                generate_report_async.delay(
                    template_id=str(schedule.template_id),
                    organization_id=str(schedule.organization_id),
                    user_id=str(schedule.created_by_id),
                    parameters=schedule.parameters,
                    title=f"{schedule.name} - {timezone.now().strftime('%Y-%m-%d')}",
                    output_format=output_format,
                )

            # Mark as executed and calculate next run
            ScheduleService.mark_executed(schedule)
            processed += 1

            # Trigger notification task for recipients
            notify_schedule_recipients.delay(
                schedule_id=str(schedule.id),
                recipient_user_ids=schedule.recipient_user_ids,
                recipient_emails=schedule.recipient_emails,
            )

        except Exception as e:
            logger.error(f"Failed to process schedule {schedule.id}: {e}", exc_info=True)
            failed += 1

    logger.info(f"Processed {processed} scheduled reports, {failed} failed")
    return {'processed': processed, 'failed': failed}


@shared_task
def notify_schedule_recipients(schedule_id, recipient_user_ids, recipient_emails):
    """
    Send notifications to schedule recipients.

    Args:
        schedule_id: Schedule UUID
        recipient_user_ids: List of user UUIDs
        recipient_emails: List of email addresses
    """
    # This would integrate with notification service
    logger.info(
        f"Sending notifications for schedule {schedule_id}",
        extra={
            'recipients': len(recipient_user_ids) + len(recipient_emails),
        }
    )

    # TODO: Integrate with notification service via NATS or HTTP
    # notification_client.send(...)

    return True


@shared_task
def cleanup_expired_reports():
    """
    Clean up expired reports.

    This task should be run daily by Celery Beat.
    """
    try:
        count = ReportService.cleanup_expired()
        logger.info(f"Cleaned up {count} expired reports")
        return {'deleted': count}
    except Exception as e:
        logger.error(f"Failed to cleanup reports: {e}", exc_info=True)
        raise


@shared_task
def cleanup_failed_reports():
    """
    Clean up old failed reports.

    Failed reports older than 7 days are deleted.
    """
    threshold = timezone.now() - timedelta(days=7)

    deleted = Report.objects.filter(
        status=STATUS_FAILED,
        created_at__lt=threshold
    ).delete()[0]

    logger.info(f"Cleaned up {deleted} failed reports")
    return {'deleted': deleted}


@shared_task
def refresh_dashboard_widgets(dashboard_id, organization_id):
    """
    Refresh all widgets on a dashboard.

    Args:
        dashboard_id: Dashboard UUID
        organization_id: Organization UUID
    """
    from .services import WidgetService

    try:
        results = WidgetService.refresh_all_widgets(dashboard_id, organization_id)
        logger.info(f"Refreshed widgets on dashboard {dashboard_id}")
        return results
    except Exception as e:
        logger.error(f"Failed to refresh dashboard widgets: {e}", exc_info=True)
        raise


@shared_task
def update_widget_cache(widget_id, organization_id):
    """
    Update cache for a single widget.

    Args:
        widget_id: Widget UUID
        organization_id: Organization UUID
    """
    from .services import WidgetService

    try:
        data = WidgetService.get_data(widget_id, organization_id, force_refresh=True)
        logger.info(f"Updated cache for widget {widget_id}")
        return {'cached': True, 'rows': len(data.get('data', []))}
    except Exception as e:
        logger.error(f"Failed to update widget cache: {e}", exc_info=True)
        raise


@shared_task
def export_report_async(report_id, organization_id, output_format):
    """
    Export an existing report to a different format.

    Args:
        report_id: Report UUID
        organization_id: Organization UUID
        output_format: Target format
    """
    from .services import ExportService

    try:
        report = ReportService.get_by_id(report_id, organization_id)

        result = ExportService.export(
            data=report.data,
            columns=report.template.columns,
            format=output_format,
            title=report.title,
            chart_type=report.template.chart_type,
            visualization_config=report.template.visualization_config,
        )

        logger.info(f"Exported report {report_id} to {output_format}")
        return result

    except Exception as e:
        logger.error(f"Failed to export report: {e}", exc_info=True)
        raise


@shared_task
def aggregate_report_stats():
    """
    Aggregate report statistics for monitoring.

    This task should be run hourly.
    """
    from django.db.models import Count, Avg

    stats = Report.objects.values('status').annotate(
        count=Count('id'),
        avg_processing_time=Avg('processing_time_seconds'),
    )

    stats_dict = {s['status']: s for s in stats}

    logger.info("Report statistics", extra={'stats': stats_dict})
    return stats_dict
