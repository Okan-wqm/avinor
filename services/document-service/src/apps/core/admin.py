from django.contrib import admin
from .models import DocumentCategory, Document, DocumentVersion, DocumentShare


@admin.register(DocumentCategory)
class DocumentCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'parent', 'organization_id', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name', 'description']
    ordering = ['name']


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ['title', 'document_type', 'current_version_number', 'status', 'access_level', 'owner_id', 'created_at']
    list_filter = ['document_type', 'status', 'access_level']
    search_fields = ['title', 'description', 'document_number']
    ordering = ['-created_at']


@admin.register(DocumentVersion)
class DocumentVersionAdmin(admin.ModelAdmin):
    list_display = ['document', 'version_number', 'version_label', 'uploaded_by_id', 'is_current', 'created_at']
    list_filter = ['is_current']
    search_fields = ['document__title', 'version_label']
    ordering = ['-created_at']


@admin.register(DocumentShare)
class DocumentShareAdmin(admin.ModelAdmin):
    list_display = ['document', 'shared_with_user_id', 'permission_level', 'shared_by_id', 'shared_at', 'expires_at', 'is_public_link']
    list_filter = ['permission_level', 'is_public_link']
    search_fields = ['document__title', 'public_token']
    ordering = ['-shared_at']
