// apps/shell/src/app/shared/components/skeleton/skeleton.component.ts
/**
 * Skeleton Loading Components
 *
 * Provides various skeleton loading states for improved UX.
 * Accessible with proper ARIA attributes for screen readers.
 */

import { Component, Input, ChangeDetectionStrategy } from '@angular/core';
import { CommonModule } from '@angular/common';

/**
 * Base Skeleton Component
 * Renders a pulsing placeholder with customizable dimensions
 */
@Component({
  selector: 'fts-skeleton',
  standalone: true,
  imports: [CommonModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div
      [class]="baseClasses + ' ' + customClass"
      [style.width]="width"
      [style.height]="height"
      [attr.aria-hidden]="true"
      role="presentation"
    ></div>
  `,
})
export class SkeletonComponent {
  @Input() width = '100%';
  @Input() height = '1rem';
  @Input() rounded: 'none' | 'sm' | 'md' | 'lg' | 'full' = 'md';
  @Input() customClass = '';

  get baseClasses(): string {
    const roundedClasses: Record<string, string> = {
      none: 'rounded-none',
      sm: 'rounded-sm',
      md: 'rounded-md',
      lg: 'rounded-lg',
      full: 'rounded-full',
    };
    return `animate-pulse bg-gray-200 dark:bg-gray-700 ${roundedClasses[this.rounded]}`;
  }
}

/**
 * Text Skeleton Component
 * Renders multiple lines of text placeholders
 */
@Component({
  selector: 'fts-skeleton-text',
  standalone: true,
  imports: [CommonModule, SkeletonComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div
      class="space-y-2"
      [attr.aria-label]="'Loading ' + lines + ' lines of text'"
      role="status"
      aria-busy="true"
    >
      <span class="sr-only">Loading content...</span>
      @for (line of lineArray; track $index; let last = $last) {
        <fts-skeleton
          [width]="last && lastLineWidth ? lastLineWidth : '100%'"
          [height]="lineHeight"
        />
      }
    </div>
  `,
})
export class SkeletonTextComponent {
  @Input() lines = 3;
  @Input() lineHeight = '0.875rem';
  @Input() lastLineWidth = '75%';

  get lineArray(): number[] {
    return Array(this.lines).fill(0);
  }
}

/**
 * Avatar Skeleton Component
 * Renders a circular avatar placeholder
 */
@Component({
  selector: 'fts-skeleton-avatar',
  standalone: true,
  imports: [CommonModule, SkeletonComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <fts-skeleton
      [width]="size"
      [height]="size"
      rounded="full"
      [attr.aria-label]="'Loading avatar'"
      role="status"
      aria-busy="true"
    />
  `,
})
export class SkeletonAvatarComponent {
  @Input() size = '2.5rem';
}

/**
 * Card Skeleton Component
 * Renders a card-like placeholder with header, content, and optional image
 */
@Component({
  selector: 'fts-skeleton-card',
  standalone: true,
  imports: [CommonModule, SkeletonComponent, SkeletonTextComponent, SkeletonAvatarComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div
      class="bg-white dark:bg-gray-800 rounded-lg shadow-md overflow-hidden"
      role="status"
      aria-busy="true"
      aria-label="Loading card content"
    >
      <span class="sr-only">Loading content...</span>

      <!-- Optional Image -->
      @if (showImage) {
        <fts-skeleton
          width="100%"
          [height]="imageHeight"
          rounded="none"
        />
      }

      <div class="p-4 space-y-4">
        <!-- Header with avatar -->
        @if (showHeader) {
          <div class="flex items-center gap-3">
            <fts-skeleton-avatar size="2.5rem" />
            <div class="flex-1 space-y-2">
              <fts-skeleton height="0.875rem" width="60%" />
              <fts-skeleton height="0.75rem" width="40%" />
            </div>
          </div>
        }

        <!-- Content -->
        <fts-skeleton-text [lines]="contentLines" />

        <!-- Footer -->
        @if (showFooter) {
          <div class="flex justify-between items-center pt-2">
            <fts-skeleton height="2rem" width="5rem" rounded="md" />
            <fts-skeleton height="2rem" width="5rem" rounded="md" />
          </div>
        }
      </div>
    </div>
  `,
})
export class SkeletonCardComponent {
  @Input() showImage = false;
  @Input() imageHeight = '12rem';
  @Input() showHeader = true;
  @Input() contentLines = 3;
  @Input() showFooter = false;
}

/**
 * Table Row Skeleton Component
 * Renders table row placeholders
 */
@Component({
  selector: 'fts-skeleton-table',
  standalone: true,
  imports: [CommonModule, SkeletonComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div
      class="w-full"
      role="status"
      aria-busy="true"
      aria-label="Loading table data"
    >
      <span class="sr-only">Loading table data...</span>

      <!-- Header -->
      @if (showHeader) {
        <div class="flex gap-4 p-4 bg-gray-50 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
          @for (col of columnArray; track $index) {
            <fts-skeleton
              class="flex-1"
              height="1rem"
              [width]="getColumnWidth($index)"
            />
          }
        </div>
      }

      <!-- Rows -->
      @for (row of rowArray; track $index) {
        <div class="flex gap-4 p-4 border-b border-gray-100 dark:border-gray-700/50">
          @for (col of columnArray; track $index) {
            <fts-skeleton
              class="flex-1"
              height="0.875rem"
              [width]="getColumnWidth($index)"
            />
          }
        </div>
      }
    </div>
  `,
})
export class SkeletonTableComponent {
  @Input() rows = 5;
  @Input() columns = 4;
  @Input() showHeader = true;
  @Input() columnWidths: string[] = [];

  get rowArray(): number[] {
    return Array(this.rows).fill(0);
  }

  get columnArray(): number[] {
    return Array(this.columns).fill(0);
  }

  getColumnWidth(index: number): string {
    return this.columnWidths[index] || '100%';
  }
}

/**
 * List Skeleton Component
 * Renders list item placeholders with optional avatars
 */
@Component({
  selector: 'fts-skeleton-list',
  standalone: true,
  imports: [CommonModule, SkeletonComponent, SkeletonAvatarComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div
      class="space-y-4"
      role="status"
      aria-busy="true"
      aria-label="Loading list items"
    >
      <span class="sr-only">Loading list...</span>

      @for (item of itemArray; track $index) {
        <div class="flex items-center gap-4 p-3 bg-white dark:bg-gray-800 rounded-lg">
          @if (showAvatar) {
            <fts-skeleton-avatar [size]="avatarSize" />
          }
          <div class="flex-1 space-y-2">
            <fts-skeleton height="0.875rem" [width]="titleWidth" />
            @if (showSubtitle) {
              <fts-skeleton height="0.75rem" [width]="subtitleWidth" />
            }
          </div>
          @if (showAction) {
            <fts-skeleton height="2rem" width="4rem" rounded="md" />
          }
        </div>
      }
    </div>
  `,
})
export class SkeletonListComponent {
  @Input() items = 5;
  @Input() showAvatar = true;
  @Input() avatarSize = '2.5rem';
  @Input() showSubtitle = true;
  @Input() showAction = false;
  @Input() titleWidth = '60%';
  @Input() subtitleWidth = '40%';

  get itemArray(): number[] {
    return Array(this.items).fill(0);
  }
}

/**
 * Dashboard Skeleton Component
 * Renders a complete dashboard loading state
 */
@Component({
  selector: 'fts-skeleton-dashboard',
  standalone: true,
  imports: [CommonModule, SkeletonComponent, SkeletonCardComponent, SkeletonTableComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div
      class="space-y-6"
      role="status"
      aria-busy="true"
      aria-label="Loading dashboard"
    >
      <span class="sr-only">Loading dashboard...</span>

      <!-- Stats Cards -->
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        @for (card of statsArray; track $index) {
          <div class="bg-white dark:bg-gray-800 rounded-lg shadow-md p-4">
            <div class="flex items-center justify-between">
              <div class="space-y-2 flex-1">
                <fts-skeleton height="0.75rem" width="60%" />
                <fts-skeleton height="1.5rem" width="40%" />
              </div>
              <fts-skeleton height="3rem" width="3rem" rounded="lg" />
            </div>
          </div>
        }
      </div>

      <!-- Main Content Grid -->
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <!-- Main Chart Area -->
        <div class="lg:col-span-2 bg-white dark:bg-gray-800 rounded-lg shadow-md p-4">
          <fts-skeleton height="1rem" width="30%" customClass="mb-4" />
          <fts-skeleton height="16rem" width="100%" rounded="lg" />
        </div>

        <!-- Side Panel -->
        <div class="bg-white dark:bg-gray-800 rounded-lg shadow-md p-4">
          <fts-skeleton height="1rem" width="50%" customClass="mb-4" />
          <div class="space-y-3">
            @for (item of sideItemsArray; track $index) {
              <div class="flex items-center gap-3">
                <fts-skeleton height="2rem" width="2rem" rounded="full" />
                <div class="flex-1 space-y-1">
                  <fts-skeleton height="0.75rem" width="80%" />
                  <fts-skeleton height="0.625rem" width="50%" />
                </div>
              </div>
            }
          </div>
        </div>
      </div>

      <!-- Table Section -->
      <div class="bg-white dark:bg-gray-800 rounded-lg shadow-md overflow-hidden">
        <div class="p-4 border-b border-gray-200 dark:border-gray-700">
          <fts-skeleton height="1rem" width="20%" />
        </div>
        <fts-skeleton-table [rows]="5" [columns]="5" [showHeader]="true" />
      </div>
    </div>
  `,
})
export class SkeletonDashboardComponent {
  @Input() statsCount = 4;
  @Input() sideItems = 5;

  get statsArray(): number[] {
    return Array(this.statsCount).fill(0);
  }

  get sideItemsArray(): number[] {
    return Array(this.sideItems).fill(0);
  }
}
