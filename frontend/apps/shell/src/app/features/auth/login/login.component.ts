import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterModule } from '@angular/router';
import { AuthStore } from '../../../core/services/auth.store';

@Component({
  selector: 'fts-login',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  template: `
    <div
      class="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900 px-4"
    >
      <div
        class="max-w-md w-full bg-white dark:bg-gray-800 rounded-xl shadow-lg p-8"
      >
        <!-- Logo -->
        <div class="text-center mb-8">
          <div
            class="inline-flex items-center justify-center w-16 h-16 bg-primary-100 dark:bg-primary-900 rounded-full mb-4"
          >
            <svg
              class="w-10 h-10 text-primary-600 dark:text-primary-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z"
              />
            </svg>
          </div>
          <h1 class="text-2xl font-bold text-gray-900 dark:text-white">
            Flight Training System
          </h1>
          <p class="text-gray-500 dark:text-gray-400 mt-2">
            Sign in to your account
          </p>
        </div>

        <!-- Error Message -->
        @if (authStore.error()) {
          <div
            class="mb-4 p-4 bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-lg"
          >
            <p class="text-sm text-red-600 dark:text-red-400">
              {{ authStore.error() }}
            </p>
          </div>
        }

        <!-- Login Form -->
        <form (ngSubmit)="onSubmit()" #loginForm="ngForm">
          <!-- Email -->
          <div class="mb-4">
            <label
              for="email"
              class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
            >
              Email
            </label>
            <input
              type="email"
              id="email"
              name="email"
              [(ngModel)]="email"
              required
              class="w-full px-4 py-2.5 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              placeholder="you@example.com"
            />
          </div>

          <!-- Password -->
          <div class="mb-6">
            <div class="flex items-center justify-between mb-1">
              <label
                for="password"
                class="block text-sm font-medium text-gray-700 dark:text-gray-300"
              >
                Password
              </label>
              <a
                routerLink="/auth/forgot-password"
                class="text-sm text-primary-600 hover:text-primary-700"
              >
                Forgot password?
              </a>
            </div>
            <input
              type="password"
              id="password"
              name="password"
              [(ngModel)]="password"
              required
              class="w-full px-4 py-2.5 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              placeholder="Enter your password"
            />
          </div>

          <!-- Remember Me -->
          <div class="flex items-center mb-6">
            <input
              type="checkbox"
              id="remember"
              name="remember"
              [(ngModel)]="rememberMe"
              class="w-4 h-4 text-primary-600 border-gray-300 rounded focus:ring-primary-500"
            />
            <label
              for="remember"
              class="ml-2 text-sm text-gray-600 dark:text-gray-400"
            >
              Remember me
            </label>
          </div>

          <!-- Submit Button -->
          <button
            type="submit"
            [disabled]="authStore.isLoading() || !loginForm.valid"
            class="w-full py-2.5 px-4 bg-primary-600 hover:bg-primary-700 disabled:bg-primary-400 text-white font-medium rounded-lg transition-colors flex items-center justify-center"
          >
            @if (authStore.isLoading()) {
              <svg
                class="animate-spin -ml-1 mr-2 h-5 w-5"
                fill="none"
                viewBox="0 0 24 24"
              >
                <circle
                  class="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  stroke-width="4"
                ></circle>
                <path
                  class="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                ></path>
              </svg>
              Signing in...
            } @else {
              Sign in
            }
          </button>
        </form>

        <!-- Footer -->
        <p class="mt-6 text-center text-sm text-gray-500 dark:text-gray-400">
          Don't have an account?
          <a href="#" class="text-primary-600 hover:text-primary-700 font-medium">
            Contact your administrator
          </a>
        </p>
      </div>
    </div>
  `,
})
export class LoginComponent {
  protected authStore = inject(AuthStore);
  private router = inject(Router);

  email = '';
  password = '';
  rememberMe = false;

  async onSubmit() {
    const success = await this.authStore.login(this.email, this.password);
    if (success) {
      this.router.navigate(['/dashboard']);
    }
  }
}
