from pathlib import Path

from app import holdings_ledger as ledger
from app import view_models as vm
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


def test_manual_suppressed_when_excel_has_same(tmp_path):
    duplicate_id = ledger.add_manual(tmp_path, {"member": "PK", "name": "Alpha Manual",
                                                "isin": "INE001A01001", "symbol": "ALPHAMOT",
                                                "qty": "10", "avg_cost": "200"})
    other_member_id = ledger.add_manual(tmp_path, {"member": "MK", "name": "Alpha Manual MK",
                                                   "isin": "INE001A01001",
                                                   "symbol": "ALPHAMOT",
                                                   "qty": "7", "avg_cost": "210"})

    pr = ledger.apply_events(parse_holdings(FIX), tmp_path)
    pk_alpha = [h for h in pr.holdings if h.member == "PK" and h.isin == "INE001A01001"]
    mk_alpha = [h for h in pr.holdings if h.member == "MK" and h.isin == "INE001A01001"]

    assert len(pk_alpha) == 1
    assert getattr(pk_alpha[0], "source", "excel") == "excel"
    assert pk_alpha[0].qty == 100
    assert len(mk_alpha) == 1
    assert getattr(mk_alpha[0], "source", "") == "manual"
    assert any("suppressed" in item for item in pr.skipped)
    assert "MK" in pr.members

    pf = build_portfolio(pr, {**ISIN, "INE001A01001": "ALPHAMOT"}, Q, [])
    ctx = vm.holdings(pf, None, "", ledger.list_manual(tmp_path))
    manual = {item["id"]: item for item in ctx["manual_items"]}
    assert manual[duplicate_id]["in_excel"] is True
    assert manual[other_member_id]["in_excel"] is False


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
