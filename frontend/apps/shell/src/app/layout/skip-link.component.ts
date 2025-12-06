// apps/shell/src/app/layout/skip-link.component.ts
/**
 * Skip Link Component
 *
 * Provides a skip-to-content link for keyboard users.
 * WCAG 2.1 AA requirement for keyboard navigation.
 */

import { Component, ChangeDetectionStrategy } from '@angular/core';

@Component({
  selector: 'fts-skip-link',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <a
      href="#main-content"
      class="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-[100] focus:px-4 focus:py-2 focus:bg-primary-600 focus:text-white focus:rounded-lg focus:shadow-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
    >
      Skip to main content
    </a>
  `,
})
export class SkipLinkComponent {}
