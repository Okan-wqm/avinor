# services/training-service/src/apps/core/services/progress_service.py
"""
Progress Service

Business logic for student progress tracking and reporting.
"""

import uuid
import logging
from decimal import Decimal
from typing import List, Dict, Any, Optional
from datetime import date, timedelta

from django.db import models
from django.db.models import Q, Count, Avg, Sum, F
from django.core.exceptions import ValidationError

from ..models import (
    StudentEnrollment,
    TrainingProgram,
    SyllabusLesson,
    LessonCompletion,
    StageCheck,
    ExerciseGrade
)

logger = logging.getLogger(__name__)


class ProgressService:
    """
    Service class for student progress tracking.

    Handles progress calculation, reporting, and analytics.
    """

    # ==========================================================================
    # Progress Overview
    # ==========================================================================

    @staticmethod
    def get_student_progress(
        enrollment_id: uuid.UUID,
        organization_id: uuid.UUID
    ) -> Dict[str, Any]:
        """
        Get comprehensive progress summary for a student enrollment.

        Args:
            enrollment_id: Enrollment UUID
            organization_id: Organization UUID

        Returns:
            Progress summary dictionary
        """
        enrollment = StudentEnrollment.objects.select_related('program').get(
            id=enrollment_id,
            organization_id=organization_id
        )

        # Get lesson completions
        completions = LessonCompletion.objects.filter(
            enrollment=enrollment
        ).select_related('lesson')

        completed_lessons = completions.filter(
            is_completed=True,
            result__in=['pass', 'satisfactory']
        )

        # Get all program lessons
        all_lessons = SyllabusLesson.objects.filter(
            program=enrollment.program,
            status='active'
        )

        # Calculate progress by stage
        stage_progress = ProgressService._calculate_stage_progress(
            enrollment, all_lessons, completed_lessons
        )

        # Get recent activity
        recent_completions = completions.order_by('-actual_date')[:5]

        # Calculate time metrics
        time_metrics = ProgressService._calculate_time_metrics(enrollment)

        # Get hour requirements status
        hour_requirements = enrollment.check_hour_requirements()

        # Get stage check status
        stage_checks = StageCheck.objects.filter(enrollment=enrollment)

        return {
            'enrollment_id': str(enrollment.id),
            'enrollment_number': enrollment.enrollment_number,
            'student_id': str(enrollment.student_id),
            'program': {
                'id': str(enrollment.program.id),
                'code': enrollment.program.code,
                'name': enrollment.program.name,
            },
            'status': enrollment.status,
            'overall_progress': {
                'lessons_completed': enrollment.lessons_completed,
                'lessons_total': enrollment.lessons_total,
                'completion_percentage': float(enrollment.completion_percentage),
                'progress_status': enrollment.progress_status,
            },
            'hours': {
                'flight': float(enrollment.total_flight_hours),
                'ground': float(enrollment.total_ground_hours),
                'simulator': float(enrollment.total_simulator_hours),
                'total': float(enrollment.total_training_hours),
                'categories': {
                    'dual': float(enrollment.dual_hours),
                    'solo': float(enrollment.solo_hours),
                    'pic': float(enrollment.pic_hours),
                    'cross_country': float(enrollment.cross_country_hours),
                    'night': float(enrollment.night_hours),
                    'instrument': float(enrollment.instrument_hours),
                }
            },
            'hour_requirements': hour_requirements,
            'performance': {
                'average_grade': float(enrollment.average_grade) if enrollment.average_grade else None,
                'stage_checks_passed': enrollment.stage_checks_passed,
                'stage_checks_failed': enrollment.stage_checks_failed,
            },
            'current_position': {
                'stage_id': str(enrollment.current_stage_id) if enrollment.current_stage_id else None,
                'stage_name': enrollment.current_stage_name,
                'lesson_id': str(enrollment.current_lesson_id) if enrollment.current_lesson_id else None,
            },
            'stage_progress': stage_progress,
            'time_metrics': time_metrics,
            'recent_activity': [
                {
                    'lesson_code': c.lesson.code,
                    'lesson_name': c.lesson.name,
                    'date': c.actual_date.isoformat() if c.actual_date else None,
                    'result': c.result,
                    'grade': float(c.grade) if c.grade else None,
                }
                for c in recent_completions
            ],
            'stage_checks': {
                'total': stage_checks.count(),
                'passed': stage_checks.filter(is_passed=True).count(),
                'pending': stage_checks.filter(status='scheduled').count(),
            },
            'dates': {
                'enrollment_date': enrollment.enrollment_date.isoformat(),
                'start_date': enrollment.start_date.isoformat() if enrollment.start_date else None,
                'expected_completion': enrollment.expected_completion.isoformat() if enrollment.expected_completion else None,
                'days_enrolled': enrollment.days_enrolled,
                'days_remaining': enrollment.days_remaining,
            }
        }

    @staticmethod
    def _calculate_stage_progress(
        enrollment: StudentEnrollment,
        all_lessons: models.QuerySet,
        completed_lessons: models.QuerySet
    ) -> List[Dict[str, Any]]:
        """Calculate progress for each stage."""
        stages = enrollment.program.stages or []
        completed_ids = set(str(c.lesson_id) for c in completed_lessons)

        stage_progress = []
        for stage in stages:
            stage_id = stage.get('id')
            stage_lessons = all_lessons.filter(stage_id=stage_id)
            total = stage_lessons.count()
            completed = sum(
                1 for lesson in stage_lessons
                if str(lesson.id) in completed_ids
            )

            # Check if stage check passed
            stage_check = StageCheck.objects.filter(
                enrollment=enrollment,
                stage_id=stage_id,
                is_passed=True
            ).first()

            stage_progress.append({
                'stage_id': stage_id,
                'stage_name': stage.get('name'),
                'order': stage.get('order', 0),
                'lessons_total': total,
                'lessons_completed': completed,
                'percentage': round(completed / total * 100, 2) if total > 0 else 0,
                'stage_check_passed': stage_check is not None,
                'is_current': str(enrollment.current_stage_id) == stage_id,
            })

        return sorted(stage_progress, key=lambda x: x['order'])

    @staticmethod
    def _calculate_time_metrics(enrollment: StudentEnrollment) -> Dict[str, Any]:
        """Calculate time-based metrics."""
        metrics = {
            'days_enrolled': enrollment.days_enrolled,
            'days_remaining': enrollment.days_remaining,
            'average_days_per_lesson': None,
            'projected_completion': None,
            'is_on_track': None,
        }

        if enrollment.lessons_completed > 0:
            metrics['average_days_per_lesson'] = round(
                enrollment.days_enrolled / enrollment.lessons_completed, 1
            )

            remaining_lessons = enrollment.lessons_total - enrollment.lessons_completed
            if remaining_lessons > 0:
                projected_days = int(
                    remaining_lessons * metrics['average_days_per_lesson']
                )
                metrics['projected_completion'] = (
                    date.today() + timedelta(days=projected_days)
                ).isoformat()

                if enrollment.expected_completion:
                    metrics['is_on_track'] = (
                        date.today() + timedelta(days=projected_days)
                    ) <= enrollment.expected_completion

        return metrics

    # ==========================================================================
    # Lesson Progress
    # ==========================================================================

    @staticmethod
    def get_lesson_progress(
        enrollment_id: uuid.UUID,
        organization_id: uuid.UUID
    ) -> List[Dict[str, Any]]:
        """
        Get detailed progress for each lesson.

        Args:
            enrollment_id: Enrollment UUID
            organization_id: Organization UUID

        Returns:
            List of lesson progress dictionaries
        """
        enrollment = StudentEnrollment.objects.get(
            id=enrollment_id,
            organization_id=organization_id
        )

        all_lessons = SyllabusLesson.objects.filter(
            program=enrollment.program,
            status='active'
        ).order_by('sort_order')

        completions = {
            str(c.lesson_id): c
            for c in LessonCompletion.objects.filter(
                enrollment=enrollment
            ).select_related('lesson')
        }

        # Get completed lesson IDs for prerequisite checking
        completed_ids = [
            str(c.lesson_id) for c in LessonCompletion.objects.filter(
                enrollment=enrollment,
                is_completed=True,
                result__in=['pass', 'satisfactory']
            )
        ]

        lesson_progress = []
        for lesson in all_lessons:
            lesson_id = str(lesson.id)
            completion = completions.get(lesson_id)

            # Check prerequisites
            prereq_check = lesson.check_prerequisites(
                completed_ids,
                enrollment.total_flight_hours
            )

            status = 'locked'
            if completion:
                if completion.is_completed and completion.is_passed:
                    status = 'completed'
                elif completion.is_completed and not completion.is_passed:
                    status = 'failed'
                elif completion.status == 'in_progress':
                    status = 'in_progress'
                elif completion.status == 'scheduled':
                    status = 'scheduled'
            elif prereq_check['met']:
                status = 'available'

            lesson_progress.append({
                'lesson_id': lesson_id,
                'code': lesson.code,
                'name': lesson.name,
                'lesson_type': lesson.lesson_type,
                'stage_id': str(lesson.stage_id) if lesson.stage_id else None,
                'stage_name': lesson.get_stage_name(),
                'status': status,
                'prerequisites_met': prereq_check['met'],
                'missing_prerequisites': prereq_check.get('missing_lessons', []),
                'completion': {
                    'date': completion.completion_date.isoformat() if completion and completion.completion_date else None,
                    'grade': float(completion.grade) if completion and completion.grade else None,
                    'result': completion.result if completion else None,
                    'attempts': completion.attempt_number if completion else 0,
                } if completion else None,
                'is_current': str(enrollment.current_lesson_id) == lesson_id,
            })

        return lesson_progress

    @staticmethod
    def get_next_lessons(
        enrollment_id: uuid.UUID,
        organization_id: uuid.UUID,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Get next available lessons for student.

        Args:
            enrollment_id: Enrollment UUID
            organization_id: Organization UUID
            limit: Maximum lessons to return

        Returns:
            List of next available lessons
        """
        from .syllabus_service import SyllabusService

        available_lessons = SyllabusService.get_available_lessons(
            enrollment_id, organization_id
        )

        return [
            {
                'id': str(lesson.id),
                'code': lesson.code,
                'name': lesson.name,
                'lesson_type': lesson.lesson_type,
                'stage_name': lesson.get_stage_name(),
                'duration': float(lesson.total_duration),
            }
            for lesson in available_lessons[:limit]
        ]

    # ==========================================================================
    # Hour Tracking
    # ==========================================================================

    @staticmethod
    def get_hour_breakdown(
        enrollment_id: uuid.UUID,
        organization_id: uuid.UUID
    ) -> Dict[str, Any]:
        """
        Get detailed hour breakdown for enrollment.

        Args:
            enrollment_id: Enrollment UUID
            organization_id: Organization UUID

        Returns:
            Hour breakdown dictionary
        """
        enrollment = StudentEnrollment.objects.select_related('program').get(
            id=enrollment_id,
            organization_id=organization_id
        )

        program = enrollment.program
        requirements = enrollment.check_hour_requirements()

        # Get hours by lesson type
        completions = LessonCompletion.objects.filter(
            enrollment=enrollment
        ).select_related('lesson')

        hours_by_type = completions.values(
            'lesson__lesson_type'
        ).annotate(
            flight=Sum('flight_time'),
            ground=Sum('ground_time'),
            simulator=Sum('simulator_time'),
        )

        # Get hours by stage
        hours_by_stage = []
        for stage in (program.stages or []):
            stage_completions = completions.filter(
                lesson__stage_id=stage.get('id')
            )
            stage_hours = stage_completions.aggregate(
                flight=Sum('flight_time'),
                ground=Sum('ground_time'),
                simulator=Sum('simulator_time'),
            )
            hours_by_stage.append({
                'stage_id': stage.get('id'),
                'stage_name': stage.get('name'),
                'flight': float(stage_hours['flight'] or 0),
                'ground': float(stage_hours['ground'] or 0),
                'simulator': float(stage_hours['simulator'] or 0),
            })

        return {
            'totals': {
                'flight': float(enrollment.total_flight_hours),
                'ground': float(enrollment.total_ground_hours),
                'simulator': float(enrollment.total_simulator_hours),
                'total_training': float(enrollment.total_training_hours),
            },
            'categories': {
                'dual': float(enrollment.dual_hours),
                'solo': float(enrollment.solo_hours),
                'pic': float(enrollment.pic_hours),
                'cross_country': float(enrollment.cross_country_hours),
                'night': float(enrollment.night_hours),
                'instrument': float(enrollment.instrument_hours),
            },
            'requirements': requirements,
            'by_lesson_type': {
                item['lesson__lesson_type']: {
                    'flight': float(item['flight'] or 0),
                    'ground': float(item['ground'] or 0),
                    'simulator': float(item['simulator'] or 0),
                }
                for item in hours_by_type
            },
            'by_stage': hours_by_stage,
        }

    # ==========================================================================
    # Performance Analytics
    # ==========================================================================

    @staticmethod
    def get_performance_analytics(
        enrollment_id: uuid.UUID,
        organization_id: uuid.UUID
    ) -> Dict[str, Any]:
        """
        Get performance analytics for enrollment.

        Args:
            enrollment_id: Enrollment UUID
            organization_id: Organization UUID

        Returns:
            Performance analytics dictionary
        """
        enrollment = StudentEnrollment.objects.get(
            id=enrollment_id,
            organization_id=organization_id
        )

        completions = LessonCompletion.objects.filter(
            enrollment=enrollment,
            is_completed=True
        )

        # Grade distribution
        grade_distribution = completions.filter(
            grade__isnull=False
        ).values('grade').annotate(count=Count('id'))

        # Calculate grade buckets
        grade_buckets = {
            'excellent': 0,  # 90-100
            'good': 0,       # 80-89
            'satisfactory': 0,  # 70-79
            'needs_improvement': 0,  # 60-69
            'unsatisfactory': 0,  # <60
        }

        for item in grade_distribution:
            grade = float(item['grade'])
            if grade >= 90:
                grade_buckets['excellent'] += item['count']
            elif grade >= 80:
                grade_buckets['good'] += item['count']
            elif grade >= 70:
                grade_buckets['satisfactory'] += item['count']
            elif grade >= 60:
                grade_buckets['needs_improvement'] += item['count']
            else:
                grade_buckets['unsatisfactory'] += item['count']

        # Pass/fail breakdown
        pass_fail = completions.aggregate(
            passed=Count('id', filter=Q(result__in=['pass', 'satisfactory'])),
            failed=Count('id', filter=Q(result__in=['fail', 'unsatisfactory'])),
        )

        # Exercise performance
        exercise_grades = ExerciseGrade.objects.filter(
            completion__enrollment=enrollment
        ).select_related('exercise')

        exercise_stats = exercise_grades.aggregate(
            total=Count('id'),
            passed=Count('id', filter=Q(is_passed=True)),
            avg_grade=Avg('grade', filter=Q(grade__isnull=False)),
        )

        # Identify weak areas
        weak_areas = exercise_grades.filter(
            is_passed=False
        ).values(
            'exercise__name'
        ).annotate(
            fail_count=Count('id')
        ).order_by('-fail_count')[:5]

        # Strong areas
        strong_areas = exercise_grades.filter(
            grade__gte=90
        ).values(
            'exercise__name'
        ).annotate(
            count=Count('id')
        ).order_by('-count')[:5]

        return {
            'overall': {
                'average_grade': float(enrollment.average_grade) if enrollment.average_grade else None,
                'total_completions': completions.count(),
                'pass_rate': round(
                    pass_fail['passed'] / completions.count() * 100, 2
                ) if completions.count() > 0 else 0,
            },
            'grade_distribution': grade_buckets,
            'pass_fail': {
                'passed': pass_fail['passed'] or 0,
                'failed': pass_fail['failed'] or 0,
            },
            'exercises': {
                'total_graded': exercise_stats['total'] or 0,
                'passed': exercise_stats['passed'] or 0,
                'average_grade': round(
                    float(exercise_stats['avg_grade'] or 0), 2
                ),
            },
            'weak_areas': [
                {
                    'exercise': item['exercise__name'],
                    'fail_count': item['fail_count'],
                }
                for item in weak_areas
            ],
            'strong_areas': [
                {
                    'exercise': item['exercise__name'],
                    'high_grade_count': item['count'],
                }
                for item in strong_areas
            ],
            'stage_checks': {
                'passed': enrollment.stage_checks_passed,
                'failed': enrollment.stage_checks_failed,
                'total': enrollment.stage_checks_passed + enrollment.stage_checks_failed,
            }
        }

    # ==========================================================================
    # Comparison and Benchmarking
    # ==========================================================================

    @staticmethod
    def compare_to_program_average(
        enrollment_id: uuid.UUID,
        organization_id: uuid.UUID
    ) -> Dict[str, Any]:
        """
        Compare student progress to program averages.

        Args:
            enrollment_id: Enrollment UUID
            organization_id: Organization UUID

        Returns:
            Comparison dictionary
        """
        enrollment = StudentEnrollment.objects.get(
            id=enrollment_id,
            organization_id=organization_id
        )

        # Get program averages
        program_enrollments = StudentEnrollment.objects.filter(
            organization_id=organization_id,
            program=enrollment.program,
            status__in=['active', 'completed']
        ).exclude(id=enrollment_id)

        program_stats = program_enrollments.aggregate(
            avg_completion=Avg('completion_percentage'),
            avg_grade=Avg('average_grade', filter=Q(average_grade__isnull=False)),
            avg_flight_hours=Avg('total_flight_hours'),
            avg_days_enrolled=Avg(
                F('actual_completion') - F('enrollment_date'),
                filter=Q(actual_completion__isnull=False)
            ),
        )

        return {
            'student': {
                'completion_percentage': float(enrollment.completion_percentage),
                'average_grade': float(enrollment.average_grade) if enrollment.average_grade else None,
                'flight_hours': float(enrollment.total_flight_hours),
                'days_enrolled': enrollment.days_enrolled,
            },
            'program_average': {
                'completion_percentage': round(
                    float(program_stats['avg_completion'] or 0), 2
                ),
                'average_grade': round(
                    float(program_stats['avg_grade'] or 0), 2
                ) if program_stats['avg_grade'] else None,
                'flight_hours': round(
                    float(program_stats['avg_flight_hours'] or 0), 2
                ),
            },
            'comparison': {
                'completion_vs_average': round(
                    float(enrollment.completion_percentage) -
                    float(program_stats['avg_completion'] or 0), 2
                ),
                'grade_vs_average': round(
                    float(enrollment.average_grade or 0) -
                    float(program_stats['avg_grade'] or 0), 2
                ) if enrollment.average_grade and program_stats['avg_grade'] else None,
                'hours_vs_average': round(
                    float(enrollment.total_flight_hours) -
                    float(program_stats['avg_flight_hours'] or 0), 2
                ),
            },
            'sample_size': program_enrollments.count(),
        }

    # ==========================================================================
    # Progress Reports
    # ==========================================================================

    @staticmethod
    def generate_progress_report(
        enrollment_id: uuid.UUID,
        organization_id: uuid.UUID
    ) -> Dict[str, Any]:
        """
        Generate comprehensive progress report.

        Args:
            enrollment_id: Enrollment UUID
            organization_id: Organization UUID

        Returns:
            Complete progress report dictionary
        """
        progress = ProgressService.get_student_progress(
            enrollment_id, organization_id
        )

        lesson_progress = ProgressService.get_lesson_progress(
            enrollment_id, organization_id
        )

        hour_breakdown = ProgressService.get_hour_breakdown(
            enrollment_id, organization_id
        )

        performance = ProgressService.get_performance_analytics(
            enrollment_id, organization_id
        )

        comparison = ProgressService.compare_to_program_average(
            enrollment_id, organization_id
        )

        next_lessons = ProgressService.get_next_lessons(
            enrollment_id, organization_id
        )

        return {
            'report_date': date.today().isoformat(),
            'summary': progress,
            'lesson_progress': lesson_progress,
            'hours': hour_breakdown,
            'performance': performance,
            'comparison': comparison,
            'next_lessons': next_lessons,
        }
