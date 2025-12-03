# services/theory-service/src/apps/core/tests/test_services.py
"""
Service Tests

Tests for theory service business logic layer.
"""

import uuid
from decimal import Decimal
from datetime import date, timedelta
from unittest.mock import patch, MagicMock

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
    ReviewStatus,
)
from ..services import (
    CourseService,
    QuestionService,
    ExamService,
    EnrollmentService,
    CertificateService,
    PracticeService,
)


class CourseServiceTest(TestCase):
    """Tests for CourseService."""

    def setUp(self):
        """Set up test fixtures."""
        self.organization_id = str(uuid.uuid4())
        self.user_id = str(uuid.uuid4())

    def test_create_course(self):
        """Test creating a course."""
        course = CourseService.create_course(
            organization_id=self.organization_id,
            code='MET-101',
            name='Meteorology Fundamentals',
            category='meteorology',
            program_type='ppl',
            created_by=self.user_id,
        )

        self.assertEqual(course.code, 'MET-101')
        self.assertEqual(course.status, CourseStatus.DRAFT)

    def test_get_course(self):
        """Test getting a course by ID."""
        course = Course.objects.create(
            organization_id=self.organization_id,
            code='MET-101',
            name='Meteorology',
            category='meteorology',
        )

        result = CourseService.get_course(
            organization_id=self.organization_id,
            course_id=str(course.id),
        )

        self.assertEqual(result.id, course.id)

    def test_get_course_not_found(self):
        """Test getting non-existent course raises error."""
        with self.assertRaises(ValueError):
            CourseService.get_course(
                organization_id=self.organization_id,
                course_id=str(uuid.uuid4()),
            )

    def test_list_courses(self):
        """Test listing courses with filters."""
        Course.objects.create(
            organization_id=self.organization_id,
            code='MET-101',
            name='Meteorology',
            category='meteorology',
        )
        Course.objects.create(
            organization_id=self.organization_id,
            code='NAV-101',
            name='Navigation',
            category='navigation',
        )

        courses = CourseService.list_courses(
            organization_id=self.organization_id,
            category='meteorology',
        )

        self.assertEqual(len(courses), 1)
        self.assertEqual(courses[0].category, 'meteorology')

    def test_publish_course(self):
        """Test publishing a course."""
        course = Course.objects.create(
            organization_id=self.organization_id,
            code='MET-101',
            name='Meteorology',
            category='meteorology',
        )
        CourseModule.objects.create(
            course=course,
            name='Introduction',
            content_type='text',
        )

        result = CourseService.publish_course(
            organization_id=self.organization_id,
            course_id=str(course.id),
        )

        self.assertTrue(result.is_published)
        self.assertEqual(result.status, CourseStatus.PUBLISHED)

    def test_publish_course_without_modules_fails(self):
        """Test publishing fails without modules."""
        course = Course.objects.create(
            organization_id=self.organization_id,
            code='MET-101',
            name='Meteorology',
            category='meteorology',
        )

        with self.assertRaises(ValueError):
            CourseService.publish_course(
                organization_id=self.organization_id,
                course_id=str(course.id),
            )

    def test_archive_course(self):
        """Test archiving a course."""
        course = Course.objects.create(
            organization_id=self.organization_id,
            code='MET-101',
            name='Meteorology',
            category='meteorology',
            status=CourseStatus.PUBLISHED,
        )

        result = CourseService.archive_course(
            organization_id=self.organization_id,
            course_id=str(course.id),
        )

        self.assertEqual(result.status, CourseStatus.ARCHIVED)

    def test_clone_course(self):
        """Test cloning a course."""
        course = Course.objects.create(
            organization_id=self.organization_id,
            code='MET-101',
            name='Meteorology',
            category='meteorology',
        )
        CourseModule.objects.create(
            course=course,
            name='Introduction',
            content_type='text',
        )

        cloned = CourseService.clone_course(
            organization_id=self.organization_id,
            course_id=str(course.id),
            new_code='MET-102',
        )

        self.assertEqual(cloned.code, 'MET-102')
        self.assertNotEqual(cloned.id, course.id)
        self.assertEqual(cloned.modules.count(), 1)

    def test_add_module(self):
        """Test adding a module to a course."""
        course = Course.objects.create(
            organization_id=self.organization_id,
            code='MET-101',
            name='Meteorology',
            category='meteorology',
        )

        module = CourseService.add_module(
            organization_id=self.organization_id,
            course_id=str(course.id),
            name='Introduction',
            content_type='text',
        )

        self.assertEqual(module.course, course)
        self.assertEqual(module.name, 'Introduction')

    def test_get_course_statistics(self):
        """Test getting course statistics."""
        course = Course.objects.create(
            organization_id=self.organization_id,
            code='MET-101',
            name='Meteorology',
            category='meteorology',
        )

        stats = CourseService.get_course_statistics(
            organization_id=self.organization_id,
            course_id=str(course.id),
        )

        self.assertIn('total_enrollments', stats)
        self.assertIn('completion_rate', stats)


class QuestionServiceTest(TestCase):
    """Tests for QuestionService."""

    def setUp(self):
        """Set up test fixtures."""
        self.organization_id = str(uuid.uuid4())
        self.user_id = str(uuid.uuid4())

    def test_create_question(self):
        """Test creating a question."""
        question = QuestionService.create_question(
            organization_id=self.organization_id,
            category='meteorology',
            question_type=QuestionType.MULTIPLE_CHOICE,
            question_text='What is METAR?',
            options=[
                {'id': 'a', 'text': 'Weather report'},
                {'id': 'b', 'text': 'Flight plan'},
            ],
            correct_answer={'option_id': 'a'},
            created_by=self.user_id,
        )

        self.assertEqual(question.category, 'meteorology')
        self.assertTrue(question.is_active)

    def test_list_questions(self):
        """Test listing questions with filters."""
        Question.objects.create(
            organization_id=self.organization_id,
            category='meteorology',
            question_type=QuestionType.MULTIPLE_CHOICE,
            question_text='Question 1?',
            options=[{'id': 'a', 'text': 'A'}],
            correct_answer={'option_id': 'a'},
            difficulty=Difficulty.EASY,
        )
        Question.objects.create(
            organization_id=self.organization_id,
            category='navigation',
            question_type=QuestionType.MULTIPLE_CHOICE,
            question_text='Question 2?',
            options=[{'id': 'a', 'text': 'A'}],
            correct_answer={'option_id': 'a'},
            difficulty=Difficulty.HARD,
        )

        questions = QuestionService.list_questions(
            organization_id=self.organization_id,
            category='meteorology',
        )

        self.assertEqual(len(questions), 1)

    def test_submit_review(self):
        """Test submitting a question review."""
        question = Question.objects.create(
            organization_id=self.organization_id,
            category='meteorology',
            question_type=QuestionType.MULTIPLE_CHOICE,
            question_text='Test?',
            options=[{'id': 'a', 'text': 'A'}],
            correct_answer={'option_id': 'a'},
        )

        review = QuestionService.submit_review(
            organization_id=self.organization_id,
            question_id=str(question.id),
            reviewer_id=self.user_id,
            status=ReviewStatus.APPROVED,
        )

        self.assertEqual(review.status, ReviewStatus.APPROVED)
        question.refresh_from_db()
        self.assertTrue(question.is_reviewed)

    def test_get_question_statistics(self):
        """Test getting question statistics."""
        question = Question.objects.create(
            organization_id=self.organization_id,
            category='meteorology',
            question_type=QuestionType.MULTIPLE_CHOICE,
            question_text='Test?',
            options=[{'id': 'a', 'text': 'A'}],
            correct_answer={'option_id': 'a'},
            times_asked=100,
            times_correct=75,
        )

        stats = QuestionService.get_question_statistics(
            organization_id=self.organization_id,
            question_id=str(question.id),
        )

        self.assertEqual(stats['times_asked'], 100)
        self.assertEqual(stats['times_correct'], 75)


class ExamServiceTest(TestCase):
    """Tests for ExamService."""

    def setUp(self):
        """Set up test fixtures."""
        self.organization_id = str(uuid.uuid4())
        self.user_id = str(uuid.uuid4())
        self.exam = Exam.objects.create(
            organization_id=self.organization_id,
            name='Test Exam',
            total_questions=5,
            time_limit_minutes=30,
            passing_score=75,
            is_published=True,
        )

    def test_create_exam(self):
        """Test creating an exam."""
        exam = ExamService.create_exam(
            organization_id=self.organization_id,
            name='New Exam',
            exam_type=ExamType.FINAL,
            total_questions=50,
            time_limit_minutes=90,
            passing_score=75,
        )

        self.assertEqual(exam.name, 'New Exam')
        self.assertEqual(exam.exam_type, ExamType.FINAL)

    def test_start_exam(self):
        """Test starting an exam attempt."""
        # Create questions for the exam
        for i in range(5):
            Question.objects.create(
                organization_id=self.organization_id,
                category='meteorology',
                question_type=QuestionType.MULTIPLE_CHOICE,
                question_text=f'Question {i+1}?',
                options=[
                    {'id': 'a', 'text': 'A'},
                    {'id': 'b', 'text': 'B'},
                ],
                correct_answer={'option_id': 'a'},
            )

        self.exam.question_categories = ['meteorology']
        self.exam.save()

        attempt = ExamService.start_exam(
            organization_id=self.organization_id,
            exam_id=str(self.exam.id),
            user_id=self.user_id,
        )

        self.assertEqual(attempt.status, AttemptStatus.IN_PROGRESS)
        self.assertIsNotNone(attempt.started_at)

    def test_save_answer(self):
        """Test saving an answer during exam."""
        attempt = ExamAttempt.objects.create(
            organization_id=self.organization_id,
            exam=self.exam,
            user_id=self.user_id,
            questions=[],
            total_points=5,
        )

        question_id = str(uuid.uuid4())
        ExamService.save_answer(
            organization_id=self.organization_id,
            attempt_id=str(attempt.id),
            question_id=question_id,
            answer='a',
        )

        attempt.refresh_from_db()
        self.assertIn(question_id, attempt.answers)

    def test_submit_exam(self):
        """Test submitting an exam attempt."""
        question = Question.objects.create(
            organization_id=self.organization_id,
            category='meteorology',
            question_type=QuestionType.MULTIPLE_CHOICE,
            question_text='Test?',
            options=[
                {'id': 'a', 'text': 'A'},
                {'id': 'b', 'text': 'B'},
            ],
            correct_answer={'option_id': 'a'},
        )

        attempt = ExamAttempt.objects.create(
            organization_id=self.organization_id,
            exam=self.exam,
            user_id=self.user_id,
            questions=[
                {'question_id': str(question.id), 'order': 1, 'points': 1}
            ],
            total_points=1,
            answers={
                str(question.id): {'selected': 'a', 'timestamp': timezone.now().isoformat()}
            },
        )

        result = ExamService.submit_exam(
            organization_id=self.organization_id,
            attempt_id=str(attempt.id),
        )

        self.assertEqual(result['status'], AttemptStatus.COMPLETED)
        self.assertIn('score', result)

    def test_get_user_attempts(self):
        """Test getting user's exam attempts."""
        ExamAttempt.objects.create(
            organization_id=self.organization_id,
            exam=self.exam,
            user_id=self.user_id,
            questions=[],
            total_points=5,
        )

        attempts = ExamService.get_user_attempts(
            organization_id=self.organization_id,
            user_id=self.user_id,
        )

        self.assertEqual(len(attempts), 1)


class EnrollmentServiceTest(TestCase):
    """Tests for EnrollmentService."""

    def setUp(self):
        """Set up test fixtures."""
        self.organization_id = str(uuid.uuid4())
        self.user_id = str(uuid.uuid4())
        self.course = Course.objects.create(
            organization_id=self.organization_id,
            code='MET-101',
            name='Meteorology',
            category='meteorology',
            is_published=True,
            status=CourseStatus.PUBLISHED,
        )

    def test_enroll_user(self):
        """Test enrolling a user in a course."""
        enrollment = EnrollmentService.enroll_user(
            organization_id=self.organization_id,
            user_id=self.user_id,
            course_id=str(self.course.id),
        )

        self.assertEqual(enrollment.status, EnrollmentStatus.ENROLLED)
        self.assertEqual(enrollment.user_id, uuid.UUID(self.user_id))

    def test_enroll_user_duplicate_fails(self):
        """Test enrolling same user twice fails."""
        EnrollmentService.enroll_user(
            organization_id=self.organization_id,
            user_id=self.user_id,
            course_id=str(self.course.id),
        )

        with self.assertRaises(ValueError):
            EnrollmentService.enroll_user(
                organization_id=self.organization_id,
                user_id=self.user_id,
                course_id=str(self.course.id),
            )

    def test_start_course(self):
        """Test starting a course."""
        enrollment = CourseEnrollment.objects.create(
            organization_id=self.organization_id,
            course=self.course,
            user_id=self.user_id,
        )

        result = EnrollmentService.start_course(
            organization_id=self.organization_id,
            enrollment_id=str(enrollment.id),
        )

        self.assertEqual(result.status, EnrollmentStatus.IN_PROGRESS)
        self.assertIsNotNone(result.started_at)

    def test_record_module_activity(self):
        """Test recording module activity."""
        module = CourseModule.objects.create(
            course=self.course,
            name='Introduction',
            content_type='text',
        )
        enrollment = CourseEnrollment.objects.create(
            organization_id=self.organization_id,
            course=self.course,
            user_id=self.user_id,
        )
        progress = ModuleProgress.objects.create(
            enrollment=enrollment,
            module=module,
        )

        result = EnrollmentService.record_module_activity(
            organization_id=self.organization_id,
            progress_id=str(progress.id),
            activity_type='page_view',
            activity_data={'page': 1},
        )

        self.assertIn('page_view', result.activities)

    def test_complete_module(self):
        """Test completing a module."""
        module = CourseModule.objects.create(
            course=self.course,
            name='Introduction',
            content_type='text',
        )
        enrollment = CourseEnrollment.objects.create(
            organization_id=self.organization_id,
            course=self.course,
            user_id=self.user_id,
            modules_total=1,
        )
        progress = ModuleProgress.objects.create(
            enrollment=enrollment,
            module=module,
        )

        result = EnrollmentService.complete_module(
            organization_id=self.organization_id,
            progress_id=str(progress.id),
        )

        self.assertTrue(result.completed)
        self.assertIsNotNone(result.completed_at)

    def test_get_user_enrollments(self):
        """Test getting user's enrollments."""
        CourseEnrollment.objects.create(
            organization_id=self.organization_id,
            course=self.course,
            user_id=self.user_id,
        )

        enrollments = EnrollmentService.get_user_enrollments(
            organization_id=self.organization_id,
            user_id=self.user_id,
        )

        self.assertEqual(len(enrollments), 1)


class CertificateServiceTest(TestCase):
    """Tests for CertificateService."""

    def setUp(self):
        """Set up test fixtures."""
        self.organization_id = str(uuid.uuid4())
        self.user_id = str(uuid.uuid4())
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

    def test_generate_certificate(self):
        """Test generating a certificate."""
        certificate = CertificateService.generate_certificate(
            organization_id=self.organization_id,
            enrollment_id=str(self.enrollment.id),
            recipient_name='John Doe',
        )

        self.assertEqual(certificate.status, CertificateStatus.GENERATED)
        self.assertIsNotNone(certificate.certificate_number)
        self.assertIsNotNone(certificate.verification_code)

    def test_generate_certificate_not_passed_fails(self):
        """Test generating certificate for non-passed enrollment fails."""
        self.enrollment.passed = False
        self.enrollment.save()

        with self.assertRaises(ValueError):
            CertificateService.generate_certificate(
                organization_id=self.organization_id,
                enrollment_id=str(self.enrollment.id),
                recipient_name='John Doe',
            )

    def test_issue_certificate(self):
        """Test issuing a certificate."""
        certificate = Certificate.objects.create(
            organization_id=self.organization_id,
            course=self.course,
            enrollment=self.enrollment,
            user_id=self.user_id,
            certificate_number='CERT-12345',
            title='Meteorology Certificate',
            recipient_name='John Doe',
            course_name='Meteorology',
            course_category='meteorology',
            completion_date=date.today(),
            valid_from=date.today(),
            verification_code='ABC123',
            status=CertificateStatus.GENERATED,
        )

        result = CertificateService.issue_certificate(
            organization_id=self.organization_id,
            certificate_id=str(certificate.id),
        )

        self.assertEqual(result.status, CertificateStatus.ISSUED)
        self.assertIsNotNone(result.issued_at)

    def test_verify_certificate(self):
        """Test verifying a certificate."""
        certificate = Certificate.objects.create(
            organization_id=self.organization_id,
            course=self.course,
            enrollment=self.enrollment,
            user_id=self.user_id,
            certificate_number='CERT-12345',
            title='Meteorology Certificate',
            recipient_name='John Doe',
            course_name='Meteorology',
            course_category='meteorology',
            completion_date=date.today(),
            valid_from=date.today(),
            verification_code='ABC123',
            status=CertificateStatus.ISSUED,
        )

        result = CertificateService.verify_certificate(
            verification_code='ABC123',
        )

        self.assertTrue(result['valid'])
        self.assertEqual(result['certificate_number'], 'CERT-12345')

    def test_verify_certificate_invalid(self):
        """Test verifying invalid certificate."""
        result = CertificateService.verify_certificate(
            verification_code='INVALID',
        )

        self.assertFalse(result['valid'])

    def test_revoke_certificate(self):
        """Test revoking a certificate."""
        certificate = Certificate.objects.create(
            organization_id=self.organization_id,
            course=self.course,
            enrollment=self.enrollment,
            user_id=self.user_id,
            certificate_number='CERT-12345',
            title='Meteorology Certificate',
            recipient_name='John Doe',
            course_name='Meteorology',
            course_category='meteorology',
            completion_date=date.today(),
            valid_from=date.today(),
            verification_code='ABC123',
            status=CertificateStatus.ISSUED,
        )

        result = CertificateService.revoke_certificate(
            organization_id=self.organization_id,
            certificate_id=str(certificate.id),
            reason='Academic dishonesty',
            revoked_by=self.user_id,
        )

        self.assertEqual(result.status, CertificateStatus.REVOKED)
        self.assertFalse(result.is_valid)


class PracticeServiceTest(TestCase):
    """Tests for PracticeService."""

    def setUp(self):
        """Set up test fixtures."""
        self.organization_id = str(uuid.uuid4())
        self.user_id = str(uuid.uuid4())

        # Create sample questions
        for i in range(10):
            Question.objects.create(
                organization_id=self.organization_id,
                category='meteorology',
                question_type=QuestionType.MULTIPLE_CHOICE,
                question_text=f'Question {i+1}?',
                options=[
                    {'id': 'a', 'text': 'A'},
                    {'id': 'b', 'text': 'B'},
                ],
                correct_answer={'option_id': 'a'},
                difficulty=Difficulty.MEDIUM,
            )

    def test_get_practice_questions(self):
        """Test getting practice questions."""
        questions = PracticeService.get_practice_questions(
            organization_id=self.organization_id,
            user_id=self.user_id,
            category='meteorology',
            count=5,
        )

        self.assertEqual(len(questions), 5)

    def test_submit_practice_answer(self):
        """Test submitting a practice answer."""
        question = Question.objects.filter(
            organization_id=self.organization_id
        ).first()

        result = PracticeService.submit_practice_answer(
            organization_id=self.organization_id,
            user_id=self.user_id,
            question_id=str(question.id),
            answer='a',
        )

        self.assertTrue(result['correct'])

    def test_get_flashcards(self):
        """Test getting flashcards for a category."""
        flashcards = PracticeService.get_flashcards(
            organization_id=self.organization_id,
            user_id=self.user_id,
            category='meteorology',
            count=5,
        )

        self.assertEqual(len(flashcards), 5)

    def test_start_quick_quiz(self):
        """Test starting a quick quiz."""
        quiz = PracticeService.start_quick_quiz(
            organization_id=self.organization_id,
            user_id=self.user_id,
            category='meteorology',
            question_count=5,
        )

        self.assertEqual(len(quiz['questions']), 5)
        self.assertIn('quiz_id', quiz)

    def test_get_practice_statistics(self):
        """Test getting practice statistics."""
        stats = PracticeService.get_practice_statistics(
            organization_id=self.organization_id,
            user_id=self.user_id,
        )

        self.assertIn('total_practiced', stats)
        self.assertIn('correct_rate', stats)
