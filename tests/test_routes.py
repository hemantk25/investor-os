import importlib
import shutil
from pathlib import Path

import pytest

from app.prices import Quote


FIXDIR = Path(__file__).parent / "fixtures"
ISIN_MAP = {"INE001A01001": "ALPHAMOT", "INE002B01012": "BETAPH",
            "INE004D01034": "DELTAB"}
QUOTES = {"ALPHAMOT": Quote(300.0, 2.0), "DELTAB": Quote(160.0, -1.0)}
HISTORY = {"ALPHAMOT": [200.0, 250.0, 300.0],
           "DELTAB": [140.0, 150.0, 160.0]}
MARKET_QUOTES = {"^NSEI": Quote(24000.0, 0.5), "INR=X": Quote(83.25, -0.1)}


@pytest.fixture()
def client(tmp_path, monkeypatch):
    shutil.copy(FIXDIR / "sample-holdings.xlsx", tmp_path / "holdings.xlsx")
    shutil.copy(FIXDIR / "sample-advisory.xlsx", tmp_path / "advisory.xlsx")
    monkeypatch.setenv("INVESTOR_OS_DATA", str(tmp_path))

    import app.server as srv
    srv = importlib.reload(srv)
    monkeypatch.setattr(srv.mapping, "ensure_map", lambda data: ISIN_MAP)
    monkeypatch.setattr(srv.prices, "fetch_quotes", lambda symbols: QUOTES)
    monkeypatch.setattr(srv.prices, "fetch_history", lambda symbols, period: HISTORY)
    monkeypatch.setattr(srv.prices, "fetch_market_quotes", lambda symbols: MARKET_QUOTES)

    from app import brief as bmod
    monkeypatch.setattr(bmod, "find_claude", lambda: None)
    monkeypatch.setattr(bmod, "generate_brief",
                        lambda pf, base_dir: Path(base_dir) / "briefs" / "fake.md")

    c = srv.create_app().test_client()
    c.data_dir = tmp_path
    return c


def test_overview_ok(client):
    r = client.get("/")
    assert r.status_code == 200
    assert b"Market Pulse" in r.data
    assert b"Nifty 50" in r.data
    assert b"Current Value" in r.data
    assert b"Portfolio Value" not in r.data
    assert b"Portfolio Summary" in r.data
    assert b"Asset-Class Split" in r.data
    assert b"Family Split" in r.data
    assert b"Watchlist" in r.data


def test_overview_empty_data(monkeypatch, tmp_path):
    monkeypatch.setenv("INVESTOR_OS_DATA", str(tmp_path))
    import app.server as srv
    srv = importlib.reload(srv)
    r = srv.create_app().test_client().get("/")
    assert r.status_code == 200
    assert b"No holdings yet" in r.data


def test_member_filter_changes_page(client):
    r = client.get("/?member=CK&range=1M")
    assert r.status_code == 200
    assert b"Current Value" in r.data


def test_holdings_and_search(client):
    r = client.get("/holdings")
    assert r.status_code == 200
    assert b"Portfolio Holdings" in r.data
    r = client.get("/holdings?q=alpha")
    assert r.status_code == 200
    assert b"Alpha Motors" in r.data


def test_holdings_manual_and_sell_routes(client):
    r = client.post("/holdings/manual", data={"member": "PK",
                                              "name": "Epsilon Tech",
                                              "isin": "INE005E01011",
                                              "symbol": "EPSILON",
                                              "qty": "10",
                                              "avg_cost": "40",
                                              "price": "45"},
                    follow_redirects=True)
    assert r.status_code == 200
    assert b"Epsilon Tech" in r.data

    from app import holdings_ledger as ledger
    item = ledger.list_manual(client.data_dir)[0]
    r = client.post(f"/holdings/manual/{item['id']}/edit",
                    data={"member": "CK", "name": "Epsilon Tech",
                          "isin": "INE005E01011", "symbol": "EPSILON",
                          "qty": "12", "avg_cost": "41", "price": "46"},
                    follow_redirects=True)
    assert r.status_code == 200

    r = client.post("/holdings/events/sell", data={"member": "PK",
                                                   "isin": "INE001A01001",
                                                   "qty": "5"},
                    follow_redirects=True)
    assert r.status_code == 200

    r = client.post(f"/holdings/manual/{item['id']}/delete", follow_redirects=True)
    assert r.status_code == 200


def test_watchlist_filters_and_preview(client):
    r = client.get("/watchlist?market=UAE")
    assert r.status_code == 200
    assert b"DFM General Index" in r.data
    assert b"Watchlist Workspace" in r.data


def test_watchlist_add_import_export_delete(client):
    r = client.post("/watchlist/items", data={"symbol": "NASDAQ:MSFT",
                                              "name": "Microsoft",
                                              "market": "US",
                                              "group": "Custom",
                                              "member": "PK"},
                    follow_redirects=True)
    assert r.status_code == 200
    assert b"Microsoft" in r.data

    r = client.post("/watchlist/import", data={"symbols": "NASDAQ:AAPL,NSE:RELIANCE",
                                               "market": "US",
                                               "group": "Custom",
                                               "member": "All"},
                    follow_redirects=True)
    assert r.status_code == 200
    assert b"NASDAQ:AAPL" in r.data

    r = client.get("/watchlist/export?market=US&group=Custom")
    assert r.status_code == 200
    assert b"NASDAQ:MSFT" in r.data and b"NASDAQ:AAPL" in r.data

    from app import watchlist as wmod
    item = next(i for i in wmod.load(client.data_dir) if i["symbol"] == "NASDAQ:MSFT")
    r = client.post(f"/watchlist/items/{item['id']}/delete", data={"market_filter": "US",
                                                                   "group_filter": "Custom"},
                    follow_redirects=True)
    assert r.status_code == 200
    assert b"Microsoft" not in r.data


def test_watchlist_board_open_and_close(client):
    r = client.post("/watchlist/boards", data={"title": "US Tech",
                                               "market": "US",
                                               "category": "Technology",
                                               "subcategory": "Tech"},
                    follow_redirects=True)
    assert r.status_code == 200
    assert b"US Tech" in r.data

    from app import watchlist as wmod
    board = next(b for b in wmod.open_boards(client.data_dir) if b["title"] == "US Tech")
    r = client.post(f"/watchlist/boards/{board['id']}/close", follow_redirects=True)
    assert r.status_code == 200
    assert b"US Tech" not in r.data


def test_rebalance_tabs(client):
    for tab in ("exits", "buys", "schedule"):
        r = client.get(f"/rebalance?tab={tab}")
        assert r.status_code == 200
    assert b"Execution Schedule" in client.get("/rebalance?tab=schedule").data


def test_brief_and_profile(client):
    assert client.get("/brief").status_code == 200
    assert client.get("/profile").status_code == 200


def test_brief_generate_redirects(client):
    r = client.post("/brief/generate")
    assert r.status_code in (302, 303)


def test_news_page_lists_markets(client):
    r = client.get("/news")
    assert r.status_code == 200
    for m in ("India", "US", "UAE", "Canada", "Global"):
        assert m.encode() in r.data


def test_news_page_market_filter(client):
    r = client.get("/news?market=India")
    assert r.status_code == 200


def test_news_page_mine_filter(client):
    r = client.get("/news?mine=1")
    assert r.status_code == 200


def test_news_refresh_redirects(client, monkeypatch):
    import app.news as nmod
    called = {}

    def fake_fetch_all(data_dir, pf):
        called["ok"] = True
        return {"holdings": 0, "markets": 0}

    monkeypatch.setattr(nmod, "fetch_all", fake_fetch_all)
    r = client.post("/news/refresh")
    assert r.status_code in (302, 303)
    assert called.get("ok") is True


def test_nav_order_news_between_brief_and_rebalance(client):
    html = client.get("/").data.decode()
    assert html.index("Morning Brief") < html.index(">News<") < html.index("Rebalance")


def test_profile_removed_from_nav_but_route_still_works(client):
    html = client.get("/").data.decode()
    assert "Investor Profile" not in html
    assert client.get("/profile").status_code == 200


def test_goal_placeholder_route(client):
    r = client.get("/goal")
    assert r.status_code == 200
