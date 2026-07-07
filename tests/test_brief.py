from datetime import date
from pathlib import Path

import app.brief as brief
from app.brief import build_prompt, find_claude, portfolio_snapshot
from app.parser import parse_holdings
from app.portfolio import build_portfolio
from app.prices import Quote

FIX = Path(__file__).parent / "fixtures" / "sample-holdings.xlsx"


def _pf():
    return build_portfolio(parse_holdings(FIX),
                           {"INE001A01001": "ALPHAMOT"}, {"ALPHAMOT": Quote(300.0, 2.0)}, [])


def test_snapshot_compact_and_serialisable():
    import json
    snap = portfolio_snapshot(_pf())
    s = json.dumps(snap)
    assert "ALPHA" in s.upper() and snap["total_value"] > 0
    assert set(snap) == {"date_generated", "total_value", "members", "positions",
                         "extras_by_class", "movers"}


def test_prompt_contains_rules_and_sections():
    p = build_prompt("MY ONE PAGER RULES", portfolio_snapshot(_pf()), date(2026, 7, 8))
    assert "MY ONE PAGER RULES" in p
    for sec in ["MARKETS OVERNIGHT", "IMPACT ON YOUR PORTFOLIO", "SUGGESTED ACTIONS"]:
        assert sec in p
    assert "8 July 2026" in p


def test_find_claude_missing(monkeypatch):
    monkeypatch.setattr(brief.shutil, "which", lambda _: None)
    assert find_claude() is None
