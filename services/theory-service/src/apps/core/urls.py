from django.urls import path, include
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
# ViewSets will be registered here when created
# router.register(r'courses', CourseViewSet, basename='course')
# router.register(r'lessons', LessonViewSet, basename='lesson')
# router.register(r'quizzes', QuizViewSet, basename='quiz')
# router.register(r'questions', QuestionViewSet, basename='question')
# router.register(r'progress', StudentProgressViewSet, basename='progress')
# router.register(r'attempts', ExamAttemptViewSet, basename='attempt')

urlpatterns = [
    path('', include(router.urls)),
]
