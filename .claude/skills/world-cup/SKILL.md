---
name: world-cup
description: |-
  2026 FIFA World Cup analysis — predict matches, simulate tournaments,
  rank teams by Elo, explore historical results. Uses the WC2026 predictor
  (Elo-based model, 172 historical matches, 48 qualified teams).
---

# World Cup 2026 Prediction Skill

Use this skill whenever the user wants to analyze, predict, or discuss
the 2026 FIFA World Cup — match predictions, tournament simulations,
team rankings, group analysis, historical comparisons, or methodology
questions about the Elo prediction model.

## Tools at Your Disposal

### 1. The Project CLI (`python -m wc2026`)

| Command | What It Does |
|---------|--------------|
| `predict "Team A" "Team B" [--stage X]` | Head-to-head prediction with Elo win/draw/win percentages |
| `group <letter>` | Predict all 6 matches in a group (A–L) |
| `teams` | Ranked table of all 48 teams by Elo |
| `simulate [--seed N]` | Full tournament: group stage → R32 → R16 → QF → SF → Final |
| `stats "Team"` | Team history: Elo, all-time W-D-L, tournament appearances |

### 2. The MCP Server

When the MCP is connected, these tools are available:
- `predict_match` — same as CLI predict, with structured output
- `list_all_teams` — all 48 teams with Elo, codes, groups
- `get_team_info` — deep dive on one team
- `get_group` — group standings + all 6 match predictions

### 3. Data Files (you can read directly)

- `data/teams.json` — 48 teams, FIFA codes, confederations, group assignments
- `data/elo_ratings.json` — current Elo ratings
- `data/historical_matches.json` — 172 real World Cup matches (1930–2022)

## How to Analyze

### Match Prediction Workflow
1. Run `python -m wc2026 predict "A" "B"` for a quick prediction
2. Check the confidence level (HIGH/MEDIUM/LOW)
3. If the match is close, mention the draw probability
4. Add context: compare Elo ratings, historical head-to-heads from historical_matches.json

### Tournament Simulation Workflow
1. Run `python -m wc2026 simulate` with a seed for reproducibility
2. Note interesting upsets from the group stage
3. Trace the path of favorites vs dark horses
4. Run multiple seeds to see variance (mention this to the user)

### Group Analysis Workflow
1. Run `python -m wc2026 group <letter>` for full predictions
2. Rank teams by Elo within the group
3. Identify "group of death" (tightest Elo cluster) vs "group of life" (widest spread)

## Methodology Reference

### Elo Formula
$$\text{Win Probability} = \frac{1}{1 + 10^{(R_B - R_A) / 400}}$$

### Draw Model
- Peaks at ~30% when ratings are equal (Gaussian decay, σ=200)
- Drops to ~5% floor for large gaps
- Reduced 35% in knockout stages (extra time + penalties)

### Home Advantage
- +50 Elo points for the first-named team

### Confidence Tiers
| Gap | Tier |
|-----|------|
| <40 Elo | LOW — too close to call |
| 40–119 | MEDIUM — moderate edge |
| ≥120 | HIGH — strong favorite |

### Key Facts to Mention
- 48-team format (expanded from 32): 12 groups of 4
- Top 2 from each group + 8 best 3rd-placed teams → Round of 32
- Argentina (Elo 2138) are the #1 rated team; defending champions
- France (Elo 2115), Brazil (Elo 2102), Spain (Elo 2098) round out the top tier
- The model is built on 172 historical World Cup matches from every tournament (1930–2022)

## Tone

- Data-driven but not overconfident — football is unpredictable
- Acknowledge uncertainty: "This is a close matchup, the model slightly favors..."
- When a prediction is high-confidence, say so, but remind users that upsets happen
- Refer to the 2022 Saudi Arabia 2-1 Argentina as a reminder that Elo isn't everything
