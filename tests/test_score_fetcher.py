"""Unit tests for score_fetcher.py"""

import json
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from wc2026.score_fetcher import (
    LiveMatch,
    LiveScore,
    GroupStanding,
    _parse_matches,
    _parse_standings,
    _read_cache,
    _write_cache,
    _read_cache_stale,
    cache_age,
    CACHE_TTL,
)


# ── Sample API responses ──────────────────────────────────────────────────

SAMPLE_MATCHES_RESPONSE = {
    "matches": [
        {
            "id": 1001,
            "homeTeam": {"name": "Argentina"},
            "awayTeam": {"name": "France"},
            "score": {
                "fullTime": {"home": 2, "away": 1},
                "winner": "HOME_TEAM",
            },
            "status": "FINISHED",
            "stage": "GROUP_STAGE",
            "group": "GROUP_C",
            "utcDate": "2026-06-15T18:00:00Z",
            "minute": None,
        },
        {
            "id": 1002,
            "homeTeam": {"name": "Brazil"},
            "awayTeam": {"name": "Germany"},
            "score": {
                "fullTime": {"home": None, "away": None},
                "winner": None,
            },
            "status": "LIVE",
            "stage": "GROUP_STAGE",
            "group": "GROUP_E",
            "utcDate": "2026-06-17T20:00:00Z",
            "minute": {"regular": 67},
        },
        {
            "id": 1003,
            "homeTeam": {"name": "England"},
            "awayTeam": {"name": "Costa Rica"},
            "score": {
                "fullTime": {"home": None, "away": None},
                "winner": None,
            },
            "status": "SCHEDULED",
            "stage": "GROUP_STAGE",
            "group": "GROUP_F",
            "utcDate": "2026-06-18T14:00:00Z",
            "minute": None,
        },
    ]
}

SAMPLE_STANDINGS_RESPONSE = {
    "standings": [
        {
            "group": "GROUP_C",
            "table": [
                {
                    "team": {"name": "Argentina"},
                    "position": 1,
                    "playedGames": 1,
                    "won": 1,
                    "draw": 0,
                    "lost": 0,
                    "goalsFor": 2,
                    "goalsAgainst": 1,
                    "goalDifference": 1,
                    "points": 3,
                },
                {
                    "team": {"name": "France"},
                    "position": 2,
                    "playedGames": 1,
                    "won": 0,
                    "draw": 0,
                    "lost": 1,
                    "goalsFor": 1,
                    "goalsAgainst": 2,
                    "goalDifference": -1,
                    "points": 0,
                },
            ],
        }
    ]
}


# ── Parsing tests ──────────────────────────────────────────────────────────


class TestMatchParsing(unittest.TestCase):
    def test_parse_finished_match(self):
        matches = _parse_matches(SAMPLE_MATCHES_RESPONSE)
        self.assertEqual(len(matches), 3)

        m = matches[0]
        self.assertEqual(m.match_id, 1001)
        self.assertEqual(m.home_team, "Argentina")
        self.assertEqual(m.away_team, "France")
        self.assertEqual(m.home_score, 2)
        self.assertEqual(m.away_score, 1)
        self.assertEqual(m.status, "FINISHED")
        self.assertEqual(m.group, "C")
        self.assertTrue(m.is_finished)
        self.assertFalse(m.is_live)
        self.assertFalse(m.is_scheduled)
        self.assertEqual(m.winner, "HOME_TEAM")
        self.assertEqual(m.score_display, "2 - 1")
        self.assertEqual(m.minute_display, "FT")

    def test_parse_live_match(self):
        matches = _parse_matches(SAMPLE_MATCHES_RESPONSE)
        m = matches[1]
        self.assertEqual(m.match_id, 1002)
        self.assertTrue(m.is_live)
        self.assertFalse(m.is_finished)
        self.assertEqual(m.home_score, None)
        self.assertEqual(m.away_score, None)
        self.assertEqual(m.score_display, "vs")
        self.assertEqual(m.minute_display, "67'")
        self.assertEqual(m.group, "E")

    def test_parse_scheduled_match(self):
        matches = _parse_matches(SAMPLE_MATCHES_RESPONSE)
        m = matches[2]
        self.assertTrue(m.is_scheduled)
        self.assertEqual(m.score_display, "vs")
        self.assertEqual(m.minute_display, "")
        self.assertEqual(m.group, "F")

    def test_empty_matches(self):
        matches = _parse_matches({"matches": []})
        self.assertEqual(matches, [])

    def test_no_group_prefix(self):
        """Matches with non-GROUP_ group field (e.g. knockout stages) get group=None."""
        data = {"matches": [{
            "id": 1,
            "homeTeam": {"name": "A"}, "awayTeam": {"name": "B"},
            "score": {"fullTime": {"home": None, "away": None}, "winner": None},
            "status": "SCHEDULED", "stage": "ROUND_OF_16",
            "group": "ROUND_OF_16", "utcDate": "", "minute": None,
        }]}
        matches = _parse_matches(data)
        self.assertEqual(matches[0].group, None)

    def test_paused_status(self):
        data = {"matches": [{
            "id": 1,
            "homeTeam": {"name": "A"}, "awayTeam": {"name": "B"},
            "score": {"fullTime": {"home": 1, "away": 1}, "winner": None},
            "status": "PAUSED", "stage": "GROUP_STAGE", "group": "GROUP_A",
            "utcDate": "", "minute": None,
        }]}
        matches = _parse_matches(data)
        self.assertTrue(matches[0].is_live)
        self.assertEqual(matches[0].minute_display, "HT")


class TestStandingParsing(unittest.TestCase):
    def test_parse_standings(self):
        standings = _parse_standings(SAMPLE_STANDINGS_RESPONSE)
        self.assertEqual(len(standings), 2)

        s = standings[0]
        self.assertEqual(s.group, "C")
        self.assertEqual(s.team_name, "Argentina")
        self.assertEqual(s.position, 1)
        self.assertEqual(s.played, 1)
        self.assertEqual(s.won, 1)
        self.assertEqual(s.drawn, 0)
        self.assertEqual(s.lost, 0)
        self.assertEqual(s.goals_for, 2)
        self.assertEqual(s.goals_against, 1)
        self.assertEqual(s.goal_diff, 1)
        self.assertEqual(s.points, 3)

    def test_empty_standings(self):
        standings = _parse_standings({"standings": []})
        self.assertEqual(standings, [])


# ── Cache tests ────────────────────────────────────────────────────────────


class TestCache(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        # Patch CACHE_FILE for all tests
        self.old_cache_path_patcher = patch(
            "wc2026.score_fetcher.CACHE_FILE",
            Path(self.tmpdir) / "live_cache.json"
        )
        self.mock_cache_path = self.old_cache_path_patcher.start()
        # Clear env for cache tests
        self.old_env = os.environ.get("FOOTBALL_DATA_API_KEY")
        os.environ.pop("FOOTBALL_DATA_API_KEY", None)

    def tearDown(self):
        self.old_cache_path_patcher.stop()
        if self.old_env:
            os.environ["FOOTBALL_DATA_API_KEY"] = self.old_env
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_write_and_read_cache(self):
        data = {"test": "value"}
        _write_cache("test_key", data)
        cached = _read_cache("test_key")
        self.assertIsNotNone(cached)
        self.assertEqual(cached["test"], "value")
        self.assertIn("_cached_at", cached)

    def test_cache_freshness(self):
        _write_cache("fresh", {"x": 1})
        # Should be fresh immediately
        cached = _read_cache("fresh")
        self.assertIsNotNone(cached)

    def test_stale_cache_past_ttl(self):
        data = {"x": 1, "_cached_at": time.time() - CACHE_TTL - 10}
        path = Path(self.tmpdir) / "live_cache_stale.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(data, f)

        cached = _read_cache("stale")
        self.assertIsNone(cached)

    def test_read_stale_fallback(self):
        data = {"x": 1, "_cached_at": time.time() - CACHE_TTL - 10}
        path = Path(self.tmpdir) / "live_cache_stale2.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(data, f)

        cached = _read_cache_stale("stale2")
        self.assertIsNotNone(cached)
        self.assertEqual(cached["x"], 1)

    def test_cache_age(self):
        _write_cache("age_test", {"x": 1})
        age = cache_age("age_test")
        self.assertIsNotNone(age)
        self.assertGreaterEqual(age, 0)
        self.assertLess(age, 2)

    def test_cache_age_nonexistent(self):
        age = cache_age("nonexistent")
        self.assertIsNone(age)


# ── LiveMatch property tests ───────────────────────────────────────────────


class TestLiveMatchProperties(unittest.TestCase):
    def test_is_live_includes_in_play(self):
        m = LiveMatch(1, "A", "B", None, None, "IN_PLAY", "GROUP_STAGE", "C", "", None)
        self.assertTrue(m.is_live)

    def test_is_live_false_for_finished(self):
        m = LiveMatch(1, "A", "B", 1, 0, "FINISHED", "GROUP_STAGE", "C", "", None, "HOME_TEAM")
        self.assertFalse(m.is_live)
        self.assertTrue(m.is_finished)

    def test_score_display_with_scores(self):
        m = LiveMatch(1, "A", "B", 3, 2, "FINISHED", "GROUP_STAGE", "C", "", None, "HOME_TEAM")
        self.assertEqual(m.score_display, "3 - 2")

    def test_score_display_none_scores(self):
        m = LiveMatch(1, "A", "B", None, None, "SCHEDULED", "GROUP_STAGE", "C", "", None)
        self.assertEqual(m.score_display, "vs")

    def test_minute_display_finished(self):
        m = LiveMatch(1, "A", "B", 1, 0, "FINISHED", "GROUP_STAGE", "C", "", None, "HOME_TEAM")
        self.assertEqual(m.minute_display, "FT")

    def test_minute_display_live(self):
        m = LiveMatch(1, "A", "B", 1, 1, "LIVE", "GROUP_STAGE", "C", "", 45)
        self.assertEqual(m.minute_display, "45'")

    def test_minute_display_scheduled(self):
        m = LiveMatch(1, "A", "B", None, None, "SCHEDULED", "GROUP_STAGE", "C", "")
        self.assertEqual(m.minute_display, "")


# ── API key resolution tests ───────────────────────────────────────────────


class TestApiKey(unittest.TestCase):
    def setUp(self):
        self.old_env = os.environ.get("FOOTBALL_DATA_API_KEY")

    def tearDown(self):
        if self.old_env:
            os.environ["FOOTBALL_DATA_API_KEY"] = self.old_env
        else:
            os.environ.pop("FOOTBALL_DATA_API_KEY", None)

    def test_from_env(self):
        from wc2026.score_fetcher import _get_api_key
        os.environ["FOOTBALL_DATA_API_KEY"] = "test-key-env"
        self.assertEqual(_get_api_key(), "test-key-env")


if __name__ == "__main__":
    unittest.main()
