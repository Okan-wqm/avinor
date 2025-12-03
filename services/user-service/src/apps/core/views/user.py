# services/user-service/src/apps/core/views/user.py
"""
User ViewSet - Comprehensive user management API

Provides endpoints for:
- User CRUD operations
- Profile management
- User status management
- Bulk operations
- Search and filtering
"""

import logging
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q

from apps.core.models import User
from apps.core.serializers import (
    UserSerializer,
    UserListSerializer,
    UserSearchSerializer,
    UserCreateSerializer,
    UserUpdateSerializer,
    UserStatusUpdateSerializer,
    UserBulkActionSerializer,
    UserSessionSerializer,
    UserInviteSerializer,
    EmailChangeSerializer,
)
from apps.core.services import (
    UserService,
    UserServiceError,
    UserNotFoundError,
    UserExistsError,
    PermissionService,
    PermissionDeniedError,
)

logger = logging.getLogger(__name__)


class UserViewSet(viewsets.ModelViewSet):
    """
    ViewSet for User management.

    Endpoints:
    - GET /users/ - List users (paginated)
    - POST /users/ - Create user (admin)
    - GET /users/{id}/ - Get user details
    - PUT /users/{id}/ - Update user
    - PATCH /users/{id}/ - Partial update user
    - DELETE /users/{id}/ - Delete user (soft delete)
    - GET /users/me/ - Get current user
    - PUT /users/me/ - Update current user
    - GET /users/search/ - Search users
    - POST /users/{id}/activate/ - Activate user
    - POST /users/{id}/deactivate/ - Deactivate user
    - POST /users/{id}/suspend/ - Suspend user
    - POST /users/{id}/unlock/ - Unlock user
    - POST /users/bulk/ - Bulk actions
    - GET /users/{id}/permissions/ - Get user permissions
    - POST /users/invite/ - Invite user
    - POST /users/change-email/ - Change email
    - GET /users/statistics/ - Get user statistics
    """

    queryset = User.objects.filter(deleted_at__isnull=True)
    serializer_class = UserSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'is_active', 'organization_id', 'is_verified', 'two_factor_enabled']
    search_fields = ['email', 'username', 'first_name', 'last_name']
    ordering_fields = ['created_at', 'email', 'last_name', 'last_login']
    ordering = ['-created_at']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user_service = UserService()
        self.permission_service = PermissionService()

    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        if self.action in ['update', 'partial_update']:
            return UserUpdateSerializer
        if self.action == 'list':
            return UserListSerializer
        if self.action == 'search':
            return UserSearchSerializer
        return UserSerializer

    def get_permissions(self):
        if self.action in ['me', 'me_update', 'change_email']:
            return [IsAuthenticated()]
        if self.action in ['create', 'list', 'retrieve', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated()]
        return [IsAuthenticated()]

    def get_queryset(self):
        """Filter queryset based on user permissions."""
        queryset = super().get_queryset()
        user = self.request.user

        if not user.is_authenticated:
            return queryset.none()

        # Superusers see all
        if user.is_superuser:
            return queryset

        # Organization admins see their organization
        if hasattr(user, 'organization_id') and user.organization_id:
            if self.permission_service.has_permission(user, 'users.manage'):
                # Can see all in organization
                queryset = queryset.filter(organization_id=user.organization_id)
            elif self.permission_service.has_permission(user, 'users.read'):
                # Can see active users in organization
                queryset = queryset.filter(
                    organization_id=user.organization_id,
                    is_active=True
                )
            else:
                # Can only see themselves
                queryset = queryset.filter(id=user.id)
        else:
            # Users without organization can only see themselves
            queryset = queryset.filter(id=user.id)

        return queryset

    def _check_permission(self, permission_code: str, resource=None):
        """Check permission and raise 403 if denied."""
        if not self.permission_service.has_permission(
            self.request.user,
            permission_code,
            resource
        ):
            raise PermissionDeniedError(f"Permission '{permission_code}' required")

    def _error_response(self, error: Exception, status_code: int = 400) -> Response:
        """Create standardized error response."""
        if isinstance(error, UserServiceError):
            return Response({
                'success': False,
                'error': {
                    'code': error.code,
                    'message': error.message,
                    'details': error.details
                }
            }, status=status_code)

        if isinstance(error, PermissionDeniedError):
            return Response({
                'success': False,
                'error': {
                    'code': 'permission_denied',
                    'message': error.message
                }
            }, status=status.HTTP_403_FORBIDDEN)

        return Response({
            'success': False,
            'error': {
                'code': 'error',
                'message': str(error)
            }
        }, status=status_code)

    # ==================== CRUD OPERATIONS ====================

    def list(self, request, *args, **kwargs):
        """List users with pagination."""
        try:
            self._check_permission('users.read')
        except PermissionDeniedError as e:
            return self._error_response(e)

        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            response = self.get_paginated_response(serializer.data)
            response.data = {
                'success': True,
                'data': response.data
            }
            return response

        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'success': True,
            'data': serializer.data
        })

    def create(self, request, *args, **kwargs):
        """Create a new user (admin only)."""
        try:
            self._check_permission('users.create')
        except PermissionDeniedError as e:
            return self._error_response(e)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            data = serializer.validated_data
            data.pop('password_confirm', None)

            user = self.user_service.create_user(
                email=data['email'],
                first_name=data['first_name'],
                last_name=data['last_name'],
                organization_id=data.get('organization_id') or request.user.organization_id,
                created_by=request.user,
                password=data.get('password'),
                **{k: v for k, v in data.items() if k not in ['email', 'first_name', 'last_name', 'organization_id', 'password']}
            )

            output_serializer = UserSerializer(user)
            return Response({
                'success': True,
                'data': output_serializer.data,
                'message': 'User created successfully'
            }, status=status.HTTP_201_CREATED)

        except UserExistsError as e:
            return self._error_response(e, status.HTTP_409_CONFLICT)

        except UserServiceError as e:
            return self._error_response(e)

    def retrieve(self, request, *args, **kwargs):
        """Get user details."""
        instance = self.get_object()

        # Users can view their own profile, others need permission
        if str(instance.id) != str(request.user.id):
            try:
                self._check_permission('users.read', instance)
            except PermissionDeniedError as e:
                return self._error_response(e)

        serializer = self.get_serializer(instance)
        return Response({
            'success': True,
            'data': serializer.data
        })

    def update(self, request, *args, **kwargs):
        """Update user."""
        instance = self.get_object()
        partial = kwargs.pop('partial', False)

        # Users can update their own profile, others need permission
        if str(instance.id) != str(request.user.id):
            try:
                self._check_permission('users.update', instance)
            except PermissionDeniedError as e:
                return self._error_response(e)

        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        try:
            user = self.user_service.update_user(
                user=instance,
                updated_by=request.user,
                **serializer.validated_data
            )

            output_serializer = UserSerializer(user)
            return Response({
                'success': True,
                'data': output_serializer.data,
                'message': 'User updated successfully'
            })

        except UserServiceError as e:
            return self._error_response(e)

    def destroy(self, request, *args, **kwargs):
        """Soft delete user."""
        instance = self.get_object()

        try:
            self._check_permission('users.delete', instance)
        except PermissionDeniedError as e:
            return self._error_response(e)

        # Prevent self-deletion
        if str(instance.id) == str(request.user.id):
            return Response({
                'success': False,
                'error': {
                    'code': 'cannot_delete_self',
                    'message': 'You cannot delete your own account'
                }
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            self.user_service.soft_delete_user(
                user=instance,
                deleted_by=request.user,
                reason=request.data.get('reason')
            )

            return Response({
                'success': True,
                'message': 'User deleted successfully'
            })

        except UserServiceError as e:
            return self._error_response(e)

    # ==================== CURRENT USER ====================

    @action(detail=False, methods=['get'])
    def me(self, request):
        """Get current user's profile."""
        serializer = UserSerializer(request.user)
        return Response({
            'success': True,
            'data': serializer.data
        })

    @action(detail=False, methods=['put', 'patch'], url_path='me')
    def me_update(self, request):
        """Update current user's profile."""
        serializer = UserUpdateSerializer(
            request.user,
            data=request.data,
            partial=True
        )
        serializer.is_valid(raise_exception=True)

        try:
            user = self.user_service.update_user(
                user=request.user,
                updated_by=request.user,
                **serializer.validated_data
            )

            output_serializer = UserSerializer(user)
            return Response({
                'success': True,
                'data': output_serializer.data,
                'message': 'Profile updated successfully'
            })

        except UserServiceError as e:
            return self._error_response(e)

    # ==================== STATUS MANAGEMENT ====================

    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Activate a user account."""
        user = self.get_object()

        try:
            self._check_permission('users.manage', user)
        except PermissionDeniedError as e:
            return self._error_response(e)

        try:
            self.user_service.activate_user(user, activated_by=request.user)

            return Response({
                'success': True,
                'message': 'User activated successfully'
            })

        except UserServiceError as e:
            return self._error_response(e)

    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """Deactivate a user account."""
        user = self.get_object()

        try:
            self._check_permission('users.manage', user)
        except PermissionDeniedError as e:
            return self._error_response(e)

        # Prevent self-deactivation
        if str(user.id) == str(request.user.id):
            return Response({
                'success': False,
                'error': {
                    'code': 'cannot_deactivate_self',
                    'message': 'You cannot deactivate your own account'
                }
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            self.user_service.deactivate_user(
                user=user,
                deactivated_by=request.user,
                reason=request.data.get('reason')
            )

            return Response({
                'success': True,
                'message': 'User deactivated successfully'
            })

        except UserServiceError as e:
            return self._error_response(e)

    @action(detail=True, methods=['post'])
    def suspend(self, request, pk=None):
        """Suspend a user account."""
        user = self.get_object()

        try:
            self._check_permission('users.manage', user)
        except PermissionDeniedError as e:
            return self._error_response(e)

        try:
            self.user_service.suspend_user(
                user=user,
                suspended_by=request.user,
                reason=request.data.get('reason'),
                until=request.data.get('until')
            )

            return Response({
                'success': True,
                'message': 'User suspended successfully'
            })

        except UserServiceError as e:
            return self._error_response(e)

    @action(detail=True, methods=['post'])
    def unsuspend(self, request, pk=None):
        """Unsuspend a user account."""
        user = self.get_object()

        try:
            self._check_permission('users.manage', user)
        except PermissionDeniedError as e:
            return self._error_response(e)

        try:
            self.user_service.unsuspend_user(user, unsuspended_by=request.user)

            return Response({
                'success': True,
                'message': 'User unsuspended successfully'
            })

        except UserServiceError as e:
            return self._error_response(e)

    @action(detail=True, methods=['post'])
    def unlock(self, request, pk=None):
        """Unlock a locked user account."""
        user = self.get_object()

        try:
            self._check_permission('users.manage', user)
        except PermissionDeniedError as e:
            return self._error_response(e)

        try:
            self.user_service.unlock_user(user, unlocked_by=request.user)

            return Response({
                'success': True,
                'message': 'User account unlocked successfully'
            })

        except UserServiceError as e:
            return self._error_response(e)

    # ==================== SEARCH & BULK ====================

    @action(detail=False, methods=['get'])
    def search(self, request):
        """Quick search for users (autocomplete)."""
        query = request.query_params.get('q', '')
        limit = min(int(request.query_params.get('limit', 10)), 50)

        if len(query) < 2:
            return Response({
                'success': True,
                'data': []
            })

        users = self.user_service.search_users(
            query=query,
            organization_id=request.user.organization_id if hasattr(request.user, 'organization_id') else None,
            limit=limit
        )

        serializer = UserSearchSerializer(users, many=True)
        return Response({
            'success': True,
            'data': serializer.data
        })

    @action(detail=False, methods=['post'])
    def bulk(self, request):
        """Perform bulk actions on users."""
        try:
            self._check_permission('users.manage')
        except PermissionDeniedError as e:
            return self._error_response(e)

        serializer = UserBulkActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        action = serializer.validated_data['action']
        user_ids = serializer.validated_data['user_ids']

        # Prevent bulk actions on self
        if str(request.user.id) in [str(uid) for uid in user_ids]:
            return Response({
                'success': False,
                'error': {
                    'code': 'cannot_bulk_self',
                    'message': 'You cannot perform bulk actions on your own account'
                }
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            if action == 'activate':
                count = self.user_service.bulk_update_status(
                    user_ids=user_ids,
                    status=User.Status.ACTIVE,
                    updated_by=request.user
                )
            elif action == 'deactivate':
                count = self.user_service.bulk_update_status(
                    user_ids=user_ids,
                    status=User.Status.INACTIVE,
                    updated_by=request.user
                )
            elif action == 'suspend':
                count = self.user_service.bulk_update_status(
                    user_ids=user_ids,
                    status=User.Status.SUSPENDED,
                    updated_by=request.user
                )
            elif action == 'delete':
                count = 0
                for user_id in user_ids:
                    try:
                        user = User.objects.get(id=user_id)
                        self.user_service.soft_delete_user(
                            user=user,
                            deleted_by=request.user,
                            reason=serializer.validated_data.get('reason')
                        )
                        count += 1
                    except User.DoesNotExist:
                        pass
            else:
                return Response({
                    'success': False,
                    'error': {'message': f'Unknown action: {action}'}
                }, status=status.HTTP_400_BAD_REQUEST)

            return Response({
                'success': True,
                'data': {'affected_count': count},
                'message': f'{count} user(s) updated'
            })

        except UserServiceError as e:
            return self._error_response(e)

    # ==================== PERMISSIONS ====================

    @action(detail=True, methods=['get'])
    def permissions(self, request, pk=None):
        """Get user's roles and permissions."""
        user = self.get_object()

        # Users can view their own permissions, others need permission
        if str(user.id) != str(request.user.id):
            try:
                self._check_permission('users.read', user)
            except PermissionDeniedError as e:
                return self._error_response(e)

        roles = self.permission_service.get_user_roles(user)
        permissions = list(self.permission_service.get_user_permissions(user))

        return Response({
            'success': True,
            'data': {
                'roles': roles,
                'permissions': permissions
            }
        })

    # ==================== INVITE & EMAIL ====================

    @action(detail=False, methods=['post'])
    def invite(self, request):
        """Invite a new user via email."""
        try:
            self._check_permission('users.create')
        except PermissionDeniedError as e:
            return self._error_response(e)

        serializer = UserInviteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            user = self.user_service.create_user(
                email=serializer.validated_data['email'],
                first_name=serializer.validated_data['first_name'],
                last_name=serializer.validated_data['last_name'],
                organization_id=request.user.organization_id,
                created_by=request.user,
                send_verification=True
            )

            # TODO: Send invitation email via notification service

            return Response({
                'success': True,
                'data': {
                    'user_id': str(user.id),
                    'email': user.email
                },
                'message': 'Invitation sent successfully'
            }, status=status.HTTP_201_CREATED)

        except UserExistsError as e:
            return self._error_response(e, status.HTTP_409_CONFLICT)

        except UserServiceError as e:
            return self._error_response(e)

    @action(detail=False, methods=['post'], url_path='change-email')
    def change_email(self, request):
        """Request email change for current user."""
        serializer = EmailChangeSerializer(
            data=request.data,
            context={'user': request.user}
        )
        serializer.is_valid(raise_exception=True)

        try:
            token = self.user_service.change_email(
                user=request.user,
                new_email=serializer.validated_data['new_email'],
                changed_by=request.user
            )

            # TODO: Send confirmation email to new address

            return Response({
                'success': True,
                'message': 'Verification email sent to new address. Please check your email.'
            })

        except UserExistsError as e:
            return self._error_response(e, status.HTTP_409_CONFLICT)

        except UserServiceError as e:
            return self._error_response(e)

    # ==================== STATISTICS ====================

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get user statistics."""
        try:
            self._check_permission('users.read')
        except PermissionDeniedError as e:
            return self._error_response(e)

        organization_id = None
        if not request.user.is_superuser and hasattr(request.user, 'organization_id'):
            organization_id = request.user.organization_id

        stats = self.user_service.get_user_statistics(organization_id)

        return Response({
            'success': True,
            'data': stats
        })
