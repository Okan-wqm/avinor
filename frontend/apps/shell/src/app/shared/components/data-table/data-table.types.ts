// apps/shell/src/app/shared/components/data-table/data-table.types.ts
/**
 * Data Table Types
 *
 * Type definitions for the reusable data table component.
 */

export type SortDirection = 'asc' | 'desc' | null;

export interface ColumnDef<T = unknown> {
  /** Unique identifier for the column */
  id: string;
  /** Display header text */
  header: string;
  /** Key to access data from row object (supports nested paths like 'user.name') */
  accessorKey?: keyof T | string;
  /** Custom accessor function */
  accessorFn?: (row: T) => unknown;
  /** Whether the column is sortable */
  sortable?: boolean;
  /** Whether the column is filterable */
  filterable?: boolean;
  /** Column width (CSS value) */
  width?: string;
  /** Min width (CSS value) */
  minWidth?: string;
  /** Max width (CSS value) */
  maxWidth?: string;
  /** Text alignment */
  align?: 'left' | 'center' | 'right';
  /** Custom cell template name */
  cellTemplate?: string;
  /** Custom header template name */
  headerTemplate?: string;
  /** Whether to show on mobile */
  hideOnMobile?: boolean;
  /** Column CSS classes */
  cellClass?: string;
  /** Header CSS classes */
  headerClass?: string;
}

export interface SortState {
  columnId: string | null;
  direction: SortDirection;
}

export interface FilterState {
  columnId: string;
  value: string;
}

export interface PaginationState {
  page: number;
  pageSize: number;
  total: number;
}

export interface TableState {
  sort: SortState;
  filters: FilterState[];
  pagination: PaginationState;
  selectedIds: Set<string>;
}

export interface RowAction<T = unknown> {
  id: string;
  label: string;
  icon?: string;
  handler: (row: T) => void;
  visible?: (row: T) => boolean;
  disabled?: (row: T) => boolean;
  variant?: 'default' | 'danger' | 'success' | 'warning';
}

export interface BulkAction {
  id: string;
  label: string;
  icon?: string;
  handler: (selectedIds: string[]) => void;
  variant?: 'default' | 'danger' | 'success' | 'warning';
}

export const DEFAULT_PAGE_SIZES = [10, 25, 50, 100];
