// apps/shell/src/app/core/guards/role.guard.spec.ts
/**
 * Role Guard Tests
 *
 * Tests for the role-based route guard.
 */

import { TestBed } from '@angular/core/testing';
import { Router, ActivatedRouteSnapshot, RouterStateSnapshot } from '@angular/router';
import { roleGuard } from './role.guard';
import { AuthStore } from '../services/auth.store';
import { HttpClientTestingModule } from '@angular/common/http/testing';

describe('roleGuard', () => {
  let router: Router;
  let authStore: AuthStore;

  const createMockRoute = (roles: string[]): ActivatedRouteSnapshot => {
    return {
      data: { roles },
    } as unknown as ActivatedRouteSnapshot;
  };

  const mockState: RouterStateSnapshot = { url: '/admin' } as RouterStateSnapshot;

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
  });

  it('should redirect to login when user is not authenticated', () => {
    // Arrange
    jest.spyOn(authStore, 'isAuthenticated').mockReturnValue(false);
    const route = createMockRoute(['admin']);

    // Act
    const result = TestBed.runInInjectionContext(() =>
      roleGuard(route, mockState)
    );

    // Assert
    expect(result).toBe(false);
    expect(router.navigate).toHaveBeenCalledWith(['/auth/login'], {
      queryParams: { returnUrl: '/admin' },
    });
  });

  it('should allow access when user has required role', () => {
    // Arrange
    jest.spyOn(authStore, 'isAuthenticated').mockReturnValue(true);
    jest.spyOn(authStore, 'roles').mockReturnValue(['admin', 'user']);
    const route = createMockRoute(['admin']);

    // Act
    const result = TestBed.runInInjectionContext(() =>
      roleGuard(route, mockState)
    );

    // Assert
    expect(result).toBe(true);
    expect(router.navigate).not.toHaveBeenCalled();
  });

  it('should deny access when user does not have required role', () => {
    // Arrange
    jest.spyOn(authStore, 'isAuthenticated').mockReturnValue(true);
    jest.spyOn(authStore, 'roles').mockReturnValue(['user']);
    const route = createMockRoute(['admin', 'super_admin']);

    // Act
    const result = TestBed.runInInjectionContext(() =>
      roleGuard(route, mockState)
    );

    // Assert
    expect(result).toBe(false);
    expect(router.navigate).toHaveBeenCalledWith(['/dashboard'], {
      queryParams: { error: 'unauthorized' },
    });
  });

  it('should allow access when no roles are specified', () => {
    // Arrange
    jest.spyOn(authStore, 'isAuthenticated').mockReturnValue(true);
    jest.spyOn(authStore, 'roles').mockReturnValue(['user']);
    const route = createMockRoute([]);

    // Act
    const result = TestBed.runInInjectionContext(() =>
      roleGuard(route, mockState)
    );

    // Assert
    expect(result).toBe(true);
  });

  it('should allow access when user has any of the required roles', () => {
    // Arrange
    jest.spyOn(authStore, 'isAuthenticated').mockReturnValue(true);
    jest.spyOn(authStore, 'roles').mockReturnValue(['super_admin']);
    const route = createMockRoute(['admin', 'super_admin']);

    // Act
    const result = TestBed.runInInjectionContext(() =>
      roleGuard(route, mockState)
    );

    // Assert
    expect(result).toBe(true);
  });
});
