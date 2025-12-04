import { Component, inject, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { HttpClient } from '@angular/common/http';

interface CertificateDetail {
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
    email: string;
  };
  privileges: string[];
  limitations: string[];
  history: {
    action: string;
    date: string;
    performed_by: string;
    notes?: string;
  }[];
}

@Component({
  selector: 'fts-certificate-detail',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
    <div class="p-6 max-w-4xl mx-auto">
      <a
        routerLink="/training/certificates"
        class="inline-flex items-center text-gray-600 dark:text-gray-400 hover:text-primary-600 mb-6"
      >
        <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
        </svg>
        Back to Certificates
      </a>

      @if (loading()) {
        <div class="animate-pulse space-y-6">
          <div class="h-48 bg-gray-200 dark:bg-gray-700 rounded-lg"></div>
          <div class="h-32 bg-gray-200 dark:bg-gray-700 rounded-lg"></div>
        </div>
      } @else if (certificate()) {
        <!-- Certificate card -->
        <div class="bg-white dark:bg-gray-800 rounded-lg shadow-sm overflow-hidden mb-6">
          <div class="bg-gradient-to-r from-primary-600 to-primary-700 p-6 text-white">
            <div class="flex justify-between items-start">
              <div>
                <span class="text-primary-100 text-sm uppercase tracking-wide">{{ certificate()!.type }}</span>
                <h1 class="text-2xl font-bold mt-1">{{ certificate()!.name }}</h1>
                <p class="text-primary-100 mt-2">{{ certificate()!.issuing_authority }}</p>
              </div>
              <span
                [class]="'px-3 py-1 text-sm font-medium rounded-full ' + getStatusClass(certificate()!.status)"
              >
                {{ certificate()!.status }}
              </span>
            </div>
          </div>

          <div class="p-6">
            <div class="grid grid-cols-2 md:grid-cols-4 gap-6">
              <div>
                <p class="text-sm text-gray-500">Certificate Number</p>
                <p class="text-lg font-mono font-semibold text-gray-900 dark:text-white">
                  {{ certificate()!.number }}
                </p>
              </div>
              <div>
                <p class="text-sm text-gray-500">Issue Date</p>
                <p class="text-lg font-semibold text-gray-900 dark:text-white">
                  {{ certificate()!.issue_date | date:'mediumDate' }}
                </p>
              </div>
              <div>
                <p class="text-sm text-gray-500">Expiry Date</p>
                <p class="text-lg font-semibold text-gray-900 dark:text-white">
                  {{ certificate()!.expiry_date ? (certificate()!.expiry_date | date:'mediumDate') : 'No Expiry' }}
                </p>
              </div>
              <div>
                <p class="text-sm text-gray-500">Holder</p>
                <p class="text-lg font-semibold text-gray-900 dark:text-white">
                  {{ certificate()!.holder.name }}
                </p>
              </div>
            </div>
          </div>
        </div>

        <!-- Privileges and Limitations -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
          <div class="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-6">
            <h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
              <svg class="w-5 h-5 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
              </svg>
              Privileges
            </h3>
            <ul class="space-y-2">
              @for (privilege of certificate()!.privileges; track privilege) {
                <li class="flex items-start gap-2 text-gray-700 dark:text-gray-300">
                  <span class="w-1.5 h-1.5 rounded-full bg-green-500 mt-2"></span>
                  {{ privilege }}
                </li>
              } @empty {
                <li class="text-gray-500">No specific privileges listed</li>
              }
            </ul>
          </div>

          <div class="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-6">
            <h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
              <svg class="w-5 h-5 text-yellow-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
              Limitations
            </h3>
            <ul class="space-y-2">
              @for (limitation of certificate()!.limitations; track limitation) {
                <li class="flex items-start gap-2 text-gray-700 dark:text-gray-300">
                  <span class="w-1.5 h-1.5 rounded-full bg-yellow-500 mt-2"></span>
                  {{ limitation }}
                </li>
              } @empty {
                <li class="text-gray-500">No limitations</li>
              }
            </ul>
          </div>
        </div>

        <!-- History -->
        <div class="bg-white dark:bg-gray-800 rounded-lg shadow-sm overflow-hidden">
          <div class="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
            <h3 class="text-lg font-semibold text-gray-900 dark:text-white">Certificate History</h3>
          </div>
          <div class="divide-y divide-gray-200 dark:divide-gray-700">
            @for (event of certificate()!.history; track event.date) {
              <div class="px-6 py-4">
                <div class="flex justify-between items-start">
                  <div>
                    <p class="font-medium text-gray-900 dark:text-white">{{ event.action }}</p>
                    <p class="text-sm text-gray-500">By {{ event.performed_by }}</p>
                    @if (event.notes) {
                      <p class="text-sm text-gray-600 dark:text-gray-400 mt-1">{{ event.notes }}</p>
                    }
                  </div>
                  <p class="text-sm text-gray-500">{{ event.date | date:'medium' }}</p>
                </div>
              </div>
            } @empty {
              <div class="px-6 py-8 text-center text-gray-500">
                No history available
              </div>
            }
          </div>
        </div>

        <!-- Actions -->
        <div class="flex gap-4 mt-6">
          <button class="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700">
            Download Certificate
          </button>
          @if (certificate()!.status === 'valid' && certificate()!.expiry_date) {
            <button class="px-4 py-2 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600">
              Request Renewal
            </button>
          }
        </div>
      }
    </div>
  `,
})
export class CertificateDetailComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private http = inject(HttpClient);

  certificate = signal<CertificateDetail | null>(null);
  loading = signal(true);

  ngOnInit() {
    const id = this.route.snapshot.paramMap.get('id');
    if (id) {
      this.loadCertificate(id);
    }
  }

  loadCertificate(id: string) {
    this.loading.set(true);
    this.http.get<CertificateDetail>(`/api/v1/certificates/${id}/`).subscribe({
      next: (certificate) => {
        this.certificate.set(certificate);
        this.loading.set(false);
      },
      error: () => {
        // Mock data
        this.certificate.set({
          id: '1',
          type: 'license',
          name: 'Private Pilot License',
          number: 'PPL-12345',
          issue_date: '2023-06-15',
          expiry_date: undefined,
          issuing_authority: 'EASA',
          status: 'valid',
          holder: {
            id: 'u1',
            name: 'John Pilot',
            email: 'john@example.com',
          },
          privileges: [
            'Act as pilot in command of single-engine piston aircraft',
            'Fly under Visual Flight Rules (VFR)',
            'Carry passengers (non-commercial)',
            'Fly in Class G, E, D, C airspace with appropriate clearances',
          ],
          limitations: [
            'VFR only - No instrument flight privileges',
            'Single-engine aircraft only',
            'Non-commercial operations only',
            'English language proficiency required',
          ],
          history: [
            {
              action: 'License Issued',
              date: '2023-06-15T10:00:00Z',
              performed_by: 'CAA Norway',
              notes: 'Initial PPL issue after successful skill test',
            },
            {
              action: 'Skill Test Passed',
              date: '2023-06-10T14:30:00Z',
              performed_by: 'Capt. Johnson (Examiner)',
              notes: 'All maneuvers completed satisfactorily',
            },
            {
              action: 'Training Completed',
              date: '2023-06-01T16:00:00Z',
              performed_by: 'Flight Training School',
              notes: 'Completed 45 flight hours and 100 ground hours',
            },
          ],
        });
        this.loading.set(false);
      },
    });
  }

  getStatusClass(status: string): string {
    const classes: Record<string, string> = {
      valid: 'bg-green-100 text-green-800',
      expired: 'bg-red-100 text-red-800',
      suspended: 'bg-yellow-100 text-yellow-800',
      revoked: 'bg-gray-100 text-gray-800',
    };
    return classes[status] || 'bg-gray-100 text-gray-800';
  }
}
