#!/usr/bin/env python3
# PR‑tracker: counts Copilot / Codex PRs and saves data to CSV.
# Tracks merged PRs (not just approved ones)
# deps: requests

import csv
import datetime as dt
from pathlib import Path
import requests

# Basic headers for GitHub public API
HEADERS = {
    "Accept": "application/vnd.github+json",
    "User-Agent": "PR-Watcher"
}

# Search queries - tracking merged PRs
Q = {
    "is:pr+head:copilot/":              "copilot_total",
    "is:pr+head:copilot/+is:merged":    "copilot_merged",
    "is:pr+head:codex/":                "codex_total",
    "is:pr+head:codex/+is:merged":      "codex_merged",
    'committer:"devin-ai-integration[bot]"': "devin_commits",
    'committer:"google-labs-jules[bot]"': "jules_commits",
}

def collect_data():
    # Get data from GitHub API
    cnt = {}
    for query, key in Q.items():
        if "commits" in key:
            # For commit searches, use the /search/commits endpoint
            api_url = f"https://api.github.com/search/commits?q={query}"
            # The 'Accept' header for commit search needs to be 'application/vnd.github.cloak-preview+json'
            # according to some docs, but testing shows 'application/vnd.github+json' works for total_count.
            # Let's stick to the existing HEADERS for now unless issues arise.
        else:
            # For PR searches (issues), use the /search/issues endpoint
            api_url = f"https://api.github.com/search/issues?q={query}"
        
        r = requests.get(api_url, headers=HEADERS, timeout=30)
        r.raise_for_status()
        data = r.json()
        cnt[key] = data["total_count"]

        if key == "devin_commits":
            print(f"Devin commits found: {cnt[key]}")
        if key == "jules_commits":
            print(f"Jules commits found: {cnt[key]}")

    # Save data to CSV
    timestamp = dt.datetime.now(dt.timezone.utc).strftime("%Y‑%m‑%d %H:%M:%S")
    row = [timestamp, cnt["copilot_total"], cnt["copilot_merged"],
           cnt["codex_total"], cnt["codex_merged"], cnt["devin_commits"], cnt["jules_commits"]]

    csv_file = Path("data.csv")
    is_new_file = not csv_file.exists()
    with csv_file.open("a", newline="") as f:
        writer = csv.writer(f)
        if is_new_file:
            writer.writerow(["timestamp", "copilot_total", "copilot_merged",
                            "codex_total", "codex_merged", "devin_commits", "jules_commits"])
        writer.writerow(row)

    return csv_file

if __name__ == "__main__":
    collect_data()
    print("Data collection complete. To generate chart, run generate_chart.py")
