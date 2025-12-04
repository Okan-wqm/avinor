import { Component, inject, signal, OnInit, OnDestroy, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { HttpClient } from '@angular/common/http';

interface Answer {
  id: string;
  text: string;
}

interface Question {
  id: string;
  text: string;
  answers: Answer[];
  selected_answer?: string;
}

interface ExamSession {
  id: string;
  exam_id: string;
  title: string;
  questions: Question[];
  time_remaining_seconds: number;
  current_question_index: number;
}

@Component({
  selector: 'fts-exam-take',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
    <div class="min-h-screen bg-gray-100 dark:bg-gray-900">
      @if (loading()) {
        <div class="flex items-center justify-center h-screen">
          <div class="animate-spin rounded-full h-12 w-12 border-4 border-primary-600 border-t-transparent"></div>
        </div>
      } @else if (session()) {
        <!-- Header -->
        <div class="bg-white dark:bg-gray-800 shadow-sm sticky top-0 z-10">
          <div class="max-w-4xl mx-auto px-6 py-4">
            <div class="flex justify-between items-center">
              <div>
                <h1 class="text-lg font-semibold text-gray-900 dark:text-white">{{ session()!.title }}</h1>
                <p class="text-sm text-gray-500">
                  Question {{ currentIndex() + 1 }} of {{ session()!.questions.length }}
                </p>
              </div>
              <div class="flex items-center gap-4">
                <!-- Timer -->
                <div
                  [class]="'flex items-center gap-2 px-4 py-2 rounded-lg ' +
                    (timeRemaining() < 300 ? 'bg-red-100 text-red-800' : 'bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-white')"
                >
                  <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <span class="font-mono font-bold">{{ formatTime(timeRemaining()) }}</span>
                </div>
                <button
                  (click)="submitExam()"
                  class="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
                >
                  Submit Exam
                </button>
              </div>
            </div>

            <!-- Progress bar -->
            <div class="mt-4 h-2 bg-gray-200 dark:bg-gray-600 rounded-full overflow-hidden">
              <div
                class="h-full bg-primary-600 transition-all duration-300"
                [style.width.%]="progressPercentage()"
              ></div>
            </div>
          </div>
        </div>

        <!-- Question navigation -->
        <div class="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
          <div class="max-w-4xl mx-auto px-6 py-3">
            <div class="flex flex-wrap gap-2">
              @for (q of session()!.questions; track q.id; let i = $index) {
                <button
                  (click)="goToQuestion(i)"
                  [class]="'w-8 h-8 rounded-lg text-sm font-medium transition-colors ' +
                    (i === currentIndex()
                      ? 'bg-primary-600 text-white'
                      : q.selected_answer
                        ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
                        : 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600')"
                >
                  {{ i + 1 }}
                </button>
              }
            </div>
          </div>
        </div>

        <!-- Question content -->
        <div class="max-w-4xl mx-auto px-6 py-8">
          <div class="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-8">
            <p class="text-lg text-gray-900 dark:text-white mb-6">
              {{ currentQuestion()?.text }}
            </p>

            <div class="space-y-3">
              @for (answer of currentQuestion()?.answers; track answer.id) {
                <button
                  (click)="selectAnswer(answer.id)"
                  [class]="'w-full p-4 text-left rounded-lg border-2 transition-colors ' +
                    (currentQuestion()?.selected_answer === answer.id
                      ? 'border-primary-600 bg-primary-50 dark:bg-primary-900/20'
                      : 'border-gray-200 dark:border-gray-600 hover:border-primary-300 dark:hover:border-primary-700')"
                >
                  <div class="flex items-center gap-3">
                    <span
                      [class]="'w-6 h-6 rounded-full border-2 flex items-center justify-center text-sm font-medium ' +
                        (currentQuestion()?.selected_answer === answer.id
                          ? 'border-primary-600 bg-primary-600 text-white'
                          : 'border-gray-300 dark:border-gray-500 text-gray-500 dark:text-gray-400')"
                    >
                      {{ getAnswerLetter(answer.id) }}
                    </span>
                    <span class="text-gray-900 dark:text-white">{{ answer.text }}</span>
                  </div>
                </button>
              }
            </div>
          </div>

          <!-- Navigation buttons -->
          <div class="flex justify-between mt-6">
            <button
              (click)="previousQuestion()"
              [disabled]="currentIndex() === 0"
              [class]="'px-6 py-3 rounded-lg font-medium transition-colors ' +
                (currentIndex() === 0
                  ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                  : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600')"
            >
              Previous
            </button>
            @if (currentIndex() < session()!.questions.length - 1) {
              <button
                (click)="nextQuestion()"
                class="px-6 py-3 bg-primary-600 text-white rounded-lg font-medium hover:bg-primary-700"
              >
                Next
              </button>
            } @else {
              <button
                (click)="submitExam()"
                class="px-6 py-3 bg-green-600 text-white rounded-lg font-medium hover:bg-green-700"
              >
                Submit Exam
              </button>
            }
          </div>
        </div>
      }
    </div>
  `,
})
export class ExamTakeComponent implements OnInit, OnDestroy {
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private http = inject(HttpClient);

  session = signal<ExamSession | null>(null);
  loading = signal(true);
  currentIndex = signal(0);
  timeRemaining = signal(0);

  private timerInterval?: ReturnType<typeof setInterval>;

  currentQuestion = computed(() => {
    const s = this.session();
    if (!s) return null;
    return s.questions[this.currentIndex()];
  });

  progressPercentage = computed(() => {
    const s = this.session();
    if (!s) return 0;
    const answered = s.questions.filter((q) => q.selected_answer).length;
    return (answered / s.questions.length) * 100;
  });

  ngOnInit() {
    const examId = this.route.snapshot.paramMap.get('id');
    if (examId) {
      this.startExam(examId);
    }
  }

  ngOnDestroy() {
    if (this.timerInterval) {
      clearInterval(this.timerInterval);
    }
  }

  startExam(examId: string) {
    this.loading.set(true);
    this.http.post<ExamSession>(`/api/v1/theory/exams/${examId}/start/`, {}).subscribe({
      next: (session) => {
        this.session.set(session);
        this.timeRemaining.set(session.time_remaining_seconds);
        this.startTimer();
        this.loading.set(false);
      },
      error: () => {
        // Mock data
        this.session.set({
          id: 'session1',
          exam_id: examId,
          title: 'VFR Navigation',
          time_remaining_seconds: 5400, // 90 minutes
          current_question_index: 0,
          questions: [
            {
              id: 'q1',
              text: 'What is the standard atmospheric pressure at sea level?',
              answers: [
                { id: 'a', text: '1013.25 hPa' },
                { id: 'b', text: '1000 hPa' },
                { id: 'c', text: '1025 hPa' },
                { id: 'd', text: '1050 hPa' },
              ],
            },
            {
              id: 'q2',
              text: 'When flying from a high pressure area to a low pressure area without adjusting the altimeter, the indicated altitude will:',
              answers: [
                { id: 'a', text: 'Be higher than true altitude' },
                { id: 'b', text: 'Be lower than true altitude' },
                { id: 'c', text: 'Remain accurate' },
                { id: 'd', text: 'Fluctuate randomly' },
              ],
            },
            {
              id: 'q3',
              text: 'The isogonic line on an aeronautical chart indicates:',
              answers: [
                { id: 'a', text: 'Lines of equal magnetic variation' },
                { id: 'b', text: 'Lines of equal altitude' },
                { id: 'c', text: 'Lines of equal temperature' },
                { id: 'd', text: 'Lines of equal wind speed' },
              ],
            },
            {
              id: 'q4',
              text: 'Dead reckoning navigation involves:',
              answers: [
                { id: 'a', text: 'Using GPS coordinates exclusively' },
                { id: 'b', text: 'Computing position from heading, airspeed, time, and wind' },
                { id: 'c', text: 'Following visual landmarks only' },
                { id: 'd', text: 'Using VOR radials' },
              ],
            },
            {
              id: 'q5',
              text: 'What does a steady green light from the control tower mean to an aircraft in flight?',
              answers: [
                { id: 'a', text: 'Cleared to land' },
                { id: 'b', text: 'Return for landing' },
                { id: 'c', text: 'Give way and continue circling' },
                { id: 'd', text: 'Airport unsafe, do not land' },
              ],
            },
          ],
        });
        this.timeRemaining.set(5400);
        this.startTimer();
        this.loading.set(false);
      },
    });
  }

  startTimer() {
    this.timerInterval = setInterval(() => {
      const remaining = this.timeRemaining();
      if (remaining <= 0) {
        this.submitExam();
      } else {
        this.timeRemaining.set(remaining - 1);
      }
    }, 1000);
  }

  formatTime(seconds: number): string {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    if (hours > 0) {
      return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }
    return `${minutes}:${secs.toString().padStart(2, '0')}`;
  }

  selectAnswer(answerId: string) {
    const s = this.session();
    if (!s) return;

    const questions = [...s.questions];
    questions[this.currentIndex()] = {
      ...questions[this.currentIndex()],
      selected_answer: answerId,
    };

    this.session.set({ ...s, questions });
  }

  goToQuestion(index: number) {
    this.currentIndex.set(index);
  }

  previousQuestion() {
    if (this.currentIndex() > 0) {
      this.currentIndex.update((i) => i - 1);
    }
  }

  nextQuestion() {
    const s = this.session();
    if (s && this.currentIndex() < s.questions.length - 1) {
      this.currentIndex.update((i) => i + 1);
    }
  }

  getAnswerLetter(answerId: string): string {
    return answerId.toUpperCase();
  }

  submitExam() {
    if (this.timerInterval) {
      clearInterval(this.timerInterval);
    }

    const s = this.session();
    if (!s) return;

    const answers = s.questions.map((q) => ({
      question_id: q.id,
      answer_id: q.selected_answer,
    }));

    this.http.post(`/api/v1/theory/exams/${s.exam_id}/submit/`, { answers }).subscribe({
      next: () => {
        this.router.navigate(['/training/exams', s.exam_id, 'results']);
      },
      error: () => {
        // Navigate anyway for demo
        this.router.navigate(['/training/exams', s.exam_id, 'results']);
      },
    });
  }
}
