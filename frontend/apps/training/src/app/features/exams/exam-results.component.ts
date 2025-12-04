import { Component, inject, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { HttpClient } from '@angular/common/http';

interface ExamResult {
  id: string;
  exam: {
    id: string;
    title: string;
    passing_score: number;
  };
  score: number;
  passed: boolean;
  correct_answers: number;
  total_questions: number;
  time_taken_seconds: number;
  completed_at: string;
  category_scores: {
    category: string;
    score: number;
    correct: number;
    total: number;
  }[];
}

@Component({
  selector: 'fts-exam-results',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
    <div class="p-6 max-w-4xl mx-auto">
      <a
        routerLink="/training/exams"
        class="inline-flex items-center text-gray-600 dark:text-gray-400 hover:text-primary-600 mb-6"
      >
        <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
        </svg>
        Back to Exams
      </a>

      @if (loading()) {
        <div class="animate-pulse space-y-6">
          <div class="h-48 bg-gray-200 dark:bg-gray-700 rounded-lg"></div>
          <div class="h-32 bg-gray-200 dark:bg-gray-700 rounded-lg"></div>
        </div>
      } @else if (result()) {
        <!-- Result header -->
        <div
          [class]="'rounded-lg p-8 text-center mb-6 ' +
            (result()!.passed
              ? 'bg-green-50 dark:bg-green-900/20 border-2 border-green-200 dark:border-green-800'
              : 'bg-red-50 dark:bg-red-900/20 border-2 border-red-200 dark:border-red-800')"
        >
          @if (result()!.passed) {
            <div class="inline-flex items-center justify-center w-20 h-20 bg-green-100 dark:bg-green-900 rounded-full mb-4">
              <svg class="w-10 h-10 text-green-600 dark:text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <h1 class="text-3xl font-bold text-green-800 dark:text-green-200 mb-2">Congratulations!</h1>
            <p class="text-green-700 dark:text-green-300">You passed the exam</p>
          } @else {
            <div class="inline-flex items-center justify-center w-20 h-20 bg-red-100 dark:bg-red-900 rounded-full mb-4">
              <svg class="w-10 h-10 text-red-600 dark:text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </div>
            <h1 class="text-3xl font-bold text-red-800 dark:text-red-200 mb-2">Not Passed</h1>
            <p class="text-red-700 dark:text-red-300">Keep studying and try again</p>
          }

          <div class="mt-6">
            <p class="text-6xl font-bold" [class]="result()!.passed ? 'text-green-600' : 'text-red-600'">
              {{ result()!.score }}%
            </p>
            <p class="text-gray-600 dark:text-gray-400 mt-2">
              Passing score: {{ result()!.exam.passing_score }}%
            </p>
          </div>
        </div>

        <!-- Stats -->
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          <div class="bg-white dark:bg-gray-800 rounded-lg p-6 text-center shadow-sm">
            <p class="text-3xl font-bold text-gray-900 dark:text-white">
              {{ result()!.correct_answers }}/{{ result()!.total_questions }}
            </p>
            <p class="text-gray-500">Correct Answers</p>
          </div>
          <div class="bg-white dark:bg-gray-800 rounded-lg p-6 text-center shadow-sm">
            <p class="text-3xl font-bold text-gray-900 dark:text-white">
              {{ formatTime(result()!.time_taken_seconds) }}
            </p>
            <p class="text-gray-500">Time Taken</p>
          </div>
          <div class="bg-white dark:bg-gray-800 rounded-lg p-6 text-center shadow-sm">
            <p class="text-3xl font-bold text-gray-900 dark:text-white">
              {{ result()!.completed_at | date:'shortDate' }}
            </p>
            <p class="text-gray-500">Completed</p>
          </div>
        </div>

        <!-- Category breakdown -->
        <div class="bg-white dark:bg-gray-800 rounded-lg shadow-sm overflow-hidden">
          <div class="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
            <h3 class="text-lg font-semibold text-gray-900 dark:text-white">Score by Category</h3>
          </div>
          <div class="p-6 space-y-4">
            @for (cat of result()!.category_scores; track cat.category) {
              <div>
                <div class="flex justify-between text-sm mb-1">
                  <span class="text-gray-700 dark:text-gray-300">{{ cat.category }}</span>
                  <span class="font-medium" [class]="cat.score >= result()!.exam.passing_score ? 'text-green-600' : 'text-red-600'">
                    {{ cat.score }}% ({{ cat.correct }}/{{ cat.total }})
                  </span>
                </div>
                <div class="h-3 bg-gray-200 dark:bg-gray-600 rounded-full overflow-hidden">
                  <div
                    [class]="'h-full rounded-full ' + (cat.score >= result()!.exam.passing_score ? 'bg-green-500' : 'bg-red-500')"
                    [style.width.%]="cat.score"
                  ></div>
                </div>
              </div>
            }
          </div>
        </div>

        <!-- Actions -->
        <div class="flex justify-center gap-4 mt-6">
          <a
            routerLink="/training/exams"
            class="px-6 py-3 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg font-medium hover:bg-gray-200 dark:hover:bg-gray-600"
          >
            Back to Exams
          </a>
          @if (!result()!.passed) {
            <a
              [routerLink]="['/training/exams', result()!.exam.id]"
              class="px-6 py-3 bg-primary-600 text-white rounded-lg font-medium hover:bg-primary-700"
            >
              Try Again
            </a>
          }
        </div>
      }
    </div>
  `,
})
export class ExamResultsComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private http = inject(HttpClient);

  result = signal<ExamResult | null>(null);
  loading = signal(true);

  ngOnInit() {
    const examId = this.route.snapshot.paramMap.get('id');
    if (examId) {
      this.loadResults(examId);
    }
  }

  loadResults(examId: string) {
    this.loading.set(true);
    this.http.get<ExamResult>(`/api/v1/theory/exams/${examId}/results/`).subscribe({
      next: (result) => {
        this.result.set(result);
        this.loading.set(false);
      },
      error: () => {
        // Mock data
        this.result.set({
          id: 'result1',
          exam: {
            id: examId,
            title: 'VFR Navigation',
            passing_score: 75,
          },
          score: 84,
          passed: true,
          correct_answers: 42,
          total_questions: 50,
          time_taken_seconds: 4320,
          completed_at: '2024-12-04T10:30:00Z',
          category_scores: [
            { category: 'Chart Reading', score: 90, correct: 9, total: 10 },
            { category: 'Dead Reckoning', score: 80, correct: 8, total: 10 },
            { category: 'VOR Navigation', score: 85, correct: 17, total: 20 },
            { category: 'Flight Planning', score: 80, correct: 8, total: 10 },
          ],
        });
        this.loading.set(false);
      },
    });
  }

  formatTime(seconds: number): string {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    if (hours > 0) {
      return `${hours}h ${minutes}m`;
    }
    return `${minutes}m`;
  }
}
