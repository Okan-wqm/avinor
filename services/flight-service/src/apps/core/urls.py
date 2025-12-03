from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import FlightViewSet, LogbookViewSet

router = DefaultRouter()
router.register(r'flights', FlightViewSet, basename='flight')
router.register(r'logbook', LogbookViewSet, basename='logbook')

urlpatterns = [path('', include(router.urls))]
