# services/training-service/src/apps/core/tests/test_api.py
"""
API Tests

Tests for training service REST API endpoints.
"""

import uuid
import json
from decimal import Decimal
from datetime import date, timedelta

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from ..models import (
    TrainingProgram,
    SyllabusLesson,
    StudentEnrollment,
    LessonCompletion,
    StageCheck,
)


class MockUser:
    """Mock user for testing."""
    def __init__(self):
        self.id = uuid.uuid4()
        self.is_authenticated = True


class TrainingProgramAPITest(TestCase):
    """Tests for TrainingProgram API endpoints."""

    def setUp(self):
        """Set up test fixtures."""
        self.client = APIClient()
        self.client.force_authenticate(user=MockUser())
        self.organization_id = str(uuid.uuid4())
        self.client.credentials(HTTP_X_ORGANIZATION_ID=self.organization_id)

        # Create test program
        self.program = TrainingProgram.objects.create(
            organization_id=self.organization_id,
            code='PPL-2024',
            name='Private Pilot License',
            program_type='ppl',
            min_hours_total=Decimal('45.00'),
        )

    def test_list_programs(self):
        """Test listing training programs."""
        response = self.client.get('/api/v1/training/programs/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
        self.assertEqual(len(response.data['results']), 1)

    def test_create_program(self):
        """Test creating a training program."""
        data = {
            'code': 'IR-2024',
            'name': 'Instrument Rating',
            'program_type': 'ir',
            'min_hours_total': '40.00',
        }

        response = self.client.post(
            '/api/v1/training/programs/',
            data,
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['code'], 'IR-2024')

    def test_get_program_detail(self):
        """Test getting program details."""
        response = self.client.get(
            f'/api/v1/training/programs/{self.program.id}/'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['code'], 'PPL-2024')

    def test_update_program(self):
        """Test updating a training program."""
        data = {
            'name': 'Updated PPL Name',
            'min_hours_total': '50.00',
        }

        response = self.client.patch(
            f'/api/v1/training/programs/{self.program.id}/',
            data,
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Updated PPL Name')

    def test_publish_program(self):
        """Test publishing a program."""
        # Add a lesson first (required for publishing)
        SyllabusLesson.objects.create(
            organization_id=self.organization_id,
            program=self.program,
            code='L01',
            name='First Lesson',
            lesson_type='ground',
        )

        response = self.client.post(
            f'/api/v1/training/programs/{self.program.id}/publish/'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['is_published'])

    def test_get_program_statistics(self):
        """Test getting program statistics."""
        response = self.client.get(
            f'/api/v1/training/programs/{self.program.id}/statistics/'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('enrollments', response.data)
        self.assertIn('lessons', response.data)


class EnrollmentAPITest(TestCase):
    """Tests for Enrollment API endpoints."""

    def setUp(self):
        """Set up test fixtures."""
        self.client = APIClient()
        self.client.force_authenticate(user=MockUser())
        self.organization_id = str(uuid.uuid4())
        self.student_id = str(uuid.uuid4())
        self.client.credentials(HTTP_X_ORGANIZATION_ID=self.organization_id)

        self.program = TrainingProgram.objects.create(
            organization_id=self.organization_id,
            code='PPL-2024',
            name='Private Pilot License',
            program_type='ppl',
            is_published=True,
            status='active',
        )

        self.enrollment = StudentEnrollment.objects.create(
            organization_id=self.organization_id,
            student_id=self.student_id,
            program=self.program,
            enrollment_date=date.today(),
        )

    def test_list_enrollments(self):
        """Test listing enrollments."""
        response = self.client.get('/api/v1/training/enrollments/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
        self.assertEqual(len(response.data['results']), 1)

    def test_create_enrollment(self):
        """Test creating an enrollment."""
        new_student_id = str(uuid.uuid4())
        data = {
            'student_id': new_student_id,
            'program': str(self.program.id),
            'enrollment_date': date.today().isoformat(),
        }

        response = self.client.post(
            '/api/v1/training/enrollments/',
            data,
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIsNotNone(response.data['enrollment_number'])

    def test_activate_enrollment(self):
        """Test activating an enrollment."""
        response = self.client.post(
            f'/api/v1/training/enrollments/{self.enrollment.id}/activate/',
            {},
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'active')

    def test_put_on_hold(self):
        """Test putting enrollment on hold."""
        # First activate
        self.enrollment.status = 'active'
        self.enrollment.save()

        response = self.client.post(
            f'/api/v1/training/enrollments/{self.enrollment.id}/hold/',
            {'reason': 'Personal reasons'},
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'on_hold')


class LessonCompletionAPITest(TestCase):
    """Tests for LessonCompletion API endpoints."""

    def setUp(self):
        """Set up test fixtures."""
        self.client = APIClient()
        self.client.force_authenticate(user=MockUser())
        self.organization_id = str(uuid.uuid4())
        self.student_id = str(uuid.uuid4())
        self.instructor_id = str(uuid.uuid4())
        self.client.credentials(HTTP_X_ORGANIZATION_ID=self.organization_id)

        self.program = TrainingProgram.objects.create(
            organization_id=self.organization_id,
            code='PPL-2024',
            name='Private Pilot License',
            program_type='ppl',
        )

        self.lesson = SyllabusLesson.objects.create(
            organization_id=self.organization_id,
            program=self.program,
            code='F01',
            name='First Flight',
            lesson_type='flight',
        )

        self.enrollment = StudentEnrollment.objects.create(
            organization_id=self.organization_id,
            student_id=self.student_id,
            program=self.program,
            enrollment_date=date.today(),
            status='active',
        )

        self.completion = LessonCompletion.objects.create(
            organization_id=self.organization_id,
            enrollment=self.enrollment,
            lesson=self.lesson,
            instructor_id=self.instructor_id,
            scheduled_date=date.today(),
        )

    def test_list_completions(self):
        """Test listing completions."""
        response = self.client.get('/api/v1/training/completions/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)

    def test_create_completion(self):
        """Test creating a completion."""
        new_lesson = SyllabusLesson.objects.create(
            organization_id=self.organization_id,
            program=self.program,
            code='F02',
            name='Second Flight',
            lesson_type='flight',
        )

        data = {
            'enrollment': str(self.enrollment.id),
            'lesson': str(new_lesson.id),
            'instructor_id': self.instructor_id,
            'scheduled_date': date.today().isoformat(),
        }

        response = self.client.post(
            '/api/v1/training/completions/',
            data,
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_start_lesson(self):
        """Test starting a lesson."""
        response = self.client.post(
            f'/api/v1/training/completions/{self.completion.id}/start/',
            {},
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'in_progress')

    def test_complete_lesson(self):
        """Test completing a lesson."""
        self.completion.status = 'in_progress'
        self.completion.save()

        response = self.client.post(
            f'/api/v1/training/completions/{self.completion.id}/complete/',
            {
                'grade': '85.00',
                'flight_time': '1.5',
                'instructor_comments': 'Good flight',
            },
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['is_completed'])


class StageCheckAPITest(TestCase):
    """Tests for StageCheck API endpoints."""

    def setUp(self):
        """Set up test fixtures."""
        self.client = APIClient()
        self.client.force_authenticate(user=MockUser())
        self.organization_id = str(uuid.uuid4())
        self.student_id = str(uuid.uuid4())
        self.examiner_id = str(uuid.uuid4())
        self.client.credentials(HTTP_X_ORGANIZATION_ID=self.organization_id)

        self.program = TrainingProgram.objects.create(
            organization_id=self.organization_id,
            code='PPL-2024',
            name='Private Pilot License',
            program_type='ppl',
        )

        stage = self.program.add_stage('Pre-Solo')
        self.stage_id = stage['id']
        self.program.save()

        self.enrollment = StudentEnrollment.objects.create(
            organization_id=self.organization_id,
            student_id=self.student_id,
            program=self.program,
            enrollment_date=date.today(),
            status='active',
        )

        self.check = StageCheck.objects.create(
            organization_id=self.organization_id,
            enrollment=self.enrollment,
            stage_id=self.stage_id,
            check_type='combined',
            scheduled_date=date.today() + timedelta(days=7),
        )

    def test_list_stage_checks(self):
        """Test listing stage checks."""
        response = self.client.get('/api/v1/training/stage-checks/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)

    def test_create_stage_check(self):
        """Test creating a stage check."""
        # Add another stage
        stage = self.program.add_stage('Solo')
        self.program.save()

        data = {
            'enrollment': str(self.enrollment.id),
            'stage_id': stage['id'],
            'check_type': 'flight',
            'scheduled_date': (date.today() + timedelta(days=14)).isoformat(),
        }

        response = self.client.post(
            '/api/v1/training/stage-checks/',
            data,
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_get_statistics(self):
        """Test getting stage check statistics."""
        response = self.client.get('/api/v1/training/stage-checks/statistics/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('total', response.data)
        self.assertIn('pass_rate', response.data)


class ProgressAPITest(TestCase):
    """Tests for Progress API endpoints."""

    def setUp(self):
        """Set up test fixtures."""
        self.client = APIClient()
        self.client.force_authenticate(user=MockUser())
        self.organization_id = str(uuid.uuid4())
        self.student_id = str(uuid.uuid4())
        self.client.credentials(HTTP_X_ORGANIZATION_ID=self.organization_id)

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
            completion_percentage=Decimal('45.00'),
        )

    def test_get_progress(self):
        """Test getting student progress."""
        response = self.client.get(
            f'/api/v1/training/progress/{self.enrollment.id}/'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('overall_progress', response.data)
        self.assertIn('hours', response.data)

    def test_get_lesson_progress(self):
        """Test getting lesson progress."""
        response = self.client.get(
            f'/api/v1/training/progress/{self.enrollment.id}/lessons/'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('lessons', response.data)

    def test_get_hours_breakdown(self):
        """Test getting hours breakdown."""
        response = self.client.get(
            f'/api/v1/training/progress/{self.enrollment.id}/hours/'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('totals', response.data)
        self.assertIn('requirements', response.data)

    def test_generate_report(self):
        """Test generating progress report."""
        response = self.client.get(
            f'/api/v1/training/progress/{self.enrollment.id}/report/'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('summary', response.data)
        self.assertIn('report_date', response.data)
