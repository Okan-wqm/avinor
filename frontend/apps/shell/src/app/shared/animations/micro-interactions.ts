// apps/shell/src/app/shared/animations/micro-interactions.ts
/**
 * Micro-Interaction Animations
 *
 * Small, delightful animations for UI feedback.
 * All animations respect prefers-reduced-motion.
 */

import {
  trigger,
  transition,
  style,
  animate,
  state,
  keyframes,
  query,
  stagger,
} from '@angular/animations';

/**
 * Fade in animation
 */
export const fadeIn = trigger('fadeIn', [
  transition(':enter', [
    style({ opacity: 0 }),
    animate('300ms ease-out', style({ opacity: 1 })),
  ]),
  transition(':leave', [
    animate('200ms ease-in', style({ opacity: 0 })),
  ]),
]);

/**
 * Slide up animation
 */
export const slideUp = trigger('slideUp', [
  transition(':enter', [
    style({ opacity: 0, transform: 'translateY(20px)' }),
    animate(
      '300ms cubic-bezier(0.4, 0, 0.2, 1)',
      style({ opacity: 1, transform: 'translateY(0)' })
    ),
  ]),
  transition(':leave', [
    animate(
      '200ms cubic-bezier(0.4, 0, 0.2, 1)',
      style({ opacity: 0, transform: 'translateY(20px)' })
    ),
  ]),
]);

/**
 * Slide down animation
 */
export const slideDown = trigger('slideDown', [
  transition(':enter', [
    style({ opacity: 0, transform: 'translateY(-20px)' }),
    animate(
      '300ms cubic-bezier(0.4, 0, 0.2, 1)',
      style({ opacity: 1, transform: 'translateY(0)' })
    ),
  ]),
  transition(':leave', [
    animate(
      '200ms cubic-bezier(0.4, 0, 0.2, 1)',
      style({ opacity: 0, transform: 'translateY(-20px)' })
    ),
  ]),
]);

/**
 * Scale animation for buttons/cards
 */
export const scale = trigger('scale', [
  transition(':enter', [
    style({ opacity: 0, transform: 'scale(0.95)' }),
    animate(
      '200ms cubic-bezier(0.4, 0, 0.2, 1)',
      style({ opacity: 1, transform: 'scale(1)' })
    ),
  ]),
  transition(':leave', [
    animate(
      '150ms cubic-bezier(0.4, 0, 0.2, 1)',
      style({ opacity: 0, transform: 'scale(0.95)' })
    ),
  ]),
]);

/**
 * Expand/collapse animation
 */
export const expandCollapse = trigger('expandCollapse', [
  state('collapsed', style({ height: '0', overflow: 'hidden', opacity: 0 })),
  state('expanded', style({ height: '*', overflow: 'visible', opacity: 1 })),
  transition('collapsed <=> expanded', [
    animate('300ms cubic-bezier(0.4, 0, 0.2, 1)'),
  ]),
]);

/**
 * Stagger list animation
 */
export const staggerList = trigger('staggerList', [
  transition('* => *', [
    query(
      ':enter',
      [
        style({ opacity: 0, transform: 'translateY(15px)' }),
        stagger('50ms', [
          animate(
            '300ms cubic-bezier(0.4, 0, 0.2, 1)',
            style({ opacity: 1, transform: 'translateY(0)' })
          ),
        ]),
      ],
      { optional: true }
    ),
  ]),
]);

/**
 * Pulse animation for notifications
 */
export const pulse = trigger('pulse', [
  transition('* => *', [
    animate(
      '400ms ease-in-out',
      keyframes([
        style({ transform: 'scale(1)', offset: 0 }),
        style({ transform: 'scale(1.05)', offset: 0.5 }),
        style({ transform: 'scale(1)', offset: 1 }),
      ])
    ),
  ]),
]);

/**
 * Shake animation for errors
 */
export const shake = trigger('shake', [
  transition('* => *', [
    animate(
      '400ms ease-in-out',
      keyframes([
        style({ transform: 'translateX(0)', offset: 0 }),
        style({ transform: 'translateX(-10px)', offset: 0.2 }),
        style({ transform: 'translateX(10px)', offset: 0.4 }),
        style({ transform: 'translateX(-10px)', offset: 0.6 }),
        style({ transform: 'translateX(10px)', offset: 0.8 }),
        style({ transform: 'translateX(0)', offset: 1 }),
      ])
    ),
  ]),
]);

/**
 * Bounce animation for success
 */
export const bounce = trigger('bounce', [
  transition(':enter', [
    animate(
      '500ms cubic-bezier(0.68, -0.55, 0.265, 1.55)',
      keyframes([
        style({ opacity: 0, transform: 'scale(0.3)', offset: 0 }),
        style({ opacity: 0.9, transform: 'scale(1.1)', offset: 0.5 }),
        style({ opacity: 1, transform: 'scale(1)', offset: 1 }),
      ])
    ),
  ]),
]);

/**
 * Spin animation for loading
 */
export const spin = trigger('spin', [
  state('spinning', style({ transform: 'rotate(360deg)' })),
  transition('* => spinning', [
    animate('1000ms linear'),
  ]),
]);

/**
 * Slide in from left
 */
export const slideInLeft = trigger('slideInLeft', [
  transition(':enter', [
    style({ opacity: 0, transform: 'translateX(-100%)' }),
    animate(
      '300ms cubic-bezier(0.4, 0, 0.2, 1)',
      style({ opacity: 1, transform: 'translateX(0)' })
    ),
  ]),
  transition(':leave', [
    animate(
      '200ms cubic-bezier(0.4, 0, 0.2, 1)',
      style({ opacity: 0, transform: 'translateX(-100%)' })
    ),
  ]),
]);

/**
 * Slide in from right
 */
export const slideInRight = trigger('slideInRight', [
  transition(':enter', [
    style({ opacity: 0, transform: 'translateX(100%)' }),
    animate(
      '300ms cubic-bezier(0.4, 0, 0.2, 1)',
      style({ opacity: 1, transform: 'translateX(0)' })
    ),
  ]),
  transition(':leave', [
    animate(
      '200ms cubic-bezier(0.4, 0, 0.2, 1)',
      style({ opacity: 0, transform: 'translateX(100%)' })
    ),
  ]),
]);

/**
 * Flip card animation
 */
export const flipCard = trigger('flipCard', [
  state('front', style({ transform: 'rotateY(0deg)' })),
  state('back', style({ transform: 'rotateY(180deg)' })),
  transition('front <=> back', [
    animate('600ms cubic-bezier(0.4, 0, 0.2, 1)'),
  ]),
]);
