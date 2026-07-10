from __future__ import annotations

from datetime import date, timedelta
from types import SimpleNamespace

import yfinance

from app import goal as goal_mod
from app import storage


# ---------------------------------------------------------------------------
# load_goal: seed + baseline immutability
# ---------------------------------------------------------------------------

def test_seed_and_baseline(tmp_path):
    g = goal_mod.load_goal(tmp_path, current_total=48_000_000)

    assert (tmp_path / "goal.json").exists()
    assert g["target_value"] == 200000000
    assert g["target_date"] == "2031-07-31"
    assert g["expected_cagr_pct"] == 16.0
    assert g["sip_monthly"] == 500000
    assert g["bands_pct"] == {"large": 40, "mid": 40, "small": 20}
    assert g["small_cap_max_pct"] == 20
    assert g["cap_large_min_cr"] == 100000
    assert g["cap_mid_min_cr"] == 33000
    assert g["baseline_value"] == 48_000_000
    assert g["baseline_date"] == date.today().isoformat()

    # A second call with a different total must NOT move the baseline.
    g2 = goal_mod.load_goal(tmp_path, current_total=99_000_000)
    assert g2["baseline_value"] == 48_000_000
    assert g2["baseline_date"] == g["baseline_date"]


def test_load_goal_unparseable_returns_defaults_without_writing(tmp_path):
    path = tmp_path / "goal.json"
    path.write_text("{not valid json", encoding="utf-8")
    before = path.read_text(encoding="utf-8")

    g = goal_mod.load_goal(tmp_path, current_total=1_000_000)

    assert "error" in g
    assert g["target_value"] == 200000000
    assert g["baseline_value"] is None
    # file must be untouched (not overwritten with defaults)
    assert path.read_text(encoding="utf-8") == before


# ---------------------------------------------------------------------------
# required_value / required_series
# ---------------------------------------------------------------------------

def test_required_value_no_time():
    g = {"baseline_value": 1e8, "baseline_date": "2026-01-01",
         "expected_cagr_pct": 16.0, "sip_monthly": 500000}
    on_date = date(2026, 1, 1)
    assert goal_mod.required_value(g, on_date) == g["baseline_value"]


def test_required_value_one_year():
    t0 = date(2026, 1, 1)
    on_date = t0 + timedelta(days=365)
    g = {"baseline_value": 1e8, "baseline_date": t0.isoformat(),
         "expected_cagr_pct": 16.0, "sip_monthly": 500000}

    r = (1.16) ** (1 / 12) - 1
    m = (on_date - t0).days / 30.4375
    expected = 1e8 * (1 + r) ** m + 500000 * (((1 + r) ** m - 1) / r)

    result = goal_mod.required_value(g, on_date)
    assert abs(result - expected) < 1


def test_required_series_baseline_day_gives_identical_points():
    g = {"baseline_value": 1e8, "baseline_date": "2026-01-01",
         "expected_cagr_pct": 16.0, "sip_monthly": 500000}
    series = goal_mod.required_series(g, date(2026, 1, 1), points=2)
    assert len(series) == 2
    assert series[0] == series[1]
    assert series[0][0] == "2026-01-01"
    assert series[0][1] == g["baseline_value"]


def test_required_series_increasing_over_time():
    g = {"baseline_value": 1e8, "baseline_date": "2026-01-01",
         "expected_cagr_pct": 16.0, "sip_monthly": 500000}
    series = goal_mod.required_series(g, date(2027, 1, 1), points=6)
    assert len(series) == 6
    values = [v for _, v in series]
    assert values == sorted(values)
    assert values[0] == g["baseline_value"]


# ---------------------------------------------------------------------------
# implied_cagr
# ---------------------------------------------------------------------------

def test_implied_cagr_roundtrip():
    today = date(2026, 1, 1)
    target_date = date(2027, 1, 1)
    current_value = 1e8
    sip = 500000
    cagr = 16.0

    r = (1 + cagr / 100) ** (1 / 12) - 1
    n = (target_date - today).days / 30.4375
    target = current_value * (1 + r) ** n + sip * (((1 + r) ** n - 1) / r)

    g = {"target_value": target, "target_date": target_date.isoformat(), "sip_monthly": sip}
    implied = goal_mod.implied_cagr(g, current_value, today)
    assert implied is not None
    assert abs(implied - cagr) <= 0.2


def test_implied_cagr_already_past_target_is_zero():
    today = date(2026, 1, 1)
    target_date = date(2027, 1, 1)
    current_value = 1e8
    g = {"target_value": current_value, "target_date": target_date.isoformat(),
         "sip_monthly": 500000}
    assert goal_mod.implied_cagr(g, current_value, today) == 0.0


def test_implied_cagr_absurd_target_one_month_is_none():
    today = date(2026, 1, 1)
    target_date = today + timedelta(days=30)
    g = {"target_value": 1e18, "target_date": target_date.isoformat(), "sip_monthly": 500000}
    assert goal_mod.implied_cagr(g, 1e8, today) is None


# ---------------------------------------------------------------------------
# classify_caps
# ---------------------------------------------------------------------------

def test_classify_caps():
    positions = [
        SimpleNamespace(nse_symbol="LARGECO", value=6_000_000),
        SimpleNamespace(nse_symbol="MIDCO", value=3_000_000),
        SimpleNamespace(nse_symbol="SMALLCO", value=3_000_000),
        SimpleNamespace(nse_symbol="UNKCO", value=1_000_000),
    ]
    meta = {
        "LARGECO": {"market_cap": 2e12},
        "MIDCO": {"market_cap": 5e11},
        "SMALLCO": {"market_cap": 1e11},
        # UNKCO deliberately missing from meta
    }
    g = dict(goal_mod.DEFAULT_GOAL)

    result = goal_mod.classify_caps(positions, meta, g)

    assert result["large"]["value"] == 6_000_000
    assert result["mid"]["value"] == 3_000_000
    assert result["small"]["value"] == 3_000_000
    assert result["unclassified"]["value"] == 1_000_000

    classified_pct = result["large"]["pct"] + result["mid"]["pct"] + result["small"]["pct"]
    assert abs(classified_pct - 100) < 1e-6

    # small = 3M / 12M classified = 25% > small_cap_max_pct (20) -> breach
    assert result["small"]["pct"] == 25.0
    assert result["small_breach"] is True


def test_classify_caps_no_breach_when_small_within_band():
    positions = [
        SimpleNamespace(nse_symbol="LARGECO", value=9_000_000),
        SimpleNamespace(nse_symbol="SMALLCO", value=1_000_000),
    ]
    meta = {"LARGECO": {"market_cap": 2e12}, "SMALLCO": {"market_cap": 1e11}}
    g = dict(goal_mod.DEFAULT_GOAL)
    result = goal_mod.classify_caps(positions, meta, g)
    assert result["small"]["pct"] == 10.0
    assert result["small_breach"] is False


def test_classify_caps_missing_meta_entry_is_unclassified():
    positions = [SimpleNamespace(nse_symbol="NOMETA", value=500)]
    g = dict(goal_mod.DEFAULT_GOAL)
    result = goal_mod.classify_caps(positions, {}, g)
    assert result["unclassified"]["value"] == 500
    assert result["unclassified"]["pct"] == 100.0
    assert result["large"]["value"] == 0
    assert result["small_breach"] is False


# ---------------------------------------------------------------------------
# compliance
# ---------------------------------------------------------------------------

def test_compliance_flags_commodity():
    positions = [SimpleNamespace(nse_symbol="COPP", name="Copper Co", value=1)]
    meta = {"COPP": {"industry": "Copper & Mining", "sector": "Materials"}}

    rules = goal_mod.compliance(positions, meta)
    by_rule = {r["rule"]: r for r in rules}

    assert by_rule["No commodities"]["ok"] is False
    assert "Copper Co" in by_rule["No commodities"]["detail"]
    assert by_rule["No crypto"]["ok"] is True
    assert by_rule["No crypto"]["detail"] == ""


def test_compliance_clean_holdings_pass():
    positions = [SimpleNamespace(nse_symbol="CLEAN", name="Clean Software Co", value=1)]
    meta = {"CLEAN": {"industry": "Software", "sector": "Technology"}}

    rules = goal_mod.compliance(positions, meta)
    assert all(r["ok"] for r in rules)
    assert all(r["detail"] == "" for r in rules)


def test_compliance_flags_crypto():
    positions = [SimpleNamespace(nse_symbol="COIN", name="Coin Exchange", value=1)]
    meta = {"COIN": {"industry": "Crypto Asset Exchange", "sector": "Financials"}}

    rules = goal_mod.compliance(positions, meta)
    by_rule = {r["rule"]: r for r in rules}
    assert by_rule["No crypto"]["ok"] is False
    assert "Coin Exchange" in by_rule["No crypto"]["detail"]
    assert by_rule["No commodities"]["ok"] is True


# ---------------------------------------------------------------------------
# refresh_security_meta / load_security_meta (no network — yf.Ticker monkeypatched)
# ---------------------------------------------------------------------------

class _FakePF:
    def __init__(self, symbols):
        self._symbols = symbols

    def consolidated(self):
        return [SimpleNamespace(nse_symbol=s, value=100.0) for s in self._symbols]


def test_refresh_security_meta_upserts_and_respects_ttl(tmp_path, monkeypatch):
    calls = []

    class FakeTicker:
        def __init__(self, symbol):
            self.symbol = symbol

        @property
        def info(self):
            calls.append(self.symbol)
            return {"marketCap": 12345.0, "sector": "Technology", "industry": "Software"}

    monkeypatch.setattr(yfinance, "Ticker", FakeTicker)

    pf = _FakePF(["ABC"])
    updated = goal_mod.refresh_security_meta(tmp_path, pf)
    assert updated == 1
    assert calls == ["ABC.NS"]

    meta = goal_mod.load_security_meta(tmp_path)
    assert meta["ABC"]["market_cap"] == 12345.0
    assert meta["ABC"]["sector"] == "Technology"
    assert meta["ABC"]["industry"] == "Software"

    # Within TTL: no re-fetch.
    updated_again = goal_mod.refresh_security_meta(tmp_path, pf)
    assert updated_again == 0
    assert calls == ["ABC.NS"]


def test_refresh_security_meta_refetches_stale_rows(tmp_path, monkeypatch):
    calls = []

    class FakeTicker:
        def __init__(self, symbol):
            self.symbol = symbol

        @property
        def info(self):
            calls.append(self.symbol)
            return {"marketCap": 999.0, "sector": "Energy", "industry": "Oil & Gas"}

    monkeypatch.setattr(yfinance, "Ticker", FakeTicker)

    stale_date = (date.today() - timedelta(days=30)).isoformat()
    with storage.connect(tmp_path) as con:
        con.execute(
            "INSERT INTO security_meta(symbol, market_cap, sector, industry, fetched_at) "
            "VALUES (?, ?, ?, ?, ?)",
            ("OLD", 1.0, "Old Sector", "Old Industry", stale_date),
        )
        con.commit()

    pf = _FakePF(["OLD"])
    updated = goal_mod.refresh_security_meta(tmp_path, pf)
    assert updated == 1
    assert calls == ["OLD.NS"]

    meta = goal_mod.load_security_meta(tmp_path)
    assert meta["OLD"]["market_cap"] == 999.0
    assert meta["OLD"]["sector"] == "Energy"


def test_refresh_security_meta_handles_fetch_errors(tmp_path, monkeypatch):
    class FailingTicker:
        def __init__(self, symbol):
            self.symbol = symbol

        @property
        def info(self):
            raise RuntimeError("network down")

    monkeypatch.setattr(yfinance, "Ticker", FailingTicker)

    pf = _FakePF(["BAD"])
    updated = goal_mod.refresh_security_meta(tmp_path, pf)
    assert updated == 0
    assert goal_mod.load_security_meta(tmp_path) == {}


def test_refresh_security_meta_no_symbols_returns_zero(tmp_path):
    pf = _FakePF([])
    assert goal_mod.refresh_security_meta(tmp_path, pf) == 0
    assert goal_mod.refresh_security_meta(tmp_path, None) == 0
