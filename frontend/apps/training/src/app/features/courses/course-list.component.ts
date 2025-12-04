import { Component, inject, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { HttpClient } from '@angular/common/http';

interface Course {
  id: string;
  title: string;
  description: string;
  category: string;
  duration_minutes: number;
  lesson_count: number;
  thumbnail_url?: string;
  progress_percentage?: number;
  status: 'not_started' | 'in_progress' | 'completed';
  required_for?: string[];
}

@Component({
  selector: 'fts-course-list',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
    <div class="p-6">
      <div class="flex justify-between items-center mb-6">
        <div>
          <h1 class="text-2xl font-bold text-gray-900 dark:text-white">Online Courses</h1>
          <p class="text-gray-600 dark:text-gray-400">Complete theory courses at your own pace</p>
        </div>
      </div>

      <!-- Progress summary -->
      <div class="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-sm mb-6">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm text-gray-500">Overall Progress</p>
            <p class="text-3xl font-bold text-gray-900 dark:text-white">{{ overallProgress() }}%</p>
          </div>
          <div class="grid grid-cols-3 gap-8 text-center">
            <div>
              <p class="text-2xl font-bold text-green-600">{{ completedCount() }}</p>
              <p class="text-sm text-gray-500">Completed</p>
            </div>
            <div>
              <p class="text-2xl font-bold text-blue-600">{{ inProgressCount() }}</p>
              <p class="text-sm text-gray-500">In Progress</p>
            </div>
            <div>
              <p class="text-2xl font-bold text-gray-400">{{ notStartedCount() }}</p>
              <p class="text-sm text-gray-500">Not Started</p>
            </div>
          </div>
        </div>
        <div class="mt-4 h-2 bg-gray-200 dark:bg-gray-600 rounded-full overflow-hidden">
          <div
            class="h-full bg-green-500 rounded-full"
            [style.width.%]="overallProgress()"
          ></div>
        </div>
      </div>

      <!-- Course grid -->
      @if (loading()) {
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          @for (i of [1,2,3,4,5,6]; track i) {
            <div class="bg-white dark:bg-gray-800 rounded-lg overflow-hidden animate-pulse">
              <div class="h-40 bg-gray-200 dark:bg-gray-700"></div>
              <div class="p-4">
                <div class="h-6 bg-gray-200 dark:bg-gray-700 rounded w-3/4 mb-2"></div>
                <div class="h-4 bg-gray-200 dark:bg-gray-700 rounded w-full"></div>
              </div>
            </div>
          }
        </div>
      } @else {
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          @for (course of courses(); track course.id) {
            <a
              [routerLink]="['/training/courses', course.id]"
              class="bg-white dark:bg-gray-800 rounded-lg shadow-sm overflow-hidden hover:shadow-md transition-shadow"
            >
              <div class="h-40 bg-gradient-to-br from-primary-500 to-primary-700 relative">
                <div class="absolute inset-0 flex items-center justify-center">
                  <svg class="w-16 h-16 text-white/30" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
                  </svg>
                </div>
                @if (course.status === 'completed') {
                  <div class="absolute top-3 right-3 bg-green-500 text-white px-2 py-1 rounded text-xs font-medium">
                    Completed
                  </div>
                } @else if (course.status === 'in_progress') {
                  <div class="absolute top-3 right-3 bg-blue-500 text-white px-2 py-1 rounded text-xs font-medium">
                    In Progress
                  </div>
                }
              </div>

              <div class="p-4">
                <span class="text-xs text-primary-600 dark:text-primary-400 font-medium uppercase">
                  {{ course.category }}
                </span>
                <h3 class="text-lg font-semibold text-gray-900 dark:text-white mt-1 mb-2">
                  {{ course.title }}
                </h3>
                <p class="text-gray-600 dark:text-gray-400 text-sm line-clamp-2 mb-4">
                  {{ course.description }}
                </p>

                <div class="flex items-center justify-between text-sm text-gray-500">
                  <span>{{ course.lesson_count }} lessons</span>
                  <span>{{ formatDuration(course.duration_minutes) }}</span>
                </div>

                @if (course.progress_percentage !== undefined && course.progress_percentage > 0) {
                  <div class="mt-3">
                    <div class="flex justify-between text-xs mb-1">
                      <span class="text-gray-500">Progress</span>
                      <span class="font-medium text-gray-900 dark:text-white">{{ course.progress_percentage }}%</span>
                    </div>
                    <div class="h-1.5 bg-gray-200 dark:bg-gray-600 rounded-full overflow-hidden">
                      <div
                        class="h-full bg-primary-600 rounded-full"
                        [style.width.%]="course.progress_percentage"
                      ></div>
                    </div>
                  </div>
                }

                @if (course.required_for && course.required_for.length > 0) {
                  <div class="mt-3 flex flex-wrap gap-1">
                    @for (req of course.required_for; track req) {
                      <span class="text-xs px-2 py-0.5 bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 rounded">
                        {{ req }}
                      </span>
                    }
                  </div>
                }
              </div>
            </a>
          } @empty {
            <div class="col-span-3 text-center py-12 text-gray-500">
              No courses available
            </div>
          }
        </div>
      }
    </div>
  `,
})
export class CourseListComponent implements OnInit {
  private http = inject(HttpClient);

  courses = signal<Course[]>([]);
  loading = signal(true);

  overallProgress = () => {
    const all = this.courses();
    if (all.length === 0) return 0;
    const total = all.reduce((sum, c) => sum + (c.progress_percentage || 0), 0);
    return Math.round(total / all.length);
  };

  completedCount = () => this.courses().filter((c) => c.status === 'completed').length;
  inProgressCount = () => this.courses().filter((c) => c.status === 'in_progress').length;
  notStartedCount = () => this.courses().filter((c) => c.status === 'not_started').length;

  ngOnInit() {
    this.loadCourses();
  }

  loadCourses() {
    this.loading.set(true);
    this.http.get<{ results: Course[] }>('/api/v1/theory/courses/').subscribe({
      next: (response) => {
        this.courses.set(response.results || []);
        this.loading.set(false);
      },
      error: () => {
        // Mock data
        this.courses.set([
          {
            id: '1',
            title: 'Principles of Flight',
            description: 'Understand the four forces of flight, aerodynamics, and how aircraft fly.',
            category: 'Aircraft Knowledge',
            duration_minutes: 180,
            lesson_count: 12,
            progress_percentage: 100,
            status: 'completed',
            required_for: ['PPL', 'CPL'],
          },
          {
            id: '2',
            title: 'Aviation Weather',
            description: 'Learn to interpret weather reports, forecasts, and understand meteorological phenomena.',
            category: 'Meteorology',
            duration_minutes: 240,
            lesson_count: 16,
            progress_percentage: 65,
            status: 'in_progress',
            required_for: ['PPL', 'IR'],
          },
          {
            id: '3',
            title: 'Navigation Fundamentals',
            description: 'Master chart reading, dead reckoning, and radio navigation techniques.',
            category: 'Navigation',
            duration_minutes: 300,
            lesson_count: 20,
            progress_percentage: 0,
            status: 'not_started',
            required_for: ['PPL', 'CPL'],
          },
          {
            id: '4',
            title: 'Air Law and Regulations',
            description: 'Comprehensive coverage of aviation law, airspace, and regulatory requirements.',
            category: 'Air Law',
            duration_minutes: 200,
            lesson_count: 14,
            progress_percentage: 100,
            status: 'completed',
            required_for: ['PPL', 'CPL', 'ATPL'],
          },
          {
            id: '5',
            title: 'Human Performance',
            description: 'Understanding human factors, limitations, and decision making in aviation.',
            category: 'Human Factors',
            duration_minutes: 150,
            lesson_count: 10,
            progress_percentage: 30,
            status: 'in_progress',
            required_for: ['PPL'],
          },
          {
            id: '6',
            title: 'Flight Planning',
            description: 'Learn to plan flights including fuel calculations, weight and balance, and NOTAMs.',
            category: 'Operations',
            duration_minutes: 180,
            lesson_count: 12,
            progress_percentage: 0,
            status: 'not_started',
            required_for: ['PPL', 'CPL'],
          },
        ]);
        this.loading.set(false);
      },
    });
  }

  formatDuration(minutes: number): string {
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    if (hours > 0 && mins > 0) {
      return `${hours}h ${mins}m`;
    } else if (hours > 0) {
      return `${hours}h`;
    }
    return `${mins}m`;
  }
}
