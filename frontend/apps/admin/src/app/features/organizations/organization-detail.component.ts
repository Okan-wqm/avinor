import { Component, inject, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { HttpClient } from '@angular/common/http';

@Component({
  selector: 'fts-organization-detail',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
    <div class="p-6 max-w-4xl mx-auto">
      <a routerLink="/admin/organizations" class="inline-flex items-center text-gray-600 dark:text-gray-400 hover:text-primary-600 mb-6">
        <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" /></svg>
        Back to Organizations
      </a>

      @if (org()) {
        <div class="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-sm mb-6">
          <h1 class="text-2xl font-bold text-gray-900 dark:text-white">{{ org()!.name }}</h1>
          <p class="text-gray-600 dark:text-gray-400">Code: {{ org()!.code }}</p>
          <div class="grid grid-cols-3 gap-6 mt-6 pt-6 border-t border-gray-200 dark:border-gray-700">
            <div><p class="text-sm text-gray-500">Users</p><p class="text-2xl font-bold text-primary-600">{{ org()!.user_count }}</p></div>
            <div><p class="text-sm text-gray-500">Aircraft</p><p class="text-2xl font-bold text-blue-600">{{ org()!.aircraft_count }}</p></div>
            <div><p class="text-sm text-gray-500">Status</p><p class="text-2xl font-bold capitalize">{{ org()!.status }}</p></div>
          </div>
        </div>
      }
    </div>
  `,
})
export class OrganizationDetailComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private http = inject(HttpClient);
  org = signal<{ name: string; code: string; user_count: number; aircraft_count: number; status: string } | null>(null);

  ngOnInit() {
    const id = this.route.snapshot.paramMap.get('id');
    if (id) {
      this.http.get<Record<string, unknown>>(`/api/v1/organizations/${id}/`).subscribe({
        next: (o) => this.org.set(o as ReturnType<typeof this.org>),
        error: () => this.org.set({ name: 'Oslo Flight Academy', code: 'OFA', user_count: 150, aircraft_count: 12, status: 'active' }),
      });
    }
  }
}
