# services/theory-service/src/apps/core/tests/test_models.py
"""
Model Tests

Tests for theory service database models.
"""

import uuid
from decimal import Decimal
from datetime import date, timedelta

from django.test import TestCase
from django.utils import timezone

from ..models import (
    Course,
    CourseModule,
    CourseAttachment,
    Question,
    QuestionReview,
    Exam,
    ExamAttempt,
    CourseEnrollment,
    ModuleProgress,
    Certificate,
    CourseStatus,
    QuestionType,
    Difficulty,
    ExamType,
    AttemptStatus,
    EnrollmentStatus,
    CertificateStatus,
)


class CourseModelTest(TestCase):
    """Tests for Course model."""

    def setUp(self):
        """Set up test fixtures."""
        self.organization_id = uuid.uuid4()

    def test_create_course(self):
        """Test creating a course."""
        course = Course.objects.create(
            organization_id=self.organization_id,
            code='MET-101',
            name='Meteorology Fundamentals',
            category='meteorology',
            program_type='ppl',
            estimated_hours=Decimal('10.00'),
        )

        self.assertEqual(course.code, 'MET-101')
        self.assertEqual(course.category, 'meteorology')
        self.assertEqual(course.status, CourseStatus.DRAFT)
        self.assertFalse(course.is_published)

    def test_course_is_active_property(self):
        """Test is_active property."""
        course = Course.objects.create(
            organization_id=self.organization_id,
            code='MET-101',
            name='Meteorology',
            category='meteorology',
        )

        self.assertFalse(course.is_active)

        course.status = CourseStatus.PUBLISHED
        course.is_published = True
        course.save()

        self.assertTrue(course.is_active)

    def test_publish_course(self):
        """Test publishing a course."""
        course = Course.objects.create(
            organization_id=self.organization_id,
            code='MET-101',
            name='Meteorology',
            category='meteorology',
        )

        # Add a module first
        CourseModule.objects.create(
            course=course,
            name='Introduction',
            content_type='text',
        )

        course.publish()

        self.assertTrue(course.is_published)
        self.assertEqual(course.status, CourseStatus.PUBLISHED)
        self.assertIsNotNone(course.published_at)

    def test_publish_course_without_modules_fails(self):
        """Test publishing fails without modules."""
        course = Course.objects.create(
            organization_id=self.organization_id,
            code='MET-101',
            name='Meteorology',
            category='meteorology',
        )

        with self.assertRaises(ValueError):
            course.publish()

    def test_check_prerequisites(self):
        """Test check_prerequisites method."""
        prereq_id = uuid.uuid4()

        course = Course.objects.create(
            organization_id=self.organization_id,
            code='MET-201',
            name='Advanced Meteorology',
            category='meteorology',
            prerequisites=[prereq_id],
        )

        # Without prerequisite
        result = course.check_prerequisites([])
        self.assertFalse(result['met'])
        self.assertIn(str(prereq_id), result['missing'])

        # With prerequisite
        result = course.check_prerequisites([str(prereq_id)])
        self.assertTrue(result['met'])


class CourseModuleModelTest(TestCase):
    """Tests for CourseModule model."""

    def setUp(self):
        """Set up test fixtures."""
        self.organization_id = uuid.uuid4()
        self.course = Course.objects.create(
            organization_id=self.organization_id,
            code='MET-101',
            name='Meteorology',
            category='meteorology',
        )

    def test_create_module(self):
        """Test creating a module."""
        module = CourseModule.objects.create(
            course=self.course,
            name='Introduction to Weather',
            content_type='mixed',
            estimated_minutes=30,
        )

        self.assertEqual(module.course, self.course)
        self.assertEqual(module.content_type, 'mixed')

    def test_check_completion(self):
        """Test check_completion method."""
        module = CourseModule.objects.create(
            course=self.course,
            name='Video Module',
            content_type='video',
            completion_criteria={
                'video_watched_percentage': 90,
                'quiz_passed': True,
            },
        )

        # Not complete
        result = module.check_completion(
            video_watched_percentage=50,
            quiz_passed=False
        )
        self.assertFalse(result['completed'])

        # Complete
        result = module.check_completion(
            video_watched_percentage=95,
            quiz_passed=True
        )
        self.assertTrue(result['completed'])


class QuestionModelTest(TestCase):
    """Tests for Question model."""

    def setUp(self):
        """Set up test fixtures."""
        self.organization_id = uuid.uuid4()

    def test_create_question(self):
        """Test creating a question."""
        question = Question.objects.create(
            organization_id=self.organization_id,
            category='meteorology',
            question_type=QuestionType.MULTIPLE_CHOICE,
            question_text='What is the METAR code for rain?',
            options=[
                {'id': 'a', 'text': 'RA'},
                {'id': 'b', 'text': 'SN'},
                {'id': 'c', 'text': 'FG'},
                {'id': 'd', 'text': 'BR'},
            ],
            correct_answer={'option_id': 'a'},
            explanation='RA is the METAR code for rain.',
        )

        self.assertEqual(question.question_type, QuestionType.MULTIPLE_CHOICE)
        self.assertTrue(question.is_active)

    def test_check_answer_multiple_choice(self):
        """Test check_answer for multiple choice."""
        question = Question.objects.create(
            organization_id=self.organization_id,
            category='meteorology',
            question_type=QuestionType.MULTIPLE_CHOICE,
            question_text='Test question?',
            options=[
                {'id': 'a', 'text': 'Answer A'},
                {'id': 'b', 'text': 'Answer B'},
            ],
            correct_answer={'option_id': 'a'},
        )

        result = question.check_answer('a')
        self.assertTrue(result['correct'])

        result = question.check_answer('b')
        self.assertFalse(result['correct'])

    def test_check_answer_multi_select(self):
        """Test check_answer for multi-select."""
        question = Question.objects.create(
            organization_id=self.organization_id,
            category='meteorology',
            question_type=QuestionType.MULTI_SELECT,
            question_text='Select all correct answers:',
            options=[
                {'id': 'a', 'text': 'Answer A'},
                {'id': 'b', 'text': 'Answer B'},
                {'id': 'c', 'text': 'Answer C'},
            ],
            correct_answer={'option_ids': ['a', 'c']},
        )

        result = question.check_answer(['a', 'c'])
        self.assertTrue(result['correct'])

        result = question.check_answer(['a'])
        self.assertFalse(result['correct'])

    def test_update_statistics(self):
        """Test update_statistics method."""
        question = Question.objects.create(
            organization_id=self.organization_id,
            category='meteorology',
            question_type=QuestionType.MULTIPLE_CHOICE,
            question_text='Test?',
            options=[{'id': 'a', 'text': 'A'}],
            correct_answer={'option_id': 'a'},
        )

        question.update_statistics(is_correct=True, time_seconds=30)
        question.update_statistics(is_correct=False, time_seconds=45)

        self.assertEqual(question.times_asked, 2)
        self.assertEqual(question.times_correct, 1)
        self.assertEqual(question.success_rate, Decimal('50.00'))


class ExamModelTest(TestCase):
    """Tests for Exam model."""

    def setUp(self):
        """Set up test fixtures."""
        self.organization_id = uuid.uuid4()

    def test_create_exam(self):
        """Test creating an exam."""
        exam = Exam.objects.create(
            organization_id=self.organization_id,
            code='MET-FINAL',
            name='Meteorology Final Exam',
            exam_type=ExamType.FINAL,
            total_questions=50,
            time_limit_minutes=90,
            passing_score=75,
        )

        self.assertEqual(exam.exam_type, ExamType.FINAL)
        self.assertEqual(exam.passing_score, 75)
        self.assertTrue(exam.is_timed)

    def test_check_availability(self):
        """Test check_availability method."""
        user_id = str(uuid.uuid4())

        exam = Exam.objects.create(
            organization_id=self.organization_id,
            name='Test Exam',
            total_questions=10,
            max_attempts=3,
            is_published=True,
        )

        result = exam.check_availability(user_id)
        self.assertTrue(result['available'])

    def test_calculate_passing(self):
        """Test calculate_passing method."""
        exam = Exam.objects.create(
            organization_id=self.organization_id,
            name='Test Exam',
            total_questions=10,
            passing_score=75,
        )

        results = {'score_percentage': 80}
        self.assertTrue(exam.calculate_passing(results))

        results = {'score_percentage': 70}
        self.assertFalse(exam.calculate_passing(results))


class ExamAttemptModelTest(TestCase):
    """Tests for ExamAttempt model."""

    def setUp(self):
        """Set up test fixtures."""
        self.organization_id = uuid.uuid4()
        self.user_id = uuid.uuid4()
        self.exam = Exam.objects.create(
            organization_id=self.organization_id,
            name='Test Exam',
            total_questions=5,
            time_limit_minutes=30,
            passing_score=75,
        )

    def test_create_attempt(self):
        """Test creating an attempt."""
        attempt = ExamAttempt.objects.create(
            organization_id=self.organization_id,
            exam=self.exam,
            user_id=self.user_id,
            questions=[
                {'question_id': str(uuid.uuid4()), 'order': 1, 'points': 1}
            ],
            total_points=5,
        )

        self.assertEqual(attempt.status, AttemptStatus.IN_PROGRESS)
        self.assertEqual(attempt.attempt_number, 1)

    def test_save_answer(self):
        """Test save_answer method."""
        attempt = ExamAttempt.objects.create(
            organization_id=self.organization_id,
            exam=self.exam,
            user_id=self.user_id,
            questions=[],
            total_points=5,
        )

        q_id = str(uuid.uuid4())
        attempt.save_answer(q_id, 'a', time_spent_seconds=30)

        self.assertIn(q_id, attempt.answers)
        self.assertEqual(attempt.answers[q_id]['selected'], 'a')


class CourseEnrollmentModelTest(TestCase):
    """Tests for CourseEnrollment model."""

    def setUp(self):
        """Set up test fixtures."""
        self.organization_id = uuid.uuid4()
        self.user_id = uuid.uuid4()
        self.course = Course.objects.create(
            organization_id=self.organization_id,
            code='MET-101',
            name='Meteorology',
            category='meteorology',
        )

    def test_create_enrollment(self):
        """Test creating an enrollment."""
        enrollment = CourseEnrollment.objects.create(
            organization_id=self.organization_id,
            course=self.course,
            user_id=self.user_id,
        )

        self.assertEqual(enrollment.status, EnrollmentStatus.ENROLLED)
        self.assertFalse(enrollment.passed)

    def test_start_course(self):
        """Test starting a course."""
        enrollment = CourseEnrollment.objects.create(
            organization_id=self.organization_id,
            course=self.course,
            user_id=self.user_id,
        )

        enrollment.start()

        self.assertEqual(enrollment.status, EnrollmentStatus.IN_PROGRESS)
        self.assertIsNotNone(enrollment.started_at)

    def test_update_progress(self):
        """Test update_progress method."""
        enrollment = CourseEnrollment.objects.create(
            organization_id=self.organization_id,
            course=self.course,
            user_id=self.user_id,
            modules_total=4,
        )

        # Create modules and progress
        for i in range(4):
            module = CourseModule.objects.create(
                course=self.course,
                name=f'Module {i+1}',
                sort_order=i,
            )
            progress = ModuleProgress.objects.create(
                enrollment=enrollment,
                module=module,
                completed=(i < 2),  # First 2 completed
            )

        enrollment.update_progress()

        self.assertEqual(enrollment.modules_completed, 2)
        self.assertEqual(enrollment.progress_percentage, Decimal('50.00'))


class CertificateModelTest(TestCase):
    """Tests for Certificate model."""

    def setUp(self):
        """Set up test fixtures."""
        self.organization_id = uuid.uuid4()
        self.user_id = uuid.uuid4()
        self.course = Course.objects.create(
            organization_id=self.organization_id,
            code='MET-101',
            name='Meteorology',
            category='meteorology',
        )
        self.enrollment = CourseEnrollment.objects.create(
            organization_id=self.organization_id,
            course=self.course,
            user_id=self.user_id,
            status=EnrollmentStatus.COMPLETED,
            passed=True,
        )

    def test_create_certificate(self):
        """Test creating a certificate."""
        certificate = Certificate.objects.create(
            organization_id=self.organization_id,
            course=self.course,
            enrollment=self.enrollment,
            user_id=self.user_id,
            certificate_number='CERT-MET-12345',
            title='Meteorology Certificate',
            recipient_name='John Doe',
            course_name='Meteorology',
            course_category='meteorology',
            completion_date=date.today(),
            valid_from=date.today(),
            verification_code='ABC123',
        )

        self.assertEqual(certificate.status, CertificateStatus.PENDING)
        self.assertTrue(certificate.is_valid)

    def test_issue_certificate(self):
        """Test issuing a certificate."""
        certificate = Certificate.objects.create(
            organization_id=self.organization_id,
            course=self.course,
            enrollment=self.enrollment,
            user_id=self.user_id,
            certificate_number='CERT-MET-12345',
            title='Meteorology Certificate',
            recipient_name='John Doe',
            course_name='Meteorology',
            course_category='meteorology',
            completion_date=date.today(),
            valid_from=date.today(),
            verification_code='ABC123',
            status=CertificateStatus.GENERATED,
        )

        certificate.issue()

        self.assertEqual(certificate.status, CertificateStatus.ISSUED)
        self.assertIsNotNone(certificate.issued_at)

    def test_revoke_certificate(self):
        """Test revoking a certificate."""
        certificate = Certificate.objects.create(
            organization_id=self.organization_id,
            course=self.course,
            enrollment=self.enrollment,
            user_id=self.user_id,
            certificate_number='CERT-MET-12345',
            title='Meteorology Certificate',
            recipient_name='John Doe',
            course_name='Meteorology',
            course_category='meteorology',
            completion_date=date.today(),
            valid_from=date.today(),
            verification_code='ABC123',
            status=CertificateStatus.ISSUED,
        )

        certificate.revoke('Academic dishonesty')

        self.assertEqual(certificate.status, CertificateStatus.REVOKED)
        self.assertFalse(certificate.is_valid)
