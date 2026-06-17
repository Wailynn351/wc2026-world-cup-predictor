# Plan: 2026 World Cup Match Predictor

## Overview
A Python CLI tool that predicts 2026 FIFA World Cup match winners using historical reference data and an Elo-based prediction model. Zero dependencies beyond Python stdlib.

## Architecture
```
world-cup-2026/
├── wc2026/
│   ├── __init__.py
│   ├── cli.py          # argparse CLI — predict, teams, matches, simulate
│   ├── models.py       # Team, Match dataclasses
│   ├── data.py         # Load reference data (teams, historical matches, Elo ratings)
│   ├── predictor.py    # Elo win-probability engine
│   └── display.py      # Pretty-printed tables and match cards
├── data/
│   ├── teams.json           # 48 teams (2026 expanded format)
│   ├── historical_matches.json  # ~900 historical World Cup matches
│   └── elo_ratings.json     # Current Elo ratings for all teams
├── tests/
│   ├── __init__.py
│   ├── test_models.py
│   ├── test_predictor.py
│   └── test_data.py
└── README.md
```

## Data Model
- **Team**: name, fifa_code, confederation, elo_rating (float), group
- **Match**: home_team, away_team, home_score, away_score, date, tournament_year, stage
- **Prediction**: home_team, away_team, home_win_pct, draw_pct, away_win_pct, predicted_winner, confidence

## Prediction Engine
- **Elo model**: Win probability = 1 / (1 + 10^((ratingB - ratingA) / 400))
- **Draw factor**: Poisson-derived draw probability based on expected goals
- **Adjustments**: Home advantage, tournament knockout-stage modifier, recent form

## Reference Data (included in repo)
- Real historical World Cup match results (1930–2022)
- Current Elo ratings sourced from eloratings.net methodology
- 2026 teams and group assignments (where confirmed)

## CLI Commands
- `wc2026 predict <team_a> <team_b>` — predict single match outcome
- `wc2026 group <group_letter>` — predict all group-stage matches for a group
- `wc2026 teams` — list all teams with ratings
- `wc2026 simulate` — run a full tournament simulation
- `wc2026 stats <team>` — show team history and form

## Implementation Steps (small, frequent commits)
1. Project scaffolding — package structure, README skeleton
2. Data files — teams.json with real 2026 teams
3. Historical match data — populate World Cup results
4. Elo ratings data — current Elo ratings for all teams
5. Models layer — Team and Match dataclasses
6. Data loader — read/validate JSON reference data
7. Prediction engine — Elo win-probability calculation
8. Display layer — formatted tables and match cards
9. CLI layer — argparse with all subcommands
10. Tests — unit tests for models, predictor, data
11. README polish — usage, examples, methodology docs

## Design Decisions
- **Zero dependencies** — pure Python stdlib
- **JSON data files** — human-readable, easy to update as teams qualify
- **Real data** — historical matches and current Elo ratings, not synthetic
- **Separation of concerns** — data/prediction/display all independent layers
- **Testable** — every layer independently unit-testable
