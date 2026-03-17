"""
Unit tests for fetch_metadata.py

Coverage:
  - extract_metadata()  : genres, overview, runtime, and cast extraction
  - search_tmdb()       : HTTP request construction and response parsing (mocked)
  - load_api_key()      : TMDB_API_KEY loading from env / .env file
  - load_movies()       : reads movies.json correctly
  - movies.json integrity: 100 entries, unique ranks 1-100, required fields

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
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _PROJECT_ROOT)

import fetch_metadata  # noqa: E402


# ─── Fixtures ─────────────────────────────────────────────────────────────────

def _make_details(genres=None, overview="A test movie.", runtime=120, cast_names=None,
                  original_language="en", vote_average=7.5, vote_count=1000,
                  tagline="A tagline."):
    """Build a minimal TMDB details+credits response."""
    if genres is None:
        genres = [{"id": 28, "name": "Action"}, {"id": 18, "name": "Drama"}]
    if cast_names is None:
        cast_names = ["Alice Actor", "Bob Star", "Carol Lead"]
    return {
        "genres": genres,
        "overview": overview,
        "runtime": runtime,
        "original_language": original_language,
        "vote_average": vote_average,
        "vote_count": vote_count,
        "tagline": tagline,
        "credits": {
            "cast": [{"name": n, "order": i} for i, n in enumerate(cast_names)]
        },
    }


def _mock_urlopen(response_data):
    """Returns a context-manager mock that urlopen returns, yielding a bytes body."""
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(response_data).encode()
    mock_resp.__enter__ = MagicMock(return_value=mock_resp)
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


# ─── extract_metadata() ───────────────────────────────────────────────────────

class TestExtractMetadata(unittest.TestCase):
    """Tests for extract_metadata() — pulls genres, overview, runtime, language, rating, tagline, cast."""

    def test_none_returns_empty_defaults(self):
        """Returns safe empty defaults when details is None."""
        result = fetch_metadata.extract_metadata(None)
        self.assertEqual(result["genres"], [])
        self.assertEqual(result["overview"], "")
        self.assertIsNone(result["runtime"])
        self.assertIsNone(result["original_language"])
        self.assertIsNone(result["vote_average"])
        self.assertIsNone(result["vote_count"])
        self.assertEqual(result["tagline"], "")
        self.assertEqual(result["cast"], [])

    def test_extracts_genre_names(self):
        """Extracts genre name strings from the genres list."""
        details = _make_details(genres=[{"id": 1, "name": "Drama"}, {"id": 2, "name": "Comedy"}])
        result = fetch_metadata.extract_metadata(details)
        self.assertEqual(result["genres"], ["Drama", "Comedy"])

    def test_extracts_overview(self):
        """Extracts overview text correctly."""
        details = _make_details(overview="A fascinating story about nothing.")
        self.assertEqual(fetch_metadata.extract_metadata(details)["overview"],
                         "A fascinating story about nothing.")

    def test_extracts_runtime(self):
        """Extracts runtime as integer minutes."""
        details = _make_details(runtime=132)
        self.assertEqual(fetch_metadata.extract_metadata(details)["runtime"], 132)

    def test_runtime_none_when_missing(self):
        """Returns None when runtime key is absent."""
        details = _make_details()
        del details["runtime"]
        self.assertIsNone(fetch_metadata.extract_metadata(details)["runtime"])

    def test_runtime_none_when_zero(self):
        """Returns None when runtime is 0 (TMDB uses 0 for unknown)."""
        details = _make_details(runtime=0)
        self.assertIsNone(fetch_metadata.extract_metadata(details)["runtime"])

    def test_extracts_top_cast_up_to_limit(self):
        """Returns at most CAST_LIMIT cast members."""
        many = [f"Actor {i}" for i in range(10)]
        details = _make_details(cast_names=many)
        result = fetch_metadata.extract_metadata(details)
        self.assertEqual(len(result["cast"]), fetch_metadata.CAST_LIMIT)
        self.assertEqual(result["cast"], many[:fetch_metadata.CAST_LIMIT])

    def test_cast_fewer_than_limit(self):
        """Returns all cast when there are fewer than CAST_LIMIT."""
        details = _make_details(cast_names=["Solo Star"])
        self.assertEqual(fetch_metadata.extract_metadata(details)["cast"], ["Solo Star"])

    def test_cast_empty_when_no_credits(self):
        """Returns [] when credits key is absent."""
        details = _make_details()
        del details["credits"]
        self.assertEqual(fetch_metadata.extract_metadata(details)["cast"], [])

    def test_empty_genres_list(self):
        """Returns [] genres when list is empty."""
        details = _make_details(genres=[])
        self.assertEqual(fetch_metadata.extract_metadata(details)["genres"], [])

    def test_empty_overview_string(self):
        """Returns empty string when overview is absent."""
        details = _make_details()
        del details["overview"]
        self.assertEqual(fetch_metadata.extract_metadata(details)["overview"], "")

    # ── original_language ──

    def test_extracts_original_language(self):
        """Extracts ISO 639-1 language code."""
        details = _make_details(original_language="ko")
        self.assertEqual(fetch_metadata.extract_metadata(details)["original_language"], "ko")

    def test_original_language_none_when_missing(self):
        """Returns None when original_language key is absent."""
        details = _make_details()
        del details["original_language"]
        self.assertIsNone(fetch_metadata.extract_metadata(details)["original_language"])

    def test_original_language_none_when_empty_string(self):
        """Returns None when original_language is an empty string."""
        details = _make_details(original_language="")
        self.assertIsNone(fetch_metadata.extract_metadata(details)["original_language"])

    # ── vote_average / vote_count ──

    def test_extracts_vote_average(self):
        """Extracts vote_average rounded to 1 decimal place."""
        details = _make_details(vote_average=8.3456)
        self.assertAlmostEqual(fetch_metadata.extract_metadata(details)["vote_average"], 8.3, places=1)

    def test_vote_average_none_when_zero(self):
        """Returns None when vote_average is 0.0 (no ratings yet)."""
        details = _make_details(vote_average=0.0)
        self.assertIsNone(fetch_metadata.extract_metadata(details)["vote_average"])

    def test_vote_average_none_when_missing(self):
        """Returns None when vote_average key is absent."""
        details = _make_details()
        del details["vote_average"]
        self.assertIsNone(fetch_metadata.extract_metadata(details)["vote_average"])

    def test_extracts_vote_count(self):
        """Extracts vote_count as an integer."""
        details = _make_details(vote_count=5000)
        self.assertEqual(fetch_metadata.extract_metadata(details)["vote_count"], 5000)

    def test_vote_count_zero_when_missing(self):
        """Returns 0 when vote_count key is absent."""
        details = _make_details()
        del details["vote_count"]
        self.assertEqual(fetch_metadata.extract_metadata(details)["vote_count"], 0)

    # ── tagline ──

    def test_extracts_tagline(self):
        """Extracts tagline string."""
        details = _make_details(tagline="Be afraid. Be very afraid.")
        self.assertEqual(fetch_metadata.extract_metadata(details)["tagline"],
                         "Be afraid. Be very afraid.")

    def test_tagline_empty_when_missing(self):
        """Returns empty string when tagline key is absent."""
        details = _make_details()
        del details["tagline"]
        self.assertEqual(fetch_metadata.extract_metadata(details)["tagline"], "")

    def test_tagline_empty_when_none(self):
        """Returns empty string when tagline is None (TMDB uses None for missing taglines)."""
        details = _make_details(tagline=None)
        self.assertEqual(fetch_metadata.extract_metadata(details)["tagline"], "")


# ─── search_tmdb() ────────────────────────────────────────────────────────────

class TestSearchTmdb(unittest.TestCase):
    """Tests for search_tmdb() — searches TMDB and returns best match."""

    def _make_search_result(self, title, year):
        return {"id": 123, "title": title, "release_date": f"{year}-01-15"}

    def test_returns_exact_year_match(self):
        """Prefers result whose release year matches exactly."""
        data = {
            "results": [
                self._make_search_result("Parasite", 2010),
                self._make_search_result("Parasite", 2019),
            ]
        }
        with patch("urllib.request.urlopen", return_value=_mock_urlopen(data)):
            result = fetch_metadata.search_tmdb("Parasite", 2019, "key")
        self.assertIsNotNone(result)
        self.assertEqual(result["release_date"][:4], "2019")

    def test_falls_back_to_year_plus_one(self):
        """Accepts a result with year off by 1 when no exact match."""
        data = {"results": [self._make_search_result("Film", 2020)]}
        with patch("urllib.request.urlopen", return_value=_mock_urlopen(data)):
            result = fetch_metadata.search_tmdb("Film", 2019, "key")
        self.assertIsNotNone(result)

    def test_falls_back_to_first_result(self):
        """Returns first result when no year match is found."""
        data = {"results": [self._make_search_result("Old Film", 1990)]}
        with patch("urllib.request.urlopen", return_value=_mock_urlopen(data)):
            result = fetch_metadata.search_tmdb("Old Film", 2020, "key")
        self.assertIsNotNone(result)

    def test_returns_none_for_empty_results(self):
        """Returns None when TMDB returns no results on both attempts."""
        data = {"results": []}
        with patch("urllib.request.urlopen", return_value=_mock_urlopen(data)):
            result = fetch_metadata.search_tmdb("Unknown", 2000, "key")
        self.assertIsNone(result)

    def test_returns_none_on_http_error(self):
        """Returns None when the API returns an HTTP error."""
        import urllib.error
        err = urllib.error.HTTPError(None, 404, "Not Found", {}, None)
        with patch("urllib.request.urlopen", side_effect=err):
            self.assertIsNone(fetch_metadata.search_tmdb("Ghost", 2000, "key"))

    def test_returns_none_on_network_error(self):
        """Returns None for any generic network exception."""
        with patch("urllib.request.urlopen", side_effect=Exception("timeout")):
            self.assertIsNone(fetch_metadata.search_tmdb("Movie", 2010, "key"))


# ─── load_api_key() ───────────────────────────────────────────────────────────

class TestLoadApiKey(unittest.TestCase):
    """Tests for load_api_key() — reads TMDB_API_KEY from env or .env file."""

    def test_returns_key_from_environment(self):
        """Returns the key when TMDB_API_KEY is set as an env var."""
        with patch.dict(os.environ, {"TMDB_API_KEY": "real_tmdb_key"}):
            with patch("fetch_metadata.os.path.exists", return_value=False):
                self.assertEqual(fetch_metadata.load_api_key(), "real_tmdb_key")

    def test_exits_when_key_missing(self):
        """sys.exit(1) is called when TMDB_API_KEY is not set."""
        env = {k: v for k, v in os.environ.items() if k != "TMDB_API_KEY"}
        with patch.dict(os.environ, env, clear=True):
            with patch("fetch_metadata.os.path.exists", return_value=False):
                with self.assertRaises(SystemExit) as cm:
                    fetch_metadata.load_api_key()
                self.assertEqual(cm.exception.code, 1)

    def test_exits_when_key_is_placeholder(self):
        """sys.exit(1) when the key is still the example placeholder."""
        with patch.dict(os.environ, {"TMDB_API_KEY": "your_tmdb_api_key_here"}):
            with patch("fetch_metadata.os.path.exists", return_value=False):
                with self.assertRaises(SystemExit) as cm:
                    fetch_metadata.load_api_key()
                self.assertEqual(cm.exception.code, 1)

    def test_reads_key_from_env_file(self):
        """Parses TMDB_API_KEY from a .env file when env var is not set."""
        env_content = "# comment\nTMDB_API_KEY=from_file_abc\n"
        env = {k: v for k, v in os.environ.items() if k != "TMDB_API_KEY"}
        with patch.dict(os.environ, env, clear=True):
            with patch("fetch_metadata.os.path.exists", return_value=True):
                with patch("builtins.open", mock_open(read_data=env_content)):
                    self.assertEqual(fetch_metadata.load_api_key(), "from_file_abc")


# ─── load_movies() ────────────────────────────────────────────────────────────

class TestLoadMovies(unittest.TestCase):
    """Tests for load_movies() — reads the shared movies.json."""

    def test_returns_list(self):
        """load_movies() returns a list."""
        movies = fetch_metadata.load_movies()
        self.assertIsInstance(movies, list)

    def test_exits_on_missing_file(self):
        """sys.exit(1) when movies.json does not exist."""
        with patch("fetch_metadata.os.path.exists", return_value=False):
            with patch("builtins.open", side_effect=FileNotFoundError):
                with self.assertRaises(SystemExit) as cm:
                    fetch_metadata.load_movies()
                self.assertEqual(cm.exception.code, 1)


# ─── movies.json data integrity ───────────────────────────────────────────────

class TestMoviesJsonIntegrity(unittest.TestCase):
    """
    Data integrity checks for movies.json — the shared source of truth.
    These tests catch drift if movies.json is hand-edited incorrectly.
    """

    @classmethod
    def setUpClass(cls):
        movies_path = os.path.join(_PROJECT_ROOT, "movies.json")
        with open(movies_path) as f:
            cls.movies = json.load(f)

    def test_is_a_list(self):
        """movies.json must be a JSON array."""
        self.assertIsInstance(self.movies, list)

    def test_exactly_100_movies(self):
        """Must have exactly 100 entries."""
        self.assertEqual(len(self.movies), 100)

    def test_all_ranks_unique(self):
        """Every rank value must be unique."""
        ranks = [m["rank"] for m in self.movies]
        self.assertEqual(len(ranks), len(set(ranks)))

    def test_ranks_cover_1_to_100(self):
        """Ranks must be exactly 1 through 100 with no gaps."""
        ranks = sorted(m["rank"] for m in self.movies)
        self.assertEqual(ranks, list(range(1, 101)))

    def test_all_movies_have_required_keys(self):
        """Each entry must have rank, title, year, and director."""
        for movie in self.movies:
            with self.subTest(rank=movie.get("rank")):
                for key in ("rank", "title", "year", "director"):
                    self.assertIn(key, movie)

    def test_all_titles_non_empty(self):
        """Titles must be non-empty strings."""
        for movie in self.movies:
            with self.subTest(rank=movie["rank"]):
                self.assertIsInstance(movie["title"], str)
                self.assertGreater(len(movie["title"].strip()), 0)

    def test_all_directors_non_empty(self):
        """Directors must be non-empty strings."""
        for movie in self.movies:
            with self.subTest(rank=movie["rank"]):
                self.assertIsInstance(movie["director"], str)
                self.assertGreater(len(movie["director"].strip()), 0)

    def test_all_years_are_21st_century(self):
        """All release years must be 2000 or later."""
        for movie in self.movies:
            with self.subTest(title=movie["title"]):
                self.assertGreaterEqual(movie["year"], 2000)

    def test_rank_1_is_parasite_2019(self):
        """Rank 1 must be Parasite (2019)."""
        rank1 = next(m for m in self.movies if m["rank"] == 1)
        self.assertEqual(rank1["title"], "Parasite")
        self.assertEqual(rank1["year"], 2019)

    def test_rank_100_is_superbad_2007(self):
        """Rank 100 must be Superbad (2007)."""
        rank100 = next(m for m in self.movies if m["rank"] == 100)
        self.assertEqual(rank100["title"], "Superbad")
        self.assertEqual(rank100["year"], 2007)

    def test_all_ranks_are_integers(self):
        """Rank values must be integers."""
        for movie in self.movies:
            self.assertIsInstance(movie["rank"], int)

    def test_all_years_are_integers(self):
        """Year values must be integers."""
        for movie in self.movies:
            self.assertIsInstance(movie["year"], int)


if __name__ == "__main__":
    unittest.main(verbosity=2)
