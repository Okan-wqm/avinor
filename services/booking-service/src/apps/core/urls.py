from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import BookingViewSet, ScheduleViewSet, WaitlistViewSet

router = DefaultRouter()
router.register(r'bookings', BookingViewSet, basename='booking')
router.register(r'schedules', ScheduleViewSet, basename='schedule')
router.register(r'waitlist', WaitlistViewSet, basename='waitlist')

urlpatterns = [path('', include(router.urls))]
