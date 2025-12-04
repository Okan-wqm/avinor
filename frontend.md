# 16. ANGULAR MICRO-FRONTEND MİMARİSİ

> **Flight Training System - Professional Aviation Frontend**
> 
> Uçuş okulları için tasarlanmış, havacılık sektörünün güvenilirlik 
> standartlarına uygun, enterprise-grade Angular uygulaması.

---

## İÇİNDEKİLER

1. [Mimari Karar](#1-mimari-karar)
2. [Teknoloji Stack](#2-teknoloji-stack)
3. [Nx Monorepo Yapısı](#3-nx-monorepo-yapısı)
4. [Shell Application](#4-shell-application)
5. [Micro-Frontend Modülleri](#5-micro-frontend-modülleri)
6. [Shared Libraries](#6-shared-libraries)
7. [Design System](#7-design-system)
8. [State Management](#8-state-management)
9. [GraphQL Integration](#9-graphql-integration)
10. [Authentication & Authorization](#10-authentication--authorization)
11. [Error Handling & Fault Tolerance](#11-error-handling--fault-tolerance)
12. [Real-time Features](#12-real-time-features)
13. [Testing Strategy](#13-testing-strategy)
14. [Performance Optimization](#14-performance-optimization)
15. [CI/CD & Deployment](#15-cicd--deployment)

---

## 1. MİMARİ KARAR

### 1.1 Neden Micro-Frontend?

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         MİMARİ KARAR                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ✅ KARAR: Micro-Frontend + Nx Monorepo                                    │
│                                                                             │
│  ═══════════════════════════════════════════════════════════════════════   │
│                                                                             │
│  GEREKÇE: DEPLOYMENT ISOLATION                                             │
│  ─────────────────────────────────────────────────────────────────────────  │
│                                                                             │
│  "Booking MFE bozuk deploy edilirse, Flight MFE çalışmaya devam eder"      │
│                                                                             │
│  Havacılık sektöründe kritik:                                              │
│  • Pazartesi sabah 07:00 - Dispatch board açılmalı                         │
│  • Finance modülünde bug var → Uçuşlar ETKİLENMEMELİ                       │
│  • Her modül bağımsız deploy, bağımsız rollback                            │
│                                                                             │
│  ═══════════════════════════════════════════════════════════════════════   │
│                                                                             │
│  ⚠️ NOT: Runtime Fault Isolation DEĞİL                                     │
│  ─────────────────────────────────────────────────────────────────────────  │
│  Tüm MFE'ler aynı browser'da çalışır.                                      │
│  Memory leak, infinite loop herkesi etkiler.                               │
│  AMA: Error boundaries ile %90 hata yakalanır.                             │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Mimari Genel Bakış

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         FRONTEND ARCHITECTURE                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│                              BROWSER                                        │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                                                                      │  │
│  │   ┌────────────────────────────────────────────────────────────┐    │  │
│  │   │                    SHELL APPLICATION                        │    │  │
│  │   │                                                             │    │  │
│  │   │  ┌─────────┐  ┌──────────────────────────┐  ┌───────────┐  │    │  │
│  │   │  │ Header  │  │      Main Router         │  │  Notif    │  │    │  │
│  │   │  │ + User  │  │                          │  │  Panel    │  │    │  │
│  │   │  │ + Org   │  │  ┌────────────────────┐  │  │           │  │    │  │
│  │   │  └─────────┘  │  │   ACTIVE MFE       │  │  └───────────┘  │    │  │
│  │   │               │  │                    │  │                 │    │  │
│  │   │  ┌─────────┐  │  │  Booking / Flight  │  │                 │    │  │
│  │   │  │Sidebar  │  │  │  Training / Admin  │  │                 │    │  │
│  │   │  │         │  │  │  Finance / Reports │  │                 │    │  │
│  │   │  │ - Book  │  │  │                    │  │                 │    │  │
│  │   │  │ - Fly   │  │  └────────────────────┘  │                 │    │  │
│  │   │  │ - Train │  │                          │                 │    │  │
│  │   │  │ - Admin │  └──────────────────────────┘                 │    │  │
│  │   │  └─────────┘                                               │    │  │
│  │   │                                                             │    │  │
│  │   └────────────────────────────────────────────────────────────┘    │  │
│  │                                                                      │  │
│  │   MFE'ler lazy load edilir:                                         │  │
│  │   /booking/*  → Booking MFE (remoteEntry.js)                        │  │
│  │   /flights/*  → Flight MFE (remoteEntry.js)                         │  │
│  │   /training/* → Training MFE (remoteEntry.js)                       │  │
│  │                                                                      │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│                                    │                                        │
│                                    │ GraphQL + WebSocket                   │
│                                    ▼                                        │
│                           ┌────────────────┐                               │
│                           │  API Gateway   │                               │
│                           │   /graphql     │                               │
│                           └────────────────┘                               │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.3 MFE Criticality Matrix

| MFE | Kritiklik | Açıklama | Bozulursa |
|-----|-----------|----------|-----------|
| **Shell** | 🔴 MAX | Ana uygulama, layout, auth | Hiçbir şey çalışmaz |
| **Booking** | 🔴 HIGH | Rezervasyon, dispatch board | Günlük ops durur |
| **Flight** | 🔴 HIGH | Uçuş kayıtları, logbook | Kayıt tutulamaz |
| **Training** | 🟠 MEDIUM | Eğitim progress, syllabus | Eğitim takibi durur |
| **Admin** | 🟡 LOW | Kullanıcı/org yönetimi | Sadece admin etkilenir |
| **Finance** | 🟡 LOW | Fatura, ödeme | Bekleyebilir |
| **Reports** | 🟢 LOWEST | Dashboard, raporlar | Kritik değil |

---

## 2. TEKNOLOJİ STACK

### 2.1 Core Technologies

| Layer | Technology | Version | Why |
|-------|------------|---------|-----|
| Framework | Angular | 18+ | Enterprise standard |
| Micro-Frontend | Module Federation | Webpack 5 | Native lazy loading |
| Monorepo | Nx | 19+ | Affected builds, shared libs |
| State (Simple) | Angular Signals | Built-in | Reactive, simple |
| State (Complex) | NgRx Signals | 18+ | Global state |
| API Client | Apollo Angular | 7+ | GraphQL |
| UI Framework | Tailwind CSS | 3.4+ | Utility-first |
| UI Components | PrimeNG + Custom | 17+ | Rich widgets |
| Forms | Reactive Forms | Built-in | Validation |
| Charts | Chart.js | 4+ | Dashboards |
| Date/Time | date-fns + date-fns-tz | 3+ | Timezone support |
| i18n | @ngx-translate | 15+ | Multi-language |
| Testing Unit | Jest | 29+ | Fast, simple |
| Testing E2E | Playwright | 1.40+ | Cross-browser |

### 2.2 Aviation-Specific Dependencies

```json
{
  "dependencies": {
    "date-fns": "^3.0.0",
    "date-fns-tz": "^2.0.0",
    "metar-taf-parser": "^7.0.0",
    "pdfmake": "^0.2.0",
    "exceljs": "^4.4.0",
    "@angular/google-maps": "^18.0.0",
    "signature_pad": "^4.2.0"
  }
}
```

---

## 3. NX MONOREPO YAPISI

### 3.1 Proje Yapısı

```
flight-training-frontend/
│
├── apps/                                    # APPLICATIONS
│   │
│   ├── shell/                               # 🏠 HOST APPLICATION
│   │   ├── src/
│   │   │   ├── app/
│   │   │   │   ├── core/                    # Singleton services
│   │   │   │   │   ├── services/
│   │   │   │   │   │   ├── mfe-loader.service.ts
│   │   │   │   │   │   ├── health-check.service.ts
│   │   │   │   │   │   └── theme.service.ts
│   │   │   │   │   └── interceptors/
│   │   │   │   │
│   │   │   │   ├── layout/                  # Shell layout
│   │   │   │   │   ├── main-layout/
│   │   │   │   │   │   └── main-layout.component.ts
│   │   │   │   │   ├── header/
│   │   │   │   │   │   └── header.component.ts
│   │   │   │   │   ├── sidebar/
│   │   │   │   │   │   └── sidebar.component.ts
│   │   │   │   │   └── notification-panel/
│   │   │   │   │       └── notification-panel.component.ts
│   │   │   │   │
│   │   │   │   ├── features/
│   │   │   │   │   ├── dashboard/           # Main dashboard
│   │   │   │   │   │   └── dashboard.component.ts
│   │   │   │   │   ├── auth/                # Login/logout
│   │   │   │   │   │   ├── login/
│   │   │   │   │   │   └── auth.routes.ts
│   │   │   │   │   └── settings/
│   │   │   │   │       └── settings.component.ts
│   │   │   │   │
│   │   │   │   ├── fallback/                # MFE error fallbacks
│   │   │   │   │   ├── mfe-error.component.ts
│   │   │   │   │   └── mfe-loading.component.ts
│   │   │   │   │
│   │   │   │   ├── app.component.ts
│   │   │   │   ├── app.config.ts
│   │   │   │   └── app.routes.ts
│   │   │   │
│   │   │   ├── environments/
│   │   │   │   ├── environment.ts           # Development
│   │   │   │   ├── environment.prod.ts      # Production
│   │   │   │   └── environment.staging.ts   # Staging
│   │   │   │
│   │   │   ├── styles/
│   │   │   │   ├── _variables.scss
│   │   │   │   ├── _aviation-theme.scss
│   │   │   │   └── styles.scss
│   │   │   │
│   │   │   ├── assets/
│   │   │   │   ├── images/
│   │   │   │   ├── icons/
│   │   │   │   └── i18n/
│   │   │   │
│   │   │   └── main.ts
│   │   │
│   │   ├── webpack.config.js                # Module Federation
│   │   ├── project.json
│   │   └── tsconfig.app.json
│   │
│   │
│   ├── booking/                             # ✈️ BOOKING MFE
│   │   ├── src/
│   │   │   ├── app/
│   │   │   │   ├── features/
│   │   │   │   │   ├── calendar/            # Full calendar view
│   │   │   │   │   │   ├── booking-calendar.component.ts
│   │   │   │   │   │   └── calendar.service.ts
│   │   │   │   │   │
│   │   │   │   │   ├── dispatch-board/      # Daily dispatch board
│   │   │   │   │   │   ├── dispatch-board.component.ts
│   │   │   │   │   │   └── dispatch-board.component.html
│   │   │   │   │   │
│   │   │   │   │   ├── resource-view/       # Aircraft/instructor view
│   │   │   │   │   │   └── resource-view.component.ts
│   │   │   │   │   │
│   │   │   │   │   ├── quick-book/          # Quick booking form
│   │   │   │   │   │   ├── quick-book.component.ts
│   │   │   │   │   │   └── quick-book-form.component.ts
│   │   │   │   │   │
│   │   │   │   │   └── booking-detail/      # Booking details
│   │   │   │   │       └── booking-detail.component.ts
│   │   │   │   │
│   │   │   │   ├── booking.routes.ts
│   │   │   │   └── remote-entry.ts          # MFE entry point
│   │   │   │
│   │   │   └── bootstrap.ts
│   │   │
│   │   ├── webpack.config.js
│   │   └── project.json
│   │
│   │
│   ├── flight/                              # 🛩️ FLIGHT MFE
│   │   ├── src/
│   │   │   ├── app/
│   │   │   │   ├── features/
│   │   │   │   │   ├── flight-log/          # Start/stop flight
│   │   │   │   │   │   ├── start-flight.component.ts
│   │   │   │   │   │   ├── end-flight.component.ts
│   │   │   │   │   │   └── flight-timer.component.ts
│   │   │   │   │   │
│   │   │   │   │   ├── logbook/             # Pilot logbook
│   │   │   │   │   │   ├── pilot-logbook.component.ts
│   │   │   │   │   │   ├── logbook-entry.component.ts
│   │   │   │   │   │   └── logbook-export.service.ts
│   │   │   │   │   │
│   │   │   │   │   ├── currency/            # Currency tracking
│   │   │   │   │   │   ├── currency-dashboard.component.ts
│   │   │   │   │   │   └── currency-card.component.ts
│   │   │   │   │   │
│   │   │   │   │   └── flight-review/       # Post-flight review
│   │   │   │   │       ├── flight-review.component.ts
│   │   │   │   │       └── grade-maneuver.component.ts
│   │   │   │   │
│   │   │   │   ├── flight.routes.ts
│   │   │   │   └── remote-entry.ts
│   │   │   │
│   │   │   └── bootstrap.ts
│   │   │
│   │   └── webpack.config.js
│   │
│   │
│   ├── training/                            # 📚 TRAINING MFE
│   │   ├── src/
│   │   │   ├── app/
│   │   │   │   ├── features/
│   │   │   │   │   ├── syllabus/            # Training syllabus
│   │   │   │   │   │   ├── syllabus-list.component.ts
│   │   │   │   │   │   ├── syllabus-detail.component.ts
│   │   │   │   │   │   └── lesson-item.component.ts
│   │   │   │   │   │
│   │   │   │   │   ├── progress/            # Student progress
│   │   │   │   │   │   ├── student-progress.component.ts
│   │   │   │   │   │   ├── progress-chart.component.ts
│   │   │   │   │   │   └── milestone-tracker.component.ts
│   │   │   │   │   │
│   │   │   │   │   ├── lessons/             # Lesson records
│   │   │   │   │   │   ├── lesson-record.component.ts
│   │   │   │   │   │   └── instructor-notes.component.ts
│   │   │   │   │   │
│   │   │   │   │   ├── examinations/        # Written/practical exams
│   │   │   │   │   │   ├── exam-list.component.ts
│   │   │   │   │   │   └── exam-result.component.ts
│   │   │   │   │   │
│   │   │   │   │   └── certificates/        # Certificates
│   │   │   │   │       ├── certificate-list.component.ts
│   │   │   │   │       └── certificate-view.component.ts
│   │   │   │   │
│   │   │   │   ├── training.routes.ts
│   │   │   │   └── remote-entry.ts
│   │   │   │
│   │   │   └── bootstrap.ts
│   │   │
│   │   └── webpack.config.js
│   │
│   │
│   ├── admin/                               # ⚙️ ADMIN MFE
│   │   ├── src/
│   │   │   ├── app/
│   │   │   │   ├── features/
│   │   │   │   │   ├── users/               # User management
│   │   │   │   │   │   ├── user-list.component.ts
│   │   │   │   │   │   ├── user-form.component.ts
│   │   │   │   │   │   └── user-detail.component.ts
│   │   │   │   │   │
│   │   │   │   │   ├── organizations/       # Org settings
│   │   │   │   │   │   ├── org-settings.component.ts
│   │   │   │   │   │   └── org-branding.component.ts
│   │   │   │   │   │
│   │   │   │   │   ├── aircraft/            # Fleet management
│   │   │   │   │   │   ├── aircraft-list.component.ts
│   │   │   │   │   │   ├── aircraft-form.component.ts
│   │   │   │   │   │   └── aircraft-maintenance.component.ts
│   │   │   │   │   │
│   │   │   │   │   ├── instructors/         # Instructor management
│   │   │   │   │   │   ├── instructor-list.component.ts
│   │   │   │   │   │   └── instructor-schedule.component.ts
│   │   │   │   │   │
│   │   │   │   │   └── system/              # System settings
│   │   │   │   │       ├── system-settings.component.ts
│   │   │   │   │       └── audit-log.component.ts
│   │   │   │   │
│   │   │   │   ├── admin.routes.ts
│   │   │   │   └── remote-entry.ts
│   │   │   │
│   │   │   └── bootstrap.ts
│   │   │
│   │   └── webpack.config.js
│   │
│   │
│   ├── finance/                             # 💰 FINANCE MFE
│   │   ├── src/
│   │   │   ├── app/
│   │   │   │   ├── features/
│   │   │   │   │   ├── invoices/            # Invoice management
│   │   │   │   │   │   ├── invoice-list.component.ts
│   │   │   │   │   │   ├── invoice-detail.component.ts
│   │   │   │   │   │   └── create-invoice.component.ts
│   │   │   │   │   │
│   │   │   │   │   ├── payments/            # Payment processing
│   │   │   │   │   │   ├── payment-list.component.ts
│   │   │   │   │   │   └── record-payment.component.ts
│   │   │   │   │   │
│   │   │   │   │   ├── accounts/            # Account statements
│   │   │   │   │   │   ├── account-statement.component.ts
│   │   │   │   │   │   └── balance-summary.component.ts
│   │   │   │   │   │
│   │   │   │   │   └── pricing/             # Pricing rules
│   │   │   │   │       ├── pricing-rules.component.ts
│   │   │   │   │       └── rate-card.component.ts
│   │   │   │   │
│   │   │   │   ├── finance.routes.ts
│   │   │   │   └── remote-entry.ts
│   │   │   │
│   │   │   └── bootstrap.ts
│   │   │
│   │   └── webpack.config.js
│   │
│   │
│   └── reports/                             # 📊 REPORTS MFE
│       ├── src/
│       │   ├── app/
│       │   │   ├── features/
│       │   │   │   ├── dashboards/          # Analytics dashboards
│       │   │   │   │   ├── main-dashboard.component.ts
│       │   │   │   │   ├── flight-stats.component.ts
│       │   │   │   │   └── revenue-chart.component.ts
│       │   │   │   │
│       │   │   │   ├── flight-reports/      # Flight statistics
│       │   │   │   │   ├── flight-summary.component.ts
│       │   │   │   │   └── utilization-report.component.ts
│       │   │   │   │
│       │   │   │   ├── training-reports/    # Training reports
│       │   │   │   │   ├── student-report.component.ts
│       │   │   │   │   └── instructor-report.component.ts
│       │   │   │   │
│       │   │   │   ├── safety-reports/      # Safety metrics
│       │   │   │   │   ├── safety-dashboard.component.ts
│       │   │   │   │   └── incident-tracker.component.ts
│       │   │   │   │
│       │   │   │   └── export/              # Export tools
│       │   │   │       ├── export-wizard.component.ts
│       │   │   │       └── report-scheduler.component.ts
│       │   │   │
│       │   │   ├── reports.routes.ts
│       │   │   └── remote-entry.ts
│       │   │
│       │   └── bootstrap.ts
│       │
│       └── webpack.config.js
│
│
├── libs/                                    # SHARED LIBRARIES
│   │
│   ├── shared/                              # Cross-cutting concerns
│   │   │
│   │   ├── ui/                              # @fts/shared/ui
│   │   │   ├── src/
│   │   │   │   ├── lib/
│   │   │   │   │   ├── button/
│   │   │   │   │   │   ├── button.component.ts
│   │   │   │   │   │   └── button.component.spec.ts
│   │   │   │   │   │
│   │   │   │   │   ├── card/
│   │   │   │   │   │   └── card.component.ts
│   │   │   │   │   │
│   │   │   │   │   ├── data-table/
│   │   │   │   │   │   ├── data-table.component.ts
│   │   │   │   │   │   ├── table-column.directive.ts
│   │   │   │   │   │   └── table-pagination.component.ts
│   │   │   │   │   │
│   │   │   │   │   ├── form-field/
│   │   │   │   │   │   ├── form-field.component.ts
│   │   │   │   │   │   ├── input.component.ts
│   │   │   │   │   │   ├── select.component.ts
│   │   │   │   │   │   └── datepicker.component.ts
│   │   │   │   │   │
│   │   │   │   │   ├── modal/
│   │   │   │   │   │   ├── modal.component.ts
│   │   │   │   │   │   ├── modal.service.ts
│   │   │   │   │   │   └── confirm-dialog.component.ts
│   │   │   │   │   │
│   │   │   │   │   ├── toast/
│   │   │   │   │   │   ├── toast.component.ts
│   │   │   │   │   │   └── toast.service.ts
│   │   │   │   │   │
│   │   │   │   │   ├── loading/
│   │   │   │   │   │   ├── loading-spinner.component.ts
│   │   │   │   │   │   └── loading-bar.component.ts
│   │   │   │   │   │
│   │   │   │   │   ├── empty-state/
│   │   │   │   │   │   └── empty-state.component.ts
│   │   │   │   │   │
│   │   │   │   │   ├── avatar/
│   │   │   │   │   │   └── avatar.component.ts
│   │   │   │   │   │
│   │   │   │   │   ├── badge/
│   │   │   │   │   │   └── badge.component.ts
│   │   │   │   │   │
│   │   │   │   │   ├── status-indicator/
│   │   │   │   │   │   └── status-indicator.component.ts
│   │   │   │   │   │
│   │   │   │   │   ├── pagination/
│   │   │   │   │   │   └── pagination.component.ts
│   │   │   │   │   │
│   │   │   │   │   └── index.ts
│   │   │   │   │
│   │   │   │   └── index.ts
│   │   │   │
│   │   │   └── project.json
│   │   │
│   │   │
│   │   ├── data-access/                     # @fts/shared/data-access
│   │   │   ├── src/
│   │   │   │   ├── lib/
│   │   │   │   │   ├── graphql/
│   │   │   │   │   │   ├── apollo-client.ts
│   │   │   │   │   │   ├── apollo.provider.ts
│   │   │   │   │   │   └── fragments/
│   │   │   │   │   │       ├── user.fragment.ts
│   │   │   │   │   │       ├── booking.fragment.ts
│   │   │   │   │   │       └── flight.fragment.ts
│   │   │   │   │   │
│   │   │   │   │   ├── interceptors/
│   │   │   │   │   │   ├── auth.interceptor.ts
│   │   │   │   │   │   ├── error.interceptor.ts
│   │   │   │   │   │   └── loading.interceptor.ts
│   │   │   │   │   │
│   │   │   │   │   ├── websocket/
│   │   │   │   │   │   ├── websocket.service.ts
│   │   │   │   │   │   └── websocket.types.ts
│   │   │   │   │   │
│   │   │   │   │   └── index.ts
│   │   │   │   │
│   │   │   │   └── index.ts
│   │   │   │
│   │   │   └── project.json
│   │   │
│   │   │
│   │   ├── auth/                            # @fts/shared/auth
│   │   │   ├── src/
│   │   │   │   ├── lib/
│   │   │   │   │   ├── guards/
│   │   │   │   │   │   ├── auth.guard.ts
│   │   │   │   │   │   └── role.guard.ts
│   │   │   │   │   │
│   │   │   │   │   ├── services/
│   │   │   │   │   │   ├── auth.service.ts
│   │   │   │   │   │   └── token.service.ts
│   │   │   │   │   │
│   │   │   │   │   ├── interceptors/
│   │   │   │   │   │   └── jwt.interceptor.ts
│   │   │   │   │   │
│   │   │   │   │   ├── store/
│   │   │   │   │   │   ├── auth.store.ts
│   │   │   │   │   │   └── auth.selectors.ts
│   │   │   │   │   │
│   │   │   │   │   ├── models/
│   │   │   │   │   │   ├── user.model.ts
│   │   │   │   │   │   └── auth.model.ts
│   │   │   │   │   │
│   │   │   │   │   └── index.ts
│   │   │   │   │
│   │   │   │   └── index.ts
│   │   │   │
│   │   │   └── project.json
│   │   │
│   │   │
│   │   ├── util/                            # @fts/shared/util
│   │   │   ├── src/
│   │   │   │   ├── lib/
│   │   │   │   │   ├── pipes/
│   │   │   │   │   │   ├── flight-time.pipe.ts
│   │   │   │   │   │   ├── currency.pipe.ts
│   │   │   │   │   │   ├── duration.pipe.ts
│   │   │   │   │   │   └── time-ago.pipe.ts
│   │   │   │   │   │
│   │   │   │   │   ├── validators/
│   │   │   │   │   │   ├── form-validators.ts
│   │   │   │   │   │   └── aviation-validators.ts
│   │   │   │   │   │
│   │   │   │   │   ├── date/
│   │   │   │   │   │   ├── date-utils.ts
│   │   │   │   │   │   └── timezone-utils.ts
│   │   │   │   │   │
│   │   │   │   │   ├── helpers/
│   │   │   │   │   │   ├── array-utils.ts
│   │   │   │   │   │   └── string-utils.ts
│   │   │   │   │   │
│   │   │   │   │   └── index.ts
│   │   │   │   │
│   │   │   │   └── index.ts
│   │   │   │
│   │   │   └── project.json
│   │   │
│   │   │
│   │   └── i18n/                            # @fts/shared/i18n
│   │       ├── src/
│   │       │   ├── lib/
│   │       │   │   ├── i18n.module.ts
│   │       │   │   ├── i18n.service.ts
│   │       │   │   └── translations/
│   │       │   │       ├── en.json
│   │       │   │       ├── no.json
│   │       │   │       └── tr.json
│   │       │   │
│   │       │   └── index.ts
│   │       │
│   │       └── project.json
│   │
│   │
│   ├── domain/                              # Domain-specific libraries
│   │   │
│   │   ├── booking/                         # @fts/domain/booking
│   │   │   ├── src/
│   │   │   │   ├── lib/
│   │   │   │   │   ├── models/
│   │   │   │   │   │   ├── booking.model.ts
│   │   │   │   │   │   ├── time-slot.model.ts
│   │   │   │   │   │   └── booking-status.enum.ts
│   │   │   │   │   │
│   │   │   │   │   ├── services/
│   │   │   │   │   │   └── booking.service.ts
│   │   │   │   │   │
│   │   │   │   │   ├── graphql/
│   │   │   │   │   │   ├── booking.queries.ts
│   │   │   │   │   │   └── booking.mutations.ts
│   │   │   │   │   │
│   │   │   │   │   ├── store/
│   │   │   │   │   │   └── booking.store.ts
│   │   │   │   │   │
│   │   │   │   │   └── index.ts
│   │   │   │   │
│   │   │   │   └── index.ts
│   │   │   │
│   │   │   └── project.json
│   │   │
│   │   │
│   │   ├── flight/                          # @fts/domain/flight
│   │   │   ├── src/
│   │   │   │   ├── lib/
│   │   │   │   │   ├── models/
│   │   │   │   │   │   ├── flight.model.ts
│   │   │   │   │   │   ├── flight-log.model.ts
│   │   │   │   │   │   ├── flight-summary.model.ts
│   │   │   │   │   │   └── currency.model.ts
│   │   │   │   │   │
│   │   │   │   │   ├── services/
│   │   │   │   │   │   ├── flight.service.ts
│   │   │   │   │   │   └── logbook.service.ts
│   │   │   │   │   │
│   │   │   │   │   ├── graphql/
│   │   │   │   │   │   ├── flight.queries.ts
│   │   │   │   │   │   └── flight.mutations.ts
│   │   │   │   │   │
│   │   │   │   │   └── index.ts
│   │   │   │   │
│   │   │   │   └── index.ts
│   │   │   │
│   │   │   └── project.json
│   │   │
│   │   │
│   │   ├── training/                        # @fts/domain/training
│   │   │   ├── src/
│   │   │   │   ├── lib/
│   │   │   │   │   ├── models/
│   │   │   │   │   │   ├── syllabus.model.ts
│   │   │   │   │   │   ├── lesson.model.ts
│   │   │   │   │   │   └── progress.model.ts
│   │   │   │   │   │
│   │   │   │   │   ├── services/
│   │   │   │   │   │   └── training.service.ts
│   │   │   │   │   │
│   │   │   │   │   └── index.ts
│   │   │   │   │
│   │   │   │   └── index.ts
│   │   │   │
│   │   │   └── project.json
│   │   │
│   │   │
│   │   ├── aircraft/                        # @fts/domain/aircraft
│   │   │   ├── src/
│   │   │   │   ├── lib/
│   │   │   │   │   ├── models/
│   │   │   │   │   │   ├── aircraft.model.ts
│   │   │   │   │   │   ├── squawk.model.ts
│   │   │   │   │   │   └── maintenance.model.ts
│   │   │   │   │   │
│   │   │   │   │   ├── services/
│   │   │   │   │   │   └── aircraft.service.ts
│   │   │   │   │   │
│   │   │   │   │   └── index.ts
│   │   │   │   │
│   │   │   │   └── index.ts
│   │   │   │
│   │   │   └── project.json
│   │   │
│   │   │
│   │   ├── user/                            # @fts/domain/user
│   │   │   ├── src/
│   │   │   │   ├── lib/
│   │   │   │   │   ├── models/
│   │   │   │   │   │   ├── pilot.model.ts
│   │   │   │   │   │   ├── instructor.model.ts
│   │   │   │   │   │   └── staff.model.ts
│   │   │   │   │   │
│   │   │   │   │   ├── services/
│   │   │   │   │   │   └── user.service.ts
│   │   │   │   │   │
│   │   │   │   │   └── index.ts
│   │   │   │   │
│   │   │   │   └── index.ts
│   │   │   │
│   │   │   └── project.json
│   │   │
│   │   │
│   │   └── organization/                    # @fts/domain/organization
│   │       ├── src/
│   │       │   ├── lib/
│   │       │   │   ├── models/
│   │       │   │   │   └── organization.model.ts
│   │       │   │   │
│   │       │   │   ├── services/
│   │       │   │   │   └── organization.service.ts
│   │       │   │   │
│   │       │   │   └── index.ts
│   │       │   │
│   │       │   └── index.ts
│   │       │
│   │       └── project.json
│   │
│   │
│   └── aviation/                            # Aviation-specific libraries
│       │
│       ├── weather/                         # @fts/aviation/weather
│       │   ├── src/
│       │   │   ├── lib/
│       │   │   │   ├── components/
│       │   │   │   │   ├── metar-display/
│       │   │   │   │   │   └── metar-display.component.ts
│       │   │   │   │   │
│       │   │   │   │   ├── taf-display/
│       │   │   │   │   │   └── taf-display.component.ts
│       │   │   │   │   │
│       │   │   │   │   └── weather-widget/
│       │   │   │   │       └── weather-widget.component.ts
│       │   │   │   │
│       │   │   │   ├── services/
│       │   │   │   │   └── weather.service.ts
│       │   │   │   │
│       │   │   │   ├── pipes/
│       │   │   │   │   └── metar-decode.pipe.ts
│       │   │   │   │
│       │   │   │   ├── models/
│       │   │   │   │   ├── metar.model.ts
│       │   │   │   │   └── taf.model.ts
│       │   │   │   │
│       │   │   │   └── index.ts
│       │   │   │
│       │   │   └── index.ts
│       │   │
│       │   └── project.json
│       │
│       │
│       ├── maps/                            # @fts/aviation/maps
│       │   ├── src/
│       │   │   ├── lib/
│       │   │   │   ├── components/
│       │   │   │   │   ├── airport-map/
│       │   │   │   │   │   └── airport-map.component.ts
│       │   │   │   │   │
│       │   │   │   │   └── flight-tracker/
│       │   │   │   │       └── flight-tracker.component.ts
│       │   │   │   │
│       │   │   │   ├── services/
│       │   │   │   │   └── maps.service.ts
│       │   │   │   │
│       │   │   │   └── index.ts
│       │   │   │
│       │   │   └── index.ts
│       │   │
│       │   └── project.json
│       │
│       │
│       └── documents/                       # @fts/aviation/documents
│           ├── src/
│           │   ├── lib/
│           │   │   ├── services/
│           │   │   │   ├── pdf-generator.service.ts
│           │   │   │   └── logbook-export.service.ts
│           │   │   │
│           │   │   ├── templates/
│           │   │   │   ├── certificate.template.ts
│           │   │   │   └── logbook.template.ts
│           │   │   │
│           │   │   └── index.ts
│           │   │
│           │   └── index.ts
│           │
│           └── project.json
│
│
├── tools/                                   # Build tools & generators
│   ├── generators/
│   │   └── component/
│   └── scripts/
│       ├── build-all.sh
│       └── deploy-mfe.sh
│
├── .eslintrc.json
├── .prettierrc
├── jest.config.ts
├── jest.preset.js
├── nx.json
├── package.json
├── tsconfig.base.json
└── tailwind.config.js
```

### 3.2 Library Dependency Rules

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    LIBRARY DEPENDENCY RULES                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Apps (shell, booking, flight, ...)                                        │
│    └─→ Domain libs (@fts/domain/*)                                         │
│          └─→ Shared libs (@fts/shared/*)                                   │
│                └─→ Shared libs only (no circular)                          │
│                                                                             │
│  Aviation libs (@fts/aviation/*)                                           │
│    └─→ Shared libs only                                                    │
│                                                                             │
│  RULES:                                                                    │
│  ✅ Apps → Domain, Shared, Aviation                                        │
│  ✅ Domain → Shared, Aviation                                              │
│  ✅ Shared → Shared only                                                   │
│  ✅ Aviation → Shared only                                                 │
│  ❌ NO circular dependencies                                               │
│  ❌ NO Domain → Domain (use shared services)                               │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.3 Nx Workspace Configuration

```json
// nx.json

{
  "$schema": "./node_modules/nx/schemas/nx-schema.json",
  "defaultBase": "main",
  
  "namedInputs": {
    "default": ["{projectRoot}/**/*", "sharedGlobals"],
    "production": [
      "default",
      "!{projectRoot}/**/?(*.)+(spec|test).[jt]s?(x)?(.snap)",
      "!{projectRoot}/tsconfig.spec.json"
    ],
    "sharedGlobals": [
      "{workspaceRoot}/tsconfig.base.json",
      "{workspaceRoot}/tailwind.config.js"
    ]
  },
  
  "targetDefaults": {
    "build": {
      "dependsOn": ["^build"],
      "inputs": ["production", "^production"],
      "cache": true
    },
    "test": {
      "inputs": ["default", "^production"],
      "cache": true
    },
    "lint": {
      "inputs": ["default"],
      "cache": true
    }
  },
  
  "generators": {
    "@nx/angular:component": {
      "style": "scss",
      "changeDetection": "OnPush",
      "standalone": true
    }
  }
}
```

### 3.4 Module Boundaries (ESLint)

```json
// .eslintrc.json - module boundary rules

{
  "rules": {
    "@nx/enforce-module-boundaries": [
      "error",
      {
        "depConstraints": [
          {
            "sourceTag": "type:app",
            "onlyDependOnLibsWithTags": ["type:feature", "type:domain", "type:shared", "type:aviation"]
          },
          {
            "sourceTag": "type:domain",
            "onlyDependOnLibsWithTags": ["type:shared", "type:aviation"]
          },
          {
            "sourceTag": "type:shared",
            "onlyDependOnLibsWithTags": ["type:shared"]
          },
          {
            "sourceTag": "type:aviation",
            "onlyDependOnLibsWithTags": ["type:shared"]
          },
          {
            "sourceTag": "scope:booking",
            "onlyDependOnLibsWithTags": ["scope:booking", "scope:shared"]
          },
          {
            "sourceTag": "scope:flight",
            "onlyDependOnLibsWithTags": ["scope:flight", "scope:shared"]
          }
        ]
      }
    ]
  }
}
```

---

## 4. SHELL APPLICATION

### 4.1 Module Federation Configuration

```javascript
// apps/shell/webpack.config.js

const { withModuleFederationPlugin, shareAll } = require('@angular-architects/module-federation/webpack');

module.exports = withModuleFederationPlugin({
  name: 'shell',
  
  remotes: {
    // MFE'ler dinamik olarak yüklenecek - Environment'dan URL alınır
  },
  
  shared: {
    ...shareAll({
      singleton: true,
      strictVersion: true,
      requiredVersion: 'auto',
    }),
  },
  
  sharedMappings: ['@fts/shared/ui', '@fts/shared/auth', '@fts/shared/util'],
});
```

### 4.2 Environment Configuration

```typescript
// apps/shell/src/environments/environment.ts (Development)

export const environment = {
  production: false,
  apiUrl: 'http://localhost:4000/graphql',
  wsUrl: 'ws://localhost:4000/graphql',
  
  mfeUrls: {
    booking: 'http://localhost:4201/remoteEntry.js',
    flight: 'http://localhost:4202/remoteEntry.js',
    training: 'http://localhost:4203/remoteEntry.js',
    admin: 'http://localhost:4204/remoteEntry.js',
    finance: 'http://localhost:4205/remoteEntry.js',
    reports: 'http://localhost:4206/remoteEntry.js',
  },
  
  features: {
    darkMode: true,
    realTimeUpdates: true,
    offlineMode: false,
  },
};
```

```typescript
// apps/shell/src/environments/environment.prod.ts (Production)

export const environment = {
  production: true,
  apiUrl: 'https://api.flighttraining.app/graphql',
  wsUrl: 'wss://api.flighttraining.app/graphql',
  
  mfeUrls: {
    booking: 'https://cdn.flighttraining.app/mfe/booking/remoteEntry.js',
    flight: 'https://cdn.flighttraining.app/mfe/flight/remoteEntry.js',
    training: 'https://cdn.flighttraining.app/mfe/training/remoteEntry.js',
    admin: 'https://cdn.flighttraining.app/mfe/admin/remoteEntry.js',
    finance: 'https://cdn.flighttraining.app/mfe/finance/remoteEntry.js',
    reports: 'https://cdn.flighttraining.app/mfe/reports/remoteEntry.js',
  },
  
  features: {
    darkMode: true,
    realTimeUpdates: true,
    offlineMode: true,
  },
};
```

### 4.3 App Configuration

```typescript
// apps/shell/src/app/app.config.ts

import { ApplicationConfig, ErrorHandler } from '@angular/core';
import { provideRouter, withPreloading, PreloadAllModules } from '@angular/router';
import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { provideAnimations } from '@angular/platform-browser/animations';
import { provideApollo } from 'apollo-angular';

import { APP_ROUTES } from './app.routes';
import { GlobalErrorHandler } from './core/services/error-handler.service';
import { authInterceptor } from '@fts/shared/auth';
import { loadingInterceptor, errorInterceptor } from '@fts/shared/data-access';
import { apolloClientFactory } from '@fts/shared/data-access';

export const appConfig: ApplicationConfig = {
  providers: [
    // Routing with preloading
    provideRouter(APP_ROUTES, withPreloading(PreloadAllModules)),
    
    // HTTP with interceptors
    provideHttpClient(
      withInterceptors([authInterceptor, loadingInterceptor, errorInterceptor])
    ),
    
    // Animations
    provideAnimations(),
    
    // GraphQL
    provideApollo(apolloClientFactory),
    
    // Global Error Handler
    { provide: ErrorHandler, useClass: GlobalErrorHandler },
  ],
};
```

### 4.4 App Routes with Error Boundaries

```typescript
// apps/shell/src/app/app.routes.ts

import { Routes } from '@angular/router';
import { loadRemoteModule } from '@angular-architects/module-federation';
import { AuthGuard, RoleGuard } from '@fts/shared/auth';
import { MainLayoutComponent } from './layout/main-layout/main-layout.component';
import { MfeErrorComponent } from './fallback/mfe-error.component';
import { environment } from '../environments/environment';

// MFE Configuration
interface MfeConfig {
  name: string;
  displayName: string;
  url: string;
  criticality: 'high' | 'medium' | 'low';
  requiredRoles?: string[];
}

const MFE_CONFIG: Record<string, MfeConfig> = {
  booking: {
    name: 'booking',
    displayName: 'Rezervasyon',
    url: environment.mfeUrls.booking,
    criticality: 'high',
  },
  flight: {
    name: 'flight',
    displayName: 'Uçuş Kayıtları',
    url: environment.mfeUrls.flight,
    criticality: 'high',
  },
  training: {
    name: 'training',
    displayName: 'Eğitim',
    url: environment.mfeUrls.training,
    criticality: 'medium',
  },
  admin: {
    name: 'admin',
    displayName: 'Yönetim',
    url: environment.mfeUrls.admin,
    criticality: 'low',
    requiredRoles: ['admin', 'super_admin'],
  },
  finance: {
    name: 'finance',
    displayName: 'Finans',
    url: environment.mfeUrls.finance,
    criticality: 'low',
    requiredRoles: ['admin', 'finance'],
  },
  reports: {
    name: 'reports',
    displayName: 'Raporlar',
    url: environment.mfeUrls.reports,
    criticality: 'low',
  },
};

/**
 * Load MFE with error boundary
 * MFE yüklenemezse fallback component gösterilir
 */
function loadMfe(config: MfeConfig) {
  return () =>
    loadRemoteModule({
      type: 'module',
      remoteEntry: config.url,
      exposedModule: './routes',
    })
      .then((m) => m[`${config.name.toUpperCase()}_ROUTES`])
      .catch((error) => {
        console.error(`❌ Failed to load MFE: ${config.name}`, error);
        
        // Return fallback route - diğer MFE'ler çalışmaya devam eder
        return [{
          path: '**',
          component: MfeErrorComponent,
          data: {
            mfeName: config.name,
            displayName: config.displayName,
            criticality: config.criticality,
            error: error.message,
          },
        }];
      });
}

export const APP_ROUTES: Routes = [
  // Auth routes (layout olmadan)
  {
    path: 'auth',
    loadChildren: () => import('./features/auth/auth.routes').then(m => m.AUTH_ROUTES),
  },
  
  // Main application (layout ile)
  {
    path: '',
    component: MainLayoutComponent,
    canActivate: [AuthGuard],
    children: [
      { path: '', redirectTo: 'dashboard', pathMatch: 'full' },
      
      // Dashboard (Shell feature)
      {
        path: 'dashboard',
        loadComponent: () => import('./features/dashboard/dashboard.component')
          .then(m => m.DashboardComponent),
        data: { title: 'Dashboard' },
      },
      
      // ═══════════════════════════════════════════════════════════════════
      // HIGH CRITICALITY MFEs - Preload edilir
      // ═══════════════════════════════════════════════════════════════════
      
      {
        path: 'booking',
        loadChildren: loadMfe(MFE_CONFIG.booking),
        data: { title: 'Rezervasyon', preload: true },
      },
      {
        path: 'flights',
        loadChildren: loadMfe(MFE_CONFIG.flight),
        data: { title: 'Uçuşlar', preload: true },
      },
      
      // ═══════════════════════════════════════════════════════════════════
      // MEDIUM CRITICALITY MFEs
      // ═══════════════════════════════════════════════════════════════════
      
      {
        path: 'training',
        loadChildren: loadMfe(MFE_CONFIG.training),
        data: { title: 'Eğitim' },
      },
      
      // ═══════════════════════════════════════════════════════════════════
      // LOW CRITICALITY MFEs (Role Protected)
      // ═══════════════════════════════════════════════════════════════════
      
      {
        path: 'admin',
        loadChildren: loadMfe(MFE_CONFIG.admin),
        canActivate: [RoleGuard],
        data: { title: 'Yönetim', roles: ['admin', 'super_admin'] },
      },
      {
        path: 'finance',
        loadChildren: loadMfe(MFE_CONFIG.finance),
        canActivate: [RoleGuard],
        data: { title: 'Finans', roles: ['admin', 'finance'] },
      },
      {
        path: 'reports',
        loadChildren: loadMfe(MFE_CONFIG.reports),
        data: { title: 'Raporlar' },
      },
      
      // Settings (Shell feature)
      {
        path: 'settings',
        loadChildren: () => import('./features/settings/settings.routes')
          .then(m => m.SETTINGS_ROUTES),
        data: { title: 'Ayarlar' },
      },
    ],
  },
  
  // 404
  { path: '**', redirectTo: 'dashboard' },
];
```

### 4.5 Main Layout Component

```typescript
// apps/shell/src/app/layout/main-layout/main-layout.component.ts

import { Component, inject, signal, computed, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule, Router, NavigationStart, NavigationEnd } from '@angular/router';
import { Subject, takeUntil } from 'rxjs';

import { HeaderComponent } from '../header/header.component';
import { SidebarComponent } from '../sidebar/sidebar.component';
import { NotificationPanelComponent } from '../notification-panel/notification-panel.component';
import { LoadingBarComponent } from '@fts/shared/ui';
import { AuthStore } from '@fts/shared/auth';
import { ThemeService } from '../../core/services/theme.service';

interface MenuItem {
  label: string;
  icon: string;
  route: string;
  badge?: number;
  children?: MenuItem[];
  roles?: string[];
}

@Component({
  selector: 'fts-main-layout',
  standalone: true,
  imports: [
    CommonModule,
    RouterModule,
    HeaderComponent,
    SidebarComponent,
    NotificationPanelComponent,
    LoadingBarComponent,
  ],
  template: `
    <div class="flex h-screen overflow-hidden" [class.dark]="isDarkMode()">
      
      <!-- Loading Bar -->
      <fts-loading-bar [loading]="isNavigating()" />
      
      <!-- Sidebar -->
      <fts-sidebar
        [collapsed]="sidebarCollapsed()"
        [menuItems]="menuItems()"
        [currentUser]="authStore.user()"
        [currentOrg]="authStore.organization()"
        (toggleCollapse)="toggleSidebar()"
      />
      
      <!-- Main Content Area -->
      <div class="flex-1 flex flex-col min-w-0 overflow-hidden">
        
        <!-- Header -->
        <fts-header
          [currentUser]="authStore.user()"
          [notifications]="notifications()"
          [showNotificationPanel]="showNotificationPanel()"
          (toggleNotifications)="toggleNotificationPanel()"
          (toggleSidebar)="toggleSidebar()"
          (logout)="onLogout()"
        />
        
        <!-- Page Content -->
        <main class="flex-1 overflow-auto bg-gray-50 dark:bg-gray-900 p-6">
          <router-outlet />
        </main>
        
        <!-- Footer -->
        <footer class="px-6 py-3 bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700">
          <div class="flex items-center justify-between text-sm text-gray-500">
            <span>© 2024 Flight Training System</span>
            <span>v1.0.0</span>
          </div>
        </footer>
        
      </div>
      
      <!-- Notification Panel -->
      @if (showNotificationPanel()) {
        <fts-notification-panel
          [notifications]="notifications()"
          (close)="showNotificationPanel.set(false)"
          (markAsRead)="markNotificationAsRead($event)"
        />
      }
      
    </div>
  `,
})
export class MainLayoutComponent implements OnInit, OnDestroy {
  protected authStore = inject(AuthStore);
  private router = inject(Router);
  private themeService = inject(ThemeService);
  private destroy$ = new Subject<void>();
  
  // State
  sidebarCollapsed = signal(false);
  showNotificationPanel = signal(false);
  isNavigating = signal(false);
  notifications = signal<any[]>([]);
  
  // Computed
  isDarkMode = computed(() => this.themeService.isDarkMode());
  
  // Menu items based on user roles
  menuItems = computed<MenuItem[]>(() => {
    const user = this.authStore.user();
    const roles = user?.roles || [];
    
    const items: MenuItem[] = [
      { label: 'Dashboard', icon: 'dashboard', route: '/dashboard' },
      {
        label: 'Rezervasyon',
        icon: 'calendar',
        route: '/booking',
        children: [
          { label: 'Takvim', icon: 'calendar-days', route: '/booking/calendar' },
          { label: 'Dispatch Board', icon: 'clipboard-list', route: '/booking/dispatch' },
          { label: 'Hızlı Rezervasyon', icon: 'plus', route: '/booking/quick' },
        ],
      },
      {
        label: 'Uçuşlar',
        icon: 'plane',
        route: '/flights',
        children: [
          { label: 'Aktif Uçuşlar', icon: 'plane-departure', route: '/flights/active' },
          { label: 'Uçuş Geçmişi', icon: 'history', route: '/flights/history' },
          { label: 'Logbook', icon: 'book', route: '/flights/logbook' },
        ],
      },
      {
        label: 'Eğitim',
        icon: 'graduation-cap',
        route: '/training',
        children: [
          { label: 'Müfredat', icon: 'list-check', route: '/training/syllabus' },
          { label: 'İlerleme', icon: 'chart-line', route: '/training/progress' },
          { label: 'Sınavlar', icon: 'file-text', route: '/training/exams' },
        ],
      },
      { label: 'Raporlar', icon: 'chart-bar', route: '/reports' },
    ];
    
    // Admin menu (role-based)
    if (roles.includes('admin') || roles.includes('super_admin')) {
      items.push({
        label: 'Yönetim',
        icon: 'cog',
        route: '/admin',
        roles: ['admin', 'super_admin'],
        children: [
          { label: 'Kullanıcılar', icon: 'users', route: '/admin/users' },
          { label: 'Uçaklar', icon: 'plane', route: '/admin/aircraft' },
          { label: 'Organizasyon', icon: 'building', route: '/admin/organization' },
        ],
      });
    }
    
    // Finance menu (role-based)
    if (roles.includes('admin') || roles.includes('finance')) {
      items.push({
        label: 'Finans',
        icon: 'wallet',
        route: '/finance',
        roles: ['admin', 'finance'],
        children: [
          { label: 'Faturalar', icon: 'file-invoice', route: '/finance/invoices' },
          { label: 'Ödemeler', icon: 'credit-card', route: '/finance/payments' },
        ],
      });
    }
    
    return items;
  });
  
  ngOnInit() {
    // Track navigation for loading state
    this.router.events.pipe(takeUntil(this.destroy$)).subscribe((event) => {
      if (event instanceof NavigationStart) {
        this.isNavigating.set(true);
      }
      if (event instanceof NavigationEnd) {
        this.isNavigating.set(false);
      }
    });
    
    this.loadNotifications();
  }
  
  ngOnDestroy() {
    this.destroy$.next();
    this.destroy$.complete();
  }
  
  toggleSidebar() {
    this.sidebarCollapsed.update(v => !v);
  }
  
  toggleNotificationPanel() {
    this.showNotificationPanel.update(v => !v);
  }
  
  onLogout() {
    this.authStore.logout();
    this.router.navigate(['/auth/login']);
  }
  
  markNotificationAsRead(id: string) {
    this.notifications.update(notifs =>
      notifs.map(n => n.id === id ? { ...n, read: true } : n)
    );
  }
  
  private loadNotifications() {
    // TODO: Load from API via WebSocket
    this.notifications.set([
      {
        id: '1',
        type: 'booking',
        title: 'Yeni Rezervasyon',
        message: 'John Doe yarın 09:00 için rezervasyon yaptı',
        time: new Date(),
        read: false,
      },
    ]);
  }
}
```

---

## 5. MICRO-FRONTEND MODÜLLERİ

### 5.1 Booking MFE - Routes

```typescript
// apps/booking/src/app/booking.routes.ts

import { Routes } from '@angular/router';

export const BOOKING_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () => import('./features/dispatch-board/dispatch-board.component')
      .then(m => m.DispatchBoardComponent),
    data: { title: 'Dispatch Board' },
  },
  {
    path: 'calendar',
    loadComponent: () => import('./features/calendar/booking-calendar.component')
      .then(m => m.BookingCalendarComponent),
    data: { title: 'Rezervasyon Takvimi', fullWidth: true },
  },
  {
    path: 'quick',
    loadComponent: () => import('./features/quick-book/quick-book.component')
      .then(m => m.QuickBookComponent),
    data: { title: 'Hızlı Rezervasyon' },
  },
  {
    path: 'resources',
    loadComponent: () => import('./features/resource-view/resource-view.component')
      .then(m => m.ResourceViewComponent),
    data: { title: 'Kaynak Görünümü' },
  },
  {
    path: ':id',
    loadComponent: () => import('./features/booking-detail/booking-detail.component')
      .then(m => m.BookingDetailComponent),
    data: { title: 'Rezervasyon Detayı' },
  },
];
```

### 5.2 Booking MFE - Dispatch Board Component

```typescript
// apps/booking/src/app/features/dispatch-board/dispatch-board.component.ts

import { Component, inject, signal, computed, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';

import { CardComponent, ButtonComponent, BadgeComponent, StatusIndicatorComponent, EmptyStateComponent } from '@fts/shared/ui';
import { FlightTimePipe } from '@fts/shared/util';
import { BookingService, Booking, BookingStatus } from '@fts/domain/booking';
import { WeatherWidgetComponent } from '@fts/aviation/weather';

@Component({
  selector: 'fts-dispatch-board',
  standalone: true,
  imports: [
    CommonModule,
    RouterModule,
    CardComponent,
    ButtonComponent,
    BadgeComponent,
    StatusIndicatorComponent,
    EmptyStateComponent,
    FlightTimePipe,
    WeatherWidgetComponent,
  ],
  template: `
    <div class="space-y-6">
      
      <!-- Header -->
      <div class="flex items-center justify-between">
        <div>
          <h1 class="text-2xl font-bold text-gray-900 dark:text-white">
            Dispatch Board
          </h1>
          <p class="text-gray-500 dark:text-gray-400">
            {{ today | date:'EEEE, d MMMM yyyy' }} • 
            <span class="text-primary-600">{{ bookings().length }} rezervasyon</span>
          </p>
        </div>
        
        <div class="flex items-center gap-3">
          <!-- Date Navigation -->
          <div class="flex items-center bg-white dark:bg-gray-800 rounded-lg shadow-sm">
            <button class="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-l-lg"
                    (click)="previousDay()">
              <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/>
              </svg>
            </button>
            <button class="px-4 py-2 font-medium hover:bg-gray-100 dark:hover:bg-gray-700"
                    (click)="goToToday()">
              Bugün
            </button>
            <button class="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-r-lg"
                    (click)="nextDay()">
              <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/>
              </svg>
            </button>
          </div>
          
          <!-- Quick Book Button -->
          <fts-button variant="primary" routerLink="/booking/quick">
            <svg class="w-5 h-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
            </svg>
            Yeni Rezervasyon
          </fts-button>
        </div>
      </div>
      
      <!-- Weather Widget -->
      <fts-weather-widget [icaoCode]="organizationIcao()" />
      
      <!-- Stats Cards -->
      <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
        <fts-card>
          <div class="flex items-center">
            <div class="p-3 bg-blue-100 dark:bg-blue-900 rounded-lg">
              <svg class="w-6 h-6 text-blue-600 dark:text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"/>
              </svg>
            </div>
            <div class="ml-4">
              <p class="text-sm text-gray-500 dark:text-gray-400">Toplam</p>
              <p class="text-2xl font-bold text-gray-900 dark:text-white">{{ bookings().length }}</p>
            </div>
          </div>
        </fts-card>
        
        <fts-card>
          <div class="flex items-center">
            <div class="p-3 bg-green-100 dark:bg-green-900 rounded-lg">
              <svg class="w-6 h-6 text-green-600 dark:text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
              </svg>
            </div>
            <div class="ml-4">
              <p class="text-sm text-gray-500 dark:text-gray-400">Tamamlanan</p>
              <p class="text-2xl font-bold text-green-600">{{ completedCount() }}</p>
            </div>
          </div>
        </fts-card>
        
        <fts-card>
          <div class="flex items-center">
            <div class="p-3 bg-yellow-100 dark:bg-yellow-900 rounded-lg">
              <svg class="w-6 h-6 text-yellow-600 dark:text-yellow-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/>
              </svg>
            </div>
            <div class="ml-4">
              <p class="text-sm text-gray-500 dark:text-gray-400">Devam Eden</p>
              <p class="text-2xl font-bold text-yellow-600">{{ activeCount() }}</p>
            </div>
          </div>
        </fts-card>
        
        <fts-card>
          <div class="flex items-center">
            <div class="p-3 bg-purple-100 dark:bg-purple-900 rounded-lg">
              <svg class="w-6 h-6 text-purple-600 dark:text-purple-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"/>
              </svg>
            </div>
            <div class="ml-4">
              <p class="text-sm text-gray-500 dark:text-gray-400">Bekleyen</p>
              <p class="text-2xl font-bold text-purple-600">{{ pendingCount() }}</p>
            </div>
          </div>
        </fts-card>
      </div>
      
      <!-- Dispatch Table -->
      <fts-card [noPadding]="true">
        <div class="p-4 border-b border-gray-200 dark:border-gray-700">
          <h2 class="text-lg font-semibold text-gray-900 dark:text-white">Günlük Program</h2>
        </div>
        
        @if (bookings().length === 0) {
          <fts-empty-state
            icon="calendar"
            title="Bugün rezervasyon yok"
            description="Yeni bir rezervasyon oluşturmak için butona tıklayın."
          >
            <fts-button variant="primary" routerLink="/booking/quick">Rezervasyon Oluştur</fts-button>
          </fts-empty-state>
        } @else {
          <div class="overflow-x-auto">
            <table class="w-full">
              <thead class="bg-gray-50 dark:bg-gray-800">
                <tr>
                  <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Saat</th>
                  <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Uçak</th>
                  <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Pilot</th>
                  <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Eğitmen</th>
                  <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Tür</th>
                  <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Durum</th>
                  <th class="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">İşlemler</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-gray-200 dark:divide-gray-700">
                @for (booking of bookings(); track booking.id) {
                  <tr class="hover:bg-gray-50 dark:hover:bg-gray-800 cursor-pointer"
                      [routerLink]="['/booking', booking.id]">
                    <td class="px-4 py-4 whitespace-nowrap">
                      <div class="text-sm font-medium text-gray-900 dark:text-white">
                        {{ booking.startTime | date:'HH:mm' }} - {{ booking.endTime | date:'HH:mm' }}
                      </div>
                      <div class="text-xs text-gray-500">{{ booking.duration | flightTime }}</div>
                    </td>
                    <td class="px-4 py-4 whitespace-nowrap">
                      <div class="flex items-center">
                        <div class="w-8 h-8 bg-primary-100 dark:bg-primary-900 rounded-full flex items-center justify-center">
                          <span class="text-xs font-bold text-primary-600 dark:text-primary-400">
                            {{ booking.aircraft.registration.slice(-3) }}
                          </span>
                        </div>
                        <div class="ml-3">
                          <div class="text-sm font-medium text-gray-900 dark:text-white">
                            {{ booking.aircraft.registration }}
                          </div>
                          <div class="text-xs text-gray-500">{{ booking.aircraft.type }}</div>
                        </div>
                      </div>
                    </td>
                    <td class="px-4 py-4 whitespace-nowrap">
                      <div class="text-sm text-gray-900 dark:text-white">
                        {{ booking.pilot.firstName }} {{ booking.pilot.lastName }}
                      </div>
                    </td>
                    <td class="px-4 py-4 whitespace-nowrap">
                      @if (booking.instructor) {
                        <div class="text-sm text-gray-900 dark:text-white">
                          {{ booking.instructor.firstName }} {{ booking.instructor.lastName }}
                        </div>
                      } @else {
                        <span class="text-sm text-gray-400">-</span>
                      }
                    </td>
                    <td class="px-4 py-4 whitespace-nowrap">
                      <fts-badge [variant]="getBookingTypeVariant(booking.type)">
                        {{ getBookingTypeLabel(booking.type) }}
                      </fts-badge>
                    </td>
                    <td class="px-4 py-4 whitespace-nowrap">
                      <fts-status-indicator [status]="booking.status" [label]="getStatusLabel(booking.status)" />
                    </td>
                    <td class="px-4 py-4 whitespace-nowrap text-right">
                      <div class="flex items-center justify-end gap-2">
                        @if (booking.status === 'confirmed') {
                          <fts-button variant="success" size="sm"
                                      (buttonClick)="startFlight(booking); $event.stopPropagation()">
                            Uçuşu Başlat
                          </fts-button>
                        }
                        @if (booking.status === 'in_progress') {
                          <fts-button variant="warning" size="sm"
                                      (buttonClick)="endFlight(booking); $event.stopPropagation()">
                            Uçuşu Bitir
                          </fts-button>
                        }
                      </div>
                    </td>
                  </tr>
                }
              </tbody>
            </table>
          </div>
        }
      </fts-card>
      
    </div>
  `,
})
export class DispatchBoardComponent implements OnInit {
  private bookingService = inject(BookingService);
  
  // State
  today = signal(new Date());
  bookings = signal<Booking[]>([]);
  organizationIcao = signal('ENGM'); // Default: Oslo Gardermoen
  
  // Computed
  completedCount = computed(() => this.bookings().filter(b => b.status === 'completed').length);
  activeCount = computed(() => this.bookings().filter(b => b.status === 'in_progress').length);
  pendingCount = computed(() => this.bookings().filter(b => b.status === 'confirmed').length);
  
  ngOnInit() {
    this.loadBookings();
  }
  
  previousDay() {
    const date = new Date(this.today());
    date.setDate(date.getDate() - 1);
    this.today.set(date);
    this.loadBookings();
  }
  
  nextDay() {
    const date = new Date(this.today());
    date.setDate(date.getDate() + 1);
    this.today.set(date);
    this.loadBookings();
  }
  
  goToToday() {
    this.today.set(new Date());
    this.loadBookings();
  }
  
  async loadBookings() {
    const bookings = await this.bookingService.getBookingsForDate(this.today());
    this.bookings.set(bookings);
  }
  
  getBookingTypeVariant(type: string): string {
    const variants: Record<string, string> = {
      training: 'blue',
      solo: 'green',
      checkride: 'purple',
      rental: 'yellow',
    };
    return variants[type] || 'gray';
  }
  
  getBookingTypeLabel(type: string): string {
    const labels: Record<string, string> = {
      training: 'Eğitim',
      solo: 'Solo',
      checkride: 'Checkride',
      rental: 'Kiralama',
    };
    return labels[type] || type;
  }
  
  getStatusLabel(status: BookingStatus): string {
    const labels: Record<BookingStatus, string> = {
      pending: 'Beklemede',
      confirmed: 'Onaylandı',
      in_progress: 'Devam Ediyor',
      completed: 'Tamamlandı',
      cancelled: 'İptal',
      no_show: 'Gelmedi',
    };
    return labels[status];
  }
  
  startFlight(booking: Booking) {
    // Navigate to flight start page
    console.log('Start flight:', booking.id);
  }
  
  endFlight(booking: Booking) {
    // Navigate to flight end page
    console.log('End flight:', booking.id);
  }
}
```

### 5.3 Flight MFE - Pilot Logbook

```typescript
// apps/flight/src/app/features/logbook/pilot-logbook.component.ts

import { Component, inject, signal, computed, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { CardComponent, ButtonComponent, PaginationComponent } from '@fts/shared/ui';
import { FlightTimePipe } from '@fts/shared/util';
import { FlightService, Flight, FlightSummary } from '@fts/domain/flight';

@Component({
  selector: 'fts-pilot-logbook',
  standalone: true,
  imports: [CommonModule, CardComponent, ButtonComponent, PaginationComponent, FlightTimePipe],
  template: `
    <div class="space-y-6">
      
      <!-- Header -->
      <div class="flex items-center justify-between">
        <div>
          <h1 class="text-2xl font-bold text-gray-900 dark:text-white">Pilot Logbook</h1>
          <p class="text-gray-500 dark:text-gray-400">
            Toplam: {{ summary()?.totalFlightTime | flightTime }} uçuş saati
          </p>
        </div>
        
        <div class="flex items-center gap-3">
          <fts-button variant="secondary" (buttonClick)="exportPdf()">PDF İndir</fts-button>
          <fts-button variant="primary" routerLink="/flights/new">Yeni Kayıt</fts-button>
        </div>
      </div>
      
      <!-- Summary Cards -->
      <div class="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
        <fts-card>
          <div class="text-center">
            <p class="text-sm text-gray-500 dark:text-gray-400">Toplam Süre</p>
            <p class="text-2xl font-bold text-gray-900 dark:text-white">{{ summary()?.totalFlightTime | flightTime }}</p>
          </div>
        </fts-card>
        <fts-card>
          <div class="text-center">
            <p class="text-sm text-gray-500 dark:text-gray-400">PIC</p>
            <p class="text-2xl font-bold text-primary-600">{{ summary()?.picTime | flightTime }}</p>
          </div>
        </fts-card>
        <fts-card>
          <div class="text-center">
            <p class="text-sm text-gray-500 dark:text-gray-400">Dual</p>
            <p class="text-2xl font-bold text-blue-600">{{ summary()?.dualTime | flightTime }}</p>
          </div>
        </fts-card>
        <fts-card>
          <div class="text-center">
            <p class="text-sm text-gray-500 dark:text-gray-400">Solo</p>
            <p class="text-2xl font-bold text-green-600">{{ summary()?.soloTime | flightTime }}</p>
          </div>
        </fts-card>
        <fts-card>
          <div class="text-center">
            <p class="text-sm text-gray-500 dark:text-gray-400">Gece</p>
            <p class="text-2xl font-bold text-purple-600">{{ summary()?.nightTime | flightTime }}</p>
          </div>
        </fts-card>
        <fts-card>
          <div class="text-center">
            <p class="text-sm text-gray-500 dark:text-gray-400">IFR</p>
            <p class="text-2xl font-bold text-yellow-600">{{ summary()?.ifrTime | flightTime }}</p>
          </div>
        </fts-card>
      </div>
      
      <!-- Logbook Table -->
      <fts-card [noPadding]="true">
        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead class="bg-gray-50 dark:bg-gray-800 text-xs uppercase">
              <tr>
                <th class="px-3 py-3 text-left">Tarih</th>
                <th class="px-3 py-3 text-left">Uçak</th>
                <th class="px-3 py-3 text-left">Kalkış</th>
                <th class="px-3 py-3 text-left">Varış</th>
                <th class="px-3 py-3 text-center">İniş</th>
                <th class="px-3 py-3 text-right">Toplam</th>
                <th class="px-3 py-3 text-right">PIC</th>
                <th class="px-3 py-3 text-right">Dual</th>
                <th class="px-3 py-3 text-right">Gece</th>
                <th class="px-3 py-3 text-right">IFR</th>
                <th class="px-3 py-3 text-left">Notlar</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-200 dark:divide-gray-700">
              @for (flight of flights(); track flight.id) {
                <tr class="hover:bg-gray-50 dark:hover:bg-gray-800">
                  <td class="px-3 py-3 whitespace-nowrap font-medium">{{ flight.date | date:'dd.MM.yyyy' }}</td>
                  <td class="px-3 py-3 whitespace-nowrap">
                    <span class="font-mono">{{ flight.aircraft.registration }}</span>
                    <span class="text-gray-500 text-xs ml-1">{{ flight.aircraft.type }}</span>
                  </td>
                  <td class="px-3 py-3 whitespace-nowrap font-mono uppercase">{{ flight.departureAirport }}</td>
                  <td class="px-3 py-3 whitespace-nowrap font-mono uppercase">{{ flight.arrivalAirport }}</td>
                  <td class="px-3 py-3 text-center">{{ flight.landings }}</td>
                  <td class="px-3 py-3 text-right font-mono">{{ flight.totalTime | flightTime }}</td>
                  <td class="px-3 py-3 text-right font-mono">{{ flight.picTime | flightTime }}</td>
                  <td class="px-3 py-3 text-right font-mono">{{ flight.dualTime | flightTime }}</td>
                  <td class="px-3 py-3 text-right font-mono">{{ flight.nightTime | flightTime }}</td>
                  <td class="px-3 py-3 text-right font-mono">{{ flight.ifrTime | flightTime }}</td>
                  <td class="px-3 py-3 max-w-xs truncate" [title]="flight.remarks">{{ flight.remarks || '-' }}</td>
                </tr>
              }
            </tbody>
            <tfoot class="bg-gray-100 dark:bg-gray-800 font-bold">
              <tr>
                <td colspan="5" class="px-3 py-3 text-right">TOPLAM:</td>
                <td class="px-3 py-3 text-right font-mono">{{ summary()?.totalFlightTime | flightTime }}</td>
                <td class="px-3 py-3 text-right font-mono">{{ summary()?.picTime | flightTime }}</td>
                <td class="px-3 py-3 text-right font-mono">{{ summary()?.dualTime | flightTime }}</td>
                <td class="px-3 py-3 text-right font-mono">{{ summary()?.nightTime | flightTime }}</td>
                <td class="px-3 py-3 text-right font-mono">{{ summary()?.ifrTime | flightTime }}</td>
                <td></td>
              </tr>
            </tfoot>
          </table>
        </div>
        
        <div class="p-4 border-t border-gray-200 dark:border-gray-700">
          <fts-pagination [currentPage]="currentPage()" [totalPages]="totalPages()" (pageChange)="onPageChange($event)" />
        </div>
      </fts-card>
      
    </div>
  `,
})
export class PilotLogbookComponent implements OnInit {
  private flightService = inject(FlightService);
  
  flights = signal<Flight[]>([]);
  summary = signal<FlightSummary | null>(null);
  currentPage = signal(1);
  pageSize = signal(20);
  totalFlights = signal(0);
  
  totalPages = computed(() => Math.ceil(this.totalFlights() / this.pageSize()));
  
  ngOnInit() {
    this.loadFlights();
    this.loadSummary();
  }
  
  async loadFlights() {
    const result = await this.flightService.getLogbook({ page: this.currentPage(), pageSize: this.pageSize() });
    this.flights.set(result.items);
    this.totalFlights.set(result.total);
  }
  
  async loadSummary() {
    const summary = await this.flightService.getFlightSummary();
    this.summary.set(summary);
  }
  
  onPageChange(page: number) {
    this.currentPage.set(page);
    this.loadFlights();
  }
  
  exportPdf() {
    console.log('Export PDF');
  }
}
```

---

## 6. SHARED LIBRARIES

### 6.1 Button Component (@fts/shared/ui)

```typescript
// libs/shared/ui/src/lib/button/button.component.ts

import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';

type ButtonVariant = 'primary' | 'secondary' | 'success' | 'warning' | 'danger' | 'ghost';
type ButtonSize = 'sm' | 'md' | 'lg';

@Component({
  selector: 'fts-button',
  standalone: true,
  imports: [CommonModule],
  template: `
    <button [type]="type" [disabled]="disabled || loading" [class]="classes" (click)="onClick($event)">
      @if (loading) {
        <svg class="animate-spin -ml-1 mr-2 h-4 w-4" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
        </svg>
      }
      <ng-content />
    </button>
  `,
})
export class ButtonComponent {
  @Input() variant: ButtonVariant = 'primary';
  @Input() size: ButtonSize = 'md';
  @Input() type: 'button' | 'submit' = 'button';
  @Input() disabled = false;
  @Input() loading = false;
  @Input() fullWidth = false;
  @Output() buttonClick = new EventEmitter<MouseEvent>();
  
  get classes(): string {
    const base = 'inline-flex items-center justify-center font-medium rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed';
    
    const variants: Record<ButtonVariant, string> = {
      primary: 'bg-primary-600 text-white hover:bg-primary-700 focus:ring-primary-500',
      secondary: 'bg-gray-200 text-gray-900 hover:bg-gray-300 focus:ring-gray-500 dark:bg-gray-700 dark:text-white',
      success: 'bg-green-600 text-white hover:bg-green-700 focus:ring-green-500',
      warning: 'bg-yellow-500 text-white hover:bg-yellow-600 focus:ring-yellow-500',
      danger: 'bg-red-600 text-white hover:bg-red-700 focus:ring-red-500',
      ghost: 'bg-transparent text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800',
    };
    
    const sizes: Record<ButtonSize, string> = {
      sm: 'px-3 py-1.5 text-sm',
      md: 'px-4 py-2 text-sm',
      lg: 'px-6 py-3 text-base',
    };
    
    return `${base} ${variants[this.variant]} ${sizes[this.size]} ${this.fullWidth ? 'w-full' : ''}`;
  }
  
  onClick(event: MouseEvent) {
    if (!this.disabled && !this.loading) {
      this.buttonClick.emit(event);
    }
  }
}
```

### 6.2 Flight Time Pipe (@fts/shared/util)

```typescript
// libs/shared/util/src/lib/pipes/flight-time.pipe.ts

import { Pipe, PipeTransform } from '@angular/core';

/**
 * Converts decimal hours to HH:MM format
 * 
 * Usage:
 *   {{ 1.5 | flightTime }}  → "1:30"
 *   {{ 2.75 | flightTime }} → "2:45"
 *   {{ 0.1 | flightTime }}  → "0:06"
 */
@Pipe({
  name: 'flightTime',
  standalone: true,
})
export class FlightTimePipe implements PipeTransform {
  transform(decimalHours: number | null | undefined): string {
    if (decimalHours === null || decimalHours === undefined) {
      return '-';
    }
    
    if (decimalHours === 0) {
      return '0:00';
    }
    
    const hours = Math.floor(decimalHours);
    const minutes = Math.round((decimalHours - hours) * 60);
    
    return `${hours}:${minutes.toString().padStart(2, '0')}`;
  }
}
```

### 6.3 Aviation Validators (@fts/shared/util)

```typescript
// libs/shared/util/src/lib/validators/aviation-validators.ts

import { AbstractControl, ValidationErrors, ValidatorFn } from '@angular/forms';

export class AviationValidators {
  
  /** Aircraft registration: N12345, LN-ABC, G-ABCD */
  static registration(): ValidatorFn {
    return (control: AbstractControl): ValidationErrors | null => {
      if (!control.value) return null;
      const pattern = /^[A-Z]{1,2}-?[A-Z0-9]{2,5}$/i;
      return pattern.test(control.value) ? null : { registration: { value: control.value } };
    };
  }
  
  /** ICAO airport code (4 letters) */
  static icaoCode(): ValidatorFn {
    return (control: AbstractControl): ValidationErrors | null => {
      if (!control.value) return null;
      const pattern = /^[A-Z]{4}$/i;
      return pattern.test(control.value) ? null : { icaoCode: { value: control.value } };
    };
  }
  
  /** Flight time (0.1 - 24.0, 6-minute increments) */
  static flightTime(): ValidatorFn {
    return (control: AbstractControl): ValidationErrors | null => {
      if (!control.value) return null;
      const value = parseFloat(control.value);
      if (isNaN(value) || value < 0 || value > 24) {
        return { flightTime: { value: control.value } };
      }
      return null;
    };
  }
  
  /** Pilot license number */
  static licenseNumber(): ValidatorFn {
    return (control: AbstractControl): ValidationErrors | null => {
      if (!control.value) return null;
      const pattern = /^[A-Z0-9]{5,15}$/i;
      return pattern.test(control.value) ? null : { licenseNumber: { value: control.value } };
    };
  }
}
```

---

## 11. ERROR HANDLING & FAULT TOLERANCE

### 11.1 MFE Error Component

```typescript
// apps/shell/src/app/fallback/mfe-error.component.ts

import { Component, inject, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { ButtonComponent, CardComponent } from '@fts/shared/ui';

@Component({
  selector: 'fts-mfe-error',
  standalone: true,
  imports: [CommonModule, RouterModule, ButtonComponent, CardComponent],
  template: `
    <div class="flex items-center justify-center min-h-[60vh] p-6">
      <fts-card class="max-w-lg w-full">
        <div class="text-center p-8">
          
          <!-- Icon -->
          <div class="w-20 h-20 mx-auto mb-6 rounded-full flex items-center justify-center"
               [class]="criticality() === 'high' ? 'bg-red-100' : criticality() === 'medium' ? 'bg-yellow-100' : 'bg-blue-100'">
            <svg class="w-10 h-10" 
                 [class]="criticality() === 'high' ? 'text-red-600' : criticality() === 'medium' ? 'text-yellow-600' : 'text-blue-600'" 
                 fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          </div>
          
          <h2 class="text-2xl font-bold text-gray-900 dark:text-white mb-2">
            {{ displayName() }} Modülü Kullanılamıyor
          </h2>
          
          <p class="text-gray-600 dark:text-gray-400 mb-6">
            @if (criticality() === 'high') {
              Bu modül şu an kullanılamıyor. Kritik bir işlem yapmanız gerekiyorsa destek ekibiyle iletişime geçin.
            } @else {
              Modül geçici olarak kullanılamıyor. Birkaç dakika içinde tekrar deneyin.
            }
          </p>
          
          @if (criticality() === 'high') {
            <div class="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 mb-6">
              <p class="text-sm text-red-800 dark:text-red-300">
                <strong>Acil Destek:</strong> +47 XXX XX XXX
              </p>
            </div>
          }
          
          <div class="flex flex-col sm:flex-row gap-3 justify-center">
            <fts-button variant="primary" (buttonClick)="retry()">Tekrar Dene</fts-button>
            <fts-button variant="secondary" routerLink="/dashboard">Dashboard'a Dön</fts-button>
          </div>
          
        </div>
      </fts-card>
    </div>
    
    <!-- Other modules working notice -->
    <div class="fixed bottom-4 right-4 bg-green-100 dark:bg-green-900/50 border border-green-300 dark:border-green-700 rounded-lg p-3 shadow-lg max-w-xs">
      <p class="text-sm text-green-800 dark:text-green-300">
        ✅ Diğer modüller normal çalışmaya devam ediyor
      </p>
    </div>
  `,
})
export class MfeErrorComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  
  displayName = signal('Bilinmeyen Modül');
  criticality = signal<'high' | 'medium' | 'low'>('low');
  
  ngOnInit() {
    const data = this.route.snapshot.data;
    this.displayName.set(data['displayName'] || 'Bilinmeyen Modül');
    this.criticality.set(data['criticality'] || 'low');
  }
  
  retry() {
    const url = this.router.url;
    this.router.navigateByUrl('/', { skipLocationChange: true }).then(() => this.router.navigateByUrl(url));
  }
}
```

### 11.2 Global Error Handler

```typescript
// apps/shell/src/app/core/services/error-handler.service.ts

import { ErrorHandler, Injectable, inject, NgZone } from '@angular/core';
import { Router } from '@angular/router';

@Injectable()
export class GlobalErrorHandler implements ErrorHandler {
  private router = inject(Router);
  private ngZone = inject(NgZone);
  
  handleError(error: any): void {
    console.error('🔴 Global Error:', error);
    
    // ChunkLoadError = MFE yüklenemedi
    if (this.isChunkLoadError(error)) {
      this.handleChunkLoadError(error);
      return;
    }
    
    // Network error
    if (this.isNetworkError(error)) {
      this.handleNetworkError(error);
      return;
    }
    
    // Log other errors
    this.logError(error);
  }
  
  private isChunkLoadError(error: any): boolean {
    return error?.name === 'ChunkLoadError' ||
           error?.message?.includes('Loading chunk') ||
           error?.message?.includes('remoteEntry');
  }
  
  private isNetworkError(error: any): boolean {
    return error?.name === 'HttpErrorResponse' || error?.status === 0;
  }
  
  private handleChunkLoadError(error: any) {
    this.ngZone.run(() => {
      console.warn('MFE yüklenemedi');
    });
  }
  
  private handleNetworkError(error: any) {
    this.ngZone.run(() => {
      console.warn('Ağ hatası:', error.message);
    });
  }
  
  private logError(error: any) {
    // Production: Send to Sentry/LogRocket
  }
}
```

---

## 15. CI/CD & DEPLOYMENT

### 15.1 GitHub Actions

```yaml
# .github/workflows/frontend-ci.yml

name: Frontend CI/CD

on:
  push:
    branches: [main]
    paths: ['apps/**', 'libs/**']

jobs:
  changes:
    runs-on: ubuntu-latest
    outputs:
      shell: ${{ steps.filter.outputs.shell }}
      booking: ${{ steps.filter.outputs.booking }}
      flight: ${{ steps.filter.outputs.flight }}
      training: ${{ steps.filter.outputs.training }}
    steps:
      - uses: actions/checkout@v4
      - uses: dorny/paths-filter@v2
        id: filter
        with:
          filters: |
            shell: ['apps/shell/**', 'libs/shared/**']
            booking: ['apps/booking/**', 'libs/domain/booking/**', 'libs/shared/**']
            flight: ['apps/flight/**', 'libs/domain/flight/**', 'libs/shared/**']
            training: ['apps/training/**', 'libs/domain/training/**', 'libs/shared/**']

  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: '20', cache: 'npm' }
      - run: npm ci
      - run: npx nx affected:lint --base=origin/main
      - run: npx nx affected:test --base=origin/main --ci

  deploy-shell:
    needs: [changes, test]
    if: needs.changes.outputs.shell == 'true'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: '20', cache: 'npm' }
      - run: npm ci
      - run: npx nx build shell --prod
      - run: |
          aws s3 sync dist/apps/shell s3://${{ secrets.CDN_BUCKET }}/shell/ --delete
          aws cloudfront create-invalidation --distribution-id ${{ secrets.CF_DIST }} --paths "/shell/*"

  deploy-booking:
    needs: [changes, test]
    if: needs.changes.outputs.booking == 'true'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: '20', cache: 'npm' }
      - run: npm ci
      - run: npx nx build booking --prod
      - run: |
          aws s3 sync dist/apps/booking s3://${{ secrets.CDN_BUCKET }}/mfe/booking/ --delete
          aws cloudfront create-invalidation --distribution-id ${{ secrets.CF_DIST }} --paths "/mfe/booking/*"

  # Similar jobs for flight, training, admin, finance, reports...
```

---

## SUMMARY

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    ANGULAR MICRO-FRONTEND SUMMARY                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  MİMARİ: Micro-Frontend + Nx Monorepo                                      │
│  GEREKÇE: Deployment Isolation                                             │
│  "Bir MFE bozuk deploy edilirse, diğerleri çalışmaya devam eder"           │
│                                                                             │
│  ═══════════════════════════════════════════════════════════════════════   │
│                                                                             │
│  YAPISI:                                                                   │
│  • 1 Shell Application (Host)                                              │
│  • 6 Micro-Frontends (Remote)                                              │
│    - Booking (🔴 HIGH)                                                     │
│    - Flight (🔴 HIGH)                                                      │
│    - Training (🟠 MEDIUM)                                                  │
│    - Admin (🟡 LOW)                                                        │
│    - Finance (🟡 LOW)                                                      │
│    - Reports (🟢 LOWEST)                                                   │
│  • Shared Libraries (@fts/shared/*, @fts/domain/*, @fts/aviation/*)       │
│                                                                             │
│  ═══════════════════════════════════════════════════════════════════════   │
│                                                                             │
│  TEKNOLOJİ:                                                                │
│  • Angular 18+ (Standalone Components)                                     │
│  • Module Federation (Webpack 5)                                           │
│  • Nx Monorepo                                                             │
│  • Signals + NgRx                                                          │
│  • Tailwind CSS                                                            │
│  • Apollo Client (GraphQL)                                                 │
│                                                                             │
│  ═══════════════════════════════════════════════════════════════════════   │
│                                                                             │
│  FAULT TOLERANCE:                                                          │
│  • Error Boundaries - MFE yüklenemezse fallback göster                    │
│  • Independent Deployment - Her MFE bağımsız deploy                       │
│  • Graceful Degradation - Diğer modüller çalışmaya devam eder             │
│                                                                             │
│  ═══════════════════════════════════════════════════════════════════════   │
│                                                                             │
│  DEVELOPMENT COMMANDS:                                                     │
│  ─────────────────────────────────────────────────────────────────────────  │
│  npx nx serve shell                    # Shell başlat                      │
│  npx nx run-many --target=serve --all  # Tümünü başlat                    │
│  npx nx affected:test                  # Değişen kodları test et          │
│  npx nx build booking --prod           # Booking MFE build                │
│  npx nx graph                          # Dependency graph                  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

Bu doküman Flight Training System Angular Micro-Frontend mimarisinin tüm detaylarını içermektedir.