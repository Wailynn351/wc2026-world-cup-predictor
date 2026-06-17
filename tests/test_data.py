"""Unit tests for data.py"""

import unittest

from wc2026.data import load_teams, load_historical_matches, get_team_by_name, get_team_by_code, get_groups


class TestLoadTeams(unittest.TestCase):
    def test_returns_48_teams(self):
        teams = load_teams()
        self.assertEqual(len(teams), 48)

    def test_teams_have_elo(self):
        teams = load_teams()
        for team in teams:
            self.assertGreater(team.elo_rating, 0)

    def test_teams_have_groups(self):
        teams = load_teams()
        groups = {t.group for t in teams}
        self.assertEqual(groups, set("ABCDEFGHIJKL"))

    def test_teams_have_confederations(self):
        teams = load_teams()
        confeds = {t.confederation for t in teams}
        expected = {"AFC", "CAF", "CONCACAF", "CONMEBOL", "OFC", "UEFA"}
        self.assertEqual(confeds, expected)


class TestLoadHistoricalMatches(unittest.TestCase):
    def test_returns_matches(self):
        matches = load_historical_matches()
        self.assertGreater(len(matches), 0)

    def test_all_have_scores(self):
        matches = load_historical_matches()
        for m in matches:
            self.assertIsNotNone(m.home_score)
            self.assertIsNotNone(m.away_score)

    def test_covers_multiple_years(self):
        matches = load_historical_matches()
        years = {m.tournament_year for m in matches}
        self.assertIn(1930, years)
        self.assertIn(2022, years)
        self.assertGreaterEqual(len(years), 20)


class TestLookup(unittest.TestCase):
    def test_get_team_by_name(self):
        teams = load_teams()
        t = get_team_by_name("argentina", teams)
        self.assertIsNotNone(t)
        self.assertEqual(t.fifa_code, "ARG")

    def test_get_team_by_code(self):
        teams = load_teams()
        t = get_team_by_code("fra", teams)
        self.assertIsNotNone(t)
        self.assertEqual(t.name, "France")

    def test_get_team_not_found(self):
        teams = load_teams()
        self.assertIsNone(get_team_by_name("Minions FC", teams))


class TestGroups(unittest.TestCase):
    def test_12_groups(self):
        teams = load_teams()
        groups = get_groups(teams)
        self.assertEqual(len(groups), 12)

    def test_each_group_has_4_teams(self):
        teams = load_teams()
        groups = get_groups(teams)
        for letter, group_teams in groups.items():
            self.assertEqual(len(group_teams), 4, f"Group {letter} has {len(group_teams)} teams")

    def test_groups_sorted(self):
        teams = load_teams()
        groups = get_groups(teams)
        keys = list(groups.keys())
        self.assertEqual(keys, sorted(keys))
