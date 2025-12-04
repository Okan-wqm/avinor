import { Component, inject, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { FormsModule } from '@angular/forms';

interface User {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  role: 'student' | 'instructor' | 'staff' | 'admin';
  status: 'active' | 'inactive' | 'suspended';
  created_at: string;
  last_login?: string;
  avatar_url?: string;
}

@Component({
  selector: 'fts-user-list',
  standalone: true,
  imports: [CommonModule, RouterLink, FormsModule],
  template: `
    <div class="p-6">
      <div class="flex justify-between items-center mb-6">
        <div>
          <h1 class="text-2xl font-bold text-gray-900 dark:text-white">Users</h1>
          <p class="text-gray-600 dark:text-gray-400">Manage system users and permissions</p>
        </div>
        <a
          routerLink="/admin/users/new"
          class="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
        >
          + Add User
        </a>
      </div>

      <!-- Filters -->
      <div class="bg-white dark:bg-gray-800 rounded-lg p-4 mb-6 shadow-sm">
        <div class="flex flex-wrap gap-4">
          <div class="flex-1 min-w-[200px]">
            <input
              type="text"
              placeholder="Search users..."
              [(ngModel)]="searchQuery"
              (ngModelChange)="filterUsers()"
              class="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            />
          </div>
          <select
            [(ngModel)]="roleFilter"
            (ngModelChange)="filterUsers()"
            class="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
          >
            <option value="">All Roles</option>
            <option value="student">Student</option>
            <option value="instructor">Instructor</option>
            <option value="staff">Staff</option>
            <option value="admin">Admin</option>
          </select>
          <select
            [(ngModel)]="statusFilter"
            (ngModelChange)="filterUsers()"
            class="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
          >
            <option value="">All Status</option>
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
            <option value="suspended">Suspended</option>
          </select>
        </div>
      </div>

      <!-- User table -->
      <div class="bg-white dark:bg-gray-800 rounded-lg shadow-sm overflow-hidden">
        <table class="w-full">
          <thead class="bg-gray-50 dark:bg-gray-700">
            <tr>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                User
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                Role
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                Status
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                Created
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                Last Login
              </th>
              <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-200 dark:divide-gray-700">
            @for (user of filteredUsers(); track user.id) {
              <tr class="hover:bg-gray-50 dark:hover:bg-gray-700/50">
                <td class="px-6 py-4 whitespace-nowrap">
                  <div class="flex items-center">
                    <div class="h-10 w-10 rounded-full bg-primary-100 dark:bg-primary-900 flex items-center justify-center">
                      <span class="text-primary-600 dark:text-primary-400 font-medium">
                        {{ user.first_name.charAt(0) }}{{ user.last_name.charAt(0) }}
                      </span>
                    </div>
                    <div class="ml-4">
                      <p class="font-medium text-gray-900 dark:text-white">
                        {{ user.first_name }} {{ user.last_name }}
                      </p>
                      <p class="text-sm text-gray-500">{{ user.email }}</p>
                    </div>
                  </div>
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                  <span
                    [class]="'px-2 py-1 text-xs font-medium rounded capitalize ' + getRoleClass(user.role)"
                  >
                    {{ user.role }}
                  </span>
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                  <span
                    [class]="'px-2 py-1 text-xs font-medium rounded capitalize ' + getStatusClass(user.status)"
                  >
                    {{ user.status }}
                  </span>
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                  {{ user.created_at | date:'mediumDate' }}
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                  {{ user.last_login ? (user.last_login | date:'medium') : 'Never' }}
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-right">
                  <div class="flex justify-end gap-2">
                    <a
                      [routerLink]="['/admin/users', user.id]"
                      class="text-primary-600 hover:text-primary-700 text-sm font-medium"
                    >
                      View
                    </a>
                    <a
                      [routerLink]="['/admin/users', user.id, 'edit']"
                      class="text-gray-600 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300 text-sm font-medium"
                    >
                      Edit
                    </a>
                  </div>
                </td>
              </tr>
            } @empty {
              <tr>
                <td colspan="6" class="px-6 py-12 text-center text-gray-500">
                  No users found matching your criteria
                </td>
              </tr>
            }
          </tbody>
        </table>

        <!-- Pagination -->
        <div class="px-6 py-4 border-t border-gray-200 dark:border-gray-700 flex justify-between items-center">
          <p class="text-sm text-gray-500">
            Showing {{ filteredUsers().length }} of {{ users().length }} users
          </p>
          <div class="flex gap-2">
            <button class="px-3 py-1 border border-gray-300 dark:border-gray-600 rounded text-sm disabled:opacity-50">
              Previous
            </button>
            <button class="px-3 py-1 border border-gray-300 dark:border-gray-600 rounded text-sm disabled:opacity-50">
              Next
            </button>
          </div>
        </div>
      </div>
    </div>
  `,
})
export class UserListComponent implements OnInit {
  private http = inject(HttpClient);

  users = signal<User[]>([]);
  loading = signal(true);

  searchQuery = '';
  roleFilter = '';
  statusFilter = '';

  filteredUsers = signal<User[]>([]);

  ngOnInit() {
    this.loadUsers();
  }

  loadUsers() {
    this.loading.set(true);
    this.http.get<{ results: User[] }>('/api/v1/users/').subscribe({
      next: (response) => {
        this.users.set(response.results || []);
        this.filterUsers();
        this.loading.set(false);
      },
      error: () => {
        // Mock data
        this.users.set([
          {
            id: '1',
            email: 'john.pilot@example.com',
            first_name: 'John',
            last_name: 'Pilot',
            role: 'student',
            status: 'active',
            created_at: '2024-01-15',
            last_login: '2024-12-03T14:30:00Z',
          },
          {
            id: '2',
            email: 'jane.instructor@example.com',
            first_name: 'Jane',
            last_name: 'Instructor',
            role: 'instructor',
            status: 'active',
            created_at: '2023-06-20',
            last_login: '2024-12-04T09:15:00Z',
          },
          {
            id: '3',
            email: 'mike.admin@example.com',
            first_name: 'Mike',
            last_name: 'Admin',
            role: 'admin',
            status: 'active',
            created_at: '2023-01-10',
            last_login: '2024-12-04T08:00:00Z',
          },
          {
            id: '4',
            email: 'sarah.staff@example.com',
            first_name: 'Sarah',
            last_name: 'Staff',
            role: 'staff',
            status: 'active',
            created_at: '2023-09-05',
            last_login: '2024-12-02T16:45:00Z',
          },
          {
            id: '5',
            email: 'tom.student@example.com',
            first_name: 'Tom',
            last_name: 'Student',
            role: 'student',
            status: 'inactive',
            created_at: '2024-03-22',
            last_login: '2024-08-15T11:20:00Z',
          },
        ]);
        this.filterUsers();
        this.loading.set(false);
      },
    });
  }

  filterUsers() {
    let filtered = this.users();

    if (this.searchQuery) {
      const query = this.searchQuery.toLowerCase();
      filtered = filtered.filter(
        (u) =>
          u.first_name.toLowerCase().includes(query) ||
          u.last_name.toLowerCase().includes(query) ||
          u.email.toLowerCase().includes(query)
      );
    }

    if (this.roleFilter) {
      filtered = filtered.filter((u) => u.role === this.roleFilter);
    }

    if (this.statusFilter) {
      filtered = filtered.filter((u) => u.status === this.statusFilter);
    }

    this.filteredUsers.set(filtered);
  }

  getRoleClass(role: string): string {
    const classes: Record<string, string> = {
      student: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
      instructor: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200',
      staff: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
      admin: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
    };
    return classes[role] || 'bg-gray-100 text-gray-800';
  }

  getStatusClass(status: string): string {
    const classes: Record<string, string> = {
      active: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
      inactive: 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300',
      suspended: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
    };
    return classes[status] || 'bg-gray-100 text-gray-800';
  }
}
