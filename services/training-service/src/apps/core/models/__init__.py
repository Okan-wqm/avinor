# services/training-service/src/apps/core/models/__init__.py
"""
Training Service Models

Database models for training management including:
- Training programs and syllabi
- Student enrollment and progress
- Stage checks and grading
- Gamification (achievements, XP, streaks, leaderboards)
"""

from .training_program import TrainingProgram, ProgramStage
from .syllabus import SyllabusLesson, Exercise
from .enrollment import StudentEnrollment
from .completion import LessonCompletion, ExerciseGrade
from .stage_check import StageCheck
from .gamification import (
    AchievementCategory,
    Achievement,
    UserAchievement,
    ExperienceLevel,
    UserExperience,
    ExperienceTransaction,
    Streak,
    Challenge,
    ChallengeParticipant,
    Leaderboard,
    LeaderboardEntry,
    ProgressMilestone,
    UserMilestone,
    GamificationSettings,
    UserGamificationProfile,
)

__all__ = [
    # Training Program Models
    'TrainingProgram',
    'ProgramStage',
    'SyllabusLesson',
    'Exercise',
    'StudentEnrollment',
    'LessonCompletion',
    'ExerciseGrade',
    'StageCheck',

    # Gamification Models
    'AchievementCategory',
    'Achievement',
    'UserAchievement',
    'ExperienceLevel',
    'UserExperience',
    'ExperienceTransaction',
    'Streak',
    'Challenge',
    'ChallengeParticipant',
    'Leaderboard',
    'LeaderboardEntry',
    'ProgressMilestone',
    'UserMilestone',
    'GamificationSettings',
    'UserGamificationProfile',
]
