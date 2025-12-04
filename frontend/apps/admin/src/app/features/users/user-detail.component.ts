import { Component, inject, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { HttpClient } from '@angular/common/http';

interface UserDetail {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  phone?: string;
  role: 'student' | 'instructor' | 'staff' | 'admin';
  status: 'active' | 'inactive' | 'suspended';
  created_at: string;
  last_login?: string;
  permissions: string[];
  organization?: {
    id: string;
    name: string;
  };
  stats?: {
    total_bookings: number;
    total_flights: number;
    total_flight_hours: number;
  };
}

@Component({
  selector: 'fts-user-detail',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
    <div class="p-6 max-w-4xl mx-auto">
      <a
        routerLink="/admin/users"
        class="inline-flex items-center text-gray-600 dark:text-gray-400 hover:text-primary-600 mb-6"
      >
        <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
        </svg>
        Back to Users
      </a>

      @if (loading()) {
        <div class="animate-pulse space-y-6">
          <div class="h-32 bg-gray-200 dark:bg-gray-700 rounded-lg"></div>
          <div class="h-48 bg-gray-200 dark:bg-gray-700 rounded-lg"></div>
        </div>
      } @else if (user()) {
        <!-- User header -->
        <div class="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-sm mb-6">
          <div class="flex justify-between items-start">
            <div class="flex items-center gap-4">
              <div class="h-20 w-20 rounded-full bg-primary-100 dark:bg-primary-900 flex items-center justify-center">
                <span class="text-3xl text-primary-600 dark:text-primary-400 font-bold">
                  {{ user()!.first_name.charAt(0) }}{{ user()!.last_name.charAt(0) }}
                </span>
              </div>
              <div>
                <h1 class="text-2xl font-bold text-gray-900 dark:text-white">
                  {{ user()!.first_name }} {{ user()!.last_name }}
                </h1>
                <p class="text-gray-600 dark:text-gray-400">{{ user()!.email }}</p>
                @if (user()!.phone) {
                  <p class="text-gray-500 text-sm">{{ user()!.phone }}</p>
                }
              </div>
            </div>
            <div class="flex gap-2">
              <a
                [routerLink]="['/admin/users', user()!.id, 'edit']"
                class="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
              >
                Edit User
              </a>
              <button
                class="px-4 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700"
              >
                Reset Password
              </button>
            </div>
          </div>

          <div class="flex gap-4 mt-6">
            <span
              [class]="'px-3 py-1 text-sm font-medium rounded-full capitalize ' + getRoleClass(user()!.role)"
            >
              {{ user()!.role }}
            </span>
            <span
              [class]="'px-3 py-1 text-sm font-medium rounded-full capitalize ' + getStatusClass(user()!.status)"
            >
              {{ user()!.status }}
            </span>
          </div>
        </div>

        <!-- Stats -->
        @if (user()!.stats) {
          <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            <div class="bg-white dark:bg-gray-800 rounded-lg p-4 shadow-sm text-center">
              <p class="text-3xl font-bold text-primary-600">{{ user()!.stats!.total_bookings }}</p>
              <p class="text-sm text-gray-500">Total Bookings</p>
            </div>
            <div class="bg-white dark:bg-gray-800 rounded-lg p-4 shadow-sm text-center">
              <p class="text-3xl font-bold text-blue-600">{{ user()!.stats!.total_flights }}</p>
              <p class="text-sm text-gray-500">Total Flights</p>
            </div>
            <div class="bg-white dark:bg-gray-800 rounded-lg p-4 shadow-sm text-center">
              <p class="text-3xl font-bold text-green-600">{{ user()!.stats!.total_flight_hours }}</p>
              <p class="text-sm text-gray-500">Flight Hours</p>
            </div>
          </div>
        }

        <!-- Details -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div class="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-sm">
            <h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-4">Account Details</h3>
            <dl class="space-y-3">
              <div class="flex justify-between">
                <dt class="text-gray-500">Created</dt>
                <dd class="text-gray-900 dark:text-white">{{ user()!.created_at | date:'mediumDate' }}</dd>
              </div>
              <div class="flex justify-between">
                <dt class="text-gray-500">Last Login</dt>
                <dd class="text-gray-900 dark:text-white">
                  {{ user()!.last_login ? (user()!.last_login | date:'medium') : 'Never' }}
                </dd>
              </div>
              @if (user()!.organization) {
                <div class="flex justify-between">
                  <dt class="text-gray-500">Organization</dt>
                  <dd class="text-gray-900 dark:text-white">{{ user()!.organization!.name }}</dd>
                </div>
              }
            </dl>
          </div>

          <div class="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-sm">
            <h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-4">Permissions</h3>
            <div class="flex flex-wrap gap-2">
              @for (permission of user()!.permissions; track permission) {
                <span class="px-2 py-1 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded text-sm">
                  {{ permission }}
                </span>
              } @empty {
                <p class="text-gray-500">No special permissions</p>
              }
            </div>
          </div>
        </div>

        <!-- Actions -->
        <div class="mt-6 pt-6 border-t border-gray-200 dark:border-gray-700">
          <h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-4">Account Actions</h3>
          <div class="flex gap-4">
            @if (user()!.status === 'active') {
              <button class="px-4 py-2 bg-yellow-100 text-yellow-800 rounded-lg hover:bg-yellow-200">
                Suspend Account
              </button>
            } @else if (user()!.status === 'suspended') {
              <button class="px-4 py-2 bg-green-100 text-green-800 rounded-lg hover:bg-green-200">
                Reactivate Account
              </button>
            }
            <button class="px-4 py-2 bg-red-100 text-red-800 rounded-lg hover:bg-red-200">
              Delete Account
            </button>
          </div>
        </div>
      }
    </div>
  `,
})
export class UserDetailComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private http = inject(HttpClient);

  user = signal<UserDetail | null>(null);
  loading = signal(true);

  ngOnInit() {
    const id = this.route.snapshot.paramMap.get('id');
    if (id) {
      this.loadUser(id);
    }
  }

  loadUser(id: string) {
    this.loading.set(true);
    this.http.get<UserDetail>(`/api/v1/users/${id}/`).subscribe({
      next: (user) => {
        this.user.set(user);
        this.loading.set(false);
      },
      error: () => {
        // Mock data
        this.user.set({
          id: '1',
          email: 'john.pilot@example.com',
          first_name: 'John',
          last_name: 'Pilot',
          phone: '+47 123 45 678',
          role: 'student',
          status: 'active',
          created_at: '2024-01-15',
          last_login: '2024-12-03T14:30:00Z',
          permissions: ['book_flights', 'view_own_flights', 'view_own_progress'],
          organization: {
            id: 'org1',
            name: 'Oslo Flight Academy',
          },
          stats: {
            total_bookings: 45,
            total_flights: 38,
            total_flight_hours: 32,
          },
        });
        this.loading.set(false);
      },
    });
  }

  getRoleClass(role: string): string {
    const classes: Record<string, string> = {
      student: 'bg-blue-100 text-blue-800',
      instructor: 'bg-purple-100 text-purple-800',
      staff: 'bg-green-100 text-green-800',
      admin: 'bg-red-100 text-red-800',
    };
    return classes[role] || 'bg-gray-100 text-gray-800';
  }

  getStatusClass(status: string): string {
    const classes: Record<string, string> = {
      active: 'bg-green-100 text-green-800',
      inactive: 'bg-gray-100 text-gray-800',
      suspended: 'bg-red-100 text-red-800',
    };
    return classes[status] || 'bg-gray-100 text-gray-800';
  }
}
