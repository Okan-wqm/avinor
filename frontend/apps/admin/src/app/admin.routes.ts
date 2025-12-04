import { Routes } from '@angular/router';

export const adminRoutes: Routes = [
  {
    path: '',
    children: [
      {
        path: '',
        redirectTo: 'users',
        pathMatch: 'full',
      },
      // User Management
      {
        path: 'users',
        loadComponent: () =>
          import('./features/users/user-list.component').then(
            (m) => m.UserListComponent
          ),
      },
      {
        path: 'users/new',
        loadComponent: () =>
          import('./features/users/user-form.component').then(
            (m) => m.UserFormComponent
          ),
      },
      {
        path: 'users/:id',
        loadComponent: () =>
          import('./features/users/user-detail.component').then(
            (m) => m.UserDetailComponent
          ),
      },
      {
        path: 'users/:id/edit',
        loadComponent: () =>
          import('./features/users/user-form.component').then(
            (m) => m.UserFormComponent
          ),
      },
      // Aircraft Management
      {
        path: 'aircraft',
        loadComponent: () =>
          import('./features/aircraft/aircraft-list.component').then(
            (m) => m.AircraftListComponent
          ),
      },
      {
        path: 'aircraft/new',
        loadComponent: () =>
          import('./features/aircraft/aircraft-form.component').then(
            (m) => m.AircraftFormComponent
          ),
      },
      {
        path: 'aircraft/:id',
        loadComponent: () =>
          import('./features/aircraft/aircraft-detail.component').then(
            (m) => m.AircraftDetailComponent
          ),
      },
      // Organization Management
      {
        path: 'organizations',
        loadComponent: () =>
          import('./features/organizations/organization-list.component').then(
            (m) => m.OrganizationListComponent
          ),
      },
      {
        path: 'organizations/:id',
        loadComponent: () =>
          import('./features/organizations/organization-detail.component').then(
            (m) => m.OrganizationDetailComponent
          ),
      },
      // Finance
      {
        path: 'finance',
        loadComponent: () =>
          import('./features/finance/finance-dashboard.component').then(
            (m) => m.FinanceDashboardComponent
          ),
      },
      {
        path: 'finance/invoices',
        loadComponent: () =>
          import('./features/finance/invoice-list.component').then(
            (m) => m.InvoiceListComponent
          ),
      },
      {
        path: 'finance/pricing',
        loadComponent: () =>
          import('./features/finance/pricing-rules.component').then(
            (m) => m.PricingRulesComponent
          ),
      },
      // Reports
      {
        path: 'reports',
        loadComponent: () =>
          import('./features/reports/reports-dashboard.component').then(
            (m) => m.ReportsDashboardComponent
          ),
      },
      // Settings
      {
        path: 'settings',
        loadComponent: () =>
          import('./features/settings/settings.component').then(
            (m) => m.SettingsComponent
          ),
      },
    ],
  },
];
