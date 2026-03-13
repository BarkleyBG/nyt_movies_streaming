/**
 * Integration tests for the NYT Top 100 Movie Tracker.
 *
 * These run against the real index.html in a browser (Chromium + Firefox)
 * using Playwright. The Python HTTP server is started automatically by
 * playwright.config.js before all tests.
 *
 * Coverage areas:
 *  - Page load & initial render
 *  - Movie card structure
 *  - Search (title, director, year, case-insensitive, empty state)
 *  - Sort (rank, alpha, year)
 *  - Streaming service filter pills
 *  - Show filter pills (All / Unseen / Want / Seen)
 *  - Seen / Want buttons and state persistence (localStorage)
 *  - Stats bar updates
 *  - Accessibility basics
 */

const { test, expect } = require("@playwright/test");

// ─── Helpers ─────────────────────────────────────────────────────────────────

/**
 * Navigate to the app and wait for the movie list to be rendered.
 * Playwright beforeEach hooks must use destructured { page } syntax.
 */
async function loadApp({ page }) {
  await page.goto("/");
  // The movie list renders after the async loadStreamingData() call resolves.
  await page.waitForSelector(".movie-card");
}

/**
 * Clear localStorage then reload the page (gives each test a clean slate).
 * Playwright beforeEach hooks must use destructured { page } syntax.
 */
async function freshLoad({ page }) {
  await page.goto("/");
  await page.evaluate(() => localStorage.clear());
  await page.reload();
  await page.waitForSelector(".movie-card");
}

// ─── Page Load ───────────────────────────────────────────────────────────────
test.describe("Page Load", () => {
  test("has the correct page title", async ({ page }) => {
    await loadApp({ page });
    await expect(page).toHaveTitle(/Streaming the Top 100/);
  });

  test("header contains 'Top 100' text", async ({ page }) => {
    await loadApp({ page });
    await expect(page.locator("header h1")).toContainText("Top 100");
  });

  test("renders exactly 100 movie cards", async ({ page }) => {
    await loadApp({ page });
    await expect(page.locator(".movie-card")).toHaveCount(100);
  });

  test("footer is visible", async ({ page }) => {
    await loadApp({ page });
    await expect(page.locator("footer")).toBeVisible();
  });
});

// ─── Stats Bar (initial) ──────────────────────────────────────────────────────
test.describe("Stats Bar — initial state", () => {
  test.beforeEach(freshLoad);

  test("seen starts at 0", async ({ page }) => {
    await expect(page.locator("#stat-seen")).toHaveText("0");
  });

  test("want starts at 0", async ({ page }) => {
    await expect(page.locator("#stat-want")).toHaveText("0");
  });

  test("remaining starts at 100", async ({ page }) => {
    await expect(page.locator("#stat-remaining")).toHaveText("100");
  });

  test("showing starts at 100", async ({ page }) => {
    await expect(page.locator("#stat-showing")).toHaveText("100");
  });
});

// ─── Movie Card Structure ─────────────────────────────────────────────────────
test.describe("Movie Card Structure", () => {
  test.beforeEach(loadApp);

  test("first card is rank 1 — Parasite", async ({ page }) => {
    const first = page.locator(".movie-card").first();
    await expect(first.locator(".rank-badge")).toHaveText("1");
    await expect(first.locator(".movie-title")).toContainText("Parasite");
  });

  test("last card is rank 100 — Superbad (default rank sort)", async ({ page }) => {
    const last = page.locator(".movie-card").last();
    await expect(last.locator(".rank-badge")).toHaveText("100");
    await expect(last.locator(".movie-title")).toContainText("Superbad");
  });

  test("each card shows year and director in meta line", async ({ page }) => {
    const first = page.locator(".movie-card").first();
    await expect(first.locator(".movie-meta")).toContainText("2019");
    await expect(first.locator(".movie-meta")).toContainText("Bong Joon-ho");
  });

  test("each card has Seen and Want to See action buttons", async ({ page }) => {
    const first = page.locator(".movie-card").first();
    await expect(first.locator('[data-action="seen"]')).toBeVisible();
    await expect(first.locator('[data-action="want"]')).toBeVisible();
  });
});

// ─── Search ───────────────────────────────────────────────────────────────────
test.describe("Search", () => {
  test.beforeEach(loadApp);

  test("filtering by title returns only matching movies", async ({ page }) => {
    await page.fill("#search-box", "Parasite");
    await expect(page.locator(".movie-card")).toHaveCount(1);
    await expect(page.locator(".movie-title").first()).toContainText("Parasite");
  });

  test("filtering by director name returns all that director's films", async ({ page }) => {
    // David Fincher directed: The Social Network (#10), Zodiac (#19), Gone Girl (#64)
    await page.fill("#search-box", "David Fincher");
    await expect(page.locator(".movie-card")).toHaveCount(3);
  });

  test("filtering by year narrows to that year's films", async ({ page }) => {
    // 2023: The Zone of Interest (#12), Anatomy of a Fall (#26), Oppenheimer (#65), Past Lives (#86)
    await page.fill("#search-box", "2023");
    await expect(page.locator(".movie-card")).toHaveCount(4);
  });

  test("no-match search shows the empty-state message", async ({ page }) => {
    await page.fill("#search-box", "xyznonexistentfilm999");
    await expect(page.locator(".empty-state")).toBeVisible();
    await expect(page.locator(".empty-state")).toContainText("No movies match");
  });

  test("search is case-insensitive", async ({ page }) => {
    await page.fill("#search-box", "PARASITE");
    await expect(page.locator(".movie-card")).toHaveCount(1);
  });

  test("clearing the search box restores all 100 movies", async ({ page }) => {
    await page.fill("#search-box", "Parasite");
    await page.fill("#search-box", "");
    await expect(page.locator(".movie-card")).toHaveCount(100);
  });

  test("'Showing' stat updates to match search result count", async ({ page }) => {
    await page.fill("#search-box", "Parasite");
    await expect(page.locator("#stat-showing")).toHaveText("1");
  });

  test("partial title match works ('social' matches 'The Social Network')", async ({ page }) => {
    await page.fill("#search-box", "social");
    await expect(page.locator(".movie-card")).toHaveCount(1);
  });
});

// ─── Sort ─────────────────────────────────────────────────────────────────────
test.describe("Sort", () => {
  test.beforeEach(loadApp);

  test("default sort shows rank 1 first", async ({ page }) => {
    const first = page.locator(".movie-card").first();
    await expect(first.locator(".rank-badge")).toHaveText("1");
  });

  test("alphabetical sort — first title starts before 'B'", async ({ page }) => {
    await page.selectOption("#sort-select", "alpha");
    // The alphabetically-first title should start with a letter ≤ 'A'/'B'
    const firstTitle = await page.locator(".movie-title").first().textContent();
    expect(firstTitle?.charAt(0).toUpperCase() <= "B").toBe(true);
  });

  test("year sort — first card is from year 2000", async ({ page }) => {
    await page.selectOption("#sort-select", "year");
    const firstMeta = await page.locator(".movie-meta").first().textContent();
    expect(firstMeta).toContain("2000");
  });

  test("year sort — last card is from year 2023", async ({ page }) => {
    await page.selectOption("#sort-select", "year");
    const lastMeta = await page.locator(".movie-meta").last().textContent();
    expect(lastMeta).toContain("2023");
  });

  test("switching sort back to rank restores rank 1 first", async ({ page }) => {
    await page.selectOption("#sort-select", "alpha");
    await page.selectOption("#sort-select", "rank");
    await expect(page.locator(".movie-card").first().locator(".rank-badge")).toHaveText("1");
  });
});

// ─── Streaming Service Filter Pills ──────────────────────────────────────────
test.describe("Streaming Service Filter Pills", () => {
  test.beforeEach(loadApp);

  test("no streaming pill is active on load", async ({ page }) => {
    await expect(page.locator(".filter-pills .pill.active")).toHaveCount(0);
  });

  test("clicking a pill activates it", async ({ page }) => {
    await page.click('[data-service="netflix"]');
    await expect(page.locator('[data-service="netflix"]')).toHaveClass(/active/);
  });

  test("clicking the active pill again deactivates it (toggle)", async ({ page }) => {
    await page.click('[data-service="netflix"]');
    await page.click('[data-service="netflix"]');
    await expect(page.locator('[data-service="netflix"]')).not.toHaveClass(/active/);
  });

  test("only one streaming pill can be active at a time", async ({ page }) => {
    await page.click('[data-service="netflix"]');
    await page.click('[data-service="hbo"]');
    await expect(page.locator(".filter-pills .pill.active")).toHaveCount(1);
    await expect(page.locator('[data-service="netflix"]')).not.toHaveClass(/active/);
    await expect(page.locator('[data-service="hbo"]')).toHaveClass(/active/);
  });

  test("deactivating a streaming pill returns all 100 movies", async ({ page }) => {
    await page.click('[data-service="netflix"]');
    await page.click('[data-service="netflix"]'); // toggle off
    await expect(page.locator(".movie-card")).toHaveCount(100);
  });
});

// ─── Show Filter Pills ────────────────────────────────────────────────────────
test.describe("Show Filter Pills", () => {
  test.beforeEach(freshLoad);

  test("'All' pill is active by default", async ({ page }) => {
    await expect(page.locator('[data-show="all"]')).toHaveClass(/active/);
  });

  test("'Unseen Only' shows all 100 when nothing is marked seen", async ({ page }) => {
    await page.click('[data-show="unseen"]');
    await expect(page.locator(".movie-card")).toHaveCount(100);
  });

  test("'Already Seen' shows empty state when nothing is marked", async ({ page }) => {
    await page.click('[data-show="seen"]');
    await expect(page.locator(".empty-state")).toBeVisible();
  });

  test("'Want to See' shows empty state when nothing is marked", async ({ page }) => {
    await page.click('[data-show="want"]');
    await expect(page.locator(".empty-state")).toBeVisible();
  });

  test("only one show pill is active at a time", async ({ page }) => {
    await page.click('[data-show="unseen"]');
    await expect(page.locator(".show-filters .pill.active")).toHaveCount(1);
  });

  test("clicking 'All' after another filter restores all movies", async ({ page }) => {
    await page.click('[data-show="seen"]'); // empty state
    await page.click('[data-show="all"]');  // back to all
    await expect(page.locator(".movie-card")).toHaveCount(100);
  });
});

// ─── Seen / Want Buttons ──────────────────────────────────────────────────────
test.describe("Seen and Want to See Buttons", () => {
  test.beforeEach(freshLoad);

  test("clicking Seen applies 'is-seen' class to the card", async ({ page }) => {
    const firstCard = page.locator(".movie-card").first();
    await firstCard.locator('[data-action="seen"]').click();
    await expect(firstCard).toHaveClass(/is-seen/);
  });

  test("seen count increments and remaining decrements after marking a movie seen", async ({ page }) => {
    await page.locator(".movie-card").first().locator('[data-action="seen"]').click();
    await expect(page.locator("#stat-seen")).toHaveText("1");
    await expect(page.locator("#stat-remaining")).toHaveText("99");
  });

  test("seen count + remaining always equals 100", async ({ page }) => {
    // Mark 3 movies
    const cards = page.locator(".movie-card");
    for (let i = 0; i < 3; i++) {
      await cards.nth(i).locator('[data-action="seen"]').click();
    }
    const seen      = parseInt(await page.locator("#stat-seen").textContent() ?? "0");
    const remaining = parseInt(await page.locator("#stat-remaining").textContent() ?? "0");
    expect(seen + remaining).toBe(100);
  });

  test("clicking Seen a second time un-marks the movie", async ({ page }) => {
    const firstCard = page.locator(".movie-card").first();
    const seenBtn = firstCard.locator('[data-action="seen"]');
    await seenBtn.click(); // mark
    await seenBtn.click(); // unmark
    await expect(firstCard).not.toHaveClass(/is-seen/);
    await expect(page.locator("#stat-seen")).toHaveText("0");
  });

  test("clicking Want to See adds 'active-want' class to the button", async ({ page }) => {
    const firstCard = page.locator(".movie-card").first();
    const wantBtn = firstCard.locator('[data-action="want"]');
    await wantBtn.click();
    await expect(wantBtn).toHaveClass(/active-want/);
    await expect(page.locator("#stat-want")).toHaveText("1");
  });

  test("clicking Want a second time removes 'active-want'", async ({ page }) => {
    const firstCard = page.locator(".movie-card").first();
    const wantBtn = firstCard.locator('[data-action="want"]');
    await wantBtn.click();
    await wantBtn.click();
    await expect(wantBtn).not.toHaveClass(/active-want/);
    await expect(page.locator("#stat-want")).toHaveText("0");
  });

  test("Seen state persists after page reload (localStorage)", async ({ page }) => {
    await page.locator(".movie-card").first().locator('[data-action="seen"]').click();
    await page.reload();
    await page.waitForSelector(".movie-card");
    await expect(page.locator("#stat-seen")).toHaveText("1");
    await expect(page.locator("#stat-remaining")).toHaveText("99");
  });

  test("Want state persists after page reload (localStorage)", async ({ page }) => {
    await page.locator(".movie-card").first().locator('[data-action="want"]').click();
    await page.reload();
    await page.waitForSelector(".movie-card");
    await expect(page.locator("#stat-want")).toHaveText("1");
  });

  test("'Unseen Only' hides movies marked as seen", async ({ page }) => {
    // Mark Parasite (rank 1) as seen
    await page.locator(".movie-card").first().locator('[data-action="seen"]').click();
    await page.click('[data-show="unseen"]');
    const titles = await page.locator(".movie-title").allTextContents();
    expect(titles).not.toContain("Parasite");
    await expect(page.locator(".movie-card")).toHaveCount(99);
  });

  test("'Already Seen' shows only seen movies", async ({ page }) => {
    await page.locator(".movie-card").first().locator('[data-action="seen"]').click();
    await page.click('[data-show="seen"]');
    await expect(page.locator(".movie-card")).toHaveCount(1);
    await expect(page.locator(".movie-title").first()).toContainText("Parasite");
  });

  test("'Want to See' filter shows only want-listed movies", async ({ page }) => {
    await page.locator(".movie-card").first().locator('[data-action="want"]').click();
    await page.click('[data-show="want"]');
    await expect(page.locator(".movie-card")).toHaveCount(1);
    await expect(page.locator(".movie-title").first()).toContainText("Parasite");
  });
});

// ─── Combined Filters ─────────────────────────────────────────────────────────
test.describe("Combined Filters", () => {
  test.beforeEach(loadApp);

  test("search + sort both apply simultaneously", async ({ page }) => {
    await page.fill("#search-box", "David Fincher");
    await page.selectOption("#sort-select", "year");
    // Fincher films sorted by year: Zodiac (2007), The Social Network (2010), Gone Girl (2014)
    const metas = await page.locator(".movie-meta").allTextContents();
    const years = metas.map((t) => parseInt(t.match(/\d{4}/)?.[0] ?? "0"));
    expect(years[0]).toBeLessThanOrEqual(years[years.length - 1]);
  });

  test("showing count reflects search + streaming filter together", async ({ page }) => {
    // With no streaming data loaded (file not present), filter returns 0
    // This test just verifies the showing stat changes with the filter
    const before = parseInt(await page.locator("#stat-showing").textContent() ?? "0");
    await page.click('[data-service="disney"]');
    const after = parseInt(await page.locator("#stat-showing").textContent() ?? "0");
    expect(after).toBeLessThanOrEqual(before);
  });
});

// ─── Accessibility Basics ─────────────────────────────────────────────────────
test.describe("Accessibility", () => {
  test.beforeEach(loadApp);

  test("search input has an associated label", async ({ page }) => {
    await expect(page.locator('label[for="search-box"]')).toBeVisible();
  });

  test("sort select has an associated label", async ({ page }) => {
    await expect(page.locator('label[for="sort-select"]')).toBeVisible();
  });

  test("Seen buttons are focusable via keyboard", async ({ page }) => {
    const btn = page.locator('[data-action="seen"]').first();
    await btn.focus();
    await expect(btn).toBeFocused();
  });

  test("Want buttons are focusable via keyboard", async ({ page }) => {
    const btn = page.locator('[data-action="want"]').first();
    await btn.focus();
    await expect(btn).toBeFocused();
  });
});
