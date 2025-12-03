# services/user-service/src/apps/core/services/user_service.py
"""
User Service - Comprehensive Business Logic Layer

Handles all user management operations including:
- User CRUD operations
- Profile management
- Organization membership
- User search and filtering
- Bulk operations
- Avatar management
"""

import logging
from typing import Dict, List, Optional, Tuple, Any
from django.db import transaction
from django.db.models import Q, Count
from django.utils import timezone
from django.core.paginator import Paginator

from apps.core.models import (
    User, UserRole, Role, AuditLog,
    EmailVerificationToken, RefreshToken
)

logger = logging.getLogger(__name__)


class UserServiceError(Exception):
    """Base exception for user service errors"""
    def __init__(self, message: str, code: str = 'user_error', details: Dict = None):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(message)


class UserNotFoundError(UserServiceError):
    """User not found"""
    def __init__(self, identifier: str = None):
        super().__init__(
            f"User not found" + (f": {identifier}" if identifier else ""),
            'user_not_found'
        )


class UserExistsError(UserServiceError):
    """User already exists"""
    def __init__(self, email: str):
        super().__init__(
            f"User with email '{email}' already exists",
            'user_exists',
            {'email': email}
        )


class UserService:
    """
    Comprehensive user management service.

    Features:
    - User CRUD with validation
    - Profile updates
    - Status management (activate, deactivate, suspend)
    - Soft delete with data retention
    - Organization management
    - Search and filtering
    - Bulk operations
    - Audit logging
    """

    def __init__(self):
        pass

    # ==================== USER CRUD ====================

    @transaction.atomic
    def create_user(
        self,
        email: str,
        first_name: str,
        last_name: str,
        organization_id: str = None,
        created_by: User = None,
        send_verification: bool = True,
        **kwargs
    ) -> User:
        """
        Create a new user.

        Args:
            email: User's email address
            first_name: First name
            last_name: Last name
            organization_id: Organization ID
            created_by: User creating this user
            send_verification: Send email verification
            **kwargs: Additional user fields

        Returns:
            Created User object

        Raises:
            UserExistsError: If email already exists
        """
        # Check for existing user
        if User.objects.filter(email__iexact=email).exists():
            raise UserExistsError(email)

        # Extract password if provided
        password = kwargs.pop('password', None)

        # Create user
        user = User(
            email=email.lower(),
            username=email.lower(),
            first_name=first_name,
            last_name=last_name,
            organization_id=organization_id,
            status=User.Status.PENDING if send_verification else User.Status.ACTIVE,
            is_active=not send_verification,
            created_by=created_by.id if created_by else None,
            **kwargs
        )

        if password:
            user.set_password(password)
            user.password_changed_at = timezone.now()
        else:
            # Set unusable password for invited users
            user.set_unusable_password()

        user.save()

        # Create email verification token
        if send_verification:
            EmailVerificationToken.create_for_user(user)

        # Assign default role
        self._assign_default_role(user)

        # Audit log
        AuditLog.log(
            action='create',
            entity_type='user',
            entity_id=user.id,
            entity_name=user.email,
            user=created_by,
            organization_id=organization_id,
            risk_level='medium',
            new_values={
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'organization_id': str(organization_id) if organization_id else None
            }
        )

        # Publish event
        self._publish_event('user.created', {
            'user_id': str(user.id),
            'email': user.email,
            'organization_id': str(organization_id) if organization_id else None,
            'created_by': str(created_by.id) if created_by else None
        })

        logger.info(f"User created: {user.email}")
        return user

    def get_user(
        self,
        user_id: str = None,
        email: str = None,
        username: str = None,
        include_deleted: bool = False
    ) -> Optional[User]:
        """
        Get user by ID, email, or username.

        Args:
            user_id: User UUID
            email: User email
            username: Username
            include_deleted: Include soft-deleted users

        Returns:
            User object or None
        """
        try:
            query = User.objects.all()

            if not include_deleted:
                query = query.filter(deleted_at__isnull=True)

            if user_id:
                return query.get(id=user_id)
            elif email:
                return query.get(email__iexact=email)
            elif username:
                return query.get(username__iexact=username)
            else:
                return None

        except User.DoesNotExist:
            return None

    def get_user_or_404(
        self,
        user_id: str = None,
        email: str = None
    ) -> User:
        """
        Get user or raise UserNotFoundError.

        Args:
            user_id: User UUID
            email: User email

        Returns:
            User object

        Raises:
            UserNotFoundError: If user not found
        """
        user = self.get_user(user_id=user_id, email=email)
        if not user:
            raise UserNotFoundError(user_id or email)
        return user

    @transaction.atomic
    def update_user(
        self,
        user: User,
        updated_by: User = None,
        **kwargs
    ) -> User:
        """
        Update user information.

        Args:
            user: User to update
            updated_by: User making the update
            **kwargs: Fields to update

        Returns:
            Updated User object
        """
        old_values = {}
        changed_fields = []

        # Define updatable fields
        allowed_fields = [
            'first_name', 'last_name', 'middle_name',
            'phone', 'mobile_phone',
            'address', 'city', 'state', 'country', 'postal_code',
            'date_of_birth', 'gender', 'nationality',
            'timezone', 'language', 'locale',
            'avatar_url',
            'emergency_contact_name', 'emergency_contact_phone',
            'emergency_contact_relationship',
            'metadata'
        ]

        for field in allowed_fields:
            if field in kwargs:
                old_value = getattr(user, field)
                new_value = kwargs[field]
                if old_value != new_value:
                    old_values[field] = old_value
                    setattr(user, field, new_value)
                    changed_fields.append(field)

        if changed_fields:
            user.updated_at = timezone.now()
            user.save(update_fields=changed_fields + ['updated_at'])

            # Audit log
            AuditLog.log(
                action='update',
                entity_type='user',
                entity_id=user.id,
                entity_name=user.email,
                user=updated_by,
                old_values=old_values,
                new_values={k: kwargs[k] for k in changed_fields},
                changed_fields=changed_fields,
                risk_level='low'
            )

            # Publish event
            self._publish_event('user.updated', {
                'user_id': str(user.id),
                'changed_fields': changed_fields
            })

            logger.info(f"User updated: {user.email}, fields: {changed_fields}")

        return user

    @transaction.atomic
    def soft_delete_user(
        self,
        user: User,
        deleted_by: User = None,
        reason: str = None
    ) -> User:
        """
        Soft delete a user.

        Args:
            user: User to delete
            deleted_by: User performing deletion
            reason: Reason for deletion

        Returns:
            Deleted User object
        """
        if user.deleted_at:
            return user  # Already deleted

        user.deleted_at = timezone.now()
        user.deleted_by = deleted_by.id if deleted_by else None
        user.status = User.Status.DELETED
        user.is_active = False
        user.save(update_fields=['deleted_at', 'deleted_by', 'status', 'is_active', 'updated_at'])

        # Revoke all role assignments
        UserRole.objects.filter(
            user=user,
            revoked_at__isnull=True
        ).update(
            revoked_at=timezone.now(),
            revoked_by=deleted_by.id if deleted_by else None
        )

        # Revoke all tokens
        RefreshToken.revoke_all_for_user(user)

        # Audit log
        AuditLog.log(
            action='delete',
            entity_type='user',
            entity_id=user.id,
            entity_name=user.email,
            user=deleted_by,
            risk_level='high',
            metadata={'reason': reason}
        )

        # Publish event
        self._publish_event('user.deleted', {
            'user_id': str(user.id),
            'email': user.email,
            'deleted_by': str(deleted_by.id) if deleted_by else None
        })

        logger.info(f"User soft deleted: {user.email}")
        return user

    @transaction.atomic
    def restore_user(
        self,
        user: User,
        restored_by: User = None
    ) -> User:
        """
        Restore a soft-deleted user.

        Args:
            user: User to restore
            restored_by: User performing restoration

        Returns:
            Restored User object
        """
        if not user.deleted_at:
            return user  # Not deleted

        user.deleted_at = None
        user.deleted_by = None
        user.status = User.Status.INACTIVE
        user.save(update_fields=['deleted_at', 'deleted_by', 'status', 'updated_at'])

        # Audit log
        AuditLog.log(
            action='restore',
            entity_type='user',
            entity_id=user.id,
            entity_name=user.email,
            user=restored_by,
            risk_level='medium'
        )

        logger.info(f"User restored: {user.email}")
        return user

    @transaction.atomic
    def hard_delete_user(
        self,
        user: User,
        deleted_by: User = None
    ) -> None:
        """
        Permanently delete a user.

        This should only be used for GDPR compliance or similar requirements.

        Args:
            user: User to delete
            deleted_by: User performing deletion
        """
        email = user.email
        user_id = user.id

        # Delete related data
        UserRole.objects.filter(user=user).delete()
        RefreshToken.objects.filter(user=user).delete()
        EmailVerificationToken.objects.filter(user=user).delete()

        # Delete user
        user.delete()

        # Audit log (create orphan log)
        AuditLog.log(
            action='hard_delete',
            entity_type='user',
            entity_id=user_id,
            entity_name=email,
            user=deleted_by,
            risk_level='critical',
            metadata={'permanent': True}
        )

        logger.warning(f"User permanently deleted: {email}")

    # ==================== STATUS MANAGEMENT ====================

    @transaction.atomic
    def activate_user(
        self,
        user: User,
        activated_by: User = None
    ) -> User:
        """Activate a user account."""
        old_status = user.status

        user.is_active = True
        user.status = User.Status.ACTIVE
        user.save(update_fields=['is_active', 'status', 'updated_at'])

        # Audit log
        AuditLog.log(
            action='activate',
            entity_type='user',
            entity_id=user.id,
            entity_name=user.email,
            user=activated_by,
            old_values={'status': old_status},
            new_values={'status': User.Status.ACTIVE},
            risk_level='low'
        )

        # Publish event
        self._publish_event('user.activated', {
            'user_id': str(user.id),
            'email': user.email
        })

        logger.info(f"User activated: {user.email}")
        return user

    @transaction.atomic
    def deactivate_user(
        self,
        user: User,
        deactivated_by: User = None,
        reason: str = None
    ) -> User:
        """Deactivate a user account."""
        old_status = user.status

        user.is_active = False
        user.status = User.Status.INACTIVE
        user.save(update_fields=['is_active', 'status', 'updated_at'])

        # Revoke all active tokens
        RefreshToken.revoke_all_for_user(user)

        # Audit log
        AuditLog.log(
            action='deactivate',
            entity_type='user',
            entity_id=user.id,
            entity_name=user.email,
            user=deactivated_by,
            old_values={'status': old_status},
            new_values={'status': User.Status.INACTIVE},
            risk_level='medium',
            metadata={'reason': reason}
        )

        # Publish event
        self._publish_event('user.deactivated', {
            'user_id': str(user.id),
            'email': user.email
        })

        logger.info(f"User deactivated: {user.email}")
        return user

    @transaction.atomic
    def suspend_user(
        self,
        user: User,
        suspended_by: User = None,
        reason: str = None,
        until: timezone.datetime = None
    ) -> User:
        """
        Suspend a user account.

        Args:
            user: User to suspend
            suspended_by: User performing suspension
            reason: Reason for suspension
            until: Suspension end date (None for indefinite)

        Returns:
            Suspended User object
        """
        old_status = user.status

        user.is_active = False
        user.status = User.Status.SUSPENDED
        user.save(update_fields=['is_active', 'status', 'updated_at'])

        # Revoke all active tokens
        RefreshToken.revoke_all_for_user(user)

        # Audit log
        AuditLog.log(
            action='suspend',
            entity_type='user',
            entity_id=user.id,
            entity_name=user.email,
            user=suspended_by,
            old_values={'status': old_status},
            new_values={'status': User.Status.SUSPENDED},
            risk_level='high',
            metadata={
                'reason': reason,
                'until': until.isoformat() if until else None
            }
        )

        # Publish event
        self._publish_event('user.suspended', {
            'user_id': str(user.id),
            'email': user.email,
            'reason': reason
        })

        logger.info(f"User suspended: {user.email}")
        return user

    @transaction.atomic
    def unsuspend_user(
        self,
        user: User,
        unsuspended_by: User = None
    ) -> User:
        """Unsuspend a previously suspended user."""
        if user.status != User.Status.SUSPENDED:
            return user

        user.is_active = True
        user.status = User.Status.ACTIVE
        user.save(update_fields=['is_active', 'status', 'updated_at'])

        # Audit log
        AuditLog.log(
            action='unsuspend',
            entity_type='user',
            entity_id=user.id,
            entity_name=user.email,
            user=unsuspended_by,
            old_values={'status': User.Status.SUSPENDED},
            new_values={'status': User.Status.ACTIVE},
            risk_level='medium'
        )

        logger.info(f"User unsuspended: {user.email}")
        return user

    def unlock_user(
        self,
        user: User,
        unlocked_by: User = None
    ) -> User:
        """Unlock a locked user account."""
        if not user.is_locked:
            return user

        user.locked_until = None
        user.failed_login_attempts = 0
        user.save(update_fields=['locked_until', 'failed_login_attempts', 'updated_at'])

        # Audit log
        AuditLog.log(
            action='unlock',
            entity_type='user',
            entity_id=user.id,
            entity_name=user.email,
            user=unlocked_by,
            risk_level='medium'
        )

        logger.info(f"User unlocked: {user.email}")
        return user

    # ==================== SEARCH & FILTERING ====================

    def list_users(
        self,
        organization_id: str = None,
        status: str = None,
        role_code: str = None,
        search: str = None,
        is_verified: bool = None,
        is_active: bool = None,
        ordering: str = '-created_at',
        page: int = 1,
        page_size: int = 20,
        include_deleted: bool = False
    ) -> Tuple[List[User], int]:
        """
        List users with filtering and pagination.

        Args:
            organization_id: Filter by organization
            status: Filter by status
            role_code: Filter by role
            search: Search in name, email
            is_verified: Filter by verification status
            is_active: Filter by active status
            ordering: Field to order by
            page: Page number
            page_size: Items per page
            include_deleted: Include soft-deleted users

        Returns:
            Tuple of (users list, total count)
        """
        query = User.objects.all()

        # Exclude deleted unless requested
        if not include_deleted:
            query = query.filter(deleted_at__isnull=True)

        # Apply filters
        if organization_id:
            query = query.filter(organization_id=organization_id)

        if status:
            query = query.filter(status=status)

        if is_verified is not None:
            query = query.filter(is_verified=is_verified)

        if is_active is not None:
            query = query.filter(is_active=is_active)

        if role_code:
            user_ids = UserRole.objects.filter(
                role__code=role_code,
                revoked_at__isnull=True
            ).values_list('user_id', flat=True)
            query = query.filter(id__in=user_ids)

        if search:
            query = query.filter(
                Q(email__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(username__icontains=search)
            )

        # Get total count
        total = query.count()

        # Apply ordering
        query = query.order_by(ordering)

        # Paginate
        paginator = Paginator(query, page_size)
        users = list(paginator.get_page(page))

        return users, total

    def search_users(
        self,
        query: str,
        organization_id: str = None,
        limit: int = 10
    ) -> List[User]:
        """
        Quick search for users (for autocomplete).

        Args:
            query: Search term
            organization_id: Limit to organization
            limit: Max results

        Returns:
            List of matching users
        """
        qs = User.objects.filter(
            deleted_at__isnull=True,
            is_active=True
        ).filter(
            Q(email__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query)
        )

        if organization_id:
            qs = qs.filter(organization_id=organization_id)

        return list(qs[:limit])

    def get_users_by_ids(
        self,
        user_ids: List[str],
        organization_id: str = None
    ) -> List[User]:
        """Get multiple users by their IDs."""
        query = User.objects.filter(
            id__in=user_ids,
            deleted_at__isnull=True
        )

        if organization_id:
            query = query.filter(organization_id=organization_id)

        return list(query)

    # ==================== ORGANIZATION MANAGEMENT ====================

    @transaction.atomic
    def change_organization(
        self,
        user: User,
        new_organization_id: str,
        changed_by: User = None,
        revoke_roles: bool = True
    ) -> User:
        """
        Move user to a different organization.

        Args:
            user: User to move
            new_organization_id: New organization ID
            changed_by: User making the change
            revoke_roles: Revoke organization-specific roles

        Returns:
            Updated User object
        """
        old_org_id = user.organization_id

        user.organization_id = new_organization_id
        user.save(update_fields=['organization_id', 'updated_at'])

        # Revoke organization-specific roles
        if revoke_roles and old_org_id:
            UserRole.objects.filter(
                user=user,
                role__organization_id=old_org_id,
                revoked_at__isnull=True
            ).update(
                revoked_at=timezone.now(),
                revoked_by=changed_by.id if changed_by else None
            )

        # Audit log
        AuditLog.log(
            action='change_organization',
            entity_type='user',
            entity_id=user.id,
            entity_name=user.email,
            user=changed_by,
            old_values={'organization_id': str(old_org_id) if old_org_id else None},
            new_values={'organization_id': str(new_organization_id)},
            risk_level='high'
        )

        # Publish event
        self._publish_event('user.organization_changed', {
            'user_id': str(user.id),
            'old_organization_id': str(old_org_id) if old_org_id else None,
            'new_organization_id': str(new_organization_id)
        })

        logger.info(f"User organization changed: {user.email}")
        return user

    # ==================== BULK OPERATIONS ====================

    @transaction.atomic
    def bulk_create_users(
        self,
        users_data: List[Dict],
        organization_id: str = None,
        created_by: User = None
    ) -> Tuple[List[User], List[Dict]]:
        """
        Create multiple users at once.

        Args:
            users_data: List of user data dicts
            organization_id: Default organization
            created_by: User creating the users

        Returns:
            Tuple of (created users, errors)
        """
        created = []
        errors = []

        for idx, data in enumerate(users_data):
            try:
                user = self.create_user(
                    organization_id=data.get('organization_id', organization_id),
                    created_by=created_by,
                    **data
                )
                created.append(user)
            except Exception as e:
                errors.append({
                    'index': idx,
                    'email': data.get('email'),
                    'error': str(e)
                })

        logger.info(f"Bulk create: {len(created)} created, {len(errors)} errors")
        return created, errors

    @transaction.atomic
    def bulk_update_status(
        self,
        user_ids: List[str],
        status: str,
        updated_by: User = None
    ) -> int:
        """
        Update status for multiple users.

        Args:
            user_ids: List of user IDs
            status: New status
            updated_by: User making the update

        Returns:
            Number of updated users
        """
        is_active = status == User.Status.ACTIVE

        count = User.objects.filter(
            id__in=user_ids,
            deleted_at__isnull=True
        ).update(
            status=status,
            is_active=is_active,
            updated_at=timezone.now()
        )

        # Audit log
        AuditLog.log(
            action='bulk_status_update',
            entity_type='user',
            entity_id=None,
            user=updated_by,
            risk_level='high',
            metadata={
                'user_count': count,
                'new_status': status
            }
        )

        logger.info(f"Bulk status update: {count} users updated to {status}")
        return count

    # ==================== STATISTICS ====================

    def get_user_statistics(
        self,
        organization_id: str = None
    ) -> Dict:
        """
        Get user statistics.

        Args:
            organization_id: Limit to organization

        Returns:
            Statistics dict
        """
        query = User.objects.filter(deleted_at__isnull=True)

        if organization_id:
            query = query.filter(organization_id=organization_id)

        stats = query.aggregate(
            total=Count('id'),
            active=Count('id', filter=Q(status=User.Status.ACTIVE)),
            pending=Count('id', filter=Q(status=User.Status.PENDING)),
            suspended=Count('id', filter=Q(status=User.Status.SUSPENDED)),
            inactive=Count('id', filter=Q(status=User.Status.INACTIVE)),
            verified=Count('id', filter=Q(is_verified=True)),
            with_2fa=Count('id', filter=Q(two_factor_enabled=True))
        )

        return stats

    # ==================== HELPER METHODS ====================

    def _assign_default_role(self, user: User) -> None:
        """Assign default role to new user."""
        try:
            # Try organization-specific default role
            default_role = None
            if user.organization_id:
                default_role = Role.objects.filter(
                    organization_id=user.organization_id,
                    is_default=True
                ).first()

            # Fall back to system default role
            if not default_role:
                default_role = Role.objects.filter(
                    is_system_role=True,
                    is_default=True
                ).first()

            if default_role:
                UserRole.objects.create(
                    user=user,
                    role=default_role
                )
                logger.debug(f"Default role assigned: {user.email}")

        except Exception as e:
            logger.warning(f"Failed to assign default role: {e}")

    def _publish_event(self, event_type: str, data: Dict) -> None:
        """Publish event to message bus."""
        try:
            from common.events import EventBus
            event_bus = EventBus()
            event_bus.publish(event_type, data)
        except Exception as e:
            logger.error(f"Failed to publish event {event_type}: {e}")

    # ==================== EMAIL MANAGEMENT ====================

    @transaction.atomic
    def change_email(
        self,
        user: User,
        new_email: str,
        changed_by: User = None
    ) -> str:
        """
        Initiate email change (requires verification).

        Args:
            user: User changing email
            new_email: New email address
            changed_by: User initiating change

        Returns:
            Verification token
        """
        # Check if email is already taken
        if User.objects.filter(email__iexact=new_email).exclude(id=user.id).exists():
            raise UserExistsError(new_email)

        # Create verification token for new email
        token = EmailVerificationToken.create_for_user(user, email=new_email)

        # Audit log
        AuditLog.log(
            action='email_change_requested',
            entity_type='user',
            entity_id=user.id,
            entity_name=user.email,
            user=changed_by,
            risk_level='medium',
            metadata={'new_email': new_email}
        )

        logger.info(f"Email change requested: {user.email} -> {new_email}")
        return token.token

    def confirm_email_change(
        self,
        token: str
    ) -> User:
        """
        Confirm email change with token.

        Args:
            token: Verification token

        Returns:
            Updated User object
        """
        try:
            token_obj = EmailVerificationToken.objects.select_related('user').get(
                token=token,
                is_used=False
            )
        except EmailVerificationToken.DoesNotExist:
            raise UserServiceError("Invalid or expired token", 'invalid_token')

        if token_obj.is_expired:
            raise UserServiceError("Token has expired", 'token_expired')

        user = token_obj.user
        old_email = user.email
        new_email = token_obj.email

        # Update email
        user.email = new_email
        user.username = new_email
        user.save(update_fields=['email', 'username', 'updated_at'])

        # Mark token as used
        token_obj.use()

        # Audit log
        AuditLog.log(
            action='email_changed',
            entity_type='user',
            entity_id=user.id,
            entity_name=user.email,
            user=user,
            old_values={'email': old_email},
            new_values={'email': new_email},
            risk_level='high'
        )

        logger.info(f"Email changed: {old_email} -> {new_email}")
        return user

    # ==================== AVATAR MANAGEMENT ====================

    def update_avatar(
        self,
        user: User,
        avatar_url: str,
        updated_by: User = None
    ) -> User:
        """
        Update user's avatar URL.

        Args:
            user: User to update
            avatar_url: New avatar URL
            updated_by: User making the update

        Returns:
            Updated User object
        """
        old_avatar = user.avatar_url
        user.avatar_url = avatar_url
        user.save(update_fields=['avatar_url', 'updated_at'])

        # Audit log
        AuditLog.log(
            action='avatar_updated',
            entity_type='user',
            entity_id=user.id,
            entity_name=user.email,
            user=updated_by,
            old_values={'avatar_url': old_avatar},
            new_values={'avatar_url': avatar_url},
            risk_level='low'
        )

        return user

    def remove_avatar(
        self,
        user: User,
        updated_by: User = None
    ) -> User:
        """Remove user's avatar."""
        return self.update_avatar(user, None, updated_by)
