/**
 * Unit tests for the stats bar calculation logic.
 *
 * The stats bar in index.html shows: Seen | Want to See | Remaining | Showing.
 * This file tests the pure calculation logic extracted from render() in index.html.
 *
 * Key invariant: seen + remaining === MOVIES.length (always 100 in production).
 */

// ─── Pure logic mirroring render() stats section in index.html ────────────────

/**
 * Calculates all four stats bar values from movies + user state.
 *
 * @param {object[]} movies       - Full 100-movie array (or subset for tests)
 * @param {object}   userState    - { [rank]: { seen?, want? } }
 * @param {number}   filteredCount - Length of the currently-displayed subset
 * @returns {{ seen: number, want: number, remaining: number, showing: number }}
 */
function calculateStats(movies, userState, filteredCount) {
  // Count movies the user has explicitly marked seen
  const seenCount = movies.filter((m) => userState[m.rank]?.seen).length;
  // Count movies marked "want to see" (independent of seen)
  const wantCount = movies.filter((m) => userState[m.rank]?.want).length;
  return {
    seen:      seenCount,
    want:      wantCount,
    remaining: movies.length - seenCount, // total − seen (not total − showing)
    showing:   filteredCount,
  };
}

// ─── Shared fixture: 10-movie list (ranks 1–10) ───────────────────────────────
const SAMPLE_MOVIES = Array.from({ length: 10 }, (_, i) => ({
  rank:      i + 1,
  title:     `Movie ${i + 1}`,
  year:      2000 + i,
  director:  "Director",
  streaming: [],
}));

// ─── Stats tests ──────────────────────────────────────────────────────────────
describe("calculateStats — initial state (nothing marked)", () => {
  test("seen is 0 with empty user state", () => {
    expect(calculateStats(SAMPLE_MOVIES, {}, 10).seen).toBe(0);
  });

  test("want is 0 with empty user state", () => {
    expect(calculateStats(SAMPLE_MOVIES, {}, 10).want).toBe(0);
  });

  test("remaining equals total movie count when nothing is seen", () => {
    expect(calculateStats(SAMPLE_MOVIES, {}, 10).remaining).toBe(10);
  });

  test("showing equals filteredCount argument", () => {
    expect(calculateStats(SAMPLE_MOVIES, {}, 10).showing).toBe(10);
  });
});

describe("calculateStats — seen count", () => {
  test("counts exactly the movies with seen=true", () => {
    const userState = { 1: { seen: true }, 3: { seen: true }, 5: { seen: true } };
    expect(calculateStats(SAMPLE_MOVIES, userState, 10).seen).toBe(3);
  });

  test("seen=false is not counted", () => {
    const userState = { 1: { seen: false } };
    expect(calculateStats(SAMPLE_MOVIES, userState, 10).seen).toBe(0);
  });

  test("seen count with all movies marked returns total", () => {
    const userState = {};
    SAMPLE_MOVIES.forEach((m) => { userState[m.rank] = { seen: true }; });
    expect(calculateStats(SAMPLE_MOVIES, userState, 0).seen).toBe(10);
  });
});

describe("calculateStats — remaining count", () => {
  test("remaining decreases by 1 for each seen movie", () => {
    const userState = { 1: { seen: true } };
    expect(calculateStats(SAMPLE_MOVIES, userState, 10).remaining).toBe(9);
  });

  test("remaining is 0 when all movies are seen", () => {
    const userState = {};
    SAMPLE_MOVIES.forEach((m) => { userState[m.rank] = { seen: true }; });
    expect(calculateStats(SAMPLE_MOVIES, userState, 0).remaining).toBe(0);
  });

  test("remaining is not affected by 'want' flag — only 'seen' reduces it", () => {
    // want does NOT count toward remaining
    const userState = { 2: { want: true } };
    expect(calculateStats(SAMPLE_MOVIES, userState, 10).remaining).toBe(10);
  });
});

describe("calculateStats — want count", () => {
  test("counts exactly the movies with want=true", () => {
    const userState = { 2: { want: true }, 4: { want: true } };
    expect(calculateStats(SAMPLE_MOVIES, userState, 10).want).toBe(2);
  });

  test("want=false is not counted", () => {
    const userState = { 2: { want: false } };
    expect(calculateStats(SAMPLE_MOVIES, userState, 10).want).toBe(0);
  });
});

describe("calculateStats — seen and want are independent", () => {
  test("a movie marked both seen and want increments both counts", () => {
    const userState = { 3: { seen: true, want: true } };
    const stats = calculateStats(SAMPLE_MOVIES, userState, 10);
    expect(stats.seen).toBe(1);
    expect(stats.want).toBe(1);
  });

  test("seen count and want count can differ independently", () => {
    const userState = {
      1: { seen: true,  want: false },
      2: { seen: false, want: true  },
      3: { seen: true,  want: true  }, // both
    };
    const stats = calculateStats(SAMPLE_MOVIES, userState, 10);
    expect(stats.seen).toBe(2); // ranks 1 and 3
    expect(stats.want).toBe(2); // ranks 2 and 3
  });
});

describe("calculateStats — showing count", () => {
  test("showing reflects filtered count, not total", () => {
    // Even if total is 10, showing only 3 (e.g. after a search)
    const stats = calculateStats(SAMPLE_MOVIES, {}, 3);
    expect(stats.showing).toBe(3);
  });

  test("showing=0 for empty filter results (empty state message)", () => {
    expect(calculateStats(SAMPLE_MOVIES, {}, 0).showing).toBe(0);
  });

  test("remaining is always from full list regardless of showing", () => {
    // Filters don't change how many are 'remaining' (unwatched total)
    const stats = calculateStats(SAMPLE_MOVIES, {}, 3);
    expect(stats.remaining).toBe(10); // still 10 unseen out of 10 total
  });
});

describe("calculateStats — key invariant: seen + remaining === total", () => {
  /**
   * This invariant must always hold: the sum of seen and remaining equals
   * the total movie count (100 in production, 10 in these tests).
   */
  test("invariant holds with no movies seen", () => {
    const stats = calculateStats(SAMPLE_MOVIES, {}, 10);
    expect(stats.seen + stats.remaining).toBe(SAMPLE_MOVIES.length);
  });

  test("invariant holds with some movies seen", () => {
    const userState = { 2: { seen: true }, 7: { seen: true } };
    const stats = calculateStats(SAMPLE_MOVIES, userState, 8);
    expect(stats.seen + stats.remaining).toBe(SAMPLE_MOVIES.length);
  });

  test("invariant holds when all movies are seen", () => {
    const userState = {};
    SAMPLE_MOVIES.forEach((m) => { userState[m.rank] = { seen: true }; });
    const stats = calculateStats(SAMPLE_MOVIES, userState, 0);
    expect(stats.seen + stats.remaining).toBe(SAMPLE_MOVIES.length);
  });
});
