from django.urls import path, include
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
# ViewSets will be registered here when created
# router.register(r'licenses', LicenseViewSet, basename='license')
# router.register(r'ratings', RatingViewSet, basename='rating')
# router.register(r'medical-certificates', MedicalCertificateViewSet, basename='medical-certificate')
# router.register(r'type-ratings', TypeRatingViewSet, basename='type-rating')
# router.register(r'endorsements', EndorsementViewSet, basename='endorsement')

urlpatterns = [
    path('', include(router.urls)),
]
