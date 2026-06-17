"""California harmful algal bloom (HAB) / red tide monitoring, from the
CalHABMAP shore-station network via the SCCOOS ERDDAP server (public, keyless).

Each pier reports Pseudo-nitzschia cell counts and domoic acid, the toxin
behind these blooms. We pull the recent readings for each station and warn when
either crosses a bloom-level threshold. US Pacific coast only.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import requests

from ..config import USER_AGENT
from . import Signal, pick, gather

ERDDAP = "https://erddap.sccoos.org/erddap/tabledap/{dataset}.json"
VARS = "time,pDA,tDA,Pseudo_nitzschia_seriata_group,Pseudo_nitzschia_delicatissima_group"
TIMEOUT = 25
TZ = "America/Los_Angeles"  # the whole CalHABMAP network is on the US Pacific coast

# (display location, ERDDAP dataset id) for the CalHABMAP shore stations.
STATIONS = [
    ("San Diego", "HABs-ScrippsPier"),
    ("Newport Beach", "HABs-NewportBeachPier"),
    ("Santa Monica", "HABs-SantaMonicaPier"),
    ("Santa Barbara", "HABs-StearnsWharf"),
    ("Avila Beach", "HABs-CalPolyPier"),
    ("Monterey", "HABs-MontereyWharf"),
    ("Santa Cruz", "HABs-SantaCruzWharf"),
    ("Bodega Bay", "HABs-BodegaMarineLab"),
    ("Humboldt", "HABs-TrinidadPier"),
]

# Fired by a Pseudo-nitzschia cell-count bloom.
CELL_VARIANTS = [
    "A harmful bloom is taking hold off {name}, Pseudo-nitzschia running to {cells} cells per litre. The water can turn toxic with domoic acid. Avoid discolored patches and do not harvest shellfish until it clears.",
]

# Fired by a domoic acid spike.
DA_VARIANTS = [
    "Domoic acid is spiking off {name}, the bloom toxin climbing to {da} ng/mL. Do not harvest or eat local shellfish, and keep well clear of any discolored water.",
]


def _num(v) -> float:
    """ERDDAP gives None or a number; treat missing as 0 for comparisons."""
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _recent_rows(dataset: str, cutoff_iso: str) -> list[list]:
    url = f"{ERDDAP.format(dataset=dataset)}?{VARS}&time>={cutoff_iso}"
    try:
        resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT)
        resp.raise_for_status()
        return resp.json().get("table", {}).get("rows", []) or []
    except (requests.RequestException, ValueError):
        return []


def hab_signals(cell_threshold: float, da_threshold: float, lookback_days: int = 14) -> list[Signal]:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=lookback_days)).strftime("%Y-%m-%dT00:00:00Z")

    def _one(station: tuple) -> Signal | None:
        name, dataset = station
        rows = _recent_rows(dataset, cutoff)
        # Rows come time-ascending; keep the most recent one over threshold.
        best = None  # (time, cells, da)
        for row in rows:
            # row = [time, pDA, tDA, pn_seriata, pn_delicatissima]
            t = row[0]
            cells = _num(row[3]) + _num(row[4])
            da = max(_num(row[1]), _num(row[2]))
            if cells >= cell_threshold or da >= da_threshold:
                best = (t, cells, da)  # later rows overwrite -> latest wins
        if best is None:
            return None
        t, cells, da = best
        day = (t or "")[:10]
        key = f"hab:{dataset}:{day}"
        # Lead with whichever signal is the stronger driver of the alert.
        if da >= da_threshold and (cells < cell_threshold or da >= da_threshold * 2):
            text = pick(DA_VARIANTS, key).format(name=name, da=round(da, 1))
        else:
            text = pick(CELL_VARIANTS, key).format(name=name, cells=f"{int(cells):,}")
        return Signal(
            category="hab",
            severity=64,
            text=text,
            dedup_key=key,
            hashtags=["#RedTide", "#Marine"],
            tz=TZ,
        )

    return gather(_one, STATIONS)
