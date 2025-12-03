# services/certificate-service/src/apps/core/api/serializers/__init__.py
"""
Certificate Service API Serializers

Serializers for certificate service API.
"""

from .certificate_serializers import (
    CertificateSerializer,
    CertificateCreateSerializer,
    CertificateUpdateSerializer,
    CertificateListSerializer,
    CertificateVerifySerializer,
    CertificateSuspendSerializer,
    CertificateRevokeSerializer,
    CertificateRenewSerializer,
    ExpiringCertificateSerializer,
)
from .medical_serializers import (
    MedicalCertificateSerializer,
    MedicalCertificateCreateSerializer,
    MedicalCertificateListSerializer,
    MedicalValidityCheckSerializer,
    MedicalValidityResponseSerializer,
)
from .rating_serializers import (
    RatingSerializer,
    RatingCreateSerializer,
    RatingListSerializer,
    ProficiencyCheckSerializer,
    RatingRenewSerializer,
    TypeRatingCheckSerializer,
    TypeRatingCheckResponseSerializer,
)
from .endorsement_serializers import (
    EndorsementSerializer,
    EndorsementCreateSerializer,
    EndorsementListSerializer,
    EndorsementSignSerializer,
    SoloEndorsementCreateSerializer,
    SoloAuthorizationCheckSerializer,
    SoloAuthorizationResponseSerializer,
)
from .currency_serializers import (
    CurrencyRequirementSerializer,
    CurrencyRequirementCreateSerializer,
    CurrencyRequirementListSerializer,
    UserCurrencyStatusSerializer,
    UserCurrencyStatusListSerializer,
    CurrencyCheckSerializer,
    CurrencyCheckResponseSerializer,
    CurrencyUpdateSerializer,
    CurrencyBatchUpdateSerializer,
    CurrencySummarySerializer,
    FlightCurrencyImpactSerializer,
)
from .validity_serializers import (
    ValidityCheckSerializer,
    ValidityCheckResponseSerializer,
    UserSummarySerializer,
    FlightValidityCheckSerializer,
    FlightValidityResponseSerializer,
    ExpirationAlertSerializer,
    OrganizationComplianceSerializer,
    StudentProgressSerializer,
    InstructorValiditySerializer,
)

__all__ = [
    # Certificate
    'CertificateSerializer',
    'CertificateCreateSerializer',
    'CertificateUpdateSerializer',
    'CertificateListSerializer',
    'CertificateVerifySerializer',
    'CertificateSuspendSerializer',
    'CertificateRevokeSerializer',
    'CertificateRenewSerializer',
    'ExpiringCertificateSerializer',
    # Medical
    'MedicalCertificateSerializer',
    'MedicalCertificateCreateSerializer',
    'MedicalCertificateListSerializer',
    'MedicalValidityCheckSerializer',
    'MedicalValidityResponseSerializer',
    # Rating
    'RatingSerializer',
    'RatingCreateSerializer',
    'RatingListSerializer',
    'ProficiencyCheckSerializer',
    'RatingRenewSerializer',
    'TypeRatingCheckSerializer',
    'TypeRatingCheckResponseSerializer',
    # Endorsement
    'EndorsementSerializer',
    'EndorsementCreateSerializer',
    'EndorsementListSerializer',
    'EndorsementSignSerializer',
    'SoloEndorsementCreateSerializer',
    'SoloAuthorizationCheckSerializer',
    'SoloAuthorizationResponseSerializer',
    # Currency
    'CurrencyRequirementSerializer',
    'CurrencyRequirementCreateSerializer',
    'CurrencyRequirementListSerializer',
    'UserCurrencyStatusSerializer',
    'UserCurrencyStatusListSerializer',
    'CurrencyCheckSerializer',
    'CurrencyCheckResponseSerializer',
    'CurrencyUpdateSerializer',
    'CurrencyBatchUpdateSerializer',
    'CurrencySummarySerializer',
    'FlightCurrencyImpactSerializer',
    # Validity
    'ValidityCheckSerializer',
    'ValidityCheckResponseSerializer',
    'UserSummarySerializer',
    'FlightValidityCheckSerializer',
    'FlightValidityResponseSerializer',
    'ExpirationAlertSerializer',
    'OrganizationComplianceSerializer',
    'StudentProgressSerializer',
    'InstructorValiditySerializer',
]
