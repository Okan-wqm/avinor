# services/certificate-service/src/apps/core/api/urls.py
"""
Certificate Service API URLs

URL routing for certificate service API endpoints.
Includes language proficiency, flight reviews, FTL,
and pilot age limit validation.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    CertificateViewSet,
    MedicalCertificateViewSet,
    RatingViewSet,
    EndorsementViewSet,
    CurrencyRequirementViewSet,
    UserCurrencyViewSet,
    ValidityViewSet,
    AgeLimitCheckView,
    PilotValidityCheckView,
    LanguageProficiencyViewSet,
    FlightReviewViewSet,
    SkillTestViewSet,
    FTLConfigurationViewSet,
    DutyPeriodViewSet,
    RestPeriodViewSet,
    FTLViolationViewSet,
    PilotFTLStatusView,
    FTLComplianceCheckView,
    FTLPlanValidationView,
    FTLRestCheckView,
)

# Create router
router = DefaultRouter()

# Register viewsets - Core
router.register(r'certificates', CertificateViewSet, basename='certificate')
router.register(r'medicals', MedicalCertificateViewSet, basename='medical')
router.register(r'ratings', RatingViewSet, basename='rating')
router.register(r'endorsements', EndorsementViewSet, basename='endorsement')
router.register(r'currency/requirements', CurrencyRequirementViewSet, basename='currency-requirement')
router.register(r'currency/status', UserCurrencyViewSet, basename='currency-status')
router.register(r'validity', ValidityViewSet, basename='validity')

# Register viewsets - Language Proficiency
router.register(r'language-proficiency', LanguageProficiencyViewSet, basename='language-proficiency')

# Register viewsets - Flight Review
router.register(r'flight-reviews', FlightReviewViewSet, basename='flight-review')
router.register(r'skill-tests', SkillTestViewSet, basename='skill-test')

# Register viewsets - FTL
router.register(r'ftl/configuration', FTLConfigurationViewSet, basename='ftl-configuration')
router.register(r'ftl/duty-periods', DutyPeriodViewSet, basename='duty-period')
router.register(r'ftl/rest-periods', RestPeriodViewSet, basename='rest-period')
router.register(r'ftl/violations', FTLViolationViewSet, basename='ftl-violation')

app_name = 'core'

urlpatterns = [
    path('', include(router.urls)),
    # FTL API Views (non-ViewSet)
    path('ftl/pilot-status/', PilotFTLStatusView.as_view(), name='ftl-pilot-status'),
    path('ftl/compliance-check/', FTLComplianceCheckView.as_view(), name='ftl-compliance-check'),
    path('ftl/validate-plan/', FTLPlanValidationView.as_view(), name='ftl-validate-plan'),
    path('ftl/rest-check/', FTLRestCheckView.as_view(), name='ftl-rest-check'),
    # Age Limit / Pilot Validity API Views
    path('age-limit-check/', AgeLimitCheckView.as_view(), name='age-limit-check'),
    path('pilot-validity-check/', PilotValidityCheckView.as_view(), name='pilot-validity-check'),
]
