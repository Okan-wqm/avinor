# services/training-service/src/apps/core/tests/test_models.py
"""
Model Tests

Tests for training service database models.
"""

import uuid
from decimal import Decimal
from datetime import date, timedelta

from django.test import TestCase
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from ..models import (
    TrainingProgram,
    ProgramStage,
    SyllabusLesson,
    Exercise,
    StudentEnrollment,
    LessonCompletion,
    ExerciseGrade,
    StageCheck,
)


class TrainingProgramModelTest(TestCase):
    """Tests for TrainingProgram model."""

    def setUp(self):
        """Set up test fixtures."""
        self.organization_id = uuid.uuid4()

    def test_create_training_program(self):
        """Test creating a training program."""
        program = TrainingProgram.objects.create(
            organization_id=self.organization_id,
            code='PPL-2024',
            name='Private Pilot License',
            program_type='ppl',
            min_hours_total=Decimal('45.00'),
            min_hours_dual=Decimal('25.00'),
            min_hours_solo=Decimal('10.00'),
        )

        self.assertEqual(program.code, 'PPL-2024')
        self.assertEqual(program.name, 'Private Pilot License')
        self.assertEqual(program.program_type, 'ppl')
        self.assertEqual(program.status, 'draft')
        self.assertFalse(program.is_published)

    def test_program_unique_code_per_org(self):
        """Test that program code is unique per organization."""
        TrainingProgram.objects.create(
            organization_id=self.organization_id,
            code='PPL-2024',
            name='Private Pilot License',
            program_type='ppl',
        )

        with self.assertRaises(IntegrityError):
            TrainingProgram.objects.create(
                organization_id=self.organization_id,
                code='PPL-2024',
                name='Another PPL',
                program_type='ppl',
            )

    def test_program_is_active_property(self):
        """Test is_active property."""
        program = TrainingProgram.objects.create(
            organization_id=self.organization_id,
            code='PPL-2024',
            name='Private Pilot License',
            program_type='ppl',
            status='draft',
            is_published=False,
        )

        self.assertFalse(program.is_active)

        program.status = 'active'
        program.is_published = True
        program.save()

        self.assertTrue(program.is_active)

    def test_add_stage(self):
        """Test adding stages to a program."""
        program = TrainingProgram.objects.create(
            organization_id=self.organization_id,
            code='PPL-2024',
            name='Private Pilot License',
            program_type='ppl',
        )

        stage1 = program.add_stage('Pre-Solo', 'Initial training phase')
        stage2 = program.add_stage('Solo', 'Solo flying phase')

        self.assertEqual(len(program.stages), 2)
        self.assertEqual(stage1['name'], 'Pre-Solo')
        self.assertEqual(stage2['order'], 2)

    def test_get_stage(self):
        """Test getting a stage by ID."""
        program = TrainingProgram.objects.create(
            organization_id=self.organization_id,
            code='PPL-2024',
            name='Private Pilot License',
            program_type='ppl',
        )

        stage = program.add_stage('Pre-Solo')
        stage_id = stage['id']

        retrieved = program.get_stage(stage_id)
        self.assertEqual(retrieved['name'], 'Pre-Solo')

    def test_get_next_stage(self):
        """Test getting the next stage."""
        program = TrainingProgram.objects.create(
            organization_id=self.organization_id,
            code='PPL-2024',
            name='Private Pilot License',
            program_type='ppl',
        )

        stage1 = program.add_stage('Pre-Solo')
        stage2 = program.add_stage('Solo')
        program.add_stage('Cross-Country')

        next_stage = program.get_next_stage(stage1['id'])
        self.assertEqual(next_stage['name'], 'Solo')

        next_stage = program.get_next_stage(stage2['id'])
        self.assertEqual(next_stage['name'], 'Cross-Country')

    def test_requirements_summary(self):
        """Test get_requirements_summary method."""
        program = TrainingProgram.objects.create(
            organization_id=self.organization_id,
            code='PPL-2024',
            name='Private Pilot License',
            program_type='ppl',
            min_hours_total=Decimal('45.00'),
            min_hours_dual=Decimal('25.00'),
            min_age=17,
            required_medical_class=2,
        )

        summary = program.get_requirements_summary()

        self.assertEqual(summary['min_hours']['total'], 45.0)
        self.assertEqual(summary['min_hours']['dual'], 25.0)
        self.assertEqual(summary['min_age'], 17)
        self.assertEqual(summary['medical_class'], 2)


class SyllabusLessonModelTest(TestCase):
    """Tests for SyllabusLesson model."""

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
        """Test creating a syllabus lesson."""
        lesson = SyllabusLesson.objects.create(
            organization_id=self.organization_id,
            program=self.program,
            code='L01',
            name='Introduction to Flight',
            lesson_type='ground',
            ground_hours=Decimal('2.0'),
        )

        self.assertEqual(lesson.code, 'L01')
        self.assertEqual(lesson.lesson_type, 'ground')
        self.assertEqual(lesson.status, 'active')

    def test_is_flight_lesson_property(self):
        """Test is_flight_lesson property."""
        ground_lesson = SyllabusLesson.objects.create(
            organization_id=self.organization_id,
            program=self.program,
            code='G01',
            name='Ground School',
            lesson_type='ground',
        )

        flight_lesson = SyllabusLesson.objects.create(
            organization_id=self.organization_id,
            program=self.program,
            code='F01',
            name='First Flight',
            lesson_type='flight',
        )

        self.assertFalse(ground_lesson.is_flight_lesson)
        self.assertTrue(flight_lesson.is_flight_lesson)

    def test_total_duration_property(self):
        """Test total_duration property."""
        lesson = SyllabusLesson.objects.create(
            organization_id=self.organization_id,
            program=self.program,
            code='L01',
            name='Combined Lesson',
            lesson_type='flight',
            ground_hours=Decimal('1.0'),
            flight_hours=Decimal('1.5'),
            briefing_hours=Decimal('0.5'),
        )

        self.assertEqual(lesson.total_duration, Decimal('3.0'))

    def test_check_prerequisites(self):
        """Test check_prerequisites method."""
        lesson1 = SyllabusLesson.objects.create(
            organization_id=self.organization_id,
            program=self.program,
            code='L01',
            name='Lesson 1',
            lesson_type='ground',
        )

        lesson2 = SyllabusLesson.objects.create(
            organization_id=self.organization_id,
            program=self.program,
            code='L02',
            name='Lesson 2',
            lesson_type='flight',
            prerequisite_lessons=[lesson1.id],
            prerequisite_hours=Decimal('5.0'),
        )

        # Without prerequisites
        result = lesson2.check_prerequisites([], Decimal('0'))
        self.assertFalse(result['met'])
        self.assertIn(str(lesson1.id), result['missing_lessons'])

        # With lesson completed but not enough hours
        result = lesson2.check_prerequisites([str(lesson1.id)], Decimal('3.0'))
        self.assertFalse(result['met'])
        self.assertEqual(result['hours_required'], 5.0)

        # With all prerequisites met
        result = lesson2.check_prerequisites([str(lesson1.id)], Decimal('5.0'))
        self.assertTrue(result['met'])


class StudentEnrollmentModelTest(TestCase):
    """Tests for StudentEnrollment model."""

    def setUp(self):
        """Set up test fixtures."""
        self.organization_id = uuid.uuid4()
        self.student_id = uuid.uuid4()
        self.program = TrainingProgram.objects.create(
            organization_id=self.organization_id,
            code='PPL-2024',
            name='Private Pilot License',
            program_type='ppl',
            min_hours_total=Decimal('45.00'),
        )

    def test_create_enrollment(self):
        """Test creating a student enrollment."""
        enrollment = StudentEnrollment.objects.create(
            organization_id=self.organization_id,
            student_id=self.student_id,
            program=self.program,
            enrollment_date=date.today(),
        )

        self.assertEqual(enrollment.status, 'pending')
        self.assertFalse(enrollment.is_active)

    def test_activate_enrollment(self):
        """Test activating an enrollment."""
        enrollment = StudentEnrollment.objects.create(
            organization_id=self.organization_id,
            student_id=self.student_id,
            program=self.program,
            enrollment_date=date.today(),
        )

        enrollment.activate()

        self.assertEqual(enrollment.status, 'active')
        self.assertTrue(enrollment.is_active)
        self.assertEqual(enrollment.start_date, date.today())

    def test_put_on_hold(self):
        """Test putting enrollment on hold."""
        enrollment = StudentEnrollment.objects.create(
            organization_id=self.organization_id,
            student_id=self.student_id,
            program=self.program,
            enrollment_date=date.today(),
            status='active',
        )

        enrollment.put_on_hold('Medical reasons')

        self.assertEqual(enrollment.status, 'on_hold')
        self.assertEqual(enrollment.hold_reason, 'Medical reasons')

    def test_check_hour_requirements(self):
        """Test check_hour_requirements method."""
        enrollment = StudentEnrollment.objects.create(
            organization_id=self.organization_id,
            student_id=self.student_id,
            program=self.program,
            enrollment_date=date.today(),
            total_flight_hours=Decimal('30.00'),
        )

        result = enrollment.check_hour_requirements()

        self.assertFalse(result['met'])
        self.assertEqual(result['details']['total']['required'], 45.0)
        self.assertEqual(result['details']['total']['current'], 30.0)
        self.assertEqual(result['details']['total']['remaining'], 15.0)

    def test_days_enrolled_property(self):
        """Test days_enrolled property."""
        enrollment = StudentEnrollment.objects.create(
            organization_id=self.organization_id,
            student_id=self.student_id,
            program=self.program,
            enrollment_date=date.today() - timedelta(days=30),
        )

        self.assertEqual(enrollment.days_enrolled, 30)

    def test_total_training_hours_property(self):
        """Test total_training_hours property."""
        enrollment = StudentEnrollment.objects.create(
            organization_id=self.organization_id,
            student_id=self.student_id,
            program=self.program,
            enrollment_date=date.today(),
            total_flight_hours=Decimal('20.00'),
            total_ground_hours=Decimal('15.00'),
            total_simulator_hours=Decimal('5.00'),
        )

        self.assertEqual(enrollment.total_training_hours, Decimal('40.00'))


class LessonCompletionModelTest(TestCase):
    """Tests for LessonCompletion model."""

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
        self.lesson = SyllabusLesson.objects.create(
            organization_id=self.organization_id,
            program=self.program,
            code='L01',
            name='First Flight',
            lesson_type='flight',
            min_grade_to_pass=70,
        )
        self.enrollment = StudentEnrollment.objects.create(
            organization_id=self.organization_id,
            student_id=self.student_id,
            program=self.program,
            enrollment_date=date.today(),
        )

    def test_create_completion(self):
        """Test creating a lesson completion."""
        completion = LessonCompletion.objects.create(
            organization_id=self.organization_id,
            enrollment=self.enrollment,
            lesson=self.lesson,
            scheduled_date=date.today(),
        )

        self.assertEqual(completion.status, 'scheduled')
        self.assertFalse(completion.is_completed)

    def test_complete_lesson(self):
        """Test completing a lesson."""
        completion = LessonCompletion.objects.create(
            organization_id=self.organization_id,
            enrollment=self.enrollment,
            lesson=self.lesson,
            status='in_progress',
        )

        completion.complete(grade=Decimal('85.00'))

        self.assertTrue(completion.is_completed)
        self.assertEqual(completion.result, 'pass')
        self.assertEqual(completion.grade, Decimal('85.00'))

    def test_is_passed_property(self):
        """Test is_passed property."""
        completion = LessonCompletion.objects.create(
            organization_id=self.organization_id,
            enrollment=self.enrollment,
            lesson=self.lesson,
        )

        completion.complete(grade=Decimal('65.00'))
        self.assertFalse(completion.is_passed)

        completion.grade = Decimal('80.00')
        completion.result = 'pass'
        completion.save()
        self.assertTrue(completion.is_passed)

    def test_total_time_property(self):
        """Test total_time property."""
        completion = LessonCompletion.objects.create(
            organization_id=self.organization_id,
            enrollment=self.enrollment,
            lesson=self.lesson,
            flight_time=Decimal('1.5'),
            ground_time=Decimal('0.5'),
            simulator_time=Decimal('0.0'),
        )

        self.assertEqual(completion.total_time, Decimal('2.0'))


class StageCheckModelTest(TestCase):
    """Tests for StageCheck model."""

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
        stage = self.program.add_stage('Pre-Solo')
        self.stage_id = uuid.UUID(stage['id'])
        self.enrollment = StudentEnrollment.objects.create(
            organization_id=self.organization_id,
            student_id=self.student_id,
            program=self.program,
            enrollment_date=date.today(),
        )

    def test_create_stage_check(self):
        """Test creating a stage check."""
        check = StageCheck.objects.create(
            organization_id=self.organization_id,
            enrollment=self.enrollment,
            stage_id=self.stage_id,
            check_type='combined',
            scheduled_date=date.today(),
        )

        self.assertEqual(check.status, 'scheduled')
        self.assertFalse(check.is_passed)
        self.assertEqual(check.attempt_number, 1)

    def test_can_retry_property(self):
        """Test can_retry property."""
        check = StageCheck.objects.create(
            organization_id=self.organization_id,
            enrollment=self.enrollment,
            stage_id=self.stage_id,
            check_type='combined',
            max_attempts=3,
            attempt_number=2,
            is_passed=False,
        )

        self.assertTrue(check.can_retry)

        check.attempt_number = 3
        check.save()
        self.assertFalse(check.can_retry)

    def test_is_final_attempt_property(self):
        """Test is_final_attempt property."""
        check = StageCheck.objects.create(
            organization_id=self.organization_id,
            enrollment=self.enrollment,
            stage_id=self.stage_id,
            check_type='combined',
            max_attempts=3,
            attempt_number=3,
        )

        self.assertTrue(check.is_final_attempt)

    def test_add_oral_topic(self):
        """Test add_oral_topic method."""
        check = StageCheck.objects.create(
            organization_id=self.organization_id,
            enrollment=self.enrollment,
            stage_id=self.stage_id,
            check_type='oral',
            status='in_progress',
        )

        check.add_oral_topic('Weather', 85.0, 'Good understanding')
        check.add_oral_topic('Airspace', 90.0)

        self.assertEqual(len(check.oral_topics), 2)
        self.assertEqual(check.oral_topics[0]['topic'], 'Weather')
        self.assertEqual(check.oral_topics[0]['grade'], 85.0)
