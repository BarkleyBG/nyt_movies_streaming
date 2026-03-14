# Refresh streaming data

Fetches current US streaming availability for all 100 movies from the Streaming Availability API. Saves full API responses to `streaming_data_raw.json` (gitignored) and generates a clean `streaming_data.json` (committed) with service IDs and a per-movie `fetched_at` date.

**Requires:** `RAPIDAPI_KEY` set in `.env` (not needed for `--clean-only`)
**Quota:** 100 API requests — uses the full free-tier daily allowance. Confirm with the user before running.

## CLI modes

| Flag | Behavior |
|------|----------|
| *(none)* | Fetch all movies **and** write clean output |
| `--fetch-only` | Fetch raw data only; skip writing `streaming_data.json` |
| `--clean-only` | Re-generate `streaming_data.json` from existing raw cache; no API calls |

## Steps

1. Confirm the user wants to refresh (this costs API quota).
2. Check that `.env` exists and contains `RAPIDAPI_KEY`.
3. Run: `python3 fetch_streaming.py`
4. Watch for errors — HTTP 429 means rate limit hit, HTTP 401/403 means bad key.
5. After completion, report: total fetched, total cached, movies with streaming availability, and service breakdown.
6. Note: `streaming_data_raw.json` is updated incrementally during the run, so partial runs are safe to resume. The clean `streaming_data.json` is generated at the end.
