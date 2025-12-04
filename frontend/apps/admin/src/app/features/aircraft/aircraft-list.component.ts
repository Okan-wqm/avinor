import { Component, inject, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { HttpClient } from '@angular/common/http';

interface Aircraft {
  id: string;
  registration: string;
  type: string;
  model: string;
  year: number;
  status: 'available' | 'in_flight' | 'maintenance' | 'grounded';
  total_hours: number;
  hours_to_next_service: number;
  last_flight?: string;
  hourly_rate: number;
}

@Component({
  selector: 'fts-aircraft-list',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
    <div class="p-6">
      <div class="flex justify-between items-center mb-6">
        <div>
          <h1 class="text-2xl font-bold text-gray-900 dark:text-white">Aircraft Fleet</h1>
          <p class="text-gray-600 dark:text-gray-400">Manage aircraft and maintenance schedules</p>
        </div>
        <a
          routerLink="/admin/aircraft/new"
          class="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
        >
          + Add Aircraft
        </a>
      </div>

      <!-- Status summary -->
      <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <div class="bg-white dark:bg-gray-800 rounded-lg p-4 shadow-sm">
          <p class="text-sm text-gray-500">Available</p>
          <p class="text-3xl font-bold text-green-600">{{ getStatusCount('available') }}</p>
        </div>
        <div class="bg-white dark:bg-gray-800 rounded-lg p-4 shadow-sm">
          <p class="text-sm text-gray-500">In Flight</p>
          <p class="text-3xl font-bold text-blue-600">{{ getStatusCount('in_flight') }}</p>
        </div>
        <div class="bg-white dark:bg-gray-800 rounded-lg p-4 shadow-sm">
          <p class="text-sm text-gray-500">Maintenance</p>
          <p class="text-3xl font-bold text-yellow-600">{{ getStatusCount('maintenance') }}</p>
        </div>
        <div class="bg-white dark:bg-gray-800 rounded-lg p-4 shadow-sm">
          <p class="text-sm text-gray-500">Grounded</p>
          <p class="text-3xl font-bold text-red-600">{{ getStatusCount('grounded') }}</p>
        </div>
      </div>

      <!-- Aircraft grid -->
      @if (loading()) {
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          @for (i of [1,2,3,4,5,6]; track i) {
            <div class="bg-white dark:bg-gray-800 rounded-lg p-6 animate-pulse">
              <div class="h-6 bg-gray-200 dark:bg-gray-700 rounded w-1/2 mb-4"></div>
              <div class="h-4 bg-gray-200 dark:bg-gray-700 rounded w-3/4"></div>
            </div>
          }
        </div>
      } @else {
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          @for (aircraft of aircraft(); track aircraft.id) {
            <a
              [routerLink]="['/admin/aircraft', aircraft.id]"
              class="bg-white dark:bg-gray-800 rounded-lg shadow-sm overflow-hidden hover:shadow-md transition-shadow"
            >
              <div class="h-32 bg-gradient-to-br from-gray-700 to-gray-900 relative flex items-center justify-center">
                <svg class="w-16 h-16 text-white/30" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                </svg>
                <span
                  [class]="'absolute top-3 right-3 px-2 py-1 text-xs font-medium rounded capitalize ' + getStatusClass(aircraft.status)"
                >
                  {{ aircraft.status.replace('_', ' ') }}
                </span>
              </div>

              <div class="p-4">
                <div class="flex justify-between items-start mb-2">
                  <div>
                    <h3 class="text-lg font-bold text-gray-900 dark:text-white">
                      {{ aircraft.registration }}
                    </h3>
                    <p class="text-gray-600 dark:text-gray-400 text-sm">
                      {{ aircraft.type }} {{ aircraft.model }}
                    </p>
                  </div>
                  <p class="text-lg font-semibold text-primary-600">
                    {{ aircraft.hourly_rate | currency:'NOK':'symbol':'1.0-0' }}/hr
                  </p>
                </div>

                <div class="grid grid-cols-2 gap-4 mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
                  <div>
                    <p class="text-xs text-gray-500">Total Hours</p>
                    <p class="font-semibold text-gray-900 dark:text-white">{{ aircraft.total_hours }}</p>
                  </div>
                  <div>
                    <p class="text-xs text-gray-500">Next Service</p>
                    <p
                      [class]="'font-semibold ' + (aircraft.hours_to_next_service < 10 ? 'text-red-600' : 'text-gray-900 dark:text-white')"
                    >
                      {{ aircraft.hours_to_next_service }} hrs
                    </p>
                  </div>
                </div>

                @if (aircraft.hours_to_next_service < 10) {
                  <div class="mt-3 px-3 py-2 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded text-sm text-yellow-700 dark:text-yellow-300">
                    Service required soon
                  </div>
                }
              </div>
            </a>
          } @empty {
            <div class="col-span-3 text-center py-12 text-gray-500">
              No aircraft in the fleet
            </div>
          }
        </div>
      }
    </div>
  `,
})
export class AircraftListComponent implements OnInit {
  private http = inject(HttpClient);

  aircraft = signal<Aircraft[]>([]);
  loading = signal(true);

  ngOnInit() {
    this.loadAircraft();
  }

  loadAircraft() {
    this.loading.set(true);
    this.http.get<{ results: Aircraft[] }>('/api/v1/aircraft/').subscribe({
      next: (response) => {
        this.aircraft.set(response.results || []);
        this.loading.set(false);
      },
      error: () => {
        // Mock data
        this.aircraft.set([
          {
            id: '1',
            registration: 'LN-ABC',
            type: 'Cessna',
            model: '172S Skyhawk',
            year: 2018,
            status: 'available',
            total_hours: 2450,
            hours_to_next_service: 45,
            last_flight: '2024-12-03',
            hourly_rate: 2200,
          },
          {
            id: '2',
            registration: 'LN-DEF',
            type: 'Piper',
            model: 'PA-28 Cherokee',
            year: 2015,
            status: 'in_flight',
            total_hours: 3200,
            hours_to_next_service: 28,
            last_flight: '2024-12-04',
            hourly_rate: 1950,
          },
          {
            id: '3',
            registration: 'LN-GHI',
            type: 'Diamond',
            model: 'DA40 NG',
            year: 2020,
            status: 'available',
            total_hours: 1100,
            hours_to_next_service: 85,
            last_flight: '2024-12-02',
            hourly_rate: 2800,
          },
          {
            id: '4',
            registration: 'LN-JKL',
            type: 'Cessna',
            model: '182T Skylane',
            year: 2016,
            status: 'maintenance',
            total_hours: 2800,
            hours_to_next_service: 0,
            last_flight: '2024-11-28',
            hourly_rate: 2600,
          },
          {
            id: '5',
            registration: 'LN-MNO',
            type: 'Piper',
            model: 'PA-44 Seminole',
            year: 2019,
            status: 'available',
            total_hours: 1850,
            hours_to_next_service: 8,
            last_flight: '2024-12-01',
            hourly_rate: 4200,
          },
        ]);
        this.loading.set(false);
      },
    });
  }

  getStatusCount(status: string): number {
    return this.aircraft().filter((a) => a.status === status).length;
  }

  getStatusClass(status: string): string {
    const classes: Record<string, string> = {
      available: 'bg-green-100 text-green-800',
      in_flight: 'bg-blue-100 text-blue-800',
      maintenance: 'bg-yellow-100 text-yellow-800',
      grounded: 'bg-red-100 text-red-800',
    };
    return classes[status] || 'bg-gray-100 text-gray-800';
  }
}
