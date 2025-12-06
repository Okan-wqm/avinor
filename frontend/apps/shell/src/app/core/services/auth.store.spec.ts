// apps/shell/src/app/core/services/auth.store.spec.ts
/**
 * Auth Store Tests
 *
 * Tests for the authentication state management store.
 */

import { TestBed, fakeAsync, tick } from '@angular/core/testing';
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';
import { Router } from '@angular/router';
import { AuthStore, User } from './auth.store';
import { environment } from '../../../environments/environment';

describe('AuthStore', () => {
  let authStore: AuthStore;
  let httpMock: HttpTestingController;
  let router: Router;

  const mockUser: User = {
    id: '123',
    email: 'test@example.com',
    firstName: 'John',
    lastName: 'Doe',
    roles: ['user'],
    permissions: ['read:flights'],
    organizationId: 'org-123',
    organizationName: 'Test Org',
  };

  const mockLoginResponse = {
    access: 'mock-access-token',
    refresh: 'mock-refresh-token',
    user: mockUser,
    expires_in: 3600,
  };

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

    authStore = TestBed.inject(AuthStore);
    httpMock = TestBed.inject(HttpTestingController);
    router = TestBed.inject(Router);
  });

  afterEach(() => {
    httpMock.verify();
    localStorage.clear();
    sessionStorage.clear();
  });

  describe('initial state', () => {
    it('should start with unauthenticated state', () => {
      expect(authStore.isAuthenticated()).toBe(false);
      expect(authStore.user()).toBeNull();
      expect(authStore.accessToken()).toBeNull();
    });

    it('should start with no loading or error', () => {
      expect(authStore.isLoading()).toBe(false);
      expect(authStore.error()).toBeNull();
    });
  });

  describe('login', () => {
    it('should set loading state during login', fakeAsync(() => {
      const loginPromise = authStore.login('test@example.com', 'password123');

      expect(authStore.isLoading()).toBe(true);

      const req = httpMock.expectOne(
        `${environment.apiBaseUrl}${environment.api.auth}/login/`
      );
      req.flush(mockLoginResponse);

      tick();
      expect(authStore.isLoading()).toBe(false);
    }));

    it('should update state on successful login', fakeAsync(() => {
      const loginPromise = authStore.login('test@example.com', 'password123');

      const req = httpMock.expectOne(
        `${environment.apiBaseUrl}${environment.api.auth}/login/`
      );
      req.flush(mockLoginResponse);

      tick();

      expect(authStore.isAuthenticated()).toBe(true);
      expect(authStore.user()).toEqual(mockUser);
      expect(authStore.accessToken()).toBe('mock-access-token');
      expect(authStore.error()).toBeNull();
    }));

    it('should set error on failed login', fakeAsync(() => {
      const loginPromise = authStore.login('test@example.com', 'wrongpassword');

      const req = httpMock.expectOne(
        `${environment.apiBaseUrl}${environment.api.auth}/login/`
      );
      req.flush(
        { detail: 'Invalid credentials' },
        { status: 401, statusText: 'Unauthorized' }
      );

      tick();

      expect(authStore.isAuthenticated()).toBe(false);
      expect(authStore.error()).toBe('Invalid credentials');
    }));

    it('should return true on successful login', fakeAsync(async () => {
      const loginPromise = authStore.login('test@example.com', 'password123');

      const req = httpMock.expectOne(
        `${environment.apiBaseUrl}${environment.api.auth}/login/`
      );
      req.flush(mockLoginResponse);

      tick();

      const result = await loginPromise;
      expect(result).toBe(true);
    }));
  });

  describe('logout', () => {
    it('should clear state and redirect on logout', fakeAsync(async () => {
      // First login
      authStore.login('test@example.com', 'password123');
      const req = httpMock.expectOne(
        `${environment.apiBaseUrl}${environment.api.auth}/login/`
      );
      req.flush(mockLoginResponse);
      tick();

      // Verify logged in
      expect(authStore.isAuthenticated()).toBe(true);

      // Logout
      authStore.logout();

      // Verify logged out
      expect(authStore.isAuthenticated()).toBe(false);
      expect(authStore.user()).toBeNull();
      expect(authStore.accessToken()).toBeNull();
      expect(router.navigate).toHaveBeenCalledWith(['/auth/login']);
    }));
  });

  describe('role checks', () => {
    beforeEach(fakeAsync(() => {
      authStore.login('test@example.com', 'password123');
      const req = httpMock.expectOne(
        `${environment.apiBaseUrl}${environment.api.auth}/login/`
      );
      req.flush(mockLoginResponse);
      tick();
    }));

    it('should correctly check hasRole', () => {
      expect(authStore.hasRole('user')).toBe(true);
      expect(authStore.hasRole('admin')).toBe(false);
    });

    it('should correctly check hasPermission', () => {
      expect(authStore.hasPermission('read:flights')).toBe(true);
      expect(authStore.hasPermission('write:flights')).toBe(false);
    });

    it('should return correct isAdmin value', () => {
      expect(authStore.isAdmin()).toBe(false);
    });
  });

  describe('computed selectors', () => {
    beforeEach(fakeAsync(() => {
      authStore.login('test@example.com', 'password123');
      const req = httpMock.expectOne(
        `${environment.apiBaseUrl}${environment.api.auth}/login/`
      );
      req.flush(mockLoginResponse);
      tick();
    }));

    it('should return user roles', () => {
      expect(authStore.roles()).toEqual(['user']);
    });

    it('should return organization id', () => {
      expect(authStore.organizationId()).toBe('org-123');
    });
  });
});
