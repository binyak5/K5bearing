"""World Cup scores: result wording + knockout-only / final-only filtering."""
from src.sources import worldcup as wc


# --- _score_text --------------------------------------------------------
def _side(name, score, pens=None):
    return {"name": name, "score": score, "pens": pens}


def test_score_text_regular():
    out = wc._score_text(_side("Netherlands", 3), _side("United States", 1), "Round of 16", "FT")
    assert out == "Full time - Netherlands 3–1 United States (Round of 16)"


def test_score_text_penalties():
    out = wc._score_text(_side("Argentina", 2, 4), _side("France", 2, 2), "Final", "FT")
    assert out == "Full time (AET) - Argentina 2–2 France - 4–2 penalties (Final)"


# --- final_signals: filtering -------------------------------------------
class _Resp:
    def __init__(self, payload):
        self._p = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._p


def _event(eid, slug, completed, home, away, date="2026-06-28T19:00Z"):
    return {
        "id": eid, "date": date, "season": {"slug": slug},
        "competitions": [{
            "status": {"type": {"completed": completed, "detail": "FT"}},
            "competitors": [
                {"homeAway": "home", "team": {"displayName": home[0]}, "score": home[1], "shootoutScore": None},
                {"homeAway": "away", "team": {"displayName": away[0]}, "score": away[1], "shootoutScore": None},
            ],
        }],
    }


def test_final_signals_only_finished_knockouts(monkeypatch):
    payload = {"events": [
        _event("1", "round-of-32", True, ("Brazil", "2"), ("Korea", "0")),   # keep
        _event("2", "group", True, ("Spain", "1"), ("Japan", "1")),          # drop: group stage
        _event("3", "round-of-16", False, ("France", "0"), ("Mexico", "0")),  # drop: not final
    ]}
    monkeypatch.setattr(wc.requests, "get", lambda *a, **k: _Resp(payload))
    sigs = wc.final_signals("2026-06-28T19:00:00Z")
    assert len(sigs) == 1
    assert sigs[0].dedup_key == "wc:1"
    assert sigs[0].text == "Full time - Brazil 2–0 Korea (Round of 32)"


def test_final_signals_respects_start_floor(monkeypatch):
    payload = {"events": [
        _event("9", "round-of-32", True, ("Brazil", "2"), ("Korea", "0"), date="2026-06-27T19:00Z"),
    ]}
    monkeypatch.setattr(wc.requests, "get", lambda *a, **k: _Resp(payload))
    assert wc.final_signals("2026-06-28T19:00:00Z") == []  # before start -> nothing
