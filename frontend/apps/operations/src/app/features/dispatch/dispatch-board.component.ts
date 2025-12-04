import { Component, signal, computed, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../../environments/environment';

interface Booking {
  id: string;
  startTime: string;
  endTime: string;
  status: 'pending' | 'confirmed' | 'in_progress' | 'completed' | 'cancelled';
  bookingType: string;
  aircraft: {
    id: string;
    registration: string;
    type: string;
  };
  pilot: {
    id: string;
    firstName: string;
    lastName: string;
  };
  instructor?: {
    id: string;
    firstName: string;
    lastName: string;
  };
}

@Component({
  selector: 'fts-dispatch-board',
  standalone: true,
  imports: [CommonModule, RouterModule],
  template: `
    <div class="space-y-6">
      <!-- Header -->
      <div class="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
        <div>
          <h1 class="text-2xl font-bold text-gray-900 dark:text-white">
            Dispatch Board
          </h1>
          <p class="text-gray-500 dark:text-gray-400">
            {{ selectedDate() | date : 'EEEE, MMMM d, yyyy' }} -
            <span class="text-primary-600">{{ bookings().length }} bookings</span>
          </p>
        </div>

        <div class="flex items-center gap-3">
          <!-- Date Navigation -->
          <div
            class="flex items-center bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700"
          >
            <button
              (click)="previousDay()"
              class="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-l-lg"
            >
              <svg
                class="w-5 h-5 text-gray-600 dark:text-gray-300"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M15 19l-7-7 7-7"
                />
              </svg>
            </button>
            <button
              (click)="goToToday()"
              class="px-4 py-2 font-medium hover:bg-gray-100 dark:hover:bg-gray-700"
            >
              Today
            </button>
            <button
              (click)="nextDay()"
              class="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-r-lg"
            >
              <svg
                class="w-5 h-5 text-gray-600 dark:text-gray-300"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M9 5l7 7-7 7"
                />
              </svg>
            </button>
          </div>

          <button
            routerLink="/booking/quick"
            class="px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg font-medium transition-colors flex items-center gap-2"
          >
            <svg
              class="w-5 h-5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M12 4v16m8-8H4"
              />
            </svg>
            New Booking
          </button>
        </div>
      </div>

      <!-- Stats -->
      <div class="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div
          class="bg-white dark:bg-gray-800 rounded-xl p-4 border border-gray-200 dark:border-gray-700"
        >
          <div class="flex items-center gap-3">
            <div class="p-2 bg-blue-100 dark:bg-blue-900 rounded-lg">
              <svg
                class="w-5 h-5 text-blue-600 dark:text-blue-400"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"
                />
              </svg>
            </div>
            <div>
              <p class="text-sm text-gray-500 dark:text-gray-400">Total</p>
              <p class="text-xl font-bold text-gray-900 dark:text-white">
                {{ bookings().length }}
              </p>
            </div>
          </div>
        </div>

        <div
          class="bg-white dark:bg-gray-800 rounded-xl p-4 border border-gray-200 dark:border-gray-700"
        >
          <div class="flex items-center gap-3">
            <div class="p-2 bg-green-100 dark:bg-green-900 rounded-lg">
              <svg
                class="w-5 h-5 text-green-600 dark:text-green-400"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M5 13l4 4L19 7"
                />
              </svg>
            </div>
            <div>
              <p class="text-sm text-gray-500 dark:text-gray-400">Completed</p>
              <p class="text-xl font-bold text-green-600">{{ completedCount() }}</p>
            </div>
          </div>
        </div>

        <div
          class="bg-white dark:bg-gray-800 rounded-xl p-4 border border-gray-200 dark:border-gray-700"
        >
          <div class="flex items-center gap-3">
            <div class="p-2 bg-yellow-100 dark:bg-yellow-900 rounded-lg">
              <svg
                class="w-5 h-5 text-yellow-600 dark:text-yellow-400"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
            </div>
            <div>
              <p class="text-sm text-gray-500 dark:text-gray-400">In Progress</p>
              <p class="text-xl font-bold text-yellow-600">{{ activeCount() }}</p>
            </div>
          </div>
        </div>

        <div
          class="bg-white dark:bg-gray-800 rounded-xl p-4 border border-gray-200 dark:border-gray-700"
        >
          <div class="flex items-center gap-3">
            <div class="p-2 bg-purple-100 dark:bg-purple-900 rounded-lg">
              <svg
                class="w-5 h-5 text-purple-600 dark:text-purple-400"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
                />
              </svg>
            </div>
            <div>
              <p class="text-sm text-gray-500 dark:text-gray-400">Pending</p>
              <p class="text-xl font-bold text-purple-600">{{ pendingCount() }}</p>
            </div>
          </div>
        </div>
      </div>

      <!-- Bookings Table -->
      <div
        class="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 overflow-hidden"
      >
        <div class="p-4 border-b border-gray-200 dark:border-gray-700">
          <h2 class="text-lg font-semibold text-gray-900 dark:text-white">
            Daily Schedule
          </h2>
        </div>

        @if (isLoading()) {
          <div class="p-8 text-center">
            <div
              class="inline-block w-8 h-8 border-4 border-primary-200 border-t-primary-600 rounded-full animate-spin"
            ></div>
            <p class="mt-2 text-gray-500 dark:text-gray-400">Loading...</p>
          </div>
        } @else if (bookings().length === 0) {
          <div class="p-8 text-center">
            <svg
              class="w-12 h-12 mx-auto text-gray-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"
              />
            </svg>
            <h3 class="mt-2 text-lg font-medium text-gray-900 dark:text-white">
              No bookings for today
            </h3>
            <p class="mt-1 text-gray-500 dark:text-gray-400">
              Create a new booking to get started
            </p>
            <button
              routerLink="/booking/quick"
              class="mt-4 px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg font-medium transition-colors"
            >
              Create Booking
            </button>
          </div>
        } @else {
          <div class="overflow-x-auto">
            <table class="w-full">
              <thead class="bg-gray-50 dark:bg-gray-900">
                <tr>
                  <th
                    class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase"
                  >
                    Time
                  </th>
                  <th
                    class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase"
                  >
                    Aircraft
                  </th>
                  <th
                    class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase"
                  >
                    Pilot
                  </th>
                  <th
                    class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase"
                  >
                    Instructor
                  </th>
                  <th
                    class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase"
                  >
                    Type
                  </th>
                  <th
                    class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase"
                  >
                    Status
                  </th>
                  <th
                    class="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase"
                  >
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody class="divide-y divide-gray-200 dark:divide-gray-700">
                @for (booking of bookings(); track booking.id) {
                  <tr
                    class="hover:bg-gray-50 dark:hover:bg-gray-700 cursor-pointer"
                    [routerLink]="['/booking', booking.id]"
                  >
                    <td class="px-4 py-4 whitespace-nowrap">
                      <div class="text-sm font-medium text-gray-900 dark:text-white">
                        {{ booking.startTime | date : 'HH:mm' }} -
                        {{ booking.endTime | date : 'HH:mm' }}
                      </div>
                    </td>
                    <td class="px-4 py-4 whitespace-nowrap">
                      <div class="flex items-center">
                        <div
                          class="w-8 h-8 bg-primary-100 dark:bg-primary-900 rounded-full flex items-center justify-center"
                        >
                          <span
                            class="text-xs font-bold text-primary-600 dark:text-primary-400"
                          >
                            {{ booking.aircraft.registration.slice(-3) }}
                          </span>
                        </div>
                        <div class="ml-3">
                          <div
                            class="text-sm font-medium text-gray-900 dark:text-white"
                          >
                            {{ booking.aircraft.registration }}
                          </div>
                          <div class="text-xs text-gray-500">
                            {{ booking.aircraft.type }}
                          </div>
                        </div>
                      </div>
                    </td>
                    <td class="px-4 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                      {{ booking.pilot.firstName }} {{ booking.pilot.lastName }}
                    </td>
                    <td class="px-4 py-4 whitespace-nowrap text-sm">
                      @if (booking.instructor) {
                        <span class="text-gray-900 dark:text-white">
                          {{ booking.instructor.firstName }}
                          {{ booking.instructor.lastName }}
                        </span>
                      } @else {
                        <span class="text-gray-400">-</span>
                      }
                    </td>
                    <td class="px-4 py-4 whitespace-nowrap">
                      <span
                        [class]="
                          'px-2 py-1 text-xs font-medium rounded-full ' +
                          getTypeClass(booking.bookingType)
                        "
                      >
                        {{ booking.bookingType }}
                      </span>
                    </td>
                    <td class="px-4 py-4 whitespace-nowrap">
                      <span
                        [class]="
                          'px-2 py-1 text-xs font-medium rounded-full ' +
                          getStatusClass(booking.status)
                        "
                      >
                        {{ booking.status }}
                      </span>
                    </td>
                    <td class="px-4 py-4 whitespace-nowrap text-right">
                      @if (booking.status === 'confirmed') {
                        <button
                          (click)="startFlight(booking); $event.stopPropagation()"
                          class="px-3 py-1 bg-green-600 hover:bg-green-700 text-white text-sm rounded-lg transition-colors"
                        >
                          Start Flight
                        </button>
                      }
                      @if (booking.status === 'in_progress') {
                        <button
                          (click)="endFlight(booking); $event.stopPropagation()"
                          class="px-3 py-1 bg-yellow-600 hover:bg-yellow-700 text-white text-sm rounded-lg transition-colors"
                        >
                          End Flight
                        </button>
                      }
                    </td>
                  </tr>
                }
              </tbody>
            </table>
          </div>
        }
      </div>
    </div>
  `,
})
export class DispatchBoardComponent implements OnInit {
  private http = inject(HttpClient);

  selectedDate = signal(new Date());
  bookings = signal<Booking[]>([]);
  isLoading = signal(false);

  completedCount = computed(
    () => this.bookings().filter((b) => b.status === 'completed').length
  );
  activeCount = computed(
    () => this.bookings().filter((b) => b.status === 'in_progress').length
  );
  pendingCount = computed(
    () => this.bookings().filter((b) => b.status === 'confirmed').length
  );

  ngOnInit() {
    this.loadBookings();
  }

  previousDay() {
    const date = new Date(this.selectedDate());
    date.setDate(date.getDate() - 1);
    this.selectedDate.set(date);
    this.loadBookings();
  }

  nextDay() {
    const date = new Date(this.selectedDate());
    date.setDate(date.getDate() + 1);
    this.selectedDate.set(date);
    this.loadBookings();
  }

  goToToday() {
    this.selectedDate.set(new Date());
    this.loadBookings();
  }

  loadBookings() {
    this.isLoading.set(true);
    const date = this.selectedDate().toISOString().split('T')[0];

    // TODO: Load from API
    // this.http.get<Booking[]>(`${environment.apiBaseUrl}${environment.api.bookings}?date=${date}`)
    //   .subscribe(bookings => this.bookings.set(bookings));

    // Mock data for now
    setTimeout(() => {
      this.bookings.set([
        {
          id: '1',
          startTime: new Date().toISOString(),
          endTime: new Date(Date.now() + 3600000).toISOString(),
          status: 'confirmed',
          bookingType: 'Training',
          aircraft: { id: '1', registration: 'LN-ABC', type: 'C172' },
          pilot: { id: '1', firstName: 'John', lastName: 'Doe' },
          instructor: { id: '2', firstName: 'Jane', lastName: 'Smith' },
        },
      ]);
      this.isLoading.set(false);
    }, 500);
  }

  getStatusClass(status: string): string {
    const classes: Record<string, string> = {
      pending: 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300',
      confirmed: 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300',
      in_progress: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-300',
      completed: 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300',
      cancelled: 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300',
    };
    return classes[status] || classes['pending'];
  }

  getTypeClass(type: string): string {
    const classes: Record<string, string> = {
      Training: 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300',
      Solo: 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300',
      Checkride: 'bg-purple-100 text-purple-700 dark:bg-purple-900 dark:text-purple-300',
      Rental: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-300',
    };
    return classes[type] || 'bg-gray-100 text-gray-700';
  }

  startFlight(booking: Booking) {
    // Navigate to start flight page
    console.log('Start flight:', booking.id);
  }

  endFlight(booking: Booking) {
    // Navigate to end flight page
    console.log('End flight:', booking.id);
  }
}
