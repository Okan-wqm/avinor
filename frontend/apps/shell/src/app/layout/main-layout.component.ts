import {
  Component,
  signal,
  computed,
  inject,
  OnInit,
  ChangeDetectionStrategy,
  DestroyRef,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule, Router, NavigationStart, NavigationEnd } from '@angular/router';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';

import { HeaderComponent } from './header/header.component';
import { SidebarComponent } from './sidebar/sidebar.component';
import { SkipLinkComponent } from './skip-link.component';
import { AuthStore } from '../core/services/auth.store';
import { ThemeService } from '../core/services/theme.service';

export interface MenuItem {
  label: string;
  icon: string;
  route: string;
  badge?: number;
  children?: MenuItem[];
  roles?: string[];
}

@Component({
  selector: 'fts-main-layout',
  standalone: true,
  imports: [CommonModule, RouterModule, HeaderComponent, SidebarComponent, SkipLinkComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <!-- Skip to main content link for keyboard users (WCAG 2.1 AA) -->
    <fts-skip-link />

    <div class="flex h-screen overflow-hidden" [class.dark]="isDarkMode()">
      <!-- Loading Bar - hidden from screen readers -->
      @if (isNavigating()) {
        <div
          class="fixed top-0 left-0 right-0 h-1 bg-primary-500 z-50 animate-pulse"
          aria-hidden="true"
          role="presentation"
        ></div>
      }

      <!-- Sidebar Navigation -->
      <fts-sidebar
        [collapsed]="sidebarCollapsed()"
        [menuItems]="menuItems()"
        [currentUser]="authStore.user()"
        (toggleCollapse)="toggleSidebar()"
      />

      <!-- Main Content Area -->
      <div class="flex-1 flex flex-col min-w-0 overflow-hidden">
        <!-- Header -->
        <fts-header
          [currentUser]="authStore.user()"
          [sidebarCollapsed]="sidebarCollapsed()"
          (toggleSidebar)="toggleSidebar()"
          (logout)="onLogout()"
        />

        <!-- Page Content - Main landmark for accessibility -->
        <main
          id="main-content"
          class="flex-1 overflow-auto bg-gray-50 dark:bg-gray-900 p-4 lg:p-6"
          role="main"
          aria-label="Main content"
          tabindex="-1"
        >
          <router-outlet />
        </main>

        <!-- Footer - Contentinfo landmark -->
        <footer
          class="px-4 lg:px-6 py-3 bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700"
          role="contentinfo"
        >
          <div
            class="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400"
          >
            <span>&copy; 2024 Flight Training System</span>
            <span>v1.0.0</span>
          </div>
        </footer>
      </div>
    </div>
  `,
})
export class MainLayoutComponent implements OnInit {
  protected authStore = inject(AuthStore);
  private router = inject(Router);
  private themeService = inject(ThemeService);
  private destroyRef = inject(DestroyRef);

  // State
  sidebarCollapsed = signal(false);
  isNavigating = signal(false);

  // Computed
  isDarkMode = computed(() => this.themeService.isDarkMode());

  // Menu items based on user roles
  menuItems = computed<MenuItem[]>(() => {
    const user = this.authStore.user();
    const roles = user?.roles || [];

    const items: MenuItem[] = [
      { label: 'Dashboard', icon: 'home', route: '/dashboard' },
      {
        label: 'Dispatch',
        icon: 'clipboard-list',
        route: '/dispatch',
      },
      {
        label: 'Booking',
        icon: 'calendar',
        route: '/booking',
        children: [
          { label: 'Calendar', icon: 'calendar-days', route: '/booking/calendar' },
          { label: 'Quick Book', icon: 'plus', route: '/booking/quick' },
          { label: 'Resources', icon: 'layers', route: '/booking/resources' },
        ],
      },
      {
        label: 'Flights',
        icon: 'plane',
        route: '/flights',
        children: [
          { label: 'Active', icon: 'plane-departure', route: '/flights/active' },
          { label: 'History', icon: 'history', route: '/flights/history' },
          { label: 'Logbook', icon: 'book', route: '/flights/logbook' },
        ],
      },
      {
        label: 'Training',
        icon: 'graduation-cap',
        route: '/training',
        children: [
          { label: 'Syllabus', icon: 'list', route: '/training/syllabus' },
          { label: 'Progress', icon: 'chart-line', route: '/training/progress' },
          { label: 'Exams', icon: 'file-text', route: '/training/exams' },
        ],
      },
    ];

    // Admin menu (role-based)
    if (roles.includes('admin') || roles.includes('super_admin')) {
      items.push({
        label: 'Admin',
        icon: 'settings',
        route: '/admin',
        roles: ['admin', 'super_admin'],
        children: [
          { label: 'Users', icon: 'users', route: '/admin/users' },
          { label: 'Aircraft', icon: 'plane', route: '/admin/aircraft' },
          { label: 'Organization', icon: 'building', route: '/admin/organization' },
          { label: 'Finance', icon: 'wallet', route: '/admin/finance' },
          { label: 'Reports', icon: 'chart-bar', route: '/admin/reports' },
        ],
      });
    }

    return items;
  });

  ngOnInit() {
    // Track navigation for loading state (auto-cleanup with takeUntilDestroyed)
    this.router.events
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((event) => {
        if (event instanceof NavigationStart) {
          this.isNavigating.set(true);
        }
        if (event instanceof NavigationEnd) {
          this.isNavigating.set(false);
        }
      });
  }

  toggleSidebar() {
    this.sidebarCollapsed.update((v) => !v);
  }

  onLogout() {
    this.authStore.logout();
    this.router.navigate(['/auth/login']);
  }
}
