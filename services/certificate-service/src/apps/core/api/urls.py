# services/certificate-service/src/apps/core/api/urls.py
"""
Certificate Service API URLs

URL routing for certificate service API endpoints.
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
)

# Create router
router = DefaultRouter()

# Register viewsets
router.register(r'certificates', CertificateViewSet, basename='certificate')
router.register(r'medicals', MedicalCertificateViewSet, basename='medical')
router.register(r'ratings', RatingViewSet, basename='rating')
router.register(r'endorsements', EndorsementViewSet, basename='endorsement')
router.register(r'currency/requirements', CurrencyRequirementViewSet, basename='currency-requirement')
router.register(r'currency/status', UserCurrencyViewSet, basename='currency-status')
router.register(r'validity', ValidityViewSet, basename='validity')

app_name = 'core'

urlpatterns = [
    path('', include(router.urls)),
]
