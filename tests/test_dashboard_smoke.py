import shutil
from pathlib import Path

from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).parent.parent
FIXDIR = Path(__file__).parent / "fixtures"


def _isolated(tmp_path, monkeypatch, with_advisory=False):
    """Point the app at a throwaway data dir so tests never touch real data."""
    shutil.copy(FIXDIR / "sample-holdings.xlsx", tmp_path / "holdings.xlsx")
    if with_advisory:
        shutil.copy(FIXDIR / "sample-advisory.xlsx", tmp_path / "advisory.xlsx")
    monkeypatch.setenv("INVESTOR_OS_DATA", str(tmp_path))
    return AppTest.from_file(str(ROOT / "app" / "dashboard.py"), default_timeout=60)


def test_overview_renders_without_exceptions(tmp_path, monkeypatch):
    at = _isolated(tmp_path, monkeypatch).run()
    assert not at.exception, at.exception
    assert at.title[0].value == "Paresh Karia — Investor OS"
    body = " ".join(m.value for m in at.markdown)
    assert "Total Value" in body and "₹" in body


def test_holdings_view_renders(tmp_path, monkeypatch):
    at = _isolated(tmp_path, monkeypatch).run()
    at.sidebar.radio[0].set_value("▤ Holdings").run()
    assert not at.exception, at.exception
    assert len(at.dataframe) >= 1
    df = at.dataframe[0].value
    assert "Held By" in df.columns
    assert (df["Flags"].str.contains("cost").any())   # BETA row flagged


def test_rebalance_view_renders(tmp_path, monkeypatch):
    at = _isolated(tmp_path, monkeypatch, with_advisory=True).run()
    at.sidebar.radio[0].set_value("⚖ Rebalance").run()
    assert not at.exception, at.exception
    assert len(at.tabs) == 4
    assert len(at.dataframe) >= 2      # exits table + target table


def test_brief_and_profile_views_render(tmp_path, monkeypatch):
    at = _isolated(tmp_path, monkeypatch).run()
    at.sidebar.radio[0].set_value("⚡ Morning Brief").run()
    assert not at.exception, at.exception
    at.sidebar.radio[0].set_value("👤 Investor Profile").run()
    assert not at.exception, at.exception
