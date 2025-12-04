import { Component, inject, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { HttpClient } from '@angular/common/http';

interface Lesson {
  id: string;
  sequence: number;
  name: string;
  type: 'ground' | 'flight' | 'sim';
  duration_minutes: number;
  objectives: string[];
  completed?: boolean;
}

interface Stage {
  id: string;
  name: string;
  sequence: number;
  lessons: Lesson[];
}

interface SyllabusDetail {
  id: string;
  name: string;
  description: string;
  license_type: string;
  stages: Stage[];
  prerequisites: string[];
  total_lessons: number;
  total_flight_hours: number;
  total_ground_hours: number;
}

@Component({
  selector: 'fts-syllabus-detail',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
    <div class="p-6">
      <!-- Back navigation -->
      <a
        routerLink="/training/syllabus"
        class="inline-flex items-center text-gray-600 dark:text-gray-400 hover:text-primary-600 mb-6"
      >
        <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
        </svg>
        Back to Syllabi
      </a>

      @if (loading()) {
        <div class="animate-pulse">
          <div class="h-8 bg-gray-200 dark:bg-gray-700 rounded w-1/3 mb-4"></div>
          <div class="h-4 bg-gray-200 dark:bg-gray-700 rounded w-2/3 mb-8"></div>
          <div class="space-y-4">
            @for (i of [1,2,3]; track i) {
              <div class="h-24 bg-gray-200 dark:bg-gray-700 rounded"></div>
            }
          </div>
        </div>
      } @else if (syllabus()) {
        <!-- Header -->
        <div class="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-sm mb-6">
          <div class="flex justify-between items-start">
            <div>
              <h1 class="text-2xl font-bold text-gray-900 dark:text-white mb-2">
                {{ syllabus()!.name }}
              </h1>
              <p class="text-gray-600 dark:text-gray-400 mb-4">
                {{ syllabus()!.description }}
              </p>
              <div class="flex gap-4">
                <span class="px-3 py-1 bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200 rounded-full text-sm">
                  {{ syllabus()!.license_type }}
                </span>
              </div>
            </div>
            <div class="text-right">
              <div class="grid grid-cols-3 gap-6">
                <div class="text-center">
                  <p class="text-3xl font-bold text-primary-600">{{ syllabus()!.total_lessons }}</p>
                  <p class="text-sm text-gray-500">Lessons</p>
                </div>
                <div class="text-center">
                  <p class="text-3xl font-bold text-blue-600">{{ syllabus()!.total_flight_hours }}</p>
                  <p class="text-sm text-gray-500">Flight Hours</p>
                </div>
                <div class="text-center">
                  <p class="text-3xl font-bold text-green-600">{{ syllabus()!.total_ground_hours }}</p>
                  <p class="text-sm text-gray-500">Ground Hours</p>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Prerequisites -->
        @if (syllabus()!.prerequisites?.length) {
          <div class="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4 mb-6">
            <h3 class="font-semibold text-yellow-800 dark:text-yellow-200 mb-2">Prerequisites</h3>
            <ul class="list-disc list-inside text-yellow-700 dark:text-yellow-300 text-sm">
              @for (prereq of syllabus()!.prerequisites; track prereq) {
                <li>{{ prereq }}</li>
              }
            </ul>
          </div>
        }

        <!-- Stages -->
        <div class="space-y-6">
          @for (stage of syllabus()!.stages; track stage.id) {
            <div class="bg-white dark:bg-gray-800 rounded-lg shadow-sm overflow-hidden">
              <button
                (click)="toggleStage(stage.id)"
                class="w-full px-6 py-4 flex justify-between items-center hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
              >
                <div class="flex items-center gap-4">
                  <span class="w-8 h-8 bg-primary-100 dark:bg-primary-900 text-primary-600 dark:text-primary-400 rounded-full flex items-center justify-center font-bold">
                    {{ stage.sequence }}
                  </span>
                  <div class="text-left">
                    <h3 class="font-semibold text-gray-900 dark:text-white">{{ stage.name }}</h3>
                    <p class="text-sm text-gray-500">{{ stage.lessons.length }} lessons</p>
                  </div>
                </div>
                <svg
                  class="w-5 h-5 text-gray-400 transition-transform"
                  [class.rotate-180]="expandedStages().has(stage.id)"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
                </svg>
              </button>

              @if (expandedStages().has(stage.id)) {
                <div class="border-t border-gray-200 dark:border-gray-700">
                  @for (lesson of stage.lessons; track lesson.id) {
                    <div
                      class="px-6 py-4 flex items-center justify-between border-b border-gray-100 dark:border-gray-700 last:border-0 hover:bg-gray-50 dark:hover:bg-gray-700/50"
                    >
                      <div class="flex items-center gap-4">
                        <span class="w-6 h-6 text-gray-400 text-sm flex items-center justify-center">
                          {{ lesson.sequence }}
                        </span>
                        <div
                          [class]="'w-2 h-2 rounded-full ' + getLessonTypeColor(lesson.type)"
                        ></div>
                        <div>
                          <p class="font-medium text-gray-900 dark:text-white">{{ lesson.name }}</p>
                          <div class="flex items-center gap-2 text-sm text-gray-500">
                            <span class="capitalize">{{ lesson.type }}</span>
                            <span>&bull;</span>
                            <span>{{ lesson.duration_minutes }} min</span>
                          </div>
                        </div>
                      </div>
                      <button class="text-primary-600 hover:text-primary-700 text-sm font-medium">
                        View Details
                      </button>
                    </div>
                  }
                </div>
              }
            </div>
          }
        </div>
      }
    </div>
  `,
})
export class SyllabusDetailComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private http = inject(HttpClient);

  syllabus = signal<SyllabusDetail | null>(null);
  loading = signal(true);
  expandedStages = signal<Set<string>>(new Set());

  ngOnInit() {
    const id = this.route.snapshot.paramMap.get('id');
    if (id) {
      this.loadSyllabus(id);
    }
  }

  loadSyllabus(id: string) {
    this.loading.set(true);
    this.http.get<SyllabusDetail>(`/api/v1/training/syllabi/${id}/`).subscribe({
      next: (syllabus) => {
        this.syllabus.set(syllabus);
        this.loading.set(false);
        // Expand first stage by default
        if (syllabus.stages.length > 0) {
          this.expandedStages.update((s) => new Set([...s, syllabus.stages[0].id]));
        }
      },
      error: () => {
        // Mock data
        this.syllabus.set({
          id: '1',
          name: 'Private Pilot License',
          description: 'Complete PPL training program covering all required ground and flight training per EASA Part-FCL.',
          license_type: 'PPL',
          prerequisites: [
            'Minimum age 16 for solo flight, 17 for license',
            'Class 2 Medical Certificate',
            'English language proficiency',
          ],
          total_lessons: 45,
          total_flight_hours: 45,
          total_ground_hours: 100,
          stages: [
            {
              id: 's1',
              name: 'Pre-Solo Training',
              sequence: 1,
              lessons: [
                { id: 'l1', sequence: 1, name: 'Familiarization Flight', type: 'flight', duration_minutes: 60, objectives: ['Aircraft systems', 'Basic controls'] },
                { id: 'l2', sequence: 2, name: 'Straight and Level Flight', type: 'flight', duration_minutes: 60, objectives: ['Altitude control', 'Heading control'] },
                { id: 'l3', sequence: 3, name: 'Climbs and Descents', type: 'flight', duration_minutes: 60, objectives: ['Power settings', 'Pitch attitudes'] },
                { id: 'l4', sequence: 4, name: 'Turns', type: 'flight', duration_minutes: 60, objectives: ['Shallow turns', 'Medium turns', 'Steep turns'] },
                { id: 'l5', sequence: 5, name: 'Slow Flight', type: 'flight', duration_minutes: 60, objectives: ['Minimum controllable airspeed', 'Stall recognition'] },
              ],
            },
            {
              id: 's2',
              name: 'Solo Phase',
              sequence: 2,
              lessons: [
                { id: 'l6', sequence: 1, name: 'First Solo', type: 'flight', duration_minutes: 60, objectives: ['Pattern work', 'Landings'] },
                { id: 'l7', sequence: 2, name: 'Solo Practice', type: 'flight', duration_minutes: 60, objectives: ['Maneuver practice'] },
                { id: 'l8', sequence: 3, name: 'Solo Cross-Country Prep', type: 'ground', duration_minutes: 120, objectives: ['Navigation planning', 'Weather'] },
              ],
            },
            {
              id: 's3',
              name: 'Cross-Country Phase',
              sequence: 3,
              lessons: [
                { id: 'l9', sequence: 1, name: 'Dual Cross-Country', type: 'flight', duration_minutes: 180, objectives: ['Navigation', 'Radio procedures'] },
                { id: 'l10', sequence: 2, name: 'Solo Cross-Country', type: 'flight', duration_minutes: 180, objectives: ['Solo navigation'] },
              ],
            },
          ],
        });
        this.loading.set(false);
        this.expandedStages.update((s) => new Set([...s, 's1']));
      },
    });
  }

  toggleStage(stageId: string) {
    this.expandedStages.update((stages) => {
      const newSet = new Set(stages);
      if (newSet.has(stageId)) {
        newSet.delete(stageId);
      } else {
        newSet.add(stageId);
      }
      return newSet;
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
}
