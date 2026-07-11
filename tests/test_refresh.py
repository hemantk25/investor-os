from pathlib import Path
import shutil

from app import holdings_ledger as ledger
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
    # No network for the two new fetchers wired into run_refresh.
    monkeypatch.setattr(refresh.goal, "refresh_security_meta", lambda data_dir, pf, **kw: 2)
    monkeypatch.setattr(refresh.news, "fetch_all",
                        lambda data_dir, pf: {"holdings": 3, "markets": 5})

    result = refresh.run_refresh(tmp_path, pf)

    assert result["watchlist_quotes"] > 0
    assert result["portfolio_snapshots"] == 3
    assert result["security_meta"] == 2
    assert result["news_items"] == 8
    assert any(q["price"] == 100.0 for q in watchlist.quote_map(tmp_path).values())


def test_refresh_survives_security_meta_and_news_failures(tmp_path, monkeypatch):
    pf = build_portfolio(parse_holdings(FIX), {"INE001A01001": "ALPHAMOT"},
                         {"ALPHAMOT": Quote(300.0, 2.0)}, [])

    monkeypatch.setattr(refresh.prices, "fetch_market_quotes", lambda symbols: {})

    def boom(*args, **kwargs):
        raise RuntimeError("network down")

    monkeypatch.setattr(refresh.goal, "refresh_security_meta", boom)
    monkeypatch.setattr(refresh.news, "fetch_all", boom)

    result = refresh.run_refresh(tmp_path, pf)

    assert result["security_meta"] == 0
    assert result["news_items"] == 0
    assert result["portfolio_snapshots"] == 3


def test_refresh_portfolio_loader_ignores_legacy_manual_events(tmp_path, monkeypatch):
    shutil.copy(FIX, tmp_path / "holdings.xlsx")
    ledger.add_manual(tmp_path, {"member": "PK", "name": "Epsilon Tech",
                                 "isin": "INE005E01011", "symbol": "EPSILON",
                                 "qty": "10", "avg_cost": "40", "price": "45"})
    ledger.add_sell(tmp_path, {"member": "PK", "isin": "INE001A01001", "qty": "25"})
    monkeypatch.setattr(refresh.mapping, "ensure_map",
                        lambda data: {"INE001A01001": "ALPHAMOT"})
    monkeypatch.setattr(refresh.prices, "fetch_quotes",
                        lambda symbols: {"ALPHAMOT": Quote(300.0, 2.0)})

    pf = refresh.load_portfolio_for_refresh(tmp_path)

    alpha = next(c for c in pf.consolidated("PK") if c.isin == "INE001A01001")
    assert alpha.qty == 100
    assert all(c.isin != "INE005E01011" for c in pf.consolidated())
