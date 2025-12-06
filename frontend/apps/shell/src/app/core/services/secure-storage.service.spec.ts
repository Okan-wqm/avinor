// apps/shell/src/app/core/services/secure-storage.service.spec.ts
/**
 * Secure Storage Service Tests
 *
 * Tests for the secure token storage service.
 */

import { TestBed } from '@angular/core/testing';
import { SecureStorageService } from './secure-storage.service';

describe('SecureStorageService', () => {
  let service: SecureStorageService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [SecureStorageService],
    });

    service = TestBed.inject(SecureStorageService);
    localStorage.clear();
    sessionStorage.clear();
  });

  afterEach(() => {
    localStorage.clear();
    sessionStorage.clear();
  });

  describe('setToken', () => {
    it('should store token in session storage by default', () => {
      service.setToken('access_token', 'test-token', 3600);

      const storedValue = sessionStorage.getItem('fts_secure_access_token');
      expect(storedValue).toBeTruthy();
    });

    it('should store token in local storage when persistent', () => {
      service.setToken('access_token', 'test-token', 3600, true);

      const storedValue = localStorage.getItem('fts_secure_access_token');
      expect(storedValue).toBeTruthy();
    });
  });

  describe('getToken', () => {
    it('should retrieve stored token', () => {
      service.setToken('access_token', 'test-token', 3600);

      const token = service.getToken('access_token');
      expect(token).toBe('test-token');
    });

    it('should return null for non-existent token', () => {
      const token = service.getToken('non_existent');
      expect(token).toBeNull();
    });

    it('should return null for expired token', () => {
      // Store token with 0 second expiry
      service.setToken('access_token', 'test-token', 0);

      // Wait a tick to ensure expiry
      const token = service.getToken('access_token');
      expect(token).toBeNull();
    });
  });

  describe('removeToken', () => {
    it('should remove token from storage', () => {
      service.setToken('access_token', 'test-token', 3600);
      expect(service.getToken('access_token')).toBe('test-token');

      service.removeToken('access_token');
      expect(service.getToken('access_token')).toBeNull();
    });
  });

  describe('clearAll', () => {
    it('should clear all secure storage tokens', () => {
      service.setToken('access_token', 'token1', 3600);
      service.setToken('refresh_token', 'token2', 3600);
      service.setUserData({ name: 'Test' });

      service.clearAll();

      expect(service.getToken('access_token')).toBeNull();
      expect(service.getToken('refresh_token')).toBeNull();
      expect(service.getUserData()).toBeNull();
    });
  });

  describe('setUserData / getUserData', () => {
    it('should store and retrieve user data', () => {
      const userData = { id: '123', name: 'Test User' };
      service.setUserData(userData);

      const retrieved = service.getUserData();
      expect(retrieved).toEqual(userData);
    });
  });

  describe('hasValidSession', () => {
    it('should return true when access token exists', () => {
      service.setToken('access_token', 'test-token', 3600);
      expect(service.hasValidSession()).toBe(true);
    });

    it('should return false when no access token', () => {
      expect(service.hasValidSession()).toBe(false);
    });
  });

  describe('isTokenExpired', () => {
    it('should return true for expired JWT', () => {
      // Create an expired JWT (exp in the past)
      const expiredPayload = { exp: Math.floor(Date.now() / 1000) - 3600 };
      const expiredToken = `header.${btoa(JSON.stringify(expiredPayload))}.signature`;

      expect(service.isTokenExpired(expiredToken)).toBe(true);
    });

    it('should return false for valid JWT', () => {
      // Create a valid JWT (exp in the future)
      const validPayload = { exp: Math.floor(Date.now() / 1000) + 3600 };
      const validToken = `header.${btoa(JSON.stringify(validPayload))}.signature`;

      expect(service.isTokenExpired(validToken)).toBe(false);
    });

    it('should return true for invalid token format', () => {
      expect(service.isTokenExpired('invalid-token')).toBe(true);
    });
  });

  describe('getTokenExpiry', () => {
    it('should return expiry date for valid JWT', () => {
      const expTime = Math.floor(Date.now() / 1000) + 3600;
      const payload = { exp: expTime };
      const token = `header.${btoa(JSON.stringify(payload))}.signature`;

      const expiry = service.getTokenExpiry(token);
      expect(expiry).toBeInstanceOf(Date);
      expect(Math.floor(expiry!.getTime() / 1000)).toBe(expTime);
    });

    it('should return null for invalid token', () => {
      expect(service.getTokenExpiry('invalid')).toBeNull();
    });
  });
});
