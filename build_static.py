#!/usr/bin/env python3
"""Build a static site from the WC2026 templates for GitHub Pages.

Usage:
    python build_static.py

Outputs to docs/ directory.
"""

import json
import shutil
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from wc2026.data import load_teams, get_groups, load_historical_matches
from wc2026.predictor import predict

TEMPLATES_DIR = Path(__file__).parent / "wc2026" / "templates"
OUTPUT_DIR = Path(__file__).parent / "docs"


def build():
    """Generate all static HTML files."""
    # Clean and create output directory
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents=True)

    # Load data
    teams = load_teams()
    groups = get_groups(teams)
    teams_sorted = sorted(teams, key=lambda t: (-t.elo_rating, t.name))

    # Build template context shared by all pages
    team_dicts = [
        {"name": t.name, "code": t.fifa_code, "elo": t.elo_rating,
         "group": t.group, "confederation": t.confederation}
        for t in teams_sorted
    ]

    # Jinja2 environment
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR.resolve())),
        autoescape=select_autoescape(["html"]),
    )

    # A fake request object so nav active-state checks don't crash
    class FakeURL:
        path = "/"
    class FakeRequest:
        url = FakeURL()

    request = FakeRequest()

    # ── index.html ──────────────────────────────────────────────────
    print("  Building index.html ...")
    request.url.path = "/"
    tpl = env.get_template("index.html")
    html = tpl.render(
        request=request,
        teams=team_dicts,
        live_matches=[],
        has_api_key=False,
        static=True,
    )
    _write("index.html", html)

    # ── teams.html ──────────────────────────────────────────────────
    print("  Building teams.html ...")
    request.url.path = "/teams"
    tpl = env.get_template("teams.html")
    html = tpl.render(
        request=request,
        teams=team_dicts,
        static=True,
    )
    _write("teams.html", html)

    # ── groups.html ─────────────────────────────────────────────────
    print("  Building groups.html ...")
    request.url.path = "/groups"
    tpl = env.get_template("groups.html")

    # Generate predictions for all group matches
    group_data = {}
    for letter in sorted(groups.keys()):
        group_teams = sorted(groups[letter], key=lambda t: -t.elo_rating)
        preds = []
        for i, t1 in enumerate(group_teams):
            for t2 in group_teams[i + 1:]:
                p = predict(t1, t2, "group")
                preds.append(p)
        group_data[letter] = {
            "teams": group_teams,
            "predictions": preds,
            "standings": [],
        }

    html = tpl.render(
        request=request,
        group_data=group_data,
        static=True,
    )
    _write("groups.html", html)

    # ── predict.html ────────────────────────────────────────────────
    print("  Building predict.html ...")
    request.url.path = "/predict"
    tpl = env.get_template("predict.html")

    # Embed team data as JSON for the JS prediction engine
    teams_json = json.dumps([
        {"name": t.name, "code": t.fifa_code, "elo": t.elo_rating,
         "group": t.group, "confederation": t.confederation}
        for t in teams_sorted
    ])

    html = tpl.render(
        request=request,
        teams=team_dicts,
        home="",
        away="",
        stage="",
        prediction=None,
        error=None,
        static=True,
        teams_json=teams_json,
    )
    _write("predict.html", html)

    # ── Done ────────────────────────────────────────────────────────
    print(f"\n✓ Static site built in {OUTPUT_DIR}/")
    print(f"  Files: {', '.join(f.name for f in sorted(OUTPUT_DIR.iterdir()))}")


def _write(filename: str, content: str) -> None:
    """Write a file to the output directory."""
    (OUTPUT_DIR / filename).write_text(content, encoding="utf-8")


if __name__ == "__main__":
    build()
