// apps/shell/src/app/core/guards/auth.guard.spec.ts
/**
 * Auth Guard Tests
 *
 * Tests for the authentication route guard.
 */

import { TestBed } from '@angular/core/testing';
import { Router, ActivatedRouteSnapshot, RouterStateSnapshot } from '@angular/router';
import { authGuard } from './auth.guard';
import { AuthStore } from '../services/auth.store';
import { HttpClientTestingModule } from '@angular/common/http/testing';

describe('authGuard', () => {
  let router: Router;
  let authStore: AuthStore;
  let mockRoute: ActivatedRouteSnapshot;
  let mockState: RouterStateSnapshot;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [
        AuthStore,
        {
          provide: Router,
          useValue: {
            navigate: jest.fn(),
          },
        },
      ],
    });

    router = TestBed.inject(Router);
    authStore = TestBed.inject(AuthStore);

    mockRoute = {} as ActivatedRouteSnapshot;
    mockState = { url: '/dashboard' } as RouterStateSnapshot;
  });

  it('should allow access when user is authenticated', () => {
    // Arrange: Mock authenticated state
    jest.spyOn(authStore, 'isAuthenticated').mockReturnValue(true);

    // Act
    const result = TestBed.runInInjectionContext(() =>
      authGuard(mockRoute, mockState)
    );

    // Assert
    expect(result).toBe(true);
    expect(router.navigate).not.toHaveBeenCalled();
  });

  it('should deny access and redirect to login when user is not authenticated', () => {
    // Arrange: Mock unauthenticated state
    jest.spyOn(authStore, 'isAuthenticated').mockReturnValue(false);

    // Act
    const result = TestBed.runInInjectionContext(() =>
      authGuard(mockRoute, mockState)
    );

    // Assert
    expect(result).toBe(false);
    expect(router.navigate).toHaveBeenCalledWith(['/auth/login'], {
      queryParams: { returnUrl: '/dashboard' },
    });
  });

  it('should pass the correct return URL to login', () => {
    // Arrange
    jest.spyOn(authStore, 'isAuthenticated').mockReturnValue(false);
    mockState = { url: '/admin/users' } as RouterStateSnapshot;

    // Act
    TestBed.runInInjectionContext(() => authGuard(mockRoute, mockState));

    // Assert
    expect(router.navigate).toHaveBeenCalledWith(['/auth/login'], {
      queryParams: { returnUrl: '/admin/users' },
    });
  });
});
