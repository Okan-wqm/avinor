# services/training-service/src/apps/core/api/serializers/__init__.py
"""
Training Service API Serializers

Serializers for REST API data transformation.
"""

from .training_program_serializers import (
    TrainingProgramSerializer,
    TrainingProgramCreateSerializer,
    TrainingProgramUpdateSerializer,
    TrainingProgramListSerializer,
    TrainingProgramDetailSerializer,
    ProgramStageSerializer,
    ProgramRequirementsSerializer,
    ProgramStatisticsSerializer,
)

from .syllabus_serializers import (
    SyllabusLessonSerializer,
    SyllabusLessonCreateSerializer,
    SyllabusLessonUpdateSerializer,
    SyllabusLessonDetailSerializer,
    ExerciseSerializer,
    ExerciseCreateSerializer,
    ProgramSyllabusSerializer,
)

from .enrollment_serializers import (
    StudentEnrollmentSerializer,
    StudentEnrollmentCreateSerializer,
    StudentEnrollmentUpdateSerializer,
    StudentEnrollmentDetailSerializer,
    EnrollmentProgressSerializer,
    EnrollmentHoursSerializer,
)

from .completion_serializers import (
    LessonCompletionSerializer,
    LessonCompletionCreateSerializer,
    LessonCompletionUpdateSerializer,
    LessonCompletionDetailSerializer,
    ExerciseGradeSerializer,
    ExerciseGradeCreateSerializer,
    CompletionStatisticsSerializer,
)

from .stage_check_serializers import (
    StageCheckSerializer,
    StageCheckCreateSerializer,
    StageCheckUpdateSerializer,
    StageCheckDetailSerializer,
    StageCheckResultSerializer,
    OralTopicSerializer,
    FlightManeuverSerializer,
)

__all__ = [
    # Training Program
    'TrainingProgramSerializer',
    'TrainingProgramCreateSerializer',
    'TrainingProgramUpdateSerializer',
    'TrainingProgramListSerializer',
    'TrainingProgramDetailSerializer',
    'ProgramStageSerializer',
    'ProgramRequirementsSerializer',
    'ProgramStatisticsSerializer',

    # Syllabus
    'SyllabusLessonSerializer',
    'SyllabusLessonCreateSerializer',
    'SyllabusLessonUpdateSerializer',
    'SyllabusLessonDetailSerializer',
    'ExerciseSerializer',
    'ExerciseCreateSerializer',
    'ProgramSyllabusSerializer',

    # Enrollment
    'StudentEnrollmentSerializer',
    'StudentEnrollmentCreateSerializer',
    'StudentEnrollmentUpdateSerializer',
    'StudentEnrollmentDetailSerializer',
    'EnrollmentProgressSerializer',
    'EnrollmentHoursSerializer',

    # Completion
    'LessonCompletionSerializer',
    'LessonCompletionCreateSerializer',
    'LessonCompletionUpdateSerializer',
    'LessonCompletionDetailSerializer',
    'ExerciseGradeSerializer',
    'ExerciseGradeCreateSerializer',
    'CompletionStatisticsSerializer',

    # Stage Check
    'StageCheckSerializer',
    'StageCheckCreateSerializer',
    'StageCheckUpdateSerializer',
    'StageCheckDetailSerializer',
    'StageCheckResultSerializer',
    'OralTopicSerializer',
    'FlightManeuverSerializer',
]
