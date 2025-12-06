# services/certificate-service/src/apps/core/api/views/__init__.py
"""
Certificate Service API Views

ViewSets and views for certificate service API.
Includes language proficiency, flight reviews, FTL,
and pilot age limit validation.
"""

from .certificate_views import CertificateViewSet
from .medical_views import MedicalCertificateViewSet
from .rating_views import RatingViewSet
from .endorsement_views import EndorsementViewSet
from .currency_views import CurrencyRequirementViewSet, UserCurrencyViewSet
from .validity_views import (
    ValidityViewSet,
    AgeLimitCheckView,
    PilotValidityCheckView,
)
from .language_proficiency_views import LanguageProficiencyViewSet
from .flight_review_views import FlightReviewViewSet, SkillTestViewSet
from .ftl_views import (
    FTLConfigurationViewSet,
    DutyPeriodViewSet,
    RestPeriodViewSet,
    FTLViolationViewSet,
    PilotFTLStatusView,
    FTLComplianceCheckView,
    FTLPlanValidationView,
    FTLRestCheckView,
)

__all__ = [
    'CertificateViewSet',
    'MedicalCertificateViewSet',
    'RatingViewSet',
    'EndorsementViewSet',
    'CurrencyRequirementViewSet',
    'UserCurrencyViewSet',
    'ValidityViewSet',
    # Age Limit Views
    'AgeLimitCheckView',
    'PilotValidityCheckView',
    # Language Proficiency
    'LanguageProficiencyViewSet',
    # Flight Review
    'FlightReviewViewSet',
    'SkillTestViewSet',
    # FTL
    'FTLConfigurationViewSet',
    'DutyPeriodViewSet',
    'RestPeriodViewSet',
    'FTLViolationViewSet',
    'PilotFTLStatusView',
    'FTLComplianceCheckView',
    'FTLPlanValidationView',
    'FTLRestCheckView',
]
