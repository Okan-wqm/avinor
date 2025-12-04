# Flight Training System - Frontend

Angular 18+ Micro-Frontend architecture using Nx Monorepo and Module Federation.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         BROWSER                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                    SHELL APPLICATION                       │  │
│  │   ┌─────────┐  ┌──────────────────────┐  ┌─────────────┐  │  │
│  │   │ Header  │  │    Active MFE        │  │  Sidebar    │  │  │
│  │   │         │  │                      │  │             │  │  │
│  │   │         │  │  Operations / Admin  │  │ - Dispatch  │  │  │
│  │   │         │  │  Training            │  │ - Booking   │  │  │
│  │   │         │  │                      │  │ - Flights   │  │  │
│  │   └─────────┘  └──────────────────────┘  └─────────────┘  │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              │                                   │
│                              │ REST API                         │
│                              ▼                                   │
│                      ┌───────────────┐                          │
│                      │ Kong Gateway  │                          │
│                      └───────────────┘                          │
└─────────────────────────────────────────────────────────────────┘
```

## MFE Structure

| App | Port | Description |
|-----|------|-------------|
| Shell | 4200 | Host application, layout, auth |
| Operations | 4201 | Booking, Flight, Dispatch, Weather |
| Training | 4202 | Syllabus, Progress, Exams, Certificates |
| Admin | 4203 | Users, Aircraft, Organizations, Finance |

## Quick Start

```bash
# Install dependencies
npm install

# Start shell only
npm start

# Start all MFEs
npm run start:all

# Build for production
npm run build:all
```

## Development Commands

```bash
# Serve individual apps
nx serve shell
nx serve operations
nx serve training
nx serve admin

# Build specific app
nx build shell --configuration=production

# Run tests
nx test shell
nx run-many --target=test --all

# Lint
nx lint shell
nx run-many --target=lint --all

# Generate component
nx g @nx/angular:component my-component --project=shell

# View dependency graph
nx graph
```

## Project Structure

```
frontend/
├── apps/
│   ├── shell/              # Host application
│   ├── operations/         # Operations MFE
│   ├── training/           # Training MFE
│   └── admin/              # Admin MFE
├── libs/
│   ├── shared/
│   │   ├── ui/            # Shared UI components
│   │   ├── auth/          # Authentication
│   │   ├── data-access/   # HTTP services
│   │   ├── util/          # Utilities, pipes
│   │   └── models/        # Shared types
│   └── domain/
│       ├── booking/       # Booking domain
│       ├── flight/        # Flight domain
│       ├── training/      # Training domain
│       └── ...
├── docker/
│   ├── nginx.conf
│   └── default.conf
├── Dockerfile
└── package.json
```

## Key Technologies

- **Angular 18+** - Latest Angular with Signals
- **Nx 19** - Monorepo management
- **Module Federation** - Micro-frontend architecture
- **Tailwind CSS** - Utility-first styling
- **REST API** - Direct API consumption (no GraphQL layer)

## Differences from Original Plan

1. **REST instead of GraphQL** - Backend is Django REST, no need for GraphQL layer
2. **3 MFEs instead of 6** - Consolidated for better maintainability
3. **Signals only** - No NgRx, using Angular Signals for state
4. **Tailwind only** - No PrimeNG, cleaner styling approach

## Environment Configuration

Development:
- API: `http://localhost` (Kong Gateway)
- MFEs: `http://localhost:420X`

Production:
- API: `https://api.flighttraining.app`
- MFEs: `https://cdn.flighttraining.app/mfe/`

## Docker

```bash
# Build image
docker build -t fts-frontend .

# Run container
docker run -p 80:80 fts-frontend
```

## PWA Features

- Service Worker for offline support
- Caching strategies for API responses
- Web manifest for installability
