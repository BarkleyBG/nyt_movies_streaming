/**
 * Unit tests for the movie filtering, sorting, and search logic.
 *
 * These test the pure business logic that drives getFiltered() in index.html.
 * Because the app ships as a single HTML file with no module exports, we
 * duplicate the pure functions here so they can be tested in isolation —
 * a standard pattern for embedded-script apps. Integration tests (app.spec.js)
 * verify the actual HTML code end-to-end in a real browser.
 */

// ─── Minimal test dataset ────────────────────────────────────────────────────
// Five movies representative of the 100 in index.html.
const MOVIES = [
  { rank: 1, title: "Parasite",            year: 2019, director: "Bong Joon-ho",        streaming: ["hbo"] },
  { rank: 2, title: "Mulholland Drive",    year: 2001, director: "David Lynch",          streaming: ["netflix"] },
  { rank: 3, title: "There Will Be Blood", year: 2007, director: "Paul Thomas Anderson", streaming: ["prime"] },
  { rank: 4, title: "In the Mood for Love",year: 2000, director: "Wong Kar-wai",         streaming: [] },
  { rank: 5, title: "Moonlight",           year: 2016, director: "Barry Jenkins",        streaming: ["netflix", "prime"] },
];

// ─── Pure logic mirroring getFiltered() in index.html ───────────────────────
/**
 * Returns a filtered and sorted copy of the movies array.
 *
 * Mirrors the getFiltered() function in index.html exactly so that any
 * algorithm change to that function can be caught by updating this copy.
 *
 * @param {object[]} movies    - Full movie array
 * @param {object}   userState - { [rank]: { seen, want } }
 * @param {object}   opts      - Filter/sort options
 */
function getFiltered(
  movies,
  userState,
  { searchQuery = "", activeServices = new Set(), activeShow = "all", sortMode = "rank" } = {}
) {
  let list = [...movies];

  // Text search: matches title, director, or year
  if (searchQuery) {
    const q = searchQuery.toLowerCase();
    list = list.filter(
      (m) =>
        m.title.toLowerCase().includes(q) ||
        m.director.toLowerCase().includes(q) ||
        String(m.year).includes(q)
    );
  }

  // Streaming service filter (multi-select: show movies on any selected service)
  if (activeServices.size > 0) {
    list = list.filter((m) => m.streaming.some((s) => activeServices.has(s)));
  }

  // Watch-status filter
  if (activeShow === "unseen") {
    list = list.filter((m) => !userState[m.rank]?.seen);
  } else if (activeShow === "seen") {
    list = list.filter((m) => userState[m.rank]?.seen);
  } else if (activeShow === "want") {
    list = list.filter((m) => userState[m.rank]?.want);
  }

  // Sort
  if (sortMode === "alpha") {
    list.sort((a, b) => a.title.localeCompare(b.title));
  } else if (sortMode === "year") {
    list.sort((a, b) => a.year - b.year || a.rank - b.rank);
  } else {
    list.sort((a, b) => a.rank - b.rank);
  }

  return list;
}

// ─── Search tests ─────────────────────────────────────────────────────────────
describe("getFiltered — search", () => {
  test("returns all movies when no filters are applied", () => {
    expect(getFiltered(MOVIES, {})).toHaveLength(5);
  });

  test("filters by title (case-insensitive)", () => {
    const result = getFiltered(MOVIES, {}, { searchQuery: "parasite" });
    expect(result).toHaveLength(1);
    expect(result[0].title).toBe("Parasite");
  });

  test("filters by director name (partial match)", () => {
    // "paul thomas" matches Paul Thomas Anderson only
    const result = getFiltered(MOVIES, {}, { searchQuery: "paul thomas" });
    expect(result).toHaveLength(1);
    expect(result[0].title).toBe("There Will Be Blood");
  });

  test("filters by release year as a string", () => {
    const result = getFiltered(MOVIES, {}, { searchQuery: "2019" });
    expect(result).toHaveLength(1);
    expect(result[0].title).toBe("Parasite");
  });

  test("returns empty array when nothing matches", () => {
    expect(
      getFiltered(MOVIES, {}, { searchQuery: "xyznonexistentfilm999" })
    ).toHaveLength(0);
  });

  test("matches partial title strings", () => {
    // "mood" matches "In the Mood for Love"
    const result = getFiltered(MOVIES, {}, { searchQuery: "mood" });
    expect(result).toHaveLength(1);
    expect(result[0].title).toBe("In the Mood for Love");
  });

  test("uppercase search still returns results (case-insensitive)", () => {
    const result = getFiltered(MOVIES, {}, { searchQuery: "MOONLIGHT" });
    expect(result).toHaveLength(1);
    expect(result[0].title).toBe("Moonlight");
  });
});

// ─── Streaming filter tests ───────────────────────────────────────────────────
describe("getFiltered — streaming service filter", () => {
  test("filters by single service (netflix)", () => {
    // Mulholland Drive (netflix) and Moonlight (netflix + prime)
    const result = getFiltered(MOVIES, {}, { activeServices: new Set(["netflix"]) });
    expect(result).toHaveLength(2);
    expect(result.map((m) => m.title)).toContain("Mulholland Drive");
    expect(result.map((m) => m.title)).toContain("Moonlight");
  });

  test("returns empty array when no movies on a service", () => {
    expect(getFiltered(MOVIES, {}, { activeServices: new Set(["disney"]) })).toHaveLength(0);
  });

  test("handles movies on multiple streaming services", () => {
    // Prime: There Will Be Blood + Moonlight
    const result = getFiltered(MOVIES, {}, { activeServices: new Set(["prime"]) });
    expect(result).toHaveLength(2);
  });

  test("empty activeServices set returns all movies", () => {
    expect(getFiltered(MOVIES, {}, { activeServices: new Set() })).toHaveLength(5);
  });

  test("hbo filter returns Parasite only", () => {
    const result = getFiltered(MOVIES, {}, { activeServices: new Set(["hbo"]) });
    expect(result).toHaveLength(1);
    expect(result[0].title).toBe("Parasite");
  });

  test("movies with empty streaming array are excluded by any service filter", () => {
    // In the Mood for Love has streaming: []
    const result = getFiltered(MOVIES, {}, { activeServices: new Set(["prime"]) });
    expect(result.map((m) => m.title)).not.toContain("In the Mood for Love");
  });

  test("multi-select: netflix + prime returns union of results", () => {
    // netflix: Mulholland Drive, Moonlight; prime: There Will Be Blood, Moonlight
    // union: Mulholland Drive, There Will Be Blood, Moonlight (3 unique)
    const result = getFiltered(MOVIES, {}, { activeServices: new Set(["netflix", "prime"]) });
    expect(result).toHaveLength(3);
    expect(result.map((m) => m.title)).toContain("Mulholland Drive");
    expect(result.map((m) => m.title)).toContain("There Will Be Blood");
    expect(result.map((m) => m.title)).toContain("Moonlight");
  });

  test("multi-select: netflix + hbo returns 3 movies", () => {
    // netflix: Mulholland Drive, Moonlight; hbo: Parasite
    const result = getFiltered(MOVIES, {}, { activeServices: new Set(["netflix", "hbo"]) });
    expect(result).toHaveLength(3);
  });
});

// ─── Show filter tests ────────────────────────────────────────────────────────
describe("getFiltered — show (watch-status) filter", () => {
  // Parasite: seen=true; Moonlight: want=true; rest: untouched
  const userState = {
    1: { seen: true, want: false },
    5: { seen: false, want: true },
  };

  test("'all' shows every movie regardless of status", () => {
    expect(getFiltered(MOVIES, userState, { activeShow: "all" })).toHaveLength(5);
  });

  test("'seen' shows only movies marked as seen", () => {
    const result = getFiltered(MOVIES, userState, { activeShow: "seen" });
    expect(result).toHaveLength(1);
    expect(result[0].title).toBe("Parasite");
  });

  test("'unseen' excludes movies marked as seen", () => {
    const result = getFiltered(MOVIES, userState, { activeShow: "unseen" });
    expect(result).toHaveLength(4);
    expect(result.map((m) => m.title)).not.toContain("Parasite");
  });

  test("'want' shows only movies marked want-to-see", () => {
    const result = getFiltered(MOVIES, userState, { activeShow: "want" });
    expect(result).toHaveLength(1);
    expect(result[0].title).toBe("Moonlight");
  });

  test("'unseen' with empty user state returns all movies", () => {
    expect(getFiltered(MOVIES, {}, { activeShow: "unseen" })).toHaveLength(5);
  });

  test("'seen' with empty user state returns no movies", () => {
    expect(getFiltered(MOVIES, {}, { activeShow: "seen" })).toHaveLength(0);
  });

  test("'want' with empty user state returns no movies", () => {
    expect(getFiltered(MOVIES, {}, { activeShow: "want" })).toHaveLength(0);
  });

  test("seen flag false is treated same as unset (shown in unseen)", () => {
    // rank 5 has seen: false explicitly; should appear in unseen filter
    const result = getFiltered(MOVIES, userState, { activeShow: "unseen" });
    expect(result.map((m) => m.title)).toContain("Moonlight");
  });
});

// ─── Sort tests ───────────────────────────────────────────────────────────────
describe("getFiltered — sort modes", () => {
  test("default (rank) sort orders by rank ascending", () => {
    const result = getFiltered(MOVIES, {}, { sortMode: "rank" });
    expect(result.map((m) => m.rank)).toEqual([1, 2, 3, 4, 5]);
  });

  test("alphabetical sort is A→Z by title", () => {
    const result = getFiltered(MOVIES, {}, { sortMode: "alpha" });
    const titles = result.map((m) => m.title);
    // Expected alpha order: In the Mood for Love, Moonlight, Mulholland Drive, Parasite, There Will Be Blood
    expect(titles[0]).toBe("In the Mood for Love");
    expect(titles[4]).toBe("There Will Be Blood");
  });

  test("year sort orders oldest → newest", () => {
    const result = getFiltered(MOVIES, {}, { sortMode: "year" });
    const years = result.map((m) => m.year);
    expect(years[0]).toBe(2000); // In the Mood for Love
    expect(years[years.length - 1]).toBe(2019); // Parasite
  });

  test("year sort uses rank as tiebreaker when years are equal", () => {
    const sameYear = [
      { rank: 3, title: "C", year: 2007, director: "X", streaming: [] },
      { rank: 1, title: "A", year: 2007, director: "Y", streaming: [] },
      { rank: 2, title: "B", year: 2007, director: "Z", streaming: [] },
    ];
    const result = getFiltered(sameYear, {}, { sortMode: "year" });
    expect(result.map((m) => m.rank)).toEqual([1, 2, 3]);
  });

  test("alpha sort handles titles starting with 'The' correctly (localeCompare)", () => {
    // localeCompare puts 'T' after 'M' and 'I', so "The Social Network" comes after "Moonlight"
    const result = getFiltered(MOVIES, {}, { sortMode: "alpha" });
    const moonlightIdx = result.findIndex((m) => m.title === "Moonlight");
    const thereIdx = result.findIndex((m) => m.title === "There Will Be Blood");
    expect(moonlightIdx).toBeLessThan(thereIdx);
  });
});

// ─── Combined filter tests ────────────────────────────────────────────────────
describe("getFiltered — combined filters", () => {
  test("search + streaming filter narrows results", () => {
    // 'light' matches Moonlight (netflix); only 1 result
    const result = getFiltered(MOVIES, {}, {
      searchQuery: "light",
      activeServices: new Set(["netflix"]),
    });
    expect(result).toHaveLength(1);
    expect(result[0].title).toBe("Moonlight");
  });

  test("streaming filter + unseen filter excludes seen movie on that service", () => {
    // Moonlight is on netflix and marked seen
    const userState = { 5: { seen: true } };
    const result = getFiltered(MOVIES, userState, {
      activeServices: new Set(["netflix"]),
      activeShow: "unseen",
    });
    // Only Mulholland Drive (netflix, not seen) remains
    expect(result).toHaveLength(1);
    expect(result[0].title).toBe("Mulholland Drive");
  });

  test("all filters together: search + service + show + sort", () => {
    // Search 'moon', prime service, unseen, sorted by alpha
    const userState = {}; // Moonlight unseen
    const result = getFiltered(MOVIES, userState, {
      searchQuery: "moon",
      activeServices: new Set(["prime"]),
      activeShow: "unseen",
      sortMode: "alpha",
    });
    expect(result).toHaveLength(1);
    expect(result[0].title).toBe("Moonlight");
  });
});
