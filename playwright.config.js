/**
 * Playwright configuration for NYT Movie Tracker integration tests.
 *
 * Spins up Python's built-in HTTP server before running tests,
 * then tears it down afterward. Tests run against http://localhost:3000.
 */
const { defineConfig, devices } = require("@playwright/test");

module.exports = defineConfig({
  // Where to find integration test specs
  testDir: "./tests/integration",

  // Give each test up to 30 seconds (streaming JSON load adds ~1s)
  timeout: 30_000,

  // Retry once on CI to handle flaky timing
  retries: process.env.CI ? 1 : 0,

  // Run tests in parallel (each test gets a fresh browser context)
  fullyParallel: true,

  // Reporters: list for terminal, HTML for review
  reporter: [["list"], ["html", { open: "never", outputFolder: "playwright-report" }]],

  use: {
    // Base URL all page.goto("/") calls resolve against
    baseURL: "http://localhost:3000",

    // Keep a screenshot and trace on failure for debugging
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
  },

  // Browsers to test against
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
    {
      name: "firefox",
      use: { ...devices["Desktop Firefox"] },
    },
  ],

  // Start the Python static file server before all tests
  webServer: {
    command: "python -m http.server 3000",
    url: "http://localhost:3000",
    reuseExistingServer: !process.env.CI,
    // Give the server 5 seconds to start
    timeout: 5_000,
  },
});
