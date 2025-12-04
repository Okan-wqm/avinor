// Production environment configuration
export const environment = {
  production: true,

  // API Configuration - REST endpoints through Kong Gateway
  apiBaseUrl: 'https://api.flighttraining.app',

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
  wsUrl: 'wss://api.flighttraining.app/ws',

  // Micro-Frontend URLs (production - CDN)
  mfe: {
    operations: 'https://cdn.flighttraining.app/mfe/operations/remoteEntry.js',
    training: 'https://cdn.flighttraining.app/mfe/training/remoteEntry.js',
    admin: 'https://cdn.flighttraining.app/mfe/admin/remoteEntry.js',
  },

  // Feature flags
  features: {
    darkMode: true,
    offlineMode: true,
    realTimeUpdates: true,
    debugMode: false,
  },

  // Cache settings (in seconds)
  cache: {
    userProfile: 300,      // 5 minutes
    aircraft: 60,          // 1 minute
    weather: 300,          // 5 minutes
    staticData: 3600,      // 1 hour
  },
};
