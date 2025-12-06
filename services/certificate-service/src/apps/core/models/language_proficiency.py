# services/certificate-service/src/apps/core/models/language_proficiency.py
"""
Language Proficiency Model

ICAO Language Proficiency requirements for pilots.
Compliant with ICAO Doc 9835 and EASA FCL.055.
"""

import uuid
from datetime import date, timedelta
from typing import Optional, Dict, Any

from django.db import models
from django.utils import timezone


class LanguageCode(models.TextChoices):
    """Language code choices (ICAO languages)."""
    ENGLISH = 'en', 'English'
    FRENCH = 'fr', 'French'
    SPANISH = 'es', 'Spanish'
    RUSSIAN = 'ru', 'Russian'
    CHINESE = 'zh', 'Chinese'
    ARABIC = 'ar', 'Arabic'
    TURKISH = 'tr', 'Turkish'
    GERMAN = 'de', 'German'
    PORTUGUESE = 'pt', 'Portuguese'
    NORWEGIAN = 'no', 'Norwegian'


class ProficiencyLevel(models.IntegerChoices):
    """ICAO Language Proficiency Levels."""
    LEVEL_1 = 1, 'Level 1 - Pre-Elementary'
    LEVEL_2 = 2, 'Level 2 - Elementary'
    LEVEL_3 = 3, 'Level 3 - Pre-Operational'
    LEVEL_4 = 4, 'Level 4 - Operational'
    LEVEL_5 = 5, 'Level 5 - Extended'
    LEVEL_6 = 6, 'Level 6 - Expert'


class LanguageProficiencyStatus(models.TextChoices):
    """Language proficiency status."""
    ACTIVE = 'active', 'Active'
    EXPIRED = 'expired', 'Expired'
    PENDING_TEST = 'pending_test', 'Pending Test'
    SUSPENDED = 'suspended', 'Suspended'


class LanguageProficiency(models.Model):
    """
    Language Proficiency Model.

    Tracks ICAO language proficiency for pilots.
    Required for international operations.

    Validity periods per ICAO/EASA:
    - Level 4: Valid 4 years (EASA: 4 years)
    - Level 5: Valid 6 years (EASA: 6 years)
    - Level 6: Valid indefinitely (lifetime)
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    organization_id = models.UUIDField(db_index=True)
    user_id = models.UUIDField(db_index=True)

    # Language Details
    language = models.CharField(
        max_length=5,
        choices=LanguageCode.choices,
        db_index=True
    )
    proficiency_level = models.IntegerField(
        choices=ProficiencyLevel.choices,
        db_index=True
    )

    # ICAO Skill Levels (each rated 1-6)
    pronunciation_level = models.IntegerField(
        choices=ProficiencyLevel.choices,
        help_text='Pronunciation - assumes dialect intelligible to aeronautical community'
    )
    structure_level = models.IntegerField(
        choices=ProficiencyLevel.choices,
        help_text='Structure - relevant grammatical structures and sentence patterns'
    )
    vocabulary_level = models.IntegerField(
        choices=ProficiencyLevel.choices,
        help_text='Vocabulary - range and accuracy'
    )
    fluency_level = models.IntegerField(
        choices=ProficiencyLevel.choices,
        help_text='Fluency - tempo and natural speech'
    )
    comprehension_level = models.IntegerField(
        choices=ProficiencyLevel.choices,
        help_text='Comprehension - ability to understand'
    )
    interaction_level = models.IntegerField(
        choices=ProficiencyLevel.choices,
        help_text='Interactions - response speed and appropriateness'
    )

    # Test Information
    test_date = models.DateField()
    test_center = models.CharField(max_length=255)
    test_center_code = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text='Approved test center code'
    )
    examiner_name = models.CharField(max_length=255)
    examiner_id = models.UUIDField(
        blank=True,
        null=True,
        help_text='Examiner user ID if in system'
    )
    examiner_number = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text='Examiner license/certificate number'
    )

    # Validity
    issue_date = models.DateField()
    expiry_date = models.DateField(
        blank=True,
        null=True,
        help_text='Null for Level 6 (lifetime validity)'
    )
    status = models.CharField(
        max_length=20,
        choices=LanguageProficiencyStatus.choices,
        default=LanguageProficiencyStatus.ACTIVE,
        db_index=True
    )

    # Certificate Details
    certificate_number = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )
    issuing_authority = models.CharField(
        max_length=100,
        help_text='e.g., EASA, FAA, SHGM'
    )

    # Document
    document_url = models.URLField(max_length=500, blank=True, null=True)
    document_filename = models.CharField(max_length=255, blank=True, null=True)

    # Verification
    verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(blank=True, null=True)
    verified_by = models.UUIDField(blank=True, null=True)

    # Notes
    notes = models.TextField(blank=True, null=True)
    endorsement_text = models.TextField(
        blank=True,
        null=True,
        help_text='Text to be added to license'
    )

    # Metadata
    metadata = models.JSONField(default=dict, blank=True)

    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'language_proficiencies'
        ordering = ['-test_date']
        indexes = [
            models.Index(fields=['organization_id', 'user_id']),
            models.Index(fields=['language', 'proficiency_level']),
            models.Index(fields=['expiry_date']),
            models.Index(fields=['status']),
        ]
        verbose_name = 'Language Proficiency'
        verbose_name_plural = 'Language Proficiencies'

    def __str__(self) -> str:
        return f"{self.get_language_display()} Level {self.proficiency_level}"

    def save(self, *args, **kwargs):
        """Override save to calculate overall level and expiry."""
        # Overall level is the lowest of all component levels
        self.proficiency_level = min(
            self.pronunciation_level,
            self.structure_level,
            self.vocabulary_level,
            self.fluency_level,
            self.comprehension_level,
            self.interaction_level
        )

        # Calculate expiry based on level
        if not self.expiry_date:
            self.expiry_date = self.calculate_expiry_date()

        super().save(*args, **kwargs)

    def calculate_expiry_date(self) -> Optional[date]:
        """
        Calculate expiry date based on ICAO/EASA rules.

        Level 4: 4 years (EASA FCL.055)
        Level 5: 6 years (EASA FCL.055)
        Level 6: No expiry (lifetime)
        """
        if self.proficiency_level == 6:
            return None  # Level 6 never expires
        elif self.proficiency_level == 5:
            return self.issue_date + timedelta(days=6*365)  # 6 years
        elif self.proficiency_level == 4:
            return self.issue_date + timedelta(days=4*365)  # 4 years
        else:
            # Levels 1-3 not operational, require retest
            return self.issue_date + timedelta(days=365)  # 1 year

    @property
    def is_operational(self) -> bool:
        """Check if level meets ICAO minimum (Level 4)."""
        return self.proficiency_level >= 4

    @property
    def is_expired(self) -> bool:
        """Check if proficiency is expired."""
        if not self.expiry_date:
            return False
        return self.expiry_date < date.today()

    @property
    def days_until_expiry(self) -> Optional[int]:
        """Calculate days until expiry."""
        if not self.expiry_date:
            return None
        return (self.expiry_date - date.today()).days

    @property
    def is_expiring_soon(self) -> bool:
        """Check if expiring within 180 days."""
        days = self.days_until_expiry
        if days is None:
            return False
        return 0 < days <= 180

    @property
    def is_valid(self) -> bool:
        """Check if proficiency is valid for operations."""
        return (
            self.status == LanguageProficiencyStatus.ACTIVE and
            self.is_operational and
            not self.is_expired
        )

    @property
    def level_description(self) -> str:
        """Get description for current level."""
        descriptions = {
            1: 'Pre-Elementary - Cannot communicate effectively',
            2: 'Elementary - Limited communication ability',
            3: 'Pre-Operational - Can communicate with some difficulty',
            4: 'Operational - Meets ICAO minimum for international operations',
            5: 'Extended - Proficient in aviation English',
            6: 'Expert - Native or expert level proficiency'
        }
        return descriptions.get(self.proficiency_level, 'Unknown')

    def get_validity_info(self) -> Dict[str, Any]:
        """Get detailed validity information."""
        return {
            'proficiency_id': str(self.id),
            'user_id': str(self.user_id),
            'language': self.language,
            'language_name': self.get_language_display(),
            'overall_level': self.proficiency_level,
            'level_description': self.level_description,
            'component_levels': {
                'pronunciation': self.pronunciation_level,
                'structure': self.structure_level,
                'vocabulary': self.vocabulary_level,
                'fluency': self.fluency_level,
                'comprehension': self.comprehension_level,
                'interaction': self.interaction_level,
            },
            'is_operational': self.is_operational,
            'status': self.status,
            'is_valid': self.is_valid,
            'is_expired': self.is_expired,
            'is_expiring_soon': self.is_expiring_soon,
            'test_date': self.test_date.isoformat(),
            'issue_date': self.issue_date.isoformat(),
            'expiry_date': self.expiry_date.isoformat() if self.expiry_date else None,
            'days_until_expiry': self.days_until_expiry,
            'issuing_authority': self.issuing_authority,
            'test_center': self.test_center,
            'verified': self.verified,
        }

    def update_status(self) -> None:
        """Update status based on current state."""
        if self.status == LanguageProficiencyStatus.SUSPENDED:
            return

        if self.is_expired:
            self.status = LanguageProficiencyStatus.EXPIRED
            self.save(update_fields=['status', 'updated_at'])


class LanguageTestHistory(models.Model):
    """
    Language Test History Model.

    Tracks all language proficiency tests taken by a pilot.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    organization_id = models.UUIDField(db_index=True)
    user_id = models.UUIDField(db_index=True)

    # Test Details
    language = models.CharField(max_length=5, choices=LanguageCode.choices)
    test_date = models.DateField()
    test_center = models.CharField(max_length=255)
    examiner_name = models.CharField(max_length=255)

    # Results
    passed = models.BooleanField()
    overall_level = models.IntegerField(choices=ProficiencyLevel.choices)
    pronunciation_level = models.IntegerField(choices=ProficiencyLevel.choices)
    structure_level = models.IntegerField(choices=ProficiencyLevel.choices)
    vocabulary_level = models.IntegerField(choices=ProficiencyLevel.choices)
    fluency_level = models.IntegerField(choices=ProficiencyLevel.choices)
    comprehension_level = models.IntegerField(choices=ProficiencyLevel.choices)
    interaction_level = models.IntegerField(choices=ProficiencyLevel.choices)

    # Proficiency Record (if passed and recorded)
    proficiency = models.ForeignKey(
        LanguageProficiency,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='test_history'
    )

    # Notes
    examiner_comments = models.TextField(blank=True, null=True)
    areas_for_improvement = models.TextField(blank=True, null=True)

    # Audit
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'language_test_history'
        ordering = ['-test_date']
        indexes = [
            models.Index(fields=['organization_id', 'user_id']),
            models.Index(fields=['test_date']),
        ]

    def __str__(self) -> str:
        status = 'Passed' if self.passed else 'Failed'
        return f"{self.get_language_display()} Test - {status} - Level {self.overall_level}"
