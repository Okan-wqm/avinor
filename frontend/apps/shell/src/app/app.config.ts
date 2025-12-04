import { ApplicationConfig, ErrorHandler, isDevMode } from '@angular/core';
import { provideRouter, withPreloading, PreloadAllModules, withComponentInputBinding } from '@angular/router';
import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { provideAnimations } from '@angular/platform-browser/animations';
import { provideServiceWorker } from '@angular/service-worker';

import { APP_ROUTES } from './app.routes';
import { GlobalErrorHandler } from './core/services/error-handler.service';
import { authInterceptor } from './core/interceptors/auth.interceptor';
import { errorInterceptor } from './core/interceptors/error.interceptor';
import { loadingInterceptor } from './core/interceptors/loading.interceptor';

export const appConfig: ApplicationConfig = {
  providers: [
    // Routing with preloading and component input binding
    provideRouter(
      APP_ROUTES,
      withPreloading(PreloadAllModules),
      withComponentInputBinding()
    ),

    // HTTP Client with interceptors (order matters!)
    provideHttpClient(
      withInterceptors([
        authInterceptor,      // Add JWT token
        loadingInterceptor,   // Track loading state
        errorInterceptor,     // Handle errors
      ])
    ),

    // Animations
    provideAnimations(),

    // Service Worker for PWA
    provideServiceWorker('ngsw-worker.js', {
      enabled: !isDevMode(),
      registrationStrategy: 'registerWhenStable:30000',
    }),

    // Global Error Handler
    { provide: ErrorHandler, useClass: GlobalErrorHandler },
  ],
};
