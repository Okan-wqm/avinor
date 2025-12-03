# services/training-service/src/apps/core/api/views/__init__.py
"""
Training Service API Views

ViewSets for REST API endpoints.
"""

from .training_program_views import TrainingProgramViewSet
from .syllabus_views import SyllabusLessonViewSet, ExerciseViewSet
from .enrollment_views import StudentEnrollmentViewSet
from .completion_views import LessonCompletionViewSet, ExerciseGradeViewSet
from .stage_check_views import StageCheckViewSet
from .progress_views import ProgressViewSet

__all__ = [
    'TrainingProgramViewSet',
    'SyllabusLessonViewSet',
    'ExerciseViewSet',
    'StudentEnrollmentViewSet',
    'LessonCompletionViewSet',
    'ExerciseGradeViewSet',
    'StageCheckViewSet',
    'ProgressViewSet',
]
