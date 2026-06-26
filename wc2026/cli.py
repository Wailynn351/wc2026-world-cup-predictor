"""CLI for the 2026 World Cup Match Predictor.

Usage:
    python -m wc2026 predict "Argentina" "France"
    python -m wc2026 predict "Brazil" "Germany" --stage semifinal
    python -m wc2026 group A
    python -m wc2026 teams
    python -m wc2026 simulate
    python -m wc2026 stats "Argentina"
"""

import argparse
import math
import random
import sys
from collections import defaultdict
from typing import Optional

from wc2026.data import (
    load_teams,
    load_historical_matches,
    get_team_by_name,
    get_team_by_code,
    get_groups,
)
from wc2026.models import Team, Match
from wc2026.predictor import predict
from wc2026.display import (
    prediction_card,
    teams_table,
    group_table,
    simulation_header,
    round_header,
    knockout_result,
    stats_display,
    live_match_card,
    live_scores_banner,
    standing_table,
    prediction_vs_actual_card,
    GREEN,
    RED,
    CYAN,
    BOLD,
    RESET,
    DIM,
)


def cmd_predict(args: argparse.Namespace) -> None:
    """Handle the 'predict' subcommand."""
    teams = load_teams()

    home = get_team_by_name(args.team_a, teams)
    if not home:
        home = get_team_by_code(args.team_a, teams)
    if not home:
        print(f"Team not found: {args.team_a}")
        print("Use 'wc2026 teams' to see all teams.")
        return

    away = get_team_by_name(args.team_b, teams)
    if not away:
        away = get_team_by_code(args.team_b, teams)
    if not away:
        print(f"Team not found: {args.team_b}")
        print("Use 'wc2026 teams' to see all teams.")
        return

    stage = getattr(args, "stage", None)
    result = predict(home, away, stage)
    print(prediction_card(result))


def cmd_group(args: argparse.Namespace) -> None:
    """Handle the 'group' subcommand — predict all matches in a group."""
    teams = load_teams()
    group_letter = args.group_letter.upper()

    group_teams = sorted(
        [t for t in teams if t.group == group_letter],
        key=lambda t: -t.elo_rating
    )

    if not group_teams:
        print(f"No teams found in Group {group_letter}. Valid groups: A-L")
        return

    print(group_table(group_letter, teams))
    print(f"\n{BOLD}Match Predictions:{RESET}\n")

    for i, t1 in enumerate(group_teams):
        for t2 in group_teams[i + 1:]:
            result = predict(t1, t2, "group")
            print(prediction_card(result))
            print()


def cmd_teams(args: argparse.Namespace) -> None:
    """Handle the 'teams' subcommand — list all teams."""
    teams = load_teams()
    print(teams_table(teams))


def _simulate_knockout_match(
    home: Team,
    away: Team,
    stage: str,
    elo_adjustments: dict[str, float],
) -> Team:
    """Simulate a single knockout match, returning the winner."""
    # Apply Elo adjustments from previous results
    home_adj = home.elo_rating + elo_adjustments.get(home.name, 0)
    away_adj = away.elo_rating + elo_adjustments.get(away.name, 0)

    # Create temporary teams with adjusted ratings
    home_tmp = Team(home.fifa_code, home.name, home.confederation, home.group, home_adj)
    away_tmp = Team(away.fifa_code, away.name, away.confederation, away.group, away_adj)

    pred = predict(home_tmp, away_tmp, stage)

    # Roll the dice
    roll = random.random()
    if roll < pred.home_win_pct:
        winner = home
    elif roll < pred.home_win_pct + pred.draw_pct:
        # Draw → pick winner randomly (simulating extra time/penalties)
        winner = home if random.random() < 0.5 else away
    else:
        winner = away

    # Simulate a scoreline (simple Poisson-inspired)
    elo_gap = home_adj - away_adj
    expected_goals_winner = max(0.5, 2.0 + elo_gap / 400)
    expected_goals_loser = max(0, 1.2 - elo_gap / 800)
    w_goals = max(1, round(random.gauss(expected_goals_winner, 1.0)))
    l_goals = round(random.gauss(expected_goals_loser, 0.8))
    l_goals = max(0, min(l_goals, w_goals - 1))  # Ensure winner scores more

    if winner == home:
        home_score, away_score = w_goals, l_goals
    else:
        home_score, away_score = l_goals, w_goals

    print(knockout_result(home.name, away.name, winner.name, home_score, away_score))

    # Small Elo bump for winning
    elo_adjustments[winner.name] = elo_adjustments.get(winner.name, 0) + 25
    return winner


def cmd_simulate(args: argparse.Namespace) -> None:
    """Handle the 'simulate' subcommand — run a full tournament simulation."""
    teams = load_teams()
    random.seed(getattr(args, "seed", None))

    print(simulation_header())

    # ── Group Stage ──
    print(round_header("GROUP STAGE"))
    groups = get_groups(teams)
    knockout_teams: list[Team] = []
    elo_adjustments: dict[str, float] = defaultdict(float)

    for group_letter, group_teams in sorted(groups.items()):
        # Simulate group matches
        standings: dict[str, int] = defaultdict(int)  # team_name -> points
        goal_diff: dict[str, int] = defaultdict(int)

        for i, t1 in enumerate(group_teams):
            for t2 in group_teams[i + 1:]:
                pred = predict(t1, t2, "group")
                roll = random.random()
                if roll < pred.home_win_pct:
                    standings[t1.name] += 3
                    goal_diff[t1.name] += 1
                    goal_diff[t2.name] -= 1
                elif roll < pred.home_win_pct + pred.draw_pct:
                    standings[t1.name] += 1
                    standings[t2.name] += 1
                else:
                    standings[t2.name] += 3
                    goal_diff[t2.name] += 1
                    goal_diff[t1.name] -= 1

        # Sort by points, then goal diff, then Elo
        sorted_teams = sorted(
            group_teams,
            key=lambda t: (standings[t.name], goal_diff[t.name], t.elo_rating),
            reverse=True,
        )

        # Top 2 advance
        adv1, adv2 = sorted_teams[0], sorted_teams[1]
        knockout_teams.append(adv1)
        knockout_teams.append(adv2)

        # Display group results
        print(f"  Group {group_letter}: ", end="")
        for i, t in enumerate(sorted_teams):
            suffix = f" {GREEN}▲{RESET}" if i < 2 else ""
            print(f"{t.name}({standings[t.name]}pt){suffix}  ", end="")
        print()

    # ── Knockout Stage ──
    # Round of 32: top 2 from each group (24) + 8 best 3rd-placed teams
    # Simplified: take all 24 top-2 teams
    # For a 48-team tournament, we need 32 teams in R32, then 16, 8, 4, 2

    # Select 8 best 3rd-placed from groups (simplified: take highest Elo 3rd-placed)
    third_placed = []
    for group_letter, group_teams in sorted(groups.items()):
        sorted_teams = sorted(group_teams, key=lambda t: t.elo_rating, reverse=True)
        third_placed.append(sorted_teams[2])
    third_placed.sort(key=lambda t: -t.elo_rating)
    knockout_teams.extend(third_placed[:8])

    # Seed by Elo
    knockout_teams.sort(key=lambda t: -t.elo_rating)

    # Round of 32
    print(round_header("ROUND OF 32"))
    r32_winners = []
    for i in range(0, 32, 2):
        winner = _simulate_knockout_match(
            knockout_teams[i], knockout_teams[31 - i],
            "round_of_16", elo_adjustments
        )
        r32_winners.append(winner)

    # Round of 16
    print(round_header("ROUND OF 16"))
    r16_winners = []
    for i in range(0, 16, 2):
        winner = _simulate_knockout_match(
            r32_winners[i], r32_winners[i + 1],
            "round_of_16", elo_adjustments
        )
        r16_winners.append(winner)

    # Quarterfinals
    print(round_header("QUARTERFINALS"))
    qf_winners = []
    for i in range(0, 8, 2):
        winner = _simulate_knockout_match(
            r16_winners[i], r16_winners[i + 1],
            "quarterfinal", elo_adjustments
        )
        qf_winners.append(winner)

    # Semifinals
    print(round_header("SEMIFINALS"))
    sf_winners = []
    for i in range(0, 4, 2):
        winner = _simulate_knockout_match(
            qf_winners[i], qf_winners[i + 1],
            "semifinal", elo_adjustments
        )
        sf_winners.append(winner)

    # Third-place match
    print(round_header("THIRD PLACE MATCH"))
    third_place_losers = [t for t in qf_winners if t not in sf_winners]
    if len(third_place_losers) >= 2:
        _simulate_knockout_match(
            third_place_losers[0], third_place_losers[1],
            "semifinal", elo_adjustments
        )

    # Final
    print(round_header("FINAL"))
    champion = _simulate_knockout_match(
        sf_winners[0], sf_winners[1],
        "final", elo_adjustments
    )

    print(f"\n{BOLD}{GREEN}╔══════════════════════════════════╗")
    print(f"║  CHAMPION: {champion.name:<21}║")
    print(f"╚══════════════════════════════════╝{RESET}\n")


def cmd_stats(args: argparse.Namespace) -> None:
    """Handle the 'stats' subcommand — show team history and info."""
    teams = load_teams()
    team = get_team_by_name(args.team, teams)
    if not team:
        team = get_team_by_code(args.team, teams)
    if not team:
        print(f"Team not found: {args.team}")
        return

    # Count historical matches for this team
    historical = load_historical_matches()
    wins = draws = losses = 0
    for m in historical:
        if not m.is_played:
            continue
        if m.home == team.name:
            if m.home_score > m.away_score:
                wins += 1
            elif m.home_score == m.away_score:
                draws += 1
            else:
                losses += 1
        elif m.away == team.name:
            if m.away_score > m.home_score:
                wins += 1
            elif m.home_score == m.away_score:
                draws += 1
            else:
                losses += 1

    print(stats_display(team, wins + draws + losses, wins, draws, losses))

    # Show tournament history
    tournaments = defaultdict(list)
    for m in historical:
        if m.tournament_year and (m.home == team.name or m.away == team.name):
            if m.tournament_year not in tournaments[m.tournament_year]:
                tournaments[m.tournament_year].append(m)

    if tournaments:
        print(f"\n  {BOLD}Tournament History:{RESET}")
        for year in sorted(tournaments.keys(), reverse=True)[:10]:
            matches = tournaments[year]
            results = []
            for m in matches:
                if m.home == team.name:
                    results.append(f"{'W' if m.winner == team.name else 'D' if m.is_draw else 'L'} "
                                   f"{m.home_score}-{m.away_score} vs {m.away}")
                else:
                    results.append(f"{'W' if m.winner == team.name else 'D' if m.is_draw else 'L'} "
                                   f"{m.away_score}-{m.home_score} vs {m.home}")
            print(f"    {year}: {', '.join(results)}")


def cmd_live(args: argparse.Namespace) -> None:
    """Handle the 'live' subcommand — fetch and display live scores."""
    from wc2026.score_fetcher import fetch_matches, fetch_standings, cache_age

    status = getattr(args, "status", None)
    group_filter = getattr(args, "group", None)

    try:
        matches = fetch_matches(status=status)
    except ValueError as e:
        print(f"{RED}Error: {e}{RESET}")
        return
    except RuntimeError as e:
        print(f"{RED}API error: {e}{RESET}")
        return

    if not matches:
        print(f"{DIM}No matches found.{RESET}")
        return

    # Filter by group if requested
    if group_filter:
        group_upper = group_filter.upper()
        matches = [m for m in matches if m.group == group_upper]
        if not matches:
            print(f"{DIM}No matches found for Group {group_upper}.{RESET}")
            return

    # Show cache age
    age = cache_age(f"matches_{status or 'all'}")
    if age is not None:
        print(f"{DIM}Data age: {age:.0f}s ago{RESET}\n")

    # Live scores banner
    print(live_scores_banner(matches))

    # Detailed match cards
    if not getattr(args, "compact", False):
        print(f"\n{BOLD}Match Details:{RESET}\n")
        for m in matches:
            if m.is_live or m.is_finished:
                # Try to get prediction for comparison
                teams = load_teams()
                home = get_team_by_name(m.home_team, teams)
                away = get_team_by_name(m.away_team, teams)
                if home and away:
                    pred = predict(home, away, m.stage.lower() if m.stage else None)
                    print(live_match_card(m, pred))
                else:
                    print(live_match_card(m))
                print()

    # Standings
    if not getattr(args, "no_standings", False):
        try:
            standings = fetch_standings()
            print(standing_table(standings, group_filter))
        except (RuntimeError, ValueError):
            pass  # Silently skip if standings unavailable


def cmd_web(args: argparse.Namespace) -> None:
    """Handle the 'web' subcommand — launch the web UI."""
    import os

    try:
        from wc2026.web_server import create_app
    except ImportError as e:
        print(f"{RED}Missing dependencies. Install with:{RESET}")
        print("  pip install fastapi uvicorn jinja2 python-dotenv")
        print(f"\n{RED}Error: {e}{RESET}")
        return

    host = getattr(args, "host", "127.0.0.1")
    port = getattr(args, "port", 8080)

    print(f"\n{BOLD}{CYAN}╔══ WC2026 Web UI ═══════════════════════════════════╗{RESET}")
    print(f"{BOLD}{CYAN}║  Starting server at http://{host}:{port}          {' ' * (24 - len(str(port)))}║{RESET}")
    print(f"{BOLD}{CYAN}║  Press Ctrl+C to stop                              ║{RESET}")
    print(f"{BOLD}{CYAN}╚══════════════════════════════════════════════════════╝{RESET}\n")

    import uvicorn
    app = create_app()
    uvicorn.run(app, host=host, port=port, log_level="info")


def main() -> None:
    """Entry point for the CLI."""
    parser = argparse.ArgumentParser(
        prog="wc2026",
        description="2026 FIFA World Cup Match Predictor — predict outcomes with real data and Elo ratings.",
    )
    sub = parser.add_subparsers(dest="command", help="Available commands")

    # predict
    p_predict = sub.add_parser("predict", help="Predict a single match")
    p_predict.add_argument("team_a", help="First (home) team name or FIFA code")
    p_predict.add_argument("team_b", help="Second (away) team name or FIFA code")
    p_predict.add_argument(
        "--stage", "-s",
        choices=["group", "round_of_16", "quarterfinal", "semifinal", "final"],
        default=None,
        help="Tournament stage (affects draw probability)",
    )

    # group
    p_group = sub.add_parser("group", help="Predict all matches in a group")
    p_group.add_argument("group_letter", help="Group letter (A-L)")

    # teams
    sub.add_parser("teams", help="List all 48 teams by Elo ranking")

    # simulate
    p_sim = sub.add_parser("simulate", help="Run a full tournament simulation")
    p_sim.add_argument("--seed", type=int, default=None, help="Random seed for reproducibility")

    # stats
    p_stats = sub.add_parser("stats", help="Show team history and info")
    p_stats.add_argument("team", help="Team name or FIFA code")

    # live
    p_live = sub.add_parser("live", help="Fetch and display live World Cup scores")
    p_live.add_argument(
        "--status", "-s",
        choices=["SCHEDULED", "LIVE", "FINISHED"],
        default=None,
        help="Filter by match status (default: all)",
    )
    p_live.add_argument("--group", "-g", help="Filter by group (A-L)")
    p_live.add_argument("--compact", "-c", action="store_true",
                        help="Compact output (banner only, no match details)")
    p_live.add_argument("--no-standings", action="store_true",
                        help="Skip standings display")

    # web
    p_web = sub.add_parser("web", help="Launch the web UI")
    p_web.add_argument("--host", default="127.0.0.1", help="Bind address (default: 127.0.0.1)")
    p_web.add_argument("--port", "-p", type=int, default=8080, help="Port (default: 8080)")

    args = parser.parse_args()

    if args.command == "predict":
        cmd_predict(args)
    elif args.command == "group":
        cmd_group(args)
    elif args.command == "teams":
        cmd_teams(args)
    elif args.command == "simulate":
        cmd_simulate(args)
    elif args.command == "stats":
        cmd_stats(args)
    elif args.command == "live":
        cmd_live(args)
    elif args.command == "web":
        cmd_web(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
