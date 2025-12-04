import { Routes } from '@angular/router';
import { loadRemoteModule } from '@angular-architects/module-federation';
import { environment } from '../environments/environment';

// MFE Configuration with error handling
interface MfeConfig {
  name: string;
  displayName: string;
  url: string;
  exposedModule: string;
  routesExport: string;
}

const MFE_CONFIG: Record<string, MfeConfig> = {
  operations: {
    name: 'operations',
    displayName: 'Operations',
    url: environment.mfe.operations,
    exposedModule: './routes',
    routesExport: 'OPERATIONS_ROUTES',
  },
  training: {
    name: 'training',
    displayName: 'Training',
    url: environment.mfe.training,
    exposedModule: './routes',
    routesExport: 'TRAINING_ROUTES',
  },
  admin: {
    name: 'admin',
    displayName: 'Admin',
    url: environment.mfe.admin,
    exposedModule: './routes',
    routesExport: 'ADMIN_ROUTES',
  },
};

/**
 * Load MFE with graceful error handling
 * If MFE fails to load, show fallback component instead of crashing
 */
function loadMfe(config: MfeConfig) {
  return () =>
    loadRemoteModule({
      type: 'module',
      remoteEntry: config.url,
      exposedModule: config.exposedModule,
    })
      .then((m) => m[config.routesExport])
      .catch((error) => {
        console.error(`Failed to load MFE: ${config.name}`, error);

        // Return fallback route - other MFEs continue working
        return [
          {
            path: '**',
            loadComponent: () =>
              import('./fallback/mfe-error.component').then(
                (m) => m.MfeErrorComponent
              ),
            data: {
              mfeName: config.name,
              displayName: config.displayName,
              error: error.message,
            },
          },
        ];
      });
}

export const APP_ROUTES: Routes = [
  // =========================================================================
  // AUTH ROUTES (No layout)
  // =========================================================================
  {
    path: 'auth',
    loadChildren: () =>
      import('./features/auth/auth.routes').then((m) => m.AUTH_ROUTES),
  },

  // =========================================================================
  // MAIN APPLICATION (With layout)
  // =========================================================================
  {
    path: '',
    loadComponent: () =>
      import('./layout/main-layout.component').then(
        (m) => m.MainLayoutComponent
      ),
    canActivate: [], // TODO: Add AuthGuard
    children: [
      { path: '', redirectTo: 'dashboard', pathMatch: 'full' },

      // Dashboard (Shell feature)
      {
        path: 'dashboard',
        loadComponent: () =>
          import('./features/dashboard/dashboard.component').then(
            (m) => m.DashboardComponent
          ),
        title: 'Dashboard',
      },

      // =====================================================================
      // OPERATIONS MFE - Booking, Flight, Dispatch, Weather
      // High criticality - Core business operations
      // =====================================================================
      {
        path: 'booking',
        loadChildren: loadMfe(MFE_CONFIG.operations),
        data: { mfe: 'operations', section: 'booking' },
      },
      {
        path: 'flights',
        loadChildren: loadMfe(MFE_CONFIG.operations),
        data: { mfe: 'operations', section: 'flights' },
      },
      {
        path: 'dispatch',
        loadChildren: loadMfe(MFE_CONFIG.operations),
        data: { mfe: 'operations', section: 'dispatch' },
      },

      // =====================================================================
      // TRAINING MFE - Syllabus, Progress, Exams, Certificates
      // Medium criticality - Training management
      // =====================================================================
      {
        path: 'training',
        loadChildren: loadMfe(MFE_CONFIG.training),
        data: { mfe: 'training' },
      },

      // =====================================================================
      // ADMIN MFE - Users, Aircraft, Organizations, Finance, Reports
      // Low criticality - Administrative functions
      // =====================================================================
      {
        path: 'admin',
        loadChildren: loadMfe(MFE_CONFIG.admin),
        data: { mfe: 'admin', roles: ['admin', 'super_admin'] },
      },

      // Settings (Shell feature)
      {
        path: 'settings',
        loadChildren: () =>
          import('./features/settings/settings.routes').then(
            (m) => m.SETTINGS_ROUTES
          ),
        title: 'Settings',
      },
    ],
  },

  // 404 - Redirect to dashboard
  { path: '**', redirectTo: 'dashboard' },
];
