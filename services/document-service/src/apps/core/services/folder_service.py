# services/document-service/src/apps/core/services/folder_service.py
"""
Folder Service

Business logic for folder management operations.
"""

import uuid
import logging
from typing import List, Optional

from django.db import transaction

from ..models import DocumentFolder, Document, DocumentStatus


logger = logging.getLogger(__name__)


class FolderNotFoundError(Exception):
    """Folder not found."""
    pass


class FolderAccessDeniedError(Exception):
    """Access to folder denied."""
    pass


class FolderOperationError(Exception):
    """Folder operation failed."""
    pass


class FolderService:
    """
    Service for folder management operations.

    Handles:
    - Folder CRUD operations
    - Hierarchical folder management
    - Statistics calculation
    - Permission checks
    """

    # =========================================================================
    # CREATE
    # =========================================================================

    @transaction.atomic
    def create_folder(
        self,
        organization_id: uuid.UUID,
        owner_id: uuid.UUID,
        name: str,
        parent_folder_id: uuid.UUID = None,
        description: str = None,
        color: str = None,
        icon: str = None,
        is_default: bool = False,
        default_for_document_type: str = None,
        created_by: uuid.UUID = None,
    ) -> DocumentFolder:
        """
        Create a new folder.

        Args:
            organization_id: Organization UUID
            owner_id: User UUID who owns the folder
            name: Folder name
            parent_folder_id: Parent folder UUID (None for root)
            description: Optional description
            color: Optional hex color
            icon: Optional icon identifier
            is_default: Whether this is a default folder
            default_for_document_type: Document type this is default for
            created_by: User creating the folder

        Returns:
            Created DocumentFolder instance
        """
        # Check for duplicate name in same parent
        existing = DocumentFolder.objects.filter(
            organization_id=organization_id,
            parent_folder_id=parent_folder_id,
            name=name,
        ).exists()

        if existing:
            raise FolderOperationError(
                f"Folder '{name}' already exists in this location"
            )

        parent_folder = None
        if parent_folder_id:
            parent_folder = self.get_folder(parent_folder_id)

        folder = DocumentFolder.objects.create(
            organization_id=organization_id,
            owner_id=owner_id,
            name=name,
            parent_folder=parent_folder,
            description=description,
            color=color,
            icon=icon,
            is_default=is_default,
            default_for_document_type=default_for_document_type,
            created_by=created_by or owner_id,
        )

        # Update parent's subfolder count
        if parent_folder:
            parent_folder.subfolder_count += 1
            parent_folder.save(update_fields=['subfolder_count'])

        logger.info(f"Created folder: {folder.path}")

        return folder

    def create_system_folders(
        self,
        organization_id: uuid.UUID,
        owner_id: uuid.UUID,
    ) -> List[DocumentFolder]:
        """
        Create default system folders for an organization.

        Args:
            organization_id: Organization UUID
            owner_id: Admin user UUID

        Returns:
            List of created folders
        """
        system_folders = [
            {'name': 'Certificates', 'default_for': 'certificate', 'icon': 'certificate'},
            {'name': 'Licenses', 'default_for': 'license', 'icon': 'id-card'},
            {'name': 'Medical Records', 'default_for': 'medical', 'icon': 'heartbeat'},
            {'name': 'Training Records', 'default_for': 'training_record', 'icon': 'graduation-cap'},
            {'name': 'Flight Logs', 'default_for': 'flight_log', 'icon': 'plane'},
            {'name': 'Maintenance', 'default_for': 'maintenance', 'icon': 'wrench'},
            {'name': 'Insurance', 'default_for': 'insurance', 'icon': 'shield'},
            {'name': 'Manuals', 'default_for': 'manual', 'icon': 'book'},
            {'name': 'Contracts', 'default_for': 'contract', 'icon': 'file-signature'},
            {'name': 'Invoices', 'default_for': 'invoice', 'icon': 'file-invoice'},
        ]

        created = []
        for folder_def in system_folders:
            folder = self.create_folder(
                organization_id=organization_id,
                owner_id=owner_id,
                name=folder_def['name'],
                is_default=True,
                default_for_document_type=folder_def['default_for'],
                icon=folder_def.get('icon'),
            )
            folder.is_system_folder = True
            folder.save(update_fields=['is_system_folder'])
            created.append(folder)

        logger.info(f"Created {len(created)} system folders for org {organization_id}")

        return created

    # =========================================================================
    # RETRIEVE
    # =========================================================================

    def get_folder(
        self,
        folder_id: uuid.UUID,
    ) -> DocumentFolder:
        """
        Get a folder by ID.

        Args:
            folder_id: Folder UUID

        Returns:
            DocumentFolder instance

        Raises:
            FolderNotFoundError: If folder not found
        """
        try:
            return DocumentFolder.objects.get(id=folder_id)
        except DocumentFolder.DoesNotExist:
            raise FolderNotFoundError(f"Folder not found: {folder_id}")

    def get_folders(
        self,
        organization_id: uuid.UUID,
        parent_folder_id: uuid.UUID = None,
        owner_id: uuid.UUID = None,
        include_system: bool = True,
    ) -> List[DocumentFolder]:
        """
        Get folders with filtering.

        Args:
            organization_id: Organization UUID
            parent_folder_id: Filter by parent (None for root folders)
            owner_id: Filter by owner
            include_system: Include system folders

        Returns:
            List of DocumentFolder instances
        """
        queryset = DocumentFolder.objects.filter(
            organization_id=organization_id
        )

        if parent_folder_id:
            queryset = queryset.filter(parent_folder_id=parent_folder_id)
        else:
            # Root level folders
            queryset = queryset.filter(parent_folder__isnull=True)

        if owner_id:
            queryset = queryset.filter(owner_id=owner_id)

        if not include_system:
            queryset = queryset.filter(is_system_folder=False)

        return list(queryset.order_by('name'))

    def get_folder_tree(
        self,
        organization_id: uuid.UUID,
        max_depth: int = 10,
    ) -> List[dict]:
        """
        Get full folder tree structure.

        Args:
            organization_id: Organization UUID
            max_depth: Maximum tree depth

        Returns:
            Nested list of folder dictionaries
        """
        def build_tree(parent_id=None, depth=0):
            if depth >= max_depth:
                return []

            folders = DocumentFolder.objects.filter(
                organization_id=organization_id,
                parent_folder_id=parent_id,
            ).order_by('name')

            tree = []
            for folder in folders:
                node = {
                    'id': str(folder.id),
                    'name': folder.name,
                    'path': folder.path,
                    'depth': folder.depth,
                    'is_system': folder.is_system_folder,
                    'document_count': folder.document_count,
                    'color': folder.color,
                    'icon': folder.icon,
                    'children': build_tree(folder.id, depth + 1),
                }
                tree.append(node)

            return tree

        return build_tree()

    def get_folder_path(
        self,
        folder_id: uuid.UUID,
    ) -> List[DocumentFolder]:
        """
        Get full path from root to folder.

        Args:
            folder_id: Target folder UUID

        Returns:
            List of folders from root to target (inclusive)
        """
        folder = self.get_folder(folder_id)
        path = folder.get_ancestors()
        path.append(folder)
        return path

    def get_default_folder(
        self,
        organization_id: uuid.UUID,
        document_type: str,
    ) -> Optional[DocumentFolder]:
        """
        Get the default folder for a document type.

        Args:
            organization_id: Organization UUID
            document_type: Document type to find default for

        Returns:
            DocumentFolder or None
        """
        return DocumentFolder.objects.filter(
            organization_id=organization_id,
            default_for_document_type=document_type,
            is_default=True,
        ).first()

    # =========================================================================
    # UPDATE
    # =========================================================================

    @transaction.atomic
    def update_folder(
        self,
        folder_id: uuid.UUID,
        user_id: uuid.UUID,
        **updates
    ) -> DocumentFolder:
        """
        Update folder metadata.

        Args:
            folder_id: Folder UUID
            user_id: User updating
            **updates: Fields to update

        Returns:
            Updated DocumentFolder instance
        """
        folder = self.get_folder(folder_id)

        if not self._can_modify(folder, user_id):
            raise FolderAccessDeniedError("Cannot modify folder")

        if folder.is_system_folder:
            # System folders have restricted updates
            allowed_fields = {'description', 'color', 'icon'}
        else:
            allowed_fields = {
                'name', 'description', 'color', 'icon',
                'is_default', 'default_for_document_type',
            }

        # Check for name conflict if renaming
        if 'name' in updates and updates['name'] != folder.name:
            existing = DocumentFolder.objects.filter(
                organization_id=folder.organization_id,
                parent_folder_id=folder.parent_folder_id,
                name=updates['name'],
            ).exclude(id=folder_id).exists()

            if existing:
                raise FolderOperationError(
                    f"Folder '{updates['name']}' already exists"
                )

        for field, value in updates.items():
            if field in allowed_fields:
                setattr(folder, field, value)

        folder.save()

        # Update path if name changed
        if 'name' in updates:
            # Re-save to update path
            folder.save()
            # Update descendant paths
            for descendant in folder.get_descendants():
                descendant.save()

        logger.info(f"Updated folder: {folder_id}")

        return folder

    @transaction.atomic
    def move_folder(
        self,
        folder_id: uuid.UUID,
        user_id: uuid.UUID,
        new_parent_id: uuid.UUID = None,
    ) -> DocumentFolder:
        """
        Move folder to a new parent.

        Args:
            folder_id: Folder to move
            user_id: User moving
            new_parent_id: New parent folder (None for root)

        Returns:
            Updated DocumentFolder instance
        """
        folder = self.get_folder(folder_id)

        if not self._can_modify(folder, user_id):
            raise FolderAccessDeniedError("Cannot move folder")

        if folder.is_system_folder:
            raise FolderOperationError("Cannot move system folder")

        # Check not moving to self or descendant
        if new_parent_id:
            new_parent = self.get_folder(new_parent_id)

            if new_parent.id == folder.id:
                raise FolderOperationError("Cannot move folder to itself")

            # Check if new parent is a descendant
            descendants = list(folder.get_descendants().values_list('id', flat=True))
            if new_parent_id in [str(d) for d in descendants]:
                raise FolderOperationError(
                    "Cannot move folder to its own descendant"
                )

            # Check name conflict
            existing = DocumentFolder.objects.filter(
                organization_id=folder.organization_id,
                parent_folder_id=new_parent_id,
                name=folder.name,
            ).exclude(id=folder_id).exists()

            if existing:
                raise FolderOperationError(
                    f"Folder '{folder.name}' already exists in destination"
                )

        old_parent_id = folder.parent_folder_id

        folder.move_to(
            new_parent=DocumentFolder.objects.get(id=new_parent_id)
            if new_parent_id else None
        )

        # Update subfolder counts
        if old_parent_id:
            old_parent = DocumentFolder.objects.get(id=old_parent_id)
            old_parent.subfolder_count = max(0, old_parent.subfolder_count - 1)
            old_parent.save(update_fields=['subfolder_count'])

        if new_parent_id:
            new_parent = DocumentFolder.objects.get(id=new_parent_id)
            new_parent.subfolder_count += 1
            new_parent.save(update_fields=['subfolder_count'])

        logger.info(f"Moved folder {folder_id} to {new_parent_id or 'root'}")

        return folder

    # =========================================================================
    # DELETE
    # =========================================================================

    @transaction.atomic
    def delete_folder(
        self,
        folder_id: uuid.UUID,
        user_id: uuid.UUID,
        force: bool = False,
    ) -> bool:
        """
        Delete a folder.

        Args:
            folder_id: Folder UUID
            user_id: User deleting
            force: If True, delete contents recursively

        Returns:
            True if deleted
        """
        folder = self.get_folder(folder_id)

        if not self._can_delete(folder, user_id):
            raise FolderAccessDeniedError("Cannot delete folder")

        can_delete, reason = folder.can_delete()

        if not can_delete and not force:
            raise FolderOperationError(reason)

        if force:
            # Delete all documents in folder and subfolders
            all_docs = folder.get_all_documents()
            for doc in all_docs:
                doc.soft_delete(deleted_by=user_id)

            # Delete subfolders recursively
            for subfolder in folder.get_descendants():
                subfolder.delete()

        parent_id = folder.parent_folder_id
        folder.delete()

        # Update parent subfolder count
        if parent_id:
            parent = DocumentFolder.objects.get(id=parent_id)
            parent.subfolder_count = max(0, parent.subfolder_count - 1)
            parent.save(update_fields=['subfolder_count'])

        logger.info(f"Deleted folder: {folder_id}")

        return True

    # =========================================================================
    # STATISTICS
    # =========================================================================

    def recalculate_all_statistics(
        self,
        organization_id: uuid.UUID,
    ) -> int:
        """
        Recalculate statistics for all folders in an organization.

        Args:
            organization_id: Organization UUID

        Returns:
            Number of folders updated
        """
        folders = DocumentFolder.objects.filter(
            organization_id=organization_id
        ).order_by('-depth')  # Process deepest first

        count = 0
        for folder in folders:
            folder.recalculate_statistics()
            count += 1

        logger.info(f"Recalculated statistics for {count} folders")

        return count

    # =========================================================================
    # ACCESS CONTROL HELPERS
    # =========================================================================

    def _can_view(self, folder: DocumentFolder, user_id: uuid.UUID) -> bool:
        """Check if user can view folder."""
        return True  # All org members can view folders

    def _can_modify(self, folder: DocumentFolder, user_id: uuid.UUID) -> bool:
        """Check if user can modify folder."""
        return folder.owner_id == user_id or not folder.is_system_folder

    def _can_delete(self, folder: DocumentFolder, user_id: uuid.UUID) -> bool:
        """Check if user can delete folder."""
        if folder.is_system_folder:
            return False
        return folder.owner_id == user_id
