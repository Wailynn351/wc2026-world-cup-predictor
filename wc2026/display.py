"""Display utilities for formatted terminal output."""

import math
from typing import Optional

from wc2026.models import Team, Prediction

# ANSI color codes
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"
DIM = "\033[2m"

BAR_CHARS = ("█", "▓", "▒", "░")


def _bar(pct: float, width: int = 16) -> str:
    """Draw a horizontal bar chart."""
    filled = round(pct * width)
    if pct >= 0.40:
        color = GREEN
    elif pct >= 0.25:
        color = YELLOW
    else:
        color = RED
    return f"{color}{BAR_CHARS[0] * filled}{RESET}{DIM}{BAR_CHARS[3] * (width - filled)}{RESET}"


def _color_for_team(team_name: str) -> str:
    """Cycle through colors for team names (for distinguishing in tables)."""
    return team_name  # Just plain for now; can be colored later


def prediction_card(p: Prediction) -> str:
    """Render a single prediction as a rich match card."""
    lines = []
    lines.append("┌" + "─" * 58 + "┐")

    # Header line
    header = f"  {BOLD}{p.home_team} vs {p.away_team}{RESET}"
    lines.append(f"│{header:<62}│")

    # Elo line
    elo_line = f"  {DIM}Elo: {p.home_elo:.0f} — {p.away_elo:.0f}{RESET}"
    lines.append(f"│{elo_line:<62}│")
    lines.append("│" + " " * 58 + "│")

    # Probability bars
    bar_w = 40
    home_bar = _bar(p.home_win_pct, bar_w)
    draw_bar = _bar(p.draw_pct, bar_w)
    away_bar = _bar(p.away_win_pct, bar_w)

    lines.append(f"│  {p.home_team:<14} {home_bar} {p.home_win_pct:5.1%} │")
    lines.append(f"│  {'Draw':<14} {draw_bar} {p.draw_pct:5.1%} │")
    lines.append(f"│  {p.away_team:<14} {away_bar} {p.away_win_pct:5.1%} │")
    lines.append("│" + " " * 58 + "│")

    # Result line
    winner_text = p.predicted_winner or "Draw"
    conf_color = {"high": GREEN, "medium": YELLOW, "low": RED}
    color = conf_color.get(p.confidence, RESET)

    result = f"  Prediction: {BOLD}{winner_text}{RESET}"
    lines.append(f"│{result:<62}│")
    conf_line = f"  Confidence: {color}{p.confidence.upper()}{RESET}"
    lines.append(f"│{conf_line:<62}│")

    lines.append("└" + "─" * 58 + "┘")
    return "\n".join(lines)


def teams_table(teams: list[Team]) -> str:
    """Render a table of all teams."""
    teams_sorted = sorted(teams, key=lambda t: (-t.elo_rating, t.name))
    lines = []
    lines.append(f"{BOLD}{'Rank':<5} {'Team':<22} {'Code':<5} {'Elo':<8} {'Group':<6} {'Confed'}{RESET}")
    lines.append("─" * 64)

    for i, team in enumerate(teams_sorted, 1):
        if i <= 10:
            rank_color = GREEN
        elif i <= 30:
            rank_color = YELLOW
        else:
            rank_color = RESET
        lines.append(
            f"{rank_color}{i:<5}{RESET} "
            f"{team.name:<22} "
            f"{team.fifa_code:<5} "
            f"{team.elo_rating:>6.0f}  "
            f"{team.group:<6} "
            f"{DIM}{team.confederation}{RESET}"
        )
    return "\n".join(lines)


def group_table(group_letter: str, teams: list[Team]) -> str:
    """Render a group's teams with predictions header."""
    group_teams = sorted(
        [t for t in teams if t.group == group_letter.upper()],
        key=lambda t: -t.elo_rating
    )
    lines = []
    lines.append(f"\n{BOLD}{CYAN}╔══ Group {group_letter.upper()} ═══╗{RESET}")
    lines.append(f"{BOLD}{'Team':<22} {'Elo':<8}{RESET}")
    lines.append("─" * 30)
    for team in group_teams:
        lines.append(f"{team.name:<22} {team.elo_rating:>6.0f}")
    return "\n".join(lines)


def simulation_header() -> str:
    """Header for tournament simulation output."""
    return f"""
{BOLD}{CYAN}╔══════════════════════════════════════════════════╗
║     2026 FIFA WORLD CUP — FULL SIMULATION        ║
╚══════════════════════════════════════════════════╝{RESET}
"""


def round_header(round_name: str) -> str:
    """Section header for a tournament round."""
    w = 50
    pad = (w - len(round_name) - 2) // 2
    return f"\n{BOLD}{'─' * pad} {round_name} {'─' * pad}{RESET}\n"


def knockout_result(home: str, away: str, winner: str, home_score: int, away_score: int) -> str:
    """Render a knockout match result."""
    if winner == home:
        hl, al = BOLD + GREEN, RESET
    elif winner == away:
        hl, al = RESET, BOLD + GREEN
    else:
        hl = al = RESET

    return f"  {hl}{home:<20}{RESET} {home_score} - {away_score} {al}{away:<20}{RESET}"


def stats_display(team: Team, matches_played: int, wins: int, draws: int, losses: int) -> str:
    """Render a team stats card."""
    total = matches_played or 1
    lines = []
    lines.append(f"\n{BOLD}═══ {team.name} ({team.fifa_code}) ═══{RESET}")
    lines.append(f"  Confederation: {team.confederation}")
    lines.append(f"  Group:         {team.group}")
    lines.append(f"  Elo Rating:    {team.elo_rating:.0f}")
    lines.append(f"  All-time W-D-L: {wins}-{draws}-{losses}")
    lines.append(f"  Win rate:      {wins/total:.1%}")
    return "\n".join(lines)
