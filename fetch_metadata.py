"""
fetch_metadata.py
─────────────────
Queries the TMDB (The Movie Database) API for each movie in movies.json
and saves genres, overview, runtime, and top cast to movie_metadata.json.

Usage:
    1. Copy .env.example to .env and add your TMDB API key
    2. Run:  python fetch_metadata.py

TMDB API:
    Free tier — no daily cap; rate limit is ~40 requests/10 seconds.
    Two API calls per movie: search + details+credits (via append_to_response).
    Get a free key at: https://www.themoviedb.org/settings/api

Output files:
    movie_metadata_raw.json  — full TMDB response cache (gitignored)
    movie_metadata.json      — clean output served by the app (committed)
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

TMDB_BASE = "https://api.themoviedb.org/3"
CAST_LIMIT = 3          # top N cast members to store
DELAY_BETWEEN_REQUESTS = 0.3  # seconds — well within TMDB's rate limit

RAW_FILE    = "movie_metadata_raw.json"
OUTPUT_FILE = "movie_metadata.json"
MOVIES_FILE = "movies.json"


# ─── Helpers ─────────────────────────────────────────────────────────────────

def load_movies():
    """Load the shared movie list from movies.json."""
    movies_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), MOVIES_FILE)
    try:
        with open(movies_path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"ERROR: Could not load {MOVIES_FILE}: {e}")
        sys.exit(1)


def load_api_key():
    """Load TMDB API key from .env file or environment variable."""
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ[key.strip()] = value.strip()

    api_key = os.environ.get("TMDB_API_KEY")
    if not api_key or api_key == "your_tmdb_api_key_here":
        print("ERROR: TMDB_API_KEY not set.")
        print("  1. Copy .env.example to .env")
        print("  2. Replace 'your_tmdb_api_key_here' with your actual key")
        print("  3. Get a free key at: https://www.themoviedb.org/settings/api")
        sys.exit(1)
    return api_key


def tmdb_get(path, params, api_key):
    """Make a GET request to the TMDB API. Returns parsed JSON or None on error."""
    params["api_key"] = api_key
    url = f"{TMDB_BASE}{path}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ""
        print(f"    HTTP {e.code}: {body[:200]}")
        if e.code == 429:
            print("    Rate limit hit — waiting 10s before retrying...")
            time.sleep(10)
            # one retry
            try:
                with urllib.request.urlopen(req, timeout=15) as resp:
                    return json.loads(resp.read().decode())
            except Exception:
                pass
        return None
    except Exception as e:
        print(f"    Error: {e}")
        return None


def search_tmdb(title, year, api_key):
    """Search TMDB for a movie. Returns the best-matching result dict or None."""
    data = tmdb_get("/search/movie", {"query": title, "year": year, "language": "en-US"}, api_key)
    if not data:
        return None

    results = data.get("results", [])
    if not results:
        # Retry without year constraint (some films are off by 1)
        data = tmdb_get("/search/movie", {"query": title, "language": "en-US"}, api_key)
        results = data.get("results", []) if data else []

    if not results:
        return None

    # Prefer exact year match, then ±1 year, then first result
    for r in results:
        if r.get("release_date", "")[:4] == str(year):
            return r
    for r in results:
        release_year = int(r.get("release_date", "0000")[:4] or 0)
        if abs(release_year - year) <= 1:
            return r
    return results[0]


def fetch_movie_details(tmdb_id, api_key):
    """Fetch movie details + credits in a single API call. Returns dict or None."""
    return tmdb_get(
        f"/movie/{tmdb_id}",
        {"append_to_response": "credits", "language": "en-US"},
        api_key,
    )


def extract_metadata(details):
    """Extract clean genres, overview, runtime, and top cast from a TMDB details+credits response."""
    if not details:
        return {"genres": [], "overview": "", "runtime": None, "cast": []}

    genres = [g["name"] for g in details.get("genres", [])]

    overview = details.get("overview", "") or ""

    runtime = details.get("runtime") or None  # minutes as int, or None if unknown

    cast_raw = details.get("credits", {}).get("cast", [])
    cast = [c["name"] for c in cast_raw[:CAST_LIMIT] if c.get("name")]

    return {"genres": genres, "overview": overview, "runtime": runtime, "cast": cast}


# ─── Main fetch/clean pipeline ───────────────────────────────────────────────

def fetch_raw(api_key, movies):
    """
    Fetch raw TMDB data for all movies. Skips already-cached entries.
    Returns results dict.
    """
    existing_data = {}
    if os.path.exists(RAW_FILE):
        try:
            with open(RAW_FILE) as f:
                existing_data = json.load(f)
            print(f"Loaded {len(existing_data)} existing entries from {RAW_FILE}")
        except (json.JSONDecodeError, IOError):
            pass

    results = dict(existing_data)
    total = len(movies)
    fetched = 0
    skipped = 0

    print(f"\nFetching TMDB metadata for {total} movies...")
    print(f"Fields: genres, overview, runtime, top {CAST_LIMIT} cast members")
    print("=" * 60)

    for i, movie in enumerate(movies):
        rank_key = str(movie["rank"])

        if rank_key in existing_data and rank_key != "_updated":
            skipped += 1
            meta = existing_data[rank_key].get("metadata", {})
            genres = meta.get("genres", [])
            print(f"[{i+1:3d}/{total}] (cached)  #{movie['rank']:3d} {movie['title']} -> {genres or 'no genres'}")
            continue

        print(f"[{i+1:3d}/{total}] Fetching #{movie['rank']:3d} {movie['title']} ({movie['year']})...", end=" ", flush=True)

        search_result = search_tmdb(movie["title"], movie["year"], api_key)
        if not search_result:
            print("-> not found on TMDB")
            results[rank_key] = {
                "title": movie["title"],
                "year": movie["year"],
                "metadata": {"genres": [], "overview": "", "cast": []},
                "fetched_at": datetime.date.today().isoformat(),
                "raw": None,
            }
        else:
            tmdb_id = search_result["id"]
            details = fetch_movie_details(tmdb_id, api_key)
            metadata = extract_metadata(details)

            results[rank_key] = {
                "title": movie["title"],
                "year": movie["year"],
                "metadata": metadata,
                "fetched_at": datetime.date.today().isoformat(),
                "raw": {
                    "tmdb_id": tmdb_id,
                    "tmdb_title": search_result.get("title"),
                    "tmdb_year": (search_result.get("release_date") or "")[:4],
                    "details": details,
                },
            }
            print(f"-> {metadata['genres'] or 'no genres'}")

        fetched += 1

        # Save after each movie so progress isn't lost on interruption
        with open(RAW_FILE, "w") as f:
            json.dump(results, f, indent=2)

        if i < total - 1:
            time.sleep(DELAY_BETWEEN_REQUESTS)

    updated_date = datetime.date.today().strftime("%B %d, %Y")
    results["_updated"] = updated_date

    with open(RAW_FILE, "w") as f:
        json.dump(results, f, indent=2)

    print("=" * 60)
    print(f"Done! Fetched: {fetched}, Cached: {skipped}, Total: {total}")
    print(f"Raw data saved to {RAW_FILE}")
    return results


def clean_raw(results=None, movies=None):
    """
    Produce the clean movie_metadata.json from raw results.
    Only genres, overview, cast, and fetched_at are written — no raw API data.
    """
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

    clean = {}
    for key, value in results.items():
        if key == "_updated":
            clean["_updated"] = value
        elif isinstance(value, dict):
            meta = value.get("metadata", {})
            entry = {
                "genres":   meta.get("genres", []),
                "overview": meta.get("overview", ""),
                "runtime":  meta.get("runtime", None),
                "cast":     meta.get("cast", []),
            }
            if "fetched_at" in value:
                entry["fetched_at"] = value["fetched_at"]
            clean[key] = entry

    with open(OUTPUT_FILE, "w") as f:
        json.dump(clean, f, indent=2)

    print(f"Clean metadata saved to {OUTPUT_FILE}")

    if movies:
        total = len(movies)
        with_meta = sum(
            1 for k, v in clean.items()
            if k not in ("_updated",) and isinstance(v, dict) and v.get("genres")
        )
        print(f"\nMovies with metadata: {with_meta}/{total}")

        # Genre breakdown
        genre_counts = {}
        for v in clean.values():
            if not isinstance(v, dict):
                continue
            for g in v.get("genres", []):
                genre_counts[g] = genre_counts.get(g, 0) + 1
        if genre_counts:
            print("Top genres:")
            for genre, count in sorted(genre_counts.items(), key=lambda x: -x[1])[:10]:
                print(f"  {genre:20s}: {count} movies")


def main():
    parser = argparse.ArgumentParser(description="Fetch and/or clean TMDB movie metadata")
    parser.add_argument("--fetch-only", action="store_true",
                        help="Only fetch raw TMDB data, save to movie_metadata_raw.json")
    parser.add_argument("--clean-only", action="store_true",
                        help="Only clean existing raw data into movie_metadata.json")
    args = parser.parse_args()

    if args.fetch_only and args.clean_only:
        print("Cannot use --fetch-only and --clean-only together.")
        sys.exit(1)

    movies = load_movies()

    if args.clean_only:
        clean_raw(movies=movies)
        return

    api_key = load_api_key()
    results = fetch_raw(api_key, movies)

    if args.fetch_only:
        return

    clean_raw(results, movies)


if __name__ == "__main__":
    main()
