import { HttpInterceptorFn, HttpRequest, HttpHandlerFn, HttpErrorResponse } from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError, switchMap, throwError } from 'rxjs';
import { AuthStore } from '../services/auth.store';

// Paths that don't require authentication
const PUBLIC_PATHS = [
  '/api/v1/auth/login',
  '/api/v1/auth/register',
  '/api/v1/auth/forgot-password',
  '/api/v1/auth/reset-password',
  '/api/v1/auth/refresh',
];

export const authInterceptor: HttpInterceptorFn = (
  req: HttpRequest<unknown>,
  next: HttpHandlerFn
) => {
  const authStore = inject(AuthStore);

  // Skip auth for public paths
  if (isPublicPath(req.url)) {
    return next(req);
  }

  // Add token to request
  const token = authStore.accessToken();
  if (token) {
    req = addToken(req, token);
  }

  return next(req).pipe(
    catchError((error: HttpErrorResponse) => {
      // Handle 401 - try to refresh token
      if (error.status === 401 && !isPublicPath(req.url)) {
        return handleUnauthorized(req, next, authStore);
      }
      return throwError(() => error);
    })
  );
};

function addToken(req: HttpRequest<unknown>, token: string): HttpRequest<unknown> {
  return req.clone({
    setHeaders: {
      Authorization: `Bearer ${token}`,
    },
  });
}

function isPublicPath(url: string): boolean {
  return PUBLIC_PATHS.some((path) => url.includes(path));
}

function handleUnauthorized(
  req: HttpRequest<unknown>,
  next: HttpHandlerFn,
  authStore: AuthStore
) {
  return new Promise<string | null>((resolve) => {
    authStore.refreshAccessToken().then(resolve);
  }).then((newToken) => {
    if (newToken) {
      // Retry with new token
      return next(addToken(req, newToken));
    }
    // Logout if refresh failed
    authStore.logout();
    return throwError(() => new HttpErrorResponse({ status: 401 }));
  });
}
