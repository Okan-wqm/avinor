import { Component, inject, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { HttpClient } from '@angular/common/http';

interface Certificate {
  id: string;
  type: 'license' | 'rating' | 'endorsement' | 'medical';
  name: string;
  number: string;
  issue_date: string;
  expiry_date?: string;
  issuing_authority: string;
  status: 'valid' | 'expired' | 'suspended' | 'revoked';
  holder: {
    id: string;
    name: string;
  };
}

@Component({
  selector: 'fts-certificate-list',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
    <div class="p-6">
      <div class="flex justify-between items-center mb-6">
        <div>
          <h1 class="text-2xl font-bold text-gray-900 dark:text-white">Certificates</h1>
          <p class="text-gray-600 dark:text-gray-400">Manage licenses, ratings, and endorsements</p>
        </div>
        <button
          class="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
        >
          + Add Certificate
        </button>
      </div>

      <!-- Filter tabs -->
      <div class="flex gap-2 mb-6">
        @for (type of certificateTypes; track type.value) {
          <button
            (click)="filterByType(type.value)"
            [class]="selectedType() === type.value
              ? 'px-4 py-2 bg-primary-600 text-white rounded-lg'
              : 'px-4 py-2 bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-700'"
          >
            {{ type.label }}
          </button>
        }
      </div>

      <!-- Expiring soon alert -->
      @if (expiringSoon().length > 0) {
        <div class="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4 mb-6">
          <div class="flex items-center gap-2">
            <svg class="w-5 h-5 text-yellow-600 dark:text-yellow-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            <span class="font-medium text-yellow-800 dark:text-yellow-200">
              {{ expiringSoon().length }} certificate(s) expiring within 90 days
            </span>
          </div>
        </div>
      }

      <!-- Certificate grid -->
      @if (loading()) {
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          @for (i of [1,2,3,4,5,6]; track i) {
            <div class="bg-white dark:bg-gray-800 rounded-lg p-6 animate-pulse">
              <div class="h-6 bg-gray-200 dark:bg-gray-700 rounded w-3/4 mb-4"></div>
              <div class="h-4 bg-gray-200 dark:bg-gray-700 rounded w-full mb-2"></div>
            </div>
          }
        </div>
      } @else {
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          @for (cert of filteredCertificates(); track cert.id) {
            <a
              [routerLink]="['/training/certificates', cert.id]"
              class="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 overflow-hidden hover:shadow-md transition-shadow"
            >
              <div class="p-6">
                <div class="flex justify-between items-start mb-4">
                  <span
                    [class]="'px-2 py-1 text-xs font-medium rounded capitalize ' + getTypeClass(cert.type)"
                  >
                    {{ cert.type }}
                  </span>
                  <span
                    [class]="'px-2 py-1 text-xs font-medium rounded capitalize ' + getStatusClass(cert.status)"
                  >
                    {{ cert.status }}
                  </span>
                </div>

                <h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-2">
                  {{ cert.name }}
                </h3>

                <div class="space-y-2 text-sm">
                  <div class="flex justify-between">
                    <span class="text-gray-500">Number</span>
                    <span class="text-gray-900 dark:text-white font-mono">{{ cert.number }}</span>
                  </div>
                  <div class="flex justify-between">
                    <span class="text-gray-500">Issued</span>
                    <span class="text-gray-900 dark:text-white">{{ cert.issue_date | date:'mediumDate' }}</span>
                  </div>
                  @if (cert.expiry_date) {
                    <div class="flex justify-between">
                      <span class="text-gray-500">Expires</span>
                      <span
                        [class]="isExpiringSoon(cert.expiry_date)
                          ? 'text-yellow-600 dark:text-yellow-400 font-medium'
                          : 'text-gray-900 dark:text-white'"
                      >
                        {{ cert.expiry_date | date:'mediumDate' }}
                      </span>
                    </div>
                  }
                  <div class="flex justify-between">
                    <span class="text-gray-500">Authority</span>
                    <span class="text-gray-900 dark:text-white">{{ cert.issuing_authority }}</span>
                  </div>
                </div>
              </div>

              @if (cert.status === 'valid' && cert.expiry_date && isExpiringSoon(cert.expiry_date)) {
                <div class="px-6 py-3 bg-yellow-50 dark:bg-yellow-900/20 border-t border-yellow-200 dark:border-yellow-800">
                  <p class="text-sm text-yellow-700 dark:text-yellow-300">
                    Expires in {{ getDaysUntilExpiry(cert.expiry_date) }} days
                  </p>
                </div>
              }
            </a>
          } @empty {
            <div class="col-span-3 text-center py-12 text-gray-500">
              No certificates found for the selected filter
            </div>
          }
        </div>
      }
    </div>
  `,
})
export class CertificateListComponent implements OnInit {
  private http = inject(HttpClient);

  certificates = signal<Certificate[]>([]);
  loading = signal(true);
  selectedType = signal<string>('all');

  certificateTypes = [
    { value: 'all', label: 'All' },
    { value: 'license', label: 'Licenses' },
    { value: 'rating', label: 'Ratings' },
    { value: 'endorsement', label: 'Endorsements' },
    { value: 'medical', label: 'Medical' },
  ];

  filteredCertificates = () => {
    const type = this.selectedType();
    if (type === 'all') return this.certificates();
    return this.certificates().filter((c) => c.type === type);
  };

  expiringSoon = () => {
    const now = new Date();
    const ninetyDays = new Date(now.getTime() + 90 * 24 * 60 * 60 * 1000);
    return this.certificates().filter(
      (c) => c.expiry_date && c.status === 'valid' && new Date(c.expiry_date) <= ninetyDays
    );
  };

  ngOnInit() {
    this.loadCertificates();
  }

  loadCertificates() {
    this.loading.set(true);
    this.http.get<{ results: Certificate[] }>('/api/v1/certificates/').subscribe({
      next: (response) => {
        this.certificates.set(response.results || []);
        this.loading.set(false);
      },
      error: () => {
        // Mock data
        this.certificates.set([
          {
            id: '1',
            type: 'license',
            name: 'Private Pilot License',
            number: 'PPL-12345',
            issue_date: '2023-06-15',
            expiry_date: undefined,
            issuing_authority: 'EASA',
            status: 'valid',
            holder: { id: 'u1', name: 'John Pilot' },
          },
          {
            id: '2',
            type: 'medical',
            name: 'Class 2 Medical Certificate',
            number: 'MED-67890',
            issue_date: '2024-01-10',
            expiry_date: '2025-01-10',
            issuing_authority: 'CAA Norway',
            status: 'valid',
            holder: { id: 'u1', name: 'John Pilot' },
          },
          {
            id: '3',
            type: 'rating',
            name: 'Night Rating',
            number: 'NR-11111',
            issue_date: '2023-09-20',
            expiry_date: undefined,
            issuing_authority: 'EASA',
            status: 'valid',
            holder: { id: 'u1', name: 'John Pilot' },
          },
          {
            id: '4',
            type: 'endorsement',
            name: 'Complex Aircraft Endorsement',
            number: 'END-22222',
            issue_date: '2024-03-15',
            expiry_date: undefined,
            issuing_authority: 'Flight School',
            status: 'valid',
            holder: { id: 'u1', name: 'John Pilot' },
          },
          {
            id: '5',
            type: 'rating',
            name: 'Instrument Rating',
            number: 'IR-33333',
            issue_date: '2023-12-01',
            expiry_date: '2024-12-01',
            issuing_authority: 'EASA',
            status: 'valid',
            holder: { id: 'u1', name: 'John Pilot' },
          },
        ]);
        this.loading.set(false);
      },
    });
  }

  filterByType(type: string) {
    this.selectedType.set(type);
  }

  isExpiringSoon(expiryDate: string): boolean {
    const now = new Date();
    const expiry = new Date(expiryDate);
    const ninetyDays = 90 * 24 * 60 * 60 * 1000;
    return expiry.getTime() - now.getTime() <= ninetyDays;
  }

  getDaysUntilExpiry(expiryDate: string): number {
    const now = new Date();
    const expiry = new Date(expiryDate);
    return Math.ceil((expiry.getTime() - now.getTime()) / (24 * 60 * 60 * 1000));
  }

  getTypeClass(type: string): string {
    const classes: Record<string, string> = {
      license: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
      rating: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200',
      endorsement: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
      medical: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
    };
    return classes[type] || 'bg-gray-100 text-gray-800';
  }

  getStatusClass(status: string): string {
    const classes: Record<string, string> = {
      valid: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
      expired: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
      suspended: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
      revoked: 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300',
    };
    return classes[status] || 'bg-gray-100 text-gray-800';
  }
}
