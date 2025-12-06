// apps/shell/src/app/shared/components/card/card.component.ts
/**
 * Card Component
 *
 * A reusable card component with hover effects and various styles.
 */

import {
  Component,
  Input,
  Output,
  EventEmitter,
  ChangeDetectionStrategy,
} from '@angular/core';
import { CommonModule } from '@angular/common';

export type CardVariant = 'default' | 'elevated' | 'outlined' | 'filled';

@Component({
  selector: 'fts-card',
  standalone: true,
  imports: [CommonModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <article
      [class]="cardClasses"
      [attr.role]="clickable ? 'button' : 'article'"
      [attr.tabindex]="clickable ? 0 : null"
      (click)="onClick($event)"
      (keydown.enter)="onClick($event)"
      (keydown.space)="onClick($event)"
    >
      <!-- Header -->
      @if (hasHeader) {
        <header
          class="px-4 py-3 border-b border-gray-200 dark:border-gray-700"
          [class.bg-gray-50]="variant !== 'filled'"
          [class.dark:bg-gray-800/50]="variant !== 'filled'"
        >
          <ng-content select="[card-header]" />
        </header>
      }

      <!-- Body -->
      <div [class]="bodyClasses">
        <ng-content />
      </div>

      <!-- Footer -->
      @if (hasFooter) {
        <footer
          class="px-4 py-3 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50"
        >
          <ng-content select="[card-footer]" />
        </footer>
      }
    </article>
  `,
})
export class CardComponent {
  @Input() variant: CardVariant = 'default';
  @Input() padding: 'none' | 'sm' | 'md' | 'lg' = 'md';
  @Input() clickable = false;
  @Input() hasHeader = false;
  @Input() hasFooter = false;
  @Input() hoverable = true;

  @Output() cardClick = new EventEmitter<Event>();

  get cardClasses(): string {
    const base = 'rounded-lg overflow-hidden transition-all duration-200';

    const variants: Record<CardVariant, string> = {
      default: `
        bg-white dark:bg-gray-800
        shadow-md
        ${this.hoverable ? 'hover:shadow-lg' : ''}
      `,
      elevated: `
        bg-white dark:bg-gray-800
        shadow-lg
        ${this.hoverable ? 'hover:shadow-xl hover:-translate-y-0.5' : ''}
      `,
      outlined: `
        bg-white dark:bg-gray-800
        border border-gray-200 dark:border-gray-700
        ${this.hoverable ? 'hover:border-primary-300 dark:hover:border-primary-600' : ''}
      `,
      filled: `
        bg-gray-100 dark:bg-gray-700
        ${this.hoverable ? 'hover:bg-gray-200 dark:hover:bg-gray-600' : ''}
      `,
    };

    const clickableClass = this.clickable
      ? 'cursor-pointer focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2'
      : '';

    return `${base} ${variants[this.variant]} ${clickableClass}`.trim();
  }

  get bodyClasses(): string {
    const paddings: Record<string, string> = {
      none: '',
      sm: 'p-3',
      md: 'p-4',
      lg: 'p-6',
    };
    return paddings[this.padding];
  }

  onClick(event: Event): void {
    if (this.clickable) {
      this.cardClick.emit(event);
    }
  }
}
