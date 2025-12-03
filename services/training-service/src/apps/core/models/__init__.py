# services/training-service/src/apps/core/models/__init__.py
"""
Training Service Models

Database models for training management.
"""

from .training_program import TrainingProgram, ProgramStage
from .syllabus import SyllabusLesson, Exercise
from .enrollment import StudentEnrollment
from .completion import LessonCompletion, ExerciseGrade
from .stage_check import StageCheck

__all__ = [
    'TrainingProgram',
    'ProgramStage',
    'SyllabusLesson',
    'Exercise',
    'StudentEnrollment',
    'LessonCompletion',
    'ExerciseGrade',
    'StageCheck',
]
