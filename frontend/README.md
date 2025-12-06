# Flight Training Management System - Frontend

Modern, scalable micro-frontend application for professional flight training organizations built with Angular 18+, Nx Monorepo, and Module Federation.

## Overview

This frontend provides a comprehensive user interface for managing all aspects of flight training operations including booking, scheduling, training progress, certificates, and administration.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              BROWSER                                         │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                         SHELL APPLICATION                              │  │
│  │   ┌──────────────┐  ┌────────────────────────┐  ┌─────────────────┐   │  │
│  │   │    Header    │  │     Active MFE          │  │    Sidebar      │   │  │
│  │   │  - Logo      │  │                         │  │                 │   │  │
│  │   │  - Search    │  │   Operations  ← Port    │  │  - Dashboard    │   │  │
│  │   │  - User      │  │   Training      4201    │  │  - Booking      │   │  │
│  │   │  - Theme     │  │   Admin         4202    │  │  - Flights      │   │  │
│  │   │              │  │                 4203    │  │  - Training     │   │  │
│  │   └──────────────┘  └────────────────────────┘  │  - Admin        │   │  │
│  │                                                  └─────────────────┘   │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                      │                                       │
│                                      │ REST API                              │
│                                      ▼                                       │
│                           ┌──────────────────┐                               │
│                           │   API Gateway    │                               │
│                           │   (Nginx/Kong)   │                               │
│                           └──────────────────┘                               │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Micro-Frontend Structure

| Application | Port | Description |
|------------|------|-------------|
| **Shell** | 4200 | Host application - Layout, Authentication, Dashboard, Settings |
| **Operations** | 4201 | Core operations - Booking, Flights, Dispatch, Weather |
| **Training** | 4202 | Training management - Syllabus, Progress, Exams, Certificates, Courses |
| **Admin** | 4203 | Administration - Users, Aircraft, Organizations, Finance, Reports |

### Shell Application (Host)

The shell serves as the host application and provides:

- **Authentication**: Login, logout, password reset, session management
- **Layout**: Header, sidebar, main content area with responsive design
- **Dashboard**: Overview widgets, notifications, quick actions
- **Settings**: User preferences, theme, notifications
- **Shared Services**: Auth store, theme service, toast notifications
- **Error Handling**: Global error handler, 404/500 pages
- **Guards**: Auth guard, role-based access control

### Operations MFE

Core business operations module:

| Feature | Route | Description |
|---------|-------|-------------|
| Booking | `/booking` | Aircraft and instructor scheduling |
| Flights | `/flights` | Flight records, logbook entries |
| Dispatch | `/dispatch` | Daily dispatch board, flight assignments |
| Weather | `/weather` | Weather briefings, METAR/TAF |

### Training MFE

Training and progress management:

| Feature | Route | Description |
|---------|-------|-------------|
| Syllabus | `/training/syllabus` | Training syllabi, lesson plans |
| Progress | `/training/progress` | Student progress tracking |
| Exams | `/training/exams` | Theory exams, results |
| Courses | `/training/courses` | Online course player |
| Certificates | `/training/certificates` | License and rating certificates |

### Admin MFE

Administrative functions (role-protected):

| Feature | Route | Description |
|---------|-------|-------------|
| Users | `/admin/users` | User management, roles |
| Aircraft | `/admin/aircraft` | Fleet management |
| Organizations | `/admin/organizations` | Multi-tenant management |
| Finance | `/admin/finance` | Invoices, pricing rules |
| Reports | `/admin/reports` | Analytics dashboard |
| Settings | `/admin/settings` | System configuration |

## Technology Stack

| Category | Technology |
|----------|------------|
| Framework | Angular 18+ (Standalone Components) |
| State Management | Angular Signals |
| Build System | Nx 19 Monorepo |
| Module Federation | @angular-architects/module-federation |
| Styling | Tailwind CSS 3.x |
| HTTP | Angular HttpClient with interceptors |
| Testing | Jest + Angular Testing Library |
| E2E Testing | Playwright |
| Code Quality | ESLint, Prettier |

## Project Structure

```
frontend/
├── apps/
│   ├── shell/                          # Host application
│   │   ├── src/
│   │   │   ├── app/
│   │   │   │   ├── core/               # Core services & guards
│   │   │   │   │   ├── guards/         # Auth, role guards
│   │   │   │   │   ├── handlers/       # Global error handler
│   │   │   │   │   ├── interceptors/   # HTTP interceptors
│   │   │   │   │   └── services/       # Auth store, theme, etc.
│   │   │   │   ├── features/           # Shell features
│   │   │   │   │   ├── auth/           # Login, password reset
│   │   │   │   │   ├── dashboard/      # Main dashboard
│   │   │   │   │   ├── settings/       # User settings
│   │   │   │   │   └── errors/         # Error pages
│   │   │   │   ├── layout/             # Header, sidebar, layout
│   │   │   │   ├── shared/             # Shared components
│   │   │   │   │   ├── animations/     # Route & micro animations
│   │   │   │   │   └── components/     # Button, card, toast, etc.
│   │   │   │   ├── fallback/           # MFE error fallback
│   │   │   │   ├── app.component.ts
│   │   │   │   ├── app.config.ts
│   │   │   │   └── app.routes.ts
│   │   │   └── environments/
│   │   └── webpack.config.js           # Module Federation config
│   │
│   ├── operations/                     # Operations MFE
│   │   ├── src/app/
│   │   │   ├── features/
│   │   │   │   ├── booking/
│   │   │   │   ├── flights/
│   │   │   │   ├── dispatch/
│   │   │   │   └── weather/
│   │   │   └── operations.routes.ts
│   │   └── webpack.config.js
│   │
│   ├── training/                       # Training MFE
│   │   ├── src/app/
│   │   │   ├── features/
│   │   │   │   ├── syllabus/
│   │   │   │   ├── progress/
│   │   │   │   ├── exams/
│   │   │   │   ├── courses/
│   │   │   │   └── certificates/
│   │   │   └── training.routes.ts
│   │   └── webpack.config.js
│   │
│   └── admin/                          # Admin MFE
│       ├── src/app/
│       │   ├── features/
│       │   │   ├── users/
│       │   │   ├── aircraft/
│       │   │   ├── organizations/
│       │   │   ├── finance/
│       │   │   ├── reports/
│       │   │   └── settings/
│       │   └── admin.routes.ts
│       └── webpack.config.js
│
├── libs/                               # Shared libraries
│   ├── shared/
│   │   ├── ui/                         # Shared UI components
│   │   │   └── src/lib/
│   │   │       ├── components/
│   │   │       │   ├── button/
│   │   │       │   ├── card/
│   │   │       │   ├── badge/
│   │   │       │   ├── loading/
│   │   │       │   └── empty-state/
│   │   │       └── pipes/
│   │   │           └── relative-time.pipe.ts
│   │   ├── data-access/                # HTTP services
│   │   │   └── src/lib/
│   │   │       ├── api.service.ts
│   │   │       └── base-http.service.ts
│   │   ├── models/                     # TypeScript interfaces
│   │   └── util/                       # Utilities
│   └── domain/                         # Domain-specific libs
│       ├── booking/
│       ├── flight/
│       └── training/
│
├── docker/
│   ├── nginx.conf                      # Production Nginx config
│   └── default.conf                    # Server configuration
├── Dockerfile                          # Multi-stage build
├── nx.json                             # Nx configuration
├── package.json
└── tailwind.config.js                  # Tailwind configuration
```

## Quick Start

### Prerequisites

- Node.js 20+
- npm 10+ or pnpm
- Nx CLI: `npm install -g nx`

### Installation

```bash
# Clone repository
git clone <repository-url>
cd frontend

# Install dependencies
npm install
```

### Development

```bash
# Start shell only (port 4200)
npm start

# Start all MFEs simultaneously
npm run start:all

# Start individual MFE
nx serve shell          # Port 4200
nx serve operations     # Port 4201
nx serve training       # Port 4202
nx serve admin          # Port 4203
```

### Building

```bash
# Build all applications for production
npm run build:all

# Build specific app
nx build shell --configuration=production
nx build operations --configuration=production
nx build training --configuration=production
nx build admin --configuration=production
```

### Testing

```bash
# Run all tests
nx run-many --target=test --all

# Run tests for specific app
nx test shell
nx test operations

# Run tests with coverage
nx test shell --coverage

# E2E tests
nx e2e shell-e2e
```

### Code Quality

```bash
# Lint all projects
nx run-many --target=lint --all

# Lint specific project
nx lint shell

# Format code
npm run format
```

## Shared Components

### UI Components (`libs/shared/ui`)

| Component | Description |
|-----------|-------------|
| `ButtonComponent` | Primary, secondary, outline button variants |
| `CardComponent` | Content card with header, body, footer |
| `BadgeComponent` | Status badges with color variants |
| `LoadingComponent` | Loading spinner and skeleton |
| `EmptyStateComponent` | Empty data placeholder |

### Shell Components (`apps/shell/src/app/shared`)

| Component | Description |
|-----------|-------------|
| `ToastComponent` | Toast notifications with ToastService |
| `DataTableComponent` | Sortable, paginated data table |
| `SkeletonComponent` | Loading skeleton placeholders |
| `ButtonComponent` | Extended button with loading state |
| `CardComponent` | Shell-specific card component |

### Animations (`apps/shell/src/app/shared/animations`)

| Animation | Usage |
|-----------|-------|
| `routeAnimations` | Page transition animations |
| `fadeIn` | Fade in micro-interaction |
| `slideIn` | Slide in from direction |
| `scaleIn` | Scale up animation |

## Core Services

### Auth Store (`apps/shell/src/app/core/services/auth.store.ts`)

Signal-based authentication state management:

```typescript
// Inject and use
authStore = inject(AuthStore);

// Reactive state
user = this.authStore.user;
isAuthenticated = this.authStore.isAuthenticated;
isLoading = this.authStore.isLoading;

// Actions
this.authStore.login(credentials);
this.authStore.logout();
this.authStore.refreshToken();
```

### Theme Service (`apps/shell/src/app/core/services/theme.service.ts`)

Dark/light theme management:

```typescript
themeService = inject(ThemeService);
themeService.toggleTheme();
currentTheme = themeService.currentTheme;
```

### Toast Service (`apps/shell/src/app/shared/components/toast`)

Notification system:

```typescript
toastService = inject(ToastService);
toastService.success('Operation completed');
toastService.error('An error occurred');
toastService.warning('Please review');
toastService.info('Information');
```

## HTTP Interceptors

| Interceptor | Function |
|-------------|----------|
| `AuthInterceptor` | Attaches JWT token to requests |
| `ErrorInterceptor` | Global HTTP error handling |
| `LoadingInterceptor` | Automatic loading state management |

## Route Guards

| Guard | Purpose |
|-------|---------|
| `authGuard` | Protects authenticated routes |
| `noAuthGuard` | Redirects authenticated users (login page) |
| `roleGuard` | Role-based access control |

## Environment Configuration

### Development (`environment.ts`)

```typescript
export const environment = {
  production: false,
  apiUrl: 'http://localhost',
  mfe: {
    operations: 'http://localhost:4201/remoteEntry.js',
    training: 'http://localhost:4202/remoteEntry.js',
    admin: 'http://localhost:4203/remoteEntry.js',
  },
};
```

### Production (`environment.prod.ts`)

```typescript
export const environment = {
  production: true,
  apiUrl: 'https://api.flighttraining.app',
  mfe: {
    operations: 'https://cdn.flighttraining.app/mfe/operations/remoteEntry.js',
    training: 'https://cdn.flighttraining.app/mfe/training/remoteEntry.js',
    admin: 'https://cdn.flighttraining.app/mfe/admin/remoteEntry.js',
  },
};
```

## Docker Deployment

```bash
# Build Docker image
docker build -t ftms-frontend .

# Run container
docker run -p 80:80 ftms-frontend

# With environment variables
docker run -p 80:80 \
  -e API_URL=https://api.example.com \
  ftms-frontend
```

### Docker Compose

```yaml
services:
  frontend:
    build: ./frontend
    ports:
      - "80:80"
    environment:
      - API_URL=${API_URL}
    depends_on:
      - api-gateway
```

## PWA Features

The application supports Progressive Web App features:

- **Service Worker**: Offline caching and background sync
- **Web Manifest**: Installable on mobile devices
- **Cache Strategies**: API response caching for offline access
- **Push Notifications**: Real-time notification support

## Accessibility

- WCAG 2.1 AA compliance target
- Skip links for keyboard navigation
- ARIA labels on interactive elements
- Focus management for route changes
- High contrast theme support

## Browser Support

| Browser | Version |
|---------|---------|
| Chrome | Latest 2 versions |
| Firefox | Latest 2 versions |
| Safari | Latest 2 versions |
| Edge | Latest 2 versions |

## Performance Optimization

- **Code Splitting**: Lazy loading for all routes
- **Module Federation**: Independent MFE bundles
- **Tree Shaking**: Unused code elimination
- **Compression**: Gzip/Brotli for production
- **Image Optimization**: Lazy loading, WebP format
- **Bundle Analysis**: `nx build shell --stats-json`

## Contributing

1. Create feature branch from `develop`
2. Follow Angular style guide
3. Write tests for new features
4. Run `nx affected:lint` and `nx affected:test`
5. Submit pull request

## License

Proprietary - All rights reserved.
