import { Component, inject, signal, OnInit, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';

interface Lesson {
  id: string;
  title: string;
  duration_minutes: number;
  content_type: 'video' | 'text' | 'quiz';
  completed: boolean;
  order: number;
}

interface Module {
  id: string;
  title: string;
  lessons: Lesson[];
}

interface CourseDetail {
  id: string;
  title: string;
  description: string;
  modules: Module[];
  current_lesson_id?: string;
}

interface LessonContent {
  id: string;
  title: string;
  content_type: 'video' | 'text' | 'quiz';
  content: string;
  video_url?: string;
}

@Component({
  selector: 'fts-course-player',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
    <div class="flex h-screen bg-gray-100 dark:bg-gray-900">
      <!-- Sidebar -->
      <div class="w-80 bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 flex flex-col">
        <div class="p-4 border-b border-gray-200 dark:border-gray-700">
          <a
            routerLink="/training/courses"
            class="inline-flex items-center text-gray-600 dark:text-gray-400 hover:text-primary-600 text-sm mb-2"
          >
            <svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
            </svg>
            Back to Courses
          </a>
          <h2 class="text-lg font-semibold text-gray-900 dark:text-white">{{ course()?.title }}</h2>
          <div class="mt-2">
            <div class="flex justify-between text-xs mb-1">
              <span class="text-gray-500">Progress</span>
              <span class="font-medium text-gray-900 dark:text-white">{{ progressPercentage() }}%</span>
            </div>
            <div class="h-1.5 bg-gray-200 dark:bg-gray-600 rounded-full overflow-hidden">
              <div
                class="h-full bg-primary-600 rounded-full transition-all"
                [style.width.%]="progressPercentage()"
              ></div>
            </div>
          </div>
        </div>

        <div class="flex-1 overflow-y-auto">
          @for (module of course()?.modules; track module.id) {
            <div class="border-b border-gray-200 dark:border-gray-700">
              <button
                (click)="toggleModule(module.id)"
                class="w-full px-4 py-3 flex justify-between items-center hover:bg-gray-50 dark:hover:bg-gray-700"
              >
                <span class="font-medium text-gray-900 dark:text-white text-sm text-left">{{ module.title }}</span>
                <svg
                  class="w-4 h-4 text-gray-400 transition-transform"
                  [class.rotate-180]="expandedModules().has(module.id)"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
                </svg>
              </button>

              @if (expandedModules().has(module.id)) {
                <div class="bg-gray-50 dark:bg-gray-700/50">
                  @for (lesson of module.lessons; track lesson.id) {
                    <button
                      (click)="selectLesson(lesson)"
                      [class]="'w-full px-4 py-2 flex items-center gap-3 text-left text-sm transition-colors ' +
                        (currentLesson()?.id === lesson.id
                          ? 'bg-primary-50 dark:bg-primary-900/20 text-primary-700 dark:text-primary-300'
                          : 'hover:bg-gray-100 dark:hover:bg-gray-600')"
                    >
                      @if (lesson.completed) {
                        <svg class="w-5 h-5 text-green-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                      } @else {
                        <div class="w-5 h-5 rounded-full border-2 border-gray-300 dark:border-gray-500 flex-shrink-0"></div>
                      }
                      <div class="flex-1 min-w-0">
                        <p class="truncate" [class]="lesson.completed ? 'text-gray-500' : 'text-gray-900 dark:text-white'">
                          {{ lesson.title }}
                        </p>
                        <p class="text-xs text-gray-400">{{ lesson.duration_minutes }} min</p>
                      </div>
                    </button>
                  }
                </div>
              }
            </div>
          }
        </div>
      </div>

      <!-- Content area -->
      <div class="flex-1 flex flex-col">
        @if (currentLesson()) {
          <div class="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 px-6 py-4">
            <h1 class="text-xl font-semibold text-gray-900 dark:text-white">{{ currentLesson()!.title }}</h1>
          </div>

          <div class="flex-1 overflow-y-auto p-6">
            @if (lessonContent()) {
              @if (lessonContent()!.content_type === 'video') {
                <div class="aspect-video bg-black rounded-lg mb-6">
                  <div class="w-full h-full flex items-center justify-center text-white">
                    <svg class="w-16 h-16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  </div>
                </div>
              }

              <div
                class="prose dark:prose-invert max-w-none"
                [innerHTML]="sanitizedContent()"
              ></div>
            }
          </div>

          <div class="bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700 px-6 py-4 flex justify-between">
            <button
              (click)="previousLesson()"
              [disabled]="!hasPreviousLesson()"
              [class]="'px-4 py-2 rounded-lg font-medium transition-colors ' +
                (hasPreviousLesson()
                  ? 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
                  : 'bg-gray-100 text-gray-400 cursor-not-allowed')"
            >
              Previous
            </button>

            <button
              (click)="markComplete()"
              [class]="'px-4 py-2 rounded-lg font-medium transition-colors ' +
                (currentLesson()!.completed
                  ? 'bg-green-100 text-green-700'
                  : 'bg-primary-600 text-white hover:bg-primary-700')"
            >
              {{ currentLesson()!.completed ? 'Completed' : 'Mark Complete' }}
            </button>

            <button
              (click)="nextLesson()"
              [disabled]="!hasNextLesson()"
              [class]="'px-4 py-2 rounded-lg font-medium transition-colors ' +
                (hasNextLesson()
                  ? 'bg-primary-600 text-white hover:bg-primary-700'
                  : 'bg-gray-100 text-gray-400 cursor-not-allowed')"
            >
              Next
            </button>
          </div>
        } @else {
          <div class="flex-1 flex items-center justify-center text-gray-500">
            Select a lesson to begin
          </div>
        }
      </div>
    </div>
  `,
})
export class CoursePlayerComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private http = inject(HttpClient);
  private sanitizer = inject(DomSanitizer);

  course = signal<CourseDetail | null>(null);
  currentLesson = signal<Lesson | null>(null);
  lessonContent = signal<LessonContent | null>(null);
  expandedModules = signal<Set<string>>(new Set());

  progressPercentage = computed(() => {
    const c = this.course();
    if (!c) return 0;
    const allLessons = c.modules.flatMap((m) => m.lessons);
    const completed = allLessons.filter((l) => l.completed).length;
    return Math.round((completed / allLessons.length) * 100);
  });

  sanitizedContent = computed((): SafeHtml => {
    const content = this.lessonContent();
    if (!content) return '';
    return this.sanitizer.bypassSecurityTrustHtml(content.content);
  });

  ngOnInit() {
    const courseId = this.route.snapshot.paramMap.get('id');
    if (courseId) {
      this.loadCourse(courseId);
    }
  }

  loadCourse(id: string) {
    this.http.get<CourseDetail>(`/api/v1/theory/courses/${id}/`).subscribe({
      next: (course) => {
        this.course.set(course);
        this.initializeCourse(course);
      },
      error: () => {
        // Mock data
        const mockCourse: CourseDetail = {
          id: '1',
          title: 'Aviation Weather',
          description: 'Learn to interpret weather reports and forecasts.',
          modules: [
            {
              id: 'm1',
              title: 'Introduction to Meteorology',
              lessons: [
                { id: 'l1', title: 'The Atmosphere', duration_minutes: 15, content_type: 'text', completed: true, order: 1 },
                { id: 'l2', title: 'Pressure and Altimetry', duration_minutes: 20, content_type: 'video', completed: true, order: 2 },
                { id: 'l3', title: 'Temperature and Density', duration_minutes: 15, content_type: 'text', completed: false, order: 3 },
              ],
            },
            {
              id: 'm2',
              title: 'Weather Reports',
              lessons: [
                { id: 'l4', title: 'METAR Decoding', duration_minutes: 25, content_type: 'video', completed: false, order: 1 },
                { id: 'l5', title: 'TAF Interpretation', duration_minutes: 25, content_type: 'video', completed: false, order: 2 },
                { id: 'l6', title: 'Weather Report Quiz', duration_minutes: 15, content_type: 'quiz', completed: false, order: 3 },
              ],
            },
            {
              id: 'm3',
              title: 'Weather Hazards',
              lessons: [
                { id: 'l7', title: 'Thunderstorms', duration_minutes: 20, content_type: 'video', completed: false, order: 1 },
                { id: 'l8', title: 'Icing Conditions', duration_minutes: 20, content_type: 'video', completed: false, order: 2 },
                { id: 'l9', title: 'Turbulence', duration_minutes: 15, content_type: 'text', completed: false, order: 3 },
                { id: 'l10', title: 'Visibility Hazards', duration_minutes: 15, content_type: 'text', completed: false, order: 4 },
              ],
            },
          ],
          current_lesson_id: 'l3',
        };
        this.course.set(mockCourse);
        this.initializeCourse(mockCourse);
      },
    });
  }

  initializeCourse(course: CourseDetail) {
    // Expand first module and select current lesson
    if (course.modules.length > 0) {
      this.expandedModules.set(new Set([course.modules[0].id]));
    }

    if (course.current_lesson_id) {
      for (const module of course.modules) {
        const lesson = module.lessons.find((l) => l.id === course.current_lesson_id);
        if (lesson) {
          this.expandedModules.update((s) => new Set([...s, module.id]));
          this.selectLesson(lesson);
          break;
        }
      }
    } else if (course.modules[0]?.lessons[0]) {
      this.selectLesson(course.modules[0].lessons[0]);
    }
  }

  toggleModule(moduleId: string) {
    this.expandedModules.update((modules) => {
      const newSet = new Set(modules);
      if (newSet.has(moduleId)) {
        newSet.delete(moduleId);
      } else {
        newSet.add(moduleId);
      }
      return newSet;
    });
  }

  selectLesson(lesson: Lesson) {
    this.currentLesson.set(lesson);
    this.loadLessonContent(lesson.id);
  }

  loadLessonContent(lessonId: string) {
    this.http.get<LessonContent>(`/api/v1/theory/lessons/${lessonId}/`).subscribe({
      next: (content) => {
        this.lessonContent.set(content);
      },
      error: () => {
        // Mock content
        this.lessonContent.set({
          id: lessonId,
          title: this.currentLesson()?.title || 'Lesson',
          content_type: this.currentLesson()?.content_type || 'text',
          content: `
            <h2>Learning Objectives</h2>
            <ul>
              <li>Understand the key concepts of this topic</li>
              <li>Apply knowledge to real-world aviation scenarios</li>
              <li>Prepare for the knowledge test</li>
            </ul>

            <h2>Introduction</h2>
            <p>This lesson covers important concepts that every pilot must understand. Pay close attention to the details as they will be tested in your knowledge exam.</p>

            <h2>Key Concepts</h2>
            <p>The atmosphere is divided into several layers, each with distinct characteristics that affect flight operations. Understanding these layers is fundamental to aviation weather.</p>

            <h3>The Troposphere</h3>
            <p>The troposphere is the lowest layer of the atmosphere and is where most weather occurs. It extends from the surface to approximately 36,000 feet at the mid-latitudes.</p>

            <h3>Standard Atmosphere</h3>
            <p>The International Standard Atmosphere (ISA) provides a reference for atmospheric conditions:</p>
            <ul>
              <li>Sea level pressure: 1013.25 hPa (29.92 inHg)</li>
              <li>Sea level temperature: 15°C (59°F)</li>
              <li>Temperature lapse rate: 1.98°C per 1,000 feet</li>
            </ul>

            <h2>Summary</h2>
            <p>Understanding atmospheric properties is essential for flight planning and safe operations. Continue to the next lesson to learn more about pressure and altimetry.</p>
          `,
        });
      },
    });
  }

  markComplete() {
    const lesson = this.currentLesson();
    if (!lesson || lesson.completed) return;

    this.http.post(`/api/v1/theory/lessons/${lesson.id}/complete/`, {}).subscribe({
      next: () => {
        this.updateLessonCompletion(lesson.id, true);
      },
      error: () => {
        // Update locally anyway for demo
        this.updateLessonCompletion(lesson.id, true);
      },
    });
  }

  updateLessonCompletion(lessonId: string, completed: boolean) {
    const c = this.course();
    if (!c) return;

    const updatedModules = c.modules.map((m) => ({
      ...m,
      lessons: m.lessons.map((l) => (l.id === lessonId ? { ...l, completed } : l)),
    }));

    this.course.set({ ...c, modules: updatedModules });

    const lesson = this.currentLesson();
    if (lesson?.id === lessonId) {
      this.currentLesson.set({ ...lesson, completed });
    }
  }

  getAllLessons(): Lesson[] {
    const c = this.course();
    if (!c) return [];
    return c.modules.flatMap((m) => m.lessons);
  }

  getCurrentLessonIndex(): number {
    const all = this.getAllLessons();
    const current = this.currentLesson();
    return current ? all.findIndex((l) => l.id === current.id) : -1;
  }

  hasPreviousLesson(): boolean {
    return this.getCurrentLessonIndex() > 0;
  }

  hasNextLesson(): boolean {
    const all = this.getAllLessons();
    return this.getCurrentLessonIndex() < all.length - 1;
  }

  previousLesson() {
    const all = this.getAllLessons();
    const index = this.getCurrentLessonIndex();
    if (index > 0) {
      this.selectLesson(all[index - 1]);
    }
  }

  nextLesson() {
    const all = this.getAllLessons();
    const index = this.getCurrentLessonIndex();
    if (index < all.length - 1) {
      this.selectLesson(all[index + 1]);
    }
  }
}
