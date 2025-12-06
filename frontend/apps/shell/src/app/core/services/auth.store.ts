import { Injectable, signal, computed, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { environment } from '../../../environments/environment';
import { SecureStorageService } from './secure-storage.service';

export interface User {
  id: string;
  email: string;
  firstName: string;
  lastName: string;
  avatarUrl?: string;
  roles: string[];
  permissions: string[];
  organizationId: string;
  organizationName: string;
}

export interface AuthState {
  user: User | null;
  accessToken: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
}

const initialState: AuthState = {
  user: null,
  accessToken: null,
  refreshToken: null,
  isAuthenticated: false,
  isLoading: false,
  error: null,
};

@Injectable({ providedIn: 'root' })
export class AuthStore {
  private http = inject(HttpClient);
  private router = inject(Router);
  private secureStorage = inject(SecureStorageService);

  // Remember me preference
  private rememberMe = false;

  // Private state
  private state = signal<AuthState>(this.loadFromStorage());

  // Public selectors
  user = computed(() => this.state().user);
  accessToken = computed(() => this.state().accessToken);
  isAuthenticated = computed(() => this.state().isAuthenticated);
  isLoading = computed(() => this.state().isLoading);
  error = computed(() => this.state().error);
  roles = computed(() => this.state().user?.roles || []);
  organizationId = computed(() => this.state().user?.organizationId);

  // Role checks
  isAdmin = computed(() => this.hasRole('admin') || this.hasRole('super_admin'));
  isInstructor = computed(() => this.hasRole('instructor'));
  isStudent = computed(() => this.hasRole('student'));

  hasRole(role: string): boolean {
    return this.roles().includes(role);
  }

  hasPermission(permission: string): boolean {
    return this.state().user?.permissions.includes(permission) || false;
  }

  // Actions
  async login(email: string, password: string, rememberMe: boolean = false): Promise<boolean> {
    this.state.update((s) => ({ ...s, isLoading: true, error: null }));
    this.rememberMe = rememberMe;

    try {
      const response = await this.http
        .post<{
          access: string;
          refresh: string;
          user: User;
          expires_in?: number;
        }>(`${environment.apiBaseUrl}${environment.api.auth}/login/`, {
          email,
          password,
        })
        .toPromise();

      if (response) {
        this.state.set({
          user: response.user,
          accessToken: response.access,
          refreshToken: response.refresh,
          isAuthenticated: true,
          isLoading: false,
          error: null,
        });

        // Use secure storage with appropriate expiry
        const expiresIn = response.expires_in || 3600; // Default 1 hour
        this.saveToSecureStorage(expiresIn);
        return true;
      }

      return false;
    } catch (error: any) {
      this.state.update((s) => ({
        ...s,
        isLoading: false,
        error: error.error?.detail || 'Login failed',
      }));
      return false;
    }
  }

  logout(): void {
    this.state.set(initialState);
    this.clearSecureStorage();
    this.router.navigate(['/auth/login']);
  }

  async refreshAccessToken(): Promise<string | null> {
    const refreshToken = this.state().refreshToken;
    if (!refreshToken) return null;

    // Check if refresh token is expired
    if (this.secureStorage.isTokenExpired(refreshToken)) {
      this.logout();
      return null;
    }

    try {
      const response = await this.http
        .post<{ access: string; expires_in?: number }>(`${environment.apiBaseUrl}${environment.api.auth}/refresh/`, {
          refresh: refreshToken,
        })
        .toPromise();

      if (response) {
        this.state.update((s) => ({
          ...s,
          accessToken: response.access,
        }));

        // Update secure storage with new access token
        const expiresIn = response.expires_in || 3600;
        this.secureStorage.setToken('access_token', response.access, expiresIn, this.rememberMe);
        return response.access;
      }

      return null;
    } catch {
      this.logout();
      return null;
    }
  }

  // Secure Storage management
  private saveToSecureStorage(expiresInSeconds: number = 3600): void {
    const state = this.state();

    if (state.accessToken) {
      this.secureStorage.setToken('access_token', state.accessToken, expiresInSeconds, this.rememberMe);
    }

    if (state.refreshToken) {
      // Refresh tokens typically last longer (7 days)
      this.secureStorage.setToken('refresh_token', state.refreshToken, 7 * 24 * 3600, this.rememberMe);
    }

    if (state.user) {
      this.secureStorage.setUserData(state.user, this.rememberMe);
    }
  }

  private loadFromStorage(): AuthState {
    // Try to load from secure storage (check both session and persistent)
    const accessToken = this.secureStorage.getToken('access_token', false) ||
                        this.secureStorage.getToken('access_token', true);
    const refreshToken = this.secureStorage.getToken('refresh_token', false) ||
                         this.secureStorage.getToken('refresh_token', true);
    const user = this.secureStorage.getUserData<User>(false) ||
                 this.secureStorage.getUserData<User>(true);

    // If we found tokens in persistent storage, set rememberMe flag
    if (this.secureStorage.getToken('access_token', true)) {
      this.rememberMe = true;
    }

    if (accessToken && user) {
      // Validate access token isn't expired
      if (!this.secureStorage.isTokenExpired(accessToken)) {
        return {
          user,
          accessToken,
          refreshToken,
          isAuthenticated: true,
          isLoading: false,
          error: null,
        };
      }

      // Access token expired, but we have refresh token - try to use it
      if (refreshToken && !this.secureStorage.isTokenExpired(refreshToken)) {
        return {
          user,
          accessToken: null,  // Will trigger refresh
          refreshToken,
          isAuthenticated: false, // Will be set after refresh
          isLoading: false,
          error: null,
        };
      }

      // Both tokens expired, clear storage
      this.clearSecureStorage();
    }

    // Also migrate from legacy storage if exists
    return this.migrateFromLegacyStorage();
  }

  private clearSecureStorage(): void {
    this.secureStorage.clearAll();
    // Also clear legacy storage
    this.clearLegacyStorage();
  }

  // Migration from old localStorage keys
  private migrateFromLegacyStorage(): AuthState {
    const accessToken = localStorage.getItem('fts_auth_token');
    const refreshToken = localStorage.getItem('fts_refresh_token');
    const userJson = localStorage.getItem('fts_user');

    if (accessToken && userJson) {
      try {
        const user = JSON.parse(userJson) as User;

        // Migrate to secure storage
        this.secureStorage.setToken('access_token', accessToken, 3600, true);
        if (refreshToken) {
          this.secureStorage.setToken('refresh_token', refreshToken, 7 * 24 * 3600, true);
        }
        this.secureStorage.setUserData(user, true);

        // Clear legacy storage
        this.clearLegacyStorage();

        this.rememberMe = true;

        return {
          user,
          accessToken,
          refreshToken,
          isAuthenticated: true,
          isLoading: false,
          error: null,
        };
      } catch {
        this.clearLegacyStorage();
      }
    }

    return initialState;
  }

  private clearLegacyStorage(): void {
    localStorage.removeItem('fts_auth_token');
    localStorage.removeItem('fts_refresh_token');
    localStorage.removeItem('fts_user');
  }
}
