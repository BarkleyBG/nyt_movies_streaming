# AGENTS.md — Instructions for AI Agents

This document tells AI coding assistants (Claude Code, Copilot, Cursor, etc.) how to work safely and effectively in this repository.

---

## Repository overview

Single-page static web app. All application logic lives in **`index.html`** (inline `<script>` tag). There is no build system, no bundler, no framework. The Python script `fetch_streaming.py` is a standalone data fetcher, not part of the app runtime.

---

## Key constraints

### Do not add a build system
The app intentionally has zero build dependencies. Do not introduce webpack, Vite, Rollup, TypeScript compilation, or any other build step. If you need to test new logic, add it directly to the script block in `index.html`.

### Do not modularize index.html
JavaScript functions in `index.html` are **not exported** (no ES modules, no CommonJS). Unit tests in `tests/unit/` duplicate pure logic functions — this is by design. Do not refactor the app into separate `.js` files unless explicitly asked.

### Do not commit `.env`
The file `.env` contains `RAPIDAPI_KEY` and is gitignored. Never include API keys in committed files.

### Do not commit `streaming_data.json` with real API keys or PII
`streaming_data.json` is committed (it's static data the app needs), but it should only contain movie metadata and service IDs. The `raw` field includes third-party API responses — do not expand what gets stored there.

---

## Where things live

| What | Where |
|------|--------|
| App HTML/CSS/JS | `index.html` |
| Streaming data fetcher | `fetch_streaming.py` |
| Fetched data (committed) | `streaming_data.json` |
| JS unit tests | `tests/unit/*.test.js` |
| Integration tests | `tests/integration/app.spec.js` |
| Python tests | `tests/python/test_fetch_streaming.py` |
| Test runner config | `jest.config.js`, `playwright.config.js` |
| Dev server config | `.claude/launch.json` |

---

## Running the app

```bash
python -m http.server 3000
# → open http://localhost:3000
```

Or use the Claude Code preview server (configured in `.claude/launch.json`).

---

## Running tests

```bash
# JS unit tests (fast, no browser needed)
npx jest --testPathPattern="tests/unit"

# Python tests
C:/Python314/python.exe -m pytest tests/python/ -v

# Integration tests (auto-starts HTTP server on port 3000)
npx playwright test tests/integration/app.spec.js

# All tests
npm run test:all
```

**All 205 tests must pass before merging.**

---

## Adding or modifying features

1. **UI/logic changes** → edit `index.html` only.
2. **Streaming data schema changes** → update both `fetch_streaming.py` and the JS parser in `index.html`, and update `tests/python/test_fetch_streaming.py`.
3. **New filter/sort logic** → add corresponding unit tests in `tests/unit/filtering.test.js`.
4. **New state management** → add corresponding unit tests in `tests/unit/state.test.js`.
5. **New stats calculations** → add corresponding unit tests in `tests/unit/stats.test.js`.

---

## Streaming services

The tracked services (US, subscription/free only) are:

`netflix` · `disney` · `hulu` · `prime` · `peacock` · `hbo` · `apple` · `paramount` · `tubi` · `starz`

Service IDs must match between `fetch_streaming.py` (`US_SERVICES`) and `index.html` (CSS classes and badge rendering).

---

## localStorage

User data is stored under the key `nyt100_user_data` as a JSON object keyed by rank number. Schema per entry:

```json
{
  "seen": true,
  "want": false,
  "notes": "optional string"
}
```

Do not change this key name without a migration path — existing users would lose their data.

---

## What agents should NOT do

- Do not run `fetch_streaming.py` autonomously — it consumes paid API quota (100 req/day limit).
- Do not delete or overwrite `streaming_data.json` without user confirmation.
- Do not add new npm dependencies to `package.json` without asking — the package is intentionally minimal (test-only deps).
- Do not push to `main` or create PRs without explicit user instruction.
