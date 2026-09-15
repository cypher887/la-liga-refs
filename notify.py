import os
import sys

import requests

from scraper import Fixture

NTFY_SERVER = os.environ.get("NTFY_SERVER", "https://ntfy.sh")


def send_referee_notification(fixture: Fixture) -> None:
    topic = os.environ.get("NTFY_TOPIC")
    if not topic:
        print("NTFY_TOPIC not set, skipping notification", file=sys.stderr)
        return

    message = f"{fixture.date} {fixture.time}\nReferee: {fixture.referee}"

    payload = {
        "topic": topic,
        "title": f"Ref announced: {fixture.home} vs {fixture.away}",
        "message": message,
        "tags": ["yellow_square"],
        "priority": 3,
    }
    if fixture.url:
        payload["actions"] = [
            {"action": "view", "label": "Open match page", "url": fixture.url}
        ]

    # JSON body (not headers) so accented names (García, etc.) are safe.
    resp = requests.post(NTFY_SERVER, json=payload, timeout=10)
    resp.raise_for_status()
