// apps/shell/src/test-setup.ts
/**
 * Jest test setup file.
 * Runs before each test file.
 */

import 'jest-preset-angular/setup-jest';

// Mock localStorage and sessionStorage
const storageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: (key: string): string | null => store[key] || null,
    setItem: (key: string, value: string): void => {
      store[key] = value.toString();
    },
    removeItem: (key: string): void => {
      delete store[key];
    },
    clear: (): void => {
      store = {};
    },
    get length(): number {
      return Object.keys(store).length;
    },
    key: (index: number): string | null => Object.keys(store)[index] || null,
  };
})();

Object.defineProperty(window, 'localStorage', { value: storageMock });
Object.defineProperty(window, 'sessionStorage', { value: storageMock });

// Mock matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: jest.fn().mockImplementation((query) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: jest.fn(),
    removeListener: jest.fn(),
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    dispatchEvent: jest.fn(),
  })),
});

// Reset storage between tests
beforeEach(() => {
  localStorage.clear();
  sessionStorage.clear();
});
