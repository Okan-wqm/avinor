# services/theory-service/src/apps/core/api/serializers/__init__.py
"""
Theory Service API Serializers

Serializers for REST API endpoints.
"""

from .course_serializers import (
    CourseListSerializer,
    CourseDetailSerializer,
    CourseCreateSerializer,
    CourseUpdateSerializer,
    CourseModuleSerializer,
    CourseModuleCreateSerializer,
    CourseModuleUpdateSerializer,
    CourseAttachmentSerializer,
    ModuleReorderSerializer,
)
from .question_serializers import (
    QuestionListSerializer,
    QuestionDetailSerializer,
    QuestionCreateSerializer,
    QuestionUpdateSerializer,
    QuestionReviewSerializer,
    QuestionBulkImportSerializer,
)
from .exam_serializers import (
    ExamListSerializer,
    ExamDetailSerializer,
    ExamCreateSerializer,
    ExamUpdateSerializer,
    ExamStartSerializer,
    ExamAnswerSerializer,
    ExamAttemptSerializer,
    ExamResultSerializer,
)
from .enrollment_serializers import (
    EnrollmentListSerializer,
    EnrollmentDetailSerializer,
    EnrollmentCreateSerializer,
    ModuleProgressSerializer,
    ModuleActivitySerializer,
    ReviewSerializer,
)
from .certificate_serializers import (
    CertificateListSerializer,
    CertificateDetailSerializer,
    CertificateGenerateSerializer,
    CertificateVerifySerializer,
)

__all__ = [
    # Course
    'CourseListSerializer',
    'CourseDetailSerializer',
    'CourseCreateSerializer',
    'CourseUpdateSerializer',
    'CourseModuleSerializer',
    'CourseModuleCreateSerializer',
    'CourseModuleUpdateSerializer',
    'CourseAttachmentSerializer',
    'ModuleReorderSerializer',
    # Question
    'QuestionListSerializer',
    'QuestionDetailSerializer',
    'QuestionCreateSerializer',
    'QuestionUpdateSerializer',
    'QuestionReviewSerializer',
    'QuestionBulkImportSerializer',
    # Exam
    'ExamListSerializer',
    'ExamDetailSerializer',
    'ExamCreateSerializer',
    'ExamUpdateSerializer',
    'ExamStartSerializer',
    'ExamAnswerSerializer',
    'ExamAttemptSerializer',
    'ExamResultSerializer',
    # Enrollment
    'EnrollmentListSerializer',
    'EnrollmentDetailSerializer',
    'EnrollmentCreateSerializer',
    'ModuleProgressSerializer',
    'ModuleActivitySerializer',
    'ReviewSerializer',
    # Certificate
    'CertificateListSerializer',
    'CertificateDetailSerializer',
    'CertificateGenerateSerializer',
    'CertificateVerifySerializer',
]
