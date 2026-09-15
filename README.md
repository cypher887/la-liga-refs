# LALIGA referee watch

Browse LALIGA fixtures by gameweek in a web page, click to subscribe, and get
a Slack notification the moment a referee is assigned to a match you're
watching. No local install needed to use it day-to-day — a browser is enough.

## Setup (one-time, ~10 minutes)

1. **Push this repo to GitHub.**

2. **Turn on GitHub Pages**
   Repo → Settings → Pages → Source: "Deploy from a branch" → Branch: `main`,
   folder: `/docs` → Save. Your page will be live at
   `https://<you>.github.io/<repo>/` within a minute or two.

3. **Create a Slack Incoming Webhook**
   [api.slack.com/messaging/webhooks](https://api.slack.com/messaging/webhooks) →
   create one for the channel you want alerts in → copy the URL.

4. **Add repo secret**
   Repo → Settings → Secrets and variables → Actions → New repository secret
   → name `SLACK_WEBHOOK_URL` → paste the webhook URL.

5. **Create a GitHub token for the web page**
   GitHub → Settings → Developer settings → Personal access tokens →
   Fine-grained tokens → New token → restrict "Repository access" to this
   one repo → under Permissions, set **Contents: Read and write** (nothing
   else needed) → Generate.

6. **Open your page**, paste in the repo owner, repo name, and that token
   under Settings (top right) → Save. This is stored only in your browser's
   local storage — it isn't sent anywhere except GitHub's API.

That's it — no Python, no `pip install`, nothing on your machine.

## Using it

- **Browse**: pick a season/gameweek, click Load. If it's not tracked yet,
  click "Start tracking" — it'll show up within ~15 minutes, once the
  scheduled job has fetched it.
- **Subscribe**: click Subscribe on any fixture without a referee yet.
- **Get notified**: within 15 minutes of the referee appearing on laliga.com,
  you'll get a Slack message. The fixture will also show as "Notified" in
  your subscriptions list.
- **Unsubscribe** any time from the subscriptions list.

## How it fits together

- `docs/index.html` — the web page (static, hosted by GitHub Pages). Reads
  fixture data directly (no token needed) and reads/writes
  `subscriptions.json` / `watched_gameweeks.json` via the GitHub API using
  your token, so clicking Subscribe is really just committing a small JSON
  edit to the repo.
- The scheduled workflow (`.github/workflows/check-referees.yml`) runs every
  15 minutes: `dump_fixtures.py` refreshes `docs/data/*.json` for every
  tracked/subscribed gameweek (what the page reads), then
  `check_referees.py` checks subscriptions for newly-announced referees and
  posts to Slack.
- Nothing runs on your machine. The only things that need to exist are the
  GitHub repo (with Pages + Actions enabled) and your browser.

## If LALIGA changes their page layout

The scraper (`scraper.py`) works off visible text order rather than CSS
classes, but a redesign could still break it. To debug, run the Action
manually (Actions tab → "Check referee assignments" → Run workflow) and
check its logs, or, if you do have Python available somewhere,
`python scraper.py 6 --debug` dumps the raw per-fixture chunks it extracted.

## Files

| File | Purpose |
|---|---|
| `docs/index.html` | The browsable, clickable web UI (GitHub Pages) |
| `scraper.py` | Fetches + parses a gameweek page into fixture data |
| `dump_fixtures.py` | Writes `docs/data/*.json` for tracked/subscribed gameweeks |
| `check_referees.py` | Checks subscriptions, notifies Slack, updates state |
| `notify.py` | Posts a Slack message via webhook |
| `browse.py` | Optional CLI equivalent of the web UI, if you'd rather run it locally |
| `subscriptions.json` | Your watch list (edited by the web UI) |
| `watched_gameweeks.json` | Gameweeks kept fresh for browsing (edited by the web UI) |
| `state.json` | Last-seen referee per subscribed match (avoids duplicate alerts) |
