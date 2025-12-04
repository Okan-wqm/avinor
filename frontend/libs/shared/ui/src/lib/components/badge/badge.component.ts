import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'fts-badge',
  standalone: true,
  imports: [CommonModule],
  template: `<span [class]="badgeClasses"><ng-content></ng-content></span>`,
})
export class BadgeComponent {
  @Input() variant: 'primary' | 'success' | 'warning' | 'danger' | 'info' | 'gray' = 'gray';
  @Input() size: 'sm' | 'md' = 'md';

  get badgeClasses(): string {
    const base = 'inline-flex items-center font-medium rounded-full';

    const variants: Record<string, string> = {
      primary: 'bg-primary-100 text-primary-800 dark:bg-primary-900 dark:text-primary-200',
      success: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
      warning: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
      danger: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
      info: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
      gray: 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300',
    };

    const sizes: Record<string, string> = {
      sm: 'px-2 py-0.5 text-xs',
      md: 'px-2.5 py-1 text-sm',
    };

    return `${base} ${variants[this.variant]} ${sizes[this.size]}`;
  }
}
