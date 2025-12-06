// apps/shell/src/app/features/errors/not-found.component.ts
/**
 * 404 Not Found Page
 *
 * Displayed when users navigate to a non-existent route.
 * Provides helpful navigation options and a friendly message.
 */

import { Component, inject, ChangeDetectionStrategy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterModule } from '@angular/router';

@Component({
  selector: 'fts-not-found',
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
            class="w-64 h-64 mx-auto text-gray-300 dark:text-gray-600"
            viewBox="0 0 400 300"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
          >
            <!-- Cloud -->
            <ellipse cx="200" cy="80" rx="80" ry="40" fill="currentColor" opacity="0.3" />
            <ellipse cx="150" cy="90" rx="50" ry="30" fill="currentColor" opacity="0.3" />
            <ellipse cx="250" cy="90" rx="50" ry="30" fill="currentColor" opacity="0.3" />

            <!-- Airplane -->
            <g transform="translate(80, 120) rotate(-15)">
              <path
                d="M180 30 L220 45 L180 60 L185 45 Z"
                fill="currentColor"
                opacity="0.6"
              />
              <ellipse cx="100" cy="45" rx="90" ry="15" fill="currentColor" opacity="0.8" />
              <ellipse cx="100" cy="45" rx="70" ry="10" fill="currentColor" />
              <path
                d="M50 25 L70 45 L50 65 L60 45 Z"
                fill="currentColor"
                opacity="0.6"
              />
              <circle cx="30" cy="45" r="8" fill="currentColor" opacity="0.9" />
            </g>

            <!-- Question marks -->
            <text
              x="320"
              y="100"
              font-size="40"
              fill="currentColor"
              opacity="0.4"
              font-family="Arial"
            >
              ?
            </text>
            <text
              x="70"
              y="150"
              font-size="30"
              fill="currentColor"
              opacity="0.3"
              font-family="Arial"
            >
              ?
            </text>
            <text
              x="340"
              y="180"
              font-size="25"
              fill="currentColor"
              opacity="0.25"
              font-family="Arial"
            >
              ?
            </text>

            <!-- Ground -->
            <path
              d="M0 260 Q100 240 200 260 Q300 280 400 260 L400 300 L0 300 Z"
              fill="currentColor"
              opacity="0.2"
            />
          </svg>
        </div>

        <!-- Error Code -->
        <h1
          class="text-9xl font-bold text-primary-600 dark:text-primary-400 mb-4"
          aria-label="Error 404"
        >
          404
        </h1>

        <!-- Message -->
        <h2 class="text-2xl font-semibold text-gray-900 dark:text-white mb-2">
          Page Not Found
        </h2>
        <p class="text-gray-500 dark:text-gray-400 mb-8">
          Oops! It seems the page you're looking for has flown off course.
          The URL might be incorrect or the page may have been moved.
        </p>

        <!-- Actions -->
        <div class="flex flex-col sm:flex-row gap-4 justify-center">
          <button
            (click)="goBack()"
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
                d="M10 19l-7-7m0 0l7-7m-7 7h18"
              />
            </svg>
            Go Back
          </button>

          <a
            routerLink="/dashboard"
            class="inline-flex items-center justify-center px-6 py-3 bg-primary-600 hover:bg-primary-700 text-white font-medium rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
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

        <!-- Help Link -->
        <p class="mt-8 text-sm text-gray-500 dark:text-gray-400">
          Need help?
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
export class NotFoundComponent {
  private router = inject(Router);

  goBack(): void {
    // Navigate back in history, or to dashboard if no history
    if (window.history.length > 1) {
      window.history.back();
    } else {
      this.router.navigate(['/dashboard']);
    }
  }
}
