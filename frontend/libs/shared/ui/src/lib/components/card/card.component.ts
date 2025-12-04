import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'fts-card',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div [class]="cardClasses">
      @if (title) {
        <div class="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <h3 class="text-lg font-semibold text-gray-900 dark:text-white">{{ title }}</h3>
          @if (subtitle) {
            <p class="text-sm text-gray-500 mt-1">{{ subtitle }}</p>
          }
        </div>
      }
      <div [class]="padding ? 'p-6' : ''">
        <ng-content></ng-content>
      </div>
    </div>
  `,
})
export class CardComponent {
  @Input() title?: string;
  @Input() subtitle?: string;
  @Input() padding = true;
  @Input() hoverable = false;

  get cardClasses(): string {
    const base = 'bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700';
    return `${base} ${this.hoverable ? 'hover:shadow-md transition-shadow cursor-pointer' : ''}`;
  }
}
