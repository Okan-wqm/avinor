import { Component, Input, Output, EventEmitter, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { MenuItem } from '../main-layout.component';

@Component({
  selector: 'fts-sidebar',
  standalone: true,
  imports: [CommonModule, RouterModule],
  template: `
    <aside
      [class]="
        'h-screen bg-gray-900 text-white transition-all duration-300 flex flex-col ' +
        (collapsed ? 'w-16' : 'w-64')
      "
    >
      <!-- Logo -->
      <div
        class="h-16 flex items-center justify-between px-4 border-b border-gray-800"
      >
        @if (!collapsed) {
          <div class="flex items-center gap-2">
            <svg
              class="w-8 h-8 text-primary-500"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z"
              />
            </svg>
            <span class="font-bold text-lg">FTS</span>
          </div>
        } @else {
          <svg
            class="w-8 h-8 text-primary-500 mx-auto"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z"
            />
          </svg>
        }
      </div>

      <!-- Navigation -->
      <nav class="flex-1 overflow-y-auto py-4">
        <ul class="space-y-1 px-2">
          @for (item of menuItems; track item.route) {
            <li>
              <!-- Main menu item -->
              <a
                [routerLink]="item.route"
                routerLinkActive="bg-gray-800 text-white"
                [routerLinkActiveOptions]="{ exact: item.route === '/dashboard' }"
                class="flex items-center gap-3 px-3 py-2.5 rounded-lg text-gray-300 hover:bg-gray-800 hover:text-white transition-colors"
                [class.justify-center]="collapsed"
                [title]="collapsed ? item.label : ''"
                (click)="item.children ? toggleSubmenu(item.route) : null"
              >
                <span class="flex-shrink-0">
                  <ng-container [ngSwitch]="item.icon">
                    <svg
                      *ngSwitchCase="'home'"
                      class="w-5 h-5"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"
                      />
                    </svg>
                    <svg
                      *ngSwitchCase="'clipboard-list'"
                      class="w-5 h-5"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01"
                      />
                    </svg>
                    <svg
                      *ngSwitchCase="'calendar'"
                      class="w-5 h-5"
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
                    <svg
                      *ngSwitchCase="'plane'"
                      class="w-5 h-5"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"
                      />
                    </svg>
                    <svg
                      *ngSwitchCase="'graduation-cap'"
                      class="w-5 h-5"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M12 14l9-5-9-5-9 5 9 5z"
                      />
                      <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M12 14l6.16-3.422a12.083 12.083 0 01.665 6.479A11.952 11.952 0 0012 20.055a11.952 11.952 0 00-6.824-2.998 12.078 12.078 0 01.665-6.479L12 14z"
                      />
                    </svg>
                    <svg
                      *ngSwitchCase="'settings'"
                      class="w-5 h-5"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
                      />
                      <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                      />
                    </svg>
                    <svg
                      *ngSwitchDefault
                      class="w-5 h-5"
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
                  </ng-container>
                </span>
                @if (!collapsed) {
                  <span class="flex-1">{{ item.label }}</span>
                  @if (item.badge) {
                    <span
                      class="px-2 py-0.5 text-xs font-medium bg-primary-500 rounded-full"
                    >
                      {{ item.badge }}
                    </span>
                  }
                  @if (item.children) {
                    <svg
                      class="w-4 h-4 transition-transform"
                      [class.rotate-180]="openSubmenus()[item.route]"
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
                  }
                }
              </a>

              <!-- Submenu -->
              @if (item.children && !collapsed && openSubmenus()[item.route]) {
                <ul class="mt-1 ml-4 space-y-1">
                  @for (child of item.children; track child.route) {
                    <li>
                      <a
                        [routerLink]="child.route"
                        routerLinkActive="text-primary-400"
                        class="flex items-center gap-3 px-3 py-2 rounded-lg text-gray-400 hover:text-white transition-colors text-sm"
                      >
                        {{ child.label }}
                      </a>
                    </li>
                  }
                </ul>
              }
            </li>
          }
        </ul>
      </nav>

      <!-- User info at bottom -->
      @if (currentUser && !collapsed) {
        <div class="p-4 border-t border-gray-800">
          <div class="flex items-center gap-3">
            <div
              class="w-10 h-10 rounded-full bg-gray-700 flex items-center justify-center"
            >
              <span class="text-sm font-medium">
                {{ currentUser.firstName?.[0] }}{{ currentUser.lastName?.[0] }}
              </span>
            </div>
            <div class="flex-1 min-w-0">
              <p class="text-sm font-medium text-white truncate">
                {{ currentUser.firstName }} {{ currentUser.lastName }}
              </p>
              <p class="text-xs text-gray-400 truncate">
                {{ currentUser.email }}
              </p>
            </div>
          </div>
        </div>
      }

      <!-- Collapse toggle -->
      <button
        (click)="toggleCollapse.emit()"
        class="hidden lg:flex items-center justify-center h-12 border-t border-gray-800 hover:bg-gray-800 transition-colors"
      >
        <svg
          class="w-5 h-5 text-gray-400 transition-transform"
          [class.rotate-180]="collapsed"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M11 19l-7-7 7-7m8 14l-7-7 7-7"
          />
        </svg>
      </button>
    </aside>
  `,
})
export class SidebarComponent {
  @Input() collapsed = false;
  @Input() menuItems: MenuItem[] = [];
  @Input() currentUser: any = null;

  @Output() toggleCollapse = new EventEmitter<void>();

  openSubmenus = signal<Record<string, boolean>>({});

  toggleSubmenu(route: string) {
    this.openSubmenus.update((state) => ({
      ...state,
      [route]: !state[route],
    }));
  }
}
