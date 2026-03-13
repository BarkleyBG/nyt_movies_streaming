"""
Unit tests for fetch_streaming.py

Coverage:
  - extract_streaming()     : service extraction from raw API response
  - search_movie()          : HTTP request construction and response parsing (mocked)
  - load_api_key()          : .env / environment variable loading
  - MOVIES data integrity   : list has 100 entries, unique ranks 1-100, valid years

All external I/O (HTTP calls, file access) is mocked so tests are fast,
hermetic, and don't consume API quota.

Run with:
    python -m pytest tests/python/ -v
"""

import json
import os
import sys
import unittest
from unittest.mock import patch, MagicMock, mock_open

# ─── Import the module under test ─────────────────────────────────────────────
# Resolve path to project root regardless of where pytest is invoked from
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _PROJECT_ROOT)

import fetch_streaming  # noqa: E402


# ─── Fixtures ─────────────────────────────────────────────────────────────────

def _make_show(title="Test Movie", year=2020, us_options=None):
    """Build a minimal show dict that mirrors the streaming API response shape."""
    return {
        "title": title,
        "releaseYear": year,
        "streamingOptions": {"us": us_options or []},
    }


def _make_us_option(service_id, stream_type="subscription"):
    """Build a single streaming option entry."""
    return {"service": {"id": service_id}, "type": stream_type}


def _mock_urlopen(response_data):
    """
    Returns a context-manager mock that urlopen returns, yielding a bytes body.
    Supports both `with urlopen(...) as r:` usage patterns.
    """
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(response_data).encode()
    mock_resp.__enter__ = MagicMock(return_value=mock_resp)
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


# ─── extract_streaming() ──────────────────────────────────────────────────────

class TestExtractStreaming(unittest.TestCase):
    """
    Tests for extract_streaming() — the function that pulls US service IDs
    out of a raw streaming API show object.
    """

    def test_none_input_returns_empty_list(self):
        """Returns [] when the show was not found (None passed in)."""
        self.assertEqual(fetch_streaming.extract_streaming(None), [])

    def test_empty_dict_returns_empty_list(self):
        """Returns [] when the show dict has no streamingOptions key."""
        self.assertEqual(fetch_streaming.extract_streaming({}), [])

    def test_single_us_subscription_service(self):
        """Extracts a single US subscription service correctly."""
        show = _make_show(us_options=[_make_us_option("netflix")])
        self.assertEqual(fetch_streaming.extract_streaming(show), ["netflix"])

    def test_multiple_us_subscription_services(self):
        """Extracts multiple US services in the order they appear."""
        show = _make_show(us_options=[
            _make_us_option("netflix"),
            _make_us_option("prime"),
        ])
        result = fetch_streaming.extract_streaming(show)
        self.assertIn("netflix", result)
        self.assertIn("prime", result)
        self.assertEqual(len(result), 2)

    def test_ignores_non_us_regions(self):
        """Only US streaming options are considered; other regions are ignored."""
        show = {
            "streamingOptions": {
                "gb": [_make_us_option("netflix")],
                "us": [_make_us_option("hbo")],
            }
        }
        self.assertEqual(fetch_streaming.extract_streaming(show), ["hbo"])

    def test_ignores_rental_type(self):
        """'rent' type does not count as streaming availability."""
        show = _make_show(us_options=[
            _make_us_option("netflix", "subscription"),
            _make_us_option("prime",   "rent"),
        ])
        self.assertEqual(fetch_streaming.extract_streaming(show), ["netflix"])

    def test_ignores_buy_type(self):
        """'buy' type does not count as streaming availability."""
        show = _make_show(us_options=[
            _make_us_option("apple", "buy"),
        ])
        self.assertEqual(fetch_streaming.extract_streaming(show), [])

    def test_includes_free_type(self):
        """'free' type is a valid streaming type (e.g. Peacock free tier)."""
        show = _make_show(us_options=[_make_us_option("peacock", "free")])
        self.assertIn("peacock", fetch_streaming.extract_streaming(show))

    def test_ignores_unknown_service_ids(self):
        """Service IDs not in US_SERVICES (e.g. 'mubi') are ignored."""
        show = _make_show(us_options=[
            _make_us_option("mubi"),          # unknown
            _make_us_option("netflix"),       # known
        ])
        self.assertEqual(fetch_streaming.extract_streaming(show), ["netflix"])

    def test_deduplicates_same_service_appearing_twice(self):
        """A service should not appear twice even if it has multiple entries."""
        show = _make_show(us_options=[
            _make_us_option("hbo", "subscription"),
            _make_us_option("hbo", "free"),           # duplicate
        ])
        result = fetch_streaming.extract_streaming(show)
        self.assertEqual(result.count("hbo"), 1)

    def test_empty_us_options_returns_empty(self):
        """Returns [] when the US list is present but empty."""
        show = _make_show(us_options=[])
        self.assertEqual(fetch_streaming.extract_streaming(show), [])

    def test_all_seven_supported_services(self):
        """All seven services in US_SERVICES can be extracted."""
        services = ["netflix", "disney", "hulu", "prime", "peacock", "hbo", "apple"]
        show = _make_show(us_options=[_make_us_option(s) for s in services])
        result = fetch_streaming.extract_streaming(show)
        self.assertEqual(set(result), set(services))


# ─── load_api_key() ───────────────────────────────────────────────────────────

class TestLoadApiKey(unittest.TestCase):
    """
    Tests for load_api_key() — reads RAPIDAPI_KEY from a .env file or
    the environment, and calls sys.exit(1) when it's missing or is a placeholder.
    """

    def test_returns_key_from_environment(self):
        """Returns the key when RAPIDAPI_KEY is set as an env var."""
        with patch.dict(os.environ, {"RAPIDAPI_KEY": "real_key_abc"}):
            with patch("fetch_streaming.os.path.exists", return_value=False):
                self.assertEqual(fetch_streaming.load_api_key(), "real_key_abc")

    def test_exits_when_key_missing(self):
        """sys.exit(1) is called when RAPIDAPI_KEY is not in the environment."""
        env = {k: v for k, v in os.environ.items() if k != "RAPIDAPI_KEY"}
        with patch.dict(os.environ, env, clear=True):
            with patch("fetch_streaming.os.path.exists", return_value=False):
                with self.assertRaises(SystemExit) as cm:
                    fetch_streaming.load_api_key()
                self.assertEqual(cm.exception.code, 1)

    def test_exits_when_key_is_placeholder(self):
        """sys.exit(1) is called when the key is still the example placeholder."""
        with patch.dict(os.environ, {"RAPIDAPI_KEY": "your_rapidapi_key_here"}):
            with patch("fetch_streaming.os.path.exists", return_value=False):
                with self.assertRaises(SystemExit) as cm:
                    fetch_streaming.load_api_key()
                self.assertEqual(cm.exception.code, 1)

    def test_reads_key_from_env_file(self):
        """Parses RAPIDAPI_KEY from a .env file when env var is not set."""
        env_content = "# comment\nRAPIDAPI_KEY=from_env_file_123\n"
        # Remove the key from environment so the .env file path is exercised
        env = {k: v for k, v in os.environ.items() if k != "RAPIDAPI_KEY"}
        with patch.dict(os.environ, env, clear=True):
            with patch("fetch_streaming.os.path.exists", return_value=True):
                with patch("builtins.open", mock_open(read_data=env_content)):
                    self.assertEqual(fetch_streaming.load_api_key(), "from_env_file_123")

    def test_env_file_ignores_comment_lines(self):
        """Lines starting with # in .env are ignored."""
        env_content = "# RAPIDAPI_KEY=commented_out\nRAPIDAPI_KEY=real_key\n"
        env = {k: v for k, v in os.environ.items() if k != "RAPIDAPI_KEY"}
        with patch.dict(os.environ, env, clear=True):
            with patch("fetch_streaming.os.path.exists", return_value=True):
                with patch("builtins.open", mock_open(read_data=env_content)):
                    self.assertEqual(fetch_streaming.load_api_key(), "real_key")


# ─── search_movie() ───────────────────────────────────────────────────────────

class TestSearchMovie(unittest.TestCase):
    """
    Tests for search_movie() — makes an HTTP request to the streaming API
    and returns the best-matched show dict (or None on failure).

    All network calls are mocked with unittest.mock.patch.
    """

    def test_returns_year_matched_result(self):
        """Prefers the result whose releaseYear matches the requested year."""
        api_data = [
            {"title": "Parasite", "releaseYear": 2019, "streamingOptions": {}},
            {"title": "Parasite", "releaseYear": 1999, "streamingOptions": {}},
        ]
        with patch("urllib.request.urlopen", return_value=_mock_urlopen(api_data)):
            result = fetch_streaming.search_movie("Parasite", 2019, "key")
        self.assertIsNotNone(result)
        self.assertEqual(result["releaseYear"], 2019)

    def test_returns_none_on_http_404(self):
        """Returns None when the API returns a 404."""
        import urllib.error
        err = urllib.error.HTTPError(None, 404, "Not Found", {}, None)
        with patch("urllib.request.urlopen", side_effect=err):
            self.assertIsNone(fetch_streaming.search_movie("Ghost", 2000, "key"))

    def test_returns_none_on_http_429_rate_limit(self):
        """Returns None when the API signals rate-limiting (429)."""
        import urllib.error
        err = urllib.error.HTTPError(None, 429, "Too Many Requests", {}, None)
        with patch("urllib.request.urlopen", side_effect=err):
            self.assertIsNone(fetch_streaming.search_movie("Movie", 2010, "key"))

    def test_returns_none_on_network_error(self):
        """Returns None for any generic network/connection exception."""
        with patch("urllib.request.urlopen", side_effect=Exception("Connection refused")):
            self.assertIsNone(fetch_streaming.search_movie("Movie", 2010, "key"))

    def test_falls_back_to_first_result_when_no_year_match(self):
        """Returns the first result when no entry matches the given year."""
        api_data = [{"title": "Old Film", "releaseYear": 1980, "streamingOptions": {}}]
        with patch("urllib.request.urlopen", return_value=_mock_urlopen(api_data)):
            result = fetch_streaming.search_movie("Old Film", 2020, "key")
        self.assertIsNotNone(result)
        self.assertEqual(result["releaseYear"], 1980)

    def test_returns_none_for_empty_results_list(self):
        """Returns None when the API returns an empty list."""
        with patch("urllib.request.urlopen", return_value=_mock_urlopen([])):
            self.assertIsNone(fetch_streaming.search_movie("Unknown", 2000, "key"))

    def test_handles_dict_response_with_result_key(self):
        """Parses responses wrapped in a 'result' key (alternate API shape)."""
        api_data = {"result": [{"title": "Moonlight", "releaseYear": 2016, "streamingOptions": {}}]}
        with patch("urllib.request.urlopen", return_value=_mock_urlopen(api_data)):
            result = fetch_streaming.search_movie("Moonlight", 2016, "key")
        self.assertIsNotNone(result)
        self.assertEqual(result["title"], "Moonlight")

    def test_handles_dict_response_with_results_key(self):
        """Parses responses wrapped in a 'results' key (another alternate shape)."""
        api_data = {"results": [{"title": "Her", "releaseYear": 2013, "streamingOptions": {}}]}
        with patch("urllib.request.urlopen", return_value=_mock_urlopen(api_data)):
            result = fetch_streaming.search_movie("Her", 2013, "key")
        self.assertIsNotNone(result)
        self.assertEqual(result["title"], "Her")


# ─── MOVIES data integrity ────────────────────────────────────────────────────

class TestMovieDataIntegrity(unittest.TestCase):
    """
    Data integrity checks for the MOVIES list in fetch_streaming.py.

    These tests ensure the Python list stays in sync with the list in index.html
    and that no entries are missing, duplicated, or malformed.
    """

    def test_exactly_100_movies(self):
        """The MOVIES list must have exactly 100 entries."""
        self.assertEqual(len(fetch_streaming.MOVIES), 100)

    def test_all_ranks_unique(self):
        """Every rank value must be unique — no duplicates allowed."""
        ranks = [m["rank"] for m in fetch_streaming.MOVIES]
        self.assertEqual(len(ranks), len(set(ranks)), "Duplicate ranks found")

    def test_ranks_cover_1_to_100_with_no_gaps(self):
        """Ranks must be exactly 1 through 100 with no gaps."""
        ranks = sorted(m["rank"] for m in fetch_streaming.MOVIES)
        self.assertEqual(ranks, list(range(1, 101)))

    def test_all_movies_have_required_keys(self):
        """Each entry must have 'rank', 'title', and 'year'."""
        for movie in fetch_streaming.MOVIES:
            with self.subTest(rank=movie.get("rank")):
                self.assertIn("rank",  movie)
                self.assertIn("title", movie)
                self.assertIn("year",  movie)

    def test_all_titles_are_non_empty_strings(self):
        """Titles must be non-empty strings."""
        for movie in fetch_streaming.MOVIES:
            with self.subTest(rank=movie["rank"]):
                self.assertIsInstance(movie["title"], str)
                self.assertGreater(len(movie["title"].strip()), 0)

    def test_all_years_are_21st_century(self):
        """All movies must have a release year of 2000 or later."""
        for movie in fetch_streaming.MOVIES:
            with self.subTest(title=movie["title"]):
                self.assertGreaterEqual(
                    movie["year"], 2000,
                    f"'{movie['title']}' year {movie['year']} is before 2000"
                )

    def test_rank_1_is_parasite_2019(self):
        """Rank 1 is Parasite (2019) — matches index.html."""
        rank1 = next(m for m in fetch_streaming.MOVIES if m["rank"] == 1)
        self.assertEqual(rank1["title"], "Parasite")
        self.assertEqual(rank1["year"],  2019)

    def test_rank_100_is_superbad_2007(self):
        """Rank 100 is Superbad (2007) — matches index.html."""
        rank100 = next(m for m in fetch_streaming.MOVIES if m["rank"] == 100)
        self.assertEqual(rank100["title"], "Superbad")
        self.assertEqual(rank100["year"],  2007)

    def test_all_ranks_are_integers(self):
        """Rank values must be integers, not strings."""
        for movie in fetch_streaming.MOVIES:
            with self.subTest(title=movie["title"]):
                self.assertIsInstance(movie["rank"], int)

    def test_all_years_are_integers(self):
        """Year values must be integers."""
        for movie in fetch_streaming.MOVIES:
            with self.subTest(title=movie["title"]):
                self.assertIsInstance(movie["year"], int)


if __name__ == "__main__":
    unittest.main(verbosity=2)
