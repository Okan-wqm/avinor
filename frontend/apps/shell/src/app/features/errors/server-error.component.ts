// apps/shell/src/app/features/errors/server-error.component.ts
/**
 * 500 Server Error Page
 *
 * Displayed when a critical server error occurs.
 * Provides options to retry or contact support.
 */

import { Component, inject, ChangeDetectionStrategy, signal } from '@angular/core';
import { CommonModule, Location } from '@angular/common';
import { Router, RouterModule } from '@angular/router';

@Component({
  selector: 'fts-server-error',
  standalone: true,
  imports: [CommonModule, RouterModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div
      class="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900 px-4"
    >
      <div class="text-center max-w-lg">
        <!-- Illustration -->
        <div class="mb-8" aria-hidden="true">
          <svg
            class="w-64 h-64 mx-auto"
            viewBox="0 0 400 300"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
          >
            <!-- Server rack -->
            <rect
              x="120"
              y="60"
              width="160"
              height="180"
              rx="8"
              fill="#374151"
              class="dark:fill-gray-600"
            />
            <rect
              x="130"
              y="70"
              width="140"
              height="30"
              rx="4"
              fill="#1F2937"
              class="dark:fill-gray-700"
            />
            <rect
              x="130"
              y="110"
              width="140"
              height="30"
              rx="4"
              fill="#1F2937"
              class="dark:fill-gray-700"
            />
            <rect
              x="130"
              y="150"
              width="140"
              height="30"
              rx="4"
              fill="#1F2937"
              class="dark:fill-gray-700"
            />
            <rect
              x="130"
              y="190"
              width="140"
              height="30"
              rx="4"
              fill="#1F2937"
              class="dark:fill-gray-700"
            />

            <!-- Status lights (error state) -->
            <circle cx="145" cy="85" r="5" fill="#EF4444" class="animate-pulse" />
            <circle cx="160" cy="85" r="5" fill="#EF4444" class="animate-pulse" />
            <circle cx="145" cy="125" r="5" fill="#EF4444" />
            <circle cx="160" cy="125" r="5" fill="#F59E0B" />
            <circle cx="145" cy="165" r="5" fill="#EF4444" class="animate-pulse" />
            <circle cx="160" cy="165" r="5" fill="#EF4444" class="animate-pulse" />
            <circle cx="145" cy="205" r="5" fill="#6B7280" />
            <circle cx="160" cy="205" r="5" fill="#6B7280" />

            <!-- Error spark effects -->
            <g class="animate-pulse">
              <path d="M95 80 L105 90 L95 100 L100 90 Z" fill="#EF4444" />
              <path d="M295 120 L305 130 L295 140 L300 130 Z" fill="#F59E0B" />
              <path d="M85 160 L95 170 L85 180 L90 170 Z" fill="#EF4444" />
              <path d="M305 180 L315 190 L305 200 L310 190 Z" fill="#EF4444" />
            </g>

            <!-- Smoke/error cloud -->
            <ellipse cx="200" cy="40" rx="40" ry="20" fill="#9CA3AF" opacity="0.5" />
            <ellipse cx="180" cy="35" rx="25" ry="15" fill="#9CA3AF" opacity="0.4" />
            <ellipse cx="225" cy="38" rx="30" ry="18" fill="#9CA3AF" opacity="0.4" />

            <!-- Ground shadow -->
            <ellipse cx="200" cy="255" rx="100" ry="15" fill="#374151" opacity="0.2" />
          </svg>
        </div>

        <!-- Error Code -->
        <h1
          class="text-9xl font-bold text-red-500 dark:text-red-400 mb-4"
          aria-label="Error 500"
        >
          500
        </h1>

        <!-- Message -->
        <h2 class="text-2xl font-semibold text-gray-900 dark:text-white mb-2">
          Server Error
        </h2>
        <p class="text-gray-500 dark:text-gray-400 mb-8">
          Something went wrong on our end. Our team has been notified and is working to fix the issue.
          Please try again in a few moments.
        </p>

        <!-- Actions -->
        <div class="flex flex-col sm:flex-row gap-4 justify-center">
          <button
            (click)="retry()"
            [disabled]="isRetrying()"
            class="inline-flex items-center justify-center px-6 py-3 bg-primary-600 hover:bg-primary-700 disabled:bg-primary-400 text-white font-medium rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
          >
            @if (isRetrying()) {
              <svg
                class="animate-spin -ml-1 mr-2 h-5 w-5"
                fill="none"
                viewBox="0 0 24 24"
                aria-hidden="true"
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
              Retrying...
            } @else {
              <svg
                class="w-5 h-5 mr-2"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                aria-hidden="true"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                />
              </svg>
              Try Again
            }
          </button>

          <a
            routerLink="/dashboard"
            class="inline-flex items-center justify-center px-6 py-3 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 font-medium rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
          >
            <svg
              class="w-5 h-5 mr-2"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              aria-hidden="true"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"
              />
            </svg>
            Go to Dashboard
          </a>
        </div>

        <!-- Status info -->
        <div class="mt-8 p-4 bg-gray-100 dark:bg-gray-800 rounded-lg">
          <p class="text-sm text-gray-600 dark:text-gray-400">
            <span class="font-medium">Error ID:</span>
            <code class="ml-2 px-2 py-1 bg-gray-200 dark:bg-gray-700 rounded text-xs">
              {{ errorId }}
            </code>
          </p>
          <p class="text-xs text-gray-500 dark:text-gray-500 mt-2">
            Please reference this ID when contacting support.
          </p>
        </div>

        <!-- Help Link -->
        <p class="mt-6 text-sm text-gray-500 dark:text-gray-400">
          Issue persists?
          <a
            href="mailto:support@flighttraining.com"
            class="text-primary-600 hover:text-primary-700 dark:text-primary-400 dark:hover:text-primary-300 font-medium"
          >
            Contact Support
          </a>
        </p>
      </div>
    </div>
  `,
})
export class ServerErrorComponent {
  private router = inject(Router);
  private location = inject(Location);

  isRetrying = signal(false);
  errorId = this.generateErrorId();

  retry(): void {
    this.isRetrying.set(true);

    // Simulate retry delay
    setTimeout(() => {
      this.isRetrying.set(false);
      // Try to go back to previous page
      this.location.back();
    }, 1500);
  }

  private generateErrorId(): string {
    const timestamp = Date.now().toString(36);
    const random = Math.random().toString(36).substring(2, 8);
    return `ERR-${timestamp}-${random}`.toUpperCase();
  }
}
