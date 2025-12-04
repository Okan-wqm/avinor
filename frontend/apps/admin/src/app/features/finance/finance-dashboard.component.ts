import { Component, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'fts-finance-dashboard',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
    <div class="p-6">
      <h1 class="text-2xl font-bold text-gray-900 dark:text-white mb-6">Financial Overview</h1>

      <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <div class="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-sm">
          <p class="text-sm text-gray-500">Monthly Revenue</p>
          <p class="text-3xl font-bold text-green-600">{{ 285000 | currency:'NOK':'symbol':'1.0-0' }}</p>
          <p class="text-sm text-green-600">+12% from last month</p>
        </div>
        <div class="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-sm">
          <p class="text-sm text-gray-500">Outstanding</p>
          <p class="text-3xl font-bold text-yellow-600">{{ 42500 | currency:'NOK':'symbol':'1.0-0' }}</p>
          <p class="text-sm text-gray-500">15 invoices</p>
        </div>
        <div class="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-sm">
          <p class="text-sm text-gray-500">Overdue</p>
          <p class="text-3xl font-bold text-red-600">{{ 8200 | currency:'NOK':'symbol':'1.0-0' }}</p>
          <p class="text-sm text-gray-500">3 invoices</p>
        </div>
        <div class="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-sm">
          <p class="text-sm text-gray-500">Active Packages</p>
          <p class="text-3xl font-bold text-primary-600">45</p>
          <p class="text-sm text-gray-500">{{ 125000 | currency:'NOK':'symbol':'1.0-0' }} value</p>
        </div>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div class="bg-white dark:bg-gray-800 rounded-lg shadow-sm">
          <div class="px-6 py-4 border-b border-gray-200 dark:border-gray-700 flex justify-between items-center">
            <h3 class="font-semibold text-gray-900 dark:text-white">Recent Invoices</h3>
            <a routerLink="/admin/finance/invoices" class="text-primary-600 text-sm">View All</a>
          </div>
          <div class="p-6">
            @for (inv of recentInvoices(); track inv.id) {
              <div class="flex justify-between py-3 border-b border-gray-100 dark:border-gray-700 last:border-0">
                <div>
                  <p class="font-medium text-gray-900 dark:text-white">{{ inv.number }}</p>
                  <p class="text-sm text-gray-500">{{ inv.customer }}</p>
                </div>
                <div class="text-right">
                  <p class="font-medium">{{ inv.amount | currency:'NOK':'symbol':'1.0-0' }}</p>
                  <span [class]="'text-xs px-2 py-0.5 rounded ' + (inv.status === 'paid' ? 'bg-green-100 text-green-800' : inv.status === 'overdue' ? 'bg-red-100 text-red-800' : 'bg-yellow-100 text-yellow-800')">{{ inv.status }}</span>
                </div>
              </div>
            }
          </div>
        </div>

        <div class="bg-white dark:bg-gray-800 rounded-lg shadow-sm">
          <div class="px-6 py-4 border-b border-gray-200 dark:border-gray-700 flex justify-between items-center">
            <h3 class="font-semibold text-gray-900 dark:text-white">Quick Actions</h3>
          </div>
          <div class="p-6 space-y-3">
            <a routerLink="/admin/finance/invoices" class="block w-full px-4 py-3 bg-gray-50 dark:bg-gray-700 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-600 text-gray-900 dark:text-white">Create Invoice</a>
            <a routerLink="/admin/finance/pricing" class="block w-full px-4 py-3 bg-gray-50 dark:bg-gray-700 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-600 text-gray-900 dark:text-white">Manage Pricing</a>
            <button class="block w-full px-4 py-3 bg-gray-50 dark:bg-gray-700 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-600 text-gray-900 dark:text-white text-left">Export Reports</button>
          </div>
        </div>
      </div>
    </div>
  `,
})
export class FinanceDashboardComponent {
  recentInvoices = signal([
    { id: '1', number: 'INV-2024-0156', customer: 'John Pilot', amount: 4400, status: 'paid' },
    { id: '2', number: 'INV-2024-0155', customer: 'Jane Aviator', amount: 6600, status: 'pending' },
    { id: '3', number: 'INV-2024-0154', customer: 'Mike Flyer', amount: 2200, status: 'overdue' },
    { id: '4', number: 'INV-2024-0153', customer: 'Sarah Sky', amount: 8800, status: 'paid' },
  ]);
}
