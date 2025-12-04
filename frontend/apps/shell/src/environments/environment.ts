// Development environment configuration
export const environment = {
  production: false,

  // API Configuration - REST endpoints (NOT GraphQL!)
  apiBaseUrl: 'http://localhost',  // Kong Gateway

  // Individual service endpoints (through Kong)
  api: {
    users: '/api/v1/users',
    auth: '/api/v1/auth',
    organizations: '/api/v1/organizations',
    aircraft: '/api/v1/aircraft',
    bookings: '/api/v1/bookings',
    flights: '/api/v1/flights',
    training: '/api/v1/training',
    theory: '/api/v1/theory',
    certificates: '/api/v1/certificates',
    finance: '/api/v1/accounts',
    documents: '/api/v1/documents',
    maintenance: '/api/v1/maintenance',
    reports: '/api/v1/reports',
    notifications: '/api/v1/notifications',
    weather: '/api/v1/weather',
  },

  // WebSocket for real-time updates
  wsUrl: 'ws://localhost/ws',

  // Micro-Frontend URLs (development - separate ports)
  mfe: {
    operations: 'http://localhost:4201/remoteEntry.js',
    training: 'http://localhost:4202/remoteEntry.js',
    admin: 'http://localhost:4203/remoteEntry.js',
  },

  // Feature flags
  features: {
    darkMode: true,
    offlineMode: false,
    realTimeUpdates: true,
    debugMode: true,
  },

  // Cache settings (in seconds)
  cache: {
    userProfile: 300,      // 5 minutes
    aircraft: 60,          // 1 minute
    weather: 300,          // 5 minutes
    staticData: 3600,      // 1 hour
  },
};
