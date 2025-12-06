// apps/shell/src/app/shared/components/button/button.component.ts
/**
 * Button Component
 *
 * A reusable button component with various styles, sizes, and states.
 * Includes loading state and micro-interactions.
 */

import {
  Component,
  Input,
  Output,
  EventEmitter,
  ChangeDetectionStrategy,
  HostBinding,
} from '@angular/core';
import { CommonModule } from '@angular/common';

export type ButtonVariant = 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger' | 'success';
export type ButtonSize = 'sm' | 'md' | 'lg';

@Component({
  selector: 'fts-button',
  standalone: true,
  imports: [CommonModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <button
      [type]="type"
      [disabled]="disabled || loading"
      [class]="buttonClasses"
      [attr.aria-busy]="loading"
      [attr.aria-disabled]="disabled"
      (click)="handleClick($event)"
    >
      <!-- Loading Spinner -->
      @if (loading) {
        <svg
          class="animate-spin -ml-1 mr-2 h-4 w-4"
          fill="none"
          viewBox="0 0 24 24"
          aria-hidden="true"
        >
          <circle
            class="opacity-25"
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            stroke-width="4"
          ></circle>
          <path
            class="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
          ></path>
        </svg>
      }

      <!-- Icon (left) -->
      @if (iconLeft && !loading) {
        <span class="mr-2" aria-hidden="true">
          <ng-content select="[icon-left]" />
        </span>
      }

      <!-- Button Content -->
      <span [class.sr-only]="loading && loadingText">
        <ng-content />
      </span>

      <!-- Loading Text -->
      @if (loading && loadingText) {
        <span>{{ loadingText }}</span>
      }

      <!-- Icon (right) -->
      @if (iconRight && !loading) {
        <span class="ml-2" aria-hidden="true">
          <ng-content select="[icon-right]" />
        </span>
      }
    </button>
  `,
})
export class ButtonComponent {
  @Input() variant: ButtonVariant = 'primary';
  @Input() size: ButtonSize = 'md';
  @Input() type: 'button' | 'submit' | 'reset' = 'button';
  @Input() disabled = false;
  @Input() loading = false;
  @Input() loadingText?: string;
  @Input() fullWidth = false;
  @Input() iconLeft = false;
  @Input() iconRight = false;
  @Input() rounded = false;

  @Output() buttonClick = new EventEmitter<MouseEvent>();

  get buttonClasses(): string {
    const base = `
      inline-flex items-center justify-center font-medium
      transition-all duration-200 ease-in-out
      focus:outline-none focus:ring-2 focus:ring-offset-2
      disabled:opacity-50 disabled:cursor-not-allowed
      active:scale-[0.98]
    `;

    const variants: Record<ButtonVariant, string> = {
      primary: `
        bg-primary-600 text-white
        hover:bg-primary-700 hover:shadow-md
        focus:ring-primary-500
      `,
      secondary: `
        bg-gray-600 text-white
        hover:bg-gray-700 hover:shadow-md
        focus:ring-gray-500
      `,
      outline: `
        border-2 border-primary-600 text-primary-600
        hover:bg-primary-50 dark:hover:bg-primary-900/20
        focus:ring-primary-500
      `,
      ghost: `
        text-gray-700 dark:text-gray-300
        hover:bg-gray-100 dark:hover:bg-gray-700
        focus:ring-gray-500
      `,
      danger: `
        bg-red-600 text-white
        hover:bg-red-700 hover:shadow-md
        focus:ring-red-500
      `,
      success: `
        bg-green-600 text-white
        hover:bg-green-700 hover:shadow-md
        focus:ring-green-500
      `,
    };

    const sizes: Record<ButtonSize, string> = {
      sm: 'px-3 py-1.5 text-sm',
      md: 'px-4 py-2 text-sm',
      lg: 'px-6 py-3 text-base',
    };

    const width = this.fullWidth ? 'w-full' : '';
    const borderRadius = this.rounded ? 'rounded-full' : 'rounded-lg';

    return `${base} ${variants[this.variant]} ${sizes[this.size]} ${width} ${borderRadius}`.trim();
  }

  handleClick(event: MouseEvent): void {
    if (!this.disabled && !this.loading) {
      this.buttonClick.emit(event);
    }
  }
}
