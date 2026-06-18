"""Fetch live match data from football-data.org's free API.

Free tier: 10 requests/minute. We cache aggressively (60s TTL) to stay within limits.

Setup:
    export FOOTBALL_DATA_API_KEY="your-key-here"
    # or create a .env file in the project root with:
    # FOOTBALL_DATA_API_KEY=your-key-here

Endpoints used:
    GET /v4/competitions/WC/matches    — fixtures, live scores, results
    GET /v4/competitions/WC/standings  — group standings
"""

import json
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

import httpx

BASE_URL = "https://api.football-data.org/v4"
COMPETITION = "WC"  # World Cup competition code
CACHE_FILE = Path(__file__).parent.parent / "data" / "live_cache.json"
CACHE_TTL = 60  # seconds — free tier allows 10 req/min, so 60s is safe

# ── Data models for API responses ──────────────────────────────────────────


@dataclass
class LiveScore:
    """A scoreline from a match (can be partial during a live match)."""
    home: Optional[int] = None
    away: Optional[int] = None


@dataclass
class LiveMatch:
    """A match from the football-data.org API — live, scheduled, or finished."""
    match_id: int
    home_team: str
    away_team: str
    home_score: Optional[int]
    away_score: Optional[int]
    status: str  # "SCHEDULED", "LIVE", "IN_PLAY", "PAUSED", "FINISHED", "CANCELLED"
    stage: str   # "GROUP_STAGE", "ROUND_OF_16", etc.
    group: Optional[str]  # Group letter for group stage
    utc_date: str
    minute: Optional[int] = None  # Current minute if live, else None
    winner: Optional[str] = None  # "HOME_TEAM", "AWAY_TEAM", "DRAW", or None

    @property
    def is_live(self) -> bool:
        return self.status in ("LIVE", "IN_PLAY", "PAUSED")

    @property
    def is_finished(self) -> bool:
        return self.status == "FINISHED"

    @property
    def is_scheduled(self) -> bool:
        return self.status in ("SCHEDULED", "TIMED")

    @property
    def score_display(self) -> str:
        """Human-readable score: '2 - 1' or 'vs' for scheduled."""
        if self.home_score is not None and self.away_score is not None:
            return f"{self.home_score} - {self.away_score}"
        return "vs"

    @property
    def minute_display(self) -> str:
        """Human-readable time: '67'' or 'FT' or 'HT' or ''."""
        if self.status == "FINISHED":
            return "FT"
        if self.status == "PAUSED":
            return "HT"
        if self.minute is not None:
            return f"{self.minute}'"
        return ""


@dataclass
class GroupStanding:
    """A team's standing within a group."""
    group: str
    team_name: str
    position: int
    played: int
    won: int
    drawn: int
    lost: int
    goals_for: int
    goals_against: int
    goal_diff: int
    points: int


# ── API Key resolution ─────────────────────────────────────────────────────


def _get_api_key() -> str:
    """Resolve the football-data.org API key.

    Checks, in order:
        1. FOOTBALL_DATA_API_KEY environment variable
        2. .env file in project root
    """
    key = os.environ.get("FOOTBALL_DATA_API_KEY", "")
    if key:
        return key

    # Try .env file
    env_file = Path(__file__).parent.parent / ".env"
    if env_file.exists():
        try:
            from dotenv import load_dotenv
            load_dotenv(env_file)
            key = os.environ.get("FOOTBALL_DATA_API_KEY", "")
        except ImportError:
            pass

    return key


# ── Caching ─────────────────────────────────────────────────────────────────


def _cache_path(key: str) -> Path:
    """Map a logical key to a cache file path."""
    return Path(str(CACHE_FILE).replace(".json", f"_{key}.json"))


def _read_cache(key: str) -> Optional[dict]:
    """Read cached data if still fresh (< CACHE_TTL seconds old)."""
    path = _cache_path(key)
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        age = time.time() - data.get("_cached_at", 0)
        if age < CACHE_TTL:
            return data
    except (json.JSONDecodeError, IOError):
        pass
    return None


def _write_cache(key: str, data: dict) -> None:
    """Write data to cache with a timestamp."""
    path = _cache_path(key)
    data["_cached_at"] = time.time()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ── HTTP client ─────────────────────────────────────────────────────────────


def _client(api_key: str) -> httpx.Client:
    """Create an httpx client with the API key header."""
    return httpx.Client(
        base_url=BASE_URL,
        headers={"X-Auth-Token": api_key},
        timeout=15.0,
    )


# ── Public API ──────────────────────────────────────────────────────────────


def fetch_matches(
    status: Optional[str] = None,
    api_key: Optional[str] = None,
) -> list[LiveMatch]:
    """Fetch World Cup matches from football-data.org.

    Args:
        status: Filter by status — "SCHEDULED", "LIVE", "FINISHED", or None for all.
        api_key: football-data.org API key. If None, resolved from env/ .env.

    Returns:
        List of LiveMatch objects.
    """
    key = api_key or _get_api_key()
    if not key:
        raise ValueError(
            "No API key found. Set FOOTBALL_DATA_API_KEY env var "
            "or create a .env file. Get a free key at https://www.football-data.org/"
        )

    cache_key = f"matches_{status or 'all'}"
    cached = _read_cache(cache_key)
    if cached and "_embedded" not in cached:
        # Fall through — cache is just metadata, no data
        cached = None
    if cached:
        return _parse_matches(cached)

    try:
        with _client(key) as cli:
            params = {}
            if status:
                params["status"] = status
            resp = cli.get(f"/competitions/{COMPETITION}/matches", params=params)
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPError as e:
        # Try stale cache as fallback
        stale = _read_cache_stale(cache_key)
        if stale:
            return _parse_matches(stale)
        raise RuntimeError(f"Failed to fetch matches: {e}") from e

    _write_cache(cache_key, data)
    return _parse_matches(data)


def fetch_standings(api_key: Optional[str] = None) -> list[GroupStanding]:
    """Fetch World Cup group standings from football-data.org.

    Args:
        api_key: football-data.org API key. If None, resolved from env/ .env.

    Returns:
        List of GroupStanding objects (one per team per group).
    """
    key = api_key or _get_api_key()
    if not key:
        raise ValueError(
            "No API key found. Set FOOTBALL_DATA_API_KEY env var "
            "or create a .env file. Get a free key at https://www.football-data.org/"
        )

    cache_key = "standings"
    cached = _read_cache(cache_key)
    if cached and "standings" not in cached:
        cached = None
    if cached:
        return _parse_standings(cached)

    try:
        with _client(key) as cli:
            resp = cli.get(f"/competitions/{COMPETITION}/standings")
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPError as e:
        stale = _read_cache_stale(cache_key)
        if stale:
            return _parse_standings(stale)
        raise RuntimeError(f"Failed to fetch standings: {e}") from e

    _write_cache(cache_key, data)
    return _parse_standings(data)


# ── Parsers ─────────────────────────────────────────────────────────────────


def _parse_matches(data: dict) -> list[LiveMatch]:
    """Parse football-data.org /matches response into LiveMatch objects."""
    matches = []
    raw_matches = data.get("matches", [])

    for m in raw_matches:
        score = m.get("score", {})
        full_time = score.get("fullTime", {})
        minute_info = m.get("minute")

        # Determine winner
        winner = None
        if m["status"] == "FINISHED":
            winner = score.get("winner")  # "HOME_TEAM", "AWAY_TEAM", "DRAW"

        # Determine group
        group = m.get("group", "")
        if group and group.startswith("GROUP_"):
            group = group.replace("GROUP_", "")
        # Only keep single-letter group identifiers
        if group and len(group) > 1:
            group = ""

        matches.append(LiveMatch(
            match_id=m["id"],
            home_team=m["homeTeam"]["name"],
            away_team=m["awayTeam"]["name"],
            home_score=full_time.get("home"),
            away_score=full_time.get("away"),
            status=m["status"],
            stage=m.get("stage", "GROUP_STAGE"),
            group=group or None,
            utc_date=m["utcDate"],
            minute=minute_info.get("regular") if isinstance(minute_info, dict) else minute_info,
            winner=winner,
        ))

    return matches


def _parse_standings(data: dict) -> list[GroupStanding]:
    """Parse football-data.org /standings response into GroupStanding objects."""
    standings = []
    raw_standings = data.get("standings", [])

    for group_data in raw_standings:
        group = group_data.get("group", "")
        if group and group.startswith("GROUP_"):
            group = group.replace("GROUP_", "")
        if group and group.lower().startswith("group "):
            group = group[6:]  # Strip "Group " prefix

        for entry in group_data.get("table", []):
            standings.append(GroupStanding(
                group=group,
                team_name=entry["team"]["name"],
                position=entry["position"],
                played=entry["playedGames"],
                won=entry["won"],
                drawn=entry["draw"],
                lost=entry["lost"],
                goals_for=entry["goalsFor"],
                goals_against=entry["goalsAgainst"],
                goal_diff=entry["goalDifference"],
                points=entry["points"],
            ))

    return standings


def _read_cache_stale(key: str) -> Optional[dict]:
    """Read cache even if stale (fallback on API error)."""
    path = _cache_path(key)
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return None


def cache_age(key: str) -> Optional[float]:
    """Return the age of the cache in seconds, or None if no cache exists."""
    path = _cache_path(key)
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return time.time() - data.get("_cached_at", 0)
    except (json.JSONDecodeError, IOError):
        return None
