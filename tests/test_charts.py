from app.charts import area_path, alloc_segments, CHART_COLORS
from app.parser import parse_holdings
from app.prices import Quote
from app.portfolio import build_portfolio
from pathlib import Path

FIX = Path(__file__).parent / "fixtures" / "sample-holdings.xlsx"


def test_area_path_two_points():
    p = area_path([100.0, 200.0], w=1000, h=250)
    assert p["line"].startswith("M") and p["area"].endswith("Z")


def test_area_path_flat_when_single():
    p = area_path([100.0])
    assert "L1000" in p["line"] or p["line"].count(",") >= 1  # a horizontal line renders


def test_alloc_segments_order_and_pct():
    pf = build_portfolio(parse_holdings(FIX),
                         {"INE001A01001": "ALPHAMOT"}, {"ALPHAMOT": Quote(300.0, 2.0)}, [])
    segs = alloc_segments(pf.totals())
    assert [s["label"] for s in segs][0] == "Direct Equity"
    assert all(0 <= s["pct"] <= 100 for s in segs)
    assert segs[0]["color"] == CHART_COLORS[0]
    assert abs(sum(s["pct"] for s in segs) - 100) < 0.5
