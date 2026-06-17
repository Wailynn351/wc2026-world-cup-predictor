"""Data models for the 2026 World Cup predictor."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Team:
    """A national team competing in the World Cup."""
    fifa_code: str
    name: str
    confederation: str
    group: str
    elo_rating: float = 1500.0

    def __post_init__(self):
        if not self.fifa_code or len(self.fifa_code) != 3:
            raise ValueError(f"fifa_code must be a 3-letter code, got: {self.fifa_code!r}")
        if self.elo_rating <= 0:
            raise ValueError(f"elo_rating must be positive, got: {self.elo_rating}")


@dataclass
class Match:
    """A historical or upcoming match between two teams."""
    home: str
    away: str
    home_score: Optional[int] = None
    away_score: Optional[int] = None
    tournament_year: Optional[int] = None
    stage: Optional[str] = None

    @property
    def is_played(self) -> bool:
        """Whether this match has a recorded result."""
        return self.home_score is not None and self.away_score is not None

    @property
    def winner(self) -> Optional[str]:
        """Return the winner's name, or None for a draw or unplayed match."""
        if not self.is_played:
            return None
        if self.home_score > self.away_score:
            return self.home
        if self.away_score > self.home_score:
            return self.away
        return None

    @property
    def is_draw(self) -> bool:
        """True if the match ended in a draw."""
        return self.is_played and self.home_score == self.away_score

    @property
    def total_goals(self) -> Optional[int]:
        """Total goals scored in the match."""
        if not self.is_played:
            return None
        return self.home_score + self.away_score


@dataclass
class Prediction:
    """Predicted outcome for a match between two teams."""
    home_team: str
    away_team: str
    home_elo: float
    away_elo: float
    home_win_pct: float
    draw_pct: float
    away_win_pct: float
    predicted_winner: Optional[str]
    confidence: str  # "high", "medium", "low"

    def __str__(self) -> str:
        return (
            f"{self.home_team} vs {self.away_team}\n"
            f"  {self.home_team} win: {self.home_win_pct:.1%} | "
            f"Draw: {self.draw_pct:.1%} | "
            f"{self.away_team} win: {self.away_win_pct:.1%}\n"
            f"  Predicted: {self.predicted_winner or 'Draw'} "
            f"(confidence: {self.confidence})"
        )
