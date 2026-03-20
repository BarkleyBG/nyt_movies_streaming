"""
fetch_streaming.py
──────────────────
Queries the Streaming Availability API (Movie of the Night) via RapidAPI
for each movie in movies.json and saves results to streaming_data.json.

Usage:
    1. Copy .env.example to .env and add your RapidAPI key
    2. Run:  python fetch_streaming.py

Free plan: 100 requests/day.
Use --limit N to cap new API calls per run (useful when the list exceeds 100
movies — run on consecutive days to cover the full list incrementally).
"""

import argparse
import datetime
import json
import os
import sys
import time
import urllib.request
import urllib.parse
import urllib.error

# ─── Configuration ───────────────────────────────────────────────────────────

API_BASE = "https://streaming-availability.p.rapidapi.com"
SEARCH_ENDPOINT = "/shows/search/title"
COUNTRY = "us"

# Services we care about (US-based)
US_SERVICES = {"netflix", "disney", "hulu", "prime", "peacock", "hbo", "apple", "paramount", "tubi", "starz", "plutotv", "criterion"}

# Streaming types that count as "available with subscription or free"
INCLUDED_TYPES = {"subscription", "free"}

RAW_FILE = "streaming_data_raw.json"   # full API cache (gitignored)
OUTPUT_FILE = "streaming_data.json"     # clean, minimal (committed)
MOVIES_FILE = "movies.json"
DELAY_BETWEEN_REQUESTS = 0.6  # seconds — be polite to the API


# ─── Movie List ───────────────────────────────────────────────────────────────

def load_movies():
    """Load the shared movie list from movies.json."""
    movies_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), MOVIES_FILE)
    try:
        with open(movies_path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"ERROR: Could not load {MOVIES_FILE}: {e}")
        sys.exit(1)


MOVIES = load_movies()


# ─── Helpers ─────────────────────────────────────────────────────────────────

def load_api_key():
    """Load API key from .env file or environment variable."""
    # Try .env file first
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ[key.strip()] = value.strip()

    api_key = os.environ.get("RAPIDAPI_KEY")
    if not api_key or api_key == "your_rapidapi_key_here":
        print("ERROR: RAPIDAPI_KEY not set.")
        print("  1. Copy .env.example to .env")
        print("  2. Replace 'your_rapidapi_key_here' with your actual key")
        print("  3. Get a free key at: https://rapidapi.com/movie-of-the-night-movie-of-the-night-default/api/streaming-availability")
        sys.exit(1)
    return api_key


def search_movie(title, year, api_key):
    """Search for a movie by title and return the best match."""
    params = urllib.parse.urlencode({
        "title": title,
        "country": COUNTRY,
        "show_type": "movie",
        "output_language": "en",
    })
    url = f"{API_BASE}{SEARCH_ENDPOINT}?{params}"

    req = urllib.request.Request(url, headers={
        "X-RapidAPI-Key": api_key,
        "X-RapidAPI-Host": "streaming-availability.p.rapidapi.com",
    })

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
            # The API returns a list of results; find best match by year
            results = data if isinstance(data, list) else data.get("result", data.get("results", []))
            if not isinstance(results, list):
                results = [results]

            for show in results:
                show_year = show.get("releaseYear") or show.get("year")
                show_title = show.get("title", "")
                # Match by year, or if title matches closely
                if show_year == year:
                    return show
                if show_title.lower() == title.lower():
                    return show
            # Fallback: return first result if any
            return results[0] if results else None

    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ""
        print(f"    HTTP {e.code}: {body[:200]}")
        if e.code == 429:
            print("    Rate limit hit! You may have exceeded 100 requests/day.")
        return None
    except Exception as e:
        print(f"    Error: {e}")
        return None


def extract_streaming(show):
    """Extract US streaming availability from a show result."""
    if not show:
        return []

    services_found = []
    streaming_options = show.get("streamingOptions", {})

    # The API returns streamingOptions as a dict keyed by country code
    us_options = streaming_options.get("us", [])

    for option in us_options:
        service = option.get("service", {})
        service_id = service.get("id", "")
        stream_type = option.get("type", "")

        # Only include US services we care about, with subscription or free access
        if service_id in US_SERVICES and stream_type in INCLUDED_TYPES:
            if service_id not in services_found:
                services_found.append(service_id)

    return services_found


# ─── Main ────────────────────────────────────────────────────────────────────

def fetch_raw(api_key, limit=None):
    """
    Fetch raw API data for all movies and save to RAW_FILE.

    limit: if set, cap the number of *new* API calls per run. Cached entries
           don't count against the limit. Useful for staying within the free
           tier (100 req/day) when the movie list exceeds 100 entries — just
           run the script on consecutive days to cover the full list.

    Returns results, fetched, skipped.
    """
    # Load existing raw data to support resuming interrupted runs
    existing_data = {}
    if os.path.exists(RAW_FILE):
        try:
            with open(RAW_FILE) as f:
                existing_data = json.load(f)
            print(f"Loaded {len(existing_data)} existing entries from {RAW_FILE}")
        except (json.JSONDecodeError, IOError):
            pass

    results = dict(existing_data)
    total = len(MOVIES)
    skipped = 0
    fetched = 0

    limit_str = f" (limit: {limit} new fetches)" if limit is not None else ""
    print(f"\nFetching streaming data for {total} movies{limit_str}...")
    print(f"API: Streaming Availability (Movie of the Night) via RapidAPI")
    print(f"Region: US | Included types: {', '.join(INCLUDED_TYPES)}")
    print("=" * 60)

    for i, movie in enumerate(MOVIES):
        rank_key = str(movie["rank"])

        # Skip if we already have data for this movie (not the _updated metadata key)
        if rank_key in existing_data and rank_key != "_updated":
            skipped += 1
            services = existing_data[rank_key].get("services", [])
            print(f"[{i+1:3d}/{total}] (cached)  #{movie['rank']:3d} {movie['title']} -> {services or 'none'}")
            continue

        # Stop if we've hit the per-run limit
        if limit is not None and fetched >= limit:
            print(f"[{i+1:3d}/{total}] (limit reached — stopping after {limit} new fetches)")
            break

        print(f"[{i+1:3d}/{total}] Fetching #{movie['rank']:3d} {movie['title']} ({movie['year']})...", end=" ")

        show = search_movie(movie["title"], movie["year"], api_key)
        services = extract_streaming(show)

        # Store result with full raw data for future reference
        results[rank_key] = {
            "title": movie["title"],
            "year": movie["year"],
            "services": services,
            "fetched_at": datetime.date.today().isoformat(),
            "raw": {
                "id": show.get("id") if show else None,
                "imdbId": show.get("imdbId") if show else None,
                "title": show.get("title") if show else None,
                "releaseYear": show.get("releaseYear") if show else None,
                "streamingOptions": show.get("streamingOptions") if show else None,
            } if show else None,
        }

        fetched += 1
        print(f"-> {services or 'not streaming'}")

        # Save raw data after each request so progress isn't lost
        with open(RAW_FILE, "w") as f:
            json.dump(results, f, indent=2)

        # Be polite — don't hammer the API
        if i < total - 1:
            time.sleep(DELAY_BETWEEN_REQUESTS)

    # Add timestamp
    updated_date = datetime.date.today().strftime("%B %d, %Y")
    results["_updated"] = updated_date

    # Save full raw data (gitignored — for caching/debugging)
    with open(RAW_FILE, "w") as f:
        json.dump(results, f, indent=2)

    print("=" * 60)
    print(f"Done! Fetched: {fetched}, Cached: {skipped}, Total: {total}")
    print(f"Raw data saved to {RAW_FILE}")
    return results, fetched, skipped


def clean_raw(results=None):
    """Load raw results (or use provided dict), generate clean summary, and save to OUTPUT_FILE."""
    if results is None:
        if not os.path.exists(RAW_FILE):
            print(f"No raw data found ({RAW_FILE}). Run fetch first.")
            return None
        try:
            with open(RAW_FILE) as f:
                results = json.load(f)
        except (json.JSONDecodeError, IOError):
            print(f"Failed to read {RAW_FILE}")
            return None

    # Generate clean, minimal output for the website (committed)
    clean = {}
    for key, value in results.items():
        if key == "_updated":
            clean["_updated"] = value
        elif isinstance(value, dict):
            entry = {"services": value.get("services", [])}
            if "fetched_at" in value:
                entry["fetched_at"] = value["fetched_at"]
            clean[key] = entry
    with open(OUTPUT_FILE, "w") as f:
        json.dump(clean, f, indent=2)

    print(f"Clean data saved to {OUTPUT_FILE}")

    # Summary
    total = len(MOVIES)
    with_streaming = sum(1 for v in results.values() if isinstance(v, dict) and v.get("services"))
    print(f"\nMovies with streaming availability: {with_streaming}/{total}")
    service_counts = {}
    for v in results.values():
        if not isinstance(v, dict):
            continue
        for s in v.get("services", []):
            service_counts[s] = service_counts.get(s, 0) + 1
    if service_counts:
        print("Service breakdown:")
        for svc, count in sorted(service_counts.items(), key=lambda x: -x[1]):
            print(f"  {svc:10s}: {count} movies")


def main():
    parser = argparse.ArgumentParser(description="Fetch and/or clean streaming availability data")
    parser.add_argument("--fetch-only", action="store_true", help="Only fetch raw API data and save to streaming_data_raw.json")
    parser.add_argument("--clean-only", action="store_true", help="Only clean existing raw data into streaming_data.json")
    parser.add_argument("--limit", type=int, default=None, metavar="N",
                        help="Cap new API calls per run (for free-tier batching across days)")
    args = parser.parse_args()

    if args.fetch_only and args.clean_only:
        print("Cannot use --fetch-only and --clean-only together.")
        sys.exit(1)

    # If cleaning only, don't require API key
    if args.clean_only:
        clean_raw()
        return

    # If fetching (or default), ensure API key is loaded
    if args.fetch_only or not args.clean_only:
        api_key = load_api_key()
        results, fetched, skipped = fetch_raw(api_key, limit=args.limit)

    # If fetch-only requested, stop here
    if args.fetch_only:
        return

    # Default: clean using results from fetch, or load from file if results is None
    clean_raw(results if 'results' in locals() else None)


if __name__ == "__main__":
    main()
