# services/theory-service/src/apps/core/models/__init__.py
"""
Theory Service Models

Database models for theory training and examination management.
"""

from .course import Course, CourseModule, CourseAttachment
from .question import Question, QuestionReview
from .exam import Exam, ExamQuestion
from .attempt import ExamAttempt, AttemptAnswer
from .enrollment import CourseEnrollment, ModuleProgress
from .certificate import Certificate

__all__ = [
    # Course
    'Course',
    'CourseModule',
    'CourseAttachment',
    # Question
    'Question',
    'QuestionReview',
    # Exam
    'Exam',
    'ExamQuestion',
    # Attempt
    'ExamAttempt',
    'AttemptAnswer',
    # Enrollment
    'CourseEnrollment',
    'ModuleProgress',
    # Certificate
    'Certificate',
]
