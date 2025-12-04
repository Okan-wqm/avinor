import { Component, inject, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { HttpClient } from '@angular/common/http';

interface AircraftDetail {
  id: string;
  registration: string;
  type: string;
  model: string;
  serial_number: string;
  year: number;
  status: string;
  total_hours: number;
  hours_to_next_service: number;
  hourly_rate: number;
  insurance_expiry: string;
  airworthiness_expiry: string;
  maintenance_history: { date: string; type: string; description: string; hours: number }[];
}

@Component({
  selector: 'fts-aircraft-detail',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
    <div class="p-6 max-w-4xl mx-auto">
      <a routerLink="/admin/aircraft" class="inline-flex items-center text-gray-600 dark:text-gray-400 hover:text-primary-600 mb-6">
        <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
        </svg>
        Back to Fleet
      </a>

      @if (aircraft()) {
        <div class="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-sm mb-6">
          <div class="flex justify-between items-start">
            <div>
              <h1 class="text-3xl font-bold text-gray-900 dark:text-white">{{ aircraft()!.registration }}</h1>
              <p class="text-gray-600 dark:text-gray-400">{{ aircraft()!.type }} {{ aircraft()!.model }}</p>
            </div>
            <span class="px-3 py-1 bg-green-100 text-green-800 rounded-full text-sm font-medium capitalize">
              {{ aircraft()!.status }}
            </span>
          </div>

          <div class="grid grid-cols-2 md:grid-cols-4 gap-6 mt-6 pt-6 border-t border-gray-200 dark:border-gray-700">
            <div><p class="text-sm text-gray-500">Total Hours</p><p class="text-xl font-bold">{{ aircraft()!.total_hours }}</p></div>
            <div><p class="text-sm text-gray-500">Next Service</p><p class="text-xl font-bold">{{ aircraft()!.hours_to_next_service }} hrs</p></div>
            <div><p class="text-sm text-gray-500">Hourly Rate</p><p class="text-xl font-bold">{{ aircraft()!.hourly_rate | currency:'NOK' }}</p></div>
            <div><p class="text-sm text-gray-500">Year</p><p class="text-xl font-bold">{{ aircraft()!.year }}</p></div>
          </div>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
          <div class="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-sm">
            <h3 class="font-semibold text-gray-900 dark:text-white mb-4">Certifications</h3>
            <div class="space-y-3">
              <div class="flex justify-between"><span class="text-gray-500">Insurance Expiry</span><span>{{ aircraft()!.insurance_expiry | date }}</span></div>
              <div class="flex justify-between"><span class="text-gray-500">Airworthiness</span><span>{{ aircraft()!.airworthiness_expiry | date }}</span></div>
            </div>
          </div>
          <div class="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-sm">
            <h3 class="font-semibold text-gray-900 dark:text-white mb-4">Details</h3>
            <div class="space-y-3">
              <div class="flex justify-between"><span class="text-gray-500">Serial Number</span><span>{{ aircraft()!.serial_number }}</span></div>
            </div>
          </div>
        </div>

        <div class="bg-white dark:bg-gray-800 rounded-lg shadow-sm overflow-hidden">
          <div class="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
            <h3 class="font-semibold text-gray-900 dark:text-white">Maintenance History</h3>
          </div>
          <div class="divide-y divide-gray-200 dark:divide-gray-700">
            @for (item of aircraft()!.maintenance_history; track item.date) {
              <div class="px-6 py-4">
                <div class="flex justify-between"><span class="font-medium">{{ item.type }}</span><span class="text-gray-500">{{ item.date | date }}</span></div>
                <p class="text-sm text-gray-600 dark:text-gray-400">{{ item.description }} ({{ item.hours }} hrs)</p>
              </div>
            }
          </div>
        </div>
      }
    </div>
  `,
})
export class AircraftDetailComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private http = inject(HttpClient);
  aircraft = signal<AircraftDetail | null>(null);

  ngOnInit() {
    const id = this.route.snapshot.paramMap.get('id');
    if (id) this.loadAircraft(id);
  }

  loadAircraft(id: string) {
    this.http.get<AircraftDetail>(`/api/v1/aircraft/${id}/`).subscribe({
      next: (a) => this.aircraft.set(a),
      error: () => {
        this.aircraft.set({
          id: '1', registration: 'LN-ABC', type: 'Cessna', model: '172S Skyhawk', serial_number: '172S12345',
          year: 2018, status: 'available', total_hours: 2450, hours_to_next_service: 45, hourly_rate: 2200,
          insurance_expiry: '2025-06-30', airworthiness_expiry: '2025-03-15',
          maintenance_history: [
            { date: '2024-11-01', type: '100-Hour Inspection', description: 'Routine inspection completed', hours: 2400 },
            { date: '2024-08-15', type: 'Annual Inspection', description: 'Annual inspection and AD compliance', hours: 2350 },
          ],
        });
      },
    });
  }
}
