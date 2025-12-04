import { Injectable, signal, computed, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { environment } from '../../../environments/environment';

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
  async login(email: string, password: string): Promise<boolean> {
    this.state.update((s) => ({ ...s, isLoading: true, error: null }));

    try {
      const response = await this.http
        .post<{
          access: string;
          refresh: string;
          user: User;
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

        this.saveToStorage();
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
    this.clearStorage();
    this.router.navigate(['/auth/login']);
  }

  async refreshAccessToken(): Promise<string | null> {
    const refreshToken = this.state().refreshToken;
    if (!refreshToken) return null;

    try {
      const response = await this.http
        .post<{ access: string }>(`${environment.apiBaseUrl}${environment.api.auth}/refresh/`, {
          refresh: refreshToken,
        })
        .toPromise();

      if (response) {
        this.state.update((s) => ({
          ...s,
          accessToken: response.access,
        }));
        this.saveToStorage();
        return response.access;
      }

      return null;
    } catch {
      this.logout();
      return null;
    }
  }

  // Storage management
  private saveToStorage(): void {
    const state = this.state();
    localStorage.setItem('fts_auth_token', state.accessToken || '');
    localStorage.setItem('fts_refresh_token', state.refreshToken || '');
    localStorage.setItem('fts_user', JSON.stringify(state.user));
  }

  private loadFromStorage(): AuthState {
    const accessToken = localStorage.getItem('fts_auth_token');
    const refreshToken = localStorage.getItem('fts_refresh_token');
    const userJson = localStorage.getItem('fts_user');

    if (accessToken && userJson) {
      try {
        const user = JSON.parse(userJson) as User;
        return {
          user,
          accessToken,
          refreshToken,
          isAuthenticated: true,
          isLoading: false,
          error: null,
        };
      } catch {
        this.clearStorage();
      }
    }

    return initialState;
  }

  private clearStorage(): void {
    localStorage.removeItem('fts_auth_token');
    localStorage.removeItem('fts_refresh_token');
    localStorage.removeItem('fts_user');
  }
}
