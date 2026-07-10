from __future__ import annotations

import os
from pathlib import Path

from app import goal, holdings_ledger, mapping, news, parser, portfolio as pmod, prices, watchlist


BASE = Path(__file__).resolve().parent.parent


def _data_dir() -> Path:
    return Path(os.environ.get("INVESTOR_OS_DATA", str(BASE / "data")))


def load_portfolio_for_refresh(data_dir: Path):
    holdings = data_dir / "holdings.xlsx"
    if holdings.exists():
        pr = parser.parse_holdings(holdings)
    elif holdings_ledger.has_manual_holdings(data_dir):
        pr = holdings_ledger.empty_parse_result(data_dir)
    else:
        return None
    pr = holdings_ledger.apply_events(pr, data_dir) if holdings.exists() else pr
    isin_map = mapping.ensure_map(data_dir)
    isin_map.update(holdings_ledger.symbol_map(data_dir))
    quotes = prices.fetch_quotes([isin_map.get(h.isin) for h in pr.holdings if isin_map.get(h.isin)])
    extras = pmod.load_extras(data_dir / "extras.json")
    return pmod.build_portfolio(pr, isin_map, quotes, extras)


def run_refresh(data_dir: Path | None = None, pf=None) -> dict:
    data_dir = data_dir or _data_dir()
    watchlist.ensure_seeded(data_dir)
    items = watchlist.load(data_dir)
    symbol_map = watchlist.quote_symbols(items)
    yahoo_to_items = {}
    for item_symbol, yahoo in symbol_map.items():
        yahoo_to_items.setdefault(yahoo, []).append(item_symbol)
    quotes = prices.fetch_market_quotes(list(yahoo_to_items))
    quote_count = 0
    for yahoo, quote in quotes.items():
        for item_symbol in yahoo_to_items.get(yahoo, []):
            watchlist.save_quote(data_dir, item_symbol, quote)
            quote_count += 1

    pf = pf or load_portfolio_for_refresh(data_dir)
    snapshot_count = holdings_ledger.record_snapshot(data_dir, pf) if pf is not None else 0

    try:
        security_meta_count = goal.refresh_security_meta(data_dir, pf)
    except Exception:
        security_meta_count = 0

    try:
        news_result = news.fetch_all(data_dir, pf)
        news_count = sum(news_result.values()) if isinstance(news_result, dict) else int(news_result or 0)
    except Exception:
        news_count = 0

    from app import storage
    storage.set_state(data_dir, "last_refresh", storage.now_iso())
    return {"watchlist_quotes": quote_count, "portfolio_snapshots": snapshot_count,
            "security_meta": security_meta_count, "news_items": news_count}


def main() -> None:
    result = run_refresh()
    print(f"Refreshed {result['watchlist_quotes']} watchlist quotes, "
          f"{result['portfolio_snapshots']} portfolio snapshots, "
          f"{result['security_meta']} security meta rows, and "
          f"{result['news_items']} news items.")


if __name__ == "__main__":
    main()

