import { Component, inject, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { AuthStore } from '../../core/services/auth.store';

interface DashboardStats {
  todayBookings: number;
  activeFlights: number;
  upcomingExams: number;
  pendingApprovals: number;
}

interface QuickAction {
  label: string;
  icon: string;
  route: string;
  color: string;
}

@Component({
  selector: 'fts-dashboard',
  standalone: true,
  imports: [CommonModule, RouterModule],
  template: `
    <div class="space-y-6">
      <!-- Welcome Header -->
      <div
        class="bg-white dark:bg-gray-800 rounded-xl shadow-sm p-6 border border-gray-200 dark:border-gray-700"
      >
        <div class="flex items-center justify-between">
          <div>
            <h1 class="text-2xl font-bold text-gray-900 dark:text-white">
              Welcome back, {{ authStore.user()?.firstName }}!
            </h1>
            <p class="text-gray-500 dark:text-gray-400 mt-1">
              {{ currentDate | date : 'EEEE, MMMM d, yyyy' }} |
              {{ authStore.user()?.organizationName }}
            </p>
          </div>
          <div class="hidden lg:flex items-center gap-4">
            <button
              routerLink="/booking/quick"
              class="px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg font-medium transition-colors"
            >
              Quick Book
            </button>
          </div>
        </div>
      </div>

      <!-- Stats Cards -->
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <!-- Today's Bookings -->
        <div
          class="bg-white dark:bg-gray-800 rounded-xl shadow-sm p-5 border border-gray-200 dark:border-gray-700"
        >
          <div class="flex items-center">
            <div class="p-3 bg-blue-100 dark:bg-blue-900 rounded-lg">
              <svg
                class="w-6 h-6 text-blue-600 dark:text-blue-400"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"
                />
              </svg>
            </div>
            <div class="ml-4">
              <p class="text-sm text-gray-500 dark:text-gray-400">
                Today's Bookings
              </p>
              <p class="text-2xl font-bold text-gray-900 dark:text-white">
                {{ stats().todayBookings }}
              </p>
            </div>
          </div>
        </div>

        <!-- Active Flights -->
        <div
          class="bg-white dark:bg-gray-800 rounded-xl shadow-sm p-5 border border-gray-200 dark:border-gray-700"
        >
          <div class="flex items-center">
            <div class="p-3 bg-green-100 dark:bg-green-900 rounded-lg">
              <svg
                class="w-6 h-6 text-green-600 dark:text-green-400"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"
                />
              </svg>
            </div>
            <div class="ml-4">
              <p class="text-sm text-gray-500 dark:text-gray-400">
                Active Flights
              </p>
              <p class="text-2xl font-bold text-gray-900 dark:text-white">
                {{ stats().activeFlights }}
              </p>
            </div>
          </div>
        </div>

        <!-- Upcoming Exams -->
        <div
          class="bg-white dark:bg-gray-800 rounded-xl shadow-sm p-5 border border-gray-200 dark:border-gray-700"
        >
          <div class="flex items-center">
            <div class="p-3 bg-yellow-100 dark:bg-yellow-900 rounded-lg">
              <svg
                class="w-6 h-6 text-yellow-600 dark:text-yellow-400"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                />
              </svg>
            </div>
            <div class="ml-4">
              <p class="text-sm text-gray-500 dark:text-gray-400">
                Upcoming Exams
              </p>
              <p class="text-2xl font-bold text-gray-900 dark:text-white">
                {{ stats().upcomingExams }}
              </p>
            </div>
          </div>
        </div>

        <!-- Pending Approvals -->
        <div
          class="bg-white dark:bg-gray-800 rounded-xl shadow-sm p-5 border border-gray-200 dark:border-gray-700"
        >
          <div class="flex items-center">
            <div class="p-3 bg-purple-100 dark:bg-purple-900 rounded-lg">
              <svg
                class="w-6 h-6 text-purple-600 dark:text-purple-400"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4"
                />
              </svg>
            </div>
            <div class="ml-4">
              <p class="text-sm text-gray-500 dark:text-gray-400">
                Pending Approvals
              </p>
              <p class="text-2xl font-bold text-gray-900 dark:text-white">
                {{ stats().pendingApprovals }}
              </p>
            </div>
          </div>
        </div>
      </div>

      <!-- Quick Actions -->
      <div class="grid grid-cols-2 lg:grid-cols-4 gap-4">
        @for (action of quickActions; track action.route) {
          <a
            [routerLink]="action.route"
            class="flex flex-col items-center p-6 bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 hover:shadow-md transition-shadow"
          >
            <div
              [class]="
                'p-4 rounded-full mb-3 ' +
                'bg-' +
                action.color +
                '-100 dark:bg-' +
                action.color +
                '-900'
              "
            >
              <svg
                class="w-8 h-8"
                [class]="
                  'text-' + action.color + '-600 dark:text-' + action.color + '-400'
                "
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                @switch (action.icon) {
                  @case ('calendar-plus') {
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"
                    />
                  }
                  @case ('plane-departure') {
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"
                    />
                  }
                  @case ('clipboard') {
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
                    />
                  }
                  @case ('book-open') {
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"
                    />
                  }
                }
              </svg>
            </div>
            <span class="font-medium text-gray-900 dark:text-white">
              {{ action.label }}
            </span>
          </a>
        }
      </div>

      <!-- Recent Activity & Upcoming -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <!-- Today's Schedule -->
        <div
          class="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700"
        >
          <div
            class="p-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between"
          >
            <h2 class="text-lg font-semibold text-gray-900 dark:text-white">
              Today's Schedule
            </h2>
            <a
              routerLink="/dispatch"
              class="text-sm text-primary-600 hover:text-primary-700"
            >
              View all
            </a>
          </div>
          <div class="p-4">
            <div
              class="flex flex-col items-center justify-center py-8 text-gray-500 dark:text-gray-400"
            >
              <svg
                class="w-12 h-12 mb-2"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"
                />
              </svg>
              <p>No bookings for today</p>
              <a
                routerLink="/booking/quick"
                class="mt-2 text-primary-600 hover:text-primary-700 font-medium"
              >
                Create a booking
              </a>
            </div>
          </div>
        </div>

        <!-- Recent Flights -->
        <div
          class="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700"
        >
          <div
            class="p-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between"
          >
            <h2 class="text-lg font-semibold text-gray-900 dark:text-white">
              Recent Flights
            </h2>
            <a
              routerLink="/flights/history"
              class="text-sm text-primary-600 hover:text-primary-700"
            >
              View all
            </a>
          </div>
          <div class="p-4">
            <div
              class="flex flex-col items-center justify-center py-8 text-gray-500 dark:text-gray-400"
            >
              <svg
                class="w-12 h-12 mb-2"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"
                />
              </svg>
              <p>No recent flights</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  `,
})
export class DashboardComponent implements OnInit {
  protected authStore = inject(AuthStore);

  currentDate = new Date();
  stats = signal<DashboardStats>({
    todayBookings: 0,
    activeFlights: 0,
    upcomingExams: 0,
    pendingApprovals: 0,
  });

  quickActions: QuickAction[] = [
    {
      label: 'New Booking',
      icon: 'calendar-plus',
      route: '/booking/quick',
      color: 'blue',
    },
    {
      label: 'Start Flight',
      icon: 'plane-departure',
      route: '/flights/active',
      color: 'green',
    },
    {
      label: 'Dispatch Board',
      icon: 'clipboard',
      route: '/dispatch',
      color: 'yellow',
    },
    {
      label: 'My Logbook',
      icon: 'book-open',
      route: '/flights/logbook',
      color: 'purple',
    },
  ];

  ngOnInit() {
    this.loadDashboardData();
  }

  private loadDashboardData() {
    // TODO: Load from API
    this.stats.set({
      todayBookings: 5,
      activeFlights: 2,
      upcomingExams: 1,
      pendingApprovals: 3,
    });
  }
}
