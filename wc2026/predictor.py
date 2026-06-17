"""Elo-based match prediction engine."""

import math
from typing import Optional

from wc2026.models import Team, Prediction

# Elo constants
HOME_ADVANTAGE = 50       # Elo points added for the "home" (first-named) team
ELO_SCALE = 400           # Standard Elo scale factor
MAX_DRAW_PROB = 0.30      # Maximum draw probability at equal ratings
DRAW_DECAY_SIGMA = 200    # How fast draw prob drops with rating gap
MIN_DRAW_PROB = 0.05      # Floor for draw probability
KNOCKOUT_DRAW_FACTOR = 0.65  # Knockout matches draw less (extra time + penalties)


def _elo_win_probability(elo_a: float, elo_b: float, home_advantage: float = 0) -> float:
    """Probability team A beats team B, with optional home advantage.

    Uses the standard Elo formula: P(A) = 1 / (1 + 10^((ratingB - (ratingA + home)) / 400))
    """
    adjusted_a = elo_a + home_advantage
    return 1.0 / (1.0 + 10 ** ((elo_b - adjusted_a) / ELO_SCALE))


def _draw_probability(elo_gap: float, stage: Optional[str] = None) -> float:
    """Estimate the probability of a draw based on the Elo gap.

    Uses a Gaussian decay: draw peaks at equal ratings and drops as the gap widens.
    Knockout-stage matches have reduced draw probability (due to extra time/penalties).
    """
    gap = abs(elo_gap)
    raw_draw = MAX_DRAW_PROB * math.exp(-(gap ** 2) / (2 * DRAW_DECAY_SIGMA ** 2))
    raw_draw = max(MIN_DRAW_PROB, raw_draw)

    # Knockout stages have extra time + penalties, so fewer draws
    knockout_stages = {"round_of_16", "quarterfinal", "semifinal", "final",
                       "second_group", "final_group"}
    if stage and stage in knockout_stages:
        raw_draw *= KNOCKOUT_DRAW_FACTOR

    return raw_draw


def _confidence(elo_gap: float, stage: Optional[str] = None) -> str:
    """Determine confidence level based on Elo gap."""
    gap = abs(elo_gap)
    if gap < 40:
        return "low"
    elif gap < 120:
        return "medium"
    else:
        return "high"


def predict(home_team: Team, away_team: Team, stage: Optional[str] = None) -> Prediction:
    """Predict the outcome of a match between two teams.

    Args:
        home_team: The "home" (first-named) team.
        away_team: The "away" (second-named) team.
        stage: Tournament stage (group, round_of_16, quarterfinal, etc.).
               Affects draw probability.

    Returns:
        A Prediction object with win/draw probabilities.
    """
    elo_a = home_team.elo_rating
    elo_b = away_team.elo_rating
    elo_gap = elo_a - elo_b

    # Calculate draw probability first
    draw_pct = _draw_probability(elo_gap, stage)
    remaining = 1.0 - draw_pct

    # Split remaining probability via Elo (with home advantage)
    home_share = _elo_win_probability(elo_a, elo_b, home_advantage=HOME_ADVANTAGE)
    away_share = 1.0 - home_share

    home_win_pct = home_share * remaining
    away_win_pct = away_share * remaining

    # Determine predicted winner
    if home_win_pct > away_win_pct and home_win_pct > draw_pct:
        predicted_winner = home_team.name
    elif away_win_pct > home_win_pct and away_win_pct > draw_pct:
        predicted_winner = away_team.name
    else:
        predicted_winner = None  # Draw is most likely outcome

    conf = _confidence(elo_gap, stage)

    return Prediction(
        home_team=home_team.name,
        away_team=away_team.name,
        home_elo=elo_a,
        away_elo=elo_b,
        home_win_pct=round(home_win_pct, 4),
        draw_pct=round(draw_pct, 4),
        away_win_pct=round(away_win_pct, 4),
        predicted_winner=predicted_winner,
        confidence=conf,
    )
