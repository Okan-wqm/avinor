const { withModuleFederationPlugin, shareAll } = require('@angular-architects/module-federation/webpack');

module.exports = withModuleFederationPlugin({
  name: 'operations',

  exposes: {
    './routes': './apps/operations/src/app/operations.routes.ts',
  },

  shared: {
    ...shareAll({
      singleton: true,
      strictVersion: true,
      requiredVersion: 'auto',
    }),
  },

  sharedMappings: [
    '@fts/shared/ui',
    '@fts/shared/auth',
    '@fts/shared/data-access',
    '@fts/shared/util',
    '@fts/shared/models',
    '@fts/domain/booking',
    '@fts/domain/flight',
  ],
});
