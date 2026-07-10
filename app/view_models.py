from __future__ import annotations
from datetime import datetime
from app import portfolio as pmod
from app import charts

RANGE_TO_PERIOD = {"1M": "1mo", "3M": "3mo", "6M": "6mo", "1Y": "1y", "ALL": "5y"}
_GROUPS = [("equity", "Direct Equity", "NSE"), ("mf", "Mutual Funds", ""),
           ("gold", "Gold", ""), ("debt", "Debt & FD", ""), ("cash", "Cash", "")]
MARKET_METRICS = [
    {"label": "Nifty 50", "symbol": "^NSEI", "market": "India", "fmt": "index"},
    {"label": "Nifty Smallcap", "symbol": "^CNXSC", "market": "India", "fmt": "index"},
    {"label": "Nifty Midcap", "symbol": "^NSEMDCP50", "market": "India", "fmt": "index"},
    {"label": "Sensex", "symbol": "^BSESN", "market": "India", "fmt": "index"},
    {"label": "DFMGI", "symbol": "DFMGI.AE", "market": "Dubai", "fmt": "index"},
    {"label": "FADGI", "symbol": "FADGI.AE", "market": "Abu Dhabi", "fmt": "index"},
    {"label": "USD/INR", "symbol": "INR=X", "market": "FX", "fmt": "fx"},
    {"label": "Nasdaq", "symbol": "^IXIC", "market": "US", "fmt": "index"},
    {"label": "S&P 500", "symbol": "^GSPC", "market": "US", "fmt": "index"},
    {"label": "TSX Composite", "symbol": "^GSPTSE", "market": "Canada", "fmt": "index"},
]
MARKET_METRIC_SYMBOLS = [m["symbol"] for m in MARKET_METRICS]


def common(pf, active: str, member: str | None) -> dict:
    live = sum(1 for c in pf.consolidated(member) if c.price_live)
    total = len(pf.consolidated(member))
    return {"members": pf.members, "active": active, "member": member,
            "brand_sub": "Private · Paresh Karia",
            "freshness": f"Updated {pf.asof:%d %b %Y %H:%M} · live prices {live}/{total}"}


def _market_value(price, fmt: str) -> str:
    if price is None:
        return "--"
    if fmt == "fx":
        return f"{price:.2f}"
    return f"{price:,.0f}" if abs(price) >= 1000 else f"{price:,.2f}"


def market_metrics(quotes: dict | None = None) -> list[dict]:
    quotes = quotes or {}
    out = []
    for metric in MARKET_METRICS:
        q = quotes.get(metric["symbol"])
        day = q.day_pct if q and q.day_pct is not None else None
        out.append({
            "label": metric["label"],
            "symbol": metric["symbol"],
            "market": metric["market"],
            "value": _market_value(q.price if q else None, metric["fmt"]),
            "change": pmod.fmt_pct(day) if day is not None else "--",
            "known": q is not None,
            "up": (day or 0) >= 0,
        })
    return out


def _asset_donut(t) -> dict:
    entries = []
    for idx, (key, label, _tag) in enumerate(_GROUPS):
        value = t.equity_value if key == "equity" else t.extras_by_class.get(key, 0.0)
        entries.append({"label": label, "value": value,
                        "color": charts.CHART_COLORS[idx % len(charts.CHART_COLORS)]})
    return charts.donut_chart(entries)


def _family_donut(pf, member) -> dict:
    if member:
        selected = pf.totals(member).total_value
        rest = max(pf.totals().total_value - selected, 0.0)
        chart = charts.donut_chart([
            {"label": member, "value": selected, "color": charts.CHART_COLORS[0]},
            {"label": "Rest of Family", "value": rest, "color": charts.CHART_COLORS[4]},
        ])
        chart["title"] = f"{member} vs Family"
        return chart
    entries = [{"label": m, "value": pf.totals(m).total_value,
                "color": charts.CHART_COLORS[idx % len(charts.CHART_COLORS)]}
               for idx, m in enumerate(pf.members)]
    chart = charts.donut_chart(entries)
    chart["title"] = "Family Split"
    return chart


def overview(pf, member, rng: str) -> dict:
    t = pf.totals(member)
    cards = [
        {"label": "Current Value", "value": pmod.fmt_short(t.total_value),
         "sub": pmod.fmt_inr(t.total_value), "tone": "muted"},
        {"label": "Total Investment", "value": pmod.fmt_short(t.invested_known),
         "sub": "Known cost basis", "tone": "muted"},
        {"label": "Total Return", "value": pmod.fmt_short(t.pl),
         "sub": (pmod.fmt_pct(t.pl_pct) if t.pl_pct is not None else "—"),
         "tone": "up" if t.pl >= 0 else "down"},
        {"label": "Day P/L", "value": pmod.fmt_short(t.day_pl),
         "sub": pmod.fmt_pct(t.day_pl_pct), "tone": "up" if t.day_pl >= 0 else "down"},
        {"label": "Cash / Unallocated", "value": pmod.fmt_short(t.extras_by_class.get("cash", 0.0)),
         "sub": f"{(t.extras_by_class.get('cash', 0.0)/t.total_value*100 if t.total_value else 0):.1f}% of portfolio",
         "tone": "muted"},
    ]
    movers = [{"name": c.name.title(), "pct": pmod.fmt_pct(c.day_pct),
               "up": (c.day_pct or 0) >= 0, "short": pmod.fmt_short(c.value)}
              for c in pf.movers(member)]
    return {"cards": cards, "alloc": charts.alloc_segments(t), "movers": movers,
            "range": rng, "ranges": list(RANGE_TO_PERIOD),
            "market_metrics": market_metrics(),
            "asset_donut": _asset_donut(t), "family_donut": _family_donut(pf, member),
            "watchlist_preview": []}


def watchlist_preview(base_dir, member: str | None, limit: int = 6) -> list[dict]:
    from app import watchlist as wmod
    return wmod.with_quotes(base_dir, wmod.filtered(wmod.load(base_dir), member=member, limit=limit))


def watchlist_ctx(base_dir, member: str | None, q: str = "", market: str = "",
                  group: str = "", category: str = "", subcategory: str = "") -> dict:
    from app import watchlist as wmod
    items = wmod.with_quotes(base_dir, wmod.filtered(wmod.load(base_dir), q=q, market=market,
                                                     member=member, group=group,
                                                     category=category,
                                                     subcategory=subcategory))
    boards = []
    for board in wmod.open_boards(base_dir):
        bitems = wmod.with_quotes(base_dir, wmod.board_items(base_dir, board, q=q))
        board = dict(board)
        board["items"] = bitems
        board["count"] = len(bitems)
        boards.append(board)
    return {"items": items, "q": q or "", "watch_market": market or "",
            "watch_group": group or "", "watch_category": category or "",
            "watch_subcategory": subcategory or "",
            "watch_markets": wmod.MARKETS, "watch_groups": wmod.GROUPS,
            "watch_categories": wmod.CATEGORIES, "watch_subcategories": wmod.SUBCATEGORIES,
            "boards": boards, "max_boards": wmod.MAX_OPEN_BOARDS, "count": len(items)}


def holdings(pf, member, q: str, manual_items: list | None = None) -> dict:
    ql = (q or "").lower().strip()
    cls_by_isin = {p.isin: p.cls for p in pf.positions}
    source_by_isin = {}
    for p in pf.positions:
        if member is not None and p.member != member:
            continue
        source_by_isin.setdefault(p.isin, set()).add(getattr(p, "source", "excel"))
    rows = []
    total_value = 0.0
    for c in pf.consolidated(member):
        if ql and ql not in c.name.lower() and ql not in (c.nse_symbol or "").lower():
            continue
        total_value += c.value
        sources = source_by_isin.get(c.isin, {"excel"})
        source = "Mixed" if len(sources) > 1 else ("Manual" if "manual" in sources else "ICICI")
        rows.append({"name": c.name.title(), "isin": c.isin, "nse": c.nse_symbol or "",
                     "qty": c.qty, "avg": c.avg_cost, "price": c.price,
                     "value": pmod.fmt_short(c.value), "value_num": c.value,
                     "pl": (pmod.fmt_pct(c.pl_pct) if c.pl_pct is not None else "—"),
                     "pl_up": (c.pl_pct or 0) >= 0, "pl_known": c.pl_pct is not None,
                     "day": (pmod.fmt_pct(c.day_pct) if c.day_pct is not None else "—"),
                     "day_up": (c.day_pct or 0) >= 0, "day_known": c.day_pct is not None,
                     "held_by": c.held_by, "live": c.price_live,
                     "source": source, "source_ids": c.source_ids,
                     "asset_class": cls_by_isin.get(c.isin, "equity")})

    groups = []
    for key, title, tag in _GROUPS:
        group_rows = []
        sub = 0.0
        for row in rows:
            if row["asset_class"] != key:
                continue
            sub += row["value_num"]
            group_rows.append(row)
        for e in [x for x in pf.extras if member is None or x.member == member]:
            if e.asset_class != key:
                continue
            haystack = f"{e.label} {e.asset_class} {e.note}".lower()
            if ql and ql not in haystack:
                continue
            total_value += e.value
            sub += e.value
            pl_pct = (e.value / e.invested - 1) * 100 if e.invested else None
            group_rows.append({"name": e.label, "isin": "", "nse": tag or "—", "qty": None,
                         "avg": e.invested, "price": None,
                         "value": pmod.fmt_short(e.value), "value_num": e.value,
                         "pl": (pmod.fmt_pct(pl_pct) if pl_pct is not None else "—"),
                         "pl_up": (pl_pct or 0) >= 0, "pl_known": pl_pct is not None,
                         "day": "—", "day_up": True, "day_known": False,
                         "held_by": [e.member], "live": True,
                         "is_extra": True, "note": e.note, "source": "Manual Asset",
                         "source_ids": [], "asset_class": key})
        if group_rows:
            groups.append({"key": key, "title": title, "tag": tag, "rows": group_rows,
                           "subtotal": pmod.fmt_short(sub)})
    return {"groups": groups, "rows": rows, "q": q or "",
            "manual_items": manual_items or [], "holdings_total": pmod.fmt_short(total_value),
            "holdings_count": len(rows)}


def rebalance(pf, adv, tab: str) -> dict:
    badge = {"DONE": ("Done", "green"), "IN PROGRESS": ("In Progress", "amber"),
             "PENDING": ("Pending", "grey"), "REVIEW": ("Review", "grey")}
    exits = []
    for e in adv.exits:
        label, tone = badge.get(e.status, (e.status.title(), "grey"))
        exits.append({"stock": e.stock, "label": label, "tone": tone,
                      "priority": e.priority, "proceeds": e.proceeds,
                      "reason": e.reason,
                      "initials": "".join(w[0] for w in e.stock.split()[:2]).upper()})
    buys = [{"stock": b.stock, "sector": b.sector,
             "lo": pmod.fmt_short(b.alloc_lo), "hi": pmod.fmt_short(b.alloc_hi),
             "deployed": pmod.fmt_short(b.current_value),
             "pct": round(b.progress_pct),
             "entry": b.entry, "horizon": b.horizon, "thesis": b.thesis}
            for b in adv.buys]
    sched = [{"label": m.label, "exits": m.exits_text,
              "buys": m.buys_text, "here": m.is_current}
             for m in adv.schedule]
    done = sum(1 for e in adv.exits if e.status == "DONE")
    selected = tab if tab in ("exits", "buys", "schedule") else "exits"
    return {"tab": selected, "exits": exits, "buys": buys, "sched": sched,
            "summary": f"{done}/{len(adv.exits)} exits done"}


def brief_ctx(base_dir, pf, pick: str | None, data_dir) -> dict:
    from app import brief as bmod
    from app import news as nmod
    briefs_dir = base_dir / "briefs"
    files = sorted(briefs_dir.glob("*.md"), reverse=True) if briefs_dir.exists() else []
    dates = [f.stem for f in files]
    chosen = pick if pick in dates else (dates[0] if dates else None)
    sections: dict = {}
    if chosen:
        raw_md = (briefs_dir / f"{chosen}.md").read_text(encoding="utf-8")
        allowed = {item["url"] for item in nmod.load_items(data_dir, limit=5000)}
        sections = {key: bmod.sanitize_links(html, allowed)
                    for key, html in bmod.split_brief(raw_md).items()}
    news_items = nmod.load_items(data_dir, within_hours=48, limit=50)
    impact = []
    for row in bmod.impact_rows(pf, news_items):
        row = dict(row)
        row["name"] = row["name"].title()
        row["day_pct_fmt"] = pmod.fmt_pct(row["day_pct"])
        row["day_impact_fmt"] = pmod.fmt_short(row["day_impact"])
        row["value_fmt"] = pmod.fmt_short(row["value"])
        row["up"] = row["day_pct"] >= 0
        impact.append(row)
    return {"dates": dates, "chosen": chosen, "sections": sections,
            "impact": impact, "has_brief": bool(chosen)}


def profile_ctx(base_dir) -> dict:
    import markdown as md
    p = base_dir / "profile" / "one-pager.md"
    if p.exists():
        return {"has_profile": True,
                "profile_html": md.markdown(p.read_text(encoding="utf-8"),
                                            extensions=["extra"])}
    return {"has_profile": False, "profile_html": ""}


def _ago(item: dict) -> str:
    published_at = item.get("published_at")
    fetched_at = item.get("fetched_at")
    ts = published_at or fetched_at
    if not ts:
        return ""
    try:
        dt = datetime.fromisoformat(ts)
    except ValueError:
        return ""
    # published_at comes from feedparser (UTC), fetched_at from storage.now_iso() (local)
    # Use matching clock base for each timestamp source
    if published_at:
        secs = max((datetime.utcnow() - dt).total_seconds(), 0)
    else:
        secs = max((datetime.now() - dt).total_seconds(), 0)
    if secs < 3600:
        return f"{max(int(secs // 60), 1)}m ago"
    if secs < 86400:
        return f"{int(secs // 3600)}h ago"
    return f"{int(secs // 86400)}d ago"


def news_ctx(data_dir, market: str | None, mine: bool) -> dict:
    from app import news
    chosen = market if market in news.MARKETS else "All"
    load_market = chosen if chosen != "All" else None
    raw_items = news.load_items(data_dir, market=load_market, mine=mine, limit=50)
    items = [{"title": i["title"], "url": i["url"], "publisher": i.get("publisher") or "",
             "ago": _ago(i), "holding_name": i.get("holding_name")}
            for i in raw_items]
    fetched_raw = news.last_fetched(data_dir)
    fetched = None
    if fetched_raw:
        try:
            fetched = f"{datetime.fromisoformat(fetched_raw):%d %b %Y %H:%M}"
        except ValueError:
            fetched = fetched_raw
    return {"items": items, "market": chosen, "mine": mine,
            "markets": ["All"] + news.MARKETS, "fetched": fetched}
