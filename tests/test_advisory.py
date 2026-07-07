import json
from datetime import date
from pathlib import Path

from app.advisory import apply_status, parse_advisory, parse_alloc
from app.parser import parse_holdings
from app.portfolio import build_portfolio
from app.prices import Quote

FIXDIR = Path(__file__).parent / "fixtures"
ADV = FIXDIR / "sample-advisory.xlsx"
ISIN_MAP = {"INE001A01001": "ALPHAMOT", "INE002B01012": "BETAPH", "INE004D01034": "DELTAB"}
QUOTES = {"DELTAB": Quote(160.0, -1.0)}


def _pf():
    return build_portfolio(parse_holdings(FIXDIR / "sample-holdings.xlsx"), ISIN_MAP, QUOTES, [])


def test_parse_shapes():
    adv = parse_advisory(ADV)
    assert [t.stock for t in adv.targets] == ["Delta Bank", "Alpha Motors"]
    assert adv.targets[0].sector == "Banking"
    assert [e.stock for e in adv.exits] == ["Beta Pharma", "Omega Ghost"]
    assert adv.buys[0].alloc_lo == 100000 and adv.buys[0].alloc_hi == 200000
    assert [m.label for m in adv.schedule] == ["Jul 2026", "Aug 2026"]


def test_parse_alloc():
    assert parse_alloc("₹5–7L") == (500000.0, 700000.0)
    assert parse_alloc("₹4-5L") == (400000.0, 500000.0)


def test_status_pending_review_and_baseline(tmp_path):
    adv = apply_status(parse_advisory(ADV), _pf(), tmp_path, date(2026, 7, 7))
    beta = next(e for e in adv.exits if e.stock == "Beta Pharma")
    omega = next(e for e in adv.exits if e.stock == "Omega Ghost")
    assert beta.status == "PENDING" and beta.source == "auto"
    assert omega.status == "REVIEW"
    bl = json.loads((tmp_path / "advisory-baseline.json").read_text())
    assert bl["exits"]["Beta Pharma"]["baseline_qty"] == 50


def test_status_done_when_position_gone(tmp_path):
    apply_status(parse_advisory(ADV), _pf(), tmp_path, date(2026, 7, 7))   # snapshot baseline
    pf2 = _pf()
    pf2.positions = [p for p in pf2.positions if not p.name.startswith("BETA")]
    adv = apply_status(parse_advisory(ADV), pf2, tmp_path, date(2026, 7, 7))
    assert next(e for e in adv.exits if e.stock == "Beta Pharma").status == "DONE"


def test_manual_override(tmp_path):
    (tmp_path / "rebalance-status.json").write_text(json.dumps({"Omega Ghost": "DONE"}))
    adv = apply_status(parse_advisory(ADV), _pf(), tmp_path, date(2026, 7, 7))
    omega = next(e for e in adv.exits if e.stock == "Omega Ghost")
    assert omega.status == "DONE" and omega.source == "manual"


def test_buy_progress_and_current_month(tmp_path):
    adv = apply_status(parse_advisory(ADV), _pf(), tmp_path, date(2026, 8, 10))
    delta = adv.buys[0]
    assert delta.current_value == 200 * 160.0
    assert delta.progress_pct == 32.0            # 32000 / 100000
    assert [m.is_current for m in adv.schedule] == [False, True]
