#!/usr/bin/env python3
"""Accumulate real GitHub Traffic API unique-visitor counts into a running total.

The Traffic API only exposes a rolling 14-day window, so this script keeps
its own ledger of which days have already been counted (.github/view-state.json)
and only adds days it hasn't seen before.
"""
import json
import os
import re
import subprocess

REPO = "byteshiftlabs/byteshiftlabs"
STATE_FILE = os.path.join(os.path.dirname(__file__), "..", "view-state.json")
README_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "README.md")


def gh_api(path):
    result = subprocess.run(
        ["gh", "api", path],
        capture_output=True, text=True, check=True,
    )
    return json.loads(result.stdout)


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"total_uniques": 0, "counted_days": {}}


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2, sort_keys=True)
        f.write("\n")


def main():
    state = load_state()
    data = gh_api(f"repos/{REPO}/traffic/views")

    for day in data.get("views", []):
        date = day["timestamp"][:10]
        uniques = day["uniques"]
        if date not in state["counted_days"]:
            state["total_uniques"] += uniques
            state["counted_days"][date] = uniques

    save_state(state)

    total = state["total_uniques"]

    with open(README_FILE) as f:
        readme = f.read()

    badge_url = (
        f"https://img.shields.io/badge/Profile_Views-{total}-000000"
        "?style=for-the-badge"
    )
    block = (
        "<!-- PROFILE_VIEWS:START -->\n"
        f'  <img src="{badge_url}" alt="Profile views (unique visitors, via GitHub Traffic API)" />\n'
        "  <!-- PROFILE_VIEWS:END -->"
    )
    new_readme = re.sub(
        r"<!-- PROFILE_VIEWS:START -->.*<!-- PROFILE_VIEWS:END -->",
        block,
        readme,
        flags=re.DOTALL,
    )

    with open(README_FILE, "w") as f:
        f.write(new_readme)

    print(f"Total unique views: {total}")


if __name__ == "__main__":
    main()
