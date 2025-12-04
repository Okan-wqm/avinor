import { Component, inject, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { HttpClient } from '@angular/common/http';

interface Exam {
  id: string;
  title: string;
  description: string;
  category: 'air_law' | 'navigation' | 'meteorology' | 'aircraft_knowledge' | 'human_performance' | 'operational_procedures';
  license_type: string;
  question_count: number;
  time_limit_minutes: number;
  passing_score: number;
  attempts_allowed: number;
  user_attempts?: number;
  best_score?: number;
  status: 'available' | 'in_progress' | 'passed' | 'failed';
}

@Component({
  selector: 'fts-exam-list',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
    <div class="p-6">
      <div class="flex justify-between items-center mb-6">
        <div>
          <h1 class="text-2xl font-bold text-gray-900 dark:text-white">Theory Exams</h1>
          <p class="text-gray-600 dark:text-gray-400">Complete required knowledge tests for your training</p>
        </div>
      </div>

      <!-- Category filter -->
      <div class="flex flex-wrap gap-2 mb-6">
        @for (cat of categories; track cat.value) {
          <button
            (click)="filterByCategory(cat.value)"
            [class]="selectedCategory() === cat.value
              ? 'px-4 py-2 bg-primary-600 text-white rounded-lg'
              : 'px-4 py-2 bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-700'"
          >
            {{ cat.label }}
          </button>
        }
      </div>

      <!-- Exam grid -->
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
          @for (exam of filteredExams(); track exam.id) {
            <div class="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 overflow-hidden">
              <div class="p-6">
                <div class="flex justify-between items-start mb-4">
                  <span
                    [class]="'px-2 py-1 text-xs font-medium rounded ' + getCategoryClass(exam.category)"
                  >
                    {{ getCategoryLabel(exam.category) }}
                  </span>
                  <span
                    [class]="'px-2 py-1 text-xs font-medium rounded ' + getStatusClass(exam.status)"
                  >
                    {{ exam.status }}
                  </span>
                </div>

                <h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-2">
                  {{ exam.title }}
                </h3>
                <p class="text-gray-600 dark:text-gray-400 text-sm mb-4 line-clamp-2">
                  {{ exam.description }}
                </p>

                <div class="grid grid-cols-3 gap-4 text-center border-t border-gray-200 dark:border-gray-700 pt-4 mb-4">
                  <div>
                    <p class="text-lg font-bold text-gray-900 dark:text-white">{{ exam.question_count }}</p>
                    <p class="text-xs text-gray-500">Questions</p>
                  </div>
                  <div>
                    <p class="text-lg font-bold text-gray-900 dark:text-white">{{ exam.time_limit_minutes }}</p>
                    <p class="text-xs text-gray-500">Minutes</p>
                  </div>
                  <div>
                    <p class="text-lg font-bold text-gray-900 dark:text-white">{{ exam.passing_score }}%</p>
                    <p class="text-xs text-gray-500">To Pass</p>
                  </div>
                </div>

                @if (exam.best_score !== undefined) {
                  <div class="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-3 mb-4">
                    <div class="flex justify-between text-sm">
                      <span class="text-gray-600 dark:text-gray-400">Best Score</span>
                      <span
                        [class]="exam.best_score >= exam.passing_score ? 'text-green-600 font-bold' : 'text-red-600 font-bold'"
                      >
                        {{ exam.best_score }}%
                      </span>
                    </div>
                    <div class="flex justify-between text-sm mt-1">
                      <span class="text-gray-600 dark:text-gray-400">Attempts</span>
                      <span class="text-gray-900 dark:text-white">
                        {{ exam.user_attempts }}/{{ exam.attempts_allowed }}
                      </span>
                    </div>
                  </div>
                }
              </div>

              <div class="px-6 py-4 bg-gray-50 dark:bg-gray-700/50 border-t border-gray-200 dark:border-gray-700">
                @if (exam.status === 'passed') {
                  <a
                    [routerLink]="['/training/exams', exam.id, 'results']"
                    class="block w-full text-center py-2 text-green-600 font-medium"
                  >
                    View Results
                  </a>
                } @else if (exam.status === 'in_progress') {
                  <a
                    [routerLink]="['/training/exams', exam.id]"
                    class="block w-full text-center py-2 bg-yellow-600 text-white rounded-lg hover:bg-yellow-700"
                  >
                    Continue Exam
                  </a>
                } @else if (exam.user_attempts && exam.user_attempts >= exam.attempts_allowed) {
                  <button disabled class="w-full py-2 bg-gray-400 text-white rounded-lg cursor-not-allowed">
                    No Attempts Left
                  </button>
                } @else {
                  <a
                    [routerLink]="['/training/exams', exam.id]"
                    class="block w-full text-center py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
                  >
                    Start Exam
                  </a>
                }
              </div>
            </div>
          } @empty {
            <div class="col-span-3 text-center py-12 text-gray-500">
              No exams found for the selected category
            </div>
          }
        </div>
      }
    </div>
  `,
})
export class ExamListComponent implements OnInit {
  private http = inject(HttpClient);

  exams = signal<Exam[]>([]);
  loading = signal(true);
  selectedCategory = signal<string>('all');

  categories = [
    { value: 'all', label: 'All' },
    { value: 'air_law', label: 'Air Law' },
    { value: 'navigation', label: 'Navigation' },
    { value: 'meteorology', label: 'Meteorology' },
    { value: 'aircraft_knowledge', label: 'Aircraft' },
    { value: 'human_performance', label: 'Human Perf.' },
    { value: 'operational_procedures', label: 'Operations' },
  ];

  filteredExams = () => {
    const category = this.selectedCategory();
    if (category === 'all') return this.exams();
    return this.exams().filter((e) => e.category === category);
  };

  ngOnInit() {
    this.loadExams();
  }

  loadExams() {
    this.loading.set(true);
    this.http.get<{ results: Exam[] }>('/api/v1/theory/exams/').subscribe({
      next: (response) => {
        this.exams.set(response.results || []);
        this.loading.set(false);
      },
      error: () => {
        // Mock data
        this.exams.set([
          {
            id: '1',
            title: 'Air Law Fundamentals',
            description: 'Basic aviation law, regulations, and procedures including airspace classification and ATC.',
            category: 'air_law',
            license_type: 'PPL',
            question_count: 40,
            time_limit_minutes: 60,
            passing_score: 75,
            attempts_allowed: 3,
            user_attempts: 1,
            best_score: 82,
            status: 'passed',
          },
          {
            id: '2',
            title: 'VFR Navigation',
            description: 'Visual navigation techniques, chart reading, and dead reckoning calculations.',
            category: 'navigation',
            license_type: 'PPL',
            question_count: 50,
            time_limit_minutes: 90,
            passing_score: 75,
            attempts_allowed: 3,
            user_attempts: 0,
            status: 'available',
          },
          {
            id: '3',
            title: 'Aviation Meteorology',
            description: 'Weather theory, METAR/TAF interpretation, and weather hazards.',
            category: 'meteorology',
            license_type: 'PPL',
            question_count: 45,
            time_limit_minutes: 75,
            passing_score: 75,
            attempts_allowed: 3,
            status: 'available',
          },
          {
            id: '4',
            title: 'Aircraft General Knowledge',
            description: 'Aircraft systems, performance, and limitations.',
            category: 'aircraft_knowledge',
            license_type: 'PPL',
            question_count: 35,
            time_limit_minutes: 60,
            passing_score: 75,
            attempts_allowed: 3,
            user_attempts: 2,
            best_score: 68,
            status: 'failed',
          },
        ]);
        this.loading.set(false);
      },
    });
  }

  filterByCategory(category: string) {
    this.selectedCategory.set(category);
  }

  getCategoryLabel(category: string): string {
    const cat = this.categories.find((c) => c.value === category);
    return cat?.label || category;
  }

  getCategoryClass(category: string): string {
    const classes: Record<string, string> = {
      air_law: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
      navigation: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
      meteorology: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200',
      aircraft_knowledge: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
      human_performance: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
      operational_procedures: 'bg-indigo-100 text-indigo-800 dark:bg-indigo-900 dark:text-indigo-200',
    };
    return classes[category] || 'bg-gray-100 text-gray-800';
  }

  getStatusClass(status: string): string {
    const classes: Record<string, string> = {
      available: 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300',
      in_progress: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
      passed: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
      failed: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
    };
    return classes[status] || 'bg-gray-100 text-gray-800';
  }
}
