# services/user-service/src/apps/core/views/role.py
"""
Role and Permission ViewSets - RBAC management API

Provides endpoints for:
- Role CRUD operations
- Permission management
- User-role assignments
- Audit log viewing
"""

import logging
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend

from apps.core.models import User, Role, Permission, UserRole, AuditLog
from apps.core.serializers import (
    # Role serializers
    RoleSerializer,
    RoleListSerializer,
    RoleCreateSerializer,
    RoleUpdateSerializer,
    RolePermissionAssignSerializer,
    RolePermissionBulkSerializer,
    # Permission serializers
    PermissionSerializer,
    PermissionListSerializer,
    PermissionCreateSerializer,
    # User role serializers
    UserRoleSerializer,
    UserRoleAssignSerializer,
    UserRoleBulkAssignSerializer,
    UserRoleRevokeSerializer,
    # Audit serializers
    AuditLogSerializer,
    AuditLogListSerializer,
    AuditLogFilterSerializer,
    # User serializers
    UserListSerializer,
)
from apps.core.services import (
    PermissionService,
    PermissionDeniedError,
)

logger = logging.getLogger(__name__)


class PermissionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Permission management.

    Endpoints:
    - GET /permissions/ - List permissions
    - POST /permissions/ - Create permission (superadmin)
    - GET /permissions/{id}/ - Get permission details
    - GET /permissions/modules/ - Get permission modules
    """

    queryset = Permission.objects.all()
    serializer_class = PermissionSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['module', 'action', 'is_sensitive']
    search_fields = ['code', 'name', 'description']
    ordering_fields = ['module', 'action', 'code']
    ordering = ['module', 'action', 'code']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.permission_service = PermissionService()

    def get_serializer_class(self):
        if self.action == 'list':
            return PermissionListSerializer
        if self.action == 'create':
            return PermissionCreateSerializer
        return PermissionSerializer

    def _check_permission(self, permission_code: str):
        """Check permission and raise 403 if denied."""
        if not self.permission_service.has_permission(
            self.request.user,
            permission_code
        ):
            raise PermissionDeniedError(f"Permission '{permission_code}' required")

    def list(self, request, *args, **kwargs):
        """List all permissions."""
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)

        return Response({
            'success': True,
            'data': serializer.data
        })

    def create(self, request, *args, **kwargs):
        """Create a new permission (superadmin only)."""
        if not request.user.is_superuser:
            return Response({
                'success': False,
                'error': {
                    'code': 'permission_denied',
                    'message': 'Only superadmins can create permissions'
                }
            }, status=status.HTTP_403_FORBIDDEN)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            permission = self.permission_service.create_permission(
                created_by=request.user,
                **serializer.validated_data
            )

            output_serializer = PermissionSerializer(permission)
            return Response({
                'success': True,
                'data': output_serializer.data,
                'message': 'Permission created successfully'
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({
                'success': False,
                'error': {'message': str(e)}
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def modules(self, request):
        """Get list of permission modules."""
        modules = self.permission_service.get_permission_modules()

        return Response({
            'success': True,
            'data': modules
        })

    @action(detail=False, methods=['post'], url_path='seed')
    def seed_defaults(self, request):
        """Seed default permissions (superadmin only)."""
        if not request.user.is_superuser:
            return Response({
                'success': False,
                'error': {
                    'code': 'permission_denied',
                    'message': 'Only superadmins can seed permissions'
                }
            }, status=status.HTTP_403_FORBIDDEN)

        permissions = self.permission_service.seed_default_permissions()

        return Response({
            'success': True,
            'data': {'created_count': len(permissions)},
            'message': f'Created {len(permissions)} permissions'
        })


class RoleViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Role management.

    Endpoints:
    - GET /roles/ - List roles
    - POST /roles/ - Create role
    - GET /roles/{id}/ - Get role details
    - PUT /roles/{id}/ - Update role
    - DELETE /roles/{id}/ - Delete role
    - GET /roles/{id}/permissions/ - Get role permissions
    - POST /roles/{id}/permissions/ - Add permission to role
    - DELETE /roles/{id}/permissions/ - Remove permission from role
    - POST /roles/{id}/permissions/bulk/ - Bulk permission operations
    - GET /roles/{id}/users/ - Get users with role
    - POST /roles/assign/ - Assign role to user
    - POST /roles/revoke/ - Revoke role from user
    - POST /roles/bulk-assign/ - Bulk assign role
    """

    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['organization_id', 'is_system_role', 'is_default']
    search_fields = ['code', 'name', 'description']
    ordering_fields = ['priority', 'name', 'created_at']
    ordering = ['-priority', 'name']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.permission_service = PermissionService()

    def get_serializer_class(self):
        if self.action == 'list':
            return RoleListSerializer
        if self.action == 'create':
            return RoleCreateSerializer
        if self.action in ['update', 'partial_update']:
            return RoleUpdateSerializer
        return RoleSerializer

    def get_queryset(self):
        """Filter roles based on user permissions."""
        queryset = super().get_queryset()
        user = self.request.user

        if not user.is_authenticated:
            return queryset.none()

        # Superusers see all
        if user.is_superuser:
            return queryset

        # Others see system roles + their organization's roles
        if hasattr(user, 'organization_id') and user.organization_id:
            from django.db.models import Q
            queryset = queryset.filter(
                Q(is_system_role=True) | Q(organization_id=user.organization_id)
            )
        else:
            queryset = queryset.filter(is_system_role=True)

        return queryset

    def _check_permission(self, permission_code: str):
        """Check permission and raise 403 if denied."""
        if not self.permission_service.has_permission(
            self.request.user,
            permission_code
        ):
            raise PermissionDeniedError(f"Permission '{permission_code}' required")

    def list(self, request, *args, **kwargs):
        """List roles."""
        try:
            self._check_permission('roles.read')
        except PermissionDeniedError:
            return Response({
                'success': False,
                'error': {'code': 'permission_denied', 'message': 'Permission required'}
            }, status=status.HTTP_403_FORBIDDEN)

        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)

        return Response({
            'success': True,
            'data': serializer.data
        })

    def retrieve(self, request, *args, **kwargs):
        """Get role details."""
        try:
            self._check_permission('roles.read')
        except PermissionDeniedError:
            return Response({
                'success': False,
                'error': {'code': 'permission_denied', 'message': 'Permission required'}
            }, status=status.HTTP_403_FORBIDDEN)

        instance = self.get_object()
        serializer = RoleSerializer(instance)

        return Response({
            'success': True,
            'data': serializer.data
        })

    def create(self, request, *args, **kwargs):
        """Create a new role."""
        try:
            self._check_permission('roles.create')
        except PermissionDeniedError:
            return Response({
                'success': False,
                'error': {'code': 'permission_denied', 'message': 'Permission required'}
            }, status=status.HTTP_403_FORBIDDEN)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            data = serializer.validated_data
            permissions = data.pop('permissions', [])

            role = self.permission_service.create_role(
                created_by=request.user,
                permissions=permissions,
                **data
            )

            output_serializer = RoleSerializer(role)
            return Response({
                'success': True,
                'data': output_serializer.data,
                'message': 'Role created successfully'
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({
                'success': False,
                'error': {'message': str(e)}
            }, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        """Update a role."""
        try:
            self._check_permission('roles.update')
        except PermissionDeniedError:
            return Response({
                'success': False,
                'error': {'code': 'permission_denied', 'message': 'Permission required'}
            }, status=status.HTTP_403_FORBIDDEN)

        instance = self.get_object()
        partial = kwargs.pop('partial', False)
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        try:
            role = self.permission_service.update_role(
                role=instance,
                updated_by=request.user,
                **serializer.validated_data
            )

            output_serializer = RoleSerializer(role)
            return Response({
                'success': True,
                'data': output_serializer.data,
                'message': 'Role updated successfully'
            })

        except PermissionDeniedError as e:
            return Response({
                'success': False,
                'error': {'code': 'permission_denied', 'message': str(e)}
            }, status=status.HTTP_403_FORBIDDEN)

        except Exception as e:
            return Response({
                'success': False,
                'error': {'message': str(e)}
            }, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        """Delete a role."""
        try:
            self._check_permission('roles.delete')
        except PermissionDeniedError:
            return Response({
                'success': False,
                'error': {'code': 'permission_denied', 'message': 'Permission required'}
            }, status=status.HTTP_403_FORBIDDEN)

        instance = self.get_object()

        try:
            self.permission_service.delete_role(
                role=instance,
                deleted_by=request.user
            )

            return Response({
                'success': True,
                'message': 'Role deleted successfully'
            })

        except PermissionDeniedError as e:
            return Response({
                'success': False,
                'error': {'code': 'permission_denied', 'message': str(e)}
            }, status=status.HTTP_403_FORBIDDEN)

        except Exception as e:
            return Response({
                'success': False,
                'error': {'message': str(e)}
            }, status=status.HTTP_400_BAD_REQUEST)

    # ==================== PERMISSIONS ====================

    @action(detail=True, methods=['get', 'post', 'delete'])
    def permissions(self, request, pk=None):
        """Manage role permissions."""
        role = self.get_object()

        if request.method == 'GET':
            # Get permissions
            perms = self.permission_service.get_role_permissions(role)
            return Response({
                'success': True,
                'data': perms
            })

        elif request.method == 'POST':
            # Add permission
            try:
                self._check_permission('roles.update')
            except PermissionDeniedError:
                return Response({
                    'success': False,
                    'error': {'code': 'permission_denied', 'message': 'Permission required'}
                }, status=status.HTTP_403_FORBIDDEN)

            serializer = RolePermissionAssignSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            try:
                self.permission_service.assign_permission_to_role(
                    role=role,
                    permission_code=serializer.validated_data['permission_code'],
                    conditions=serializer.validated_data.get('conditions'),
                    assigned_by=request.user
                )

                return Response({
                    'success': True,
                    'message': 'Permission added to role'
                })

            except Exception as e:
                return Response({
                    'success': False,
                    'error': {'message': str(e)}
                }, status=status.HTTP_400_BAD_REQUEST)

        elif request.method == 'DELETE':
            # Remove permission
            try:
                self._check_permission('roles.update')
            except PermissionDeniedError:
                return Response({
                    'success': False,
                    'error': {'code': 'permission_denied', 'message': 'Permission required'}
                }, status=status.HTTP_403_FORBIDDEN)

            permission_code = request.data.get('permission_code')
            if not permission_code:
                return Response({
                    'success': False,
                    'error': {'message': 'permission_code is required'}
                }, status=status.HTTP_400_BAD_REQUEST)

            try:
                self.permission_service.revoke_permission_from_role(
                    role=role,
                    permission_code=permission_code,
                    revoked_by=request.user
                )

                return Response({
                    'success': True,
                    'message': 'Permission removed from role'
                })

            except Exception as e:
                return Response({
                    'success': False,
                    'error': {'message': str(e)}
                }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='permissions/bulk')
    def permissions_bulk(self, request, pk=None):
        """Bulk permission operations."""
        try:
            self._check_permission('roles.update')
        except PermissionDeniedError:
            return Response({
                'success': False,
                'error': {'code': 'permission_denied', 'message': 'Permission required'}
            }, status=status.HTTP_403_FORBIDDEN)

        role = self.get_object()
        serializer = RolePermissionBulkSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        action = serializer.validated_data['action']
        permissions = serializer.validated_data['permissions']

        try:
            if action == 'add':
                for perm_code in permissions:
                    self.permission_service.assign_permission_to_role(
                        role=role,
                        permission_code=perm_code,
                        assigned_by=request.user
                    )
            elif action == 'remove':
                for perm_code in permissions:
                    self.permission_service.revoke_permission_from_role(
                        role=role,
                        permission_code=perm_code,
                        revoked_by=request.user
                    )
            elif action == 'set':
                # Remove all and add new
                from apps.core.models import RolePermission
                RolePermission.objects.filter(role=role).delete()
                for perm_code in permissions:
                    self.permission_service.assign_permission_to_role(
                        role=role,
                        permission_code=perm_code,
                        assigned_by=request.user
                    )

            return Response({
                'success': True,
                'message': f'Permissions updated ({action}: {len(permissions)})'
            })

        except Exception as e:
            return Response({
                'success': False,
                'error': {'message': str(e)}
            }, status=status.HTTP_400_BAD_REQUEST)

    # ==================== USERS ====================

    @action(detail=True, methods=['get'])
    def users(self, request, pk=None):
        """Get users with this role."""
        role = self.get_object()
        users = self.permission_service.get_users_with_role(
            role=role,
            organization_id=request.user.organization_id if hasattr(request.user, 'organization_id') else None
        )

        serializer = UserListSerializer(users, many=True)
        return Response({
            'success': True,
            'data': serializer.data
        })

    # ==================== ASSIGNMENT ====================

    @action(detail=False, methods=['post'])
    def assign(self, request):
        """Assign role to user."""
        try:
            self._check_permission('roles.assign')
        except PermissionDeniedError:
            return Response({
                'success': False,
                'error': {'code': 'permission_denied', 'message': 'Permission required'}
            }, status=status.HTTP_403_FORBIDDEN)

        serializer = UserRoleAssignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            data = serializer.validated_data
            user = User.objects.get(id=data['user_id'])

            # Get role by ID or code
            if data.get('role_id'):
                role = Role.objects.get(id=data['role_id'])
            else:
                role = Role.objects.get(code=data['role_code'])

            self.permission_service.assign_role_to_user(
                user=user,
                role=role,
                valid_from=data.get('valid_from'),
                valid_until=data.get('valid_until'),
                location_id=data.get('location_id'),
                conditions=data.get('conditions'),
                assigned_by=request.user
            )

            return Response({
                'success': True,
                'message': f'Role "{role.name}" assigned to user'
            })

        except User.DoesNotExist:
            return Response({
                'success': False,
                'error': {'message': 'User not found'}
            }, status=status.HTTP_404_NOT_FOUND)

        except Role.DoesNotExist:
            return Response({
                'success': False,
                'error': {'message': 'Role not found'}
            }, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            return Response({
                'success': False,
                'error': {'message': str(e)}
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def revoke(self, request):
        """Revoke role from user."""
        try:
            self._check_permission('roles.assign')
        except PermissionDeniedError:
            return Response({
                'success': False,
                'error': {'code': 'permission_denied', 'message': 'Permission required'}
            }, status=status.HTTP_403_FORBIDDEN)

        serializer = UserRoleRevokeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            data = serializer.validated_data
            user = User.objects.get(id=data['user_id'])

            # Get role by ID or code
            if data.get('role_id'):
                role = Role.objects.get(id=data['role_id'])
            else:
                role = Role.objects.get(code=data['role_code'])

            self.permission_service.revoke_role_from_user(
                user=user,
                role=role,
                location_id=data.get('location_id'),
                revoked_by=request.user
            )

            return Response({
                'success': True,
                'message': f'Role "{role.name}" revoked from user'
            })

        except User.DoesNotExist:
            return Response({
                'success': False,
                'error': {'message': 'User not found'}
            }, status=status.HTTP_404_NOT_FOUND)

        except Role.DoesNotExist:
            return Response({
                'success': False,
                'error': {'message': 'Role not found'}
            }, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            return Response({
                'success': False,
                'error': {'message': str(e)}
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], url_path='bulk-assign')
    def bulk_assign(self, request):
        """Bulk assign role to multiple users."""
        try:
            self._check_permission('roles.assign')
        except PermissionDeniedError:
            return Response({
                'success': False,
                'error': {'code': 'permission_denied', 'message': 'Permission required'}
            }, status=status.HTTP_403_FORBIDDEN)

        serializer = UserRoleBulkAssignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            data = serializer.validated_data

            # Get role
            if data.get('role_id'):
                role = Role.objects.get(id=data['role_id'])
            else:
                role = Role.objects.get(code=data['role_code'])

            count = 0
            for user_id in data['user_ids']:
                try:
                    user = User.objects.get(id=user_id)
                    self.permission_service.assign_role_to_user(
                        user=user,
                        role=role,
                        valid_until=data.get('valid_until'),
                        assigned_by=request.user
                    )
                    count += 1
                except User.DoesNotExist:
                    pass

            return Response({
                'success': True,
                'data': {'assigned_count': count},
                'message': f'Role assigned to {count} user(s)'
            })

        except Role.DoesNotExist:
            return Response({
                'success': False,
                'error': {'message': 'Role not found'}
            }, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            return Response({
                'success': False,
                'error': {'message': str(e)}
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], url_path='seed')
    def seed_defaults(self, request):
        """Seed default roles (superadmin only)."""
        if not request.user.is_superuser:
            return Response({
                'success': False,
                'error': {
                    'code': 'permission_denied',
                    'message': 'Only superadmins can seed roles'
                }
            }, status=status.HTTP_403_FORBIDDEN)

        roles = self.permission_service.seed_default_roles()

        return Response({
            'success': True,
            'data': {'created_count': len(roles)},
            'message': f'Created {len(roles)} roles'
        })


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing audit logs.

    Endpoints:
    - GET /audit-logs/ - List audit logs
    - GET /audit-logs/{id}/ - Get audit log details
    """

    queryset = AuditLog.objects.all()
    serializer_class = AuditLogSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['user_id', 'entity_type', 'action', 'risk_level']
    ordering_fields = ['created_at']
    ordering = ['-created_at']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.permission_service = PermissionService()

    def get_serializer_class(self):
        if self.action == 'list':
            return AuditLogListSerializer
        return AuditLogSerializer

    def get_queryset(self):
        """Filter audit logs based on user permissions."""
        queryset = super().get_queryset()
        user = self.request.user

        if not user.is_authenticated:
            return queryset.none()

        # Superusers see all
        if user.is_superuser:
            return queryset

        # Organization admins see their organization
        if hasattr(user, 'organization_id') and user.organization_id:
            if self.permission_service.has_permission(user, 'audit.view'):
                queryset = queryset.filter(organization_id=user.organization_id)
            else:
                # Users can only see their own logs
                queryset = queryset.filter(user_id=user.id)
        else:
            queryset = queryset.filter(user_id=user.id)

        return queryset

    def list(self, request, *args, **kwargs):
        """List audit logs."""
        queryset = self.filter_queryset(self.get_queryset())

        # Additional filters from query params
        filter_serializer = AuditLogFilterSerializer(data=request.query_params)
        if filter_serializer.is_valid():
            filters = filter_serializer.validated_data
            if filters.get('entity_id'):
                queryset = queryset.filter(entity_id=filters['entity_id'])
            if filters.get('start_date'):
                queryset = queryset.filter(created_at__gte=filters['start_date'])
            if filters.get('end_date'):
                queryset = queryset.filter(created_at__lte=filters['end_date'])
            if filters.get('ip_address'):
                queryset = queryset.filter(ip_address=filters['ip_address'])

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

    def retrieve(self, request, *args, **kwargs):
        """Get audit log details."""
        instance = self.get_object()
        serializer = self.get_serializer(instance)

        return Response({
            'success': True,
            'data': serializer.data
        })
