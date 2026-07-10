from pathlib import Path

from app import refresh, watchlist
from app.parser import parse_holdings
from app.portfolio import build_portfolio
from app.prices import Quote


FIX = Path(__file__).parent / "fixtures" / "sample-holdings.xlsx"


def test_refresh_records_quotes_and_snapshots(tmp_path, monkeypatch):
    pf = build_portfolio(parse_holdings(FIX), {"INE001A01001": "ALPHAMOT"},
                         {"ALPHAMOT": Quote(300.0, 2.0)}, [])

    def fake_market_quotes(symbols):
        return {s: Quote(100.0, 0.5) for s in symbols}

    monkeypatch.setattr(refresh.prices, "fetch_market_quotes", fake_market_quotes)
    result = refresh.run_refresh(tmp_path, pf)

    assert result["watchlist_quotes"] > 0
    assert result["portfolio_snapshots"] == 3
    assert any(q["price"] == 100.0 for q in watchlist.quote_map(tmp_path).values())
