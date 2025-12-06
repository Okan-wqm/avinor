# services/certificate-service/src/apps/core/services/__init__.py
"""
Certificate Service Business Logic

Service layer for certificate management operations.
Includes language proficiency, flight reviews, FTL compliance,
pilot age limit validation per EASA FCL.065 / FAA Part 121,
and currency rules per EASA FCL.060 / FAA 14 CFR 61.57.
"""

from .certificate_service import CertificateService
from .medical_service import MedicalService
from .rating_service import RatingService
from .endorsement_service import EndorsementService
from .currency_service import (
    CurrencyService,
    EASACurrencyRules,
    FAACurrencyRules,
)
from .verification_service import VerificationService
from .validity_service import ValidityService, AgeLimit
from .language_proficiency_service import LanguageProficiencyService
from .flight_review_service import FlightReviewService
from .ftl_service import FTLService
from .rating_revalidation_service import RatingRevalidationService
from .medical_validity_service import (
    MedicalValidityService,
    EASAMedicalRules,
    FAAMedicalRules,
)

__all__ = [
    'CertificateService',
    'MedicalService',
    'RatingService',
    'EndorsementService',
    'CurrencyService',
    'EASACurrencyRules',
    'FAACurrencyRules',
    'VerificationService',
    'ValidityService',
    'AgeLimit',
    'LanguageProficiencyService',
    'FlightReviewService',
    'FTLService',
    'RatingRevalidationService',
    'MedicalValidityService',
    'EASAMedicalRules',
    'FAAMedicalRules',
]
