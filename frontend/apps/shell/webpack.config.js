const { withModuleFederationPlugin, shareAll } = require('@angular-architects/module-federation/webpack');

module.exports = withModuleFederationPlugin({
  name: 'shell',

  // Remotes are loaded dynamically from environment config
  remotes: {},

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
  ],
});
