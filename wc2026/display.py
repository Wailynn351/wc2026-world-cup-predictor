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


_TEAM_COLORS = [
    "\033[96m",   # cyan
    "\033[93m",   # yellow
    "\033[95m",   # magenta
    "\033[94m",   # blue
    "\033[92m",   # green
    "\033[91m",   # red
    "\033[36m",   # dark cyan
    "\033[33m",   # dark yellow
]


def _color_for_team(team_name: str) -> str:
    """Assign a consistent color to a team name for visual distinction."""
    idx = hash(team_name) % len(_TEAM_COLORS)
    return f"{_TEAM_COLORS[idx]}{team_name}{RESET}"


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


def live_match_card(match, prediction=None) -> str:
    """Render a single live/ finished/ scheduled match with optional prediction.

    Args:
        match: A LiveMatch from score_fetcher.
        prediction: Optional Prediction object for comparison.

    Returns:
        Formatted match card string.
    """
    from wc2026.score_fetcher import LiveMatch

    lines = []
    lines.append("┌" + "─" * 58 + "┐")

    # Status badge
    if match.is_live:
        badge = f"{RED}● LIVE{RESET}"
    elif match.is_finished:
        badge = f"{DIM}FT{RESET}"
    else:
        badge = f"{DIM}UPCOMING{RESET}"

    # Header
    status_line = f"  {badge}  {match.home_team} {match.score_display} {match.away_team}"
    lines.append(f"│{status_line:<62}│")

    if match.minute_display:
        minute_line = f"  {DIM}{match.minute_display}{RESET}"
        lines.append(f"│{minute_line:<62}│")

    lines.append("│" + " " * 58 + "│")

    # Group / stage info
    meta = f"  {DIM}Stage: {match.stage}"
    if match.group:
        meta += f" | Group {match.group}"
    meta += f"{RESET}"
    lines.append(f"│{meta:<62}│")

    # Prediction comparison (if available)
    if prediction and match.is_finished:
        lines.append("│" + " " * 58 + "│")
        pred_line = f"  {DIM}Predicted: {prediction.predicted_winner or 'Draw'}{RESET}"
        lines.append(f"│{pred_line:<62}│")

        actual_winner = match.winner
        if actual_winner == "HOME_TEAM":
            actual = match.home_team
        elif actual_winner == "AWAY_TEAM":
            actual = match.away_team
        elif actual_winner == "DRAW":
            actual = "Draw"
        else:
            actual = "?"

        # Compare
        pred_name = prediction.predicted_winner or "Draw"
        if pred_name == actual:
            acc = f"{GREEN}✓ Correct!{RESET}"
        else:
            acc = f"{RED}✗ Miss{RESET}"
        actual_line = f"  Actual: {actual}  {acc}"
        lines.append(f"│{actual_line:<62}│")

    lines.append("└" + "─" * 58 + "┘")
    return "\n".join(lines)


def live_scores_banner(matches) -> str:
    """Render a compact live scores banner for all live matches.

    Args:
        matches: List of LiveMatch objects (live or recently finished).

    Returns:
        Formatted banner string.
    """
    from wc2026.score_fetcher import LiveMatch

    live = [m for m in matches if m.is_live]
    finished = [m for m in matches if m.is_finished]
    scheduled = [m for m in matches if m.is_scheduled]

    lines = []
    lines.append(f"\n{BOLD}{CYAN}╔══ LIVE SCORES ═══════════════════════════════════╗{RESET}")

    if live:
        for m in live:
            pulse = f"{RED}●{RESET}"
            lines.append(
                f"  {pulse} {BOLD}{_color_for_team(m.home_team)}{RESET} {m.score_display} "
                f"{BOLD}{_color_for_team(m.away_team)}{RESET}  {RED}{m.minute_display}{RESET}"
            )
        lines.append("")

    if finished:
        lines.append(f"  {DIM}── Recent Results ──{RESET}")
        for m in finished[-6:]:  # Last 6 finished matches
            lines.append(
                f"     {m.home_team} {m.score_display} {m.away_team}  {DIM}FT{RESET}"
            )
        lines.append("")

    if scheduled:
        lines.append(f"  {DIM}── Upcoming ──{RESET}")
        for m in scheduled[:4]:  # Next 4 matches
            utc_dt = m.utc_date[:16].replace("T", " ") if m.utc_date else "TBD"
            lines.append(f"     {m.home_team} vs {m.away_team}  {DIM}{utc_dt}{RESET}")

    lines.append(f"{CYAN}╚══════════════════════════════════════════════════╝{RESET}")
    return "\n".join(lines)


def standing_table(standings, group_letter: str = None) -> str:
    """Render a group standing table.

    Args:
        standings: List of GroupStanding objects.
        group_letter: If provided, filter to this group only.

    Returns:
        Formatted table string.
    """
    from wc2026.score_fetcher import GroupStanding

    if group_letter:
        # Normalize: users might filter by "A" or "Group A"
        search = group_letter.upper().replace("GROUP ", "")
        standings = [s for s in standings if s.group.replace("Group ", "").upper() == search]

    if not standings:
        return f"{DIM}No standings data available.{RESET}"

    # Group by group letter
    groups: dict[str, list] = {}
    for s in standings:
        groups.setdefault(s.group, []).append(s)

    lines = []
    for grp in sorted(groups.keys()):
        grp_label = grp.replace("Group ", "") if grp.startswith("Group ") else grp
        lines.append(f"\n{BOLD}{CYAN}═══ Group {grp_label} ═══{RESET}")
        lines.append(
            f"{'#':>2} {'Team':<20} {'P':>2} {'W':>2} {'D':>2} "
            f"{'L':>2} {'GF':>2} {'GA':>2} {'GD':>3} {'Pts':>3}"
        )
        lines.append("─" * 52)
        for s in sorted(groups[grp], key=lambda x: x.position):
            pos_color = GREEN if s.position <= 2 else RESET
            lines.append(
                f"{pos_color}{s.position:>2}{RESET} "
                f"{s.team_name:<20} {s.played:>2} {s.won:>2} {s.drawn:>2} "
                f"{s.lost:>2} {s.goals_for:>2} {s.goals_against:>2} "
                f"{s.goal_diff:>+3} {s.points:>3}"
            )

    return "\n".join(lines)


def prediction_vs_actual_card(match, prediction) -> str:
    """Side-by-side comparison of prediction vs actual result.

    Args:
        match: A LiveMatch (must be finished).
        prediction: A Prediction object.

    Returns:
        Formatted comparison card.
    """
    from wc2026.score_fetcher import LiveMatch

    lines = []
    lines.append("┌" + "─" * 58 + "┐")

    # Match header
    lines.append(f"│  {BOLD}{match.home_team} vs {match.away_team}{RESET:<52}│")
    lines.append("│" + " " * 58 + "│")

    # Prediction column
    pred_winner = prediction.predicted_winner or "Draw"
    lines.append(f"│  {DIM}Predicted:{RESET}  {pred_winner:<20} "
                 f"{GREEN}{prediction.home_win_pct:.0%}{RESET} / "
                 f"{YELLOW}{prediction.draw_pct:.0%}{RESET} / "
                 f"{RED}{prediction.away_win_pct:.0%}│")

    # Actual column
    actual_winner = match.winner
    if actual_winner == "HOME_TEAM":
        actual = match.home_team
    elif actual_winner == "AWAY_TEAM":
        actual = match.away_team
    elif actual_winner == "DRAW":
        actual = "Draw"
    else:
        actual = "N/A"

    lines.append(f"│  {DIM}Actual:{RESET}     {actual:<20} "
                 f"{match.home_score or '?'} - {match.away_score or '?'}│")
    lines.append("│" + " " * 58 + "│")

    # Accuracy
    if prediction.predicted_winner == actual or (prediction.predicted_winner is None and actual_winner == "DRAW"):
        verdict = f"{GREEN}✓ Prediction correct!{RESET}"
    elif actual_winner == "DRAW" and prediction.predicted_winner is not None:
        verdict = f"{YELLOW}△ Predicted winner, got draw{RESET}"
    elif actual_winner not in ("HOME_TEAM", "AWAY_TEAM"):
        verdict = f"{DIM}? Unknown{RESET}"
    else:
        verdict = f"{RED}✗ Prediction incorrect{RESET}"
    lines.append(f"│  {verdict:<54}│")

    lines.append("└" + "─" * 58 + "┘")
    return "\n".join(lines)


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
