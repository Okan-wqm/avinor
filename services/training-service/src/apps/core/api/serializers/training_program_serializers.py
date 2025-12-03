# services/training-service/src/apps/core/api/serializers/training_program_serializers.py
"""
Training Program Serializers

Serializers for training program API endpoints.
"""

from rest_framework import serializers
from decimal import Decimal

from ...models import TrainingProgram, ProgramStage


class ProgramStageSerializer(serializers.Serializer):
    """Serializer for program stages."""

    id = serializers.UUIDField(read_only=True)
    name = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_null=True)
    order = serializers.IntegerField(required=False, default=0)
    code = serializers.CharField(max_length=50, required=False, allow_null=True)


class ProgramRequirementsSerializer(serializers.Serializer):
    """Serializer for program requirements."""

    min_hours = serializers.DictField(child=serializers.FloatField())
    min_age = serializers.IntegerField(allow_null=True)
    medical_class = serializers.IntegerField(allow_null=True)
    prerequisites = serializers.ListField(child=serializers.DictField())
    duration = serializers.DictField()


class TrainingProgramSerializer(serializers.ModelSerializer):
    """Base serializer for training programs."""

    stages = ProgramStageSerializer(many=True, required=False)
    total_lessons = serializers.IntegerField(read_only=True)
    total_flight_hours = serializers.DecimalField(
        max_digits=6, decimal_places=2, read_only=True
    )
    total_ground_hours = serializers.DecimalField(
        max_digits=6, decimal_places=2, read_only=True
    )
    is_active = serializers.BooleanField(read_only=True)

    class Meta:
        model = TrainingProgram
        fields = [
            'id', 'organization_id', 'code', 'name', 'description',
            'program_type', 'regulatory_authority', 'approval_number',
            'approval_date', 'expiry_date',
            'min_hours_total', 'min_hours_dual', 'min_hours_solo',
            'min_hours_pic', 'min_hours_cross_country', 'min_hours_night',
            'min_hours_instrument', 'min_hours_simulator', 'min_hours_ground',
            'prerequisites', 'min_age', 'required_medical_class',
            'estimated_duration_days', 'max_duration_months',
            'base_price', 'currency', 'price_includes_vat',
            'syllabus_version', 'syllabus_document_url',
            'stages', 'status', 'is_published', 'thumbnail_url',
            'metadata', 'tags',
            'total_lessons', 'total_flight_hours', 'total_ground_hours',
            'is_active',
            'created_by', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'organization_id', 'created_at', 'updated_at']


class TrainingProgramCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating training programs."""

    stages = ProgramStageSerializer(many=True, required=False)

    class Meta:
        model = TrainingProgram
        fields = [
            'code', 'name', 'description', 'program_type',
            'regulatory_authority', 'approval_number', 'approval_date',
            'min_hours_total', 'min_hours_dual', 'min_hours_solo',
            'min_hours_pic', 'min_hours_cross_country', 'min_hours_night',
            'min_hours_instrument', 'min_hours_simulator', 'min_hours_ground',
            'prerequisites', 'min_age', 'required_medical_class',
            'estimated_duration_days', 'max_duration_months',
            'base_price', 'currency', 'price_includes_vat',
            'syllabus_version', 'stages', 'thumbnail_url',
            'metadata', 'tags',
        ]

    def validate_code(self, value):
        """Validate code uniqueness within organization."""
        organization_id = self.context.get('organization_id')
        if TrainingProgram.objects.filter(
            organization_id=organization_id,
            code=value
        ).exists():
            raise serializers.ValidationError(
                f"Program with code '{value}' already exists"
            )
        return value

    def validate_program_type(self, value):
        """Validate program type."""
        valid_types = [choice[0] for choice in TrainingProgram.ProgramType.choices]
        if value not in valid_types:
            raise serializers.ValidationError(
                f"Invalid program type. Must be one of: {', '.join(valid_types)}"
            )
        return value


class TrainingProgramUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating training programs."""

    stages = ProgramStageSerializer(many=True, required=False)

    class Meta:
        model = TrainingProgram
        fields = [
            'name', 'description', 'regulatory_authority',
            'approval_number', 'approval_date', 'expiry_date',
            'min_hours_total', 'min_hours_dual', 'min_hours_solo',
            'min_hours_pic', 'min_hours_cross_country', 'min_hours_night',
            'min_hours_instrument', 'min_hours_simulator', 'min_hours_ground',
            'prerequisites', 'min_age', 'required_medical_class',
            'estimated_duration_days', 'max_duration_months',
            'base_price', 'currency', 'price_includes_vat',
            'syllabus_version', 'syllabus_document_url',
            'stages', 'status', 'thumbnail_url',
            'metadata', 'tags',
        ]

    def validate_code(self, value):
        """Validate code uniqueness if changed."""
        instance = self.instance
        organization_id = self.context.get('organization_id')

        if value != instance.code:
            if TrainingProgram.objects.filter(
                organization_id=organization_id,
                code=value
            ).exclude(id=instance.id).exists():
                raise serializers.ValidationError(
                    f"Program with code '{value}' already exists"
                )
        return value


class TrainingProgramListSerializer(serializers.ModelSerializer):
    """Serializer for listing training programs."""

    total_lessons = serializers.IntegerField(read_only=True)
    stage_count = serializers.IntegerField(read_only=True)
    active_enrollments_count = serializers.IntegerField(read_only=True)
    is_active = serializers.BooleanField(read_only=True)

    class Meta:
        model = TrainingProgram
        fields = [
            'id', 'code', 'name', 'program_type', 'status',
            'is_published', 'total_lessons', 'stage_count',
            'active_enrollments_count', 'base_price', 'currency',
            'is_active', 'thumbnail_url', 'created_at',
        ]


class TrainingProgramDetailSerializer(serializers.ModelSerializer):
    """Serializer for training program detail view."""

    stages = ProgramStageSerializer(many=True, read_only=True)
    requirements = serializers.SerializerMethodField()
    statistics = serializers.SerializerMethodField()
    total_lessons = serializers.IntegerField(read_only=True)
    total_flight_hours = serializers.DecimalField(
        max_digits=6, decimal_places=2, read_only=True
    )
    total_ground_hours = serializers.DecimalField(
        max_digits=6, decimal_places=2, read_only=True
    )
    is_active = serializers.BooleanField(read_only=True)

    class Meta:
        model = TrainingProgram
        fields = [
            'id', 'organization_id', 'code', 'name', 'description',
            'program_type', 'regulatory_authority', 'approval_number',
            'approval_date', 'expiry_date',
            'min_hours_total', 'min_hours_dual', 'min_hours_solo',
            'min_hours_pic', 'min_hours_cross_country', 'min_hours_night',
            'min_hours_instrument', 'min_hours_simulator', 'min_hours_ground',
            'prerequisites', 'min_age', 'required_medical_class',
            'estimated_duration_days', 'max_duration_months',
            'base_price', 'currency', 'price_includes_vat',
            'syllabus_version', 'syllabus_document_url',
            'stages', 'status', 'is_published', 'thumbnail_url',
            'metadata', 'tags',
            'total_lessons', 'total_flight_hours', 'total_ground_hours',
            'is_active', 'requirements', 'statistics',
            'created_by', 'created_at', 'updated_at',
        ]

    def get_requirements(self, obj):
        """Get program requirements summary."""
        return obj.get_requirements_summary()

    def get_statistics(self, obj):
        """Get basic statistics."""
        return {
            'total_lessons': obj.total_lessons,
            'stage_count': obj.stage_count,
            'active_enrollments': obj.active_enrollments_count,
            'total_flight_hours': float(obj.total_flight_hours),
            'total_ground_hours': float(obj.total_ground_hours),
        }


class ProgramStatisticsSerializer(serializers.Serializer):
    """Serializer for program statistics."""

    program_id = serializers.UUIDField()
    program_code = serializers.CharField()
    enrollments = serializers.DictField()
    lessons = serializers.DictField()
    stages = serializers.ListField(child=serializers.DictField())
    requirements = serializers.DictField()


class StageCreateSerializer(serializers.Serializer):
    """Serializer for creating a stage."""

    name = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_null=True)
    code = serializers.CharField(max_length=50, required=False, allow_null=True)


class StageUpdateSerializer(serializers.Serializer):
    """Serializer for updating a stage."""

    name = serializers.CharField(max_length=255, required=False)
    description = serializers.CharField(required=False, allow_null=True)
    code = serializers.CharField(max_length=50, required=False, allow_null=True)


class StageReorderSerializer(serializers.Serializer):
    """Serializer for reordering stages."""

    stage_order = serializers.ListField(
        child=serializers.UUIDField(),
        help_text="List of stage IDs in desired order"
    )


class ProgramCloneSerializer(serializers.Serializer):
    """Serializer for cloning a program."""

    new_code = serializers.CharField(max_length=50)
    new_name = serializers.CharField(max_length=255)
    include_lessons = serializers.BooleanField(default=True)

    def validate_new_code(self, value):
        """Validate new code uniqueness."""
        organization_id = self.context.get('organization_id')
        if TrainingProgram.objects.filter(
            organization_id=organization_id,
            code=value
        ).exists():
            raise serializers.ValidationError(
                f"Program with code '{value}' already exists"
            )
        return value
