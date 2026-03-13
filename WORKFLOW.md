# Repository Workflow

Concise reference for how data flows through this project.

---

## System overview

```mermaid
graph TD
    API["Streaming Availability API<br/>(RapidAPI / Movie of the Night)"]
    PY["fetch_streaming.py<br/>(Python CLI)"]
    JSON["streaming_data.json<br/>(static file, committed)"]
    HTML["index.html<br/>(app: HTML + CSS + JS)"]
    SERVER["python -m http.server 3000<br/>(static file server)"]
    BROWSER["Browser"]
    LS["localStorage<br/>nyt100_user_data"]

    API -->|"100 HTTP requests<br/>0.6s between each"| PY
    PY -->|"writes/updates"| JSON
    JSON -->|"served as static asset"| SERVER
    SERVER -->|"HTTP"| BROWSER
    HTML -->|"fetch() on load"| JSON
    BROWSER <-->|"read/write watch status,<br/>notes, filters"| LS
```

---

## Data refresh flow

```mermaid
sequenceDiagram
    participant Dev as Developer
    participant Env as .env file
    participant PY as fetch_streaming.py
    participant API as RapidAPI
    participant JSON as streaming_data.json

    Dev->>Env: set RAPIDAPI_KEY
    Dev->>PY: python fetch_streaming.py
    PY->>JSON: load existing (resume support)
    loop For each of 100 movies
        PY->>API: GET /shows/search/title?title=...&country=us
        API-->>PY: show + streamingOptions
        PY->>JSON: write result immediately
        PY->>PY: sleep 0.6s
    end
    PY->>JSON: write _updated timestamp
```

---

## App startup flow

```mermaid
sequenceDiagram
    participant B as Browser
    participant S as HTTP Server
    participant LS as localStorage

    B->>S: GET /index.html
    S-->>B: full app (HTML + CSS + JS)
    B->>S: fetch('/streaming_data.json')
    S-->>B: streaming data (100 movies)
    B->>LS: read nyt100_user_data
    B->>B: merge movie list + streaming data + user data
    B->>B: render cards
```

---

## User interaction flow

```mermaid
stateDiagram-v2
    [*] --> Default: page load
    Default --> Filtered: apply service / status filter
    Filtered --> Default: clear filters
    Default --> Sorted: change sort (rank / title / year)
    Sorted --> Default: reset sort

    state CardActions {
        Unseen --> Seen: mark seen
        Seen --> Unseen: unmark
        Unmarked --> WantToWatch: mark want
        WantToWatch --> Unmarked: unmark
    }

    Default --> CardActions: interact with card
    CardActions --> localStorage: persist state
```

---

## Test structure

```mermaid
graph LR
    subgraph JS["JavaScript (Jest)"]
        FT["filtering.test.js<br/>27 tests"]
        ST["state.test.js<br/>15 tests"]
        SS["stats.test.js<br/>22 tests"]
    end
    subgraph PW["Browser (Playwright)"]
        IT["app.spec.js<br/>106 tests<br/>chromium + firefox"]
    end
    subgraph PY["Python (pytest)"]
        PT["test_fetch_streaming.py<br/>35 tests"]
    end

    FT -. "duplicates pure logic from" .-> HTML2["index.html"]
    ST -. "duplicates pure logic from" .-> HTML2
    SS -. "duplicates pure logic from" .-> HTML2
    IT -- "loads via HTTP" --> HTML2
    PT -- "tests" --> PY2["fetch_streaming.py"]
```

**Total: 205 tests**

---

## File ownership at a glance

| File | Purpose | Edit when |
|------|---------|-----------|
| `index.html` | Entire app | UI, logic, or style changes |
| `fetch_streaming.py` | API data fetcher | Adding movies, changing API params, schema changes |
| `streaming_data.json` | Cached streaming data | Re-run fetcher; do not hand-edit |
| `tests/unit/filtering.test.js` | Filter/sort logic tests | Filter or sort logic changes in index.html |
| `tests/unit/state.test.js` | State management tests | State or localStorage logic changes |
| `tests/unit/stats.test.js` | Stats calculation tests | Stats bar changes |
| `tests/integration/app.spec.js` | End-to-end tests | Any user-visible feature changes |
| `tests/python/test_fetch_streaming.py` | Fetcher unit tests | Changes to fetch_streaming.py |
