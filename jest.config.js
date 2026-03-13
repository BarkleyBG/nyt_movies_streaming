/**
 * Jest configuration for NYT Movie Tracker unit tests.
 * Uses jsdom to simulate a browser DOM environment for any DOM-touching tests.
 */
module.exports = {
  // Use jsdom to emulate browser APIs (localStorage, document, etc.)
  testEnvironment: "jest-environment-jsdom",

  // Only pick up files in tests/unit/
  testMatch: ["**/tests/unit/**/*.test.js"],

  // Show individual test names in output
  verbose: true,

  // Collect coverage from the unit test helpers
  collectCoverageFrom: ["tests/unit/**/*.js"],
};
