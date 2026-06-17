---
marp: true
theme: uncover
class:
  - lead
  - invert
paginate: true
size: 16:9
footer: "WC2026 · github.com/Wailynn351/wc2026-world-cup-predictor"
---

<!--
Pecha Kucha: 6 slides × 20s = 2 minutes
Source: slides/templates/pechakucha-6x20.md
-->

# 🏆 WC2026
## World Cup Match Predictor

![bg right:35% opacity:.3](https://images.unsplash.com/photo-1579952363873-27f3bade9f55?w=800)

**Elo-powered · Real data · Pure Python**
##### `python -m wc2026 predict "Argentina" "France"`

---

<!-- _class: default -->

# The Problem

<div style="font-size: 2.5em; margin: .3em 0;">📊 48 teams</div>
<div style="font-size: 2.5em; margin: .3em 0;">🎲 12 groups</div>
<div style="font-size: 2.5em; margin: .3em 0;">❓ 1 winner</div>

## Who wins? Can we predict it with data?

---

<!-- _class: invert -->

# The Model

<!-- _footer: "Elo formula + Gaussian draw + home advantage + knockout adjustment" -->

<div style="font-size: 1.3em; margin-top: .5em;">

$$P(A) = \frac{1}{1 + 10^{\,(R_B - R_A)\,/\,400}}$$

</div>

| Factor | Value |
|--------|-------|
| Home advantage | **+50 Elo** |
| Draw peak / floor | **30% → 5%** |
| Knockout draw | **× 0.65** |
| Confidence tiers | LOW · MEDIUM · HIGH |
| Reference data | **172 matches** (1930–2022) |

---

<!-- _class: default -->

# Architecture

<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1em; margin-top: .5em;">

<div>

```
wc2026/
├── cli.py       ▶ 5 commands
├── models.py    ▶ dataclasses
├── predictor.py ▶ Elo engine
├── data.py      ▶ JSON loader
└── display.py   ▶ terminal UI
```
</div>
<div style="text-align: left;">

#### Claude Code Extensions
```
.mcp.json         ▶ 4 tools
.claude/
├── skills/world-cup/
│   └── SKILL.md
└── agents/
    └── wc2026-analyst.md
```
</div>
</div>

## Clean layers · stdlib only · 40 tests · 16 commits

---

<!-- _class: invert -->

# ✨ In Action

<div style="font-size: 0.8em; line-height: 1.3; margin-top: .3em;">

```
┌──────────────────────────────────────────────────┐
│  Argentina vs France                             │
│  Elo: 2138 — 2115                                │
│                                                  │
│  Argentina      ███████████████████░░░░ 48.7%    │
│  Draw           ████████░░░░░░░░░░░░░░ 19.4%     │
│  France         █████████████░░░░░░░░░ 32.0%     │
│                                                  │
│  Prediction: Argentina · Confidence: LOW         │
└──────────────────────────────────────────────────┘
```

</div>

<div style="margin-top: .6em;">

#### `predict` · `group` · `teams` · `simulate` · `stats`

</div>

---

<!-- _class: lead invert -->

# Takeaways

<div style="font-size: 1.8em; line-height: 1.8;">
📈 &nbsp; <b>Elo works</b> — data beats gut feel<br>
🧱 &nbsp; <b>Layers pay off</b> — easy to test & extend<br>
🤖 &nbsp; <b>Claude Code</b> — 16 commits, zero drift<br>
</div>

<br>

### ⭐ [github.com/Wailynn351/wc2026-world-cup-predictor](https://github.com/Wailynn351/wc2026-world-cup-predictor)
