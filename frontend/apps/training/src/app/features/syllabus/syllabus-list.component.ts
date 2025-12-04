import { Component, inject, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { HttpClient } from '@angular/common/http';

interface Syllabus {
  id: string;
  name: string;
  description: string;
  license_type: 'PPL' | 'CPL' | 'ATPL' | 'IR' | 'MEP';
  total_lessons: number;
  total_flight_hours: number;
  total_ground_hours: number;
  status: 'draft' | 'active' | 'archived';
  created_at: string;
}

@Component({
  selector: 'fts-syllabus-list',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
    <div class="p-6">
      <div class="flex justify-between items-center mb-6">
        <div>
          <h1 class="text-2xl font-bold text-gray-900 dark:text-white">Training Syllabi</h1>
          <p class="text-gray-600 dark:text-gray-400">Manage training programs and lesson plans</p>
        </div>
        <button
          class="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
        >
          + New Syllabus
        </button>
      </div>

      <!-- Filter tabs -->
      <div class="flex gap-2 mb-6">
        @for (type of licenseTypes; track type) {
          <button
            (click)="filterByType(type)"
            [class]="selectedType() === type
              ? 'px-4 py-2 bg-primary-600 text-white rounded-lg'
              : 'px-4 py-2 bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-700'"
          >
            {{ type }}
          </button>
        }
      </div>

      <!-- Syllabus grid -->
      @if (loading()) {
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          @for (i of [1,2,3,4,5,6]; track i) {
            <div class="bg-white dark:bg-gray-800 rounded-lg p-6 animate-pulse">
              <div class="h-6 bg-gray-200 dark:bg-gray-700 rounded w-3/4 mb-4"></div>
              <div class="h-4 bg-gray-200 dark:bg-gray-700 rounded w-full mb-2"></div>
              <div class="h-4 bg-gray-200 dark:bg-gray-700 rounded w-2/3"></div>
            </div>
          }
        </div>
      } @else {
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          @for (syllabus of filteredSyllabi(); track syllabus.id) {
            <a
              [routerLink]="['/training/syllabus', syllabus.id]"
              class="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-sm hover:shadow-md transition-shadow border border-gray-200 dark:border-gray-700"
            >
              <div class="flex justify-between items-start mb-4">
                <span
                  [class]="'px-2 py-1 text-xs font-medium rounded ' + getLicenseTypeClass(syllabus.license_type)"
                >
                  {{ syllabus.license_type }}
                </span>
                <span
                  [class]="'px-2 py-1 text-xs font-medium rounded ' + getStatusClass(syllabus.status)"
                >
                  {{ syllabus.status }}
                </span>
              </div>

              <h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-2">
                {{ syllabus.name }}
              </h3>
              <p class="text-gray-600 dark:text-gray-400 text-sm mb-4 line-clamp-2">
                {{ syllabus.description }}
              </p>

              <div class="grid grid-cols-3 gap-4 text-center border-t border-gray-200 dark:border-gray-700 pt-4">
                <div>
                  <p class="text-2xl font-bold text-primary-600">{{ syllabus.total_lessons }}</p>
                  <p class="text-xs text-gray-500">Lessons</p>
                </div>
                <div>
                  <p class="text-2xl font-bold text-blue-600">{{ syllabus.total_flight_hours }}</p>
                  <p class="text-xs text-gray-500">Flight Hrs</p>
                </div>
                <div>
                  <p class="text-2xl font-bold text-green-600">{{ syllabus.total_ground_hours }}</p>
                  <p class="text-xs text-gray-500">Ground Hrs</p>
                </div>
              </div>
            </a>
          } @empty {
            <div class="col-span-3 text-center py-12 text-gray-500">
              No syllabi found for the selected filter
            </div>
          }
        </div>
      }
    </div>
  `,
})
export class SyllabusListComponent implements OnInit {
  private http = inject(HttpClient);

  syllabi = signal<Syllabus[]>([]);
  loading = signal(true);
  selectedType = signal<string>('All');

  licenseTypes = ['All', 'PPL', 'CPL', 'ATPL', 'IR', 'MEP'];

  filteredSyllabi = () => {
    const type = this.selectedType();
    if (type === 'All') return this.syllabi();
    return this.syllabi().filter((s) => s.license_type === type);
  };

  ngOnInit() {
    this.loadSyllabi();
  }

  loadSyllabi() {
    this.loading.set(true);
    this.http.get<{ results: Syllabus[] }>('/api/v1/training/syllabi/').subscribe({
      next: (response) => {
        this.syllabi.set(response.results || []);
        this.loading.set(false);
      },
      error: () => {
        // Mock data for development
        this.syllabi.set([
          {
            id: '1',
            name: 'Private Pilot License',
            description: 'Complete PPL training program covering all required ground and flight training per EASA Part-FCL.',
            license_type: 'PPL',
            total_lessons: 45,
            total_flight_hours: 45,
            total_ground_hours: 100,
            status: 'active',
            created_at: '2024-01-15',
          },
          {
            id: '2',
            name: 'Commercial Pilot License',
            description: 'CPL training building on PPL with advanced maneuvers and commercial operations.',
            license_type: 'CPL',
            total_lessons: 65,
            total_flight_hours: 150,
            total_ground_hours: 200,
            status: 'active',
            created_at: '2024-02-20',
          },
          {
            id: '3',
            name: 'Instrument Rating',
            description: 'IFR training for flight in instrument meteorological conditions.',
            license_type: 'IR',
            total_lessons: 30,
            total_flight_hours: 50,
            total_ground_hours: 80,
            status: 'active',
            created_at: '2024-03-10',
          },
        ]);
        this.loading.set(false);
      },
    });
  }

  filterByType(type: string) {
    this.selectedType.set(type);
  }

  getLicenseTypeClass(type: string): string {
    const classes: Record<string, string> = {
      PPL: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
      CPL: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200',
      ATPL: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
      IR: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
      MEP: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
    };
    return classes[type] || 'bg-gray-100 text-gray-800';
  }

  getStatusClass(status: string): string {
    const classes: Record<string, string> = {
      active: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
      draft: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
      archived: 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200',
    };
    return classes[status] || 'bg-gray-100 text-gray-800';
  }
}
