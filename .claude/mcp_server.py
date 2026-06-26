#!/usr/bin/env python3
"""MCP server for the WC2026 World Cup Predictor.

Implements JSON-RPC 2.0 over stdio (MCP protocol).
Exposes tools: predict_match, list_all_teams, get_team_info, get_group.
"""

import json
import sys
from pathlib import Path

# Add parent dir to path so we can import wc2026
sys.path.insert(0, str(Path(__file__).parent.parent))

from wc2026.data import load_teams, get_team_by_name, get_team_by_code, get_groups, load_historical_matches
from wc2026.predictor import predict as predict_match

VERSION = "0.1.0"
SERVER_NAME = "wc2026-mcp"
_logf = None  # Debug log file handle


def _log(msg: str) -> None:
    """Write debug messages to a log file (stderr is consumed by MCP)."""
    global _logf
    if _logf is None:
        _logf = open(Path(__file__).parent / "mcp_debug.log", "w")
    _logf.write(f"[MCP] {msg}\n")
    _logf.flush()


def _send(response: dict) -> None:
    """Send a JSON-RPC response on stdout."""
    raw = json.dumps(response)
    sys.stdout.write(raw + "\n")
    sys.stdout.flush()


def _tool_definitions() -> list[dict]:
    """Return the tool definitions for tools/list."""
    return [
        {
            "name": "predict_match",
            "description": "Predict the outcome of a 2026 World Cup match between two teams "
                           "using Elo ratings. Returns win/draw probabilities, predicted "
                           "winner, and confidence level.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team_a": {
                        "type": "string",
                        "description": "First (home) team name or 3-letter FIFA code.",
                    },
                    "team_b": {
                        "type": "string",
                        "description": "Second (away) team name or 3-letter FIFA code.",
                    },
                    "stage": {
                        "type": "string",
                        "enum": ["group", "round_of_16", "quarterfinal", "semifinal", "final"],
                        "description": "Tournament stage. Affects draw probability "
                                       "(knockout stages have fewer draws due to extra time).",
                    },
                },
                "required": ["team_a", "team_b"],
            },
        },
        {
            "name": "list_all_teams",
            "description": "List all 48 qualified teams for the 2026 World Cup, "
                           "sorted by Elo rating. Includes FIFA codes, confederations, "
                           "group assignments, and Elo ratings.",
            "inputSchema": {"type": "object", "properties": {}},
        },
        {
            "name": "get_team_info",
            "description": "Get detailed information about a specific team: Elo rating, "
                           "group, confederation, FIFA code, and recent tournament history.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team": {
                        "type": "string",
                        "description": "Team name or 3-letter FIFA code.",
                    },
                },
                "required": ["team"],
            },
        },
        {
            "name": "get_group",
            "description": "Get all teams in a specific group (A-L) with their Elo ratings, "
                           "sorted strongest to weakest.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "group_letter": {
                        "type": "string",
                        "description": "Group letter from A to L.",
                        "pattern": "^[A-La-l]$",
                    },
                },
                "required": ["group_letter"],
            },
        },
    ]


def _resolve_team(name_or_code: str):
    """Look up a team by name or code. Returns Team or raises ValueError."""
    teams = load_teams()
    team = get_team_by_name(name_or_code, teams)
    if team:
        return team
    team = get_team_by_code(name_or_code, teams)
    if team:
        return team

    # Suggest similar names
    name_lower = name_or_code.lower()
    suggestions = [
        t.name for t in teams
        if name_lower[:2] in t.name.lower() or t.fifa_code.lower().startswith(name_lower[:2])
    ][:5]
    hint = f" Similar teams: {', '.join(suggestions)}" if suggestions else ""
    raise ValueError(f"Team not found: {name_or_code!r}.{hint}")


def handle_tools_call(name: str, arguments: dict) -> list[dict]:
    """Dispatch a tools/call to the right handler. Returns MCP content items."""
    if name == "predict_match":
        return _tool_predict_match(arguments)
    elif name == "list_all_teams":
        return _tool_list_all_teams(arguments)
    elif name == "get_team_info":
        return _tool_get_team_info(arguments)
    elif name == "get_group":
        return _tool_get_group(arguments)
    else:
        raise ValueError(f"Unknown tool: {name}")


def _tool_predict_match(args: dict) -> list[dict]:
    team_a = _resolve_team(args["team_a"])
    team_b = _resolve_team(args["team_b"])
    stage = args.get("stage")

    p = predict_match(team_a, team_b, stage)

    text = (
        f"Prediction: {p.home_team} vs {p.away_team}\n"
        f"  Elo: {p.home_elo:.0f} — {p.away_elo:.0f}\n"
        f"  {p.home_team} win: {p.home_win_pct:.1%}\n"
        f"  Draw:       {p.draw_pct:.1%}\n"
        f"  {p.away_team} win: {p.away_win_pct:.1%}\n"
        f"  Predicted winner: {p.predicted_winner or 'Draw'}\n"
        f"  Confidence: {p.confidence.upper()}"
    )
    return [{"type": "text", "text": text}]


def _tool_list_all_teams(args: dict) -> list[dict]:
    teams = load_teams()
    teams.sort(key=lambda t: -t.elo_rating)

    lines = [f"{'#':>3} {'Team':<22} {'Code':>4} {'Elo':>6}  {'Group':>5}  {'Confed'}"  , "─" * 58]
    for i, t in enumerate(teams, 1):
        lines.append(
            f"{i:>3} {t.name:<22} {t.fifa_code:>4} {t.elo_rating:>6.0f}  "
            f"{t.group:>5}  {t.confederation}"
        )
    return [{"type": "text", "text": "\n".join(lines)}]


def _tool_get_team_info(args: dict) -> list[dict]:
    team = _resolve_team(args["team"])
    historical = load_historical_matches()

    # Count matches
    wins = draws = losses = 0
    tournaments = set()
    for m in historical:
        if not m.is_played:
            continue
        if m.home == team.name or m.away == team.name:
            if m.tournament_year:
                tournaments.add(m.tournament_year)
            if m.winner == team.name:
                wins += 1
            elif m.is_draw:
                draws += 1
            else:
                losses += 1

    total = wins + draws + losses or 1
    text = (
        f"═══ {team.name} ({team.fifa_code}) ═══\n"
        f"  Confederation: {team.confederation}\n"
        f"  Group:         {team.group}\n"
        f"  Elo Rating:    {team.elo_rating:.0f}\n"
        f"  World Rank:    #{_find_rank(team.name)} / 48\n"
        f"  All-time W-D-L: {wins}-{draws}-{losses}\n"
        f"  Win rate:      {wins / total:.1%}\n"
        f"  Tournaments:   {len(tournaments)} ({', '.join(str(y) for y in sorted(tournaments, reverse=True))})"
    )
    return [{"type": "text", "text": text}]


def _find_rank(name: str) -> int:
    """Find the Elo rank of a team."""
    teams = load_teams()
    teams.sort(key=lambda t: -t.elo_rating)
    for i, t in enumerate(teams, 1):
        if t.name == name:
            return i
    return 0


def _tool_get_group(args: dict) -> list[dict]:
    letter = args["group_letter"].upper()
    groups = get_groups()
    if letter not in groups:
        return [{"type": "text", "text": f"Invalid group: {letter}. Valid: A-L"}]

    group_teams = sorted(groups[letter], key=lambda t: -t.elo_rating)

    lines = [
        f"═══ Group {letter} ═══",
        f"{'Team':<22} {'Code':>4} {'Elo':>6}  {'Confed'}",
        "─" * 42,
    ]
    for t in group_teams:
        lines.append(f"{t.name:<22} {t.fifa_code:>4} {t.elo_rating:>6.0f}  {t.confederation}")

    # Add match predictions
    lines.append("")
    lines.append("Group-stage match predictions:")
    for i, t1 in enumerate(group_teams):
        for t2 in group_teams[i + 1:]:
            p = predict_match(t1, t2, "group")
            lines.append(
                f"  {t1.name} vs {t2.name}: {p.predicted_winner or 'Draw'} "
                f"(W:{p.home_win_pct:.0%} D:{p.draw_pct:.0%} W:{p.away_win_pct:.0%}) "
                f"[{p.confidence}]"
            )

    return [{"type": "text", "text": "\n".join(lines)}]


def main() -> None:
    """Run the MCP server loop on stdin/stdout."""
    _log("MCP server starting")

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue

        try:
            request = json.loads(line)
        except json.JSONDecodeError as e:
            _log(f"JSON parse error: {e}")
            continue

        req_id = request.get("id")
        method = request.get("method", "")
        params = request.get("params", {})

        _log(f"← {method} id={req_id}")

        try:
            if method == "initialize":
                _send({
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "protocolVersion": "2025-03-26",
                        "serverInfo": {
                            "name": SERVER_NAME,
                            "version": VERSION,
                        },
                        "capabilities": {
                            "tools": {},
                        },
                    },
                })

            elif method == "notifications/initialized":
                # No response needed for notifications
                pass

            elif method == "tools/list":
                _send({
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {"tools": _tool_definitions()},
                })

            elif method == "tools/call":
                tool_name = params.get("name", "")
                tool_args = params.get("arguments", {})
                content = handle_tools_call(tool_name, tool_args)
                _send({
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {"content": content},
                })

            elif method == "ping":
                _send({"jsonrpc": "2.0", "id": req_id, "result": {}})

            else:
                _send({
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {
                        "code": -32601,
                        "message": f"Method not found: {method}",
                    },
                })

        except ValueError as e:
            _send({
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32602, "message": str(e)},
            })
        except Exception as e:
            _log(f"ERROR: {e}")
            _send({
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32603, "message": f"Internal error: {e}"},
            })

    _log("MCP server shutting down")


if __name__ == "__main__":
    main()
