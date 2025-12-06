import { Component, Input, Output, EventEmitter, signal, ChangeDetectionStrategy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';

export interface User {
  id: string;
  firstName: string;
  lastName: string;
  email: string;
  avatarUrl?: string;
  roles: string[];
}

@Component({
  selector: 'fts-header',
  standalone: true,
  imports: [CommonModule, RouterModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <header
      class="h-16 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 px-4 lg:px-6 flex items-center justify-between"
    >
      <!-- Left: Toggle & Breadcrumb -->
      <div class="flex items-center gap-4">
        <button
          (click)="toggleSidebar.emit()"
          class="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 lg:hidden"
        >
          <svg
            class="w-6 h-6 text-gray-600 dark:text-gray-300"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M4 6h16M4 12h16M4 18h16"
            />
          </svg>
        </button>

        <!-- Breadcrumb / Page Title -->
        <div class="hidden lg:block">
          <h1 class="text-lg font-semibold text-gray-900 dark:text-white">
            Flight Training System
          </h1>
        </div>
      </div>

      <!-- Right: Actions -->
      <div class="flex items-center gap-3">
        <!-- Notifications -->
        <button
          class="relative p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700"
        >
          <svg
            class="w-6 h-6 text-gray-600 dark:text-gray-300"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"
            />
          </svg>
          <!-- Notification badge -->
          <span
            class="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full"
          ></span>
        </button>

        <!-- User Menu -->
        <div class="relative">
          <button
            (click)="showUserMenu.set(!showUserMenu())"
            class="flex items-center gap-2 p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700"
          >
            @if (currentUser?.avatarUrl) {
              <img
                [src]="currentUser.avatarUrl"
                [alt]="currentUser.firstName"
                class="w-8 h-8 rounded-full object-cover"
              />
            } @else {
              <div
                class="w-8 h-8 rounded-full bg-primary-100 dark:bg-primary-900 flex items-center justify-center"
              >
                <span
                  class="text-sm font-medium text-primary-600 dark:text-primary-400"
                >
                  {{ getInitials() }}
                </span>
              </div>
            }
            <span
              class="hidden lg:block text-sm font-medium text-gray-700 dark:text-gray-200"
            >
              {{ currentUser?.firstName }} {{ currentUser?.lastName }}
            </span>
            <svg
              class="w-4 h-4 text-gray-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M19 9l-7 7-7-7"
              />
            </svg>
          </button>

          <!-- Dropdown Menu -->
          @if (showUserMenu()) {
            <div
              class="absolute right-0 mt-2 w-48 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 py-1 z-50"
            >
              <a
                routerLink="/settings/profile"
                (click)="showUserMenu.set(false)"
                class="block px-4 py-2 text-sm text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700"
              >
                Profile
              </a>
              <a
                routerLink="/settings"
                (click)="showUserMenu.set(false)"
                class="block px-4 py-2 text-sm text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700"
              >
                Settings
              </a>
              <hr class="my-1 border-gray-200 dark:border-gray-700" />
              <button
                (click)="onLogout()"
                class="w-full text-left px-4 py-2 text-sm text-red-600 dark:text-red-400 hover:bg-gray-100 dark:hover:bg-gray-700"
              >
                Sign out
              </button>
            </div>
          }
        </div>
      </div>
    </header>
  `,
})
export class HeaderComponent {
  @Input() currentUser: User | null = null;
  @Input() sidebarCollapsed = false;

  @Output() toggleSidebar = new EventEmitter<void>();
  @Output() logout = new EventEmitter<void>();

  showUserMenu = signal(false);

  getInitials(): string {
    if (!this.currentUser) return '?';
    return `${this.currentUser.firstName?.[0] || ''}${this.currentUser.lastName?.[0] || ''}`.toUpperCase();
  }

  onLogout() {
    this.showUserMenu.set(false);
    this.logout.emit();
  }
}
