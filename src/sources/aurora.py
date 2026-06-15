"""Aurora-visibility signal, derived from the planetary Kp index.

The equatorward edge of the auroral oval moves toward lower latitudes as Kp
rises. We translate the current Kp into a rough "how far south (or north, in
the Southern Hemisphere) might it be visible" advisory with example regions.
This is the standard "Kp viewline" approach used by aurora apps.
"""
from __future__ import annotations

from . import Signal
from . import swpc

# Kp -> (Northern Hemisphere example regions, Southern Hemisphere example regions).
# Each tier is cumulative — higher Kp means everything above plus these.
VIEWLINE = {
    5: ("N. Scotland, Scandinavia, N. Germany, WA/MT/ND/MN/ME (US), S. Canada",
        "Tasmania, southern NZ, southern Chile/Argentina"),
    6: ("Ireland, England, Denmark, N. Poland, OR/IA/NY/MI (US)",
        "Victoria & southern Australia, most of NZ"),
    7: ("Central Europe (Czechia, S. Germany), NE/IL/OH/PA (US)",
        "Southern Australia, northern NZ"),
    8: ("France, Austria, Hungary, CO/KS/MO/VA (US)",
        "Most of Australia, southern South America"),
    9: ("S. Europe, central US — rare low-latitude display",
        "Lower-latitude South America, South Africa"),
}


def aurora_signal(kp_threshold: int) -> Signal | None:
    kp = swpc.current_kp()
    if kp is None or kp < kp_threshold:
        return None
    tier = min(int(kp), 9)
    north, south = VIEWLINE.get(tier, VIEWLINE[5])
    text = (
        f"AURORA WATCH — Kp {kp:.0f}\n"
        f"Possible overhead/low on the horizon:\n"
        f"N: {north}\n"
        f"S: {south}\n"
        f"Look toward the poles, away from city lights."
    )
    return Signal(
        category="aurora",
        severity=45 + int(kp) * 4,  # below storm/compass alerts of the same Kp
        text=text,
        dedup_key=f"aurora:Kp{int(kp)}",
        hashtags=["#K5Bearing", "#Aurora", "#Northernlights"],
    )
