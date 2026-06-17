"""Unit tests for predictor.py"""

import unittest

from wc2026.models import Team
from wc2026.predictor import predict, _draw_probability


class TestPredictor(unittest.TestCase):
    def test_equal_teams(self):
        """Two equal teams should produce roughly balanced probabilities."""
        a = Team("AAA", "Team A", "UEFA", "X", 2000)
        b = Team("BBB", "Team B", "UEFA", "X", 2000)
        p = predict(a, b)

        # With home advantage, A should be slight favorite
        self.assertGreater(p.home_win_pct, p.away_win_pct)
        # But gap should be small
        self.assertLess(abs(p.home_win_pct - p.away_win_pct), 0.15)
        # Draw should be significant
        self.assertGreater(p.draw_pct, 0.20)

    def test_big_favorite(self):
        """A much stronger team should be predicted to win convincingly."""
        a = Team("AAA", "Strong", "UEFA", "X", 2200)
        b = Team("BBB", "Weak", "UEFA", "X", 1600)
        p = predict(a, b)

        self.assertGreater(p.home_win_pct, 0.80)
        self.assertLess(p.away_win_pct, 0.10)
        self.assertEqual(p.confidence, "high")
        self.assertEqual(p.predicted_winner, "Strong")

    def test_moderate_gap(self):
        """A moderate rating gap gives medium confidence."""
        a = Team("AAA", "Better", "UEFA", "X", 2100)
        b = Team("BBB", "Worse", "UEFA", "X", 2030)
        p = predict(a, b)

        self.assertEqual(p.confidence, "medium")

    def test_probabilities_sum_to_one(self):
        """Win + draw + win probabilities must sum to 1.0."""
        a = Team("AAA", "A", "UEFA", "X", 2100)
        b = Team("BBB", "B", "UEFA", "X", 1950)
        p = predict(a, b)
        total = p.home_win_pct + p.draw_pct + p.away_win_pct
        self.assertAlmostEqual(total, 1.0, places=3)

    def test_knockout_reduces_draw(self):
        """Knockout matches should have lower draw probability."""
        a = Team("AAA", "A", "UEFA", "X", 2000)
        b = Team("BBB", "B", "UEFA", "X", 2000)
        group_pred = predict(a, b, "group")
        ko_pred = predict(a, b, "final")

        self.assertLess(ko_pred.draw_pct, group_pred.draw_pct)

    def test_all_probabilities_non_negative(self):
        """No negative probabilities."""
        a = Team("AAA", "A", "UEFA", "X", 1000)
        b = Team("BBB", "B", "UEFA", "X", 2500)
        p = predict(a, b)

        self.assertGreaterEqual(p.home_win_pct, 0)
        self.assertGreaterEqual(p.draw_pct, 0)
        self.assertGreaterEqual(p.away_win_pct, 0)

    def test_knockout_final_predicts_winner(self):
        """A knockout match should still have a sensible prediction."""
        a = Team("AAA", "Home", "UEFA", "X", 2100)
        b = Team("BBB", "Away", "UEFA", "X", 1900)
        p = predict(a, b, "final")
        self.assertIsNotNone(p.predicted_winner)
        total = p.home_win_pct + p.draw_pct + p.away_win_pct
        self.assertAlmostEqual(total, 1.0, places=3)


class TestDrawProbability(unittest.TestCase):
    def test_equal_ratings_max_draw(self):
        self.assertAlmostEqual(_draw_probability(0), 0.30, places=2)

    def test_large_gap_min_draw(self):
        self.assertAlmostEqual(_draw_probability(500), 0.05, places=2)

    def test_knockout_reduces_draw(self):
        group_draw = _draw_probability(0, None)
        ko_draw = _draw_probability(0, "final")
        self.assertLess(ko_draw, group_draw)

    def test_symmetry(self):
        """Gap should be symmetric."""
        self.assertEqual(_draw_probability(100), _draw_probability(-100))
