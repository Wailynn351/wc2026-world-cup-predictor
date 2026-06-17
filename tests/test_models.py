"""Unit tests for models.py"""

import unittest

from wc2026.models import Team, Match, Prediction


class TestTeam(unittest.TestCase):
    def test_valid_team(self):
        t = Team("ARG", "Argentina", "CONMEBOL", "C", 2138)
        self.assertEqual(t.fifa_code, "ARG")
        self.assertEqual(t.name, "Argentina")
        self.assertEqual(t.confederation, "CONMEBOL")
        self.assertEqual(t.group, "C")
        self.assertEqual(t.elo_rating, 2138)

    def test_default_elo(self):
        t = Team("USA", "United States", "CONCACAF", "B")
        self.assertEqual(t.elo_rating, 1500)

    def test_invalid_fifa_code(self):
        with self.assertRaises(ValueError):
            Team("AB", "Bad Code", "UEFA", "X")

    def test_invalid_fifa_code_long(self):
        with self.assertRaises(ValueError):
            Team("ABCD", "Too Long", "UEFA", "X")

    def test_negative_elo(self):
        with self.assertRaises(ValueError):
            Team("XXX", "Negative", "UEFA", "X", -100)


class TestMatch(unittest.TestCase):
    def test_played_match(self):
        m = Match("Argentina", "France", 3, 3, 2022, "final")
        self.assertTrue(m.is_played)
        self.assertEqual(m.home_score, 3)
        self.assertEqual(m.away_score, 3)
        self.assertEqual(m.tournament_year, 2022)
        self.assertEqual(m.stage, "final")

    def test_unplayed_match(self):
        m = Match("Brazil", "Germany")
        self.assertFalse(m.is_played)
        self.assertIsNone(m.home_score)
        self.assertIsNone(m.away_score)

    def test_winner_home(self):
        m = Match("A", "B", 2, 1)
        self.assertEqual(m.winner, "A")

    def test_winner_away(self):
        m = Match("A", "B", 0, 3)
        self.assertEqual(m.winner, "B")

    def test_draw(self):
        m = Match("A", "B", 1, 1)
        self.assertIsNone(m.winner)
        self.assertTrue(m.is_draw)

    def test_unplayed_winner(self):
        m = Match("A", "B")
        self.assertIsNone(m.winner)
        self.assertFalse(m.is_draw)

    def test_total_goals(self):
        m = Match("A", "B", 4, 2)
        self.assertEqual(m.total_goals, 6)

    def test_total_goals_unplayed(self):
        m = Match("A", "B")
        self.assertIsNone(m.total_goals)


class TestPrediction(unittest.TestCase):
    def test_str_contains_teams(self):
        p = Prediction("Argentina", "France", 2138, 2115, 0.52, 0.24, 0.24, "Argentina", "low")
        s = str(p)
        self.assertIn("Argentina", s)
        self.assertIn("France", s)
        self.assertIn("52.0%", s)
        self.assertIn("24.0%", s)

    def test_str_draw_prediction(self):
        p = Prediction("A", "B", 1500, 1500, 0.38, 0.30, 0.32, None, "low")
        s = str(p)
        self.assertIn("Draw", s)

    def test_high_confidence(self):
        p = Prediction("A", "B", 2100, 1600, 0.85, 0.05, 0.10, "A", "high")
        self.assertEqual(p.confidence, "high")
        self.assertEqual(p.predicted_winner, "A")
