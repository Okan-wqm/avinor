"""
Organization Service Admin Configuration.
"""
from django.contrib import admin
from .models import Organization, OrganizationMember, Location, OrganizationSettings


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ['name', 'organization_type', 'city', 'country', 'is_active', 'is_verified']
    list_filter = ['organization_type', 'is_active', 'is_verified', 'country']
    search_fields = ['name', 'email', 'caa_approval_number']
    prepopulated_fields = {'slug': ('name',)}
    ordering = ['name']


@admin.register(OrganizationMember)
class OrganizationMemberAdmin(admin.ModelAdmin):
    list_display = ['user_id', 'organization', 'role', 'is_active', 'joined_at']
    list_filter = ['role', 'is_active', 'organization']
    search_fields = ['user_id', 'employee_id']
    ordering = ['-joined_at']


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ['name', 'organization', 'location_type', 'icao_code', 'is_active', 'is_primary']
    list_filter = ['location_type', 'is_active', 'is_primary']
    search_fields = ['name', 'icao_code', 'iata_code']
    ordering = ['name']


@admin.register(OrganizationSettings)
class OrganizationSettingsAdmin(admin.ModelAdmin):
    list_display = ['organization', 'booking_advance_days', 'allow_student_self_booking']
