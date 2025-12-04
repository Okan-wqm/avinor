import { Component, inject, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { HttpClient } from '@angular/common/http';

interface Organization {
  id: string;
  name: string;
  code: string;
  type: 'flight_school' | 'aero_club' | 'commercial';
  status: 'active' | 'inactive';
  user_count: number;
  aircraft_count: number;
  created_at: string;
}

@Component({
  selector: 'fts-organization-list',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
    <div class="p-6">
      <div class="flex justify-between items-center mb-6">
        <div>
          <h1 class="text-2xl font-bold text-gray-900 dark:text-white">Organizations</h1>
          <p class="text-gray-600 dark:text-gray-400">Manage flight schools and clubs</p>
        </div>
        <button class="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700">+ Add Organization</button>
      </div>

      <div class="bg-white dark:bg-gray-800 rounded-lg shadow-sm overflow-hidden">
        <table class="w-full">
          <thead class="bg-gray-50 dark:bg-gray-700">
            <tr>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Organization</th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Type</th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Users</th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Aircraft</th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Status</th>
              <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Actions</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-200 dark:divide-gray-700">
            @for (org of organizations(); track org.id) {
              <tr class="hover:bg-gray-50 dark:hover:bg-gray-700/50">
                <td class="px-6 py-4">
                  <p class="font-medium text-gray-900 dark:text-white">{{ org.name }}</p>
                  <p class="text-sm text-gray-500">{{ org.code }}</p>
                </td>
                <td class="px-6 py-4"><span class="capitalize text-gray-700 dark:text-gray-300">{{ org.type.replace('_', ' ') }}</span></td>
                <td class="px-6 py-4 text-gray-700 dark:text-gray-300">{{ org.user_count }}</td>
                <td class="px-6 py-4 text-gray-700 dark:text-gray-300">{{ org.aircraft_count }}</td>
                <td class="px-6 py-4">
                  <span [class]="'px-2 py-1 text-xs rounded capitalize ' + (org.status === 'active' ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800')">{{ org.status }}</span>
                </td>
                <td class="px-6 py-4 text-right">
                  <a [routerLink]="['/admin/organizations', org.id]" class="text-primary-600 hover:text-primary-700 font-medium text-sm">View</a>
                </td>
              </tr>
            }
          </tbody>
        </table>
      </div>
    </div>
  `,
})
export class OrganizationListComponent implements OnInit {
  private http = inject(HttpClient);
  organizations = signal<Organization[]>([]);

  ngOnInit() {
    this.http.get<{ results: Organization[] }>('/api/v1/organizations/').subscribe({
      next: (r) => this.organizations.set(r.results || []),
      error: () => this.organizations.set([
        { id: '1', name: 'Oslo Flight Academy', code: 'OFA', type: 'flight_school', status: 'active', user_count: 150, aircraft_count: 12, created_at: '2020-01-15' },
        { id: '2', name: 'Bergen Aero Club', code: 'BAC', type: 'aero_club', status: 'active', user_count: 85, aircraft_count: 6, created_at: '2019-06-20' },
        { id: '3', name: 'Nordic Aviation Training', code: 'NAT', type: 'commercial', status: 'active', user_count: 300, aircraft_count: 25, created_at: '2018-03-10' },
      ]),
    });
  }
}
