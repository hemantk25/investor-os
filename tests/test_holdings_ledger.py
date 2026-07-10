from pathlib import Path

from app import holdings_ledger as ledger
from app.parser import parse_holdings
from app.portfolio import build_portfolio
from app.prices import Quote


FIX = Path(__file__).parent / "fixtures" / "sample-holdings.xlsx"
ISIN = {"INE001A01001": "ALPHAMOT", "INE004D01034": "DELTAB",
        "INE005E01011": "EPSILON"}
Q = {"ALPHAMOT": Quote(300.0, 2.0), "DELTAB": Quote(160.0, -1.0),
     "EPSILON": Quote(50.0, 1.5)}


def _portfolio_with_events(tmp_path):
    pr = ledger.apply_events(parse_holdings(FIX), tmp_path)
    isin = dict(ISIN)
    isin.update(ledger.symbol_map(tmp_path))
    return build_portfolio(pr, isin, Q, [])


def test_manual_holding_layers_on_top_of_excel(tmp_path):
    event_id = ledger.add_manual(tmp_path, {"member": "PK", "name": "Epsilon Tech",
                                           "isin": "INE005E01011", "symbol": "EPSILON",
                                           "qty": "10", "avg_cost": "40",
                                           "price": "45"})
    assert event_id
    pf = _portfolio_with_events(tmp_path)
    eps = next(c for c in pf.consolidated("PK") if c.isin == "INE005E01011")
    assert eps.qty == 10
    assert eps.source == "manual"
    assert eps.value == 10 * 50


def test_sell_event_reduces_excel_quantity(tmp_path):
    ledger.add_sell(tmp_path, {"member": "PK", "isin": "INE001A01001", "qty": "25"})
    pf = _portfolio_with_events(tmp_path)
    alpha = next(c for c in pf.consolidated("PK") if c.isin == "INE001A01001")
    assert alpha.qty == 75


def test_manual_edit_delete_and_snapshots(tmp_path):
    event_id = ledger.add_manual(tmp_path, {"member": "PK", "name": "Epsilon Tech",
                                           "isin": "INE005E01011", "symbol": "EPSILON",
                                           "qty": "10"})
    ledger.edit_manual(tmp_path, event_id, {"member": "CK", "name": "Epsilon Tech",
                                           "isin": "INE005E01011", "symbol": "EPSILON",
                                           "qty": "12", "avg_cost": "41"})
    assert ledger.list_manual(tmp_path)[0]["member"] == "CK"
    pf = _portfolio_with_events(tmp_path)
    assert ledger.record_snapshot(tmp_path, pf) == 3
    assert ledger.snapshot_count(tmp_path) == 3
    ledger.delete_manual(tmp_path, event_id)
    assert ledger.list_manual(tmp_path) == []
