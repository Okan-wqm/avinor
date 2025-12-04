import { Component, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'fts-invoice-list',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
    <div class="p-6">
      <div class="flex justify-between items-center mb-6">
        <div>
          <h1 class="text-2xl font-bold text-gray-900 dark:text-white">Invoices</h1>
          <p class="text-gray-600 dark:text-gray-400">Manage customer invoices and payments</p>
        </div>
        <button class="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700">+ Create Invoice</button>
      </div>

      <div class="bg-white dark:bg-gray-800 rounded-lg shadow-sm overflow-hidden">
        <table class="w-full">
          <thead class="bg-gray-50 dark:bg-gray-700">
            <tr>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Invoice</th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Customer</th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Amount</th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Date</th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Due</th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
              <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Actions</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-200 dark:divide-gray-700">
            @for (inv of invoices(); track inv.id) {
              <tr class="hover:bg-gray-50 dark:hover:bg-gray-700/50">
                <td class="px-6 py-4 font-medium text-gray-900 dark:text-white">{{ inv.number }}</td>
                <td class="px-6 py-4 text-gray-700 dark:text-gray-300">{{ inv.customer }}</td>
                <td class="px-6 py-4 font-medium text-gray-900 dark:text-white">{{ inv.amount | currency:'NOK':'symbol':'1.0-0' }}</td>
                <td class="px-6 py-4 text-gray-500">{{ inv.date | date:'shortDate' }}</td>
                <td class="px-6 py-4 text-gray-500">{{ inv.due_date | date:'shortDate' }}</td>
                <td class="px-6 py-4">
                  <span [class]="'px-2 py-1 text-xs rounded capitalize ' + getStatusClass(inv.status)">{{ inv.status }}</span>
                </td>
                <td class="px-6 py-4 text-right">
                  <button class="text-primary-600 hover:text-primary-700 text-sm font-medium">View</button>
                </td>
              </tr>
            }
          </tbody>
        </table>
      </div>
    </div>
  `,
})
export class InvoiceListComponent {
  invoices = signal([
    { id: '1', number: 'INV-2024-0156', customer: 'John Pilot', amount: 4400, date: '2024-12-01', due_date: '2024-12-15', status: 'paid' },
    { id: '2', number: 'INV-2024-0155', customer: 'Jane Aviator', amount: 6600, date: '2024-11-28', due_date: '2024-12-12', status: 'pending' },
    { id: '3', number: 'INV-2024-0154', customer: 'Mike Flyer', amount: 2200, date: '2024-11-15', due_date: '2024-11-29', status: 'overdue' },
    { id: '4', number: 'INV-2024-0153', customer: 'Sarah Sky', amount: 8800, date: '2024-11-10', due_date: '2024-11-24', status: 'paid' },
    { id: '5', number: 'INV-2024-0152', customer: 'Tom Cloud', amount: 3300, date: '2024-11-05', due_date: '2024-11-19', status: 'paid' },
  ]);

  getStatusClass(status: string): string {
    return status === 'paid' ? 'bg-green-100 text-green-800' : status === 'overdue' ? 'bg-red-100 text-red-800' : 'bg-yellow-100 text-yellow-800';
  }
}
