# services/user-service/src/apps/core/serializers/user.py
"""
User Serializers - Comprehensive serializers for User model

Includes:
- UserSerializer: Full user details with roles and permissions
- UserListSerializer: Lightweight for list views
- UserCreateSerializer: Registration with validation
- UserUpdateSerializer: Profile updates
- UserSearchSerializer: For autocomplete/search
"""

from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from apps.core.models import User, UserSession


class UserSerializer(serializers.ModelSerializer):
    """
    Full User serializer with all details.
    Used for single user retrieval and profile views.
    """

    full_name = serializers.CharField(read_only=True)
    initials = serializers.CharField(read_only=True)
    roles = serializers.SerializerMethodField()
    permissions = serializers.SerializerMethodField()
    active_roles = serializers.SerializerMethodField()
    two_factor_methods = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id',
            'email',
            'username',
            'first_name',
            'last_name',
            'middle_name',
            'full_name',
            'initials',
            'phone',
            'mobile_phone',
            'organization_id',
            'status',
            'is_active',
            'is_verified',
            'is_superuser',
            'two_factor_enabled',
            'two_factor_methods',

            # Address
            'address',
            'city',
            'state',
            'country',
            'postal_code',

            # Demographics
            'date_of_birth',
            'gender',
            'nationality',

            # Preferences
            'timezone',
            'language',
            'locale',
            'avatar_url',

            # Emergency contact
            'emergency_contact_name',
            'emergency_contact_phone',
            'emergency_contact_relationship',

            # Timestamps
            'last_login',
            'last_activity',
            'password_changed_at',
            'created_at',
            'updated_at',

            # Computed
            'roles',
            'permissions',
            'active_roles',
        ]
        read_only_fields = [
            'id',
            'is_verified',
            'is_superuser',
            'last_login',
            'last_activity',
            'password_changed_at',
            'created_at',
            'updated_at',
        ]

    def get_roles(self, obj) -> list:
        """Get user's role codes."""
        return obj.get_roles()

    def get_permissions(self, obj) -> list:
        """Get user's permission codes."""
        return obj.get_permissions()

    def get_active_roles(self, obj) -> list:
        """Get detailed active role information."""
        from apps.core.models import UserRole
        from django.utils import timezone
        from django.db.models import Q

        now = timezone.now()
        user_roles = UserRole.objects.filter(
            user=obj,
            valid_from__lte=now,
            revoked_at__isnull=True
        ).filter(
            Q(valid_until__isnull=True) | Q(valid_until__gt=now)
        ).select_related('role')

        return [
            {
                'id': str(ur.role.id),
                'code': ur.role.code,
                'name': ur.role.name,
                'is_system_role': ur.role.is_system_role,
                'priority': ur.role.priority,
                'color': ur.role.color,
                'valid_until': ur.valid_until.isoformat() if ur.valid_until else None,
                'location_id': str(ur.location_id) if ur.location_id else None,
            }
            for ur in user_roles
        ]

    def get_two_factor_methods(self, obj) -> list:
        """Get available 2FA methods."""
        methods = []
        if obj.two_factor_enabled and obj.two_factor_method:
            methods.append(obj.two_factor_method)
            if obj.two_factor_backup_codes:
                methods.append('backup_code')
        return methods


class UserListSerializer(serializers.ModelSerializer):
    """
    Lightweight User serializer for list views.
    Optimized for performance with minimal fields.
    """

    full_name = serializers.CharField(read_only=True)
    primary_role = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id',
            'email',
            'username',
            'first_name',
            'last_name',
            'full_name',
            'avatar_url',
            'phone',
            'organization_id',
            'status',
            'is_active',
            'is_verified',
            'two_factor_enabled',
            'primary_role',
            'last_login',
            'created_at',
        ]

    def get_primary_role(self, obj) -> dict:
        """Get user's primary (highest priority) role."""
        from apps.core.models import UserRole
        from django.utils import timezone
        from django.db.models import Q

        now = timezone.now()
        user_role = UserRole.objects.filter(
            user=obj,
            valid_from__lte=now,
            revoked_at__isnull=True
        ).filter(
            Q(valid_until__isnull=True) | Q(valid_until__gt=now)
        ).select_related('role').order_by('-role__priority').first()

        if user_role:
            return {
                'code': user_role.role.code,
                'name': user_role.role.name,
                'color': user_role.role.color,
            }
        return None


class UserSearchSerializer(serializers.ModelSerializer):
    """
    Minimal serializer for search/autocomplete results.
    """

    full_name = serializers.CharField(read_only=True)
    label = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id',
            'email',
            'full_name',
            'avatar_url',
            'label',
        ]

    def get_label(self, obj) -> str:
        """Get display label for autocomplete."""
        return f"{obj.full_name} ({obj.email})"


class UserCreateSerializer(serializers.Serializer):
    """
    Serializer for creating new users.
    Handles password validation and confirmation.
    """

    email = serializers.EmailField(required=True)
    password = serializers.CharField(
        write_only=True,
        required=True,
        min_length=12,
        style={'input_type': 'password'}
    )
    password_confirm = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'}
    )
    first_name = serializers.CharField(required=True, max_length=100)
    last_name = serializers.CharField(required=True, max_length=100)
    middle_name = serializers.CharField(required=False, max_length=100, allow_blank=True)
    phone = serializers.CharField(required=False, max_length=20, allow_blank=True)
    organization_id = serializers.UUIDField(required=False, allow_null=True)

    # Optional fields
    date_of_birth = serializers.DateField(required=False, allow_null=True)
    gender = serializers.ChoiceField(
        choices=[('male', 'Male'), ('female', 'Female'), ('other', 'Other')],
        required=False,
        allow_blank=True
    )
    nationality = serializers.CharField(required=False, max_length=50, allow_blank=True)
    timezone = serializers.CharField(required=False, max_length=50, default='UTC')
    language = serializers.CharField(required=False, max_length=10, default='en')

    def validate_email(self, value):
        """Ensure email is unique."""
        email = value.lower()
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return email

    def validate_password(self, value):
        """Validate password against policy."""
        errors = []

        if len(value) < 12:
            errors.append("Password must be at least 12 characters.")
        if not any(c.isupper() for c in value):
            errors.append("Password must contain at least one uppercase letter.")
        if not any(c.islower() for c in value):
            errors.append("Password must contain at least one lowercase letter.")
        if not any(c.isdigit() for c in value):
            errors.append("Password must contain at least one number.")
        if not any(c in "!@#$%^&*()_+-=[]{}|;':\",./<>?" for c in value):
            errors.append("Password must contain at least one special character.")

        if errors:
            raise serializers.ValidationError(errors)

        return value

    def validate(self, attrs):
        """Validate password confirmation."""
        if attrs.get('password') != attrs.get('password_confirm'):
            raise serializers.ValidationError({
                'password_confirm': "Passwords do not match."
            })
        return attrs


class UserUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating user profile.
    Excludes sensitive fields that require special handling.
    """

    class Meta:
        model = User
        fields = [
            'first_name',
            'last_name',
            'middle_name',
            'phone',
            'mobile_phone',

            # Address
            'address',
            'city',
            'state',
            'country',
            'postal_code',

            # Demographics
            'date_of_birth',
            'gender',
            'nationality',

            # Preferences
            'timezone',
            'language',
            'locale',
            'avatar_url',

            # Emergency contact
            'emergency_contact_name',
            'emergency_contact_phone',
            'emergency_contact_relationship',

            # Metadata
            'metadata',
        ]


class UserStatusUpdateSerializer(serializers.Serializer):
    """Serializer for updating user status."""

    status = serializers.ChoiceField(
        choices=User.Status.choices,
        required=True
    )
    reason = serializers.CharField(
        required=False,
        max_length=500,
        allow_blank=True
    )


class UserBulkActionSerializer(serializers.Serializer):
    """Serializer for bulk user actions."""

    user_ids = serializers.ListField(
        child=serializers.UUIDField(),
        min_length=1,
        max_length=100
    )
    action = serializers.ChoiceField(
        choices=[
            ('activate', 'Activate'),
            ('deactivate', 'Deactivate'),
            ('suspend', 'Suspend'),
            ('delete', 'Delete'),
        ]
    )
    reason = serializers.CharField(
        required=False,
        max_length=500,
        allow_blank=True
    )


class UserSessionSerializer(serializers.ModelSerializer):
    """Serializer for user sessions."""

    is_current = serializers.SerializerMethodField()

    class Meta:
        model = UserSession
        fields = [
            'id',
            'ip_address',
            'user_agent',
            'device_info',
            'created_at',
            'last_activity',
            'expires_at',
            'is_active',
            'is_current',
        ]

    def get_is_current(self, obj) -> bool:
        """Check if this is the current session."""
        request = self.context.get('request')
        if request and hasattr(request, 'session_id'):
            return str(obj.id) == str(request.session_id)
        return False


class UserInviteSerializer(serializers.Serializer):
    """Serializer for inviting new users."""

    email = serializers.EmailField(required=True)
    first_name = serializers.CharField(required=True, max_length=100)
    last_name = serializers.CharField(required=True, max_length=100)
    role_codes = serializers.ListField(
        child=serializers.CharField(max_length=50),
        required=False,
        default=list
    )
    message = serializers.CharField(
        required=False,
        max_length=1000,
        allow_blank=True
    )

    def validate_email(self, value):
        """Ensure email is not already registered."""
        email = value.lower()
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return email


class EmailChangeSerializer(serializers.Serializer):
    """Serializer for email change request."""

    new_email = serializers.EmailField(required=True)
    password = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'}
    )

    def validate_new_email(self, value):
        """Ensure new email is not taken."""
        email = value.lower()
        user = self.context.get('user')

        if user and email == user.email.lower():
            raise serializers.ValidationError("New email is same as current email.")

        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError("This email is already in use.")

        return email

    def validate_password(self, value):
        """Verify current password."""
        user = self.context.get('user')
        if user and not user.check_password(value):
            raise serializers.ValidationError("Invalid password.")
        return value
