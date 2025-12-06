// apps/shell/src/app/core/handlers/global-error.handler.ts
/**
 * Global Error Handler
 *
 * Centralized error handling for the application.
 * Catches unhandled errors and displays appropriate notifications.
 */

import { ErrorHandler, Injectable, inject, NgZone } from '@angular/core';
import { HttpErrorResponse } from '@angular/common/http';
import { ToastService } from '../../shared/components/toast';

export interface AppError {
  code: string;
  message: string;
  details?: unknown;
  timestamp: Date;
  stack?: string;
}

@Injectable()
export class GlobalErrorHandler implements ErrorHandler {
  private toastService = inject(ToastService);
  private ngZone = inject(NgZone);

  handleError(error: Error | HttpErrorResponse): void {
    // Run inside Angular zone to ensure change detection
    this.ngZone.run(() => {
      const appError = this.parseError(error);

      // Log error for debugging
      console.error('[GlobalErrorHandler]', appError);

      // Show user-friendly notification
      this.showErrorNotification(appError);

      // Report to error tracking service (future implementation)
      this.reportError(appError);
    });
  }

  private parseError(error: Error | HttpErrorResponse): AppError {
    if (error instanceof HttpErrorResponse) {
      return this.parseHttpError(error);
    }

    return {
      code: 'CLIENT_ERROR',
      message: error.message || 'An unexpected error occurred',
      details: error,
      timestamp: new Date(),
      stack: error.stack,
    };
  }

  private parseHttpError(error: HttpErrorResponse): AppError {
    let message = 'An error occurred while communicating with the server';
    let code = 'HTTP_ERROR';

    switch (error.status) {
      case 0:
        code = 'NETWORK_ERROR';
        message = 'Unable to connect to the server. Please check your internet connection.';
        break;
      case 400:
        code = 'BAD_REQUEST';
        message = error.error?.message || error.error?.detail || 'Invalid request';
        break;
      case 401:
        code = 'UNAUTHORIZED';
        message = 'Your session has expired. Please log in again.';
        break;
      case 403:
        code = 'FORBIDDEN';
        message = 'You do not have permission to perform this action.';
        break;
      case 404:
        code = 'NOT_FOUND';
        message = 'The requested resource was not found.';
        break;
      case 422:
        code = 'VALIDATION_ERROR';
        message = error.error?.message || error.error?.detail || 'Validation failed';
        break;
      case 429:
        code = 'RATE_LIMIT';
        message = 'Too many requests. Please try again later.';
        break;
      case 500:
        code = 'SERVER_ERROR';
        message = 'An internal server error occurred. Please try again later.';
        break;
      case 502:
      case 503:
      case 504:
        code = 'SERVICE_UNAVAILABLE';
        message = 'The service is temporarily unavailable. Please try again later.';
        break;
      default:
        message = error.error?.message || error.error?.detail || message;
    }

    return {
      code,
      message,
      details: error.error,
      timestamp: new Date(),
    };
  }

  private showErrorNotification(error: AppError): void {
    // Don't show notification for 401 errors (handled by auth interceptor)
    if (error.code === 'UNAUTHORIZED') {
      return;
    }

    this.toastService.error({
      title: this.getErrorTitle(error.code),
      message: error.message,
      duration: error.code === 'NETWORK_ERROR' ? 10000 : 5000,
    });
  }

  private getErrorTitle(code: string): string {
    const titles: Record<string, string> = {
      NETWORK_ERROR: 'Connection Error',
      BAD_REQUEST: 'Invalid Request',
      UNAUTHORIZED: 'Session Expired',
      FORBIDDEN: 'Access Denied',
      NOT_FOUND: 'Not Found',
      VALIDATION_ERROR: 'Validation Error',
      RATE_LIMIT: 'Rate Limited',
      SERVER_ERROR: 'Server Error',
      SERVICE_UNAVAILABLE: 'Service Unavailable',
      CLIENT_ERROR: 'Error',
      HTTP_ERROR: 'Error',
    };
    return titles[code] || 'Error';
  }

  private reportError(error: AppError): void {
    // Placeholder for error reporting service integration
    // Examples: Sentry, LogRocket, DataDog, etc.
    // This would send error details to a monitoring service
  }
}
