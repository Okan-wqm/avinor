# services/theory-service/src/apps/core/api/urls.py
"""
Theory Service API URLs

URL routing configuration for REST API endpoints.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers

from .views import (
    CourseViewSet,
    CourseModuleViewSet,
    CourseAttachmentViewSet,
    QuestionViewSet,
    ExamViewSet,
    ExamAttemptViewSet,
    EnrollmentViewSet,
    ModuleProgressViewSet,
    CertificateViewSet,
    PracticeViewSet,
)

# Main router
router = DefaultRouter()
router.register(r'courses', CourseViewSet, basename='course')
router.register(r'questions', QuestionViewSet, basename='question')
router.register(r'exams', ExamViewSet, basename='exam')
router.register(r'attempts', ExamAttemptViewSet, basename='attempt')
router.register(r'enrollments', EnrollmentViewSet, basename='enrollment')
router.register(r'certificates', CertificateViewSet, basename='certificate')
router.register(r'practice', PracticeViewSet, basename='practice')

# Nested routers for courses
courses_router = routers.NestedDefaultRouter(router, r'courses', lookup='course')
courses_router.register(r'modules', CourseModuleViewSet, basename='course-module')
courses_router.register(r'attachments', CourseAttachmentViewSet, basename='course-attachment')

# Nested routers for enrollments
enrollments_router = routers.NestedDefaultRouter(router, r'enrollments', lookup='enrollment')
enrollments_router.register(r'progress', ModuleProgressViewSet, basename='enrollment-progress')

urlpatterns = [
    path('', include(router.urls)),
    path('', include(courses_router.urls)),
    path('', include(enrollments_router.urls)),
]

# API URL Patterns Summary:
#
# Courses:
#   GET/POST    /api/v1/theory/courses/
#   GET/PUT/DEL /api/v1/theory/courses/{id}/
#   POST        /api/v1/theory/courses/{id}/publish/
#   POST        /api/v1/theory/courses/{id}/archive/
#   POST        /api/v1/theory/courses/{id}/clone/
#   GET         /api/v1/theory/courses/{id}/statistics/
#   GET         /api/v1/theory/courses/{id}/modules/
#   POST        /api/v1/theory/courses/{id}/modules/reorder/
#
# Course Modules (nested):
#   GET/POST    /api/v1/theory/courses/{id}/modules/
#   GET/PUT/DEL /api/v1/theory/courses/{id}/modules/{module_id}/
#   GET         /api/v1/theory/courses/{id}/modules/{module_id}/content/
#
# Course Attachments (nested):
#   GET/POST    /api/v1/theory/courses/{id}/attachments/
#   GET/DEL     /api/v1/theory/courses/{id}/attachments/{attach_id}/
#   POST        /api/v1/theory/courses/{id}/attachments/{attach_id}/download/
#
# Questions:
#   GET/POST    /api/v1/theory/questions/
#   GET/PUT/DEL /api/v1/theory/questions/{id}/
#   POST        /api/v1/theory/questions/{id}/review/
#   GET         /api/v1/theory/questions/{id}/reviews/
#   POST        /api/v1/theory/questions/{id}/clone/
#   POST        /api/v1/theory/questions/{id}/flag/
#   POST        /api/v1/theory/questions/{id}/unflag/
#   POST        /api/v1/theory/questions/import/
#   POST        /api/v1/theory/questions/import-csv/
#   GET         /api/v1/theory/questions/export/
#   GET         /api/v1/theory/questions/statistics/
#   GET         /api/v1/theory/questions/categories/
#
# Exams:
#   GET/POST    /api/v1/theory/exams/
#   GET/PUT/DEL /api/v1/theory/exams/{id}/
#   POST        /api/v1/theory/exams/{id}/publish/
#   POST        /api/v1/theory/exams/{id}/archive/
#   POST        /api/v1/theory/exams/{id}/random-rules/
#   POST        /api/v1/theory/exams/{id}/fixed-questions/
#   GET         /api/v1/theory/exams/{id}/availability/
#   POST        /api/v1/theory/exams/{id}/start/
#   GET         /api/v1/theory/exams/{id}/statistics/
#
# Exam Attempts:
#   GET         /api/v1/theory/attempts/
#   GET         /api/v1/theory/attempts/{id}/
#   POST        /api/v1/theory/attempts/{id}/answer/
#   POST        /api/v1/theory/attempts/{id}/flag/
#   POST        /api/v1/theory/attempts/{id}/pause/
#   POST        /api/v1/theory/attempts/{id}/resume/
#   POST        /api/v1/theory/attempts/{id}/submit/
#   GET         /api/v1/theory/attempts/{id}/results/
#   GET         /api/v1/theory/attempts/statistics/
#
# Enrollments:
#   GET/POST    /api/v1/theory/enrollments/
#   GET         /api/v1/theory/enrollments/{id}/
#   POST        /api/v1/theory/enrollments/{id}/start/
#   GET         /api/v1/theory/enrollments/{id}/progress/
#   POST        /api/v1/theory/enrollments/{id}/suspend/
#   POST        /api/v1/theory/enrollments/{id}/reactivate/
#   POST        /api/v1/theory/enrollments/{id}/review/
#   GET         /api/v1/theory/enrollments/my-courses/
#
# Module Progress (nested):
#   GET         /api/v1/theory/enrollments/{id}/progress/
#   GET         /api/v1/theory/enrollments/{id}/progress/{module_id}/
#   POST        /api/v1/theory/enrollments/{id}/progress/{module_id}/activity/
#   POST        /api/v1/theory/enrollments/{id}/progress/{module_id}/complete/
#   POST        /api/v1/theory/enrollments/{id}/progress/{module_id}/quiz-result/
#   POST        /api/v1/theory/enrollments/{id}/progress/{module_id}/bookmark/
#   POST        /api/v1/theory/enrollments/{id}/progress/{module_id}/notes/
#
# Certificates:
#   GET         /api/v1/theory/certificates/
#   GET         /api/v1/theory/certificates/{id}/
#   POST        /api/v1/theory/certificates/generate/
#   POST        /api/v1/theory/certificates/{id}/issue/
#   POST        /api/v1/theory/certificates/{id}/revoke/
#   POST        /api/v1/theory/certificates/verify/
#   POST        /api/v1/theory/certificates/{id}/update-document/
#   POST        /api/v1/theory/certificates/{id}/make-public/
#   POST        /api/v1/theory/certificates/{id}/make-private/
#   POST        /api/v1/theory/certificates/{id}/linkedin-share/
#   GET         /api/v1/theory/certificates/{id}/public/
#   POST        /api/v1/theory/certificates/{id}/download/
#   GET         /api/v1/theory/certificates/my-certificates/
#   GET         /api/v1/theory/certificates/expiring/
#
# Practice:
#   GET         /api/v1/theory/practice/questions/
#   POST        /api/v1/theory/practice/check-answer/
#   GET         /api/v1/theory/practice/categories/
#   POST        /api/v1/theory/practice/adaptive/
#   GET         /api/v1/theory/practice/quick-quiz/
#   GET         /api/v1/theory/practice/flashcards/
#   GET         /api/v1/theory/practice/by-topic/
#   GET         /api/v1/theory/practice/by-learning-objective/
