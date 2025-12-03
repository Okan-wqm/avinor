# services/theory-service/src/apps/core/tests/test_api.py
"""
API Tests

Integration tests for theory service API endpoints.
"""

import uuid
import json
from decimal import Decimal
from datetime import date

from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status

from ..models import (
    Course,
    CourseModule,
    CourseAttachment,
    Question,
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


class BaseAPITestCase(APITestCase):
    """Base test case with common setup."""

    def setUp(self):
        """Set up test fixtures."""
        self.client = APIClient()
        self.organization_id = str(uuid.uuid4())
        self.user_id = str(uuid.uuid4())

        # Set organization header
        self.client.credentials(
            HTTP_X_ORGANIZATION_ID=self.organization_id,
            HTTP_X_USER_ID=self.user_id,
        )


class CourseAPITest(BaseAPITestCase):
    """Tests for Course API endpoints."""

    def test_list_courses(self):
        """Test listing courses."""
        Course.objects.create(
            organization_id=self.organization_id,
            code='MET-101',
            name='Meteorology',
            category='meteorology',
        )

        url = reverse('course-list')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_create_course(self):
        """Test creating a course."""
        url = reverse('course-list')
        data = {
            'code': 'MET-101',
            'name': 'Meteorology Fundamentals',
            'category': 'meteorology',
            'program_type': 'ppl',
            'description': 'Introduction to aviation meteorology',
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['code'], 'MET-101')
        self.assertEqual(response.data['status'], CourseStatus.DRAFT)

    def test_retrieve_course(self):
        """Test retrieving a single course."""
        course = Course.objects.create(
            organization_id=self.organization_id,
            code='MET-101',
            name='Meteorology',
            category='meteorology',
        )

        url = reverse('course-detail', kwargs={'pk': course.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['code'], 'MET-101')

    def test_update_course(self):
        """Test updating a course."""
        course = Course.objects.create(
            organization_id=self.organization_id,
            code='MET-101',
            name='Meteorology',
            category='meteorology',
        )

        url = reverse('course-detail', kwargs={'pk': course.id})
        data = {'name': 'Updated Meteorology'}

        response = self.client.patch(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Updated Meteorology')

    def test_delete_course(self):
        """Test deleting a course."""
        course = Course.objects.create(
            organization_id=self.organization_id,
            code='MET-101',
            name='Meteorology',
            category='meteorology',
        )

        url = reverse('course-detail', kwargs={'pk': course.id})
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Course.objects.filter(id=course.id).exists())

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

        url = reverse('course-publish', kwargs={'pk': course.id})
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['is_published'])

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

        url = reverse('course-clone', kwargs={'pk': course.id})
        data = {'new_code': 'MET-102'}

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['code'], 'MET-102')

    def test_course_statistics(self):
        """Test getting course statistics."""
        course = Course.objects.create(
            organization_id=self.organization_id,
            code='MET-101',
            name='Meteorology',
            category='meteorology',
        )

        url = reverse('course-statistics', kwargs={'pk': course.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('total_enrollments', response.data)


class CourseModuleAPITest(BaseAPITestCase):
    """Tests for CourseModule API endpoints."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.course = Course.objects.create(
            organization_id=self.organization_id,
            code='MET-101',
            name='Meteorology',
            category='meteorology',
        )

    def test_list_modules(self):
        """Test listing modules for a course."""
        CourseModule.objects.create(
            course=self.course,
            name='Introduction',
            content_type='text',
        )

        url = reverse('course-module-list', kwargs={'course_pk': self.course.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_create_module(self):
        """Test creating a module."""
        url = reverse('course-module-list', kwargs={'course_pk': self.course.id})
        data = {
            'name': 'Introduction to Weather',
            'content_type': 'mixed',
            'estimated_minutes': 30,
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'Introduction to Weather')


class QuestionAPITest(BaseAPITestCase):
    """Tests for Question API endpoints."""

    def test_list_questions(self):
        """Test listing questions."""
        Question.objects.create(
            organization_id=self.organization_id,
            category='meteorology',
            question_type=QuestionType.MULTIPLE_CHOICE,
            question_text='What is METAR?',
            options=[
                {'id': 'a', 'text': 'Weather report'},
                {'id': 'b', 'text': 'Flight plan'},
            ],
            correct_answer={'option_id': 'a'},
        )

        url = reverse('question-list')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_create_question(self):
        """Test creating a question."""
        url = reverse('question-list')
        data = {
            'category': 'meteorology',
            'question_type': QuestionType.MULTIPLE_CHOICE,
            'question_text': 'What is the METAR code for rain?',
            'options': [
                {'id': 'a', 'text': 'RA'},
                {'id': 'b', 'text': 'SN'},
                {'id': 'c', 'text': 'FG'},
            ],
            'correct_answer': {'option_id': 'a'},
            'explanation': 'RA is the METAR code for rain.',
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['category'], 'meteorology')

    def test_flag_question(self):
        """Test flagging a question."""
        question = Question.objects.create(
            organization_id=self.organization_id,
            category='meteorology',
            question_type=QuestionType.MULTIPLE_CHOICE,
            question_text='Test?',
            options=[{'id': 'a', 'text': 'A'}],
            correct_answer={'option_id': 'a'},
        )

        url = reverse('question-flag', kwargs={'pk': question.id})
        data = {'reason': 'Incorrect answer'}

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_filter_questions_by_category(self):
        """Test filtering questions by category."""
        Question.objects.create(
            organization_id=self.organization_id,
            category='meteorology',
            question_type=QuestionType.MULTIPLE_CHOICE,
            question_text='Met question?',
            options=[{'id': 'a', 'text': 'A'}],
            correct_answer={'option_id': 'a'},
        )
        Question.objects.create(
            organization_id=self.organization_id,
            category='navigation',
            question_type=QuestionType.MULTIPLE_CHOICE,
            question_text='Nav question?',
            options=[{'id': 'a', 'text': 'A'}],
            correct_answer={'option_id': 'a'},
        )

        url = reverse('question-list')
        response = self.client.get(url, {'category': 'meteorology'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['category'], 'meteorology')


class ExamAPITest(BaseAPITestCase):
    """Tests for Exam API endpoints."""

    def test_list_exams(self):
        """Test listing exams."""
        Exam.objects.create(
            organization_id=self.organization_id,
            name='Final Exam',
            total_questions=50,
            time_limit_minutes=90,
            passing_score=75,
        )

        url = reverse('exam-list')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_create_exam(self):
        """Test creating an exam."""
        url = reverse('exam-list')
        data = {
            'name': 'Meteorology Final',
            'exam_type': ExamType.FINAL,
            'total_questions': 50,
            'time_limit_minutes': 90,
            'passing_score': 75,
            'question_categories': ['meteorology'],
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'Meteorology Final')

    def test_start_exam(self):
        """Test starting an exam."""
        exam = Exam.objects.create(
            organization_id=self.organization_id,
            name='Test Exam',
            total_questions=5,
            time_limit_minutes=30,
            passing_score=75,
            is_published=True,
            question_categories=['meteorology'],
        )

        # Create questions
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

        url = reverse('exam-start', kwargs={'pk': exam.id})
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('attempt_id', response.data)


class ExamAttemptAPITest(BaseAPITestCase):
    """Tests for ExamAttempt API endpoints."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.exam = Exam.objects.create(
            organization_id=self.organization_id,
            name='Test Exam',
            total_questions=5,
            time_limit_minutes=30,
            passing_score=75,
        )
        self.question = Question.objects.create(
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
        self.attempt = ExamAttempt.objects.create(
            organization_id=self.organization_id,
            exam=self.exam,
            user_id=self.user_id,
            questions=[
                {'question_id': str(self.question.id), 'order': 1, 'points': 1}
            ],
            total_points=1,
        )

    def test_retrieve_attempt(self):
        """Test retrieving an attempt."""
        url = reverse('attempt-detail', kwargs={'pk': self.attempt.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], AttemptStatus.IN_PROGRESS)

    def test_save_answer(self):
        """Test saving an answer."""
        url = reverse('attempt-answer', kwargs={'pk': self.attempt.id})
        data = {
            'question_id': str(self.question.id),
            'answer': 'a',
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_submit_attempt(self):
        """Test submitting an attempt."""
        # Save an answer first
        self.attempt.answers = {
            str(self.question.id): {'selected': 'a'}
        }
        self.attempt.save()

        url = reverse('attempt-submit', kwargs={'pk': self.attempt.id})
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('score', response.data)


class EnrollmentAPITest(BaseAPITestCase):
    """Tests for Enrollment API endpoints."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.course = Course.objects.create(
            organization_id=self.organization_id,
            code='MET-101',
            name='Meteorology',
            category='meteorology',
            is_published=True,
            status=CourseStatus.PUBLISHED,
        )

    def test_list_enrollments(self):
        """Test listing enrollments."""
        CourseEnrollment.objects.create(
            organization_id=self.organization_id,
            course=self.course,
            user_id=self.user_id,
        )

        url = reverse('enrollment-list')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_create_enrollment(self):
        """Test creating an enrollment."""
        url = reverse('enrollment-list')
        data = {
            'course_id': str(self.course.id),
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['status'], EnrollmentStatus.ENROLLED)

    def test_start_enrollment(self):
        """Test starting an enrollment."""
        enrollment = CourseEnrollment.objects.create(
            organization_id=self.organization_id,
            course=self.course,
            user_id=self.user_id,
        )

        url = reverse('enrollment-start', kwargs={'pk': enrollment.id})
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], EnrollmentStatus.IN_PROGRESS)

    def test_my_enrollments(self):
        """Test getting current user's enrollments."""
        CourseEnrollment.objects.create(
            organization_id=self.organization_id,
            course=self.course,
            user_id=self.user_id,
        )

        url = reverse('enrollment-my-enrollments')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)


class CertificateAPITest(BaseAPITestCase):
    """Tests for Certificate API endpoints."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
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

    def test_list_certificates(self):
        """Test listing certificates."""
        Certificate.objects.create(
            organization_id=self.organization_id,
            course=self.course,
            enrollment=self.enrollment,
            user_id=self.user_id,
            certificate_number='CERT-12345',
            title='Test Certificate',
            recipient_name='John Doe',
            course_name='Meteorology',
            course_category='meteorology',
            completion_date=date.today(),
            valid_from=date.today(),
            verification_code='ABC123',
        )

        url = reverse('certificate-list')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_generate_certificate(self):
        """Test generating a certificate."""
        url = reverse('certificate-generate')
        data = {
            'enrollment_id': str(self.enrollment.id),
            'recipient_name': 'John Doe',
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['status'], CertificateStatus.GENERATED)

    def test_verify_certificate(self):
        """Test verifying a certificate."""
        certificate = Certificate.objects.create(
            organization_id=self.organization_id,
            course=self.course,
            enrollment=self.enrollment,
            user_id=self.user_id,
            certificate_number='CERT-12345',
            title='Test Certificate',
            recipient_name='John Doe',
            course_name='Meteorology',
            course_category='meteorology',
            completion_date=date.today(),
            valid_from=date.today(),
            verification_code='ABC123',
            status=CertificateStatus.ISSUED,
        )

        url = reverse('certificate-verify')
        response = self.client.get(url, {'code': 'ABC123'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['valid'])

    def test_issue_certificate(self):
        """Test issuing a certificate."""
        certificate = Certificate.objects.create(
            organization_id=self.organization_id,
            course=self.course,
            enrollment=self.enrollment,
            user_id=self.user_id,
            certificate_number='CERT-12345',
            title='Test Certificate',
            recipient_name='John Doe',
            course_name='Meteorology',
            course_category='meteorology',
            completion_date=date.today(),
            valid_from=date.today(),
            verification_code='ABC123',
            status=CertificateStatus.GENERATED,
        )

        url = reverse('certificate-issue', kwargs={'pk': certificate.id})
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], CertificateStatus.ISSUED)


class PracticeAPITest(BaseAPITestCase):
    """Tests for Practice API endpoints."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()

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
        url = reverse('practice-questions')
        response = self.client.get(url, {
            'category': 'meteorology',
            'count': 5,
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['questions']), 5)

    def test_submit_practice_answer(self):
        """Test submitting a practice answer."""
        question = Question.objects.filter(
            organization_id=self.organization_id
        ).first()

        url = reverse('practice-submit-answer')
        data = {
            'question_id': str(question.id),
            'answer': 'a',
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['correct'])

    def test_get_flashcards(self):
        """Test getting flashcards."""
        url = reverse('practice-flashcards')
        response = self.client.get(url, {
            'category': 'meteorology',
            'count': 5,
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['flashcards']), 5)

    def test_start_quick_quiz(self):
        """Test starting a quick quiz."""
        url = reverse('practice-quick-quiz')
        data = {
            'category': 'meteorology',
            'question_count': 5,
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(response.data['questions']), 5)

    def test_get_practice_statistics(self):
        """Test getting practice statistics."""
        url = reverse('practice-statistics')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('total_practiced', response.data)


class OrganizationFilterTest(BaseAPITestCase):
    """Tests for organization-based filtering."""

    def test_courses_filtered_by_organization(self):
        """Test that courses are filtered by organization."""
        other_org_id = str(uuid.uuid4())

        # Create course in current organization
        Course.objects.create(
            organization_id=self.organization_id,
            code='MET-101',
            name='Our Meteorology',
            category='meteorology',
        )

        # Create course in other organization
        Course.objects.create(
            organization_id=other_org_id,
            code='MET-101',
            name='Other Meteorology',
            category='meteorology',
        )

        url = reverse('course-list')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['name'], 'Our Meteorology')

    def test_questions_filtered_by_organization(self):
        """Test that questions are filtered by organization."""
        other_org_id = str(uuid.uuid4())

        Question.objects.create(
            organization_id=self.organization_id,
            category='meteorology',
            question_type=QuestionType.MULTIPLE_CHOICE,
            question_text='Our question?',
            options=[{'id': 'a', 'text': 'A'}],
            correct_answer={'option_id': 'a'},
        )
        Question.objects.create(
            organization_id=other_org_id,
            category='meteorology',
            question_type=QuestionType.MULTIPLE_CHOICE,
            question_text='Other question?',
            options=[{'id': 'a', 'text': 'A'}],
            correct_answer={'option_id': 'a'},
        )

        url = reverse('question-list')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['question_text'], 'Our question?')


class PaginationTest(BaseAPITestCase):
    """Tests for API pagination."""

    def test_course_pagination(self):
        """Test course list pagination."""
        for i in range(25):
            Course.objects.create(
                organization_id=self.organization_id,
                code=f'COURSE-{i:03d}',
                name=f'Course {i}',
                category='meteorology',
            )

        url = reverse('course-list')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('count', response.data)
        self.assertIn('next', response.data)
        self.assertIn('previous', response.data)
        self.assertEqual(response.data['count'], 25)

    def test_question_pagination(self):
        """Test question list pagination."""
        for i in range(25):
            Question.objects.create(
                organization_id=self.organization_id,
                category='meteorology',
                question_type=QuestionType.MULTIPLE_CHOICE,
                question_text=f'Question {i}?',
                options=[{'id': 'a', 'text': 'A'}],
                correct_answer={'option_id': 'a'},
            )

        url = reverse('question-list')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 25)


class ErrorHandlingTest(BaseAPITestCase):
    """Tests for API error handling."""

    def test_course_not_found(self):
        """Test 404 for non-existent course."""
        url = reverse('course-detail', kwargs={'pk': uuid.uuid4()})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_invalid_course_data(self):
        """Test validation error for invalid course data."""
        url = reverse('course-list')
        data = {
            'name': '',  # Empty name should fail
            'category': 'meteorology',
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_duplicate_enrollment(self):
        """Test error for duplicate enrollment."""
        course = Course.objects.create(
            organization_id=self.organization_id,
            code='MET-101',
            name='Meteorology',
            category='meteorology',
            is_published=True,
            status=CourseStatus.PUBLISHED,
        )

        # First enrollment
        CourseEnrollment.objects.create(
            organization_id=self.organization_id,
            course=course,
            user_id=self.user_id,
        )

        # Try to enroll again
        url = reverse('enrollment-list')
        data = {'course_id': str(course.id)}

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_missing_organization_header(self):
        """Test error when organization header is missing."""
        self.client.credentials()  # Clear credentials

        url = reverse('course-list')
        response = self.client.get(url)

        # Should return 400 or 403 depending on implementation
        self.assertIn(response.status_code, [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_403_FORBIDDEN,
        ])
