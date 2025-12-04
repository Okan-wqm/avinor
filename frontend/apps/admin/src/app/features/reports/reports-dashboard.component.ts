import { Component, signal } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'fts-reports-dashboard',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="p-6">
      <h1 class="text-2xl font-bold text-gray-900 dark:text-white mb-6">Reports</h1>

      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        @for (report of reports(); track report.id) {
          <div class="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-6 hover:shadow-md transition-shadow cursor-pointer">
            <div class="flex items-center gap-4 mb-4">
              <div class="w-12 h-12 bg-primary-100 dark:bg-primary-900 rounded-lg flex items-center justify-center">
                <svg class="w-6 h-6 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </div>
              <div>
                <h3 class="font-semibold text-gray-900 dark:text-white">{{ report.name }}</h3>
                <p class="text-sm text-gray-500">{{ report.category }}</p>
              </div>
            </div>
            <p class="text-gray-600 dark:text-gray-400 text-sm mb-4">{{ report.description }}</p>
            <div class="flex justify-between items-center">
              <span class="text-xs text-gray-500">Last run: {{ report.last_run | date:'short' }}</span>
              <button class="text-primary-600 hover:text-primary-700 text-sm font-medium">Generate</button>
            </div>
          </div>
        }
      </div>
    </div>
  `,
})
export class ReportsDashboardComponent {
  reports = signal([
    { id: '1', name: 'Flight Hours Summary', category: 'Operations', description: 'Total flight hours by aircraft, instructor, and student', last_run: '2024-12-03' },
    { id: '2', name: 'Revenue Report', category: 'Finance', description: 'Revenue breakdown by service type and period', last_run: '2024-12-01' },
    { id: '3', name: 'Aircraft Utilization', category: 'Operations', description: 'Aircraft usage rates and availability analysis', last_run: '2024-11-30' },
    { id: '4', name: 'Student Progress', category: 'Training', description: 'Training progress summary for all active students', last_run: '2024-12-02' },
    { id: '5', name: 'Maintenance Schedule', category: 'Maintenance', description: 'Upcoming maintenance requirements and history', last_run: '2024-11-28' },
    { id: '6', name: 'Instructor Activity', category: 'Operations', description: 'Instructor flight hours and student assignments', last_run: '2024-12-01' },
  ]);
}
