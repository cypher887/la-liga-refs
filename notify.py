import os
import sys

import requests

from scraper import Fixture


def send_referee_notification(fixture: Fixture) -> None:
    webhook_url = os.environ.get("SLACK_WEBHOOK_URL")
    if not webhook_url:
        print("SLACK_WEBHOOK_URL not set, skipping notification", file=sys.stderr)
        return

    text = (
        f"🟨 *Referee announced* — GW{fixture.gameweek}: "
        f"*{fixture.home} vs {fixture.away}*\n"
        f"{fixture.date} {fixture.time} · Referee: *{fixture.referee}*"
        + (f"\n{fixture.url}" if fixture.url else "")
    )
    resp = requests.post(webhook_url, json={"text": text}, timeout=10)
    resp.raise_for_status()
