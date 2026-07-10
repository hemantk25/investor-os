from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from pathlib import Path

from app import storage


GOAL_FILE = "goal.json"

DEFAULT_GOAL = {
    "target_value": 200000000,
    "target_date": "2031-07-31",
    "expected_cagr_pct": 16.0,
    "sip_monthly": 500000,
    "baseline_value": None,
    "baseline_date": None,
    "bands_pct": {"large": 40, "mid": 40, "small": 20},
    "small_cap_max_pct": 20,
    "cap_large_min_cr": 100000,
    "cap_mid_min_cr": 33000,
}

COMMODITY_KEYWORDS = ["mining", "metal", "oil", "gas", "coal", "commodity"]
CRYPTO_KEYWORDS = ["crypto"]

SECURITY_META_TTL_DAYS = 7
SECURITY_META_FETCH_CAP = 25


def _goal_path(data_dir: Path) -> Path:
    return Path(data_dir) / GOAL_FILE


def _write_goal(path: Path, goal: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(goal, indent=2), encoding="utf-8")


def load_goal(data_dir: Path, current_total: float | None = None) -> dict:
    path = _goal_path(data_dir)
    if not path.exists():
        goal = dict(DEFAULT_GOAL)
        if current_total is not None:
            goal["baseline_value"] = current_total
            goal["baseline_date"] = date.today().isoformat()
        _write_goal(path, goal)
        return goal

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("goal.json must contain a JSON object")
    except Exception as exc:
        goal = dict(DEFAULT_GOAL)
        goal["error"] = str(exc)
        return goal

    goal = dict(DEFAULT_GOAL)
    goal.update(raw)
    if goal.get("baseline_value") is None and current_total is not None:
        goal["baseline_value"] = current_total
        goal["baseline_date"] = date.today().isoformat()
        _write_goal(path, goal)
    return goal


def _monthly(rate_annual: float) -> float:
    return (1 + rate_annual) ** (1 / 12) - 1


def required_value(goal: dict, on_date: date) -> float:
    v0, t0 = goal["baseline_value"], date.fromisoformat(goal["baseline_date"])
    m = max(0.0, (on_date - t0).days / 30.4375)
    r = _monthly(goal["expected_cagr_pct"] / 100)
    sip = goal["sip_monthly"]
    return v0 * (1 + r) ** m + (sip * (((1 + r) ** m - 1) / r) if r else sip * m)


def required_series(goal: dict, upto: date, points: int = 60) -> list[tuple[str, float]]:
    t0 = date.fromisoformat(goal["baseline_date"])
    total_days = (upto - t0).days
    points = max(2, points)
    out = []
    for i in range(points):
        frac = i / (points - 1)
        d = t0 + timedelta(days=round(total_days * frac))
        out.append((d.isoformat(), required_value(goal, d)))
    return out


def implied_cagr(goal: dict, current_value: float, today: date) -> float | None:
    target, td = goal["target_value"], date.fromisoformat(goal["target_date"])
    n = (td - today).days / 30.4375
    if n <= 0:
        return None

    def fv(x):
        r = _monthly(x)
        return current_value * (1 + r) ** n + (
            goal["sip_monthly"] * (((1 + r) ** n - 1) / r) if r else goal["sip_monthly"] * n
        )

    if fv(0.0) >= target:
        return 0.0
    lo, hi = 0.0, 1.0
    if fv(hi) < target:
        return None
    for _ in range(60):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if fv(mid) < target else (lo, mid)
    return round(hi * 100, 1)


def classify_caps(cons_positions, meta: dict[str, dict], goal: dict) -> dict:
    large_min = goal["cap_large_min_cr"] * 1e7
    mid_min = goal["cap_mid_min_cr"] * 1e7
    buckets = {"large": 0.0, "mid": 0.0, "small": 0.0, "unclassified": 0.0}
    for pos in cons_positions:
        sym = getattr(pos, "nse_symbol", None)
        info = meta.get(sym) if sym else None
        cap = info.get("market_cap") if info else None
        value = pos.value
        if cap is None:
            buckets["unclassified"] += value
        elif cap >= large_min:
            buckets["large"] += value
        elif cap >= mid_min:
            buckets["mid"] += value
        else:
            buckets["small"] += value

    classified_total = buckets["large"] + buckets["mid"] + buckets["small"]
    total = classified_total + buckets["unclassified"]

    def pct_of(value, denom):
        return (value / denom * 100) if denom else 0.0

    out = {
        "large": {"value": buckets["large"], "pct": pct_of(buckets["large"], classified_total)},
        "mid": {"value": buckets["mid"], "pct": pct_of(buckets["mid"], classified_total)},
        "small": {"value": buckets["small"], "pct": pct_of(buckets["small"], classified_total)},
        "unclassified": {"value": buckets["unclassified"], "pct": pct_of(buckets["unclassified"], total)},
    }
    out["small_breach"] = out["small"]["pct"] > goal["small_cap_max_pct"]
    return out


def _text_matches(info: dict, keywords: list[str]) -> bool:
    haystack = " ".join(filter(None, [info.get("industry"), info.get("sector")])).lower()
    return any(k in haystack for k in keywords)


def compliance(cons_positions, meta: dict[str, dict]) -> list[dict]:
    commodity_hits: list[str] = []
    crypto_hits: list[str] = []
    for pos in cons_positions:
        sym = getattr(pos, "nse_symbol", None)
        info = meta.get(sym) if sym else None
        if not info:
            continue
        name = getattr(pos, "name", sym)
        if _text_matches(info, COMMODITY_KEYWORDS):
            commodity_hits.append(name)
        if _text_matches(info, CRYPTO_KEYWORDS):
            crypto_hits.append(name)
    return [
        {"rule": "No commodities", "ok": not commodity_hits,
         "detail": ", ".join(commodity_hits) if commodity_hits else ""},
        {"rule": "No crypto", "ok": not crypto_hits,
         "detail": ", ".join(crypto_hits) if crypto_hits else ""},
    ]


def load_security_meta(data_dir: Path) -> dict[str, dict]:
    with storage.connect(data_dir) as con:
        rows = con.execute("SELECT * FROM security_meta").fetchall()
        return {r["symbol"]: dict(r) for r in rows}


def _upsert_security_meta(data_dir: Path, symbol: str, market_cap, sector, industry) -> None:
    with storage.connect(data_dir) as con:
        con.execute(
            """
            INSERT INTO security_meta(symbol, market_cap, sector, industry, fetched_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(symbol) DO UPDATE SET market_cap = excluded.market_cap,
                                              sector = excluded.sector,
                                              industry = excluded.industry,
                                              fetched_at = excluded.fetched_at
            """,
            (symbol, market_cap, sector, industry, storage.now_iso()),
        )
        con.commit()


def refresh_security_meta(data_dir: Path, pf, ttl_days: int = SECURITY_META_TTL_DAYS) -> int:
    if pf is None:
        return 0
    symbols = sorted({c.nse_symbol for c in pf.consolidated() if c.nse_symbol})
    if not symbols:
        return 0

    cutoff = (datetime.now() - timedelta(days=ttl_days)).replace(microsecond=0).isoformat()
    with storage.connect(data_dir) as con:
        rows = con.execute("SELECT symbol, fetched_at FROM security_meta").fetchall()
    fetched_at = {r["symbol"]: r["fetched_at"] for r in rows}

    stale = [s for s in symbols if s not in fetched_at or fetched_at[s] < cutoff]
    stale = stale[:SECURITY_META_FETCH_CAP]

    updated = 0
    for symbol in stale:
        try:
            import yfinance as yf
            info = yf.Ticker(f"{symbol}.NS").info or {}
        except Exception:
            continue
        _upsert_security_meta(data_dir, symbol, info.get("marketCap"),
                              info.get("sector"), info.get("industry"))
        updated += 1
    return updated
