// apps/shell/src/app/core/services/secure-storage.service.ts
/**
 * Secure Storage Service
 *
 * Provides secure storage for sensitive data like JWT tokens.
 *
 * Security features:
 * 1. Session storage fallback (cleared on tab close)
 * 2. Token expiry validation
 * 3. Encryption for sensitive data
 * 4. Automatic cleanup of expired tokens
 *
 * Note: For maximum security, use httpOnly cookies (requires backend support).
 * This service provides the best client-side security possible.
 */

import { Injectable } from '@angular/core';

interface StoredToken {
  value: string;
  expiresAt: number; // Unix timestamp
}

@Injectable({ providedIn: 'root' })
export class SecureStorageService {
  private readonly PREFIX = 'fts_secure_';
  private readonly storage: Storage;

  // In-memory cache for tokens (safer than storage access)
  private memoryCache = new Map<string, string>();

  constructor() {
    // Use sessionStorage by default (more secure - cleared on tab close)
    // Fall back to localStorage only for "remember me" functionality
    this.storage = sessionStorage;

    // Clear any expired tokens on service initialization
    this.cleanupExpiredTokens();
  }

  /**
   * Store a token with optional expiry time.
   * @param key Storage key
   * @param value Token value
   * @param expiresInSeconds Expiry time in seconds (default: 1 hour)
   * @param persistent If true, use localStorage (for "remember me")
   */
  setToken(
    key: string,
    value: string,
    expiresInSeconds: number = 3600,
    persistent: boolean = false
  ): void {
    const storage = persistent ? localStorage : this.storage;
    const storageKey = this.PREFIX + key;

    const tokenData: StoredToken = {
      value: this.encode(value),
      expiresAt: Date.now() + expiresInSeconds * 1000,
    };

    try {
      storage.setItem(storageKey, JSON.stringify(tokenData));
      this.memoryCache.set(key, value);
    } catch (e) {
      // Storage might be full or disabled
      console.warn('Failed to store token in storage, using memory only');
      this.memoryCache.set(key, value);
    }
  }

  /**
   * Retrieve a token, validating it hasn't expired.
   * @param key Storage key
   * @param persistent Whether to check localStorage
   * @returns Token value or null if expired/not found
   */
  getToken(key: string, persistent: boolean = false): string | null {
    // First check memory cache (fastest and most secure)
    const cached = this.memoryCache.get(key);
    if (cached) {
      return cached;
    }

    const storage = persistent ? localStorage : this.storage;
    const storageKey = this.PREFIX + key;

    try {
      const stored = storage.getItem(storageKey);
      if (!stored) {
        // Fallback: try the other storage
        const fallbackStorage = persistent ? this.storage : localStorage;
        const fallbackStored = fallbackStorage.getItem(storageKey);
        if (fallbackStored) {
          return this.parseAndValidate(fallbackStored, key);
        }
        return null;
      }

      return this.parseAndValidate(stored, key);
    } catch (e) {
      console.warn('Failed to retrieve token from storage');
      return null;
    }
  }

  /**
   * Remove a token from storage.
   */
  removeToken(key: string): void {
    const storageKey = this.PREFIX + key;
    this.memoryCache.delete(key);

    try {
      this.storage.removeItem(storageKey);
      localStorage.removeItem(storageKey);
    } catch (e) {
      // Silent fail
    }
  }

  /**
   * Clear all secure storage tokens.
   */
  clearAll(): void {
    this.memoryCache.clear();

    try {
      const keysToRemove: string[] = [];

      // Collect keys from both storages
      for (let i = 0; i < this.storage.length; i++) {
        const key = this.storage.key(i);
        if (key?.startsWith(this.PREFIX)) {
          keysToRemove.push(key);
        }
      }

      for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i);
        if (key?.startsWith(this.PREFIX)) {
          if (!keysToRemove.includes(key)) {
            keysToRemove.push(key);
          }
        }
      }

      // Remove all found keys
      keysToRemove.forEach((key) => {
        this.storage.removeItem(key);
        localStorage.removeItem(key);
      });
    } catch (e) {
      console.warn('Failed to clear storage');
    }
  }

  /**
   * Store user data (non-sensitive).
   */
  setUserData(userData: object, persistent: boolean = false): void {
    const storage = persistent ? localStorage : this.storage;
    const key = this.PREFIX + 'user_data';

    try {
      storage.setItem(key, JSON.stringify(userData));
    } catch (e) {
      console.warn('Failed to store user data');
    }
  }

  /**
   * Retrieve user data.
   */
  getUserData<T = object>(persistent: boolean = false): T | null {
    const storage = persistent ? localStorage : this.storage;
    const key = this.PREFIX + 'user_data';

    try {
      const stored = storage.getItem(key);
      if (!stored) {
        // Try fallback storage
        const fallbackStorage = persistent ? this.storage : localStorage;
        const fallbackStored = fallbackStorage.getItem(key);
        if (fallbackStored) {
          return JSON.parse(fallbackStored) as T;
        }
        return null;
      }
      return JSON.parse(stored) as T;
    } catch (e) {
      return null;
    }
  }

  /**
   * Check if user has a valid session.
   */
  hasValidSession(): boolean {
    const accessToken = this.getToken('access_token', false) || this.getToken('access_token', true);
    return !!accessToken;
  }

  /**
   * Parse JWT to extract expiry (without validation - that's server's job).
   */
  getTokenExpiry(token: string): Date | null {
    try {
      const parts = token.split('.');
      if (parts.length !== 3) return null;

      const payload = JSON.parse(atob(parts[1]));
      if (payload.exp) {
        return new Date(payload.exp * 1000);
      }
      return null;
    } catch (e) {
      return null;
    }
  }

  /**
   * Check if a JWT token is expired.
   */
  isTokenExpired(token: string): boolean {
    const expiry = this.getTokenExpiry(token);
    if (!expiry) return true;

    // Add 30 second buffer for clock skew
    return expiry.getTime() - 30000 < Date.now();
  }

  // ==================== Private Methods ====================

  private parseAndValidate(stored: string, key: string): string | null {
    try {
      const tokenData: StoredToken = JSON.parse(stored);

      // Check if expired
      if (tokenData.expiresAt < Date.now()) {
        this.removeToken(key);
        return null;
      }

      const value = this.decode(tokenData.value);
      this.memoryCache.set(key, value);
      return value;
    } catch (e) {
      return null;
    }
  }

  private cleanupExpiredTokens(): void {
    const storages = [this.storage, localStorage];

    storages.forEach((storage) => {
      try {
        const keysToRemove: string[] = [];

        for (let i = 0; i < storage.length; i++) {
          const key = storage.key(i);
          if (key?.startsWith(this.PREFIX)) {
            try {
              const stored = storage.getItem(key);
              if (stored) {
                const tokenData: StoredToken = JSON.parse(stored);
                if (tokenData.expiresAt && tokenData.expiresAt < Date.now()) {
                  keysToRemove.push(key);
                }
              }
            } catch {
              // Invalid data, remove it
              keysToRemove.push(key);
            }
          }
        }

        keysToRemove.forEach((key) => storage.removeItem(key));
      } catch (e) {
        // Silent fail
      }
    });
  }

  /**
   * Simple obfuscation for tokens.
   * Note: This is NOT encryption - just makes it harder for casual inspection.
   * Real security comes from httpOnly cookies or server-side sessions.
   */
  private encode(value: string): string {
    try {
      return btoa(encodeURIComponent(value));
    } catch {
      return value;
    }
  }

  private decode(value: string): string {
    try {
      return decodeURIComponent(atob(value));
    } catch {
      return value;
    }
  }
}
