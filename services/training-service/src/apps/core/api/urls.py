# services/training-service/src/apps/core/api/urls.py
"""
Training Service API URLs

URL routing for all training service endpoints.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    TrainingProgramViewSet,
    SyllabusLessonViewSet,
    ExerciseViewSet,
    StudentEnrollmentViewSet,
    LessonCompletionViewSet,
    ExerciseGradeViewSet,
    StageCheckViewSet,
    ProgressViewSet,
)

# Create router
router = DefaultRouter()

# Register viewsets
router.register(r'programs', TrainingProgramViewSet, basename='program')
router.register(r'lessons', SyllabusLessonViewSet, basename='lesson')
router.register(r'exercises', ExerciseViewSet, basename='exercise')
router.register(r'enrollments', StudentEnrollmentViewSet, basename='enrollment')
router.register(r'completions', LessonCompletionViewSet, basename='completion')
router.register(r'grades', ExerciseGradeViewSet, basename='grade')
router.register(r'stage-checks', StageCheckViewSet, basename='stage-check')
router.register(r'progress', ProgressViewSet, basename='progress')

app_name = 'training'

urlpatterns = [
    # Router URLs
    path('', include(router.urls)),
]
