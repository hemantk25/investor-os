import json
from pathlib import Path

from app.parser import parse_holdings
from app.portfolio import build_portfolio, fmt_inr, fmt_pct, fmt_short, load_extras
from app.prices import Quote

FIX = Path(__file__).parent / "fixtures" / "sample-holdings.xlsx"
ISIN_MAP = {"INE001A01001": "ALPHAMOT", "INE002B01012": "BETAPH", "INE004D01034": "DELTAB"}
QUOTES = {"ALPHAMOT": Quote(300.0, 2.0), "DELTAB": Quote(160.0, -1.0)}   # BETAPH: no quote


def _pf(extras=None):
    return build_portfolio(parse_holdings(FIX), ISIN_MAP, QUOTES, extras or [])


def test_live_vs_fallback_prices():
    pf = _pf()
    alpha = next(p for p in pf.positions if p.name.startswith("ALPHA") and p.member == "PK")
    beta = next(p for p in pf.positions if p.name.startswith("BETA"))
    gamma = next(p for p in pf.positions if p.name.startswith("GAMMA"))
    assert alpha.price == 300.0 and alpha.price_live
    assert beta.price == 400.0 and not beta.price_live      # mapped but no quote -> excel cmp
    assert gamma.nse_symbol is None and gamma.price == 10.0  # unmapped -> excel cmp


def test_consolidation_weighted_avg_and_held_by():
    cons = _pf().consolidated()
    alpha = next(c for c in cons if c.name.startswith("ALPHA"))
    assert alpha.qty == 150
    assert round(alpha.avg_cost, 2) == round((100 * 200 + 50 * 220) / 150, 2)
    assert alpha.held_by == ["CK", "PK"]


def test_member_filter_totals():
    pf = _pf()
    t_ck = pf.totals("CK")
    assert t_ck.equity_value == 50 * 300.0 + 200 * 160.0
    t_all = pf.totals()
    assert t_all.equity_value == 150 * 300.0 + 50 * 400.0 + 30 * 10.0 + 200 * 160.0


def test_unknown_cost_excluded_from_pl():
    t = _pf().totals()
    # invested = alpha(100*200 + 50*220) + gamma(30*12) + delta(200*100); beta excluded
    assert t.invested_known == 20000 + 11000 + 360 + 20000


def test_extras_merge(tmp_path):
    p = tmp_path / "extras.json"
    p.write_text(json.dumps([{"member": "PK", "label": "Gold SGB", "asset_class": "gold",
                              "value": 100000, "invested": 80000}]), encoding="utf-8")
    pf = _pf(load_extras(p))
    assert pf.totals().extras_by_class["gold"] == 100000
    assert pf.totals("CK").extras_by_class == {}


def test_formats():
    assert fmt_short(24087460) == "₹2.41 Cr"
    assert fmt_short(2460000) == "₹24.6 L"
    assert fmt_inr(1234567) == "₹12,34,567"
    assert fmt_pct(22.6) == "+22.6%"
