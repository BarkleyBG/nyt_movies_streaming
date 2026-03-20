"""
fetch_streaming.py
──────────────────
Queries the Streaming Availability API (Movie of the Night) via RapidAPI
for each of the NYT Top 100 movies (and optionally Oscar Best Picture nominees)
and saves results to streaming_data.json.

Usage:
    1. Copy .env.example to .env and add your RapidAPI key
    2. Run:  python fetch_streaming.py
    3. For Oscar movies too:  python fetch_streaming.py --include-oscars

Free plan: 100 requests/day — the NYT list alone uses all 100.
Use --include-oscars only if you have quota remaining or a paid plan.
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
OSCAR_FILE = "oscar_data.json"         # Oscar Best Picture data
DELAY_BETWEEN_REQUESTS = 0.6  # seconds — be polite to the API


def movie_key(movie):
    """Generate a unique key for a movie: title_year (must match index.html movieKey())."""
    return f"{movie['title']}_{movie['year']}"

# ─── Movie List (must match index.html) ──────────────────────────────────────

MOVIES = [
    {"rank": 1,   "title": "Parasite",                                     "year": 2019},
    {"rank": 2,   "title": "Mulholland Drive",                              "year": 2001},
    {"rank": 3,   "title": "There Will Be Blood",                           "year": 2007},
    {"rank": 4,   "title": "In the Mood for Love",                          "year": 2000},
    {"rank": 5,   "title": "Moonlight",                                     "year": 2016},
    {"rank": 6,   "title": "No Country for Old Men",                        "year": 2007},
    {"rank": 7,   "title": "Eternal Sunshine of the Spotless Mind",         "year": 2004},
    {"rank": 8,   "title": "Get Out",                                       "year": 2017},
    {"rank": 9,   "title": "Spirited Away",                                 "year": 2001},
    {"rank": 10,  "title": "The Social Network",                            "year": 2010},
    {"rank": 11,  "title": "Mad Max: Fury Road",                            "year": 2015},
    {"rank": 12,  "title": "The Zone of Interest",                          "year": 2023},
    {"rank": 13,  "title": "Children of Men",                               "year": 2006},
    {"rank": 14,  "title": "Inglourious Basterds",                          "year": 2009},
    {"rank": 15,  "title": "City of God",                                   "year": 2002},
    {"rank": 16,  "title": "Crouching Tiger, Hidden Dragon",                "year": 2000},
    {"rank": 17,  "title": "Brokeback Mountain",                            "year": 2005},
    {"rank": 18,  "title": "Y Tu Mamá También",                             "year": 2001},
    {"rank": 19,  "title": "Zodiac",                                        "year": 2007},
    {"rank": 20,  "title": "The Wolf of Wall Street",                       "year": 2013},
    {"rank": 21,  "title": "The Royal Tenenbaums",                          "year": 2001},
    {"rank": 22,  "title": "The Grand Budapest Hotel",                      "year": 2014},
    {"rank": 23,  "title": "Boyhood",                                       "year": 2014},
    {"rank": 24,  "title": "Her",                                           "year": 2013},
    {"rank": 25,  "title": "Phantom Thread",                                "year": 2017},
    {"rank": 26,  "title": "Anatomy of a Fall",                             "year": 2023},
    {"rank": 27,  "title": "Adaptation",                                    "year": 2002},
    {"rank": 28,  "title": "The Dark Knight",                               "year": 2008},
    {"rank": 29,  "title": "Arrival",                                       "year": 2016},
    {"rank": 30,  "title": "Lost in Translation",                           "year": 2003},
    {"rank": 31,  "title": "The Departed",                                  "year": 2006},
    {"rank": 32,  "title": "Bridesmaids",                                   "year": 2011},
    {"rank": 33,  "title": "A Separation",                                  "year": 2011},
    {"rank": 34,  "title": "WALL-E",                                        "year": 2008},
    {"rank": 35,  "title": "A Prophet",                                     "year": 2009},
    {"rank": 36,  "title": "A Serious Man",                                 "year": 2009},
    {"rank": 37,  "title": "Call Me by Your Name",                          "year": 2017},
    {"rank": 38,  "title": "Portrait of a Lady on Fire",                    "year": 2019},
    {"rank": 39,  "title": "Lady Bird",                                     "year": 2017},
    {"rank": 40,  "title": "Yi Yi",                                         "year": 2000},
    {"rank": 41,  "title": "Amélie",                                        "year": 2001},
    {"rank": 42,  "title": "The Master",                                    "year": 2012},
    {"rank": 43,  "title": "Oldboy",                                        "year": 2003},
    {"rank": 44,  "title": "Once Upon a Time in Hollywood",                 "year": 2019},
    {"rank": 45,  "title": "Moneyball",                                     "year": 2011},
    {"rank": 46,  "title": "Roma",                                          "year": 2018},
    {"rank": 47,  "title": "Almost Famous",                                 "year": 2000},
    {"rank": 48,  "title": "The Lives of Others",                           "year": 2006},
    {"rank": 49,  "title": "Before Sunset",                                 "year": 2004},
    {"rank": 50,  "title": "Up",                                            "year": 2009},
    {"rank": 51,  "title": "12 Years a Slave",                              "year": 2013},
    {"rank": 52,  "title": "The Favourite",                                 "year": 2018},
    {"rank": 53,  "title": "Borat",                                         "year": 2006},
    {"rank": 54,  "title": "Pan's Labyrinth",                               "year": 2006},
    {"rank": 55,  "title": "Inception",                                     "year": 2010},
    {"rank": 56,  "title": "Punch-Drunk Love",                              "year": 2002},
    {"rank": 57,  "title": "Best in Show",                                  "year": 2000},
    {"rank": 58,  "title": "Uncut Gems",                                    "year": 2019},
    {"rank": 59,  "title": "Toni Erdmann",                                  "year": 2016},
    {"rank": 60,  "title": "Whiplash",                                      "year": 2014},
    {"rank": 61,  "title": "Kill Bill: Vol. 1",                             "year": 2003},
    {"rank": 62,  "title": "Memento",                                       "year": 2000},
    {"rank": 63,  "title": "Little Miss Sunshine",                          "year": 2006},
    {"rank": 64,  "title": "Gone Girl",                                     "year": 2014},
    {"rank": 65,  "title": "Oppenheimer",                                   "year": 2023},
    {"rank": 66,  "title": "Spotlight",                                     "year": 2015},
    {"rank": 67,  "title": "Tár",                                           "year": 2022},
    {"rank": 68,  "title": "The Hurt Locker",                               "year": 2008},
    {"rank": 69,  "title": "Under the Skin",                                "year": 2013},
    {"rank": 70,  "title": "Let the Right One In",                          "year": 2008},
    {"rank": 71,  "title": "Ocean's Eleven",                                "year": 2001},
    {"rank": 72,  "title": "Carol",                                         "year": 2015},
    {"rank": 73,  "title": "Ratatouille",                                   "year": 2007},
    {"rank": 74,  "title": "The Florida Project",                           "year": 2017},
    {"rank": 75,  "title": "Amour",                                         "year": 2012},
    {"rank": 76,  "title": "O Brother, Where Art Thou?",                    "year": 2000},
    {"rank": 77,  "title": "Everything Everywhere All at Once",             "year": 2022},
    {"rank": 78,  "title": "Aftersun",                                      "year": 2022},
    {"rank": 79,  "title": "The Tree of Life",                              "year": 2011},
    {"rank": 80,  "title": "Volver",                                        "year": 2006},
    {"rank": 81,  "title": "Black Swan",                                    "year": 2010},
    {"rank": 82,  "title": "The Act of Killing",                            "year": 2012},
    {"rank": 83,  "title": "Inside Llewyn Davis",                           "year": 2013},
    {"rank": 84,  "title": "Melancholia",                                   "year": 2011},
    {"rank": 85,  "title": "Anchorman: The Legend of Ron Burgundy",         "year": 2004},
    {"rank": 86,  "title": "Past Lives",                                    "year": 2023},
    {"rank": 87,  "title": "The Lord of the Rings: The Fellowship of the Ring", "year": 2001},
    {"rank": 88,  "title": "The Gleaners and I",                            "year": 2000},
    {"rank": 89,  "title": "Interstellar",                                  "year": 2014},
    {"rank": 90,  "title": "Frances Ha",                                    "year": 2012},
    {"rank": 91,  "title": "Fish Tank",                                     "year": 2009},
    {"rank": 92,  "title": "Gladiator",                                     "year": 2000},
    {"rank": 93,  "title": "Michael Clayton",                               "year": 2007},
    {"rank": 94,  "title": "Minority Report",                               "year": 2002},
    {"rank": 95,  "title": "The Worst Person in the World",                 "year": 2021},
    {"rank": 96,  "title": "Black Panther",                                 "year": 2018},
    {"rank": 97,  "title": "Gravity",                                       "year": 2013},
    {"rank": 98,  "title": "Grizzly Man",                                   "year": 2005},
    {"rank": 99,  "title": "Memories of Murder",                            "year": 2003},
    {"rank": 100, "title": "Superbad",                                      "year": 2007},
]


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

def load_oscar_movies():
    """Load Oscar Best Picture nominees from oscar_data.json."""
    oscar_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), OSCAR_FILE)
    if not os.path.exists(oscar_path):
        print(f"Warning: {OSCAR_FILE} not found, skipping Oscar movies")
        return []
    try:
        with open(oscar_path) as f:
            data = json.load(f)
        return data.get("movies", [])
    except (json.JSONDecodeError, IOError):
        print(f"Warning: Failed to read {OSCAR_FILE}")
        return []


def fetch_raw(api_key, include_oscars=False):
    """Fetch raw API data for all movies and save to RAW_FILE.

    Movies are fetched in staleness order: never-fetched first, then oldest
    fetched_at first. This maximises freshness within the daily quota.
    Returns results, fetched, refreshed.
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

    # Build deduplicated movie list
    all_movies = list(MOVIES)
    seen_keys = {movie_key(m) for m in MOVIES}

    if include_oscars:
        oscar_movies = load_oscar_movies()
        for om in oscar_movies:
            mk = movie_key(om)
            if mk not in seen_keys:
                all_movies.append(om)
                seen_keys.add(mk)
        print(f"Including Oscar movies: {len(oscar_movies)} total, {len(all_movies) - len(MOVIES)} new")

    # Sort by staleness: never-fetched first (date ""), then oldest fetched_at
    def staleness(movie):
        mk = movie_key(movie)
        entry = existing_data.get(mk)
        if not entry or not isinstance(entry, dict):
            return ""  # never fetched — sorts first
        return entry.get("fetched_at", "")

    all_movies.sort(key=staleness)

    total = len(all_movies)
    fetched = 0
    refreshed = 0
    today = datetime.date.today().isoformat()

    print(f"\nFetching streaming data for {total} movies (staleness order)...")
    print(f"API: Streaming Availability (Movie of the Night) via RapidAPI")
    print(f"Region: US | Included types: {', '.join(INCLUDED_TYPES)}")
    print("=" * 60)

    for i, movie in enumerate(all_movies):
        mk = movie_key(movie)
        existing_entry = existing_data.get(mk) if mk != "_updated" else None
        is_stale = existing_entry and isinstance(existing_entry, dict)
        old_date = existing_entry.get("fetched_at", "?") if is_stale else None

        if is_stale:
            label = f"(refresh, last {old_date})"
        else:
            label = "(new)"

        print(f"[{i+1:3d}/{total}] {label}  {movie['title']} ({movie['year']})...", end=" ")

        show = search_movie(movie["title"], movie["year"], api_key)
        services = extract_streaming(show)

        # Store result with full raw data for future reference
        results[mk] = {
            "title": movie["title"],
            "year": movie["year"],
            "services": services,
            "fetched_at": today,
            "raw": {
                "id": show.get("id") if show else None,
                "imdbId": show.get("imdbId") if show else None,
                "title": show.get("title") if show else None,
                "releaseYear": show.get("releaseYear") if show else None,
                "streamingOptions": show.get("streamingOptions") if show else None,
            } if show else None,
        }

        if is_stale:
            refreshed += 1
        else:
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
    print(f"Done! New: {fetched}, Refreshed: {refreshed}, Total: {total}")
    print(f"Raw data saved to {RAW_FILE}")
    return results, fetched, refreshed


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
    total = sum(1 for k, v in results.items() if k != "_updated" and isinstance(v, dict))
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
    parser.add_argument("--include-oscars", action="store_true", help="Also fetch streaming data for Oscar Best Picture nominees")
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
        results, fetched, skipped = fetch_raw(api_key, include_oscars=args.include_oscars)

    # If fetch-only requested, stop here
    if args.fetch_only:
        return

    # Default: clean using results from fetch, or load from file if results is None
    clean_raw(results if 'results' in locals() else None)


if __name__ == "__main__":
    main()
