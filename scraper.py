"""
Scrapes LALIGA results pages for fixtures + referee assignments.

Referee text is only present on the page once it's been assigned (usually a
few days before kickoff). Until then the site shows "-".

Parsing strategy: rather than depend on brittle CSS class names, we walk the
page's visible text in document order and split it into per-fixture chunks
using the "Watch summary" marker that precedes every match row, then align
those chunks with the ordered list of match-detail links on the page (one
per fixture, deduplicated). Each chunk is parsed with a small state machine.

If LALIGA changes the page layout, run `python scraper.py <gameweek> --debug`
to dump the raw chunks and adjust `_parse_chunk` accordingly.
"""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass, asdict
from typing import Optional

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.laliga.com/en-GB/laliga-easports/results/{season}/gameweek-{gw}"
USER_AGENT = (
    "Mozilla/5.0 (compatible; RefereeWatch/1.0; "
    "+https://github.com/) referee-availability-checker"
)

DATE_RE = re.compile(r"^(MON|TUE|WED|THU|FRI|SAT|SUN)\s+\d{2}\.\d{2}\.\d{4}$")
TIME_RE = re.compile(r"^\d{2}:\d{2}$")
SCORE_LINE_RE = re.compile(r"^\d+\s*-\s*\d+$")
LONE_DASH_RE = re.compile(r"^-$")
DIGIT_RE = re.compile(r"^\d+$")
MATCH_HREF_RE = re.compile(
    r"/en-GB/match/temporada-\d{4}-\d{4}-laliga-ea-sports-(?P<slug>.+)-(?P<gw>\d+)$"
)
NOISE_LINES = {"Watch summary", "Watch Match", "VS"}


@dataclass
class Fixture:
    season: str
    gameweek: int
    date: Optional[str]
    time: Optional[str]
    home: str
    away: str
    score: Optional[str]
    referee: Optional[str]
    url: Optional[str]

    def key(self) -> str:
        return f"{self.season}:{self.gameweek}:{self.home}:{self.away}"


def fetch_gameweek_html(gameweek: int, season: str = "2026-27") -> str:
    url = BASE_URL.format(season=season, gw=gameweek)
    resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=20)
    resp.raise_for_status()
    return resp.text


def _clean_lines(text: str) -> list[str]:
    lines = [l.strip() for l in text.splitlines()]
    return [l for l in lines if l]


def _match_hrefs_in_order(soup: BeautifulSoup) -> list[str]:
    hrefs = []
    for a in soup.find_all("a", href=True):
        if MATCH_HREF_RE.search(a["href"]):
            href = a["href"]
            if not hrefs or hrefs[-1] != href:
                hrefs.append(href)
    return hrefs


def _split_into_chunks(all_lines: list[str]) -> list[list[str]]:
    chunks: list[list[str]] = []
    current: Optional[list[str]] = None
    for line in all_lines:
        if line == "Watch summary":
            if current is not None:
                chunks.append(current)
            current = []
            continue
        if current is not None:
            current.append(line)
    if current is not None:
        chunks.append(current)
    # Each chunk currently runs up to (and slightly past) the next
    # "Watch summary"-free "Watch Match" marker; trim anything after it.
    trimmed = []
    for chunk in chunks:
        if "Watch Match" in chunk:
            chunk = chunk[: chunk.index("Watch Match")]
        trimmed.append(chunk)
    return trimmed


def _parse_chunk(lines: list[str], season: str, gameweek: int, url: Optional[str]) -> Optional[Fixture]:
    date = None
    time_ = None
    content = []
    for line in lines:
        if line in NOISE_LINES and line != "VS":
            continue
        if date is None and DATE_RE.match(line):
            date = line
            continue
        if time_ is None and TIME_RE.match(line):
            time_ = line
            continue
        content.append(line)

    if not content:
        return None

    home = away = None
    score = None
    rest_start = None

    if "VS" in content:
        idx = content.index("VS")
        home, away = content[0], content[idx + 1]
        rest_start = idx + 2
    else:
        # Look for a standalone score line, or a lone "-" flanked by digits.
        for i, line in enumerate(content):
            if SCORE_LINE_RE.match(line):
                home, away = content[0], content[i + 1]
                score = line
                rest_start = i + 2
                break
            if LONE_DASH_RE.match(line) and 0 < i < len(content) - 1:
                if DIGIT_RE.match(content[i - 1]) and DIGIT_RE.match(content[i + 1]):
                    home, away = content[0], content[i + 2]
                    score = f"{content[i - 1]}-{content[i + 1]}"
                    rest_start = i + 3
                    break

    if home is None:
        # Fallback: postponed/TBD fixtures with no score/VS marker at all.
        if len(content) >= 2:
            home, away = content[0], content[1]
            rest_start = 2
        else:
            return None

    tail = content[rest_start:] if rest_start is not None else []
    referee = tail[0] if len(tail) >= 1 and tail[0] != "-" else None
    # tail[1], if present, is the broadcaster column — not currently used.

    return Fixture(
        season=season,
        gameweek=gameweek,
        date=date,
        time=time_,
        home=home,
        away=away,
        score=score,
        referee=referee,
        url=f"https://www.laliga.com{url}" if url else None,
    )


def parse_fixtures(html: str, season: str, gameweek: int, debug: bool = False) -> list[Fixture]:
    soup = BeautifulSoup(html, "html.parser")
    body_text = soup.get_text("\n")
    all_lines = _clean_lines(body_text)
    chunks = _split_into_chunks(all_lines)
    hrefs = _match_hrefs_in_order(soup)

    if debug:
        print(f"[debug] {len(chunks)} chunk(s), {len(hrefs)} match link(s)", file=sys.stderr)
        for i, c in enumerate(chunks):
            href = hrefs[i] if i < len(hrefs) else None
            print(f"--- chunk {i} (href={href}) ---", file=sys.stderr)
            for l in c:
                print(f"  {l!r}", file=sys.stderr)

    fixtures = []
    for i, chunk in enumerate(chunks):
        href = hrefs[i] if i < len(hrefs) else None
        fx = _parse_chunk(chunk, season=season, gameweek=gameweek, url=href)
        if fx:
            fixtures.append(fx)
    return fixtures


def fetch_gameweek(gameweek: int, season: str = "2026-27", debug: bool = False) -> list[Fixture]:
    html = fetch_gameweek_html(gameweek, season)
    return parse_fixtures(html, season=season, gameweek=gameweek, debug=debug)


if __name__ == "__main__":
    import argparse
    import json

    ap = argparse.ArgumentParser(description="Fetch and parse a LALIGA gameweek page")
    ap.add_argument("gameweek", type=int)
    ap.add_argument("--season", default="2026-27")
    ap.add_argument("--debug", action="store_true")
    args = ap.parse_args()

    fixtures = fetch_gameweek(args.gameweek, args.season, debug=args.debug)
    print(json.dumps([asdict(f) for f in fixtures], indent=2, ensure_ascii=False))
