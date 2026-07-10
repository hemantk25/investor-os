from pathlib import Path
from datetime import datetime, timedelta
from app.parser import parse_holdings
from app.prices import Quote
from app.portfolio import build_portfolio
from app import view_models as vm

FIX = Path(__file__).parent / "fixtures" / "sample-holdings.xlsx"
ISIN = {"INE001A01001": "ALPHAMOT", "INE004D01034": "DELTAB"}
Q = {"ALPHAMOT": Quote(300.0, 2.0), "DELTAB": Quote(160.0, -1.0)}


def _pf():
    return build_portfolio(parse_holdings(FIX), ISIN, Q, [])


def test_common_members_and_active():
    c = vm.common(_pf(), "overview", None)
    assert c["members"] == ["PK", "CK"] and c["active"] == "overview"
    assert "live prices" in c["freshness"]


def test_overview_cards_and_movers():
    o = vm.overview(_pf(), None, "6M")
    labels = [c["label"] for c in o["cards"]]
    assert labels == ["Current Value", "Total Investment", "Total Return", "Day P/L",
                      "Cash / Unallocated"]
    assert o["alloc"] and o["movers"]
    assert o["asset_donut"]["segments"]
    assert o["family_donut"]["title"] == "Family Split"
    assert o["market_metrics"][0]["label"] == "Nifty 50"
    assert o["range"] == "6M"


def test_selected_member_family_donut():
    o = vm.overview(_pf(), "CK", "6M")
    labels = [s["label"] for s in o["family_donut"]["segments"]]
    assert labels == ["CK", "Rest of Family"]


def test_market_metrics_missing_quotes_are_safe():
    metrics = vm.market_metrics({})
    assert metrics
    assert all(m["value"] == "--" for m in metrics)
    assert all(m["change"] == "--" for m in metrics)


def test_holdings_groups_and_search():
    h = vm.holdings(_pf(), None, "delta")
    names = [r["name"] for g in h["groups"] for r in g["rows"]]
    assert any("Delta" in n for n in names) and not any("Alpha" in n for n in names)


def test_news_ctx_empty_defaults(tmp_path):
    from app import news
    ctx = vm.news_ctx(tmp_path, None, False)
    assert ctx["items"] == []
    assert ctx["market"] == "All"
    assert ctx["mine"] is False
    assert ctx["markets"] == ["All"] + news.MARKETS
    assert ctx["fetched"] is None


def test_news_ctx_items_have_ago_and_filters(tmp_path):
    from app import news, storage
    now = storage.now_iso()
    with storage.connect(tmp_path) as con:
        con.execute(
            """
            INSERT INTO news_items(url_hash, title, url, publisher, published_at, market,
                                    isin, holding_name, fetched_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("h1", "Alpha rallies", "https://example.com/a1", "Mint", None, "India",
             "INE001A01001", "Alpha Motors", now),
        )
        con.commit()

    ctx = vm.news_ctx(tmp_path, "India", False)
    assert ctx["market"] == "India"
    assert len(ctx["items"]) == 1
    item = ctx["items"][0]
    assert item["title"] == "Alpha rallies"
    assert item["url"] == "https://example.com/a1"
    assert item["publisher"] == "Mint"
    assert item["holding_name"] == "Alpha Motors"
    assert "ago" in item["ago"]
    assert ctx["fetched"] is not None

    mine_ctx = vm.news_ctx(tmp_path, None, True)
    assert len(mine_ctx["items"]) == 1
    assert mine_ctx["market"] == "All"


def test_ago_boundaries():
    """Test _ago function with various timestamp sources and ages.

    Tests timezone handling: published_at (UTC) vs fetched_at (local).
    """
    # Test 1: published_at exactly 2 hours old (UTC)
    utc_2h_ago = (datetime.utcnow() - timedelta(hours=2)).isoformat()
    item = {"published_at": utc_2h_ago}
    result = vm._ago(item)
    assert result == "2h ago", f"Expected '2h ago', got '{result}'"

    # Test 2: published_at 3 days old (UTC)
    utc_3d_ago = (datetime.utcnow() - timedelta(days=3)).isoformat()
    item = {"published_at": utc_3d_ago}
    result = vm._ago(item)
    assert result == "3d ago", f"Expected '3d ago', got '{result}'"

    # Test 3: malformed timestamp string
    item = {"published_at": "not-a-valid-iso-string"}
    result = vm._ago(item)
    assert result == "", f"Expected empty string for malformed timestamp, got '{result}'"

    # Test 4: None + None (both missing)
    item = {"published_at": None, "fetched_at": None}
    result = vm._ago(item)
    assert result == "", f"Expected empty string when both timestamps missing, got '{result}'"

    # Test 5: published_at = utcnow−10min (UTC) should yield "10m ago" (with tolerance 9m-11m)
    utc_10m_ago = (datetime.utcnow() - timedelta(minutes=10)).isoformat()
    item = {"published_at": utc_10m_ago}
    result = vm._ago(item)
    # Allow 9m, 10m, or 11m due to timing variations
    assert result in ("9m ago", "10m ago", "11m ago"), \
        f"Expected '9m/10m/11m ago' for 10min old UTC timestamp, got '{result}'"

    # Test 6: fetched_at (local time) should use datetime.now() comparison
    local_1h_ago = (datetime.now() - timedelta(hours=1)).isoformat()
    item = {"fetched_at": local_1h_ago}
    result = vm._ago(item)
    assert result == "1h ago", f"Expected '1h ago' for local 1h old timestamp, got '{result}'"

    # Test 7: Negative time (future timestamp) should clamp to "1m ago"
    future = (datetime.utcnow() + timedelta(hours=1)).isoformat()
    item = {"published_at": future}
    result = vm._ago(item)
    assert result == "1m ago", f"Expected '1m ago' for future timestamp (clamped), got '{result}'"
