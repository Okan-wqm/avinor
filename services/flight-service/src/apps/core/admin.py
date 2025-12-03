from django.contrib import admin
from .models import Flight, FlightTrack, LogbookEntry, PilotTotals

@admin.register(Flight)
class FlightAdmin(admin.ModelAdmin):
    list_display = ['id', 'flight_type', 'status', 'departure_airport', 'arrival_airport', 'actual_departure']
    list_filter = ['status', 'flight_type']

@admin.register(LogbookEntry)
class LogbookEntryAdmin(admin.ModelAdmin):
    list_display = ['pilot_id', 'date', 'aircraft_registration', 'total_time']

@admin.register(PilotTotals)
class PilotTotalsAdmin(admin.ModelAdmin):
    list_display = ['pilot_id', 'total_time', 'total_flights', 'last_flight_date']
