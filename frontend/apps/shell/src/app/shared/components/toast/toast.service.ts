// apps/shell/src/app/shared/components/toast/toast.service.ts
/**
 * Toast Notification Service
 *
 * Manages toast notifications with signals for reactive state management.
 * Supports multiple toast types, auto-dismiss, and manual dismissal.
 */

import { Injectable, signal, computed } from '@angular/core';
import {
  Toast,
  ToastType,
  ToastOptions,
  ToastPosition,
  DEFAULT_TOAST_DURATION,
} from './toast.types';

@Injectable({
  providedIn: 'root',
})
export class ToastService {
  private readonly _toasts = signal<Toast[]>([]);
  private readonly _position = signal<ToastPosition>('top-right');
  private readonly _maxToasts = signal<number>(5);

  /** All active toasts */
  readonly toasts = computed(() => this._toasts());

  /** Current toast position */
  readonly position = computed(() => this._position());

  /** Maximum number of visible toasts */
  readonly maxToasts = computed(() => this._maxToasts());

  /** Visible toasts (limited by maxToasts) */
  readonly visibleToasts = computed(() =>
    this._toasts().slice(0, this._maxToasts())
  );

  /** Number of hidden toasts */
  readonly hiddenCount = computed(() =>
    Math.max(0, this._toasts().length - this._maxToasts())
  );

  /**
   * Configure toast position
   */
  setPosition(position: ToastPosition): void {
    this._position.set(position);
  }

  /**
   * Configure maximum visible toasts
   */
  setMaxToasts(max: number): void {
    this._maxToasts.set(max);
  }

  /**
   * Show a success toast
   */
  success(options: ToastOptions | string): string {
    return this.show('success', options);
  }

  /**
   * Show an error toast
   */
  error(options: ToastOptions | string): string {
    return this.show('error', options);
  }

  /**
   * Show a warning toast
   */
  warning(options: ToastOptions | string): string {
    return this.show('warning', options);
  }

  /**
   * Show an info toast
   */
  info(options: ToastOptions | string): string {
    return this.show('info', options);
  }

  /**
   * Show a toast notification
   */
  show(type: ToastType, options: ToastOptions | string): string {
    const normalizedOptions: ToastOptions =
      typeof options === 'string' ? { title: options } : options;

    const toast: Toast = {
      id: this.generateId(),
      type,
      title: normalizedOptions.title,
      message: normalizedOptions.message,
      duration: normalizedOptions.duration ?? DEFAULT_TOAST_DURATION,
      dismissible: normalizedOptions.dismissible ?? true,
      action: normalizedOptions.action,
      createdAt: Date.now(),
    };

    this._toasts.update((toasts) => [...toasts, toast]);

    // Auto-dismiss if duration is set
    if (toast.duration && toast.duration > 0) {
      setTimeout(() => {
        this.dismiss(toast.id);
      }, toast.duration);
    }

    return toast.id;
  }

  /**
   * Dismiss a specific toast
   */
  dismiss(id: string): void {
    this._toasts.update((toasts) => toasts.filter((t) => t.id !== id));
  }

  /**
   * Dismiss all toasts
   */
  dismissAll(): void {
    this._toasts.set([]);
  }

  /**
   * Update an existing toast
   */
  update(id: string, options: Partial<ToastOptions>): void {
    this._toasts.update((toasts) =>
      toasts.map((toast) =>
        toast.id === id ? { ...toast, ...options } : toast
      )
    );
  }

  /**
   * Generate unique toast ID
   */
  private generateId(): string {
    return `toast-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
  }
}
