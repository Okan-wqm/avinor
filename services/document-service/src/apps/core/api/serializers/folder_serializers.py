# services/document-service/src/apps/core/api/serializers/folder_serializers.py
"""
Folder Serializers
"""

from rest_framework import serializers

from ...models import DocumentFolder, AccessLevel


class FolderSerializer(serializers.ModelSerializer):
    """Base folder serializer."""

    access_level_display = serializers.CharField(
        source='get_access_level_display',
        read_only=True
    )

    class Meta:
        model = DocumentFolder
        fields = [
            'id',
            'organization_id',
            'owner_id',
            'name',
            'description',
            'parent_folder_id',
            'path',
            'depth',
            'access_level',
            'access_level_display',
            'document_count',
            'total_size_bytes',
            'subfolder_count',
            'color',
            'icon',
            'is_system',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'path',
            'depth',
            'document_count',
            'total_size_bytes',
            'subfolder_count',
            'is_system',
            'created_at',
            'updated_at',
        ]


class FolderListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for folder lists."""

    class Meta:
        model = DocumentFolder
        fields = [
            'id',
            'name',
            'parent_folder_id',
            'path',
            'depth',
            'document_count',
            'subfolder_count',
            'color',
            'icon',
            'is_system',
        ]


class FolderDetailSerializer(FolderSerializer):
    """Full folder details with children."""

    children = serializers.SerializerMethodField()
    ancestors = serializers.SerializerMethodField()
    total_size_display = serializers.SerializerMethodField()

    class Meta(FolderSerializer.Meta):
        fields = FolderSerializer.Meta.fields + [
            'children',
            'ancestors',
            'total_size_display',
            'metadata',
        ]

    def get_children(self, obj):
        """Get immediate child folders."""
        children = obj.subfolders.all()[:50]
        return FolderListSerializer(children, many=True).data

    def get_ancestors(self, obj):
        """Get folder ancestors (breadcrumb)."""
        ancestors = obj.get_ancestors()
        return [
            {'id': str(a.id), 'name': a.name, 'path': a.path}
            for a in ancestors
        ]

    def get_total_size_display(self, obj):
        """Format total size for display."""
        size = obj.total_size_bytes
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"


class FolderCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating folders."""

    class Meta:
        model = DocumentFolder
        fields = [
            'name',
            'description',
            'parent_folder_id',
            'access_level',
            'color',
            'icon',
            'metadata',
        ]

    def validate_name(self, value):
        """Validate folder name."""
        # Check for invalid characters
        invalid_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
        for char in invalid_chars:
            if char in value:
                raise serializers.ValidationError(
                    f"Folder name cannot contain '{char}'"
                )
        return value

    def validate(self, data):
        """Validate folder creation."""
        organization_id = self.context.get('organization_id')
        parent_folder_id = data.get('parent_folder_id')
        name = data.get('name')

        # Check for duplicate name in same parent
        exists = DocumentFolder.objects.filter(
            organization_id=organization_id,
            parent_folder_id=parent_folder_id,
            name=name,
        ).exists()

        if exists:
            raise serializers.ValidationError({
                'name': f"Folder '{name}' already exists in this location"
            })

        # Check parent exists and belongs to same org
        if parent_folder_id:
            try:
                parent = DocumentFolder.objects.get(
                    id=parent_folder_id,
                    organization_id=organization_id,
                )
                # Check max depth (10 levels)
                if parent.depth >= 10:
                    raise serializers.ValidationError({
                        'parent_folder_id': "Maximum folder depth reached"
                    })
            except DocumentFolder.DoesNotExist:
                raise serializers.ValidationError({
                    'parent_folder_id': "Parent folder not found"
                })

        return data


class FolderUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating folders."""

    class Meta:
        model = DocumentFolder
        fields = [
            'name',
            'description',
            'access_level',
            'color',
            'icon',
            'metadata',
        ]

    def validate_name(self, value):
        """Validate folder name."""
        invalid_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
        for char in invalid_chars:
            if char in value:
                raise serializers.ValidationError(
                    f"Folder name cannot contain '{char}'"
                )
        return value

    def validate(self, data):
        """Validate folder update."""
        instance = self.instance

        if instance and instance.is_system:
            raise serializers.ValidationError(
                "System folders cannot be modified"
            )

        # Check for duplicate name if name is changing
        if 'name' in data and data['name'] != instance.name:
            exists = DocumentFolder.objects.filter(
                organization_id=instance.organization_id,
                parent_folder_id=instance.parent_folder_id,
                name=data['name'],
            ).exclude(id=instance.id).exists()

            if exists:
                raise serializers.ValidationError({
                    'name': f"Folder '{data['name']}' already exists"
                })

        return data


class FolderMoveSerializer(serializers.Serializer):
    """Serializer for moving folders."""

    target_folder_id = serializers.UUIDField(
        allow_null=True,
        help_text="Target parent folder ID (null for root)"
    )

    def validate(self, data):
        """Validate folder move."""
        folder = self.context.get('folder')
        target_id = data.get('target_folder_id')
        organization_id = self.context.get('organization_id')

        if folder.is_system:
            raise serializers.ValidationError(
                "System folders cannot be moved"
            )

        # Cannot move to self
        if target_id and str(folder.id) == str(target_id):
            raise serializers.ValidationError({
                'target_folder_id': "Cannot move folder to itself"
            })

        # Cannot move to own descendant
        if target_id:
            descendants = folder.get_descendants()
            descendant_ids = {str(d.id) for d in descendants}

            if str(target_id) in descendant_ids:
                raise serializers.ValidationError({
                    'target_folder_id': "Cannot move folder to its descendant"
                })

            # Check target exists
            try:
                target = DocumentFolder.objects.get(
                    id=target_id,
                    organization_id=organization_id,
                )

                # Check max depth
                new_depth = target.depth + 1
                max_descendant_depth = max(
                    [d.depth for d in descendants] + [folder.depth]
                ) - folder.depth

                if new_depth + max_descendant_depth > 10:
                    raise serializers.ValidationError({
                        'target_folder_id': "Move would exceed maximum depth"
                    })

            except DocumentFolder.DoesNotExist:
                raise serializers.ValidationError({
                    'target_folder_id': "Target folder not found"
                })

        return data


class FolderTreeSerializer(serializers.Serializer):
    """Serializer for folder tree structure."""

    id = serializers.UUIDField()
    name = serializers.CharField()
    path = serializers.CharField()
    depth = serializers.IntegerField()
    document_count = serializers.IntegerField()
    subfolder_count = serializers.IntegerField()
    color = serializers.CharField(allow_null=True)
    icon = serializers.CharField(allow_null=True)
    children = serializers.SerializerMethodField()

    def get_children(self, obj):
        """Recursively get children."""
        children = getattr(obj, '_children', [])
        return FolderTreeSerializer(children, many=True).data


class FolderBulkMoveSerializer(serializers.Serializer):
    """Serializer for bulk folder operations."""

    folder_ids = serializers.ListField(
        child=serializers.UUIDField(),
        min_length=1,
        max_length=50
    )
    target_folder_id = serializers.UUIDField(allow_null=True)
