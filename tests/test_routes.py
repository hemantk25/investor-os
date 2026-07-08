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

    from app import brief as bmod
    monkeypatch.setattr(bmod, "find_claude", lambda: None)
    monkeypatch.setattr(bmod, "generate_brief",
                        lambda pf, base_dir: Path(base_dir) / "briefs" / "fake.md")

    return srv.create_app().test_client()


def test_overview_ok(client):
    r = client.get("/")
    assert r.status_code == 200
    assert b"Total Value" in r.data
    assert b"Portfolio Value" in r.data


def test_member_filter_changes_page(client):
    r = client.get("/?member=CK&range=1M")
    assert r.status_code == 200
    assert b"Total Value" in r.data


def test_holdings_and_search(client):
    r = client.get("/holdings")
    assert r.status_code == 200
    assert b"Portfolio Holdings" in r.data
    r = client.get("/holdings?q=alpha")
    assert r.status_code == 200
    assert b"Alpha Motors" in r.data


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
