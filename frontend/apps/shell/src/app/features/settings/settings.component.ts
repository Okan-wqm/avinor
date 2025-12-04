import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ThemeService } from '../../core/services/theme.service';
import { AuthStore } from '../../core/services/auth.store';

@Component({
  selector: 'fts-settings',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="max-w-2xl space-y-6">
      <h1 class="text-2xl font-bold text-gray-900 dark:text-white">Settings</h1>

      <!-- Appearance -->
      <div
        class="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700"
      >
        <div class="p-4 border-b border-gray-200 dark:border-gray-700">
          <h2 class="text-lg font-semibold text-gray-900 dark:text-white">
            Appearance
          </h2>
        </div>
        <div class="p-4">
          <div class="flex items-center justify-between">
            <div>
              <p class="font-medium text-gray-900 dark:text-white">Dark Mode</p>
              <p class="text-sm text-gray-500 dark:text-gray-400">
                Switch between light and dark theme
              </p>
            </div>
            <button
              (click)="themeService.toggleTheme()"
              [class]="
                'relative inline-flex h-6 w-11 items-center rounded-full transition-colors ' +
                (themeService.isDarkMode()
                  ? 'bg-primary-600'
                  : 'bg-gray-200 dark:bg-gray-700')
              "
            >
              <span
                [class]="
                  'inline-block h-4 w-4 transform rounded-full bg-white transition-transform ' +
                  (themeService.isDarkMode() ? 'translate-x-6' : 'translate-x-1')
                "
              ></span>
            </button>
          </div>
        </div>
      </div>

      <!-- Profile -->
      <div
        class="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700"
      >
        <div class="p-4 border-b border-gray-200 dark:border-gray-700">
          <h2 class="text-lg font-semibold text-gray-900 dark:text-white">
            Profile
          </h2>
        </div>
        <div class="p-4 space-y-4">
          <div>
            <p class="text-sm text-gray-500 dark:text-gray-400">Name</p>
            <p class="font-medium text-gray-900 dark:text-white">
              {{ authStore.user()?.firstName }} {{ authStore.user()?.lastName }}
            </p>
          </div>
          <div>
            <p class="text-sm text-gray-500 dark:text-gray-400">Email</p>
            <p class="font-medium text-gray-900 dark:text-white">
              {{ authStore.user()?.email }}
            </p>
          </div>
          <div>
            <p class="text-sm text-gray-500 dark:text-gray-400">Organization</p>
            <p class="font-medium text-gray-900 dark:text-white">
              {{ authStore.user()?.organizationName }}
            </p>
          </div>
          <div>
            <p class="text-sm text-gray-500 dark:text-gray-400">Roles</p>
            <div class="flex flex-wrap gap-2 mt-1">
              @for (role of authStore.user()?.roles || []; track role) {
                <span
                  class="px-2 py-1 text-xs font-medium bg-primary-100 dark:bg-primary-900 text-primary-700 dark:text-primary-300 rounded"
                >
                  {{ role }}
                </span>
              }
            </div>
          </div>
        </div>
      </div>
    </div>
  `,
})
export class SettingsComponent {
  protected themeService = inject(ThemeService);
  protected authStore = inject(AuthStore);
}
