from __future__ import annotations
from app import portfolio as pmod
from app import charts

RANGE_TO_PERIOD = {"1M": "1mo", "3M": "3mo", "6M": "6mo", "1Y": "1y", "ALL": "5y"}
_GROUPS = [("equity", "Direct Equity", "NSE"), ("mf", "Mutual Funds", ""),
           ("gold", "Gold", ""), ("debt", "Debt & FD", ""), ("cash", "Cash", "")]


def common(pf, active: str, member: str | None) -> dict:
    live = sum(1 for c in pf.consolidated(member) if c.price_live)
    total = len(pf.consolidated(member))
    return {"members": pf.members, "active": active, "member": member,
            "brand_sub": "Private · Paresh Karia",
            "freshness": f"Updated {pf.asof:%d %b %Y %H:%M} · live prices {live}/{total}"}


def overview(pf, member, rng: str) -> dict:
    t = pf.totals(member)
    cards = [
        {"label": "Total Value", "value": pmod.fmt_short(t.total_value),
         "sub": pmod.fmt_inr(t.total_value), "tone": "muted"},
        {"label": "Unrealised P/L", "value": pmod.fmt_short(t.pl),
         "sub": (pmod.fmt_pct(t.pl_pct) if t.pl_pct is not None else "—"),
         "tone": "up" if t.pl >= 0 else "down"},
        {"label": "Day P/L", "value": pmod.fmt_short(t.day_pl),
         "sub": pmod.fmt_pct(t.day_pl_pct), "tone": "up" if t.day_pl >= 0 else "down"},
        {"label": "Cash Available", "value": pmod.fmt_short(t.extras_by_class.get("cash", 0.0)),
         "sub": f"{(t.extras_by_class.get('cash', 0.0)/t.total_value*100 if t.total_value else 0):.1f}% of portfolio",
         "tone": "muted"},
    ]
    movers = [{"name": c.name.title(), "pct": pmod.fmt_pct(c.day_pct),
               "up": (c.day_pct or 0) >= 0, "short": pmod.fmt_short(c.value)}
              for c in pf.movers(member)]
    return {"cards": cards, "alloc": charts.alloc_segments(t), "movers": movers,
            "range": rng, "ranges": list(RANGE_TO_PERIOD)}


def holdings(pf, member, q: str) -> dict:
    ql = (q or "").lower().strip()
    cls_by_isin = {p.isin: p.cls for p in pf.positions}
    groups = []
    for key, title, tag in _GROUPS:
        rows = []
        sub = 0.0
        for c in pf.consolidated(member):
            if cls_by_isin.get(c.isin) != key:
                continue
            if ql and ql not in c.name.lower() and ql not in (c.nse_symbol or "").lower():
                continue
            sub += c.value
            rows.append({"name": c.name.title(), "nse": c.nse_symbol or "—",
                         "qty": c.qty, "avg": c.avg_cost, "price": c.price,
                         "value": pmod.fmt_short(c.value),
                         "pl": (pmod.fmt_pct(c.pl_pct) if c.pl_pct is not None else "—"),
                         "pl_up": (c.pl_pct or 0) >= 0, "pl_known": c.pl_pct is not None,
                         "day": (pmod.fmt_pct(c.day_pct) if c.day_pct is not None else "—"),
                         "day_up": (c.day_pct or 0) >= 0, "day_known": c.day_pct is not None,
                         "held_by": c.held_by, "live": c.price_live})
        if rows:
            groups.append({"key": key, "title": title, "tag": tag, "rows": rows,
                           "subtotal": pmod.fmt_short(sub)})
    return {"groups": groups, "q": q or ""}
