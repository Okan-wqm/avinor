// apps/shell/src/app/core/guards/auth.guard.ts
/**
 * Authentication Guard
 *
 * Protects routes that require authentication.
 * Redirects unauthenticated users to login page.
 */

import { inject } from '@angular/core';
import { Router, CanActivateFn, ActivatedRouteSnapshot, RouterStateSnapshot } from '@angular/router';
import { AuthStore } from '../services/auth.store';

/**
 * Functional guard that checks if user is authenticated.
 * Uses Angular 15+ functional guard pattern for better tree-shaking.
 */
export const authGuard: CanActivateFn = (
  route: ActivatedRouteSnapshot,
  state: RouterStateSnapshot
): boolean => {
  const authStore = inject(AuthStore);
  const router = inject(Router);

  if (authStore.isAuthenticated()) {
    return true;
  }

  // Store the attempted URL for redirecting after login
  const returnUrl = state.url;

  // Redirect to login with return URL
  router.navigate(['/auth/login'], {
    queryParams: { returnUrl },
  });

  return false;
};
