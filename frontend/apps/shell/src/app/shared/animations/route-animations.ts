// apps/shell/src/app/shared/animations/route-animations.ts
/**
 * Route Transition Animations
 *
 * Provides smooth page transitions for improved UX.
 * Uses Angular animations with reduced motion support.
 */

import {
  trigger,
  transition,
  style,
  query,
  animate,
  group,
  animateChild,
  state,
} from '@angular/animations';

/**
 * Fade animation for route transitions
 */
export const fadeAnimation = trigger('routeAnimations', [
  transition('* <=> *', [
    style({ position: 'relative' }),
    query(
      ':enter, :leave',
      [
        style({
          position: 'absolute',
          top: 0,
          left: 0,
          width: '100%',
        }),
      ],
      { optional: true }
    ),
    query(':enter', [style({ opacity: 0 })], { optional: true }),
    query(':leave', animateChild(), { optional: true }),
    group([
      query(
        ':leave',
        [animate('200ms ease-out', style({ opacity: 0 }))],
        { optional: true }
      ),
      query(
        ':enter',
        [animate('300ms ease-out', style({ opacity: 1 }))],
        { optional: true }
      ),
    ]),
  ]),
]);

/**
 * Slide animation for route transitions
 */
export const slideAnimation = trigger('routeAnimations', [
  transition('* => *', [
    style({ position: 'relative' }),
    query(
      ':enter, :leave',
      [
        style({
          position: 'absolute',
          top: 0,
          left: 0,
          width: '100%',
        }),
      ],
      { optional: true }
    ),
    query(':enter', [style({ transform: 'translateX(100%)', opacity: 0 })], {
      optional: true,
    }),
    query(':leave', animateChild(), { optional: true }),
    group([
      query(
        ':leave',
        [
          animate(
            '250ms ease-out',
            style({ transform: 'translateX(-100%)', opacity: 0 })
          ),
        ],
        { optional: true }
      ),
      query(
        ':enter',
        [
          animate(
            '300ms ease-out',
            style({ transform: 'translateX(0)', opacity: 1 })
          ),
        ],
        { optional: true }
      ),
    ]),
  ]),
]);

/**
 * Scale fade animation for route transitions
 */
export const scaleFadeAnimation = trigger('routeAnimations', [
  transition('* <=> *', [
    style({ position: 'relative' }),
    query(
      ':enter, :leave',
      [
        style({
          position: 'absolute',
          top: 0,
          left: 0,
          width: '100%',
        }),
      ],
      { optional: true }
    ),
    query(
      ':enter',
      [style({ opacity: 0, transform: 'scale(0.98)' })],
      { optional: true }
    ),
    query(':leave', animateChild(), { optional: true }),
    group([
      query(
        ':leave',
        [
          animate(
            '200ms ease-out',
            style({ opacity: 0, transform: 'scale(1.02)' })
          ),
        ],
        { optional: true }
      ),
      query(
        ':enter',
        [
          animate(
            '300ms ease-out',
            style({ opacity: 1, transform: 'scale(1)' })
          ),
        ],
        { optional: true }
      ),
    ]),
  ]),
]);
