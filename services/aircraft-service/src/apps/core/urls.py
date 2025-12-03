from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    AircraftTypeViewSet, AircraftViewSet, AircraftDocumentViewSet,
    SquawkViewSet, FuelLogViewSet
)

router = DefaultRouter()
router.register(r'types', AircraftTypeViewSet, basename='aircraft-type')
router.register(r'aircraft', AircraftViewSet, basename='aircraft')
router.register(r'documents', AircraftDocumentViewSet, basename='document')
router.register(r'squawks', SquawkViewSet, basename='squawk')
router.register(r'fuel-logs', FuelLogViewSet, basename='fuel-log')

urlpatterns = [
    path('', include(router.urls)),
]
