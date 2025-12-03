# services/theory-service/src/apps/core/api/views/__init__.py
"""
Theory Service API Views

ViewSets for REST API endpoints.
"""

from .course_views import CourseViewSet, CourseModuleViewSet, CourseAttachmentViewSet
from .question_views import QuestionViewSet
from .exam_views import ExamViewSet, ExamAttemptViewSet
from .enrollment_views import EnrollmentViewSet, ModuleProgressViewSet
from .certificate_views import CertificateViewSet
from .practice_views import PracticeViewSet

__all__ = [
    'CourseViewSet',
    'CourseModuleViewSet',
    'CourseAttachmentViewSet',
    'QuestionViewSet',
    'ExamViewSet',
    'ExamAttemptViewSet',
    'EnrollmentViewSet',
    'ModuleProgressViewSet',
    'CertificateViewSet',
    'PracticeViewSet',
]
