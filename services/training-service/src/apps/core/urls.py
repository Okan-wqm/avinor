from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    TrainingProgramViewSet, SyllabusViewSet, StageViewSet, LessonViewSet,
    StudentEnrollmentViewSet, LessonCompletionViewSet, StageCheckViewSet
)

router = DefaultRouter()
router.register(r'programs', TrainingProgramViewSet, basename='program')
router.register(r'syllabi', SyllabusViewSet, basename='syllabus')
router.register(r'stages', StageViewSet, basename='stage')
router.register(r'lessons', LessonViewSet, basename='lesson')
router.register(r'enrollments', StudentEnrollmentViewSet, basename='enrollment')
router.register(r'completions', LessonCompletionViewSet, basename='completion')
router.register(r'stage-checks', StageCheckViewSet, basename='stage-check')

urlpatterns = [path('', include(router.urls))]
