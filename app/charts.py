from __future__ import annotations
from app.portfolio import fmt_short

CHART_COLORS = ["#005c55", "#4f46e5", "#f59e0b", "#3b82f6", "#64748b"]
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
