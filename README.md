# K5Bearing

Automated X account for **Kastle Five Systems**. Posts useful, signal-grade
alerts about space weather, geomagnetic activity, compass accuracy, severe
weather, and field readiness — sourced entirely from free US government feeds.

## What it posts

| Signal | Source | Trigger |
| --- | --- | --- |
| Geomagnetic storm + **compass accuracy** advisory | NOAA SWPC planetary K-index | Kp ≥ threshold (default 5 = G1) |
| **Aurora visibility** watch (global viewline) | NOAA SWPC Kp index | Kp ≥ threshold (default 5) |
| **Solar flares** (M/X-class) | NOAA SWPC GOES X-ray | New flare ≥ threshold class |
| Solar storms / radio blackouts / radiation storms | NOAA SWPC alerts feed | New matching alert |
| **Marine / sea / ocean** (storm surge, hurricane-force wind, gale, hazardous seas, special marine, freezing spray, high surf, rip current, beach hazards, coastal/lakeshore flood, tsunami) — **priority focus**; small-craft advisories collapse into one low-priority roundup so they don't flood | US National Weather Service | New active warning |
| Severe weather — **US** land (tornado, hurricane, severe t-storm, flood, fire, winter, extreme heat/cold, high wind, dust, avalanche…) | US National Weather Service | New active warning |
| Severe weather — **Europe** (~38 countries) | MeteoAlarm (EUMETNET) | New orange/red warning |
| **Global multi-hazard** — tropical cyclones (all basins), floods, earthquakes, volcanoes, wildfires | GDACS (UN OCHA / EC JRC) | New orange/red event |
| **Significant earthquakes** (worldwide) | USGS | New quake ≥ magnitude threshold |
| **Outdoor safety** — extreme UV index | Open-Meteo (watchlist) | UV threshold crossed at a watched city |

Every post is written as a timestamped advisory in plain, flowing prose
(National Hurricane Center style), e.g. `2:34 am EDT: A tornado warning is in
effect for ...`. The timestamp is in the **local time zone of the alert's
location** (resolved from coordinates for US/global alerts and from country for
Europe); global space-weather signals stay in UTC. The source agency is not
named in-tweet — K5Bearing is the voice. No emoji, no sign-offs.

Each alert is phrased from several vetted variants (openers + per-hazard action
lines) chosen deterministically from the alert's id, so the feed reads freshly
written rather than copy-pasted while a given alert always renders the same way.

**Coverage is worldwide.** Space-weather signals are inherently global — the Kp
index is a *planetary* index and SWPC alerts are global. Severe-weather
warnings come from the NWS (US) and MeteoAlarm (Europe), and **GDACS** adds the
rest of the planet — Asia, Africa, Latin America, Oceania — for tropical
cyclones, floods, quakes, volcanoes, and wildfires at Orange/Red alert levels.

The compass advisory is derived from the Kp index — geomagnetic storms
transiently shift magnetic declination, which is what degrades magnetic-compass
accuracy (worst at high latitudes). That's the "Bearing" in K5Bearing.

All data sources are public, free, and keyless. The only credential you need is
for posting to X.

## How it works

`python -m src.main` runs once: it gathers candidate signals, ranks them by
severity, skips anything already posted (tracked in `state.json`), and posts up
to the per-run cap. [GitHub Actions](.github/workflows/post.yml) runs it hourly
and commits `state.json` back so dedup survives between runs.

```
src/
  main.py        orchestrator
  config.py      load config.yaml + env credentials
  tz.py          resolve each alert's local timezone (timezonefinder)
  state.py       dedup + daily-budget tracking (state.json)
  formatter.py   timestamp + tweet rendering
  poster.py      X v2 client (tweepy), with DRY_RUN
  sources/
    swpc.py        solar + geomagnetic + compass (global)
    aurora.py      aurora-visibility viewline from Kp (global)
    nws.py         severe weather — US (incl. marine, winter, heat)
    meteoalarm.py  severe weather — Europe
    gdacs.py       global multi-hazard — rest of world
    usgs.py        significant earthquakes — worldwide
    outdoor.py     extreme UV index (Open-Meteo watchlist)
config.yaml      thresholds, limits, schedule — tune this
```

## Setup

### 1. X API credentials

You already have an app in the X developer portal. Now:

1. In the app settings, set **User authentication** to **Read and Write**
   (Settings → User authentication settings). Posting fails silently-ish on
   read-only tokens.
2. Under **Keys and tokens**, copy:
   - **API Key** and **API Key Secret** (consumer keys)
   - **Access Token** and **Access Token Secret** — regenerate these *after*
     setting Read+Write so they carry write permission.
3. Put them in `.env` (copy `.env.example`) for local testing.

> **Cost note:** As of Feb 2026 the free tier is closed to new developers. New
> apps are on **pay-per-use: ~$0.01 per post** (you may have a one-time $10
> credit). The defaults in `config.yaml` cap posting at 8/day ≈ $2.40/month.
> If you're on a legacy free tier instead, the 1,500-posts/month limit applies.

### 2. Test locally (no posting)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
DRY_RUN=1 python -m src.main
```

This prints the tweets it *would* send. Tune thresholds in `config.yaml`.

### 3. Post for real, on a schedule (GitHub Actions)

1. Push this repo to GitHub.
2. Repo → Settings → Secrets and variables → Actions → add four secrets:
   `X_API_KEY`, `X_API_SECRET`, `X_ACCESS_TOKEN`, `X_ACCESS_TOKEN_SECRET`.
3. The workflow runs hourly automatically. To test it once, use
   **Actions → K5Bearing signals → Run workflow** (set *Run without posting* =
   true for a dry run first).

That's it — no server to manage.

## Tuning

Everything tunable lives in [`config.yaml`](config.yaml):

- `limits.max_posts_per_run` / `max_posts_per_day` — budget control.
- `geomagnetic.kp_alert_threshold` — lower to 4 for more posts, raise to 6/7
  for only major storms.
- `weather.events` — which NWS (US) event types qualify. Add e.g.
  `"Severe Thunderstorm Warning"` for more volume.
- `weather.area` — set a state code (e.g. `"FL"`) to go regional instead of
  nationwide.
- `weather_eu.countries` — which European countries to watch (MeteoAlarm feed
  slugs, e.g. `france`, `united-kingdom`, `czechia`). Add or remove freely.
- `weather_eu.min_severity` — `Severe` (orange, default) keeps volume sane;
  `Extreme` = red-only; `Moderate` includes yellow (high volume).
- `aurora.kp_threshold` — Kp at/above which the aurora watch fires (default 5).
- `global_hazards.event_types` — which GDACS hazards qualify (`TC` cyclone,
  `FL` flood, `EQ` quake, `VO` volcano, `WF` wildfire, `TS` tsunami).
- `global_hazards.min_alert` — `Orange` (default) or `Red` for major-only.

> **Volume note:** adding severe-thunderstorm and flood warnings pulls in a lot
> of active US alerts. The severity ranking + `max_posts_per_day` cap mean only
> the most serious get posted, but raise the cap (and your budget) if you want
> more through. At 12/day that's ~$3.60/month on pay-per-use.

## Disclaimer

K5Bearing relays public NOAA/NWS data and automated advisories. It is **not**
an official source. Always confirm with official channels before making
safety-critical navigation or weather decisions.
