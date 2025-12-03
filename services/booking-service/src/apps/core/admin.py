from django.contrib import admin
from .models import Booking, BookingResource, Schedule, WaitlistEntry

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ['id', 'booking_type', 'status', 'start_time', 'end_time']
    list_filter = ['status', 'booking_type']

@admin.register(Schedule)
class ScheduleAdmin(admin.ModelAdmin):
    list_display = ['id', 'schedule_type', 'start_time', 'end_time']

@admin.register(WaitlistEntry)
class WaitlistEntryAdmin(admin.ModelAdmin):
    list_display = ['id', 'user_id', 'requested_date', 'status']
