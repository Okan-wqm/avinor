import { Component, inject, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { HttpClient } from '@angular/common/http';

interface LessonRecord {
  id: string;
  lesson: {
    id: string;
    name: string;
    type: 'ground' | 'flight' | 'sim';
  };
  date: string;
  duration_minutes: number;
  instructor: {
    id: string;
    name: string;
  };
  grade: 'satisfactory' | 'unsatisfactory' | 'incomplete';
  comments: string;
}

interface StudentDetail {
  id: string;
  name: string;
  email: string;
  phone: string;
  enrolled_date: string;
  syllabus: {
    id: string;
    name: string;
    license_type: string;
  };
  instructor: {
    id: string;
    name: string;
  };
  progress_percentage: number;
  completed_lessons: number;
  total_lessons: number;
  flight_hours: {
    dual: number;
    solo: number;
    pic: number;
    night: number;
    instrument: number;
    total: number;
    required: number;
  };
  ground_hours: {
    logged: number;
    required: number;
  };
  lesson_records: LessonRecord[];
}

@Component({
  selector: 'fts-student-progress',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
    <div class="p-6">
      <!-- Back navigation -->
      <a
        routerLink="/training/progress"
        class="inline-flex items-center text-gray-600 dark:text-gray-400 hover:text-primary-600 mb-6"
      >
        <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
        </svg>
        Back to Progress Dashboard
      </a>

      @if (loading()) {
        <div class="animate-pulse space-y-6">
          <div class="h-32 bg-gray-200 dark:bg-gray-700 rounded-lg"></div>
          <div class="h-48 bg-gray-200 dark:bg-gray-700 rounded-lg"></div>
        </div>
      } @else if (student()) {
        <!-- Student header -->
        <div class="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-sm mb-6">
          <div class="flex justify-between items-start">
            <div class="flex items-center gap-4">
              <div class="h-16 w-16 rounded-full bg-primary-100 dark:bg-primary-900 flex items-center justify-center">
                <span class="text-2xl text-primary-600 dark:text-primary-400 font-bold">
                  {{ student()!.name.charAt(0) }}
                </span>
              </div>
              <div>
                <h1 class="text-2xl font-bold text-gray-900 dark:text-white">{{ student()!.name }}</h1>
                <p class="text-gray-600 dark:text-gray-400">{{ student()!.email }}</p>
                <p class="text-sm text-gray-500">Enrolled: {{ student()!.enrolled_date | date:'mediumDate' }}</p>
              </div>
            </div>
            <div class="text-right">
              <p class="text-sm text-gray-500">Training Program</p>
              <p class="font-semibold text-gray-900 dark:text-white">{{ student()!.syllabus.name }}</p>
              <span class="text-xs px-2 py-1 bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200 rounded">
                {{ student()!.syllabus.license_type }}
              </span>
            </div>
          </div>

          <!-- Progress bar -->
          <div class="mt-6">
            <div class="flex justify-between items-center mb-2">
              <span class="text-sm font-medium text-gray-700 dark:text-gray-300">Overall Progress</span>
              <span class="text-sm font-bold text-primary-600">{{ student()!.progress_percentage }}%</span>
            </div>
            <div class="h-3 bg-gray-200 dark:bg-gray-600 rounded-full overflow-hidden">
              <div
                class="h-full bg-primary-600 rounded-full transition-all duration-500"
                [style.width.%]="student()!.progress_percentage"
              ></div>
            </div>
            <p class="text-sm text-gray-500 mt-1">
              {{ student()!.completed_lessons }} of {{ student()!.total_lessons }} lessons completed
            </p>
          </div>
        </div>

        <!-- Flight hours breakdown -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
          <div class="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-sm">
            <h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-4">Flight Hours</h3>
            <div class="space-y-4">
              <div>
                <div class="flex justify-between text-sm mb-1">
                  <span class="text-gray-600 dark:text-gray-400">Total Flight Time</span>
                  <span class="font-medium text-gray-900 dark:text-white">
                    {{ student()!.flight_hours.total }} / {{ student()!.flight_hours.required }} hrs
                  </span>
                </div>
                <div class="h-2 bg-gray-200 dark:bg-gray-600 rounded-full">
                  <div
                    class="h-full bg-blue-600 rounded-full"
                    [style.width.%]="(student()!.flight_hours.total / student()!.flight_hours.required) * 100"
                  ></div>
                </div>
              </div>

              <div class="grid grid-cols-2 gap-4 pt-4 border-t border-gray-200 dark:border-gray-700">
                <div>
                  <p class="text-2xl font-bold text-gray-900 dark:text-white">{{ student()!.flight_hours.dual }}</p>
                  <p class="text-sm text-gray-500">Dual</p>
                </div>
                <div>
                  <p class="text-2xl font-bold text-gray-900 dark:text-white">{{ student()!.flight_hours.solo }}</p>
                  <p class="text-sm text-gray-500">Solo</p>
                </div>
                <div>
                  <p class="text-2xl font-bold text-gray-900 dark:text-white">{{ student()!.flight_hours.pic }}</p>
                  <p class="text-sm text-gray-500">PIC</p>
                </div>
                <div>
                  <p class="text-2xl font-bold text-gray-900 dark:text-white">{{ student()!.flight_hours.night }}</p>
                  <p class="text-sm text-gray-500">Night</p>
                </div>
              </div>
            </div>
          </div>

          <div class="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-sm">
            <h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-4">Ground Training</h3>
            <div class="space-y-4">
              <div>
                <div class="flex justify-between text-sm mb-1">
                  <span class="text-gray-600 dark:text-gray-400">Ground Hours</span>
                  <span class="font-medium text-gray-900 dark:text-white">
                    {{ student()!.ground_hours.logged }} / {{ student()!.ground_hours.required }} hrs
                  </span>
                </div>
                <div class="h-2 bg-gray-200 dark:bg-gray-600 rounded-full">
                  <div
                    class="h-full bg-green-600 rounded-full"
                    [style.width.%]="(student()!.ground_hours.logged / student()!.ground_hours.required) * 100"
                  ></div>
                </div>
              </div>

              <div class="pt-4 border-t border-gray-200 dark:border-gray-700">
                <p class="text-sm text-gray-600 dark:text-gray-400 mb-2">Assigned Instructor</p>
                <div class="flex items-center gap-3">
                  <div class="h-10 w-10 rounded-full bg-gray-100 dark:bg-gray-700 flex items-center justify-center">
                    <span class="text-gray-600 dark:text-gray-400 font-medium">
                      {{ student()!.instructor.name.charAt(0) }}
                    </span>
                  </div>
                  <p class="font-medium text-gray-900 dark:text-white">{{ student()!.instructor.name }}</p>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Recent lessons -->
        <div class="bg-white dark:bg-gray-800 rounded-lg shadow-sm overflow-hidden">
          <div class="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
            <h3 class="text-lg font-semibold text-gray-900 dark:text-white">Lesson History</h3>
          </div>
          <div class="divide-y divide-gray-200 dark:divide-gray-700">
            @for (record of student()!.lesson_records; track record.id) {
              <div class="px-6 py-4 hover:bg-gray-50 dark:hover:bg-gray-700/50">
                <div class="flex justify-between items-start">
                  <div class="flex items-start gap-4">
                    <div
                      [class]="'w-3 h-3 rounded-full mt-1.5 ' + getLessonTypeColor(record.lesson.type)"
                    ></div>
                    <div>
                      <p class="font-medium text-gray-900 dark:text-white">{{ record.lesson.name }}</p>
                      <p class="text-sm text-gray-500">
                        {{ record.date | date:'mediumDate' }} &bull; {{ record.duration_minutes }} min &bull; {{ record.instructor.name }}
                      </p>
                      @if (record.comments) {
                        <p class="text-sm text-gray-600 dark:text-gray-400 mt-1">{{ record.comments }}</p>
                      }
                    </div>
                  </div>
                  <span
                    [class]="'px-2 py-1 text-xs font-medium rounded ' + getGradeClass(record.grade)"
                  >
                    {{ record.grade }}
                  </span>
                </div>
              </div>
            } @empty {
              <div class="px-6 py-12 text-center text-gray-500">
                No lesson records yet
              </div>
            }
          </div>
        </div>
      }
    </div>
  `,
})
export class StudentProgressComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private http = inject(HttpClient);

  student = signal<StudentDetail | null>(null);
  loading = signal(true);

  ngOnInit() {
    const studentId = this.route.snapshot.paramMap.get('studentId');
    if (studentId) {
      this.loadStudent(studentId);
    }
  }

  loadStudent(id: string) {
    this.loading.set(true);
    this.http.get<StudentDetail>(`/api/v1/training/progress/${id}/`).subscribe({
      next: (student) => {
        this.student.set(student);
        this.loading.set(false);
      },
      error: () => {
        // Mock data
        this.student.set({
          id: '1',
          name: 'John Pilot',
          email: 'john@example.com',
          phone: '+1 555-0123',
          enrolled_date: '2024-06-15',
          syllabus: { id: 'sy1', name: 'Private Pilot License', license_type: 'PPL' },
          instructor: { id: 'i1', name: 'Capt. Smith' },
          progress_percentage: 65,
          completed_lessons: 29,
          total_lessons: 45,
          flight_hours: {
            dual: 22,
            solo: 10,
            pic: 8,
            night: 3,
            instrument: 5,
            total: 32,
            required: 45,
          },
          ground_hours: {
            logged: 75,
            required: 100,
          },
          lesson_records: [
            {
              id: 'r1',
              lesson: { id: 'l1', name: 'Cross-Country Navigation', type: 'flight' },
              date: '2024-12-01',
              duration_minutes: 180,
              instructor: { id: 'i1', name: 'Capt. Smith' },
              grade: 'satisfactory',
              comments: 'Good situational awareness. Work on wind correction angles.',
            },
            {
              id: 'r2',
              lesson: { id: 'l2', name: 'Radio Navigation', type: 'ground' },
              date: '2024-11-28',
              duration_minutes: 120,
              instructor: { id: 'i1', name: 'Capt. Smith' },
              grade: 'satisfactory',
              comments: 'Solid understanding of VOR navigation.',
            },
            {
              id: 'r3',
              lesson: { id: 'l3', name: 'Emergency Procedures', type: 'flight' },
              date: '2024-11-25',
              duration_minutes: 90,
              instructor: { id: 'i1', name: 'Capt. Smith' },
              grade: 'satisfactory',
              comments: 'Good decision making during simulated engine failure.',
            },
          ],
        });
        this.loading.set(false);
      },
    });
  }

  getLessonTypeColor(type: string): string {
    const colors: Record<string, string> = {
      ground: 'bg-green-500',
      flight: 'bg-blue-500',
      sim: 'bg-purple-500',
    };
    return colors[type] || 'bg-gray-500';
  }

  getGradeClass(grade: string): string {
    const classes: Record<string, string> = {
      satisfactory: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
      unsatisfactory: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
      incomplete: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
    };
    return classes[grade] || 'bg-gray-100 text-gray-800';
  }
}
