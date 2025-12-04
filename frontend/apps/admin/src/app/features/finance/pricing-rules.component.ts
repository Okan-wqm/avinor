import { Component, signal } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'fts-pricing-rules',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="p-6">
      <div class="flex justify-between items-center mb-6">
        <div>
          <h1 class="text-2xl font-bold text-gray-900 dark:text-white">Pricing Rules</h1>
          <p class="text-gray-600 dark:text-gray-400">Configure pricing for aircraft and services</p>
        </div>
        <button class="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700">+ Add Rule</button>
      </div>

      <div class="bg-white dark:bg-gray-800 rounded-lg shadow-sm overflow-hidden">
        <table class="w-full">
          <thead class="bg-gray-50 dark:bg-gray-700">
            <tr>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Name</th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Type</th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Rate</th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Applies To</th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
              <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Actions</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-200 dark:divide-gray-700">
            @for (rule of rules(); track rule.id) {
              <tr class="hover:bg-gray-50 dark:hover:bg-gray-700/50">
                <td class="px-6 py-4 font-medium text-gray-900 dark:text-white">{{ rule.name }}</td>
                <td class="px-6 py-4 capitalize text-gray-700 dark:text-gray-300">{{ rule.type }}</td>
                <td class="px-6 py-4 text-gray-900 dark:text-white">{{ rule.rate | currency:'NOK':'symbol':'1.0-0' }}/{{ rule.unit }}</td>
                <td class="px-6 py-4 text-gray-500">{{ rule.applies_to }}</td>
                <td class="px-6 py-4">
                  <span [class]="'px-2 py-1 text-xs rounded ' + (rule.active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800')">{{ rule.active ? 'Active' : 'Inactive' }}</span>
                </td>
                <td class="px-6 py-4 text-right">
                  <button class="text-primary-600 hover:text-primary-700 text-sm font-medium">Edit</button>
                </td>
              </tr>
            }
          </tbody>
        </table>
      </div>
    </div>
  `,
})
export class PricingRulesComponent {
  rules = signal([
    { id: '1', name: 'Standard Cessna 172', type: 'per_unit', rate: 2200, unit: 'hour', applies_to: 'Cessna 172S', active: true },
    { id: '2', name: 'Weekend Rate', type: 'per_unit', rate: 2400, unit: 'hour', applies_to: 'All Aircraft', active: true },
    { id: '3', name: 'Instructor Fee', type: 'per_unit', rate: 800, unit: 'hour', applies_to: 'Dual Flights', active: true },
    { id: '4', name: 'Night Flying', type: 'per_unit', rate: 300, unit: 'hour', applies_to: 'Night Operations', active: true },
    { id: '5', name: 'Multi-Engine', type: 'per_unit', rate: 4200, unit: 'hour', applies_to: 'PA-44 Seminole', active: true },
  ]);
}
