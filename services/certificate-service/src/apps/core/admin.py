from django.contrib import admin
from .models import License, Rating, MedicalCertificate, TypeRating, Endorsement


@admin.register(License)
class LicenseAdmin(admin.ModelAdmin):
    list_display = ['license_number', 'license_type', 'pilot_id', 'issue_date', 'expiry_date', 'status']
    list_filter = ['license_type', 'status', 'issuing_country']
    search_fields = ['license_number', 'pilot_id']
    ordering = ['-issue_date']


@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = ['rating_type', 'pilot_id', 'issue_date', 'expiry_date', 'status']
    list_filter = ['rating_type', 'status']
    search_fields = ['rating_number', 'pilot_id']
    ordering = ['-issue_date']


@admin.register(MedicalCertificate)
class MedicalCertificateAdmin(admin.ModelAdmin):
    list_display = ['certificate_number', 'certificate_class', 'pilot_id', 'examination_date', 'expiry_date', 'status']
    list_filter = ['certificate_class', 'status', 'has_limitations']
    search_fields = ['certificate_number', 'pilot_id', 'examiner_name']
    ordering = ['-issue_date']


@admin.register(TypeRating)
class TypeRatingAdmin(admin.ModelAdmin):
    list_display = ['aircraft_make_model', 'pilot_id', 'checkride_date', 'status']
    list_filter = ['status']
    search_fields = ['aircraft_make_model', 'pilot_id', 'type_rating_number']
    ordering = ['-issue_date']


@admin.register(Endorsement)
class EndorsementAdmin(admin.ModelAdmin):
    list_display = ['endorsement_type', 'title', 'pilot_id', 'instructor_id', 'endorsement_date', 'expiry_date']
    list_filter = ['endorsement_type']
    search_fields = ['title', 'pilot_id', 'instructor_id']
    ordering = ['-endorsement_date']
