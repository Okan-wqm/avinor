// apps/shell/src/app/shared/components/toast/toast.component.ts
/**
 * Toast Notification Component
 *
 * Displays toast notifications with animations, icons, and action buttons.
 * WCAG 2.1 AA compliant with proper ARIA attributes.
 */

import {
  Component,
  inject,
  ChangeDetectionStrategy,
  computed,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { animate, style, transition, trigger } from '@angular/animations';
import { ToastService } from './toast.service';
import { Toast, ToastType } from './toast.types';

@Component({
  selector: 'fts-toast-container',
  standalone: true,
  imports: [CommonModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  animations: [
    trigger('toastAnimation', [
      transition(':enter', [
        style({ opacity: 0, transform: 'translateX(100%) scale(0.95)' }),
        animate(
          '300ms cubic-bezier(0.4, 0, 0.2, 1)',
          style({ opacity: 1, transform: 'translateX(0) scale(1)' })
        ),
      ]),
      transition(':leave', [
        animate(
          '200ms cubic-bezier(0.4, 0, 0.2, 1)',
          style({ opacity: 0, transform: 'translateX(100%) scale(0.95)' })
        ),
      ]),
    ]),
  ],
  template: `
    <!-- Toast Container - ARIA live region for screen readers -->
    <div
      [class]="containerClasses()"
      role="region"
      aria-label="Notifications"
      aria-live="polite"
      aria-atomic="false"
    >
      @for (toast of toastService.visibleToasts(); track toast.id) {
        <div
          [@toastAnimation]
          [class]="getToastClasses(toast.type)"
          role="alert"
          [attr.aria-labelledby]="'toast-title-' + toast.id"
          [attr.aria-describedby]="toast.message ? 'toast-msg-' + toast.id : null"
        >
          <!-- Icon -->
          <div class="flex-shrink-0" aria-hidden="true">
            @switch (toast.type) {
              @case ('success') {
                <svg class="w-5 h-5 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              }
              @case ('error') {
                <svg class="w-5 h-5 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              }
              @case ('warning') {
                <svg class="w-5 h-5 text-yellow-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
              }
              @case ('info') {
                <svg class="w-5 h-5 text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              }
            }
          </div>

          <!-- Content -->
          <div class="flex-1 ml-3">
            <p
              [id]="'toast-title-' + toast.id"
              class="text-sm font-medium"
              [class]="getTitleClasses(toast.type)"
            >
              {{ toast.title }}
            </p>
            @if (toast.message) {
              <p
                [id]="'toast-msg-' + toast.id"
                class="mt-1 text-sm"
                [class]="getMessageClasses(toast.type)"
              >
                {{ toast.message }}
              </p>
            }
            @if (toast.action) {
              <div class="mt-2">
                <button
                  type="button"
                  (click)="handleAction(toast)"
                  class="text-sm font-medium underline hover:no-underline focus:outline-none focus:ring-2 focus:ring-offset-2 rounded"
                  [class]="getActionClasses(toast.type)"
                >
                  {{ toast.action.label }}
                </button>
              </div>
            }
          </div>

          <!-- Dismiss Button -->
          @if (toast.dismissible) {
            <div class="flex-shrink-0 ml-4">
              <button
                type="button"
                (click)="dismiss(toast.id)"
                class="inline-flex rounded-md p-1.5 focus:outline-none focus:ring-2 focus:ring-offset-2 transition-colors"
                [class]="getDismissClasses(toast.type)"
                [attr.aria-label]="'Dismiss ' + toast.title"
              >
                <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          }
        </div>
      }

      <!-- Hidden toast count indicator -->
      @if (toastService.hiddenCount() > 0) {
        <div
          class="px-4 py-2 text-sm text-gray-500 dark:text-gray-400 text-center bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700"
          role="status"
          aria-live="polite"
        >
          +{{ toastService.hiddenCount() }} more notification(s)
        </div>
      }
    </div>
  `,
})
export class ToastContainerComponent {
  protected readonly toastService = inject(ToastService);

  /** Container position classes */
  containerClasses = computed(() => {
    const position = this.toastService.position();
    const baseClasses = 'fixed z-50 flex flex-col gap-3 p-4 max-w-sm w-full pointer-events-none';

    const positionClasses: Record<string, string> = {
      'top-right': 'top-0 right-0',
      'top-left': 'top-0 left-0',
      'top-center': 'top-0 left-1/2 -translate-x-1/2',
      'bottom-right': 'bottom-0 right-0',
      'bottom-left': 'bottom-0 left-0',
      'bottom-center': 'bottom-0 left-1/2 -translate-x-1/2',
    };

    return `${baseClasses} ${positionClasses[position]}`;
  });

  /** Get toast wrapper classes based on type */
  getToastClasses(type: ToastType): string {
    const baseClasses =
      'flex items-start p-4 rounded-lg shadow-lg border pointer-events-auto backdrop-blur-sm';

    const typeClasses: Record<ToastType, string> = {
      success: 'bg-green-50 dark:bg-green-900/30 border-green-200 dark:border-green-800',
      error: 'bg-red-50 dark:bg-red-900/30 border-red-200 dark:border-red-800',
      warning: 'bg-yellow-50 dark:bg-yellow-900/30 border-yellow-200 dark:border-yellow-800',
      info: 'bg-blue-50 dark:bg-blue-900/30 border-blue-200 dark:border-blue-800',
    };

    return `${baseClasses} ${typeClasses[type]}`;
  }

  /** Get title text classes based on type */
  getTitleClasses(type: ToastType): string {
    const classes: Record<ToastType, string> = {
      success: 'text-green-800 dark:text-green-200',
      error: 'text-red-800 dark:text-red-200',
      warning: 'text-yellow-800 dark:text-yellow-200',
      info: 'text-blue-800 dark:text-blue-200',
    };
    return classes[type];
  }

  /** Get message text classes based on type */
  getMessageClasses(type: ToastType): string {
    const classes: Record<ToastType, string> = {
      success: 'text-green-700 dark:text-green-300',
      error: 'text-red-700 dark:text-red-300',
      warning: 'text-yellow-700 dark:text-yellow-300',
      info: 'text-blue-700 dark:text-blue-300',
    };
    return classes[type];
  }

  /** Get action button classes based on type */
  getActionClasses(type: ToastType): string {
    const classes: Record<ToastType, string> = {
      success: 'text-green-700 dark:text-green-300 focus:ring-green-500',
      error: 'text-red-700 dark:text-red-300 focus:ring-red-500',
      warning: 'text-yellow-700 dark:text-yellow-300 focus:ring-yellow-500',
      info: 'text-blue-700 dark:text-blue-300 focus:ring-blue-500',
    };
    return classes[type];
  }

  /** Get dismiss button classes based on type */
  getDismissClasses(type: ToastType): string {
    const classes: Record<ToastType, string> = {
      success:
        'text-green-500 hover:bg-green-100 dark:hover:bg-green-800/50 focus:ring-green-500',
      error:
        'text-red-500 hover:bg-red-100 dark:hover:bg-red-800/50 focus:ring-red-500',
      warning:
        'text-yellow-500 hover:bg-yellow-100 dark:hover:bg-yellow-800/50 focus:ring-yellow-500',
      info:
        'text-blue-500 hover:bg-blue-100 dark:hover:bg-blue-800/50 focus:ring-blue-500',
    };
    return classes[type];
  }

  /** Dismiss a toast */
  dismiss(id: string): void {
    this.toastService.dismiss(id);
  }

  /** Handle action button click */
  handleAction(toast: { id: string; action?: { callback: () => void } }): void {
    if (toast.action?.callback) {
      toast.action.callback();
    }
    this.dismiss(toast.id);
  }
}
