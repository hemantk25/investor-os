from pathlib import Path
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
