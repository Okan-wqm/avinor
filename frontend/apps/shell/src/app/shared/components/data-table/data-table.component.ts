// apps/shell/src/app/shared/components/data-table/data-table.component.ts
/**
 * Data Table Component
 *
 * A reusable, accessible data table with sorting, filtering, pagination,
 * and row selection. WCAG 2.1 AA compliant.
 */

import {
  Component,
  Input,
  Output,
  EventEmitter,
  signal,
  computed,
  ChangeDetectionStrategy,
  ContentChild,
  TemplateRef,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import {
  ColumnDef,
  SortState,
  PaginationState,
  RowAction,
  BulkAction,
  DEFAULT_PAGE_SIZES,
  SortDirection,
} from './data-table.types';
import { SkeletonTableComponent } from '../skeleton';

@Component({
  selector: 'fts-data-table',
  standalone: true,
  imports: [CommonModule, FormsModule, SkeletonTableComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="bg-white dark:bg-gray-800 rounded-lg shadow-md overflow-hidden">
      <!-- Header with search and bulk actions -->
      @if (showHeader()) {
        <div
          class="px-4 py-3 border-b border-gray-200 dark:border-gray-700 flex flex-col sm:flex-row gap-3 items-start sm:items-center justify-between"
        >
          <!-- Search -->
          @if (searchable) {
            <div class="relative w-full sm:w-64">
              <svg
                class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                aria-hidden="true"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                />
              </svg>
              <input
                type="search"
                [ngModel]="searchQuery()"
                (ngModelChange)="onSearchChange($event)"
                [placeholder]="searchPlaceholder"
                class="w-full pl-9 pr-4 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                aria-label="Search table"
              />
            </div>
          }

          <!-- Bulk Actions -->
          @if (selectedCount() > 0 && bulkActions.length > 0) {
            <div class="flex items-center gap-2">
              <span class="text-sm text-gray-600 dark:text-gray-400">
                {{ selectedCount() }} selected
              </span>
              @for (action of bulkActions; track action.id) {
                <button
                  type="button"
                  (click)="onBulkAction(action)"
                  [class]="getBulkActionClasses(action.variant)"
                >
                  {{ action.label }}
                </button>
              }
            </div>
          }
        </div>
      }

      <!-- Loading State -->
      @if (loading) {
        <fts-skeleton-table [rows]="pageSize" [columns]="columns.length" />
      } @else {
        <!-- Table -->
        <div class="overflow-x-auto">
          <table
            class="w-full"
            role="grid"
            [attr.aria-rowcount]="data.length"
            [attr.aria-colcount]="columns.length"
            aria-label="Data table"
          >
            <!-- Header -->
            <thead class="bg-gray-50 dark:bg-gray-700/50">
              <tr role="row">
                <!-- Selection Column -->
                @if (selectable) {
                  <th
                    scope="col"
                    class="px-4 py-3 w-12"
                    role="columnheader"
                  >
                    <input
                      type="checkbox"
                      [checked]="isAllSelected()"
                      [indeterminate]="isIndeterminate()"
                      (change)="toggleSelectAll()"
                      class="w-4 h-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                      aria-label="Select all rows"
                    />
                  </th>
                }

                <!-- Data Columns -->
                @for (column of columns; track column.id) {
                  <th
                    scope="col"
                    [class]="getHeaderClasses(column)"
                    [style.width]="column.width"
                    [style.minWidth]="column.minWidth"
                    [style.maxWidth]="column.maxWidth"
                    role="columnheader"
                    [attr.aria-sort]="getAriaSort(column.id)"
                  >
                    @if (column.sortable) {
                      <button
                        type="button"
                        (click)="onSort(column.id)"
                        class="flex items-center gap-1 hover:text-gray-900 dark:hover:text-white focus:outline-none focus:text-primary-600"
                        [attr.aria-label]="'Sort by ' + column.header"
                      >
                        <span>{{ column.header }}</span>
                        <span class="flex flex-col" aria-hidden="true">
                          <svg
                            class="w-3 h-3 -mb-1"
                            [class.text-primary-600]="sortState().columnId === column.id && sortState().direction === 'asc'"
                            [class.text-gray-400]="sortState().columnId !== column.id || sortState().direction !== 'asc'"
                            fill="currentColor"
                            viewBox="0 0 24 24"
                          >
                            <path d="M7 14l5-5 5 5z" />
                          </svg>
                          <svg
                            class="w-3 h-3 -mt-1"
                            [class.text-primary-600]="sortState().columnId === column.id && sortState().direction === 'desc'"
                            [class.text-gray-400]="sortState().columnId !== column.id || sortState().direction !== 'desc'"
                            fill="currentColor"
                            viewBox="0 0 24 24"
                          >
                            <path d="M7 10l5 5 5-5z" />
                          </svg>
                        </span>
                      </button>
                    } @else {
                      {{ column.header }}
                    }
                  </th>
                }

                <!-- Actions Column -->
                @if (rowActions.length > 0) {
                  <th
                    scope="col"
                    class="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider"
                    role="columnheader"
                  >
                    <span class="sr-only">Actions</span>
                  </th>
                }
              </tr>
            </thead>

            <!-- Body -->
            <tbody class="divide-y divide-gray-200 dark:divide-gray-700">
              @if (displayData().length === 0) {
                <tr>
                  <td
                    [attr.colspan]="getTotalColumns()"
                    class="px-4 py-12 text-center"
                  >
                    <div class="flex flex-col items-center">
                      <svg
                        class="w-12 h-12 text-gray-300 dark:text-gray-600 mb-3"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                        aria-hidden="true"
                      >
                        <path
                          stroke-linecap="round"
                          stroke-linejoin="round"
                          stroke-width="1.5"
                          d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
                        />
                      </svg>
                      <p class="text-gray-500 dark:text-gray-400">
                        {{ emptyMessage }}
                      </p>
                    </div>
                  </td>
                </tr>
              } @else {
                @for (row of displayData(); track trackByFn(row); let i = $index) {
                  <tr
                    role="row"
                    [attr.aria-rowindex]="i + 1"
                    [class.bg-primary-50]="isSelected(row)"
                    [class.dark:bg-primary-900/20]="isSelected(row)"
                    class="hover:bg-gray-50 dark:hover:bg-gray-700/30 transition-colors"
                  >
                    <!-- Selection -->
                    @if (selectable) {
                      <td class="px-4 py-3" role="gridcell">
                        <input
                          type="checkbox"
                          [checked]="isSelected(row)"
                          (change)="toggleSelect(row)"
                          class="w-4 h-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                          [attr.aria-label]="'Select row ' + (i + 1)"
                        />
                      </td>
                    }

                    <!-- Data Cells -->
                    @for (column of columns; track column.id) {
                      <td
                        [class]="getCellClasses(column)"
                        role="gridcell"
                      >
                        @if (cellTemplates[column.cellTemplate!]) {
                          <ng-container
                            *ngTemplateOutlet="
                              cellTemplates[column.cellTemplate!];
                              context: { $implicit: row, column: column, value: getCellValue(row, column) }
                            "
                          />
                        } @else {
                          {{ getCellValue(row, column) }}
                        }
                      </td>
                    }

                    <!-- Row Actions -->
                    @if (rowActions.length > 0) {
                      <td class="px-4 py-3 text-right" role="gridcell">
                        <div class="flex items-center justify-end gap-2">
                          @for (action of getVisibleActions(row); track action.id) {
                            <button
                              type="button"
                              (click)="onRowAction(action, row)"
                              [disabled]="action.disabled?.(row)"
                              [class]="getActionButtonClasses(action.variant)"
                              [attr.aria-label]="action.label"
                            >
                              {{ action.label }}
                            </button>
                          }
                        </div>
                      </td>
                    }
                  </tr>
                }
              }
            </tbody>
          </table>
        </div>

        <!-- Pagination -->
        @if (paginated && displayData().length > 0) {
          <div
            class="px-4 py-3 border-t border-gray-200 dark:border-gray-700 flex flex-col sm:flex-row gap-3 items-center justify-between"
          >
            <!-- Page size selector -->
            <div class="flex items-center gap-2">
              <label
                for="pageSize"
                class="text-sm text-gray-600 dark:text-gray-400"
              >
                Show
              </label>
              <select
                id="pageSize"
                [ngModel]="pageSize"
                (ngModelChange)="onPageSizeChange($event)"
                class="border border-gray-300 dark:border-gray-600 rounded-md px-2 py-1 text-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500"
              >
                @for (size of pageSizes; track size) {
                  <option [value]="size">{{ size }}</option>
                }
              </select>
              <span class="text-sm text-gray-600 dark:text-gray-400">
                entries
              </span>
            </div>

            <!-- Page info and navigation -->
            <div class="flex items-center gap-4">
              <span class="text-sm text-gray-600 dark:text-gray-400">
                {{ getPageInfo() }}
              </span>

              <nav aria-label="Table pagination">
                <ul class="flex items-center gap-1">
                  <!-- First -->
                  <li>
                    <button
                      type="button"
                      (click)="goToPage(1)"
                      [disabled]="currentPage() === 1"
                      class="p-2 rounded-md hover:bg-gray-100 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
                      aria-label="First page"
                    >
                      <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 19l-7-7 7-7m8 14l-7-7 7-7" />
                      </svg>
                    </button>
                  </li>
                  <!-- Previous -->
                  <li>
                    <button
                      type="button"
                      (click)="goToPage(currentPage() - 1)"
                      [disabled]="currentPage() === 1"
                      class="p-2 rounded-md hover:bg-gray-100 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
                      aria-label="Previous page"
                    >
                      <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
                      </svg>
                    </button>
                  </li>

                  <!-- Page numbers -->
                  @for (page of visiblePages(); track page) {
                    <li>
                      @if (page === '...') {
                        <span class="px-3 py-1 text-gray-500">...</span>
                      } @else {
                        <button
                          type="button"
                          (click)="goToPage(+page)"
                          [class]="getPageButtonClasses(+page)"
                          [attr.aria-current]="currentPage() === +page ? 'page' : null"
                        >
                          {{ page }}
                        </button>
                      }
                    </li>
                  }

                  <!-- Next -->
                  <li>
                    <button
                      type="button"
                      (click)="goToPage(currentPage() + 1)"
                      [disabled]="currentPage() === totalPages()"
                      class="p-2 rounded-md hover:bg-gray-100 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
                      aria-label="Next page"
                    >
                      <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
                      </svg>
                    </button>
                  </li>
                  <!-- Last -->
                  <li>
                    <button
                      type="button"
                      (click)="goToPage(totalPages())"
                      [disabled]="currentPage() === totalPages()"
                      class="p-2 rounded-md hover:bg-gray-100 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
                      aria-label="Last page"
                    >
                      <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 5l7 7-7 7M5 5l7 7-7 7" />
                      </svg>
                    </button>
                  </li>
                </ul>
              </nav>
            </div>
          </div>
        }
      }
    </div>
  `,
})
export class DataTableComponent<T extends { id?: string | number }> {
  // Data
  @Input() data: T[] = [];
  @Input() columns: ColumnDef<T>[] = [];
  @Input() loading = false;

  // Features
  @Input() selectable = false;
  @Input() searchable = false;
  @Input() paginated = true;
  @Input() searchPlaceholder = 'Search...';
  @Input() emptyMessage = 'No data available';

  // Pagination
  @Input() pageSize = 10;
  @Input() pageSizes = DEFAULT_PAGE_SIZES;

  // Actions
  @Input() rowActions: RowAction<T>[] = [];
  @Input() bulkActions: BulkAction[] = [];

  // Custom templates
  @Input() cellTemplates: Record<string, TemplateRef<unknown>> = {};

  // Track function
  @Input() trackByFn: (row: T) => string | number = (row) =>
    row.id ?? JSON.stringify(row);

  // Events
  @Output() sortChange = new EventEmitter<SortState>();
  @Output() pageChange = new EventEmitter<PaginationState>();
  @Output() selectionChange = new EventEmitter<T[]>();
  @Output() search = new EventEmitter<string>();

  // State
  protected sortState = signal<SortState>({ columnId: null, direction: null });
  protected currentPage = signal(1);
  protected selectedIds = signal<Set<string | number>>(new Set());
  protected searchQuery = signal('');

  // Computed
  protected showHeader = computed(
    () => this.searchable || this.bulkActions.length > 0
  );

  protected selectedCount = computed(() => this.selectedIds().size);

  protected totalPages = computed(() =>
    Math.ceil(this.data.length / this.pageSize)
  );

  protected displayData = computed(() => {
    let result = [...this.data];

    // Apply search filter
    const query = this.searchQuery().toLowerCase();
    if (query) {
      result = result.filter((row) =>
        this.columns.some((col) => {
          const value = this.getCellValue(row, col);
          return String(value).toLowerCase().includes(query);
        })
      );
    }

    // Apply sorting
    const sort = this.sortState();
    if (sort.columnId && sort.direction) {
      const column = this.columns.find((c) => c.id === sort.columnId);
      if (column) {
        result.sort((a, b) => {
          const aVal = this.getCellValue(a, column);
          const bVal = this.getCellValue(b, column);
          const comparison =
            String(aVal).localeCompare(String(bVal), undefined, {
              numeric: true,
            });
          return sort.direction === 'asc' ? comparison : -comparison;
        });
      }
    }

    // Apply pagination
    if (this.paginated) {
      const start = (this.currentPage() - 1) * this.pageSize;
      result = result.slice(start, start + this.pageSize);
    }

    return result;
  });

  protected visiblePages = computed(() => {
    const total = this.totalPages();
    const current = this.currentPage();
    const pages: (string | number)[] = [];

    if (total <= 7) {
      for (let i = 1; i <= total; i++) {
        pages.push(i);
      }
    } else {
      pages.push(1);
      if (current > 3) {
        pages.push('...');
      }
      for (
        let i = Math.max(2, current - 1);
        i <= Math.min(total - 1, current + 1);
        i++
      ) {
        pages.push(i);
      }
      if (current < total - 2) {
        pages.push('...');
      }
      pages.push(total);
    }

    return pages;
  });

  // Methods
  getCellValue(row: T, column: ColumnDef<T>): unknown {
    if (column.accessorFn) {
      return column.accessorFn(row);
    }
    if (column.accessorKey) {
      // Support nested paths like 'user.name'
      const keys = String(column.accessorKey).split('.');
      let value: unknown = row;
      for (const key of keys) {
        value = (value as Record<string, unknown>)?.[key];
      }
      return value ?? '';
    }
    return '';
  }

  getHeaderClasses(column: ColumnDef<T>): string {
    const base =
      'px-4 py-3 text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider';
    const align = column.align === 'center' ? 'text-center' : column.align === 'right' ? 'text-right' : 'text-left';
    const hide = column.hideOnMobile ? 'hidden md:table-cell' : '';
    return `${base} ${align} ${hide} ${column.headerClass || ''}`;
  }

  getCellClasses(column: ColumnDef<T>): string {
    const base =
      'px-4 py-3 text-sm text-gray-900 dark:text-gray-100';
    const align = column.align === 'center' ? 'text-center' : column.align === 'right' ? 'text-right' : 'text-left';
    const hide = column.hideOnMobile ? 'hidden md:table-cell' : '';
    return `${base} ${align} ${hide} ${column.cellClass || ''}`;
  }

  getAriaSort(columnId: string): string | null {
    const sort = this.sortState();
    if (sort.columnId !== columnId) return null;
    return sort.direction === 'asc' ? 'ascending' : sort.direction === 'desc' ? 'descending' : null;
  }

  getTotalColumns(): number {
    let count = this.columns.length;
    if (this.selectable) count++;
    if (this.rowActions.length > 0) count++;
    return count;
  }

  // Selection
  isSelected(row: T): boolean {
    return this.selectedIds().has(row.id ?? JSON.stringify(row));
  }

  isAllSelected(): boolean {
    return (
      this.displayData().length > 0 &&
      this.displayData().every((row) => this.isSelected(row))
    );
  }

  isIndeterminate(): boolean {
    const count = this.selectedCount();
    return count > 0 && count < this.displayData().length;
  }

  toggleSelect(row: T): void {
    const id = row.id ?? JSON.stringify(row);
    this.selectedIds.update((ids) => {
      const newIds = new Set(ids);
      if (newIds.has(id)) {
        newIds.delete(id);
      } else {
        newIds.add(id);
      }
      return newIds;
    });
    this.emitSelectionChange();
  }

  toggleSelectAll(): void {
    if (this.isAllSelected()) {
      this.selectedIds.set(new Set());
    } else {
      const ids = this.displayData().map(
        (row) => row.id ?? JSON.stringify(row)
      );
      this.selectedIds.set(new Set(ids));
    }
    this.emitSelectionChange();
  }

  private emitSelectionChange(): void {
    const selected = this.data.filter((row) =>
      this.selectedIds().has(row.id ?? JSON.stringify(row))
    );
    this.selectionChange.emit(selected);
  }

  // Sorting
  onSort(columnId: string): void {
    this.sortState.update((state) => {
      let direction: SortDirection = 'asc';
      if (state.columnId === columnId) {
        direction =
          state.direction === 'asc'
            ? 'desc'
            : state.direction === 'desc'
              ? null
              : 'asc';
      }
      return { columnId: direction ? columnId : null, direction };
    });
    this.sortChange.emit(this.sortState());
  }

  // Pagination
  goToPage(page: number): void {
    if (page >= 1 && page <= this.totalPages()) {
      this.currentPage.set(page);
      this.pageChange.emit({
        page,
        pageSize: this.pageSize,
        total: this.data.length,
      });
    }
  }

  onPageSizeChange(size: number): void {
    this.pageSize = size;
    this.currentPage.set(1);
    this.pageChange.emit({
      page: 1,
      pageSize: size,
      total: this.data.length,
    });
  }

  getPageInfo(): string {
    const start = (this.currentPage() - 1) * this.pageSize + 1;
    const end = Math.min(this.currentPage() * this.pageSize, this.data.length);
    return `${start}-${end} of ${this.data.length}`;
  }

  getPageButtonClasses(page: number): string {
    const base = 'px-3 py-1 rounded-md text-sm';
    return this.currentPage() === page
      ? `${base} bg-primary-600 text-white`
      : `${base} hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300`;
  }

  // Search
  onSearchChange(query: string): void {
    this.searchQuery.set(query);
    this.currentPage.set(1);
    this.search.emit(query);
  }

  // Actions
  getVisibleActions(row: T): RowAction<T>[] {
    return this.rowActions.filter(
      (action) => !action.visible || action.visible(row)
    );
  }

  onRowAction(action: RowAction<T>, row: T): void {
    action.handler(row);
  }

  onBulkAction(action: BulkAction): void {
    const ids = Array.from(this.selectedIds()).map(String);
    action.handler(ids);
  }

  getActionButtonClasses(variant?: string): string {
    const base =
      'px-3 py-1.5 text-xs font-medium rounded-md transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2';
    const variants: Record<string, string> = {
      default:
        'bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600 focus:ring-gray-500',
      danger:
        'bg-red-100 text-red-700 hover:bg-red-200 dark:bg-red-900/30 dark:text-red-400 dark:hover:bg-red-900/50 focus:ring-red-500',
      success:
        'bg-green-100 text-green-700 hover:bg-green-200 dark:bg-green-900/30 dark:text-green-400 dark:hover:bg-green-900/50 focus:ring-green-500',
      warning:
        'bg-yellow-100 text-yellow-700 hover:bg-yellow-200 dark:bg-yellow-900/30 dark:text-yellow-400 dark:hover:bg-yellow-900/50 focus:ring-yellow-500',
    };
    return `${base} ${variants[variant || 'default']}`;
  }

  getBulkActionClasses(variant?: string): string {
    return this.getActionButtonClasses(variant);
  }
}
