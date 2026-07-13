from __future__ import annotations

import os
from datetime import date, datetime
from pathlib import Path

from app import datafiles, goal, holdings_ledger, mapping, news, portfolio as pmod, prices, watchlist


BASE = Path(__file__).resolve().parent.parent

OLD_FILE_DAYS = 10
SKIP_RATIO_WARN = 0.10


def _data_dir() -> Path:
    return Path(os.environ.get("INVESTOR_OS_DATA", str(BASE / "data")))


def load_portfolio_for_refresh(data_dir: Path):
    pr, _path, _warns = datafiles.resolve_and_parse_holdings(data_dir)
    if pr is None:
        return None
    isin_map = mapping.ensure_map(data_dir)
    quotes = prices.fetch_quotes([isin_map.get(h.isin) for h in pr.holdings if isin_map.get(h.isin)])
    extras = pmod.load_extras(data_dir / "extras.json")
    return pmod.build_portfolio(pr, isin_map, quotes, extras)


def run_refresh(data_dir: Path | None = None, pf=None) -> dict:
    """One-shot: load newest data files, refresh everything, report freshness."""
    data_dir = data_dir or _data_dir()
    report: dict = {"holdings_file": None, "holdings_date": None, "rows": 0, "skipped": 0,
                    "advisory_file": None, "watchlist_quotes": 0, "history_warmed": 0,
                    "security_meta": 0, "news_items": 0, "portfolio_snapshots": 0,
                    "live_prices": 0, "warnings": []}
    warn = report["warnings"].append

    # 1. Resolve + parse newest holdings; build the portfolio.
    pr, holdings_path, resolve_warns = datafiles.resolve_and_parse_holdings(data_dir)
    for w in resolve_warns:
        warn(w)
    if pf is None and pr is not None:
        try:
            isin_map = mapping.ensure_map(data_dir)
            quotes = prices.fetch_quotes(
                [isin_map.get(h.isin) for h in pr.holdings if isin_map.get(h.isin)])
            extras = pmod.load_extras(data_dir / "extras.json")
            pf = pmod.build_portfolio(pr, isin_map, quotes, extras)
        except Exception as exc:
            warn(f"portfolio build failed ({type(exc).__name__})")
            pf = None
    if holdings_path is not None:
        report["holdings_file"] = holdings_path.name
        mtime = datetime.fromtimestamp(holdings_path.stat().st_mtime)
        report["holdings_date"] = mtime.strftime("%d %b %Y")
        age_days = (datetime.now() - mtime).days
        if age_days > OLD_FILE_DAYS:
            warn(f"holdings file is {age_days} days old — download a fresh export from ICICI Direct")
    if pr is not None:
        report["rows"] = len(pr.holdings)
        report["skipped"] = len(pr.skipped)
        total = report["rows"] + report["skipped"]
        if total and report["skipped"] / total > SKIP_RATIO_WARN:
            warn(f"{report['skipped']} of {total} rows skipped — incomplete export; "
                 "ask ICICI Direct for a full download")
    else:
        warn("no holdings file found — drop the ICICI export into data/holdings/")

    adv = datafiles.latest_advisory(data_dir)
    report["advisory_file"] = adv.name if adv else None

    # 2. Watchlist quotes.
    try:
        watchlist.ensure_seeded(data_dir)
        items = watchlist.load(data_dir)
        symbol_map = watchlist.quote_symbols(items)
        yahoo_to_items: dict = {}
        for item_symbol, yahoo in symbol_map.items():
            yahoo_to_items.setdefault(yahoo, []).append(item_symbol)
        quotes = prices.fetch_market_quotes(list(yahoo_to_items))
        for yahoo, quote in quotes.items():
            for item_symbol in yahoo_to_items.get(yahoo, []):
                watchlist.save_quote(data_dir, item_symbol, quote)
                report["watchlist_quotes"] += 1
    except Exception as exc:
        warn(f"watchlist quotes failed ({type(exc).__name__})")

    # 3. Live-price coverage + history warm for the overview chart.
    if pf is not None:
        try:
            cons = pf.consolidated()
            report["live_prices"] = sum(1 for c in cons if c.price_live)
            if cons and report["live_prices"] == 0:
                warn("no live prices — check the internet connection (showing Excel prices)")
            symbols = [c.nse_symbol for c in cons if c.nse_symbol]
            hist = prices.fetch_history(symbols, "6mo")
            report["history_warmed"] = len(hist)
        except Exception as exc:
            warn(f"price history failed ({type(exc).__name__})")

    # 4. Security metadata (market caps for the Goal page).
    try:
        report["security_meta"] = goal.refresh_security_meta(data_dir, pf) if pf else 0
    except Exception as exc:
        warn(f"security metadata failed ({type(exc).__name__})")

    # 5. News.
    try:
        news_result = news.fetch_all(data_dir, pf)
        report["news_items"] = (sum(news_result.values())
                                if isinstance(news_result, dict) else int(news_result or 0))
    except Exception as exc:
        warn(f"news fetch failed ({type(exc).__name__})")

    # 6. Snapshot + state.
    try:
        report["portfolio_snapshots"] = (
            holdings_ledger.record_snapshot(data_dir, pf) if pf is not None else 0)
    except Exception as exc:
        warn(f"snapshot failed ({type(exc).__name__})")
    try:
        from app import storage
        storage.set_state(data_dir, "last_refresh", storage.now_iso())
    except Exception as exc:
        warn(f"state save failed ({type(exc).__name__})")
    return report


def format_report(r: dict) -> str:
    lines = [f"Investor OS refresh — {date.today():%d %b %Y}"]
    if r["holdings_file"]:
        lines.append(f"Holdings : {r['holdings_file']} ({r['holdings_date']}) · "
                     f"{r['rows']} rows · {r['skipped']} skipped")
    else:
        lines.append("Holdings : none found")
    lines.append(f"Advisory : {r['advisory_file'] or 'none found'}")
    lines.append(f"Prices   : {r['live_prices']}/{r['rows']} live · "
                 f"history warmed for {r['history_warmed']} stocks · "
                 f"{r['watchlist_quotes']} watchlist quotes")
    lines.append(f"News     : {r['news_items']} items stored")
    lines.append(f"Snapshot : {'written' if r['portfolio_snapshots'] else 'not written'}")
    if r["warnings"]:
        lines.append("Warnings :")
        lines.extend(f"  - {w}" for w in r["warnings"])
    else:
        lines.append("Warnings : none")
    return "\n".join(lines)


def main() -> None:
    print(format_report(run_refresh()))


if __name__ == "__main__":
    main()
