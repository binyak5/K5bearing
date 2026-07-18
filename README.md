# K5Bearing

Automated X account for **Kastle Five Systems**. Posts signal-grade alerts about
**Netherlands** severe weather, space weather, compass accuracy, tides, and the
daily sun almanac — sourced entirely from free, keyless feeds.

> **Scope: the Netherlands.** The account covers nationwide Dutch severe weather
> plus a Rotterdam forecast (home city), a national almanac, NL tides, and global
> space weather. Other
> worldwide sources (US NWS, Gulf, marine, earthquakes, GDACS, NGA, red tide,
> outdoor) are **disabled** but kept in the repo, with wording preserved in
> [`WORDING.md`](WORDING.md) and `src/sources/wording.py` — they can be switched
> back on in `config.yaml`.

## What it posts

| Signal | Source | Trigger |
| --- | --- | --- |
| **NL severe weather** — nationwide warnings naming the affected regions | MeteoAlarm (EUMETNET) | New orange/red warning |
| **Rotterdam forecast** — twice-daily outlook (the account's home city) | Open-Meteo | Scheduled window (local time) |
| **Almanac** — sunrise/sunset true bearings, solar noon, daylight ledger | Open-Meteo + solar geometry | Around the sun events |
| **Tides** — next high water at NL coastal stations | Rijkswaterstaat WaterWebservices | ~90 min before high water |
| Geomagnetic storm + **compass accuracy** advisory | NOAA SWPC planetary K-index | Kp ≥ threshold (default 5 = G1) |
| **Solar flares** (M/X) / radio blackouts / radiation storms / solar wind | NOAA SWPC feeds | New matching alert |

The NL severe-weather alerts reuse the preserved US wording library, so they read
like the account's established voice (see [`WORDING.md`](WORDING.md)).

Every post is written as a timestamped advisory in plain, flowing prose, e.g.
`18:00 CEST` then `An orange wind warning is active for ...`. Timestamps are in
local time (CEST); global space-weather signals stay in UTC. The source agency is
not named in-tweet — K5Bearing is the voice. No emoji, no sign-offs.

Each alert is phrased from several vetted variants (openers + per-hazard action
lines) chosen deterministically from the alert's id, so the feed reads freshly
written rather than copy-pasted while a given alert always renders the same way.

The compass advisory is derived from the Kp index — geomagnetic storms
transiently shift magnetic declination, which degrades magnetic-compass accuracy
(worst at high latitudes). That's the "Bearing" in K5Bearing.

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
    swpc.py        solar + geomagnetic + compass (global)      [active]
    meteoalarm.py  NL severe weather — MeteoAlarm (national)    [active]
    citywx.py      twice-daily Rotterdam forecast (Open-Meteo)  [active]
    almanac.py     sun bearings / solar noon / daylight         [active]
    tides.py       NL high-water tides (Rijkswaterstaat)        [active]
    wording.py     shared alert wording library (reused above)
    rotterdam.py   Rotterdam-derived severe weather             [disabled]
    aurora.py      aurora-visibility viewline from Kp           [disabled]
    gdacs.py       global multi-hazard                          [disabled]
    nga.py         maritime security / military nav warnings    [disabled]
    marine.py      high-seas warnings — global sea areas        [disabled]
    usgs.py        significant earthquakes                       [disabled]
    outdoor.py     extreme UV / dust / lightning watch          [disabled]
    hab.py         harmful algal bloom / red tide               [disabled]
config.yaml      thresholds, limits, schedule — tune this
```

The US (`nws.py`) and Gulf (`gulf.py`) sources were removed in the Rotterdam
pivot; their wording lives on in `wording.py` and `WORDING.md`, and the code is
in git history. `meteoalarm.py` was restored to power nationwide NL warnings.

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

> **Cost note:** pay-per-use is ~$0.015 per post. The defaults cap posting at
> **20/day** with a hard **640-posts/month ceiling ≈ $9.60/month**, sitting just
> under a **$10** X billing spend cap (`limits.max_posts_per_month` in
> `config.yaml`). The monthly cap is enforced in `state.json`, so cost can't run
> over even on busy days. Keep `max_posts_per_month` ≤ your X spend cap.

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

- `limits.max_posts_per_run` / `max_posts_per_day` / `max_posts_per_month` —
  budget control (keep the monthly cap ≤ your X spend cap).
- `rotterdam.*` — the Rotterdam alert thresholds: `wind_gust_kmh`, `rain_mm`,
  `flash_flood_mm`, `fog_visibility_m`, `heat_c`, `freeze_c`, `severe_cold_c`.
  Lower a threshold for more alerts of that type, raise it for fewer.
- `city_weather.morning_hours` / `evening_hours` — the local-time windows for
  the twice-daily Rotterdam forecast.
- `geomagnetic.kp_alert_threshold` — lower to 4 for more posts, raise to 6/7
  for only major storms.
- The disabled worldwide sources (`weather`, `weather_eu`, `gulf_weather`,
  `marine_seas`, `earthquakes`, `global_hazards`, `maritime_security`,
  `outdoor`, `algal_blooms`) can be re-enabled by flipping their `enabled: true`
  — note `weather`/`weather_eu`/`gulf_weather` also need their source modules
  restored from git history.

## Disclaimer

K5Bearing relays public NOAA/NWS data and automated advisories. It is **not**
an official source. Always confirm with official channels before making
safety-critical navigation or weather decisions.
