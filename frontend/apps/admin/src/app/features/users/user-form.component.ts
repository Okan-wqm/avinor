import { Component, inject, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';

@Component({
  selector: 'fts-user-form',
  standalone: true,
  imports: [CommonModule, RouterLink, ReactiveFormsModule],
  template: `
    <div class="p-6 max-w-2xl mx-auto">
      <a
        routerLink="/admin/users"
        class="inline-flex items-center text-gray-600 dark:text-gray-400 hover:text-primary-600 mb-6"
      >
        <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
        </svg>
        Back to Users
      </a>

      <div class="bg-white dark:bg-gray-800 rounded-lg shadow-sm">
        <div class="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <h1 class="text-xl font-semibold text-gray-900 dark:text-white">
            {{ isEditMode() ? 'Edit User' : 'Add New User' }}
          </h1>
        </div>

        <form [formGroup]="form" (ngSubmit)="onSubmit()" class="p-6 space-y-6">
          <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                First Name *
              </label>
              <input
                type="text"
                formControlName="first_name"
                class="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              />
              @if (form.get('first_name')?.touched && form.get('first_name')?.errors?.['required']) {
                <p class="text-red-500 text-sm mt-1">First name is required</p>
              }
            </div>

            <div>
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Last Name *
              </label>
              <input
                type="text"
                formControlName="last_name"
                class="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              />
              @if (form.get('last_name')?.touched && form.get('last_name')?.errors?.['required']) {
                <p class="text-red-500 text-sm mt-1">Last name is required</p>
              }
            </div>
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Email *
            </label>
            <input
              type="email"
              formControlName="email"
              class="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            />
            @if (form.get('email')?.touched && form.get('email')?.errors?.['required']) {
              <p class="text-red-500 text-sm mt-1">Email is required</p>
            }
            @if (form.get('email')?.touched && form.get('email')?.errors?.['email']) {
              <p class="text-red-500 text-sm mt-1">Please enter a valid email</p>
            }
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Phone
            </label>
            <input
              type="tel"
              formControlName="phone"
              class="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            />
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Role *
              </label>
              <select
                formControlName="role"
                class="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              >
                <option value="student">Student</option>
                <option value="instructor">Instructor</option>
                <option value="staff">Staff</option>
                <option value="admin">Admin</option>
              </select>
            </div>

            <div>
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Status
              </label>
              <select
                formControlName="status"
                class="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              >
                <option value="active">Active</option>
                <option value="inactive">Inactive</option>
                <option value="suspended">Suspended</option>
              </select>
            </div>
          </div>

          @if (!isEditMode()) {
            <div>
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Temporary Password *
              </label>
              <input
                type="password"
                formControlName="password"
                class="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              />
              <p class="text-sm text-gray-500 mt-1">User will be required to change password on first login</p>
            </div>
          }

          <div class="pt-4 border-t border-gray-200 dark:border-gray-700 flex justify-end gap-4">
            <a
              routerLink="/admin/users"
              class="px-4 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700"
            >
              Cancel
            </a>
            <button
              type="submit"
              [disabled]="form.invalid || submitting()"
              class="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {{ submitting() ? 'Saving...' : (isEditMode() ? 'Save Changes' : 'Create User') }}
            </button>
          </div>
        </form>
      </div>
    </div>
  `,
})
export class UserFormComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private http = inject(HttpClient);
  private fb = inject(FormBuilder);

  isEditMode = signal(false);
  submitting = signal(false);
  userId = signal<string | null>(null);

  form: FormGroup = this.fb.group({
    first_name: ['', Validators.required],
    last_name: ['', Validators.required],
    email: ['', [Validators.required, Validators.email]],
    phone: [''],
    role: ['student', Validators.required],
    status: ['active'],
    password: [''],
  });

  ngOnInit() {
    const id = this.route.snapshot.paramMap.get('id');
    if (id) {
      this.isEditMode.set(true);
      this.userId.set(id);
      this.loadUser(id);
    } else {
      this.form.get('password')?.setValidators([Validators.required, Validators.minLength(8)]);
    }
  }

  loadUser(id: string) {
    this.http.get<Record<string, unknown>>(`/api/v1/users/${id}/`).subscribe({
      next: (user) => {
        this.form.patchValue(user);
      },
      error: () => {
        // Mock data
        this.form.patchValue({
          first_name: 'John',
          last_name: 'Pilot',
          email: 'john.pilot@example.com',
          phone: '+47 123 45 678',
          role: 'student',
          status: 'active',
        });
      },
    });
  }

  onSubmit() {
    if (this.form.invalid) return;

    this.submitting.set(true);
    const data = this.form.value;

    const request = this.isEditMode()
      ? this.http.patch(`/api/v1/users/${this.userId()}/`, data)
      : this.http.post('/api/v1/users/', data);

    request.subscribe({
      next: () => {
        this.router.navigate(['/admin/users']);
      },
      error: () => {
        // Navigate anyway for demo
        this.router.navigate(['/admin/users']);
      },
    });
  }
}
