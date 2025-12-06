# services/certificate-service/src/apps/core/models/__init__.py
"""
Certificate Service Models

Database models for certificate, license, and rating management.
Includes language proficiency, flight reviews, FTL compliance.
"""

from .certificate import (
    Certificate,
    CertificateType,
    CertificateSubtype,
    CertificateStatus,
    IssuingAuthority,
)
from .medical import (
    MedicalCertificate,
    MedicalClass,
    MedicalStatus,
    MedicalLimitation,
)
from .rating import (
    Rating,
    RatingType,
    RatingStatus,
)
from .endorsement import (
    Endorsement,
    EndorsementType,
    EndorsementStatus,
)
from .currency import (
    CurrencyRequirement,
    UserCurrencyStatus,
    CurrencyType,
    CurrencyStatus,
)
from .verification import (
    CertificateVerification,
    VerificationMethod,
    VerificationStatus,
)
from .language_proficiency import (
    LanguageProficiency,
    LanguageTestHistory,
    LanguageCode,
    ProficiencyLevel,
    LanguageProficiencyStatus,
)
from .flight_review import (
    FlightReview,
    FlightReviewType,
    FlightReviewResult,
    FlightReviewStatus,
    SkillTest,
)
from .flight_time_limitations import (
    FTLConfiguration,
    DutyPeriod,
    DutyType,
    RestPeriod,
    FTLViolation,
    FTLViolationType,
    PilotFTLSummary,
    FTLStandard,
)

__all__ = [
    # Certificate
    'Certificate',
    'CertificateType',
    'CertificateSubtype',
    'CertificateStatus',
    'IssuingAuthority',
    # Medical
    'MedicalCertificate',
    'MedicalClass',
    'MedicalStatus',
    'MedicalLimitation',
    # Rating
    'Rating',
    'RatingType',
    'RatingStatus',
    # Endorsement
    'Endorsement',
    'EndorsementType',
    'EndorsementStatus',
    # Currency
    'CurrencyRequirement',
    'UserCurrencyStatus',
    'CurrencyType',
    'CurrencyStatus',
    # Verification
    'CertificateVerification',
    'VerificationMethod',
    'VerificationStatus',
    # Language Proficiency
    'LanguageProficiency',
    'LanguageTestHistory',
    'LanguageCode',
    'ProficiencyLevel',
    'LanguageProficiencyStatus',
    # Flight Review
    'FlightReview',
    'FlightReviewType',
    'FlightReviewResult',
    'FlightReviewStatus',
    'SkillTest',
    # Flight Time Limitations
    'FTLConfiguration',
    'DutyPeriod',
    'DutyType',
    'RestPeriod',
    'FTLViolation',
    'FTLViolationType',
    'PilotFTLSummary',
    'FTLStandard',
]
