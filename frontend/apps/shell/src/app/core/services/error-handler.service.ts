import { ErrorHandler, Injectable, inject, NgZone } from '@angular/core';
import { Router } from '@angular/router';
import { environment } from '../../../environments/environment';

@Injectable()
export class GlobalErrorHandler implements ErrorHandler {
  private router = inject(Router);
  private zone = inject(NgZone);

  handleError(error: unknown): void {
    // Log error
    console.error('Global Error:', error);

    // Only handle in production
    if (!environment.production) {
      throw error;
    }

    // Handle different error types
    if (this.isChunkLoadError(error)) {
      // MFE failed to load - show fallback
      this.zone.run(() => {
        // The route guards and MFE loader handle this
        console.warn('Chunk load error - MFE may be unavailable');
      });
      return;
    }

    // Report to error tracking service (Sentry, etc.)
    this.reportError(error);
  }

  private isChunkLoadError(error: unknown): boolean {
    return (
      error instanceof Error &&
      (error.name === 'ChunkLoadError' ||
        error.message.includes('Loading chunk') ||
        error.message.includes('remoteEntry'))
    );
  }

  private reportError(error: unknown): void {
    // TODO: Send to Sentry or similar service
    if (environment.features.debugMode) {
      console.error('Error would be reported:', error);
    }
  }
}
