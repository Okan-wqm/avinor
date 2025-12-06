// apps/shell/src/app/core/guards/index.ts
/**
 * Route Guards
 *
 * Export all guards for easy importing in route configurations.
 */

export { authGuard } from './auth.guard';
export { noAuthGuard } from './no-auth.guard';
export { roleGuard, permissionGuard } from './role.guard';
