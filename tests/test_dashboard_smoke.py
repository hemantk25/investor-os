import shutil
from pathlib import Path

from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).parent.parent
FIX = Path(__file__).parent / "fixtures" / "sample-holdings.xlsx"


def _prepare_data():
    data = ROOT / "data"
    data.mkdir(exist_ok=True)
    shutil.copy(FIX, data / "holdings.xlsx")


def test_overview_renders_without_exceptions():
    _prepare_data()
    at = AppTest.from_file(str(ROOT / "app" / "dashboard.py"), default_timeout=60).run()
    assert not at.exception, at.exception
    assert at.title[0].value == "Paresh Karia — Investor OS"
    # Overview is the default view: 4 hero metrics must render
    assert len(at.metric) == 4
    assert at.metric[0].label == "Total Value"
    assert at.metric[0].value.startswith("₹")


def test_holdings_view_renders():
    _prepare_data()
    at = AppTest.from_file(str(ROOT / "app" / "dashboard.py"), default_timeout=60).run()
    at.sidebar.radio[0].set_value("▤ Holdings").run()
    assert not at.exception, at.exception
    assert len(at.dataframe) >= 1
    df = at.dataframe[0].value
    assert "Held By" in df.columns
    assert (df["Flags"].str.contains("cost").any())   # BETA row flagged
