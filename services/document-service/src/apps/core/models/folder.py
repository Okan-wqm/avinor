# services/document-service/src/apps/core/models/folder.py
"""
Document Folder Model

Hierarchical folder structure for document organization.
"""

import uuid
from django.db import models
from django.db.models import Sum


class DocumentFolder(models.Model):
    """
    Hierarchical folder structure for organizing documents.

    Supports:
    - Nested folder hierarchies with path tracking
    - Automatic statistics (document count, total size)
    - System folders (non-deletable)
    - Sharing at folder level
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    organization_id = models.UUIDField(db_index=True)

    # =========================================================================
    # HIERARCHY
    # =========================================================================
    parent_folder = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='subfolders'
    )
    path = models.TextField(
        help_text="Full path from root: /root/folder1/folder2"
    )
    depth = models.PositiveIntegerField(
        default=0,
        help_text="Nesting depth (0 = root level)"
    )

    # =========================================================================
    # IDENTIFICATION
    # =========================================================================
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    color = models.CharField(
        max_length=7,
        blank=True,
        null=True,
        help_text="Hex color code for UI display"
    )
    icon = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Icon identifier for UI"
    )

    # =========================================================================
    # OWNERSHIP
    # =========================================================================
    owner_id = models.UUIDField(db_index=True)
    owner_type = models.CharField(
        max_length=20,
        default='user'
    )

    # =========================================================================
    # FLAGS
    # =========================================================================
    is_system_folder = models.BooleanField(
        default=False,
        help_text="System folders cannot be deleted"
    )
    is_shared = models.BooleanField(default=False)
    is_default = models.BooleanField(
        default=False,
        help_text="Default upload folder for document type"
    )

    # Default folder for specific document types
    default_for_document_type = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="If set, this folder is default for this document type"
    )

    # =========================================================================
    # STATISTICS (denormalized for performance)
    # =========================================================================
    document_count = models.PositiveIntegerField(default=0)
    total_size_bytes = models.BigIntegerField(default=0)
    subfolder_count = models.PositiveIntegerField(default=0)

    # =========================================================================
    # AUDIT
    # =========================================================================
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.UUIDField(null=True, blank=True)

    class Meta:
        db_table = 'document_folders'
        ordering = ['path', 'name']
        indexes = [
            models.Index(fields=['organization_id', 'owner_id']),
            models.Index(fields=['parent_folder_id']),
            models.Index(fields=['path']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['organization_id', 'parent_folder_id', 'name'],
                name='unique_folder_name_per_parent'
            )
        ]

    def __str__(self):
        return self.path

    # =========================================================================
    # PROPERTIES
    # =========================================================================

    @property
    def is_root(self) -> bool:
        """Check if this is a root folder."""
        return self.parent_folder is None

    @property
    def total_size_display(self) -> str:
        """Human-readable total size."""
        size = float(self.total_size_bytes)
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} PB"

    @property
    def full_path(self) -> str:
        """Get full path including this folder's name."""
        if self.parent_folder:
            return f"{self.parent_folder.full_path}/{self.name}"
        return f"/{self.name}"

    # =========================================================================
    # METHODS
    # =========================================================================

    def save(self, *args, **kwargs):
        """Override save to update path and depth."""
        if self.parent_folder:
            self.depth = self.parent_folder.depth + 1
            self.path = f"{self.parent_folder.path}/{self.name}"
        else:
            self.depth = 0
            self.path = f"/{self.name}"
        super().save(*args, **kwargs)

    def get_ancestors(self) -> list:
        """Get all ancestor folders."""
        ancestors = []
        current = self.parent_folder
        while current:
            ancestors.append(current)
            current = current.parent_folder
        return list(reversed(ancestors))

    def get_descendants(self) -> models.QuerySet:
        """Get all descendant folders."""
        return DocumentFolder.objects.filter(
            path__startswith=f"{self.path}/"
        )

    def get_all_documents(self) -> models.QuerySet:
        """Get all documents in this folder and subfolders."""
        from .document import Document
        folder_ids = [self.id] + list(
            self.get_descendants().values_list('id', flat=True)
        )
        return Document.objects.filter(folder_id__in=folder_ids)

    def recalculate_statistics(self) -> None:
        """Recalculate folder statistics from actual data."""
        from .document import Document, DocumentStatus

        # Count documents directly in this folder
        self.document_count = Document.objects.filter(
            folder=self,
            status=DocumentStatus.ACTIVE
        ).count()

        # Sum file sizes
        result = Document.objects.filter(
            folder=self,
            status=DocumentStatus.ACTIVE
        ).aggregate(total=Sum('file_size'))
        self.total_size_bytes = result['total'] or 0

        # Count subfolders
        self.subfolder_count = self.subfolders.count()

        self.save(update_fields=[
            'document_count', 'total_size_bytes', 'subfolder_count', 'updated_at'
        ])

    def move_to(self, new_parent: 'DocumentFolder' = None) -> None:
        """Move folder to a new parent."""
        old_path = self.path

        self.parent_folder = new_parent
        if new_parent:
            self.depth = new_parent.depth + 1
            self.path = f"{new_parent.path}/{self.name}"
        else:
            self.depth = 0
            self.path = f"/{self.name}"

        self.save()

        # Update all descendant paths
        descendants = DocumentFolder.objects.filter(
            path__startswith=f"{old_path}/"
        )
        for descendant in descendants:
            descendant.path = descendant.path.replace(old_path, self.path, 1)
            descendant.depth = descendant.path.count('/') - 1
            descendant.save(update_fields=['path', 'depth'])

    def can_delete(self) -> tuple[bool, str]:
        """Check if folder can be deleted."""
        if self.is_system_folder:
            return False, "System folders cannot be deleted"

        if self.document_count > 0:
            return False, f"Folder contains {self.document_count} documents"

        if self.subfolder_count > 0:
            return False, f"Folder contains {self.subfolder_count} subfolders"

        return True, ""
