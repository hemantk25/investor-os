from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Position:
    member: str
    name: str
    isin: str
    icici_symbol: str
    nse_symbol: str | None
    qty: float
    avg_cost: float | None
    price: float
    price_live: bool
    day_pct: float | None
    cls: str = "equity"

    @property
    def value(self):
        return self.qty * self.price

    @property
    def cost(self):
        return None if self.avg_cost is None else self.qty * self.avg_cost

    @property
    def pl(self):
        return None if self.cost is None else self.value - self.cost

    @property
    def pl_pct(self):
        return None if not self.cost else (self.value / self.cost - 1) * 100


@dataclass
class ConsolidatedPosition:
    name: str
    isin: str
    nse_symbol: str | None
    qty: float
    avg_cost: float | None
    price: float
    price_live: bool
    day_pct: float | None
    held_by: list = field(default_factory=list)
    cost_partial: bool = False

    value = Position.value
    cost = Position.cost
    pl = Position.pl
    pl_pct = Position.pl_pct


@dataclass
class Extra:
    member: str
    label: str
    asset_class: str
    value: float
    invested: float | None = None
    note: str = ""


@dataclass
class Totals:
    total_value: float
    equity_value: float
    extras_by_class: dict
    invested_known: float
    pl: float
    pl_pct: float | None
    day_pl: float
    day_pl_pct: float


class Portfolio:
    def __init__(self, positions, extras, asof, skipped, members):
        self.positions, self.extras = positions, extras
        self.asof, self.skipped, self.members = asof, skipped, members

    def filtered(self, member=None):
        return [p for p in self.positions if member is None or p.member == member]

    def consolidated(self, member=None):
        groups: dict[str, list] = {}
        for p in self.filtered(member):
            groups.setdefault(p.isin, []).append(p)
        out = []
        for isin, lots in groups.items():
            qty = sum(l.qty for l in lots)
            known = [l for l in lots if l.avg_cost is not None]
            kqty = sum(l.qty for l in known)
            avg = (sum(l.qty * l.avg_cost for l in known) / kqty) if kqty else None
            l0 = lots[0]
            out.append(ConsolidatedPosition(
                name=l0.name, isin=isin, nse_symbol=l0.nse_symbol, qty=qty, avg_cost=avg,
                price=l0.price, price_live=l0.price_live, day_pct=l0.day_pct,
                held_by=sorted({l.member for l in lots}), cost_partial=kqty < qty))
        return sorted(out, key=lambda c: -c.value)

    def _extras(self, member=None):
        return [e for e in self.extras if member is None or e.member == member]

    def totals(self, member=None):
        cons = self.consolidated(member)
        extras = self._extras(member)
        equity = sum(c.value for c in cons)
        ebc: dict[str, float] = {}
        for e in extras:
            ebc[e.asset_class] = ebc.get(e.asset_class, 0) + e.value
        invested = sum(c.qty * c.avg_cost for c in cons if c.avg_cost is not None) \
            + sum(e.invested for e in extras if e.invested)
        value_known = sum(c.value for c in cons if c.avg_cost is not None) \
            + sum(e.value for e in extras if e.invested)
        pl = value_known - invested
        day_pl = sum(c.value - c.value / (1 + c.day_pct / 100)
                     for c in cons if c.day_pct is not None)
        total = equity + sum(ebc.values())
        return Totals(total_value=total, equity_value=equity, extras_by_class=ebc,
                      invested_known=invested, pl=pl,
                      pl_pct=(pl / invested * 100) if invested else None,
                      day_pl=day_pl, day_pl_pct=(day_pl / total * 100) if total else 0.0)

    def movers(self, member=None, n=4):
        live = [c for c in self.consolidated(member) if c.day_pct is not None]
        live.sort(key=lambda c: -c.day_pct)
        return live[: n // 2] + live[-(n - n // 2):] if len(live) >= n else live


def build_portfolio(pr, isin_map, quotes, extras):
    positions = []
    for h in pr.holdings:
        sym = isin_map.get(h.isin)
        q = quotes.get(sym) if sym else None
        price = q.price if q else (h.excel_cmp or 0.0)
        positions.append(Position(
            member=h.member, name=h.name, isin=h.isin, icici_symbol=h.icici_symbol,
            nse_symbol=sym, qty=h.qty, avg_cost=h.avg_cost, price=price,
            price_live=q is not None,
            day_pct=q.day_pct if q else h.excel_day_pct, cls="equity"))
    return Portfolio(positions, extras, pr.asof, pr.skipped, pr.members)


def load_extras(path: Path):
    if not path.exists():
        return []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return [Extra(member=r.get("member", "PK"), label=r["label"],
                      asset_class=r["asset_class"], value=float(r["value"]),
                      invested=float(r["invested"]) if r.get("invested") else None,
                      note=r.get("note", "")) for r in raw]
    except Exception:
        return []


def _in_group(n: int) -> str:
    s = str(abs(n))
    sign = "-" if n < 0 else ""
    if len(s) <= 3:
        return sign + s
    head, tail = s[:-3], s[-3:]
    parts = []
    while len(head) > 2:
        parts.insert(0, head[-2:])
        head = head[:-2]
    if head:
        parts.insert(0, head)
    return sign + ",".join(parts + [tail])


def fmt_inr(n) -> str:
    return "₹" + _in_group(round(n))


def fmt_short(n) -> str:
    a = abs(n)
    if a >= 1e7:
        return f"₹{n/1e7:.2f} Cr"
    if a >= 1e5:
        return f"₹{n/1e5:.1f} L"
    return fmt_inr(n)


def fmt_pct(p) -> str:
    return f"{'+' if p >= 0 else ''}{p:.1f}%"
