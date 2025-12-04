import { Injectable, signal, effect } from '@angular/core';

@Injectable({ providedIn: 'root' })
export class ThemeService {
  private darkMode = signal(this.loadTheme());

  isDarkMode = this.darkMode.asReadonly();

  constructor() {
    // Apply theme on change
    effect(() => {
      const isDark = this.darkMode();
      document.documentElement.classList.toggle('dark', isDark);
      localStorage.setItem('fts_theme', isDark ? 'dark' : 'light');
    });
  }

  toggleTheme(): void {
    this.darkMode.update((v) => !v);
  }

  setTheme(dark: boolean): void {
    this.darkMode.set(dark);
  }

  private loadTheme(): boolean {
    const saved = localStorage.getItem('fts_theme');
    if (saved) {
      return saved === 'dark';
    }
    // Default to system preference
    return window.matchMedia('(prefers-color-scheme: dark)').matches;
  }
}
