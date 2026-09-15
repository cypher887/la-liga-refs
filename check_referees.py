"""
Run every 15 min (see .github/workflows/check-referees.yml).

Only fetches gameweeks that have at least one un-notified subscription, and
skips entirely (no network calls) if there are none — so it's cheap to run
on a schedule even when nothing is pending.
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

from scraper import fetch_gameweek
from notify import send_referee_notification

ROOT = Path(__file__).parent
SUBSCRIPTIONS_FILE = ROOT / "subscriptions.json"
STATE_FILE = ROOT / "state.json"


def load_json(path: Path, default):
    if not path.exists():
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def main() -> None:
    subscriptions = load_json(SUBSCRIPTIONS_FILE, [])
    state = load_json(STATE_FILE, {})

    active = [s for s in subscriptions if not s.get("notified")]
    if not active:
        print("No active subscriptions, nothing to check.")
        return

    by_gameweek = defaultdict(list)
    for sub in active:
        by_gameweek[(sub["season"], sub["gameweek"])].append(sub)

    changed = False

    for (season, gw), subs in by_gameweek.items():
        print(f"Checking {season} gameweek {gw} ({len(subs)} subscription(s))...")
        try:
            fixtures = fetch_gameweek(gw, season)
        except Exception as e:
            print(f"  ERROR fetching gameweek {gw}: {e}", file=sys.stderr)
            continue

        for sub in subs:
            match = next(
                (
                    fx
                    for fx in fixtures
                    if sub["home"].lower() in fx.home.lower()
                    and sub["away"].lower() in fx.away.lower()
                ),
                None,
            )
            if match is None:
                print(f"  WARN: no fixture matched subscription {sub}", file=sys.stderr)
                continue

            key = match.key()
            if match.referee:
                if state.get(key) != match.referee:
                    print(f"  Referee announced: {match.home} vs {match.away} -> {match.referee}")
                    send_referee_notification(match)
                    state[key] = match.referee
                    changed = True
                sub["notified"] = True
                changed = True
            else:
                print(f"  Still pending: {match.home} vs {match.away}")

    if changed:
        save_json(SUBSCRIPTIONS_FILE, subscriptions)
        save_json(STATE_FILE, state)


if __name__ == "__main__":
    main()
