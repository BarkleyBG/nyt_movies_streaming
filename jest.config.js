/**
 * Jest configuration for NYT Movie Tracker unit tests.
 *
 * All unit tests use pure Node.js functions (no DOM access) — the app logic
 * is extracted from index.html into each test file and tested in isolation,
 * with mock objects standing in for localStorage. No jsdom needed.
 */
module.exports = {
  // Pure Node environment — no DOM overhead (unit tests use mock objects only)
  testEnvironment: "node",

  // Only pick up files in tests/unit/
  testMatch: ["**/tests/unit/**/*.test.js"],

  // Show individual test names in output
  verbose: true,

  // Coverage note: the app's pure functions are extracted directly into each
  // test file (no separate source module to import). Jest excludes test files
  // from instrumentation, so branch/line coverage comes from the integration
  // tests (Playwright) rather than Jest. Run `npm run test:coverage` to confirm
  // all unit logic paths are exercised — it will show the test run summary.
  coverageDirectory: "coverage",
  coverageReporters: ["text", "lcov"],
};
