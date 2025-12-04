import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'fts-loading',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div [class]="'flex items-center justify-center ' + (fullScreen ? 'h-screen' : 'py-12')">
      <div class="text-center">
        <svg
          [class]="'animate-spin mx-auto text-primary-600 ' + sizeClasses"
          fill="none"
          viewBox="0 0 24 24"
        >
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg>
        @if (message) {
          <p class="mt-4 text-gray-500 dark:text-gray-400">{{ message }}</p>
        }
      </div>
    </div>
  `,
})
export class LoadingComponent {
  @Input() size: 'sm' | 'md' | 'lg' = 'md';
  @Input() message?: string;
  @Input() fullScreen = false;

  get sizeClasses(): string {
    const sizes: Record<string, string> = {
      sm: 'h-6 w-6',
      md: 'h-10 w-10',
      lg: 'h-16 w-16',
    };
    return sizes[this.size];
  }
}
