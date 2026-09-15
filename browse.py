"""
Browse fixtures for a gameweek and subscribe to referee-announcement alerts.

Usage:
    python browse.py 6
    python browse.py 6 --subscribe 3        # subscribe to fixture #3 shown
    python browse.py 6 --season 2025-26
"""
import argparse
import json
from pathlib import Path

from scraper import fetch_gameweek

ROOT = Path(__file__).parent
SUBSCRIPTIONS_FILE = ROOT / "subscriptions.json"


def load_subscriptions() -> list:
    if not SUBSCRIPTIONS_FILE.exists():
        return []
    with open(SUBSCRIPTIONS_FILE, encoding="utf-8") as f:
        return json.load(f)


def save_subscriptions(subs: list) -> None:
    with open(SUBSCRIPTIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(subs, f, indent=2, ensure_ascii=False)
        f.write("\n")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("gameweek", type=int)
    ap.add_argument("--season", default="2026-27")
    ap.add_argument("--subscribe", type=int, metavar="N", help="subscribe to fixture #N")
    args = ap.parse_args()

    fixtures = fetch_gameweek(args.gameweek, args.season)
    if not fixtures:
        print("No fixtures found (page layout may have changed — try scraper.py --debug).")
        return

    for i, fx in enumerate(fixtures, start=1):
        ref = fx.referee or "TBD"
        score = f" {fx.score} " if fx.score else " vs "
        print(f"[{i}] {fx.date} {fx.time}  {fx.home}{score}{fx.away}  — Ref: {ref}")

    if args.subscribe:
        idx = args.subscribe - 1
        if not (0 <= idx < len(fixtures)):
            print(f"No fixture #{args.subscribe}")
            return
        fx = fixtures[idx]
        subs = load_subscriptions()
        exists = any(
            s["season"] == fx.season and s["gameweek"] == fx.gameweek
            and s["home"] == fx.home and s["away"] == fx.away
            for s in subs
        )
        if exists:
            print("Already subscribed.")
            return
        subs.append({
            "season": fx.season,
            "gameweek": fx.gameweek,
            "home": fx.home,
            "away": fx.away,
            "notified": bool(fx.referee),
        })
        save_subscriptions(subs)
        print(f"Subscribed: {fx.home} vs {fx.away} (GW{fx.gameweek})")
        if fx.referee:
            print(f"Note: referee already assigned ({fx.referee}) — no notification will fire for this one.")


if __name__ == "__main__":
    main()
