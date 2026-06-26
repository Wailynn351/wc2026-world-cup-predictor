
<!--
Pecha Kucha: 6 slides × 20s = 2 minutes
Source: slides/templates/pechakucha-6x20.md
-->

# 🏆 WC2026 by Wailynn
## World Cup Match Predictor

![bg right:35% opacity:.3](https://images.unsplash.com/photo-1579952363873-27f3bade9f55?w=800)

**Elo-powered · Real data · Pure Python**
##### python -m wc2026 predict

---

<!-- _class: default -->

# The Problem

<div style="font-size: 2.5em; margin: .3em 0;">📊 48 teams</div>
<div style="font-size: 2.5em; margin: .3em 0;">🎲 12 groups</div>
<div style="font-size: 2.5em; margin: .3em 0;">❓ 1 winner</div>

## Who wins? Can we predict it with data?

---

<!-- _class: invert -->

# What i build - The Model

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

# Architecture by HoW I bulid

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


---
<br>

### ⭐ [github.com/Wailynn351/wc2026-world-cup-predictor](https://github.com/Wailynn351/wc2026-world-cup-predictor)
