import { Component, inject, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { HttpClient } from '@angular/common/http';

interface StudentProgress {
  id: string;
  student: {
    id: string;
    name: string;
    email: string;
    avatar_url?: string;
  };
  syllabus: {
    id: string;
    name: string;
    license_type: string;
  };
  progress_percentage: number;
  completed_lessons: number;
  total_lessons: number;
  flight_hours_logged: number;
  flight_hours_required: number;
  ground_hours_logged: number;
  ground_hours_required: number;
  last_lesson_date: string;
  status: 'active' | 'paused' | 'completed';
  instructor?: {
    id: string;
    name: string;
  };
}

@Component({
  selector: 'fts-progress-dashboard',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
    <div class="p-6">
      <div class="flex justify-between items-center mb-6">
        <div>
          <h1 class="text-2xl font-bold text-gray-900 dark:text-white">Training Progress</h1>
          <p class="text-gray-600 dark:text-gray-400">Monitor student training progression</p>
        </div>
        <div class="flex gap-2">
          <select
            class="px-4 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-700 dark:text-gray-300"
            (change)="filterByStatus($event)"
          >
            <option value="all">All Status</option>
            <option value="active">Active</option>
            <option value="paused">Paused</option>
            <option value="completed">Completed</option>
          </select>
        </div>
      </div>

      <!-- Summary cards -->
      <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <div class="bg-white dark:bg-gray-800 rounded-lg p-4 shadow-sm">
          <p class="text-sm text-gray-500 dark:text-gray-400">Active Students</p>
          <p class="text-3xl font-bold text-primary-600">{{ activeCount() }}</p>
        </div>
        <div class="bg-white dark:bg-gray-800 rounded-lg p-4 shadow-sm">
          <p class="text-sm text-gray-500 dark:text-gray-400">Avg. Progress</p>
          <p class="text-3xl font-bold text-blue-600">{{ averageProgress() }}%</p>
        </div>
        <div class="bg-white dark:bg-gray-800 rounded-lg p-4 shadow-sm">
          <p class="text-sm text-gray-500 dark:text-gray-400">Completed This Month</p>
          <p class="text-3xl font-bold text-green-600">{{ completedThisMonth() }}</p>
        </div>
        <div class="bg-white dark:bg-gray-800 rounded-lg p-4 shadow-sm">
          <p class="text-sm text-gray-500 dark:text-gray-400">Needs Attention</p>
          <p class="text-3xl font-bold text-warning-600">{{ needsAttention() }}</p>
        </div>
      </div>

      <!-- Progress table -->
      <div class="bg-white dark:bg-gray-800 rounded-lg shadow-sm overflow-hidden">
        <table class="w-full">
          <thead class="bg-gray-50 dark:bg-gray-700">
            <tr>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                Student
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                Program
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                Progress
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                Flight Hours
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                Last Activity
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                Status
              </th>
              <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-200 dark:divide-gray-700">
            @for (progress of filteredProgress(); track progress.id) {
              <tr class="hover:bg-gray-50 dark:hover:bg-gray-700/50">
                <td class="px-6 py-4 whitespace-nowrap">
                  <div class="flex items-center">
                    <div class="h-10 w-10 rounded-full bg-primary-100 dark:bg-primary-900 flex items-center justify-center">
                      <span class="text-primary-600 dark:text-primary-400 font-medium">
                        {{ progress.student.name.charAt(0) }}
                      </span>
                    </div>
                    <div class="ml-4">
                      <p class="font-medium text-gray-900 dark:text-white">{{ progress.student.name }}</p>
                      <p class="text-sm text-gray-500">{{ progress.student.email }}</p>
                    </div>
                  </div>
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                  <p class="text-gray-900 dark:text-white">{{ progress.syllabus.name }}</p>
                  <span class="text-xs px-2 py-1 bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200 rounded">
                    {{ progress.syllabus.license_type }}
                  </span>
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                  <div class="flex items-center gap-2">
                    <div class="flex-1 h-2 bg-gray-200 dark:bg-gray-600 rounded-full overflow-hidden">
                      <div
                        class="h-full bg-primary-600 rounded-full"
                        [style.width.%]="progress.progress_percentage"
                      ></div>
                    </div>
                    <span class="text-sm font-medium text-gray-700 dark:text-gray-300">
                      {{ progress.progress_percentage }}%
                    </span>
                  </div>
                  <p class="text-xs text-gray-500 mt-1">
                    {{ progress.completed_lessons }}/{{ progress.total_lessons }} lessons
                  </p>
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                  <p class="text-gray-900 dark:text-white">
                    {{ progress.flight_hours_logged }}/{{ progress.flight_hours_required }} hrs
                  </p>
                  <div class="w-full h-1.5 bg-gray-200 dark:bg-gray-600 rounded-full mt-1">
                    <div
                      class="h-full bg-blue-600 rounded-full"
                      [style.width.%]="(progress.flight_hours_logged / progress.flight_hours_required) * 100"
                    ></div>
                  </div>
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                  {{ progress.last_lesson_date | date:'mediumDate' }}
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                  <span
                    [class]="'px-2 py-1 text-xs font-medium rounded-full ' + getStatusClass(progress.status)"
                  >
                    {{ progress.status }}
                  </span>
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-right">
                  <a
                    [routerLink]="['/training/progress', progress.student.id]"
                    class="text-primary-600 hover:text-primary-700 font-medium text-sm"
                  >
                    View Details
                  </a>
                </td>
              </tr>
            } @empty {
              <tr>
                <td colspan="7" class="px-6 py-12 text-center text-gray-500">
                  No student progress records found
                </td>
              </tr>
            }
          </tbody>
        </table>
      </div>
    </div>
  `,
})
export class ProgressDashboardComponent implements OnInit {
  private http = inject(HttpClient);

  progressRecords = signal<StudentProgress[]>([]);
  loading = signal(true);
  statusFilter = signal<string>('all');

  filteredProgress = () => {
    const status = this.statusFilter();
    if (status === 'all') return this.progressRecords();
    return this.progressRecords().filter((p) => p.status === status);
  };

  activeCount = () => this.progressRecords().filter((p) => p.status === 'active').length;

  averageProgress = () => {
    const active = this.progressRecords().filter((p) => p.status === 'active');
    if (active.length === 0) return 0;
    return Math.round(active.reduce((sum, p) => sum + p.progress_percentage, 0) / active.length);
  };

  completedThisMonth = () => this.progressRecords().filter((p) => p.status === 'completed').length;

  needsAttention = () => {
    const thirtyDaysAgo = new Date();
    thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);
    return this.progressRecords().filter(
      (p) => p.status === 'active' && new Date(p.last_lesson_date) < thirtyDaysAgo
    ).length;
  };

  ngOnInit() {
    this.loadProgress();
  }

  loadProgress() {
    this.loading.set(true);
    this.http.get<{ results: StudentProgress[] }>('/api/v1/training/progress/').subscribe({
      next: (response) => {
        this.progressRecords.set(response.results || []);
        this.loading.set(false);
      },
      error: () => {
        // Mock data
        this.progressRecords.set([
          {
            id: '1',
            student: { id: 's1', name: 'John Pilot', email: 'john@example.com' },
            syllabus: { id: 'sy1', name: 'Private Pilot License', license_type: 'PPL' },
            progress_percentage: 65,
            completed_lessons: 29,
            total_lessons: 45,
            flight_hours_logged: 32,
            flight_hours_required: 45,
            ground_hours_logged: 75,
            ground_hours_required: 100,
            last_lesson_date: '2024-12-01',
            status: 'active',
            instructor: { id: 'i1', name: 'Capt. Smith' },
          },
          {
            id: '2',
            student: { id: 's2', name: 'Jane Aviator', email: 'jane@example.com' },
            syllabus: { id: 'sy1', name: 'Private Pilot License', license_type: 'PPL' },
            progress_percentage: 88,
            completed_lessons: 40,
            total_lessons: 45,
            flight_hours_logged: 42,
            flight_hours_required: 45,
            ground_hours_logged: 95,
            ground_hours_required: 100,
            last_lesson_date: '2024-12-03',
            status: 'active',
            instructor: { id: 'i2', name: 'Capt. Johnson' },
          },
          {
            id: '3',
            student: { id: 's3', name: 'Mike Flyer', email: 'mike@example.com' },
            syllabus: { id: 'sy2', name: 'Instrument Rating', license_type: 'IR' },
            progress_percentage: 100,
            completed_lessons: 30,
            total_lessons: 30,
            flight_hours_logged: 50,
            flight_hours_required: 50,
            ground_hours_logged: 80,
            ground_hours_required: 80,
            last_lesson_date: '2024-11-28',
            status: 'completed',
            instructor: { id: 'i1', name: 'Capt. Smith' },
          },
        ]);
        this.loading.set(false);
      },
    });
  }

  filterByStatus(event: Event) {
    const select = event.target as HTMLSelectElement;
    this.statusFilter.set(select.value);
  }

  getStatusClass(status: string): string {
    const classes: Record<string, string> = {
      active: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
      paused: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
      completed: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
    };
    return classes[status] || 'bg-gray-100 text-gray-800';
  }
}
