from pathlib import Path

from app.parser import parse_holdings

FIX = Path(__file__).parent / "fixtures" / "sample-holdings.xlsx"


def test_members_detected():
    pr = parse_holdings(FIX)
    assert pr.members == ["PK", "CK"]


def test_row_counts_and_skips():
    pr = parse_holdings(FIX)
    assert len(pr.holdings) == 5            # 3 valid PK + 2 CK (junk row skipped)
    assert any("JUNK" in s for s in pr.skipped)


def test_missing_avg_cost_is_none():
    pr = parse_holdings(FIX)
    beta = next(h for h in pr.holdings if h.name.startswith("BETA"))
    assert beta.avg_cost is None
    assert beta.qty == 50 and beta.excel_cmp == 400.0


def test_day_pct_normalised_to_percent():
    pr = parse_holdings(FIX)
    alpha_pk = next(h for h in pr.holdings if h.member == "PK" and h.name.startswith("ALPHA"))
    assert alpha_pk.excel_day_pct == 1.0    # 0.01 fraction -> 1.0%
