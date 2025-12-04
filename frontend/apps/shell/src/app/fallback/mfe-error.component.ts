import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';

@Component({
  selector: 'fts-mfe-error',
  standalone: true,
  imports: [CommonModule, RouterModule],
  template: `
    <div
      class="flex flex-col items-center justify-center min-h-[400px] p-8 text-center"
    >
      <div
        class="w-20 h-20 bg-red-100 dark:bg-red-900/30 rounded-full flex items-center justify-center mb-6"
      >
        <svg
          class="w-10 h-10 text-red-600 dark:text-red-400"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
          />
        </svg>
      </div>

      <h2 class="text-2xl font-bold text-gray-900 dark:text-white mb-2">
        {{ displayName }} is temporarily unavailable
      </h2>

      <p class="text-gray-500 dark:text-gray-400 max-w-md mb-6">
        We're having trouble loading this module. This might be a temporary
        issue. Please try again or contact support if the problem persists.
      </p>

      <div class="flex items-center gap-4">
        <button
          (click)="reload()"
          class="px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg font-medium transition-colors"
        >
          Try Again
        </button>
        <a
          routerLink="/dashboard"
          class="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg font-medium text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
        >
          Go to Dashboard
        </a>
      </div>

      @if (error) {
        <details class="mt-8 text-left max-w-md">
          <summary
            class="text-sm text-gray-500 dark:text-gray-400 cursor-pointer"
          >
            Technical details
          </summary>
          <pre
            class="mt-2 p-4 bg-gray-100 dark:bg-gray-800 rounded-lg text-xs text-gray-600 dark:text-gray-300 overflow-auto"
          >{{ error }}</pre>
        </details>
      }
    </div>
  `,
})
export class MfeErrorComponent {
  @Input() mfeName = 'Module';
  @Input() displayName = 'Module';
  @Input() error = '';

  reload() {
    window.location.reload();
  }
}
