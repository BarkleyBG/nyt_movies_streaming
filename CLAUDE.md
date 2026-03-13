# CLAUDE.md — Claude Code Project Config

## Project in one sentence
Static single-page app + Python data fetcher. No build system. All JS lives in `index.html`.

## Rules

- **Never modularize `index.html`** — no separate `.js` files, no ES modules, no build tools.
- **Never run `fetch_streaming.py` unprompted** — costs paid API quota (100 req/day free plan).
- **Never overwrite `streaming_data.json`** without explicit user instruction.
- **Never add npm dependencies** without asking — `package.json` has test-only deps by design.
- **Always run tests** after logic changes. See run commands below.

## Dev server

Already configured in `.claude/launch.json`. Start with:
```
preview_start: nyt-movies  (port 3000)
```
Or manually: `python -m http.server 3000`

## Test commands

```bash
# Unit tests (fast)
npx jest --testPathPattern="tests/unit"

# Python tests
C:/Python314/python.exe -m pytest tests/python/ -v

# Integration tests
npx playwright test tests/integration/app.spec.js

# All 205 tests
npm run test:all
```

## Key files

| File | Role |
|------|------|
| `index.html` | Entire app |
| `fetch_streaming.py` | One-shot API fetcher |
| `streaming_data.json` | Output of fetcher; served statically |
| `tests/unit/` | Jest — pure logic duplicated from index.html |
| `tests/integration/` | Playwright — full browser E2E |
| `tests/python/` | pytest — fetcher logic |

## localStorage

Key: `nyt100_user_data` — do not rename without a migration.

## Slash commands

| Command | What it does |
|---------|-------------|
| `/refresh-streaming` | Runs `fetch_streaming.py` to update streaming data |
| `/test` | Runs the full test suite |
