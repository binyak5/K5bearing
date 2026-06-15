"""Aurora-visibility signal, derived from the planetary Kp index.

The equatorward edge of the auroral oval moves toward lower latitudes as Kp
rises. We translate the current Kp into a rough "how far south (or north, in
the Southern Hemisphere) might it be visible" advisory with example regions.
This is the standard "Kp viewline" approach used by aurora apps.
"""
from __future__ import annotations

from . import Signal
from . import swpc

# Kp -> short list of example regions where the aurora may be visible.
# Higher Kp pushes the oval toward lower latitudes, so each tier reaches further.
VIEWLINE = {
    5: "Scotland, Scandinavia, and the northern US",
    6: "Ireland, Denmark, and the northern US",
    7: "the UK, central Europe, and the northern US",
    8: "northern France, the Alps, and the central US",
    9: "southern Europe and the central US, which is rare",
}


def aurora_signal(kp_threshold: int) -> Signal | None:
    kp = swpc.current_kp()
    if kp is None or kp < kp_threshold:
        return None
    tier = min(int(kp), 9)
    regions = VIEWLINE.get(tier, VIEWLINE[5])
    text = (
        f"Kp has climbed to {kp:.0f}, expanding the auroral oval toward lower "
        f"latitudes, so the aurora may appear over {regions} and at matching "
        "southern latitudes. Look poleward, well away from city lights."
    )
    return Signal(
        category="aurora",
        severity=45 + int(kp) * 4,  # below storm/compass alerts of the same Kp
        text=text,
        dedup_key=f"aurora:Kp{int(kp)}",
        hashtags=["#Aurora", "#SpaceWeather"],
    )
