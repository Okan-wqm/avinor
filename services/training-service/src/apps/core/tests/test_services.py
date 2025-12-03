# services/training-service/src/apps/core/tests/test_services.py
"""
Service Tests

Tests for training service business logic layer.
"""

import uuid
from decimal import Decimal
from datetime import date, timedelta

from django.test import TestCase
from django.core.exceptions import ValidationError

from ..models import (
    TrainingProgram,
    SyllabusLesson,
    Exercise,
    StudentEnrollment,
    LessonCompletion,
    StageCheck,
)
from ..services import (
    TrainingProgramService,
    EnrollmentService,
    SyllabusService,
    CompletionService,
    StageCheckService,
    ProgressService,
)


class TrainingProgramServiceTest(TestCase):
    """Tests for TrainingProgramService."""

    def setUp(self):
        """Set up test fixtures."""
        self.organization_id = uuid.uuid4()
        self.user_id = uuid.uuid4()

    def test_create_program(self):
        """Test creating a training program."""
        program = TrainingProgramService.create_program(
            organization_id=self.organization_id,
            code='PPL-2024',
            name='Private Pilot License',
            program_type='ppl',
            created_by=self.user_id,
            min_hours_total=Decimal('45.00'),
        )

        self.assertIsNotNone(program.id)
        self.assertEqual(program.code, 'PPL-2024')
        self.assertEqual(program.status, 'draft')

    def test_create_duplicate_code_raises_error(self):
        """Test that creating a program with duplicate code raises error."""
        TrainingProgramService.create_program(
            organization_id=self.organization_id,
            code='PPL-2024',
            name='Private Pilot License',
            program_type='ppl',
        )

        with self.assertRaises(ValidationError):
            TrainingProgramService.create_program(
                organization_id=self.organization_id,
                code='PPL-2024',
                name='Another PPL',
                program_type='ppl',
            )

    def test_list_programs(self):
        """Test listing programs with filters."""
        TrainingProgramService.create_program(
            organization_id=self.organization_id,
            code='PPL-2024',
            name='Private Pilot License',
            program_type='ppl',
        )
        TrainingProgramService.create_program(
            organization_id=self.organization_id,
            code='IR-2024',
            name='Instrument Rating',
            program_type='ir',
        )

        programs, total = TrainingProgramService.list_programs(
            organization_id=self.organization_id
        )

        self.assertEqual(total, 2)
        self.assertEqual(len(programs), 2)

        # Filter by type
        programs, total = TrainingProgramService.list_programs(
            organization_id=self.organization_id,
            program_type='ppl'
        )

        self.assertEqual(total, 1)
        self.assertEqual(programs[0].code, 'PPL-2024')

    def test_add_stage(self):
        """Test adding a stage to a program."""
        program = TrainingProgramService.create_program(
            organization_id=self.organization_id,
            code='PPL-2024',
            name='Private Pilot License',
            program_type='ppl',
        )

        stage = TrainingProgramService.add_stage(
            program_id=program.id,
            organization_id=self.organization_id,
            name='Pre-Solo',
            description='Initial training phase',
        )

        program.refresh_from_db()
        self.assertEqual(len(program.stages), 1)
        self.assertEqual(stage['name'], 'Pre-Solo')

    def test_clone_program(self):
        """Test cloning a program."""
        # Create source program
        source = TrainingProgramService.create_program(
            organization_id=self.organization_id,
            code='PPL-2024',
            name='Private Pilot License',
            program_type='ppl',
            min_hours_total=Decimal('45.00'),
        )

        # Add a stage
        TrainingProgramService.add_stage(
            program_id=source.id,
            organization_id=self.organization_id,
            name='Pre-Solo',
        )

        # Add a lesson
        SyllabusService.create_lesson(
            organization_id=self.organization_id,
            program_id=source.id,
            code='L01',
            name='Introduction',
            lesson_type='ground',
        )

        # Clone
        clone = TrainingProgramService.clone_program(
            source_program_id=source.id,
            organization_id=self.organization_id,
            new_code='PPL-2025',
            new_name='Private Pilot License 2025',
            include_lessons=True,
        )

        self.assertEqual(clone.code, 'PPL-2025')
        self.assertEqual(clone.min_hours_total, Decimal('45.00'))
        self.assertEqual(len(clone.stages), 1)
        self.assertEqual(clone.lessons.count(), 1)


class EnrollmentServiceTest(TestCase):
    """Tests for EnrollmentService."""

    def setUp(self):
        """Set up test fixtures."""
        self.organization_id = uuid.uuid4()
        self.student_id = uuid.uuid4()
        self.program = TrainingProgram.objects.create(
            organization_id=self.organization_id,
            code='PPL-2024',
            name='Private Pilot License',
            program_type='ppl',
            is_published=True,
            status='active',
        )

    def test_create_enrollment(self):
        """Test creating an enrollment."""
        enrollment = EnrollmentService.create_enrollment(
            organization_id=self.organization_id,
            student_id=self.student_id,
            program_id=self.program.id,
        )

        self.assertIsNotNone(enrollment.id)
        self.assertIsNotNone(enrollment.enrollment_number)
        self.assertEqual(enrollment.status, 'pending')

    def test_create_duplicate_enrollment_raises_error(self):
        """Test that creating duplicate enrollment raises error."""
        EnrollmentService.create_enrollment(
            organization_id=self.organization_id,
            student_id=self.student_id,
            program_id=self.program.id,
        )

        with self.assertRaises(ValidationError):
            EnrollmentService.create_enrollment(
                organization_id=self.organization_id,
                student_id=self.student_id,
                program_id=self.program.id,
            )

    def test_activate_enrollment(self):
        """Test activating an enrollment."""
        enrollment = EnrollmentService.create_enrollment(
            organization_id=self.organization_id,
            student_id=self.student_id,
            program_id=self.program.id,
        )

        activated = EnrollmentService.activate_enrollment(
            enrollment_id=enrollment.id,
            organization_id=self.organization_id,
        )

        self.assertEqual(activated.status, 'active')
        self.assertIsNotNone(activated.start_date)

    def test_enrollment_lifecycle(self):
        """Test full enrollment lifecycle."""
        # Create and activate
        enrollment = EnrollmentService.create_enrollment(
            organization_id=self.organization_id,
            student_id=self.student_id,
            program_id=self.program.id,
        )
        enrollment = EnrollmentService.activate_enrollment(
            enrollment_id=enrollment.id,
            organization_id=self.organization_id,
        )
        self.assertEqual(enrollment.status, 'active')

        # Put on hold
        enrollment = EnrollmentService.put_on_hold(
            enrollment_id=enrollment.id,
            organization_id=self.organization_id,
            reason='Personal reasons',
        )
        self.assertEqual(enrollment.status, 'on_hold')

        # Resume
        enrollment = EnrollmentService.resume_enrollment(
            enrollment_id=enrollment.id,
            organization_id=self.organization_id,
        )
        self.assertEqual(enrollment.status, 'active')


class SyllabusServiceTest(TestCase):
    """Tests for SyllabusService."""

    def setUp(self):
        """Set up test fixtures."""
        self.organization_id = uuid.uuid4()
        self.program = TrainingProgram.objects.create(
            organization_id=self.organization_id,
            code='PPL-2024',
            name='Private Pilot License',
            program_type='ppl',
        )

    def test_create_lesson(self):
        """Test creating a lesson."""
        lesson = SyllabusService.create_lesson(
            organization_id=self.organization_id,
            program_id=self.program.id,
            code='L01',
            name='Introduction to Flight',
            lesson_type='ground',
            ground_hours=Decimal('2.0'),
        )

        self.assertIsNotNone(lesson.id)
        self.assertEqual(lesson.code, 'L01')
        self.assertEqual(lesson.sort_order, 1)

    def test_create_exercise(self):
        """Test creating an exercise."""
        lesson = SyllabusService.create_lesson(
            organization_id=self.organization_id,
            program_id=self.program.id,
            code='F01',
            name='First Flight',
            lesson_type='flight',
        )

        exercise = SyllabusService.create_exercise(
            organization_id=self.organization_id,
            lesson_id=lesson.id,
            code='E01',
            name='Straight and Level Flight',
        )

        self.assertIsNotNone(exercise.id)
        self.assertEqual(exercise.code, 'E01')
        self.assertEqual(exercise.lesson_id, lesson.id)

    def test_add_prerequisite(self):
        """Test adding prerequisite lessons."""
        lesson1 = SyllabusService.create_lesson(
            organization_id=self.organization_id,
            program_id=self.program.id,
            code='L01',
            name='Lesson 1',
            lesson_type='ground',
        )

        lesson2 = SyllabusService.create_lesson(
            organization_id=self.organization_id,
            program_id=self.program.id,
            code='L02',
            name='Lesson 2',
            lesson_type='flight',
        )

        updated = SyllabusService.add_prerequisite(
            lesson_id=lesson2.id,
            organization_id=self.organization_id,
            prerequisite_lesson_id=lesson1.id,
        )

        self.assertIn(lesson1.id, updated.prerequisite_lessons)

    def test_get_program_syllabus(self):
        """Test getting program syllabus structure."""
        # Add stage
        stage = self.program.add_stage('Pre-Solo')
        self.program.save()

        # Add lessons
        SyllabusService.create_lesson(
            organization_id=self.organization_id,
            program_id=self.program.id,
            code='L01',
            name='Lesson 1',
            lesson_type='ground',
            stage_id=stage['id'],
        )

        syllabus = SyllabusService.get_program_syllabus(
            program_id=self.program.id,
            organization_id=self.organization_id,
        )

        self.assertIn('stages', syllabus)
        self.assertIn('statistics', syllabus)
        self.assertEqual(syllabus['statistics']['total_lessons'], 1)


class CompletionServiceTest(TestCase):
    """Tests for CompletionService."""

    def setUp(self):
        """Set up test fixtures."""
        self.organization_id = uuid.uuid4()
        self.student_id = uuid.uuid4()
        self.instructor_id = uuid.uuid4()

        self.program = TrainingProgram.objects.create(
            organization_id=self.organization_id,
            code='PPL-2024',
            name='Private Pilot License',
            program_type='ppl',
            is_published=True,
            status='active',
        )

        self.lesson = SyllabusLesson.objects.create(
            organization_id=self.organization_id,
            program=self.program,
            code='F01',
            name='First Flight',
            lesson_type='flight',
            min_grade_to_pass=70,
        )

        self.enrollment = StudentEnrollment.objects.create(
            organization_id=self.organization_id,
            student_id=self.student_id,
            program=self.program,
            enrollment_date=date.today(),
            status='active',
        )

    def test_create_completion(self):
        """Test creating a lesson completion."""
        completion = CompletionService.create_completion(
            organization_id=self.organization_id,
            enrollment_id=self.enrollment.id,
            lesson_id=self.lesson.id,
            instructor_id=self.instructor_id,
            scheduled_date=date.today(),
        )

        self.assertIsNotNone(completion.id)
        self.assertEqual(completion.status, 'scheduled')
        self.assertEqual(completion.attempt_number, 1)

    def test_complete_lesson_workflow(self):
        """Test complete lesson workflow."""
        # Create completion
        completion = CompletionService.create_completion(
            organization_id=self.organization_id,
            enrollment_id=self.enrollment.id,
            lesson_id=self.lesson.id,
            instructor_id=self.instructor_id,
        )

        # Start lesson
        completion = CompletionService.start_lesson(
            completion_id=completion.id,
            organization_id=self.organization_id,
        )
        self.assertEqual(completion.status, 'in_progress')

        # Complete lesson
        completion = CompletionService.complete_lesson(
            completion_id=completion.id,
            organization_id=self.organization_id,
            grade=Decimal('85.00'),
            flight_time=Decimal('1.5'),
            instructor_comments='Good first flight',
        )

        self.assertTrue(completion.is_completed)
        self.assertEqual(completion.result, 'pass')
        self.assertEqual(completion.grade, Decimal('85.00'))

    def test_grade_exercise(self):
        """Test grading an exercise."""
        # Create exercise
        exercise = Exercise.objects.create(
            organization_id=self.organization_id,
            lesson=self.lesson,
            code='E01',
            name='Straight and Level',
            min_grade=70,
        )

        # Create completion
        completion = CompletionService.create_completion(
            organization_id=self.organization_id,
            enrollment_id=self.enrollment.id,
            lesson_id=self.lesson.id,
        )

        # Grade exercise
        grade = CompletionService.grade_exercise(
            completion_id=completion.id,
            organization_id=self.organization_id,
            exercise_id=exercise.id,
            grade=Decimal('85.00'),
            demonstrations=3,
            successful_demonstrations=3,
        )

        self.assertEqual(grade.grade, Decimal('85.00'))
        self.assertTrue(grade.is_passed)


class StageCheckServiceTest(TestCase):
    """Tests for StageCheckService."""

    def setUp(self):
        """Set up test fixtures."""
        self.organization_id = uuid.uuid4()
        self.student_id = uuid.uuid4()
        self.examiner_id = uuid.uuid4()

        self.program = TrainingProgram.objects.create(
            organization_id=self.organization_id,
            code='PPL-2024',
            name='Private Pilot License',
            program_type='ppl',
        )

        stage = self.program.add_stage('Pre-Solo')
        self.stage_id = uuid.UUID(stage['id'])
        self.program.save()

        self.enrollment = StudentEnrollment.objects.create(
            organization_id=self.organization_id,
            student_id=self.student_id,
            program=self.program,
            enrollment_date=date.today(),
            status='active',
        )

    def test_create_stage_check(self):
        """Test creating a stage check."""
        check = StageCheckService.create_stage_check(
            organization_id=self.organization_id,
            enrollment_id=self.enrollment.id,
            stage_id=self.stage_id,
            check_type='combined',
            scheduled_date=date.today() + timedelta(days=7),
            examiner_id=self.examiner_id,
        )

        self.assertIsNotNone(check.id)
        self.assertIsNotNone(check.check_number)
        self.assertEqual(check.status, 'scheduled')

    def test_stage_check_workflow(self):
        """Test stage check workflow."""
        # Create check
        check = StageCheckService.create_stage_check(
            organization_id=self.organization_id,
            enrollment_id=self.enrollment.id,
            stage_id=self.stage_id,
            check_type='combined',
        )

        # Verify prerequisites (will pass as no lessons required)
        check.prerequisites_verified = True
        check.save()

        # Start check
        check = StageCheckService.start_stage_check(
            check_id=check.id,
            organization_id=self.organization_id,
            examiner_id=self.examiner_id,
        )
        self.assertEqual(check.status, 'in_progress')

        # Pass check
        check = StageCheckService.pass_stage_check(
            check_id=check.id,
            organization_id=self.organization_id,
            overall_grade=Decimal('85.00'),
            oral_grade=Decimal('88.00'),
            flight_grade=Decimal('82.00'),
        )

        self.assertTrue(check.is_passed)
        self.assertEqual(check.result, 'pass')

        # Verify enrollment stats updated
        self.enrollment.refresh_from_db()
        self.assertEqual(self.enrollment.stage_checks_passed, 1)

    def test_create_recheck(self):
        """Test creating a recheck for failed stage check."""
        # Create and fail first check
        check = StageCheckService.create_stage_check(
            organization_id=self.organization_id,
            enrollment_id=self.enrollment.id,
            stage_id=self.stage_id,
            check_type='combined',
            max_attempts=3,
        )
        check.prerequisites_verified = True
        check.status = 'in_progress'
        check.save()

        check = StageCheckService.fail_stage_check(
            check_id=check.id,
            organization_id=self.organization_id,
            disapproval_reasons=['Steep turns out of tolerance'],
        )

        # Create recheck
        recheck = StageCheckService.create_recheck(
            check_id=check.id,
            organization_id=self.organization_id,
            scheduled_date=date.today() + timedelta(days=14),
        )

        self.assertEqual(recheck.attempt_number, 2)
        self.assertEqual(recheck.previous_attempt_id, check.id)


class ProgressServiceTest(TestCase):
    """Tests for ProgressService."""

    def setUp(self):
        """Set up test fixtures."""
        self.organization_id = uuid.uuid4()
        self.student_id = uuid.uuid4()

        self.program = TrainingProgram.objects.create(
            organization_id=self.organization_id,
            code='PPL-2024',
            name='Private Pilot License',
            program_type='ppl',
        )

        self.enrollment = StudentEnrollment.objects.create(
            organization_id=self.organization_id,
            student_id=self.student_id,
            program=self.program,
            enrollment_date=date.today() - timedelta(days=30),
            status='active',
            total_flight_hours=Decimal('20.00'),
            total_ground_hours=Decimal('15.00'),
            completion_percentage=Decimal('45.00'),
            lessons_completed=9,
            lessons_total=20,
        )

    def test_get_student_progress(self):
        """Test getting student progress summary."""
        progress = ProgressService.get_student_progress(
            enrollment_id=self.enrollment.id,
            organization_id=self.organization_id,
        )

        self.assertIn('enrollment_id', progress)
        self.assertIn('overall_progress', progress)
        self.assertIn('hours', progress)
        self.assertEqual(progress['hours']['flight'], 20.0)
        self.assertEqual(progress['overall_progress']['completion_percentage'], 45.0)

    def test_get_hour_breakdown(self):
        """Test getting hour breakdown."""
        breakdown = ProgressService.get_hour_breakdown(
            enrollment_id=self.enrollment.id,
            organization_id=self.organization_id,
        )

        self.assertIn('totals', breakdown)
        self.assertIn('categories', breakdown)
        self.assertIn('requirements', breakdown)
        self.assertEqual(breakdown['totals']['flight'], 20.0)

    def test_generate_progress_report(self):
        """Test generating full progress report."""
        report = ProgressService.generate_progress_report(
            enrollment_id=self.enrollment.id,
            organization_id=self.organization_id,
        )

        self.assertIn('summary', report)
        self.assertIn('lesson_progress', report)
        self.assertIn('hours', report)
        self.assertIn('performance', report)
        self.assertIn('report_date', report)
