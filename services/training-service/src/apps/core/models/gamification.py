# services/training-service/src/apps/core/models/gamification.py
"""
Gamification Models for Flight Training

Comprehensive gamification system to increase student engagement:
- Achievements and badges
- Experience points and levels
- Streaks and challenges
- Leaderboards
- Progress milestones
- Rewards system

Research supports gamification in aviation training for:
- Increased engagement and motivation
- Better knowledge retention
- Healthy competition among peers
- Clear progress visualization
"""

import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal
from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone


class AchievementCategory(models.Model):
    """
    Categories for organizing achievements.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization_id = models.UUIDField(db_index=True)

    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    icon = models.CharField(max_length=50, blank=True, null=True)
    color = models.CharField(
        max_length=7,
        default='#3B82F6',
        help_text="Hex color code"
    )
    display_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'achievement_categories'
        ordering = ['display_order', 'name']
        indexes = [
            models.Index(fields=['organization_id', 'is_active']),
        ]

    def __str__(self):
        return self.name


class Achievement(models.Model):
    """
    Achievement definitions.

    Achievements are earned by completing specific criteria
    related to training progress, flight hours, skills, etc.
    """

    class AchievementType(models.TextChoices):
        ONE_TIME = 'one_time', 'One-Time Achievement'
        PROGRESSIVE = 'progressive', 'Progressive (Multiple Levels)'
        RECURRING = 'recurring', 'Recurring (Can Earn Multiple Times)'

    class Rarity(models.TextChoices):
        COMMON = 'common', 'Common'
        UNCOMMON = 'uncommon', 'Uncommon'
        RARE = 'rare', 'Rare'
        EPIC = 'epic', 'Epic'
        LEGENDARY = 'legendary', 'Legendary'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization_id = models.UUIDField(db_index=True)
    category = models.ForeignKey(
        AchievementCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='achievements'
    )

    # Basic Info
    name = models.CharField(max_length=100)
    description = models.TextField()
    short_description = models.CharField(max_length=255)

    # Display
    icon = models.CharField(max_length=50)
    badge_image_url = models.URLField(max_length=500, blank=True, null=True)
    color = models.CharField(max_length=7, default='#FFD700')

    # Type and Rarity
    achievement_type = models.CharField(
        max_length=20,
        choices=AchievementType.choices,
        default=AchievementType.ONE_TIME
    )
    rarity = models.CharField(
        max_length=20,
        choices=Rarity.choices,
        default=Rarity.COMMON
    )

    # Points
    xp_reward = models.IntegerField(
        default=100,
        help_text="Experience points awarded"
    )

    # Criteria
    criteria_type = models.CharField(
        max_length=50,
        choices=[
            ('flight_hours', 'Total Flight Hours'),
            ('solo_hours', 'Solo Flight Hours'),
            ('pic_hours', 'PIC Hours'),
            ('night_hours', 'Night Hours'),
            ('instrument_hours', 'Instrument Hours'),
            ('cross_country_hours', 'Cross-Country Hours'),
            ('flights_count', 'Number of Flights'),
            ('landings_count', 'Number of Landings'),
            ('night_landings', 'Night Landings'),
            ('lessons_completed', 'Lessons Completed'),
            ('exams_passed', 'Exams Passed'),
            ('exam_score', 'Exam Score'),
            ('stage_check_passed', 'Stage Check Passed'),
            ('certificate_earned', 'Certificate Earned'),
            ('streak_days', 'Consecutive Days'),
            ('airports_visited', 'Unique Airports Visited'),
            ('aircraft_types', 'Aircraft Types Flown'),
            ('perfect_landing', 'Perfect Landing Rating'),
            ('maneuver_mastery', 'Maneuver Mastery'),
            ('first_solo', 'First Solo'),
            ('checkride_passed', 'Checkride Passed'),
            ('custom', 'Custom Criteria'),
        ]
    )
    criteria_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Target value for criteria"
    )
    criteria_comparison = models.CharField(
        max_length=20,
        choices=[
            ('gte', 'Greater than or equal'),
            ('gt', 'Greater than'),
            ('eq', 'Equal to'),
            ('lte', 'Less than or equal'),
        ],
        default='gte'
    )
    criteria_metadata = models.JSONField(
        default=dict,
        help_text="Additional criteria parameters"
    )

    # Progressive Achievement Levels
    levels = models.JSONField(
        default=list,
        help_text="For progressive achievements: [{level: 1, name: 'Bronze', value: 10, xp: 100}, ...]"
    )

    # Visibility
    is_secret = models.BooleanField(
        default=False,
        help_text="Hidden until earned"
    )
    is_active = models.BooleanField(default=True)
    available_from = models.DateField(blank=True, null=True)
    available_until = models.DateField(blank=True, null=True)

    # Statistics
    times_earned = models.IntegerField(default=0)

    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'achievements'
        ordering = ['category', 'rarity', 'name']
        indexes = [
            models.Index(fields=['organization_id', 'is_active']),
            models.Index(fields=['criteria_type']),
            models.Index(fields=['rarity']),
        ]

    def __str__(self):
        return f"{self.name} ({self.rarity})"


class UserAchievement(models.Model):
    """
    User's earned achievements.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization_id = models.UUIDField(db_index=True)
    user_id = models.UUIDField(db_index=True)
    achievement = models.ForeignKey(
        Achievement,
        on_delete=models.CASCADE,
        related_name='user_achievements'
    )

    # Earning Details
    earned_at = models.DateTimeField(default=timezone.now)
    earned_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True, null=True,
        help_text="The value that triggered the achievement"
    )

    # For Progressive Achievements
    current_level = models.IntegerField(default=1)
    current_progress = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0')
    )
    next_level_target = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True, null=True
    )

    # XP Awarded
    xp_awarded = models.IntegerField(default=0)

    # For recurring achievements
    times_earned = models.IntegerField(default=1)
    last_earned_at = models.DateTimeField(blank=True, null=True)

    # Display Preferences
    is_featured = models.BooleanField(
        default=False,
        help_text="Show on profile"
    )
    is_hidden = models.BooleanField(
        default=False,
        help_text="User chose to hide"
    )

    # Notification
    notified = models.BooleanField(default=False)
    notified_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = 'user_achievements'
        ordering = ['-earned_at']
        indexes = [
            models.Index(fields=['organization_id', 'user_id']),
            models.Index(fields=['earned_at']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['user_id', 'achievement'],
                condition=models.Q(times_earned=1),
                name='unique_one_time_achievement'
            )
        ]

    def __str__(self):
        return f"{self.user_id} - {self.achievement.name}"


class ExperienceLevel(models.Model):
    """
    Experience level definitions.

    Defines XP thresholds for each level and associated perks.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization_id = models.UUIDField(db_index=True)

    level = models.IntegerField(
        validators=[MinValueValidator(1)]
    )
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)

    # XP Requirements
    xp_required = models.IntegerField(
        validators=[MinValueValidator(0)]
    )
    xp_to_next = models.IntegerField(
        blank=True, null=True,
        help_text="XP needed for next level"
    )

    # Display
    icon = models.CharField(max_length=50, blank=True, null=True)
    badge_image_url = models.URLField(max_length=500, blank=True, null=True)
    color = models.CharField(max_length=7, default='#3B82F6')

    # Perks
    perks = models.JSONField(
        default=list,
        help_text="Unlocked perks/features at this level"
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'experience_levels'
        ordering = ['level']
        indexes = [
            models.Index(fields=['organization_id', 'level']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['organization_id', 'level'],
                name='unique_org_level'
            )
        ]

    def __str__(self):
        return f"Level {self.level}: {self.name}"


class UserExperience(models.Model):
    """
    User's experience points and level tracking.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization_id = models.UUIDField(db_index=True)
    user_id = models.UUIDField(db_index=True, unique=True)

    # Current Status
    total_xp = models.IntegerField(default=0)
    current_level = models.IntegerField(default=1)
    xp_in_current_level = models.IntegerField(default=0)

    # Level Reference
    level_info = models.ForeignKey(
        ExperienceLevel,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    # History
    xp_earned_today = models.IntegerField(default=0)
    xp_earned_this_week = models.IntegerField(default=0)
    xp_earned_this_month = models.IntegerField(default=0)

    # Tracking
    last_xp_earned_at = models.DateTimeField(blank=True, null=True)
    last_level_up_at = models.DateTimeField(blank=True, null=True)

    # Statistics
    achievements_count = models.IntegerField(default=0)
    badges_count = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'user_experience'
        indexes = [
            models.Index(fields=['organization_id', 'total_xp']),
            models.Index(fields=['current_level']),
        ]

    def __str__(self):
        return f"{self.user_id}: Level {self.current_level} ({self.total_xp} XP)"


class ExperienceTransaction(models.Model):
    """
    XP earning transaction log.
    """

    class TransactionType(models.TextChoices):
        FLIGHT = 'flight', 'Flight Completed'
        LESSON = 'lesson', 'Lesson Completed'
        EXAM = 'exam', 'Exam Passed'
        ACHIEVEMENT = 'achievement', 'Achievement Earned'
        STREAK = 'streak', 'Streak Bonus'
        CHALLENGE = 'challenge', 'Challenge Completed'
        BONUS = 'bonus', 'Bonus Award'
        CORRECTION = 'correction', 'Correction/Adjustment'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization_id = models.UUIDField(db_index=True)
    user_id = models.UUIDField(db_index=True)

    transaction_type = models.CharField(
        max_length=20,
        choices=TransactionType.choices
    )
    xp_amount = models.IntegerField()
    description = models.CharField(max_length=255)

    # Source Reference
    source_id = models.UUIDField(
        blank=True, null=True,
        help_text="ID of flight/lesson/achievement that earned XP"
    )
    source_type = models.CharField(max_length=50, blank=True, null=True)

    # Running Total
    balance_after = models.IntegerField()
    level_after = models.IntegerField()

    # Multipliers Applied
    multiplier = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=Decimal('1.00')
    )
    multiplier_reason = models.CharField(max_length=100, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'experience_transactions'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organization_id', 'user_id']),
            models.Index(fields=['created_at']),
            models.Index(fields=['transaction_type']),
        ]

    def __str__(self):
        return f"{self.user_id}: +{self.xp_amount} XP ({self.transaction_type})"


class Streak(models.Model):
    """
    User activity streak tracking.

    Tracks consecutive days of activity to encourage
    regular engagement with training.
    """

    class StreakType(models.TextChoices):
        DAILY_LOGIN = 'daily_login', 'Daily Login'
        DAILY_FLIGHT = 'daily_flight', 'Daily Flight'
        DAILY_STUDY = 'daily_study', 'Daily Study'
        WEEKLY_FLIGHT = 'weekly_flight', 'Weekly Flight'
        LESSON_PROGRESS = 'lesson_progress', 'Lesson Progress'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization_id = models.UUIDField(db_index=True)
    user_id = models.UUIDField(db_index=True)

    streak_type = models.CharField(
        max_length=20,
        choices=StreakType.choices
    )

    # Current Streak
    current_count = models.IntegerField(default=0)
    current_start_date = models.DateField(blank=True, null=True)
    last_activity_date = models.DateField(blank=True, null=True)

    # Best Streak
    longest_count = models.IntegerField(default=0)
    longest_start_date = models.DateField(blank=True, null=True)
    longest_end_date = models.DateField(blank=True, null=True)

    # Streak Milestones
    milestones_achieved = ArrayField(
        models.IntegerField(),
        default=list,
        help_text="Milestone days achieved (7, 30, 100, etc.)"
    )

    # XP Configuration
    base_xp_per_day = models.IntegerField(default=10)
    bonus_xp_multiplier = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=Decimal('1.10'),
        help_text="Multiplier applied each day"
    )
    max_multiplier = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=Decimal('2.00')
    )

    # Freeze Protection
    freeze_available = models.IntegerField(
        default=0,
        help_text="Streak freeze days available"
    )
    freezes_used = models.IntegerField(default=0)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'streaks'
        indexes = [
            models.Index(fields=['organization_id', 'user_id']),
            models.Index(fields=['streak_type']),
            models.Index(fields=['current_count']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['user_id', 'streak_type'],
                name='unique_user_streak_type'
            )
        ]

    def __str__(self):
        return f"{self.user_id}: {self.streak_type} - {self.current_count} days"

    @property
    def is_streak_active(self) -> bool:
        """Check if streak is still active (not broken)."""
        if not self.last_activity_date:
            return False
        today = date.today()
        days_since = (today - self.last_activity_date).days
        return days_since <= 1  # Allow for today or yesterday


class Challenge(models.Model):
    """
    Training challenges/competitions.

    Time-limited challenges to encourage specific activities
    or foster healthy competition.
    """

    class ChallengeType(models.TextChoices):
        INDIVIDUAL = 'individual', 'Individual Challenge'
        TEAM = 'team', 'Team Challenge'
        GLOBAL = 'global', 'Organization-Wide'

    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        SCHEDULED = 'scheduled', 'Scheduled'
        ACTIVE = 'active', 'Active'
        ENDED = 'ended', 'Ended'
        CANCELLED = 'cancelled', 'Cancelled'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization_id = models.UUIDField(db_index=True)

    # Basic Info
    name = models.CharField(max_length=100)
    description = models.TextField()
    short_description = models.CharField(max_length=255)

    # Display
    icon = models.CharField(max_length=50)
    banner_image_url = models.URLField(max_length=500, blank=True, null=True)
    color = models.CharField(max_length=7, default='#10B981')

    # Type
    challenge_type = models.CharField(
        max_length=20,
        choices=ChallengeType.choices,
        default=ChallengeType.INDIVIDUAL
    )

    # Duration
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()

    # Goals
    goal_type = models.CharField(
        max_length=50,
        choices=[
            ('flight_hours', 'Flight Hours'),
            ('flights_count', 'Number of Flights'),
            ('landings_count', 'Landings'),
            ('lessons_completed', 'Lessons Completed'),
            ('exams_passed', 'Exams Passed'),
            ('study_hours', 'Study Hours'),
            ('xp_earned', 'XP Earned'),
            ('achievements_earned', 'Achievements Earned'),
            ('airports_visited', 'Airports Visited'),
            ('custom', 'Custom'),
        ]
    )
    goal_target = models.DecimalField(max_digits=10, decimal_places=2)
    goal_metadata = models.JSONField(default=dict)

    # Rewards
    xp_reward = models.IntegerField(default=500)
    badge_reward = models.ForeignKey(
        Achievement,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Achievement/badge awarded for completion"
    )
    additional_rewards = models.JSONField(
        default=list,
        help_text="Other rewards (discounts, prizes, etc.)"
    )

    # Participation
    min_participants = models.IntegerField(default=1)
    max_participants = models.IntegerField(blank=True, null=True)
    auto_enroll = models.BooleanField(
        default=False,
        help_text="Auto-enroll all eligible users"
    )
    eligible_roles = ArrayField(
        models.CharField(max_length=50),
        default=list,
        help_text="Roles eligible to participate"
    )

    # Status
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT
    )

    # Stats
    participants_count = models.IntegerField(default=0)
    completions_count = models.IntegerField(default=0)

    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.UUIDField(blank=True, null=True)

    class Meta:
        db_table = 'challenges'
        ordering = ['-start_date']
        indexes = [
            models.Index(fields=['organization_id', 'status']),
            models.Index(fields=['start_date', 'end_date']),
        ]

    def __str__(self):
        return f"{self.name} ({self.status})"

    @property
    def is_active(self) -> bool:
        now = timezone.now()
        return self.start_date <= now <= self.end_date and self.status == self.Status.ACTIVE


class ChallengeParticipant(models.Model):
    """
    Challenge participation tracking.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization_id = models.UUIDField(db_index=True)
    challenge = models.ForeignKey(
        Challenge,
        on_delete=models.CASCADE,
        related_name='participants'
    )
    user_id = models.UUIDField(db_index=True)

    # Progress
    current_progress = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0')
    )
    progress_percentage = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )

    # Status
    enrolled_at = models.DateTimeField(default=timezone.now)
    completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(blank=True, null=True)

    # Rewards
    rewards_claimed = models.BooleanField(default=False)
    rewards_claimed_at = models.DateTimeField(blank=True, null=True)
    xp_earned = models.IntegerField(default=0)

    # Ranking
    rank = models.IntegerField(blank=True, null=True)

    class Meta:
        db_table = 'challenge_participants'
        ordering = ['-current_progress']
        indexes = [
            models.Index(fields=['challenge', 'user_id']),
            models.Index(fields=['current_progress']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['challenge', 'user_id'],
                name='unique_challenge_participant'
            )
        ]

    def __str__(self):
        return f"{self.user_id} in {self.challenge.name}"


class Leaderboard(models.Model):
    """
    Leaderboard definitions.

    Various leaderboards to track and display top performers.
    """

    class LeaderboardType(models.TextChoices):
        ALL_TIME = 'all_time', 'All Time'
        MONTHLY = 'monthly', 'Monthly'
        WEEKLY = 'weekly', 'Weekly'
        DAILY = 'daily', 'Daily'

    class MetricType(models.TextChoices):
        XP = 'xp', 'Experience Points'
        FLIGHT_HOURS = 'flight_hours', 'Flight Hours'
        ACHIEVEMENTS = 'achievements', 'Achievements Earned'
        STREAK = 'streak', 'Longest Streak'
        EXAMS = 'exams', 'Exams Passed'
        LESSONS = 'lessons', 'Lessons Completed'
        LANDINGS = 'landings', 'Total Landings'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization_id = models.UUIDField(db_index=True)

    # Basic Info
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)

    # Type
    leaderboard_type = models.CharField(
        max_length=20,
        choices=LeaderboardType.choices,
        default=LeaderboardType.ALL_TIME
    )
    metric_type = models.CharField(
        max_length=30,
        choices=MetricType.choices
    )

    # Display
    icon = models.CharField(max_length=50, blank=True, null=True)
    show_top_n = models.IntegerField(default=10)

    # Filtering
    eligible_roles = ArrayField(
        models.CharField(max_length=50),
        default=list,
        help_text="Empty means all roles"
    )
    min_activity_threshold = models.IntegerField(
        default=0,
        help_text="Minimum activity to appear on leaderboard"
    )

    # Privacy
    show_real_names = models.BooleanField(default=True)
    show_full_standings = models.BooleanField(
        default=True,
        help_text="Show all standings or just top N"
    )

    is_active = models.BooleanField(default=True)

    # Reset Tracking
    last_reset_at = models.DateTimeField(blank=True, null=True)
    next_reset_at = models.DateTimeField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'leaderboards'
        ordering = ['name']
        indexes = [
            models.Index(fields=['organization_id', 'is_active']),
            models.Index(fields=['leaderboard_type']),
        ]

    def __str__(self):
        return f"{self.name} ({self.leaderboard_type})"


class LeaderboardEntry(models.Model):
    """
    Cached leaderboard entries for performance.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    leaderboard = models.ForeignKey(
        Leaderboard,
        on_delete=models.CASCADE,
        related_name='entries'
    )
    user_id = models.UUIDField(db_index=True)

    # Score
    score = models.DecimalField(max_digits=15, decimal_places=2)
    previous_score = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        blank=True,
        null=True
    )

    # Rank
    rank = models.IntegerField()
    previous_rank = models.IntegerField(blank=True, null=True)
    rank_change = models.IntegerField(
        default=0,
        help_text="Positive = moved up"
    )

    # Period (for periodic leaderboards)
    period_start = models.DateField(blank=True, null=True)
    period_end = models.DateField(blank=True, null=True)

    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'leaderboard_entries'
        ordering = ['rank']
        indexes = [
            models.Index(fields=['leaderboard', 'rank']),
            models.Index(fields=['user_id']),
            models.Index(fields=['score']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['leaderboard', 'user_id', 'period_start'],
                name='unique_leaderboard_entry'
            )
        ]

    def __str__(self):
        return f"#{self.rank}: {self.user_id} ({self.score})"


class ProgressMilestone(models.Model):
    """
    Training progress milestones.

    Key milestones in a pilot's training journey.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization_id = models.UUIDField(db_index=True)

    # Milestone Definition
    name = models.CharField(max_length=100)
    description = models.TextField()
    icon = models.CharField(max_length=50)
    color = models.CharField(max_length=7, default='#8B5CF6')

    # Criteria
    criteria_type = models.CharField(
        max_length=50,
        choices=[
            ('enrollment', 'Training Enrollment'),
            ('first_flight', 'First Flight'),
            ('first_solo', 'First Solo'),
            ('solo_cross_country', 'Solo Cross-Country'),
            ('stage_check', 'Stage Check Passed'),
            ('written_exam', 'Written Exam Passed'),
            ('checkride', 'Checkride Passed'),
            ('certificate', 'Certificate Issued'),
            ('rating_added', 'Rating Added'),
            ('flight_hours', 'Flight Hours Milestone'),
            ('custom', 'Custom Milestone'),
        ]
    )
    criteria_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True, null=True
    )
    criteria_metadata = models.JSONField(default=dict)

    # Training Program
    training_program_id = models.UUIDField(
        blank=True, null=True,
        help_text="If specific to a training program"
    )

    # Display Order
    display_order = models.IntegerField(default=0)

    # Rewards
    xp_reward = models.IntegerField(default=250)
    achievement = models.ForeignKey(
        Achievement,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    # Celebration
    celebration_message = models.TextField(
        blank=True, null=True,
        help_text="Custom message when milestone reached"
    )
    notification_enabled = models.BooleanField(default=True)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'progress_milestones'
        ordering = ['display_order', 'name']
        indexes = [
            models.Index(fields=['organization_id', 'is_active']),
            models.Index(fields=['criteria_type']),
        ]

    def __str__(self):
        return self.name


class UserMilestone(models.Model):
    """
    User's achieved milestones.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization_id = models.UUIDField(db_index=True)
    user_id = models.UUIDField(db_index=True)
    milestone = models.ForeignKey(
        ProgressMilestone,
        on_delete=models.CASCADE,
        related_name='user_milestones'
    )

    # Achievement Details
    achieved_at = models.DateTimeField(default=timezone.now)
    achieved_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True, null=True
    )

    # Context
    flight_id = models.UUIDField(blank=True, null=True)
    instructor_id = models.UUIDField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

    # Celebration
    celebrated = models.BooleanField(default=False)
    celebrated_at = models.DateTimeField(blank=True, null=True)

    # Sharing
    shared_to_feed = models.BooleanField(default=False)
    shared_externally = models.BooleanField(default=False)

    # XP
    xp_awarded = models.IntegerField(default=0)

    class Meta:
        db_table = 'user_milestones'
        ordering = ['-achieved_at']
        indexes = [
            models.Index(fields=['organization_id', 'user_id']),
            models.Index(fields=['achieved_at']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['user_id', 'milestone'],
                name='unique_user_milestone'
            )
        ]

    def __str__(self):
        return f"{self.user_id}: {self.milestone.name}"


class GamificationSettings(models.Model):
    """
    Organization-level gamification configuration.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization_id = models.UUIDField(db_index=True, unique=True)

    # Feature Toggles
    enabled = models.BooleanField(default=True)
    achievements_enabled = models.BooleanField(default=True)
    xp_enabled = models.BooleanField(default=True)
    levels_enabled = models.BooleanField(default=True)
    streaks_enabled = models.BooleanField(default=True)
    challenges_enabled = models.BooleanField(default=True)
    leaderboards_enabled = models.BooleanField(default=True)
    milestones_enabled = models.BooleanField(default=True)

    # Privacy Settings
    public_leaderboards = models.BooleanField(default=True)
    show_other_profiles = models.BooleanField(default=True)
    opt_out_allowed = models.BooleanField(
        default=True,
        help_text="Allow users to opt out of gamification"
    )

    # XP Configuration
    xp_per_flight_hour = models.IntegerField(default=100)
    xp_per_lesson = models.IntegerField(default=50)
    xp_per_exam = models.IntegerField(default=200)
    xp_per_solo_flight = models.IntegerField(default=300)
    daily_xp_cap = models.IntegerField(
        default=0,
        help_text="0 = no cap"
    )

    # Streak Configuration
    streak_grace_period_hours = models.IntegerField(
        default=24,
        help_text="Hours after midnight to still count as previous day"
    )
    streak_freeze_max = models.IntegerField(
        default=2,
        help_text="Maximum streak freezes available"
    )
    streak_freeze_recharge_days = models.IntegerField(
        default=7,
        help_text="Days to earn a new streak freeze"
    )

    # Notification Settings
    achievement_notifications = models.BooleanField(default=True)
    level_up_notifications = models.BooleanField(default=True)
    milestone_notifications = models.BooleanField(default=True)
    leaderboard_notifications = models.BooleanField(default=False)

    # Display Settings
    show_xp_in_profile = models.BooleanField(default=True)
    show_level_in_profile = models.BooleanField(default=True)
    show_achievements_in_profile = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'gamification_settings'

    def __str__(self):
        return f"Gamification Settings: {self.organization_id}"


class UserGamificationProfile(models.Model):
    """
    User's gamification preferences and opt-out status.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization_id = models.UUIDField(db_index=True)
    user_id = models.UUIDField(db_index=True, unique=True)

    # Opt-out
    opted_out = models.BooleanField(default=False)
    opted_out_at = models.DateTimeField(blank=True, null=True)

    # Privacy Preferences
    show_on_leaderboards = models.BooleanField(default=True)
    show_profile_publicly = models.BooleanField(default=True)
    show_achievements_publicly = models.BooleanField(default=True)

    # Notification Preferences
    receive_achievement_notifications = models.BooleanField(default=True)
    receive_level_up_notifications = models.BooleanField(default=True)
    receive_challenge_notifications = models.BooleanField(default=True)
    receive_streak_reminders = models.BooleanField(default=True)

    # Display Preferences
    featured_achievements = ArrayField(
        models.UUIDField(),
        default=list,
        help_text="Achievement IDs to feature on profile"
    )
    profile_badge = models.ForeignKey(
        Achievement,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Badge to show next to name"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'user_gamification_profiles'
        indexes = [
            models.Index(fields=['organization_id', 'user_id']),
        ]

    def __str__(self):
        return f"Gamification Profile: {self.user_id}"
