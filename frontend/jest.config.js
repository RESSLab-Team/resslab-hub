module.exports = {
  preset: "@vue/cli-plugin-unit-jest/presets/typescript-and-babel",
  setupFiles: ["<rootDir>/tests/jest-setup.js"],
  transform: {
    "^.+\\.csv$": "<rootDir>/tests/jest-csv-transformer.js",
  },
  transformIgnorePatterns: ["<rootDir>/node_modules/(?!echarts)/"],
};
