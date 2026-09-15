"""
Writes docs/data/<season>-gw<N>.json for every gameweek in watched_gameweeks.json,
plus any gameweek currently referenced in subscriptions.json (so a subscribed
match's data is always kept fresh even if someone forgot to "track" it).

GitHub Pages serves docs/ as a static site, so the browser UI just fetches
these JSON files directly — no API/token needed for reading fixtures.
"""
import json
from dataclasses import asdict
from pathlib import Path

from scraper import fetch_gameweek

ROOT = Path(__file__).parent
WATCHED_FILE = ROOT / "watched_gameweeks.json"
SUBSCRIPTIONS_FILE = ROOT / "subscriptions.json"
DATA_DIR = ROOT / "docs" / "data"


def load_json(path: Path, default):
    if not path.exists():
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def main() -> None:
    watched = load_json(WATCHED_FILE, [])
    subs = load_json(SUBSCRIPTIONS_FILE, [])

    targets = {(w["season"], w["gameweek"]) for w in watched}
    targets |= {(s["season"], s["gameweek"]) for s in subs}

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    for season, gw in sorted(targets):
        print(f"Fetching {season} gameweek {gw}...")
        try:
            fixtures = fetch_gameweek(gw, season)
        except Exception as e:
            print(f"  ERROR: {e}")
            continue
        out_path = DATA_DIR / f"{season}-gw{gw}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump([asdict(fx) for fx in fixtures], f, indent=2, ensure_ascii=False)
        print(f"  wrote {out_path} ({len(fixtures)} fixtures)")


if __name__ == "__main__":
    main()
