// apps/shell/src/app/core/guards/no-auth.guard.ts
/**
 * No Authentication Guard
 *
 * Prevents authenticated users from accessing auth pages (login, register).
 * Redirects authenticated users to dashboard.
 */

import { inject } from '@angular/core';
import { Router, CanActivateFn, ActivatedRouteSnapshot, RouterStateSnapshot } from '@angular/router';
import { AuthStore } from '../services/auth.store';

/**
 * Functional guard that checks if user is NOT authenticated.
 * Used for login/register pages to redirect already logged-in users.
 */
export const noAuthGuard: CanActivateFn = (
  route: ActivatedRouteSnapshot,
  state: RouterStateSnapshot
): boolean => {
  const authStore = inject(AuthStore);
  const router = inject(Router);

  if (!authStore.isAuthenticated()) {
    return true;
  }

  // User is already authenticated, redirect to dashboard
  router.navigate(['/dashboard']);
  return false;
};
