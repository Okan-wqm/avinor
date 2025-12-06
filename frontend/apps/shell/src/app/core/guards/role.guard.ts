// apps/shell/src/app/core/guards/role.guard.ts
/**
 * Role Guard
 *
 * Restricts access to routes based on user roles.
 * Requires route data to specify allowed roles.
 */

import { inject } from '@angular/core';
import { Router, CanActivateFn, ActivatedRouteSnapshot, RouterStateSnapshot } from '@angular/router';
import { AuthStore } from '../services/auth.store';

/**
 * Functional guard that checks if user has required roles.
 *
 * Usage in routes:
 * {
 *   path: 'admin',
 *   loadChildren: ...,
 *   canActivate: [roleGuard],
 *   data: { roles: ['admin', 'super_admin'] }
 * }
 */
export const roleGuard: CanActivateFn = (
  route: ActivatedRouteSnapshot,
  state: RouterStateSnapshot
): boolean => {
  const authStore = inject(AuthStore);
  const router = inject(Router);

  // First check if authenticated
  if (!authStore.isAuthenticated()) {
    router.navigate(['/auth/login'], {
      queryParams: { returnUrl: state.url },
    });
    return false;
  }

  // Get required roles from route data
  const requiredRoles: string[] = route.data['roles'] || [];

  // If no roles specified, allow access (just auth check)
  if (requiredRoles.length === 0) {
    return true;
  }

  // Check if user has any of the required roles
  const userRoles = authStore.roles();
  const hasRequiredRole = requiredRoles.some((role) => userRoles.includes(role));

  if (hasRequiredRole) {
    return true;
  }

  // User doesn't have required role, redirect to dashboard with error
  router.navigate(['/dashboard'], {
    queryParams: { error: 'unauthorized' },
  });

  return false;
};

/**
 * Permission Guard
 *
 * More granular access control based on specific permissions.
 *
 * Usage in routes:
 * {
 *   path: 'users',
 *   loadChildren: ...,
 *   canActivate: [permissionGuard],
 *   data: { permissions: ['users:read', 'users:write'] }
 * }
 */
export const permissionGuard: CanActivateFn = (
  route: ActivatedRouteSnapshot,
  state: RouterStateSnapshot
): boolean => {
  const authStore = inject(AuthStore);
  const router = inject(Router);

  // First check if authenticated
  if (!authStore.isAuthenticated()) {
    router.navigate(['/auth/login'], {
      queryParams: { returnUrl: state.url },
    });
    return false;
  }

  // Get required permissions from route data
  const requiredPermissions: string[] = route.data['permissions'] || [];

  // If no permissions specified, allow access
  if (requiredPermissions.length === 0) {
    return true;
  }

  // Check if user has all required permissions
  const hasAllPermissions = requiredPermissions.every((permission) =>
    authStore.hasPermission(permission)
  );

  if (hasAllPermissions) {
    return true;
  }

  // User doesn't have required permissions
  router.navigate(['/dashboard'], {
    queryParams: { error: 'forbidden' },
  });

  return false;
};
