# Streaming the Top 100

**Which of the NYT's 100 best movies of the 21st century can you stream right now?**

A single-page tracker that overlays real-time US streaming availability on the [New York Times' 2025 Best Movies of the 21st Century](https://www.nytimes.com/interactive/2025/movies/best-movies-21st-century.html) list. Mark films as seen or want-to-watch; everything saves locally in your browser.

---

## Features

- Live streaming badges (Netflix, Disney+, Hulu, Prime, Peacock, HBO Max, Apple TV+, Paramount+, Tubi, Starz)
- Filter by streaming service, seen/unseen status, or want-to-watch
- Progress stats: seen count, want-to-watch count, % of list you can stream
- Persistent per-movie notes and watch status — stored in `localStorage`, no account needed
- Zero dependencies, zero build step — one HTML file

---

## Quick start

```bash
# 1. Clone
git clone https://github.com/your-username/nyt-movies.git
cd nyt-movies

# 2. Serve (any static server works)
python3 -m http.server 3001

# 3. Open
open http://localhost:3001
```

Streaming data is already included in `streaming_data.json`. You only need the API key if you want to refresh it.

---

## Refreshing streaming data

Streaming availability changes frequently. To update `streaming_data.json`:

### 1. Get a RapidAPI key

Sign up at [RapidAPI](https://rapidapi.com/movie-of-the-night-movie-of-the-night-default/api/streaming-availability) and subscribe to the **Streaming Availability** API (Movie of the Night). The free plan provides 100 requests/day — exactly enough for one full refresh.

### 2. Set your key

```bash
echo "RAPIDAPI_KEY=your_key_here" > .env
```

### 3. Run the fetcher

```bash
# Fetch all 100 movies and generate clean output (default)
python fetch_streaming.py

# Fetch raw data only (skip writing streaming_data.json until you're ready)
python fetch_streaming.py --fetch-only

# Re-generate streaming_data.json from existing raw cache without API calls
python fetch_streaming.py --clean-only
```

The script resumes from where it left off if interrupted (safe to re-run). Progress is saved after every request to `streaming_data_raw.json` (gitignored). When complete, it generates a clean `streaming_data.json` containing service IDs and a per-movie `fetched_at` date.

---

## Project structure

```
nyt-movies/
├── index.html              # Full app — HTML, CSS, and JS all inline
├── fetch_streaming.py      # Fetches streaming data from RapidAPI
├── streaming_data.json     # Clean output (services only); loaded by the app
├── streaming_data_raw.json # Full API cache (gitignored)
├── .env                    # RAPIDAPI_KEY (gitignored)
│
├── tests/
│   ├── unit/
│   │   ├── filtering.test.js   # Filter/sort logic (27 tests)
│   │   ├── state.test.js       # State management (15 tests)
│   │   └── stats.test.js       # Stats calculation (22 tests)
│   ├── integration/
│   │   └── app.spec.js         # End-to-end Playwright tests (106 tests)
│   └── python/
│       └── test_fetch_streaming.py  # Python fetcher tests (35 tests)
│
├── AGENTS.md               # Instructions for AI agents
├── WORKFLOW.md             # System architecture diagram
├── CLAUDE.md               # Claude Code project config
├── jest.config.js
├── playwright.config.js
└── package.json
```

---

## Testing

```bash
# Install JS test deps (first time only)
npm install

# Unit tests only (fast, no browser)
npm run test:unit

# Python tests
python3 -m pytest tests/python/ -v

# Integration tests (requires Chromium/Firefox; auto-starts server)
npx playwright test tests/integration/app.spec.js

# Everything
npm run test:all
```

**Total: 205 tests across 5 suites** (Jest + Playwright + pytest)

---

## Architecture notes

- **No build system.** All JavaScript lives in a `<script>` tag inside `index.html`. Functions are not exported — unit tests duplicate pure logic functions, which is the standard pattern for embedded scripts.
- **No backend.** The app is purely static. `fetch_streaming.py` is a one-time data fetcher, not a server.
- **localStorage key:** `nyt100_user_data` — stores seen/want/notes per rank.
- **Streaming data format:** `streaming_data.json` is keyed by rank (`"1"` … `"100"`) plus `"_updated"` (last-fetch date). Each entry contains `services` (array of service IDs) and `fetched_at` (ISO date the record was last fetched, e.g. `"2026-03-14"`). Full API responses are cached locally in `streaming_data_raw.json` (gitignored).

---

## Disclaimers

- Streaming availability data is US-only and may lag reality by days or weeks.
- The NYT list is used for personal, non-commercial reference only.
- This project is not affiliated with the New York Times.
