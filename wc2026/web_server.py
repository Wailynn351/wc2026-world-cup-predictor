"""FastAPI web server for the WC2026 World Cup Predictor.

Serves:
    - Web UI pages (Jinja2 templates)
    - JSON API endpoints (mirrors MCP tools + live scores)

Usage:
    python -m wc2026 web
    python -m wc2026 web --port 3000 --host 0.0.0.0
"""

from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from jinja2 import Environment, FileSystemLoader, select_autoescape

from wc2026.data import load_teams, get_team_by_name, get_team_by_code, get_groups
from wc2026.predictor import predict as predict_match

TEMPLATES_DIR = Path(__file__).parent / "templates"

_env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR.resolve())),
    autoescape=select_autoescape(["html"]),
)


def _render(template_name: str, context: dict) -> HTMLResponse:
    """Render a Jinja2 template to an HTML response."""
    template = _env.get_template(template_name)
    return HTMLResponse(template.render(**context))


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="WC2026 Predictor",
        description="2026 FIFA World Cup match predictor with live scores",
        version="0.2.0",
    )

    # ── Page routes ─────────────────────────────────────────────────────

    @app.get("/", response_class=HTMLResponse)
    async def dashboard(request: Request):
        """Dashboard: live scores + quick predictions."""
        teams = load_teams()
        live_matches = _try_fetch_matches()

        return _render("index.html", {
            "request": request,
            "teams": _team_list(teams),
            "live_matches": live_matches,
            "has_api_key": _has_api_key(),
        })

    @app.get("/matches", response_class=HTMLResponse)
    async def matches_page(
        request: Request,
        status: Optional[str] = Query(None, description="Filter: LIVE, FINISHED, SCHEDULED"),
        group: Optional[str] = Query(None, description="Filter by group A-L"),
    ):
        """All matches page with filters."""
        teams = load_teams()
        live_matches = _try_fetch_matches(status=status)

        if group:
            live_matches = [m for m in live_matches if m.group == group.upper()]

        return _render("matches.html", {
            "request": request,
            "matches": live_matches,
            "teams": _team_list(teams),
            "current_status": status or "",
            "current_group": group or "",
        })

    @app.get("/groups", response_class=HTMLResponse)
    async def groups_page(request: Request):
        """Group standings page."""
        teams = load_teams()
        groups = get_groups(teams)
        standings = _try_fetch_standings()

        # Build group data with predictions
        group_data = {}
        for letter in sorted(groups.keys()):
            group_teams = sorted(groups[letter], key=lambda t: -t.elo_rating)
            preds = []
            for i, t1 in enumerate(group_teams):
                for t2 in group_teams[i + 1:]:
                    preds.append(predict_match(t1, t2, "group"))
            group_data[letter] = {
                "teams": group_teams,
                "predictions": preds,
                "standings": [s for s in standings if s.group == letter] if standings else [],
            }

        return _render("groups.html", {
            "request": request,
            "group_data": group_data,
        })

    @app.get("/teams", response_class=HTMLResponse)
    async def teams_page(request: Request):
        """Team rankings and list."""
        teams = load_teams()
        teams_sorted = sorted(teams, key=lambda t: (-t.elo_rating, t.name))
        team_dicts = [
            {"name": t.name, "code": t.fifa_code, "elo": int(t.elo_rating),
             "group": t.group, "confederation": t.confederation}
            for t in teams_sorted
        ]
        return _render("teams.html", {
            "request": request,
            "teams": team_dicts,
        })

    @app.get("/predict", response_class=HTMLResponse)
    async def predict_page(
        request: Request,
        home: Optional[str] = Query(None),
        away: Optional[str] = Query(None),
        stage: Optional[str] = Query(None),
    ):
        """Prediction form and result."""
        teams = load_teams()
        result = None
        error = None

        if home and away:
            home_team = get_team_by_name(home, teams) or get_team_by_code(home, teams)
            away_team = get_team_by_name(away, teams) or get_team_by_code(away, teams)

            if not home_team:
                error = f"Team not found: {home}"
            elif not away_team:
                error = f"Team not found: {away}"
            else:
                result = predict_match(home_team, away_team, stage or None)

        return _render("predict.html", {
            "request": request,
            "teams": _team_list(teams),
            "home": home or "",
            "away": away or "",
            "stage": stage or "",
            "prediction": result,
            "error": error,
        })

    @app.get("/match/{match_id}", response_class=HTMLResponse)
    async def match_detail(request: Request, match_id: int):
        """Single match detail with prediction vs actual."""
        teams = load_teams()
        matches = _try_fetch_matches()
        match = None
        for m in matches:
            if m.match_id == match_id:
                match = m
                break

        if not match:
            return HTMLResponse("<h1>Match not found</h1>", status_code=404)

        # Try to generate prediction
        pred = None
        home_team = get_team_by_name(match.home_team, teams)
        away_team = get_team_by_name(match.away_team, teams)
        if home_team and away_team:
            stage = match.stage.lower() if match.stage else None
            pred = predict_match(home_team, away_team, stage)

        return _render("match_detail.html", {
            "request": request,
            "match": match,
            "prediction": pred,
        })

    # ── JSON API routes ──────────────────────────────────────────────────

    @app.get("/api/predict")
    async def api_predict(
        home: str = Query(..., description="Home team name or FIFA code"),
        away: str = Query(..., description="Away team name or FIFA code"),
        stage: Optional[str] = Query(None, description="Tournament stage"),
    ):
        """Predict a match outcome (JSON)."""
        teams = load_teams()
        home_team = get_team_by_name(home, teams) or get_team_by_code(home, teams)
        away_team = get_team_by_name(away, teams) or get_team_by_code(away, teams)

        if not home_team:
            return JSONResponse({"error": f"Team not found: {home}"}, status_code=404)
        if not away_team:
            return JSONResponse({"error": f"Team not found: {away}"}, status_code=404)

        p = predict_match(home_team, away_team, stage)
        return {
            "home_team": p.home_team,
            "away_team": p.away_team,
            "home_elo": p.home_elo,
            "away_elo": p.away_elo,
            "home_win_pct": p.home_win_pct,
            "draw_pct": p.draw_pct,
            "away_win_pct": p.away_win_pct,
            "predicted_winner": p.predicted_winner,
            "confidence": p.confidence,
        }

    @app.get("/api/teams")
    async def api_teams():
        """List all 48 teams (JSON)."""
        teams = load_teams()
        teams.sort(key=lambda t: -t.elo_rating)
        return [
            {
                "name": t.name,
                "fifa_code": t.fifa_code,
                "confederation": t.confederation,
                "group": t.group,
                "elo_rating": t.elo_rating,
            }
            for t in teams
        ]

    @app.get("/api/team/{name}")
    async def api_team(name: str):
        """Get a single team's details (JSON)."""
        teams = load_teams()
        team = get_team_by_name(name, teams) or get_team_by_code(name, teams)
        if not team:
            return JSONResponse({"error": f"Team not found: {name}"}, status_code=404)
        return {
            "name": team.name,
            "fifa_code": team.fifa_code,
            "confederation": team.confederation,
            "group": team.group,
            "elo_rating": team.elo_rating,
        }

    @app.get("/api/group/{letter}")
    async def api_group(letter: str):
        """Get a group's teams and predictions (JSON)."""
        groups = get_groups()
        letter = letter.upper()
        if letter not in groups:
            return JSONResponse({"error": f"Invalid group: {letter}"}, status_code=404)

        group_teams = sorted(groups[letter], key=lambda t: -t.elo_rating)
        predictions = []
        for i, t1 in enumerate(group_teams):
            for t2 in group_teams[i + 1:]:
                p = predict_match(t1, t2, "group")
                predictions.append({
                    "home": p.home_team,
                    "away": p.away_team,
                    "home_win_pct": p.home_win_pct,
                    "draw_pct": p.draw_pct,
                    "away_win_pct": p.away_win_pct,
                    "predicted_winner": p.predicted_winner,
                    "confidence": p.confidence,
                })

        return {
            "group": letter,
            "teams": [
                {"name": t.name, "fifa_code": t.fifa_code, "elo_rating": t.elo_rating}
                for t in group_teams
            ],
            "predictions": predictions,
        }

    @app.get("/api/live")
    async def api_live():
        """Get live scores (JSON)."""
        matches = _try_fetch_matches()
        return [
            {
                "match_id": m.match_id,
                "home_team": m.home_team,
                "away_team": m.away_team,
                "home_score": m.home_score,
                "away_score": m.away_score,
                "status": m.status,
                "stage": m.stage,
                "group": m.group,
                "utc_date": m.utc_date,
                "minute": m.minute_display,
                "winner": m.winner,
            }
            for m in matches
        ]

    @app.get("/api/standings")
    async def api_standings():
        """Get group standings (JSON)."""
        standings = _try_fetch_standings()
        return [
            {
                "group": s.group,
                "team_name": s.team_name,
                "position": s.position,
                "played": s.played,
                "won": s.won,
                "drawn": s.drawn,
                "lost": s.lost,
                "goals_for": s.goals_for,
                "goals_against": s.goals_against,
                "goal_diff": s.goal_diff,
                "points": s.points,
            }
            for s in standings
        ]

    return app


# ── Helpers ───────────────────────────────────────────────────────────────


def _team_list(teams) -> list[dict]:
    """Convert teams to a list of dicts for templates."""
    return sorted(
        [{"name": t.name, "code": t.fifa_code, "elo": t.elo_rating,
          "group": t.group, "confederation": t.confederation} for t in teams],
        key=lambda t: (-t["elo"], t["name"]),
    )


def _has_api_key() -> bool:
    """Check if the football-data.org API key is configured."""
    import os
    return bool(os.environ.get("FOOTBALL_DATA_API_KEY", "")) or \
        (Path(__file__).parent.parent / ".env").exists()


def _try_fetch_matches(status=None) -> list:
    """Try to fetch live matches; return empty list on failure."""
    try:
        from wc2026.score_fetcher import fetch_matches
        return fetch_matches(status=status)
    except Exception:
        return []


def _try_fetch_standings() -> list:
    """Try to fetch standings; return empty list on failure."""
    try:
        from wc2026.score_fetcher import fetch_standings
        return fetch_standings()
    except Exception:
        return []
