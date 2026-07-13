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
    # No network for the fetchers wired into run_refresh.
    monkeypatch.setattr(refresh.prices, "fetch_history", lambda syms, period="6mo", **kw: {})
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
    monkeypatch.setattr(refresh.prices, "fetch_history", lambda syms, period="6mo", **kw: {})

    def boom(*args, **kwargs):
        raise RuntimeError("network down")

    monkeypatch.setattr(refresh.goal, "refresh_security_meta", boom)
    monkeypatch.setattr(refresh.news, "fetch_all", boom)

    result = refresh.run_refresh(tmp_path, pf)

    assert result["security_meta"] == 0
    assert result["news_items"] == 0
    assert result["portfolio_snapshots"] == 3
    assert any("security metadata" in w for w in result["warnings"])
    assert any("news" in w for w in result["warnings"])


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


def _mock_all_network(monkeypatch):
    monkeypatch.setattr(refresh.prices, "fetch_market_quotes", lambda symbols: {})
    monkeypatch.setattr(refresh.prices, "fetch_history", lambda syms, period="6mo", **kw: {})
    monkeypatch.setattr(refresh.prices, "fetch_quotes", lambda symbols, **kw: {})
    monkeypatch.setattr(refresh.mapping, "ensure_map", lambda data, **kw: {})
    monkeypatch.setattr(refresh.goal, "refresh_security_meta", lambda data_dir, pf, **kw: 0)
    monkeypatch.setattr(refresh.news, "fetch_all", lambda data_dir, pf: {"holdings": 0, "markets": 0})


def test_report_fields_from_dropbox_file(tmp_path, monkeypatch):
    _mock_all_network(monkeypatch)
    (tmp_path / "holdings").mkdir()
    shutil.copy(FIX, tmp_path / "holdings" / "latest.xlsx")

    report = refresh.run_refresh(tmp_path)

    assert report["holdings_file"] == "latest.xlsx"
    assert report["rows"] > 0
    assert isinstance(report["skipped"], int)
    assert report["portfolio_snapshots"] > 0
    assert isinstance(report["warnings"], list)
    text = refresh.format_report(report)
    assert "latest.xlsx" in text and "Warnings" in text


def test_warning_old_holdings_file(tmp_path, monkeypatch):
    import os, time
    _mock_all_network(monkeypatch)
    (tmp_path / "holdings").mkdir()
    dest = tmp_path / "holdings" / "old.xlsx"
    shutil.copy(FIX, dest)
    t = time.time() - 20 * 86400
    os.utime(dest, (t, t))

    report = refresh.run_refresh(tmp_path)
    assert any("days old" in w for w in report["warnings"])


def test_warning_high_skip_ratio(tmp_path, monkeypatch):
    from datetime import datetime
    from app import datafiles as dfmod
    from app.parser import ParseResult, Holding
    _mock_all_network(monkeypatch)
    holdings = [Holding(member="PK", name="A", icici_symbol="A", isin="INE001A01001",
                        qty=1, avg_cost=1.0, excel_cmp=1.0, excel_day_pct=None)]
    pr = ParseResult(holdings=holdings, skipped=["x"] * 100, asof=datetime.now(), members=["PK"])
    fake_path = tmp_path / "holdings" / "partial.xlsx"
    fake_path.parent.mkdir()
    fake_path.write_bytes(b"x")
    monkeypatch.setattr(refresh.datafiles, "resolve_and_parse_holdings",
                        lambda d: (pr, fake_path, []))

    report = refresh.run_refresh(tmp_path)
    assert any("incomplete export" in w for w in report["warnings"])


def test_no_holdings_warns(tmp_path, monkeypatch):
    _mock_all_network(monkeypatch)
    report = refresh.run_refresh(tmp_path)
    assert report["holdings_file"] is None
    assert any("no holdings file" in w for w in report["warnings"])
