/* eslint-env node */
require('@rushstack/eslint-patch/modern-module-resolution')

module.exports = {
  root: true,
  extends: [
    'plugin:vue/vue3-recommended',
    'eslint:recommended',
    '@vue/eslint-config-typescript',
    '@vue/eslint-config-prettier/skip-formatting'
  ],
  parserOptions: {
    ecmaVersion: 'latest'
  },
  rules: {
    // Every link that opens a new tab gets rel="noopener noreferrer", also when
    // the href comes from the data (#264, H5).
    'vue/no-template-target-blank': [
      'error',
      { allowReferrer: false, enforceDynamicLinks: 'always' }
    ]
  }
}
