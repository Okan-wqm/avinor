// jest.preset.js
const nxPreset = require('@nx/jest/preset').default;

module.exports = {
  ...nxPreset,
  testEnvironment: 'jsdom',
  moduleFileExtensions: ['ts', 'tsx', 'js', 'jsx', 'json', 'node', 'mjs'],
  coverageReporters: ['html', 'lcov', 'text-summary'],
  collectCoverageFrom: [
    '**/*.ts',
    '!**/*.module.ts',
    '!**/node_modules/**',
    '!**/main.ts',
    '!**/*.d.ts',
    '!**/environments/**',
  ],
};
