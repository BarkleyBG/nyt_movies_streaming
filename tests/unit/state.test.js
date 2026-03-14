/**
 * Unit tests for localStorage-based state management.
 *
 * Covers loadState(), saveState(), and the toggle logic used in the
 * movie card click handler — all extracted from index.html's <script> block.
 *
 * A mock storage object is used so tests never touch real localStorage,
 * keeping them hermetic and order-independent.
 */

// ─── Constants matching index.html ────────────────────────────────────────────
const STORAGE_KEY = "nyt100_user_data";

// ─── Pure logic mirroring index.html ─────────────────────────────────────────

/**
 * Loads persisted user state from storage.
 * Returns an empty object on missing or corrupt data (silent fail).
 * @param {Storage} storage - localStorage-compatible object
 * @returns {{ [rank: number]: { seen?: boolean, want?: boolean } }}
 */
function loadState(storage) {
  try {
    const raw = storage.getItem(STORAGE_KEY);
    if (raw) return JSON.parse(raw);
  } catch (e) {
    // Corrupted storage — return clean state
  }
  return {};
}

/**
 * Persists user state to storage.
 * Silently ignores write errors (e.g. QuotaExceededError in private browsing).
 * @param {{ [rank: number]: { seen?: boolean, want?: boolean } }} state
 * @param {Storage} storage
 */
function saveState(state, storage) {
  try {
    storage.setItem(STORAGE_KEY, JSON.stringify(state));
  } catch (e) {
    // Storage unavailable — state is ephemeral this session
  }
}

// ─── Test helpers ─────────────────────────────────────────────────────────────

/**
 * Creates an isolated, in-memory mock that has the same API as localStorage.
 * Each call produces a fresh store, so tests cannot bleed into each other.
 */
function createMockStorage() {
  const store = {};
  return {
    getItem: (key) => (Object.prototype.hasOwnProperty.call(store, key) ? store[key] : null),
    setItem: (key, value) => { store[key] = String(value); },
    removeItem: (key) => { delete store[key]; },
    clear: () => { Object.keys(store).forEach((k) => delete store[k]); },
    /** Expose internals for assertion convenience */
    _raw: store,
  };
}

// ─── loadState tests ─────────────────────────────────────────────────────────
describe("loadState", () => {
  test("returns empty object when storage has no data", () => {
    expect(loadState(createMockStorage())).toEqual({});
  });

  test("returns parsed state when valid JSON is stored", () => {
    const storage = createMockStorage();
    const state = { 1: { seen: true, want: false } };
    storage.setItem(STORAGE_KEY, JSON.stringify(state));
    expect(loadState(storage)).toEqual(state);
  });

  test("returns empty object when stored JSON is malformed", () => {
    const storage = createMockStorage();
    storage.setItem(STORAGE_KEY, "{{not valid json}}");
    expect(loadState(storage)).toEqual({});
  });

  test("returns empty object when stored value is an empty string", () => {
    const storage = createMockStorage();
    storage.setItem(STORAGE_KEY, "");
    // "" is falsy → the if (raw) branch is skipped → returns {}
    expect(loadState(storage)).toEqual({});
  });

  test("preserves seen and want flags for multiple movies", () => {
    const storage = createMockStorage();
    const state = {
      5:  { seen: true,  want: false },
      10: { seen: false, want: true  },
      42: { seen: true,  want: true  },
    };
    storage.setItem(STORAGE_KEY, JSON.stringify(state));
    const loaded = loadState(storage);
    expect(loaded[5].seen).toBe(true);
    expect(loaded[10].want).toBe(true);
    expect(loaded[42].seen).toBe(true);
    expect(loaded[42].want).toBe(true);
  });

  test("numeric string keys survive JSON round-trip", () => {
    // JSON.stringify converts numeric object keys to strings, so rank 1 is stored as "1"
    const storage = createMockStorage();
    storage.setItem(STORAGE_KEY, JSON.stringify({ 1: { seen: true } }));
    const loaded = loadState(storage);
    // Access via string key (JS object key coercion)
    expect(loaded["1"].seen).toBe(true);
  });
});

// ─── saveState tests ──────────────────────────────────────────────────────────
describe("saveState", () => {
  test("writes state JSON to storage under the correct key", () => {
    const storage = createMockStorage();
    const state = { 1: { seen: true } };
    saveState(state, storage);
    expect(storage.getItem(STORAGE_KEY)).toBe(JSON.stringify(state));
  });

  test("overwrites the previous state completely on second call", () => {
    const storage = createMockStorage();
    saveState({ 1: { seen: true } }, storage);
    saveState({ 1: { seen: false }, 2: { want: true } }, storage);
    const loaded = JSON.parse(storage.getItem(STORAGE_KEY));
    expect(loaded[1].seen).toBe(false);
    expect(loaded[2].want).toBe(true);
  });

  test("does not throw when storage throws QuotaExceededError", () => {
    const errorStorage = {
      getItem: () => null,
      setItem: () => { throw new Error("QuotaExceededError"); },
    };
    // Should silently swallow the error
    expect(() => saveState({ 1: { seen: true } }, errorStorage)).not.toThrow();
  });

  test("saved state survives a loadState round-trip", () => {
    const storage = createMockStorage();
    const original = { 7: { seen: true, want: false }, 33: { want: true } };
    saveState(original, storage);
    const restored = loadState(storage);
    expect(restored).toEqual(original);
  });
});

// ─── Toggle logic tests ───────────────────────────────────────────────────────
describe("state toggle logic (click handler behavior from index.html)", () => {
  /**
   * The click handler in index.html does:
   *   if (!userState[rank]) userState[rank] = {};
   *   userState[rank][action] = !userState[rank][action];
   *
   * These tests verify that pattern works correctly for all scenarios.
   */

  test("toggling 'seen' on an untracked movie sets it to true", () => {
    const state = {};
    const rank = 1;
    if (!state[rank]) state[rank] = {};
    state[rank].seen = !state[rank].seen; // undefined → true
    expect(state[rank].seen).toBe(true);
  });

  test("toggling 'seen' from true sets it to false", () => {
    const state = { 1: { seen: true } };
    state[1].seen = !state[1].seen;
    expect(state[1].seen).toBe(false);
  });

  test("toggling 'want' does not affect 'seen' on the same movie", () => {
    const state = { 1: { seen: true } };
    if (!state[1]) state[1] = {};
    state[1].want = !state[1].want;
    expect(state[1].seen).toBe(true);  // unchanged
    expect(state[1].want).toBe(true);  // newly toggled
  });

  test("toggling different ranks stays isolated", () => {
    const state = {};
    [1, 5, 10].forEach((rank) => {
      if (!state[rank]) state[rank] = {};
      state[rank].seen = !state[rank].seen; // all → true
    });
    // Toggle rank 5 back off
    state[5].seen = !state[5].seen;
    expect(state[1].seen).toBe(true);  // untouched
    expect(state[5].seen).toBe(false); // toggled back
    expect(state[10].seen).toBe(true); // untouched
  });

  test("double-toggle returns to original state (idempotent via two clicks)", () => {
    const state = {};
    if (!state[1]) state[1] = {};
    state[1].seen = !state[1].seen; // → true
    state[1].seen = !state[1].seen; // → false (back to falsy)
    expect(state[1].seen).toBe(false);
  });
});
