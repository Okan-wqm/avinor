// apps/shell/src/app/shared/components/toast/toast.types.ts
/**
 * Toast Notification Types
 *
 * Type definitions for the toast notification system.
 */

export type ToastType = 'success' | 'error' | 'warning' | 'info';

export type ToastPosition =
  | 'top-right'
  | 'top-left'
  | 'top-center'
  | 'bottom-right'
  | 'bottom-left'
  | 'bottom-center';

export interface Toast {
  id: string;
  type: ToastType;
  title: string;
  message?: string;
  duration?: number;
  dismissible?: boolean;
  action?: {
    label: string;
    callback: () => void;
  };
  createdAt: number;
}

export interface ToastOptions {
  title: string;
  message?: string;
  duration?: number;
  dismissible?: boolean;
  action?: {
    label: string;
    callback: () => void;
  };
}

export const DEFAULT_TOAST_DURATION = 5000;
export const TOAST_ANIMATION_DURATION = 300;
