# CLAUDE.md — Claude Code Project Config

## Project in one sentence
Static single-page app + Python data fetcher. No build system. All JS lives in `index.html`.

## Rules

- **Never modularize `index.html`** — no separate `.js` files, no ES modules, no build tools.
- **Never run `fetch_streaming.py` unprompted** — costs paid API quota (100 req/day free plan).
- **Never overwrite `streaming_data.json` or `streaming_data_raw.json`** without explicit user instruction.
- **Never add npm dependencies** without asking — `package.json` has test-only deps by design.
- **Always run tests** after logic changes. See run commands below.

## Dev server

Already configured in `.claude/launch.json`. Start with:
```
preview_start: nyt-movies  (port 3001)
```
Or manually: `python3 -m http.server 3001`

## Test commands

```bash
# Unit tests (fast)
npx jest --testPathPattern="tests/unit"

# Python tests
python -m pytest tests/python/ -v

# Integration tests
npx playwright test tests/integration/app.spec.js

# All tests
npm run test:all
```

## Key files

| File | Role |
|------|------|
| `index.html` | Entire app |
| `fetch_streaming.py` | One-shot API fetcher |
| `streaming_data.json` | Clean output (services only); served statically |
| `streaming_data_raw.json` | Full API cache (gitignored) |
| `tests/unit/` | Jest — pure logic duplicated from index.html |
| `tests/integration/` | Playwright — full browser E2E |
| `tests/python/` | pytest — fetcher logic |

## localStorage

Key: `nyt100_user_data` — do not rename without a migration.

## Streaming services (12 total)

`netflix` · `disney` · `hulu` · `prime` · `peacock` · `hbo` · `apple` ·
`paramount` · `tubi` · `starz` · `plutotv` · `criterion`

Defined in two places that **must stay in sync**:
- `fetch_streaming.py` → `US_SERVICES` set
- `index.html` → `SERVICES` array + HTML pills + CSS tag classes

## Key design notes

### Single-file app → test duplication
Unit test files duplicate the pure functions (`getFiltered`, `loadState`,
`saveState`, `calculateStats`) from `index.html` so they can run in isolation.
Integration tests catch drift between the two copies.

### Why `testEnvironment: "node"` (not jsdom)
All unit test files use plain mock objects and pure functions — no `window`,
`document`, or real `localStorage`. Dropping jsdom saves startup overhead.

### Pill counts
After `loadStreamingData()` resolves, each service pill gets a
`<span class="pill-count">N</span>` showing how many of the 100 films
are available on that service.

## Slash commands

| Command | What it does |
|---------|-------------|
| `/refresh-streaming` | Runs `fetch_streaming.py` to update streaming data |
| `/test` | Runs the full test suite |
