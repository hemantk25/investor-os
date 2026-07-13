from __future__ import annotations
from app.portfolio import fmt_short

CHART_COLORS = ["#9e0906", "#1f2a40", "#c9a96e", "#3b82f6", "#6b7280"]
_CLASS_ORDER = [("equity", "Direct Equity"), ("mf", "Mutual Funds"), ("gold", "Gold (SGB)"),
                ("debt", "Debt & FD"), ("cash", "Cash")]


def area_path(series, w: int = 1000, h: int = 250) -> dict:
    if not series:
        return {"line": f"M0,{h//2} L{w},{h//2}", "area": f"M0,{h} L{w},{h} Z"}
    if len(series) == 1:
        series = [series[0], series[0]]
    lo, hi = min(series), max(series)
    span = (hi - lo) or 1.0
    n = len(series)
    def x(i): return i * w / (n - 1)
    def y(v): return h - (v - lo) / span * (h * 0.9) - h * 0.05
    pts = [f"{x(i):.1f},{y(v):.1f}" for i, v in enumerate(series)]
    line = "M" + " L".join(pts)
    area = line + f" L{w:.1f},{h} L0,{h} Z"
    return {"line": line, "area": area}


def dual_paths(actual, required, w: int = 1000, h: int = 250) -> dict:
    combined = list(actual) + list(required)
    if not combined:
        flat = f"M0,{h//2} L{w},{h//2}"
        return {"actual_line": flat, "required_line": flat, "area": f"M0,{h} L{w},{h} Z"}
    lo, hi = min(combined), max(combined)
    span = (hi - lo) or 1.0

    def y(v):
        return h - (v - lo) / span * (h * 0.9) - h * 0.05

    def line_for(series):
        s = series if len(series) > 1 else (series * 2 if series else [lo, lo])
        n = len(s)
        def x(i): return i * w / (n - 1)
        pts = [f"{x(i):.1f},{y(v):.1f}" for i, v in enumerate(s)]
        return "M" + " L".join(pts)

    actual_line = line_for(list(actual))
    required_line = line_for(list(required))
    area = actual_line + f" L{w:.1f},{h} L0,{h} Z"
    return {"actual_line": actual_line, "required_line": required_line, "area": area}


def alloc_segments(totals) -> list[dict]:
    total = totals.total_value or 1.0
    out = []
    for i, (key, label) in enumerate(_CLASS_ORDER):
        val = totals.equity_value if key == "equity" else totals.extras_by_class.get(key, 0.0)
        if val <= 0:
            continue
        out.append({"label": label, "pct": val / total * 100, "color": CHART_COLORS[i],
                    "short": fmt_short(val)})
    return out


def donut_chart(entries: list[dict]) -> dict:
    values = [e for e in entries if e.get("value", 0) > 0]
    total = sum(e["value"] for e in values)
    if not total:
        return {"segments": [], "gradient": "#e4eaf4", "total": fmt_short(0)}
    start = 0.0
    stops = []
    segments = []
    for idx, entry in enumerate(values):
        color = entry.get("color") or CHART_COLORS[idx % len(CHART_COLORS)]
        pct = entry["value"] / total * 100
        end = start + entry["value"] / total * 360
        stops.append(f"{color} {start:.2f}deg {end:.2f}deg")
        segments.append({
            "label": entry["label"],
            "value": entry["value"],
            "short": fmt_short(entry["value"]),
            "pct": pct,
            "color": color,
        })
        start = end
    return {"segments": segments, "gradient": "conic-gradient(" + ", ".join(stops) + ")",
            "total": fmt_short(total)}


def portfolio_series(pf, member, history) -> list:
    if not history:
        return []
    cons = pf.consolidated(member)
    lengths = [len(history[c.nse_symbol]) for c in cons if c.nse_symbol in history]
    if not lengths:
        return []
    n = min(lengths)
    nonmarket = sum(v for v in pf.totals(member).extras_by_class.values())
    series = []
    for i in range(n):
        total = nonmarket
        for c in cons:
            h = history.get(c.nse_symbol)
            if h:
                total += c.qty * h[-n + i]
        series.append(total)
    return series
