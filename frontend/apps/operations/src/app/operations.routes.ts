import { Routes } from '@angular/router';

export const OPERATIONS_ROUTES: Routes = [
  // Default - Dispatch Board
  {
    path: '',
    loadComponent: () =>
      import('./features/dispatch/dispatch-board.component').then(
        (m) => m.DispatchBoardComponent
      ),
    title: 'Dispatch Board',
  },

  // =========================================================================
  // BOOKING ROUTES
  // =========================================================================
  {
    path: 'calendar',
    loadComponent: () =>
      import('./features/booking/booking-calendar.component').then(
        (m) => m.BookingCalendarComponent
      ),
    title: 'Booking Calendar',
  },
  {
    path: 'quick',
    loadComponent: () =>
      import('./features/booking/quick-book.component').then(
        (m) => m.QuickBookComponent
      ),
    title: 'Quick Book',
  },
  {
    path: 'resources',
    loadComponent: () =>
      import('./features/booking/resource-view.component').then(
        (m) => m.ResourceViewComponent
      ),
    title: 'Resources',
  },
  {
    path: ':id',
    loadComponent: () =>
      import('./features/booking/booking-detail.component').then(
        (m) => m.BookingDetailComponent
      ),
    title: 'Booking Details',
  },

  // =========================================================================
  // FLIGHT ROUTES
  // =========================================================================
  {
    path: 'active',
    loadComponent: () =>
      import('./features/flight/active-flights.component').then(
        (m) => m.ActiveFlightsComponent
      ),
    title: 'Active Flights',
  },
  {
    path: 'history',
    loadComponent: () =>
      import('./features/flight/flight-history.component').then(
        (m) => m.FlightHistoryComponent
      ),
    title: 'Flight History',
  },
  {
    path: 'logbook',
    loadComponent: () =>
      import('./features/flight/pilot-logbook.component').then(
        (m) => m.PilotLogbookComponent
      ),
    title: 'Pilot Logbook',
  },
  {
    path: 'start/:bookingId',
    loadComponent: () =>
      import('./features/flight/start-flight.component').then(
        (m) => m.StartFlightComponent
      ),
    title: 'Start Flight',
  },
  {
    path: 'end/:flightId',
    loadComponent: () =>
      import('./features/flight/end-flight.component').then(
        (m) => m.EndFlightComponent
      ),
    title: 'End Flight',
  },
];
