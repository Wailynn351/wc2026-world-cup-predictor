"""Load and cross-reference reference data from JSON files."""

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Optional

from wc2026.models import Team, Match


DATA_DIR = Path(__file__).parent.parent / "data"


def _load_json(filename: str) -> dict:
    """Load a JSON file from the data directory."""
    path = DATA_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Data file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def load_teams() -> list[Team]:
    """Load all 2026 World Cup teams with their Elo ratings."""
    teams_data = _load_json("teams.json")
    elo_data = _load_json("elo_ratings.json")
    elo_map: dict[str, float] = elo_data["ratings"]

    teams = []
    for t in teams_data["teams"]:
        name = t["name"]
        elo = elo_map.get(name, 1500.0)
        teams.append(Team(
            fifa_code=t["fifa_code"],
            name=name,
            confederation=t["confederation"],
            group=t["group"],
            elo_rating=elo,
        ))
    return teams


@lru_cache(maxsize=1)
def load_historical_matches() -> list[Match]:
    """Load all historical World Cup matches."""
    data = _load_json("historical_matches.json")
    matches = []
    for m in data["matches"]:
        matches.append(Match(
            home=m["home"],
            away=m["away"],
            home_score=m.get("home_score"),
            away_score=m.get("away_score"),
            tournament_year=m.get("year"),
            stage=m.get("stage"),
        ))
    return matches


def get_team_by_name(name: str, teams: Optional[list[Team]] = None) -> Optional[Team]:
    """Find a team by name (case-insensitive). Returns None if not found."""
    if teams is None:
        teams = load_teams()
    name_lower = name.lower()
    for team in teams:
        if team.name.lower() == name_lower:
            return team
    return None


def get_team_by_code(code: str, teams: Optional[list[Team]] = None) -> Optional[Team]:
    """Find a team by its 3-letter FIFA code. Returns None if not found."""
    if teams is None:
        teams = load_teams()
    code_upper = code.upper()
    for team in teams:
        if team.fifa_code == code_upper:
            return team
    return None


def get_groups(teams: Optional[list[Team]] = None) -> dict[str, list[Team]]:
    """Return teams grouped by their group letter."""
    if teams is None:
        teams = load_teams()
    groups: dict[str, list[Team]] = {}
    for team in teams:
        groups.setdefault(team.group, []).append(team)
    return dict(sorted(groups.items()))
