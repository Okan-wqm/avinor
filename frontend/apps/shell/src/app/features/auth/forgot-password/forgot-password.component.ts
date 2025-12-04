import { Component, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';

@Component({
  selector: 'fts-forgot-password',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  template: `
    <div
      class="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900 px-4"
    >
      <div
        class="max-w-md w-full bg-white dark:bg-gray-800 rounded-xl shadow-lg p-8"
      >
        <!-- Back Link -->
        <a
          routerLink="/auth/login"
          class="inline-flex items-center text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 mb-6"
        >
          <svg class="w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M15 19l-7-7 7-7"
            />
          </svg>
          Back to login
        </a>

        <!-- Header -->
        <div class="mb-8">
          <h1 class="text-2xl font-bold text-gray-900 dark:text-white">
            Reset your password
          </h1>
          <p class="text-gray-500 dark:text-gray-400 mt-2">
            Enter your email address and we'll send you a link to reset your
            password.
          </p>
        </div>

        @if (submitted()) {
          <!-- Success State -->
          <div
            class="p-4 bg-green-50 dark:bg-green-900/30 border border-green-200 dark:border-green-800 rounded-lg"
          >
            <div class="flex items-start">
              <svg
                class="w-5 h-5 text-green-600 dark:text-green-400 mt-0.5"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M5 13l4 4L19 7"
                />
              </svg>
              <div class="ml-3">
                <h3
                  class="text-sm font-medium text-green-800 dark:text-green-300"
                >
                  Check your email
                </h3>
                <p class="mt-1 text-sm text-green-700 dark:text-green-400">
                  If an account exists for {{ email }}, you will receive a
                  password reset link shortly.
                </p>
              </div>
            </div>
          </div>
        } @else {
          <!-- Form -->
          <form (ngSubmit)="onSubmit()" #forgotForm="ngForm">
            <div class="mb-6">
              <label
                for="email"
                class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
              >
                Email address
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

            <button
              type="submit"
              [disabled]="isLoading() || !forgotForm.valid"
              class="w-full py-2.5 px-4 bg-primary-600 hover:bg-primary-700 disabled:bg-primary-400 text-white font-medium rounded-lg transition-colors"
            >
              @if (isLoading()) {
                Sending...
              } @else {
                Send reset link
              }
            </button>
          </form>
        }
      </div>
    </div>
  `,
})
export class ForgotPasswordComponent {
  email = '';
  isLoading = signal(false);
  submitted = signal(false);

  async onSubmit() {
    this.isLoading.set(true);
    // TODO: Call API
    await new Promise((resolve) => setTimeout(resolve, 1000));
    this.isLoading.set(false);
    this.submitted.set(true);
  }
}
