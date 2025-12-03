from django.contrib import admin
from .models import AircraftType, Aircraft, AircraftDocument, Squawk, FuelLog


@admin.register(AircraftType)
class AircraftTypeAdmin(admin.ModelAdmin):
    list_display = ['manufacturer', 'model', 'category', 'icao_designator', 'is_active']
    list_filter = ['category', 'is_active', 'requires_type_rating']
    search_fields = ['manufacturer', 'model', 'icao_designator']


@admin.register(Aircraft)
class AircraftAdmin(admin.ModelAdmin):
    list_display = ['registration', 'name', 'aircraft_type', 'status', 'total_time_hours']
    list_filter = ['status', 'aircraft_type']
    search_fields = ['registration', 'name', 'serial_number']


@admin.register(AircraftDocument)
class AircraftDocumentAdmin(admin.ModelAdmin):
    list_display = ['aircraft', 'title', 'document_type', 'expiry_date', 'is_current']
    list_filter = ['document_type', 'is_current']


@admin.register(Squawk)
class SquawkAdmin(admin.ModelAdmin):
    list_display = ['aircraft', 'title', 'severity', 'status', 'discovered_at']
    list_filter = ['severity', 'status']
    search_fields = ['title', 'description']


@admin.register(FuelLog)
class FuelLogAdmin(admin.ModelAdmin):
    list_display = ['aircraft', 'transaction_type', 'quantity_liters', 'created_at']
    list_filter = ['transaction_type', 'fuel_type']
