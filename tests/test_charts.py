from app.charts import area_path, alloc_segments, CHART_COLORS, donut_chart
from app.parser import parse_holdings
from app.prices import Quote
from app.portfolio import build_portfolio
from pathlib import Path

FIX = Path(__file__).parent / "fixtures" / "sample-holdings.xlsx"


def _nonmarket(pf):
    t = pf.totals()
    return sum(v for k, v in t.extras_by_class.items())


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


def test_donut_chart_builds_gradient():
    chart = donut_chart([{"label": "Equity", "value": 75.0, "color": "#111111"},
                         {"label": "Cash", "value": 25.0, "color": "#222222"}])
    assert chart["gradient"].startswith("conic-gradient(")
    assert [s["label"] for s in chart["segments"]] == ["Equity", "Cash"]
    assert round(sum(s["pct"] for s in chart["segments"])) == 100


def test_portfolio_series_reconstructs():
    from app.charts import portfolio_series
    from app.parser import parse_holdings
    from app.prices import Quote
    from app.portfolio import build_portfolio
    from pathlib import Path
    fix = Path(__file__).parent / "fixtures" / "sample-holdings.xlsx"
    pf = build_portfolio(parse_holdings(fix), {"INE001A01001": "ALPHAMOT"},
                         {"ALPHAMOT": Quote(300.0, 2.0)}, [])
    hist = {"ALPHAMOT": [200.0, 250.0, 300.0]}   # ALPHA held 150 qty consolidated
    s = portfolio_series(pf, None, hist)
    assert len(s) == 3 and s[-1] > s[0]
    assert abs(s[2] - 150 * 300.0 - _nonmarket(pf)) < 1  # ends at current-price value + flat non-market
