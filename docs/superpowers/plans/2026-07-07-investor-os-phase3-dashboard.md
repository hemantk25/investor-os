# Investor OS Phase 3 — Real Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the real local-first Streamlit dashboard per the spec at `docs/superpowers/specs/2026-07-07-investor-os-phase3-dashboard-design.md`: ICICI Excel ingestion, ISIN→NSE mapping, live yfinance prices, member switcher, rebalance tracker, `claude -p` morning briefs, and the Mac handoff package.

**Architecture:** Pure-Python modules under `app/` with one responsibility each (parser → mapping → prices → portfolio → advisory → brief), a Streamlit `dashboard.py` that only renders, and file-based state in `data/` + `briefs/` + `profile/`. Real data stays out of git; a synthetic fixture Excel (fake data, real format) drives the pytest suite.

**Tech Stack:** Python 3.11+ (dev machine has 3.14), Streamlit ≥1.41, openpyxl, yfinance, requests, pytest. No database, no server, no API keys.

## Global Constraints

- **No real data in git.** `/data/`, `/briefs/`, `/profile/`, `report_data/` are gitignored; only `tests/fixtures/*.xlsx` (fake data) may be committed.
- **No stack traces in the UI** — every failure renders a friendly card with what-to-do (spec §8).
- **Dashboard must render fully offline** — NSE list and yfinance are best-effort with Excel-CMP fallback (spec §4, §8).
- Indian formatting everywhere: `₹` with en-IN grouping, `₹X.XX Cr` / `₹X.X L` short forms.
- Cross-platform paths via `pathlib` (dev = Windows, target = Sir's Mac).
- Brand: same gold/navy tokens as the demo (`--bg:#0b0f16, panel:#121826, line:#232e42, gold:#d4b06e, emerald:#3ecf8e, red:#ef6a5f, muted:#8c99ae`).
- Commit after every task.

## Module Interfaces (single source of truth — all tasks conform to this)

```python
# app/parser.py
@dataclass
class Holding:
    member: str; name: str; icici_symbol: str; isin: str
    qty: float; avg_cost: float | None      # None = cost unknown (flag in UI)
    excel_cmp: float | None; excel_day_pct: float | None  # day % in percent units
@dataclass
class ParseResult:
    holdings: list[Holding]; skipped: list[str]; asof: datetime; members: list[str]
def parse_holdings(path: Path) -> ParseResult

# app/mapping.py
def ensure_map(data_dir: Path, refresh: bool = False) -> dict[str, str]  # ISIN -> NSE symbol

# app/prices.py
@dataclass
class Quote: price: float; day_pct: float | None
def fetch_quotes(nse_symbols: list[str], ttl: int = 300) -> dict[str, Quote]  # {} on failure

# app/portfolio.py
@dataclass
class Position:  # enriched, per-member
    member: str; name: str; isin: str; icici_symbol: str; nse_symbol: str | None
    qty: float; avg_cost: float | None; price: float; price_live: bool; day_pct: float | None
    # properties: value, cost (None if unknown), pl (None), pl_pct (None)
@dataclass
class ConsolidatedPosition:
    name: str; isin: str; nse_symbol: str | None; qty: float; avg_cost: float | None
    price: float; price_live: bool; day_pct: float | None; held_by: list[str]
    cost_partial: bool  # True if some member lots had unknown cost
    # properties: value, cost, pl, pl_pct
@dataclass
class Extra: member: str; label: str; asset_class: str; value: float; invested: float | None; note: str
@dataclass
class Totals:
    total_value: float; equity_value: float; extras_by_class: dict[str, float]
    invested_known: float; pl: float; pl_pct: float | None; day_pl: float; day_pl_pct: float
class Portfolio:
    positions: list[Position]; extras: list[Extra]; asof: datetime; skipped: list[str]
    members: list[str]
    def filtered(self, member: str | None) -> list[Position]
    def consolidated(self, member: str | None = None) -> list[ConsolidatedPosition]
    def totals(self, member: str | None = None) -> Totals
    def movers(self, member: str | None = None, n: int = 4) -> list[ConsolidatedPosition]
def build_portfolio(pr: ParseResult, isin_map: dict, quotes: dict, extras: list[Extra]) -> Portfolio
def load_extras(path: Path) -> list[Extra]
def fmt_inr(n) -> str; def fmt_short(n) -> str; def fmt_pct(p) -> str

# app/advisory.py
@dataclass
class ExitItem: stock: str; sector: str; category: str; cur_value: str; priority: str
               proceeds: str; reason: str; status: str; source: str; isin: str | None
@dataclass
class BuyItem: stock: str; sector: str; category: str; alloc_lo: float; alloc_hi: float
              target_pct: str; conviction: str; entry: str; horizon: str; thesis: str
              current_value: float; progress_pct: float
@dataclass
class MonthBlock: label: str; exits_text: str; buys_text: str; is_current: bool
@dataclass
class TargetRow: num: int; stock: str; sector: str; status: str; cur_value: str
                target_pct: str; cagr: str; conviction: str; thesis: str
@dataclass
class Advisory: targets: list[TargetRow]; exits: list[ExitItem]; buys: list[BuyItem]
               schedule: list[MonthBlock]
def parse_advisory(path: Path) -> Advisory
def apply_status(adv: Advisory, portfolio, data_dir: Path, today: date) -> Advisory
def parse_alloc(text: str) -> tuple[float, float]   # "₹5–7L" -> (500000.0, 700000.0)

# app/brief.py
class BriefError(Exception): ...   # .message is user-facing, actionable
def find_claude() -> str | None
def portfolio_snapshot(portfolio) -> dict
def build_prompt(one_pager: str | None, snapshot: dict, today: date) -> str
def generate_brief(portfolio, base_dir: Path) -> Path

# app/theme.py
def inject() -> None   # st.markdown(<style>) with brand CSS
```

Status strings (advisory): `"DONE" | "IN PROGRESS" | "PENDING" | "REVIEW"`. Source: `"auto" | "manual"`. Extras asset_class: `"mf" | "gold" | "debt" | "cash"`.

---

### Task 1: Scaffold — env, gitignore, theme, dashboard shell

**Files:**
- Create: `requirements.txt`, `app/__init__.py`, `app/theme.py`, `app/dashboard.py`, `.streamlit/config.toml`, `start-dashboard.ps1`
- Modify: `.gitignore`

**Interfaces:**
- Produces: `theme.inject()`; `dashboard.py` shell with `VIEWS` dict and `member_selector(members)->str|None`; runnable app.

- [ ] **Step 1: requirements.txt**

```
streamlit>=1.41
openpyxl>=3.1
yfinance>=0.2.50
requests>=2.31
pytest>=8.0
```

- [ ] **Step 2: Append to .gitignore** (keep existing lines; note the fixture negation must come after `*.xlsx`)

```
/data/
/briefs/
/profile/
!tests/fixtures/*.xlsx
```

- [ ] **Step 3: .streamlit/config.toml**

```toml
[theme]
base = "dark"
primaryColor = "#d4b06e"
backgroundColor = "#0b0f16"
secondaryBackgroundColor = "#121826"
textColor = "#e9edf5"
[server]
headless = true
[browser]
gatherUsageStats = false
```

- [ ] **Step 4: app/theme.py**

```python
import streamlit as st

CSS = """
<style>
:root { --gold:#d4b06e; --emerald:#3ecf8e; --red:#ef6a5f; --muted:#8c99ae; --line:#232e42; }
h1, h2, h3 { font-family: Georgia, "Times New Roman", serif !important; }
.stMetric label { text-transform: uppercase; letter-spacing: .08em; font-size: 11px; }
[data-testid="stMetricValue"] { font-family: Georgia, serif; }
.up { color: var(--emerald); } .down { color: var(--red); } .muted { color: var(--muted); }
.stale-badge { color:#c98500; font-size:11px; border:1px solid #c98500; border-radius:8px; padding:0 6px; }
div[data-testid="stSidebarUserContent"] .brand { color: var(--gold); font-family: Georgia, serif;
  letter-spacing:.14em; font-size:16px; }
</style>
"""

def inject() -> None:
    st.markdown(CSS, unsafe_allow_html=True)
```

- [ ] **Step 5: app/dashboard.py shell**

```python
from pathlib import Path
import streamlit as st
from app import theme

BASE = Path(__file__).resolve().parent.parent
DATA = BASE / "data"

st.set_page_config(page_title="Investor OS — Paresh Karia", page_icon="◈", layout="wide")
theme.inject()

def member_selector(members: list[str]) -> str | None:
    choice = st.segmented_control("Member", ["All"] + members, default="All",
                                  label_visibility="collapsed")
    return None if choice in (None, "All") else choice

def view_overview():  st.info("Overview — coming in Task 8")
def view_holdings():  st.info("Holdings — coming in Task 9")
def view_rebalance(): st.info("Rebalance — coming in Task 10")
def view_brief():     st.info("Morning Brief — coming in Task 11")
def view_profile():   st.info("Profile — coming in Task 12")

VIEWS = {"◈ Overview": view_overview, "▤ Holdings": view_holdings,
         "⚖ Rebalance": view_rebalance, "⚡ Morning Brief": view_brief,
         "👤 Investor Profile": view_profile}

with st.sidebar:
    st.markdown('<div class="brand">INVESTOR OS</div>', unsafe_allow_html=True)
    st.caption("Private · Paresh Karia")
    view = st.radio("View", list(VIEWS), label_visibility="collapsed")

st.title("Paresh Karia — Investor OS")
VIEWS[view]()
```

- [ ] **Step 6: start-dashboard.ps1**

```powershell
if (-not (Test-Path .venv)) { python -m venv .venv; .\.venv\Scripts\pip install -r requirements.txt }
.\.venv\Scripts\python -m streamlit run app\dashboard.py
```

- [ ] **Step 7: Create venv, install, smoke-test**

Run:
```powershell
python -m venv .venv; .\.venv\Scripts\pip install -r requirements.txt
$p = Start-Process .\.venv\Scripts\python -ArgumentList "-m","streamlit","run","app\dashboard.py","--server.port","8511" -PassThru
Start-Sleep -Seconds 12
(Invoke-WebRequest http://localhost:8511 -UseBasicParsing).StatusCode
Stop-Process $p.Id -Force
```
Expected: `200`.

- [ ] **Step 8: Commit**

```bash
git add requirements.txt .gitignore .streamlit app start-dashboard.ps1
git commit -m "feat(app): scaffold Streamlit shell, theme, env"
```

---

### Task 2: Synthetic fixtures (holdings + advisory Excels, fake data, real format)

**Files:**
- Create: `tests/__init__.py` (empty), `tests/fixtures/make_fixtures.py`, generated `tests/fixtures/sample-holdings.xlsx`, `tests/fixtures/sample-advisory.xlsx`

**Interfaces:**
- Produces: fixture workbooks replicating the ICICI format (title row, header row with newline-embedded column names, member sheets PK/CK) and the advisory format (banner rows, offset first column). All later tests consume these paths.

- [ ] **Step 1: tests/fixtures/make_fixtures.py** (fake data only; includes the real-world quirks: missing avg cost, unmappable ISIN, junk row)

```python
from pathlib import Path
from openpyxl import Workbook

HERE = Path(__file__).parent
H = ["Sr.", "Stock Name", "Symbol", "ISIN", "Qty\nHeld", "CMP (₹)", "% Chg",
     "Market\nValue (₹)", "Avg Buy\nPrice (₹)", "Total\nCost (₹)",
     "Unrealised\nGain/Loss (₹)", "Gain/\nLoss %"]

def member_sheet(wb, name, rows):
    ws = wb.create_sheet(name)
    ws.append([f"{name} – Equity Portfolio (fixture)"])
    ws.append(H)
    for r in rows: ws.append(r)

def holdings():
    wb = Workbook(); wb.remove(wb.active)
    ws = wb.create_sheet("Summary"); ws.append(["Family Equity Portfolio (fixture)"])
    ws = wb.create_sheet("Consolidated"); ws.append(["ignored by parser"])
    member_sheet(wb, "PK", [
        [1, "ALPHA MOTORS LIMITED", "ALPMOT", "INE001A01001", 100, 250.0, 0.01, 25000, 200.0, 20000, 5000, 0.25],
        [2, "BETA PHARMA LIMITED",  "BETPHA", "INE002B01012", 50, 400.0, -0.02, 20000, None, None, None, None],
        [3, "GAMMA UNLISTED CO",    "GAMUNL", "IN9999X99999", 30, 10.0, 0.0, 300, 12.0, 360, -60, -0.17],
        [4, "JUNK ROW NO ISIN",     "JUNK",   None, 10, 5.0, 0, 50, 5.0, 50, 0, 0],
    ])
    member_sheet(wb, "CK", [
        [1, "ALPHA MOTORS LIMITED", "ALPMOT", "INE001A01001", 50, 250.0, 0.01, 12500, 220.0, 11000, 1500, 0.14],
        [2, "DELTA BANK LIMITED",   "DELBAN", "INE004D01034", 200, 150.0, 0.005, 30000, 100.0, 20000, 10000, 0.50],
    ])
    wb.save(HERE / "sample-holdings.xlsx")

def advisory():
    wb = Workbook(); wb.remove(wb.active)
    ws = wb.create_sheet("Target 50-Stock Portfolio")
    ws.append([]); ws.append(["", "TARGET PORTFOLIO (fixture)"]); ws.append([])
    ws.append(["", "#", "Stock", "Sector", "Status", "Cur. Value", "Target %", "CAGR Est.", "Conv.", "Investment Thesis"])
    ws.append(["", "  ▶  BANKING"])
    ws.append(["", 1, "Delta Bank", "Banking", "KEEP", "₹0.3L", "5.0%", "~15% pa", "★★★★★", "Fixture thesis"])
    ws.append(["", 2, "Alpha Motors", "Auto", "KEEP (TRIM)", "₹0.4L", "4.0%", "~12% pa", "★★★★", "Fixture thesis 2"])
    ws = wb.create_sheet("Exit List (25 Stocks)")
    ws.append([]); ws.append(["", "EXIT LIST (fixture)"]); ws.append([])
    ws.append(["", "Stock", "Sector", "Category", "Cur. Value", "G/L Est.", "Priority", "Est. Proceeds", "Reason for Exit"])
    ws.append(["", "Beta Pharma", "Pharma", "ZOMBIE", "₹0.2L", "-50%", "IMMEDIATE", "~₹20K", "Fixture reason"])
    ws.append(["", "Omega Ghost", "Misc", "ZOMBIE", "₹100", "-99%", "IMMEDIATE", "~₹100", "No match in holdings"])
    ws = wb.create_sheet("New Buys (10 Stocks)")
    ws.append([]); ws.append(["", "NEW BUYS (fixture)"]); ws.append([])
    ws.append(["", "Stock", "Sector", "Category", "Allocation", "Target%", "Conv.", "Entry Strategy", "Horizon", "Investment Thesis"])
    ws.append(["", "Delta Bank", "Banking", "Banks", "₹1–2L", "2.0%", "★★★★★", "2 tranches", "3–5yr", "Fixture buy thesis"])
    ws = wb.create_sheet("Execution Schedule")
    ws.append([]); ws.append(["", "SCHEDULE (fixture)"]); ws.append([])
    ws.append(["", "MONTH 1\nJul 2026", "EXITS THIS MONTH", "Exit zombies"])
    ws.append(["", "", "BUY/ADD THIS MONTH", "Start Delta Bank"])
    ws.append([])
    ws.append(["", "MONTH 2\nAug 2026", "EXITS THIS MONTH", "Trim Alpha"])
    ws.append(["", "", "BUY/ADD THIS MONTH", "Finish Delta Bank"])
    wb.save(HERE / "sample-advisory.xlsx")

if __name__ == "__main__":
    holdings(); advisory(); print("fixtures written")
```

- [ ] **Step 2: Generate and verify**

Run: `.\.venv\Scripts\python tests\fixtures\make_fixtures.py`
Expected: `fixtures written`; both .xlsx files exist under tests/fixtures/.

- [ ] **Step 3: Verify fixtures are committable (gitignore negation works)**

Run: `git check-ignore tests/fixtures/sample-holdings.xlsx; if ($LASTEXITCODE -eq 1) { "committable OK" }`
Expected: `committable OK`.

- [ ] **Step 4: Commit**

```bash
git add tests
git commit -m "test: synthetic ICICI-format fixtures (fake data)"
```

---

### Task 3: parser.py

**Files:**
- Create: `app/parser.py`, `tests/test_parser.py`

**Interfaces:**
- Consumes: fixture `tests/fixtures/sample-holdings.xlsx`.
- Produces: `parse_holdings(path) -> ParseResult` per the interface block.

- [ ] **Step 1: tests/test_parser.py**

```python
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
```

- [ ] **Step 2: Run to verify failure**

Run: `.\.venv\Scripts\python -m pytest tests\test_parser.py -v`
Expected: FAIL (ModuleNotFoundError: app.parser).

- [ ] **Step 3: app/parser.py**

```python
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import openpyxl

NON_MEMBER_SHEETS = {"summary", "consolidated"}

@dataclass
class Holding:
    member: str; name: str; icici_symbol: str; isin: str
    qty: float; avg_cost: float | None
    excel_cmp: float | None; excel_day_pct: float | None

@dataclass
class ParseResult:
    holdings: list; skipped: list; asof: datetime; members: list

def _norm(cell) -> str:
    return str(cell).lower().replace("\n", " ").strip() if cell is not None else ""

def _find_header(ws):
    for r, row in enumerate(ws.iter_rows(min_row=1, max_row=6, values_only=True), start=1):
        cells = [_norm(c) for c in row]
        if "isin" in cells and any(c.startswith("qty") for c in cells):
            cols = {}
            for i, c in enumerate(cells):
                if "stock name" in c: cols["name"] = i
                elif c == "symbol": cols["symbol"] = i
                elif c == "isin": cols["isin"] = i
                elif c.startswith("qty"): cols["qty"] = i
                elif c.startswith("cmp"): cols["cmp"] = i
                elif c.startswith("% chg"): cols["day"] = i
                elif c.startswith("avg buy"): cols["avg"] = i
            return r, cols
    return None, None

def _num(v) -> float | None:
    if v is None or isinstance(v, bool): return None
    if isinstance(v, (int, float)): return float(v)
    s = str(v).replace(",", "").replace("₹", "").replace("%", "").replace("+", "").strip()
    try: return float(s)
    except ValueError: return None

def _day_pct(v) -> float | None:
    if v is None: return None
    if isinstance(v, str) and "%" in v: return _num(v)          # "+0.65%" -> 0.65
    n = _num(v)
    return None if n is None else n * 100.0                      # 0.01 fraction -> 1.0

def parse_holdings(path: Path) -> ParseResult:
    wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    holdings, skipped, members = [], [], []
    for sheet in wb.sheetnames:
        if sheet.lower() in NON_MEMBER_SHEETS: continue
        ws = wb[sheet]
        hrow, cols = _find_header(ws)
        if not cols or "isin" not in cols or "qty" not in cols: continue
        members.append(sheet)
        for row in ws.iter_rows(min_row=hrow + 1, values_only=True):
            name = row[cols["name"]] if cols.get("name") is not None else None
            if name is None: continue
            isin = str(row[cols["isin"]] or "").strip()
            qty = _num(row[cols["qty"]])
            if len(isin) != 12 or not isin.startswith("IN") or not qty or qty <= 0:
                skipped.append(f"{sheet}: {name} (missing/invalid ISIN or qty)")
                continue
            avg = _num(row[cols["avg"]]) if "avg" in cols else None
            holdings.append(Holding(
                member=sheet, name=str(name).strip(),
                icici_symbol=str(row[cols["symbol"]] or "").strip() if "symbol" in cols else "",
                isin=isin, qty=qty,
                avg_cost=avg if avg and avg > 0 else None,
                excel_cmp=_num(row[cols["cmp"]]) if "cmp" in cols else None,
                excel_day_pct=_day_pct(row[cols["day"]]) if "day" in cols else None))
    wb.close()
    asof = datetime.fromtimestamp(Path(path).stat().st_mtime)
    return ParseResult(holdings=holdings, skipped=skipped, asof=asof, members=members)
```

- [ ] **Step 4: Run tests**

Run: `.\.venv\Scripts\python -m pytest tests\test_parser.py -v`
Expected: 4 passed.

- [ ] **Step 5: Sanity-run against the REAL file (not committed)**

Run: `.\.venv\Scripts\python -c "from app.parser import parse_holdings; from pathlib import Path; pr = parse_holdings(Path('report_data/Current Portfolio - All Members (1).xlsx')); print(pr.members, len(pr.holdings), 'skipped:', len(pr.skipped))"`
Expected: `['PK', 'CK', 'NK', 'DK'] ~146 skipped: <small number>` (row count near 146; skips only for genuinely blank/summary rows).

- [ ] **Step 6: Commit**

```bash
git add app/parser.py tests/test_parser.py
git commit -m "feat(app): ICICI holdings Excel parser"
```

---

### Task 4: mapping.py (ISIN → NSE symbol)

**Files:**
- Create: `app/mapping.py`, `tests/test_mapping.py`

**Interfaces:**
- Produces: `ensure_map(data_dir, refresh=False) -> dict[str, str]`. Cache file `data_dir/isin-map.csv` (cols isin,symbol); overrides `data_dir/overrides.csv` (same cols) win; network failure with existing cache → cache; no cache → `{}`.

- [ ] **Step 1: tests/test_mapping.py**

```python
import app.mapping as mapping

def _write(p, text): p.write_text(text, encoding="utf-8")

def test_cache_and_overrides_precedence(tmp_path, monkeypatch):
    monkeypatch.setattr(mapping, "_download_nse_list", lambda: (_ for _ in ()).throw(RuntimeError("offline")))
    _write(tmp_path / "isin-map.csv", "isin,symbol\nINE001A01001,ALPHAMOT\nINE004D01034,DELTABANK\n")
    _write(tmp_path / "overrides.csv", "isin,symbol\nINE004D01034,DELTAB\n")
    m = mapping.ensure_map(tmp_path)
    assert m["INE001A01001"] == "ALPHAMOT"
    assert m["INE004D01034"] == "DELTAB"          # override wins

def test_no_cache_offline_returns_empty(tmp_path, monkeypatch):
    monkeypatch.setattr(mapping, "_download_nse_list", lambda: (_ for _ in ()).throw(RuntimeError("offline")))
    assert mapping.ensure_map(tmp_path) == {}

def test_download_writes_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(mapping, "_download_nse_list",
                        lambda: {"INE001A01001": "ALPHAMOT"})
    m = mapping.ensure_map(tmp_path, refresh=True)
    assert m == {"INE001A01001": "ALPHAMOT"}
    assert (tmp_path / "isin-map.csv").exists()
```

- [ ] **Step 2: Run to verify failure** — `pytest tests\test_mapping.py -v` → FAIL (no module).

- [ ] **Step 3: app/mapping.py**

```python
from __future__ import annotations
import csv, io
from pathlib import Path
import requests

NSE_URLS = ["https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv",
            "https://archives.nseindia.com/content/equities/EQUITY_L.csv"]
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15) AppleWebKit/537.36"}

def _download_nse_list() -> dict[str, str]:
    last = None
    for url in NSE_URLS:
        try:
            r = requests.get(url, headers=UA, timeout=30)
            r.raise_for_status()
            out = {}
            for row in csv.DictReader(io.StringIO(r.text)):
                row = {k.strip(): (v or "").strip() for k, v in row.items()}
                if row.get("ISIN NUMBER") and row.get("SYMBOL"):
                    out[row["ISIN NUMBER"]] = row["SYMBOL"]
            if out: return out
        except Exception as e:
            last = e
    raise RuntimeError(f"NSE list download failed: {last}")

def _read_csv(path: Path) -> dict[str, str]:
    if not path.exists(): return {}
    with path.open(encoding="utf-8") as f:
        return {r["isin"]: r["symbol"] for r in csv.DictReader(f) if r.get("isin")}

def ensure_map(data_dir: Path, refresh: bool = False) -> dict[str, str]:
    data_dir.mkdir(parents=True, exist_ok=True)
    cache = data_dir / "isin-map.csv"
    if refresh or not cache.exists():
        try:
            fresh = _download_nse_list()
            with cache.open("w", newline="", encoding="utf-8") as f:
                w = csv.writer(f); w.writerow(["isin", "symbol"])
                for k, v in sorted(fresh.items()): w.writerow([k, v])
        except Exception:
            pass  # fall through to whatever cache exists
    result = _read_csv(cache)
    result.update(_read_csv(data_dir / "overrides.csv"))
    return result
```

- [ ] **Step 4: Run tests** — `pytest tests\test_mapping.py -v` → 3 passed.

- [ ] **Step 5: Live sanity check (real NSE download + real ISINs)**

Run: `.\.venv\Scripts\python -c "from pathlib import Path; from app.mapping import ensure_map; m = ensure_map(Path('data')); print(len(m), m.get('INE040A01034'), m.get('INE090A01021'))"`
Expected: `~2000+ HDFCBANK ICICIBANK`.

- [ ] **Step 6: Commit**

```bash
git add app/mapping.py tests/test_mapping.py
git commit -m "feat(app): ISIN to NSE symbol mapping with cache + overrides"
```

---

### Task 5: prices.py

**Files:**
- Create: `app/prices.py`, `tests/test_prices.py`

**Interfaces:**
- Produces: `Quote(price, day_pct)`, `fetch_quotes(nse_symbols, ttl=300) -> dict[str, Quote]` (empty dict on any failure; in-module TTL cache), internal pure `_frame_to_quotes(df, symbols)` used by the test.

- [ ] **Step 1: tests/test_prices.py**

```python
import pandas ... # NOT AVAILABLE — yfinance installs pandas; import it in the test
```

Actually written as:

```python
import pandas as pd
from app.prices import _frame_to_quotes

def test_frame_to_quotes_two_days():
    df = pd.DataFrame({("Close", "ALPHAMOT.NS"): [100.0, 110.0],
                       ("Close", "DELTAB.NS"):  [50.0, None]})
    df.columns = pd.MultiIndex.from_tuples(df.columns)
    q = _frame_to_quotes(df, ["ALPHAMOT", "DELTAB"])
    assert round(q["ALPHAMOT"].price, 2) == 110.0
    assert round(q["ALPHAMOT"].day_pct, 2) == 10.0
    assert q["DELTAB"].price == 50.0 and q["DELTAB"].day_pct is None
```

- [ ] **Step 2: Run to verify failure** — `pytest tests\test_prices.py -v` → FAIL.

- [ ] **Step 3: app/prices.py**

```python
from __future__ import annotations
import time
from dataclasses import dataclass

@dataclass
class Quote:
    price: float
    day_pct: float | None

_cache: dict = {}

def _frame_to_quotes(df, symbols) -> dict[str, Quote]:
    out = {}
    close = df["Close"] if "Close" in df.columns.get_level_values(0) else df
    for s in symbols:
        col = f"{s}.NS"
        if col not in close.columns: continue
        series = close[col].dropna()
        if series.empty: continue
        price = float(series.iloc[-1])
        day = float((series.iloc[-1] / series.iloc[-2] - 1) * 100) if len(series) >= 2 else None
        out[s] = Quote(price=price, day_pct=day)
    return out

def fetch_quotes(nse_symbols: list[str], ttl: int = 300) -> dict[str, Quote]:
    symbols = sorted(set(s for s in nse_symbols if s))
    if not symbols: return {}
    key = tuple(symbols)
    now = time.time()
    if key in _cache and now - _cache[key][0] < ttl:
        return _cache[key][1]
    try:
        import yfinance as yf
        df = yf.download([f"{s}.NS" for s in symbols], period="5d", interval="1d",
                         progress=False, threads=True, group_by="column")
        quotes = _frame_to_quotes(df, symbols)
    except Exception:
        quotes = {}
    if quotes: _cache[key] = (now, quotes)
    return quotes
```

- [ ] **Step 4: Run tests** — `pytest tests\test_prices.py -v` → 1 passed.

- [ ] **Step 5: Live sanity** — `.\.venv\Scripts\python -c "from app.prices import fetch_quotes; q = fetch_quotes(['HDFCBANK','TCS']); print({k:(round(v.price,1), v.day_pct and round(v.day_pct,2)) for k,v in q.items()})"` → two live quotes (or `{}` if market API hiccups — rerun once).

- [ ] **Step 6: Commit**

```bash
git add app/prices.py tests/test_prices.py
git commit -m "feat(app): yfinance batch quotes with TTL cache"
```

---

### Task 6: portfolio.py (merge, consolidate, totals, formatting)

**Files:**
- Create: `app/portfolio.py`, `tests/test_portfolio.py`

**Interfaces:**
- Consumes: `ParseResult`, `dict[isin→symbol]`, `dict[symbol→Quote]`.
- Produces: everything in the interface block (`Position`, `ConsolidatedPosition`, `Extra`, `Totals`, `Portfolio`, `build_portfolio`, `load_extras`, `fmt_inr`, `fmt_short`, `fmt_pct`).

- [ ] **Step 1: tests/test_portfolio.py**

```python
import json
from pathlib import Path
from app.parser import parse_holdings
from app.prices import Quote
from app.portfolio import build_portfolio, load_extras, fmt_short, fmt_inr, fmt_pct

FIX = Path(__file__).parent / "fixtures" / "sample-holdings.xlsx"
ISIN_MAP = {"INE001A01001": "ALPHAMOT", "INE002B01012": "BETAPH", "INE004D01034": "DELTAB"}
QUOTES = {"ALPHAMOT": Quote(300.0, 2.0), "DELTAB": Quote(160.0, -1.0)}   # BETAPH: no quote

def _pf(extras=None):
    return build_portfolio(parse_holdings(FIX), ISIN_MAP, QUOTES, extras or [])

def test_live_vs_fallback_prices():
    pf = _pf()
    alpha = next(p for p in pf.positions if p.name.startswith("ALPHA") and p.member == "PK")
    beta = next(p for p in pf.positions if p.name.startswith("BETA"))
    gamma = next(p for p in pf.positions if p.name.startswith("GAMMA"))
    assert alpha.price == 300.0 and alpha.price_live
    assert beta.price == 400.0 and not beta.price_live      # mapped but no quote -> excel cmp
    assert gamma.nse_symbol is None and gamma.price == 10.0 # unmapped -> excel cmp

def test_consolidation_weighted_avg_and_held_by():
    cons = _pf().consolidated()
    alpha = next(c for c in cons if c.name.startswith("ALPHA"))
    assert alpha.qty == 150
    assert round(alpha.avg_cost, 2) == round((100*200 + 50*220) / 150, 2)
    assert alpha.held_by == ["CK", "PK"]

def test_member_filter_totals():
    pf = _pf()
    t_ck = pf.totals("CK")
    assert t_ck.equity_value == 50*300.0 + 200*160.0
    t_all = pf.totals()
    assert t_all.equity_value == 150*300.0 + 50*400.0 + 30*10.0 + 200*160.0

def test_unknown_cost_excluded_from_pl():
    t = _pf().totals()
    # invested = alpha(100*200 + 50*220) + gamma(30*12) + delta(200*100); beta excluded
    assert t.invested_known == 20000 + 11000 + 360 + 20000

def test_extras_merge(tmp_path):
    p = tmp_path / "extras.json"
    p.write_text(json.dumps([{"member": "PK", "label": "Gold SGB", "asset_class": "gold",
                              "value": 100000, "invested": 80000}]), encoding="utf-8")
    pf = _pf(load_extras(p))
    assert pf.totals().extras_by_class["gold"] == 100000
    assert pf.totals("CK").extras_by_class == {}

def test_formats():
    assert fmt_short(24087460) == "₹2.41 Cr"
    assert fmt_short(2460000) == "₹24.6 L"
    assert fmt_inr(1234567) == "₹12,34,567"
    assert fmt_pct(22.6) == "+22.6%"
```

- [ ] **Step 2: Run to verify failure** — `pytest tests\test_portfolio.py -v` → FAIL.

- [ ] **Step 3: app/portfolio.py**

```python
from __future__ import annotations
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

@dataclass
class Position:
    member: str; name: str; isin: str; icici_symbol: str; nse_symbol: str | None
    qty: float; avg_cost: float | None; price: float; price_live: bool; day_pct: float | None
    @property
    def value(self): return self.qty * self.price
    @property
    def cost(self): return None if self.avg_cost is None else self.qty * self.avg_cost
    @property
    def pl(self): return None if self.cost is None else self.value - self.cost
    @property
    def pl_pct(self): return None if not self.cost else (self.value / self.cost - 1) * 100

@dataclass
class ConsolidatedPosition:
    name: str; isin: str; nse_symbol: str | None; qty: float; avg_cost: float | None
    price: float; price_live: bool; day_pct: float | None
    held_by: list = field(default_factory=list); cost_partial: bool = False
    value = Position.value; cost = Position.cost; pl = Position.pl; pl_pct = Position.pl_pct

@dataclass
class Extra:
    member: str; label: str; asset_class: str; value: float
    invested: float | None = None; note: str = ""

@dataclass
class Totals:
    total_value: float; equity_value: float; extras_by_class: dict
    invested_known: float; pl: float; pl_pct: float | None
    day_pl: float; day_pl_pct: float

class Portfolio:
    def __init__(self, positions, extras, asof, skipped, members):
        self.positions, self.extras = positions, extras
        self.asof, self.skipped, self.members = asof, skipped, members

    def filtered(self, member=None):
        return [p for p in self.positions if member is None or p.member == member]

    def consolidated(self, member=None):
        groups: dict[str, list] = {}
        for p in self.filtered(member):
            groups.setdefault(p.isin, []).append(p)
        out = []
        for isin, lots in groups.items():
            qty = sum(l.qty for l in lots)
            known = [l for l in lots if l.avg_cost is not None]
            kqty = sum(l.qty for l in known)
            avg = (sum(l.qty * l.avg_cost for l in known) / kqty) if kqty else None
            l0 = lots[0]
            out.append(ConsolidatedPosition(
                name=l0.name, isin=isin, nse_symbol=l0.nse_symbol, qty=qty, avg_cost=avg,
                price=l0.price, price_live=l0.price_live, day_pct=l0.day_pct,
                held_by=sorted({l.member for l in lots}), cost_partial=kqty < qty))
        return sorted(out, key=lambda c: -c.value)

    def _extras(self, member=None):
        return [e for e in self.extras if member is None or e.member == member]

    def totals(self, member=None):
        cons = self.consolidated(member)
        extras = self._extras(member)
        equity = sum(c.value for c in cons)
        ebc: dict[str, float] = {}
        for e in extras: ebc[e.asset_class] = ebc.get(e.asset_class, 0) + e.value
        invested = sum(c.qty * c.avg_cost for c in cons if c.avg_cost is not None) \
                 + sum(e.invested for e in extras if e.invested)
        value_known = sum(c.value for c in cons if c.avg_cost is not None) \
                    + sum(e.value for e in extras if e.invested)
        pl = value_known - invested
        day_pl = sum(c.value - c.value / (1 + c.day_pct / 100)
                     for c in cons if c.day_pct is not None)
        total = equity + sum(ebc.values())
        return Totals(total_value=total, equity_value=equity, extras_by_class=ebc,
                      invested_known=invested, pl=pl,
                      pl_pct=(pl / invested * 100) if invested else None,
                      day_pl=day_pl, day_pl_pct=(day_pl / total * 100) if total else 0.0)

    def movers(self, member=None, n=4):
        live = [c for c in self.consolidated(member) if c.day_pct is not None]
        live.sort(key=lambda c: -c.day_pct)
        return live[: n // 2] + live[-(n - n // 2):] if len(live) >= n else live

def build_portfolio(pr, isin_map, quotes, extras):
    positions = []
    for h in pr.holdings:
        sym = isin_map.get(h.isin)
        q = quotes.get(sym) if sym else None
        price = q.price if q else (h.excel_cmp or 0.0)
        positions.append(Position(
            member=h.member, name=h.name, isin=h.isin, icici_symbol=h.icici_symbol,
            nse_symbol=sym, qty=h.qty, avg_cost=h.avg_cost, price=price,
            price_live=q is not None,
            day_pct=q.day_pct if q else h.excel_day_pct))
    return Portfolio(positions, extras, pr.asof, pr.skipped, pr.members)

def load_extras(path: Path):
    if not path.exists(): return []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return [Extra(member=r.get("member", "PK"), label=r["label"],
                      asset_class=r["asset_class"], value=float(r["value"]),
                      invested=float(r["invested"]) if r.get("invested") else None,
                      note=r.get("note", "")) for r in raw]
    except Exception:
        return []

def fmt_inr(n): return "₹" + f"{round(n):,}".replace(",", "_TMP_") and _in_group(round(n))
```

Wait — Indian grouping needs its own helper; final code:

```python
def _in_group(n: int) -> str:
    s = str(abs(n)); sign = "-" if n < 0 else ""
    if len(s) <= 3: return sign + s
    head, tail = s[:-3], s[-3:]
    parts = []
    while len(head) > 2:
        parts.insert(0, head[-2:]); head = head[:-2]
    if head: parts.insert(0, head)
    return sign + ",".join(parts + [tail])

def fmt_inr(n) -> str: return "₹" + _in_group(round(n))

def fmt_short(n) -> str:
    a = abs(n)
    if a >= 1e7: return f"₹{n/1e7:.2f} Cr"
    if a >= 1e5: return f"₹{n/1e5:.1f} L"
    return fmt_inr(n)

def fmt_pct(p) -> str: return f"{'+' if p >= 0 else ''}{p:.1f}%"
```

(Use the `_in_group` version; delete the broken one-liner — it exists in this plan only to show the pitfall. The file must contain only the `_in_group`-based implementations.)

- [ ] **Step 4: Run tests** — `pytest tests\test_portfolio.py -v` → 6 passed. Also rerun all: `pytest -v` → all green.

- [ ] **Step 5: Commit**

```bash
git add app/portfolio.py tests/test_portfolio.py
git commit -m "feat(app): portfolio model — merge, consolidation, totals, INR formats"
```

---

### Task 7: advisory.py (rebalance model)

**Files:**
- Create: `app/advisory.py`, `tests/test_advisory.py`

**Interfaces:**
- Consumes: fixture `sample-advisory.xlsx`; a `Portfolio` (uses `.consolidated()` names/isin/qty/value).
- Produces: interface-block dataclasses + `parse_advisory`, `apply_status`, `parse_alloc`. Baseline file `data_dir/advisory-baseline.json`; overrides `data_dir/rebalance-status.json` (`{"Stock Name": "DONE"}`).

- [ ] **Step 1: tests/test_advisory.py**

```python
import json
from datetime import date
from pathlib import Path
from app.parser import parse_holdings
from app.prices import Quote
from app.portfolio import build_portfolio
from app.advisory import parse_advisory, apply_status, parse_alloc

FIXDIR = Path(__file__).parent / "fixtures"
ADV = FIXDIR / "sample-advisory.xlsx"
ISIN_MAP = {"INE001A01001": "ALPHAMOT", "INE002B01012": "BETAPH", "INE004D01034": "DELTAB"}
QUOTES = {"DELTAB": Quote(160.0, -1.0)}

def _pf():
    return build_portfolio(parse_holdings(FIXDIR / "sample-holdings.xlsx"), ISIN_MAP, QUOTES, [])

def test_parse_shapes():
    adv = parse_advisory(ADV)
    assert [t.stock for t in adv.targets] == ["Delta Bank", "Alpha Motors"]
    assert adv.targets[0].sector == "Banking"
    assert [e.stock for e in adv.exits] == ["Beta Pharma", "Omega Ghost"]
    assert adv.buys[0].alloc_lo == 100000 and adv.buys[0].alloc_hi == 200000
    assert [m.label for m in adv.schedule] == ["Jul 2026", "Aug 2026"]

def test_parse_alloc():
    assert parse_alloc("₹5–7L") == (500000.0, 700000.0)
    assert parse_alloc("₹4-5L") == (400000.0, 500000.0)

def test_status_pending_review_and_baseline(tmp_path):
    adv = apply_status(parse_advisory(ADV), _pf(), tmp_path, date(2026, 7, 7))
    beta = next(e for e in adv.exits if e.stock == "Beta Pharma")
    omega = next(e for e in adv.exits if e.stock == "Omega Ghost")
    assert beta.status == "PENDING" and beta.source == "auto"
    assert omega.status == "REVIEW"
    assert json.loads((tmp_path / "advisory-baseline.json").read_text())["exits"]["Beta Pharma"]["baseline_qty"] == 50

def test_status_done_when_position_gone(tmp_path):
    apply_status(parse_advisory(ADV), _pf(), tmp_path, date(2026, 7, 7))   # snapshot baseline
    pf2 = _pf()
    pf2.positions = [p for p in pf2.positions if not p.name.startswith("BETA")]
    adv = apply_status(parse_advisory(ADV), pf2, tmp_path, date(2026, 7, 7))
    assert next(e for e in adv.exits if e.stock == "Beta Pharma").status == "DONE"

def test_manual_override(tmp_path):
    (tmp_path / "rebalance-status.json").write_text(json.dumps({"Omega Ghost": "DONE"}))
    adv = apply_status(parse_advisory(ADV), _pf(), tmp_path, date(2026, 7, 7))
    omega = next(e for e in adv.exits if e.stock == "Omega Ghost")
    assert omega.status == "DONE" and omega.source == "manual"

def test_buy_progress_and_current_month(tmp_path):
    adv = apply_status(parse_advisory(ADV), _pf(), tmp_path, date(2026, 8, 10))
    delta = adv.buys[0]
    assert delta.current_value == 200 * 160.0
    assert delta.progress_pct == 32.0            # 32000 / 100000
    assert [m.is_current for m in adv.schedule] == [False, True]
```

- [ ] **Step 2: Run to verify failure** — `pytest tests\test_advisory.py -v` → FAIL.

- [ ] **Step 3: app/advisory.py**

```python
from __future__ import annotations
import json, re
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
import openpyxl

STOP = {"LIMITED", "LTD", "LTD.", "INDIA", "THE", "AND", "OF", "CO", "COMPANY", "&"}

@dataclass
class ExitItem:
    stock: str; sector: str; category: str; cur_value: str; priority: str
    proceeds: str; reason: str
    status: str = "PENDING"; source: str = "auto"; isin: str | None = None

@dataclass
class BuyItem:
    stock: str; sector: str; category: str; alloc_lo: float; alloc_hi: float
    target_pct: str; conviction: str; entry: str; horizon: str; thesis: str
    current_value: float = 0.0; progress_pct: float = 0.0

@dataclass
class MonthBlock:
    label: str; exits_text: str = ""; buys_text: str = ""; is_current: bool = False

@dataclass
class TargetRow:
    num: int; stock: str; sector: str; status: str; cur_value: str
    target_pct: str; cagr: str; conviction: str; thesis: str

@dataclass
class Advisory:
    targets: list = field(default_factory=list); exits: list = field(default_factory=list)
    buys: list = field(default_factory=list); schedule: list = field(default_factory=list)

def _s(v): return "" if v is None else str(v).strip()

def _rows(ws): return list(ws.iter_rows(values_only=True))

def _find_header(rows, must_contain):
    for i, row in enumerate(rows):
        cells = [_s(c).lower() for c in row]
        if all(any(m in c for c in cells) for m in must_contain):
            idx = {}
            for j, c in enumerate(cells):
                idx[c] = j
            return i, cells
    return None, None

def _col(cells, *cands):
    for j, c in enumerate(cells):
        for cand in cands:
            if c.startswith(cand): return j
    return None

def parse_alloc(text: str) -> tuple[float, float]:
    nums = re.findall(r"[\d.]+", text.replace("–", "-"))
    lo = float(nums[0]) if nums else 0.0
    hi = float(nums[1]) if len(nums) > 1 else lo
    mult = 1e5 if "l" in text.lower() else (1e7 if "cr" in text.lower() else 1.0)
    return lo * mult, hi * mult

def parse_advisory(path: Path) -> Advisory:
    wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    adv = Advisory()
    for name in wb.sheetnames:
        rows = _rows(wb[name]); low = name.lower()
        if low.startswith("target"):
            hi_, cells = _find_header(rows, ["#", "stock", "sector"])
            if hi_ is None: continue
            c_num, c_stock = _col(cells, "#"), _col(cells, "stock")
            c_sec, c_stat = _col(cells, "sector"), _col(cells, "status")
            c_val, c_tgt = _col(cells, "cur"), _col(cells, "target")
            c_cagr, c_conv, c_th = _col(cells, "cagr"), _col(cells, "conv"), _col(cells, "investment")
            sector = ""
            for row in rows[hi_ + 1:]:
                num = row[c_num] if c_num is not None else None
                if isinstance(num, (int, float)):
                    adv.targets.append(TargetRow(int(num), _s(row[c_stock]), _s(row[c_sec]) or sector,
                        _s(row[c_stat]), _s(row[c_val]), _s(row[c_tgt]), _s(row[c_cagr]),
                        _s(row[c_conv]), _s(row[c_th])))
                else:
                    banner = next((_s(c) for c in row if "▶" in _s(c)), "")
                    if banner: sector = banner.replace("▶", "").strip().title()
        elif low.startswith("exit"):
            hi_, cells = _find_header(rows, ["stock", "priority", "reason"])
            if hi_ is None: continue
            c = {k: _col(cells, k) for k in ["stock", "sector", "category", "cur", "priority", "est", "reason"]}
            for row in rows[hi_ + 1:]:
                if not _s(row[c["stock"]]): continue
                adv.exits.append(ExitItem(_s(row[c["stock"]]), _s(row[c["sector"]]),
                    _s(row[c["category"]]), _s(row[c["cur"]]), _s(row[c["priority"]]),
                    _s(row[c["est"]]), _s(row[c["reason"]])))
        elif low.startswith("new buys"):
            hi_, cells = _find_header(rows, ["stock", "allocation"])
            if hi_ is None: continue
            c = {k: _col(cells, k) for k in ["stock", "sector", "category", "allocation",
                                             "target", "conv", "entry", "horizon", "investment"]}
            for row in rows[hi_ + 1:]:
                if not _s(row[c["stock"]]): continue
                lo_a, hi_a = parse_alloc(_s(row[c["allocation"]]))
                adv.buys.append(BuyItem(_s(row[c["stock"]]), _s(row[c["sector"]]),
                    _s(row[c["category"]]), lo_a, hi_a, _s(row[c["target"]]),
                    _s(row[c["conv"]]), _s(row[c["entry"]]), _s(row[c["horizon"]]),
                    _s(row[c["investment"]])))
        elif low.startswith("execution"):
            block = None
            for row in rows:
                cells = [_s(c) for c in row]
                month = next((c for c in cells if c.upper().startswith("MONTH ")), "")
                if month:
                    label = month.split("\n")[-1].strip()
                    block = MonthBlock(label=label); adv.schedule.append(block)
                if block:
                    for j, c in enumerate(cells):
                        if c.upper().startswith("EXITS THIS") and j + 1 < len(cells):
                            block.exits_text = cells[j + 1]
                        if c.upper().startswith("BUY/ADD") and j + 1 < len(cells):
                            block.buys_text = cells[j + 1]
    wb.close()
    return adv

def _norm(name: str) -> str:
    toks = re.sub(r"[^A-Z0-9 ]", " ", name.upper()).split()
    return " ".join(t for t in toks if t not in STOP)

def _match_isin(adv_name: str, cons) -> str | None:
    n = _norm(adv_name)
    if not n: return None
    for c in cons:
        h = _norm(c.name)
        if h == n or h.startswith(n) or n.startswith(h):
            return c.isin
    return None

def apply_status(adv: Advisory, portfolio, data_dir: Path, today: date) -> Advisory:
    data_dir.mkdir(parents=True, exist_ok=True)
    cons = portfolio.consolidated()
    by_isin = {c.isin: c for c in cons}
    bl_path = data_dir / "advisory-baseline.json"
    if bl_path.exists():
        baseline = json.loads(bl_path.read_text(encoding="utf-8"))
    else:
        baseline = {"created": today.isoformat(), "exits": {}}
        for e in adv.exits:
            isin = _match_isin(e.stock, cons)
            baseline["exits"][e.stock] = {"isin": isin,
                "baseline_qty": by_isin[isin].qty if isin and isin in by_isin else None}
        bl_path.write_text(json.dumps(baseline, indent=2), encoding="utf-8")
    ov_path = data_dir / "rebalance-status.json"
    overrides = json.loads(ov_path.read_text(encoding="utf-8")) if ov_path.exists() else {}
    for e in adv.exits:
        if e.stock in overrides:
            e.status, e.source = overrides[e.stock], "manual"; continue
        info = baseline["exits"].get(e.stock) or {"isin": _match_isin(e.stock, cons), "baseline_qty": None}
        e.isin = info["isin"]
        if e.isin is None:
            e.status, e.source = "REVIEW", "auto"; continue
        cur = by_isin.get(e.isin)
        bq = info.get("baseline_qty")
        if cur is None or cur.qty <= 0: e.status = "DONE"
        elif bq and cur.qty <= 0.75 * bq: e.status = "IN PROGRESS"
        else: e.status = "PENDING"
    for b in adv.buys:
        isin = _match_isin(b.stock, cons)
        b.current_value = by_isin[isin].value if isin and isin in by_isin else 0.0
        b.progress_pct = min(100.0, b.current_value / b.alloc_lo * 100) if b.alloc_lo else 0.0
    for m in adv.schedule:
        try:
            d = datetime.strptime(m.label, "%b %Y")
            m.is_current = (d.year, d.month) == (today.year, today.month)
        except ValueError:
            m.is_current = False
    return adv
```

- [ ] **Step 4: Run tests** — `pytest tests\test_advisory.py -v` → 6 passed; full suite green.

- [ ] **Step 5: Sanity vs the REAL advisory file**

Run: `.\.venv\Scripts\python -c "from pathlib import Path; from app.advisory import parse_advisory; a = parse_advisory(Path('report_data/Portfolio Advisory Report - 50 Stocks.xlsx')); print(len(a.targets), len(a.exits), len(a.buys), [m.label for m in a.schedule][:3])"`
Expected: `~50 ~25 ~10 ['Jul 2026', 'Aug 2026', ...]`.

- [ ] **Step 6: Commit**

```bash
git add app/advisory.py tests/test_advisory.py
git commit -m "feat(app): advisory report parser + rebalance status engine"
```

---

### Task 8: Data pipeline wiring + Overview view

**Files:**
- Modify: `app/dashboard.py` (replace shell loading + `view_overview`)

**Interfaces:**
- Consumes: all modules from Tasks 3–6.
- Produces: `load_portfolio() -> Portfolio | None` (cached on holdings-file mtime) used by every later view; working Overview.

- [ ] **Step 1: Replace dashboard.py data section** (between `theme.inject()` and the view functions)

```python
from datetime import datetime
from app import parser, mapping, prices, portfolio as pmod

HOLDINGS = DATA / "holdings.xlsx"

def _mtime(p: Path) -> float:
    return p.stat().st_mtime if p.exists() else 0.0

@st.cache_data(show_spinner="Reading holdings…")
def _load(mtime: float, extras_mtime: float):
    pr = parser.parse_holdings(HOLDINGS)
    isin_map = mapping.ensure_map(DATA)
    symbols = [isin_map.get(h.isin) for h in pr.holdings]
    quotes = prices.fetch_quotes([s for s in symbols if s])
    extras = pmod.load_extras(DATA / "extras.json")
    return pr, isin_map, quotes, extras

def load_portfolio():
    if not HOLDINGS.exists():
        return None
    pr, isin_map, quotes, extras = _load(_mtime(HOLDINGS), _mtime(DATA / "extras.json"))
    return pmod.build_portfolio(pr, isin_map, quotes, extras)

def onboarding_card():
    st.markdown("### 📂 No holdings file yet")
    st.markdown(
        f"1. Log in to **ICICI Direct** → Portfolio → download the holdings Excel (all members).\n"
        f"2. Save/drag it here as: `{HOLDINGS}`\n"
        f"3. Press **R** (or the ⟳ button top-right) to reload.")
    st.caption("The dashboard reads the member sheets (PK / CK / NK / DK) automatically.")
```

- [ ] **Step 2: Implement view_overview**

```python
def view_overview():
    pf = load_portfolio()
    if pf is None: onboarding_card(); return
    member = member_selector(pf.members)
    t = pf.totals(member)
    live = sum(1 for c in pf.consolidated(member) if c.price_live)
    total = len(pf.consolidated(member))
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Value", pmod.fmt_short(t.total_value), pmod.fmt_inr(t.total_value))
    c2.metric("Unrealised P/L", pmod.fmt_short(t.pl),
              pmod.fmt_pct(t.pl_pct) + " on known cost" if t.pl_pct is not None else "—")
    c3.metric("Day P/L", pmod.fmt_short(t.day_pl), pmod.fmt_pct(t.day_pl_pct))
    c4.metric("Equity / Extras", pmod.fmt_short(t.equity_value),
              " · ".join(f"{k} {pmod.fmt_short(v)}" for k, v in t.extras_by_class.items()) or "no extras")
    st.caption(f"Holdings file: {pf.asof:%d %b %Y %H:%M} · live prices {live}/{total} · "
               f"{'member ' + member if member else 'all members'}")
    left, right = st.columns(2)
    with left:
        st.subheader("Allocation")
        cons = pf.consolidated(member)
        rows = [{"Bucket": "Equity", "Value": t.equity_value}] + \
               [{"Bucket": k.upper(), "Value": v} for k, v in t.extras_by_class.items()]
        st.dataframe(rows, hide_index=True, use_container_width=True)
        st.subheader("Largest positions")
        for c in cons[:5]:
            st.markdown(f"**{c.name.title()}** — {pmod.fmt_short(c.value)}"
                        + ("" if c.price_live else " <span class='stale-badge'>stale</span>"),
                        unsafe_allow_html=True)
    with right:
        st.subheader("Top movers today")
        for c in pf.movers(member):
            cls = "up" if (c.day_pct or 0) >= 0 else "down"
            st.markdown(f"{c.name.title()} — <span class='{cls}'>{pmod.fmt_pct(c.day_pct)}</span>"
                        f" · {pmod.fmt_short(c.value)}", unsafe_allow_html=True)
    if pf.skipped:
        with st.expander(f"{len(pf.skipped)} rows skipped while reading the Excel"):
            for s in pf.skipped: st.text(s)
```

- [ ] **Step 3: Verify with fixture as data**

Run: `Copy-Item tests\fixtures\sample-holdings.xlsx data\holdings.xlsx` then start the app (`.\start-dashboard.ps1`), open http://localhost:8501 → Overview shows totals for PK+CK fixture, member chips [All][PK][CK] switch numbers, skipped-rows expander lists the junk row. Then delete `data\holdings.xlsx`, press R → onboarding card appears. Restore the fixture copy after.

- [ ] **Step 4: Commit**

```bash
git add app/dashboard.py
git commit -m "feat(app): cached data pipeline + overview view"
```

---

### Task 9: Holdings view

**Files:**
- Modify: `app/dashboard.py` (`view_holdings`)

- [ ] **Step 1: Implement view_holdings**

```python
def view_holdings():
    pf = load_portfolio()
    if pf is None: onboarding_card(); return
    member = member_selector(pf.members)
    q = st.text_input("Search", placeholder="Filter by name or symbol…")
    cons = pf.consolidated(member)
    if q:
        ql = q.lower()
        cons = [c for c in cons if ql in c.name.lower() or ql in (c.nse_symbol or "").lower()]
    rows = []
    for c in cons:
        rows.append({
            "Stock": c.name.title(),
            "NSE": c.nse_symbol or "—",
            "Qty": c.qty,
            "Avg Cost": round(c.avg_cost, 2) if c.avg_cost else None,
            "Price": round(c.price, 2),
            "Value": round(c.value),
            "P/L %": round(c.pl_pct, 1) if c.pl_pct is not None else None,
            "Day %": round(c.day_pct, 2) if c.day_pct is not None else None,
            "Held By": " + ".join(c.held_by),
            "Flags": ("⚠cost " if (c.avg_cost is None or c.cost_partial) else "")
                     + ("" if c.price_live else "stale"),
        })
    st.dataframe(rows, hide_index=True, use_container_width=True,
                 column_config={"Value": st.column_config.NumberColumn(format="localized"),
                                "P/L %": st.column_config.NumberColumn(format="%.1f%%"),
                                "Day %": st.column_config.NumberColumn(format="%.2f%%")})
    st.caption(f"{len(rows)} positions · ⚠cost = buy price missing in ICICI export · "
               "stale = price from your Excel, not live")
    if pf.extras:
        st.subheader("Other assets (from extras.json)")
        st.dataframe([{"Member": e.member, "Asset": e.label, "Class": e.asset_class,
                       "Value": round(e.value)} for e in pf.extras
                      if member is None or e.member == member],
                     hide_index=True, use_container_width=True)
```

- [ ] **Step 2: Verify** — with fixture data: table shows ALPHA consolidated (150 qty, Held By "CK + PK"), BETA flagged `⚠cost`, GAMMA flagged `stale`; search "alpha" filters; member chip PK removes DELTA.

- [ ] **Step 3: Commit** — `git add app/dashboard.py && git commit -m "feat(app): holdings view"`

---

### Task 10: Rebalance view

**Files:**
- Modify: `app/dashboard.py` (`view_rebalance`)

**Interfaces:**
- Consumes: `advisory.parse_advisory`, `advisory.apply_status`, `load_portfolio()`. Advisory file path: `DATA / "advisory.xlsx"`.

- [ ] **Step 1: Implement view_rebalance**

```python
from datetime import date as _date
from app import advisory as amod

def view_rebalance():
    pf = load_portfolio()
    if pf is None: onboarding_card(); return
    advp = DATA / "advisory.xlsx"
    if not advp.exists():
        st.markdown("### ⚖ No advisory report found")
        st.markdown(f"Save the *Portfolio Advisory Report* Excel as `{advp}` and reload.")
        return
    adv = amod.apply_status(amod.parse_advisory(advp), pf, DATA, _date.today())
    done = sum(1 for e in adv.exits if e.status == "DONE")
    st.caption(f"Exits: {done}/{len(adv.exits)} done · New buys: {len(adv.buys)} · "
               "auto-detected from your latest holdings; override via data/rebalance-status.json")
    tab_e, tab_b, tab_s, tab_t = st.tabs(["Exits", "New Buys", "Schedule", "Target Portfolio"])
    with tab_e:
        badge = {"DONE": "✅", "IN PROGRESS": "🔄", "PENDING": "⏳", "REVIEW": "❓"}
        st.dataframe([{"": badge[e.status], "Stock": e.stock, "Status": e.status,
                       "Src": e.source, "Priority": e.priority, "Category": e.category,
                       "Est. Proceeds": e.proceeds, "Reason": e.reason} for e in adv.exits],
                     hide_index=True, use_container_width=True)
        st.caption("❓ REVIEW = couldn't match this name to a holding — set it manually in rebalance-status.json")
    with tab_b:
        for b in adv.buys:
            st.markdown(f"**{b.stock}** ({b.sector}) — target {pmod.fmt_short(b.alloc_lo)}–"
                        f"{pmod.fmt_short(b.alloc_hi)} · deployed {pmod.fmt_short(b.current_value)}")
            st.progress(min(1.0, b.progress_pct / 100))
    with tab_s:
        for m in adv.schedule:
            head = f"**{m.label}**" + (" ← you are here" if m.is_current else "")
            st.markdown(head)
            if m.exits_text: st.markdown(f"- Exits: {m.exits_text}")
            if m.buys_text: st.markdown(f"- Buys: {m.buys_text}")
    with tab_t:
        st.dataframe([{"#": t.num, "Stock": t.stock, "Sector": t.sector, "Status": t.status,
                       "Target %": t.target_pct, "CAGR": t.cagr, "Conviction": t.conviction,
                       "Thesis": t.thesis} for t in adv.targets],
                     hide_index=True, use_container_width=True)
```

- [ ] **Step 2: Verify** — copy `tests\fixtures\sample-advisory.xlsx` to `data\advisory.xlsx`; Rebalance view shows Beta Pharma ⏳ PENDING, Omega Ghost ❓ REVIEW, Delta Bank progress bar ~32%, schedule months listed. Remove file → friendly card.

- [ ] **Step 3: Commit** — `git add app/dashboard.py && git commit -m "feat(app): rebalance tracker view"`

---

### Task 11: brief.py + Morning Brief view

**Files:**
- Create: `app/brief.py`, `tests/test_brief.py`
- Modify: `app/dashboard.py` (`view_brief`)

**Interfaces:**
- Produces: interface-block functions. Briefs saved to `BASE/briefs/YYYY-MM-DD.md`. One-pager read from `BASE/profile/one-pager.md`.

- [ ] **Step 1: tests/test_brief.py**

```python
from datetime import date
from pathlib import Path
from app.parser import parse_holdings
from app.prices import Quote
from app.portfolio import build_portfolio
from app.brief import portfolio_snapshot, build_prompt, find_claude
import app.brief as brief

FIX = Path(__file__).parent / "fixtures" / "sample-holdings.xlsx"

def _pf():
    return build_portfolio(parse_holdings(FIX),
                           {"INE001A01001": "ALPHAMOT"}, {"ALPHAMOT": Quote(300.0, 2.0)}, [])

def test_snapshot_compact_and_serialisable():
    import json
    snap = portfolio_snapshot(_pf())
    s = json.dumps(snap)
    assert "ALPHA" in s.upper() and snap["total_value"] > 0
    assert set(snap) == {"date_generated", "total_value", "members", "positions", "extras_by_class", "movers"}

def test_prompt_contains_rules_and_sections():
    p = build_prompt("MY ONE PAGER RULES", portfolio_snapshot(_pf()), date(2026, 7, 8))
    assert "MY ONE PAGER RULES" in p
    for sec in ["MARKETS OVERNIGHT", "IMPACT ON YOUR PORTFOLIO", "SUGGESTED ACTIONS"]:
        assert sec in p
    assert "8 July 2026" in p

def test_find_claude_missing(monkeypatch):
    monkeypatch.setattr(brief.shutil, "which", lambda _: None)
    assert find_claude() is None
```

- [ ] **Step 2: Run to verify failure** — FAIL (no module).

- [ ] **Step 3: app/brief.py**

```python
from __future__ import annotations
import json, shutil, subprocess
from datetime import date
from pathlib import Path

class BriefError(Exception):
    def __init__(self, message: str):
        super().__init__(message); self.message = message

def find_claude() -> str | None:
    return shutil.which("claude")

def portfolio_snapshot(pf) -> dict:
    cons = pf.consolidated()
    total = pf.totals()
    return {
        "date_generated": str(date.today()),
        "total_value": round(total.total_value),
        "members": {m: round(pf.totals(m).total_value) for m in pf.members},
        "positions": [{"name": c.name, "nse": c.nse_symbol, "qty": c.qty,
                       "value": round(c.value),
                       "pl_pct": round(c.pl_pct, 1) if c.pl_pct is not None else None,
                       "day_pct": round(c.day_pct, 2) if c.day_pct is not None else None,
                       "held_by": c.held_by}
                      for c in cons[:40]],
        "extras_by_class": {k: round(v) for k, v in total.extras_by_class.items()},
        "movers": [{"name": c.name, "day_pct": round(c.day_pct, 2)} for c in pf.movers()],
    }

def build_prompt(one_pager: str | None, snapshot: dict, today: date) -> str:
    rules = one_pager or "(No investor one-pager on file yet — keep advice generic and say so.)"
    return f"""You are the personal investment strategist for this portfolio's owner.
Today is {today.strftime('%-d %B %Y') if hasattr(today, 'strftime') else today}.

THE OWNER'S INVESTOR ONE-PAGER (treat as governing law):
{rules}

CURRENT PORTFOLIO (live values, INR):
{json.dumps(snapshot, indent=1)}

Write today's MORNING BRIEF in markdown with EXACTLY these sections:
## MARKETS OVERNIGHT — use web search for Indian & US markets since yesterday's close.
## IMPACT ON YOUR PORTFOLIO — only positions actually affected; reference qty and member.
## SUGGESTED ACTIONS — max 3, each checked against a specific one-pager rule (name it).
Direct, no fluff, no disclaimers beyond one line. All amounts in ₹ lakh/crore format."""

def generate_brief(pf, base_dir: Path) -> Path:
    exe = find_claude()
    if not exe:
        raise BriefError("Claude Code CLI not found. Install: npm install -g @anthropic-ai/claude-code "
                         "then run `claude` once to log in. Or: open this folder in Claude Cowork and say "
                         "\"write today's brief to briefs/\".")
    one_pager_path = base_dir / "profile" / "one-pager.md"
    one_pager = one_pager_path.read_text(encoding="utf-8") if one_pager_path.exists() else None
    prompt = build_prompt(one_pager, portfolio_snapshot(pf), date.today())
    try:
        out = subprocess.run([exe, "-p", "--allowed-tools", "WebSearch"],
                             input=prompt, capture_output=True, text=True,
                             encoding="utf-8", timeout=300)
    except subprocess.TimeoutExpired:
        raise BriefError("Brief generation timed out after 5 minutes. Try again, or generate it in "
                         "Claude Cowork instead.")
    if out.returncode != 0 or not out.stdout.strip():
        raise BriefError(f"Claude CLI error: {(out.stderr or 'no output').strip()[:300]} — "
                         "check you are logged in (`claude` then /login).")
    briefs = base_dir / "briefs"; briefs.mkdir(exist_ok=True)
    path = briefs / f"{date.today().isoformat()}.md"
    path.write_text(out.stdout, encoding="utf-8")
    return path
```

Note: `%-d` fails on Windows strftime — use `str(int(today.strftime('%d')))` composition instead. Final line for the date inside `build_prompt`:

```python
    day = f"{today.day} {today.strftime('%B %Y')}"
```
and interpolate `{day}` (the test asserts "8 July 2026"). The file must use this version.

- [ ] **Step 4: Run tests** — `pytest tests\test_brief.py -v` → 3 passed.

- [ ] **Step 5: Implement view_brief in dashboard.py**

```python
from app import brief as bmod

def view_brief():
    pf = load_portfolio()
    if pf is None: onboarding_card(); return
    briefs_dir = BASE / "briefs"
    files = sorted(briefs_dir.glob("*.md"), reverse=True) if briefs_dir.exists() else []
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("⚡ Generate Morning Brief", type="primary", use_container_width=True):
            try:
                with st.spinner("Claude is reading your portfolio and overnight markets… (1–3 min)"):
                    path = bmod.generate_brief(pf, BASE)
                st.success(f"Saved {path.name}")
                st.rerun()
            except bmod.BriefError as e:
                st.error(e.message)
        if not bmod.find_claude():
            st.warning("Claude CLI not detected — the button will explain the fix.")
    with col1:
        if not files:
            st.markdown("### ⚡ No briefs yet")
            st.markdown("Click **Generate Morning Brief** — Claude reads your one-pager, your live "
                        "portfolio and overnight news, and writes the brief here.")
        else:
            pick = st.selectbox("Brief date", [f.stem for f in files])
            st.markdown((briefs_dir / f"{pick}.md").read_text(encoding="utf-8"))
```

- [ ] **Step 6: Verify** — app runs; Brief view shows empty-state; clicking Generate either produces a real brief (dev machine has claude CLI logged in) or the actionable BriefError card. Generate once for real with fixture data; confirm `briefs/<today>.md` exists and renders.

- [ ] **Step 7: Commit**

```bash
git add app/brief.py tests/test_brief.py app/dashboard.py
git commit -m "feat(app): morning brief via claude -p + brief view"
```

---

### Task 12: Profile view

**Files:**
- Modify: `app/dashboard.py` (`view_profile`)

- [ ] **Step 1: Implement**

```python
def view_profile():
    p = BASE / "profile" / "one-pager.md"
    if p.exists():
        st.markdown(p.read_text(encoding="utf-8"))
        st.caption(f"Source: {p} — edit the file in any editor; every brief obeys it.")
    else:
        st.markdown("### 👤 No investor one-pager yet")
        st.markdown(
            "This file makes every brief and suggestion *yours*.\n\n"
            "1. Open a new chat in Claude and paste the interview prompt "
            "(`prompts/investor-interview-prompt.md` in the repo, or ask Hemant).\n"
            "2. Answer ~20–30 min of questions (voice input is fastest).\n"
            f"3. Save the result as `{p}` and reload this page.")
```

- [ ] **Step 2: Verify** — without file: instructions card. Create `profile/one-pager.md` with the sample one-pager content → renders. Delete after.

- [ ] **Step 3: Commit** — `git add app/dashboard.py && git commit -m "feat(app): investor profile view"`

---

### Task 13: Handoff package (CLAUDE.md, README-SIR, launchers, setup)

**Files:**
- Create: `CLAUDE.md`, `README-SIR.md`, `Start Dashboard.command`, `setup.sh`, `setup.ps1`
- Modify: `README.md` (add Phase 3 section)

- [ ] **Step 1: CLAUDE.md** (full content)

```markdown
# Investor OS — System Guide (read me first, Claude)

This folder is Paresh Karia's personal investment dashboard. You (Claude Code /
Cowork) are its maintenance interface. The owner is non-technical — when he asks
for changes, do them end-to-end and verify before reporting done.

## How it works
- `data/holdings.xlsx` — weekly ICICI Direct export. Member sheets (PK/CK/NK/DK)
  are parsed by `app/parser.py` (ISIN is the key; symbols in the file are ICICI
  codes, NOT NSE tickers).
- `app/mapping.py` maps ISIN → NSE symbol (cache `data/isin-map.csv`; manual fixes
  in `data/overrides.csv` — isin,symbol — which always win).
- `app/prices.py` fetches live prices from Yahoo Finance (`SYMBOL.NS`). On any
  failure the dashboard falls back to the CMP inside the Excel and shows "stale".
- `app/portfolio.py` consolidates across members and computes all totals.
- `data/advisory.xlsx` + `app/advisory.py` power the Rebalance view. Baseline
  quantities are frozen in `data/advisory-baseline.json` (delete it to re-baseline).
  Manual status overrides: `data/rebalance-status.json` e.g. {"Oravel Stays (OYO)": "DONE"}.
- `app/brief.py` generates the morning brief by running `claude -p` (the owner's
  Claude subscription). Briefs land in `briefs/YYYY-MM-DD.md`.
- `profile/one-pager.md` — the owner's investor profile. Injected into every brief.
- Run tests with: `python -m pytest` (fixtures are fake data in tests/fixtures/).

## Weekly ritual (owner does this)
Download holdings Excel from ICICI Direct → replace `data/holdings.xlsx` → open
the dashboard (Start Dashboard.command).

## Maintenance playbook — likely requests and what to do
- "Dashboard won't start" → run `./setup.sh`, then `Start Dashboard.command`;
  check Python 3.11+ exists (`python3 --version`).
- "A stock shows stale price" → its ISIN is missing from the NSE map. Add a line
  to `data/overrides.csv`. Unlisted holdings (pre-IPO etc.) stay stale by design.
- "ICICI changed the Excel format" → adjust `_find_header`/column detection in
  `app/parser.py`; run `python -m pytest tests/test_parser.py` before finishing.
- "Add a family member" → nothing to do; any new member sheet in the Excel is
  picked up automatically.
- "Add gold/FD/MF" → edit `data/extras.json`:
  [{"member":"PK","label":"SGB 2022","asset_class":"gold","value":500000,"invested":400000}]
- "Change the brief style" → edit build_prompt in `app/brief.py`.
- "Mark an exit as done" → `data/rebalance-status.json`.
- NEVER commit anything in data/, briefs/, profile/ — real financial data; the
  GitHub repo is public.
```

- [ ] **Step 2: README-SIR.md**

```markdown
# Investor OS — How to use (1 page)

## Every week (2 minutes)
1. Log in to ICICI Direct → Portfolio → download the holdings Excel (all members).
2. Drag the file into the `data` folder, replacing `holdings.xlsx`.
3. Double-click **Start Dashboard** — your browser opens with everything updated.

## Every morning (optional)
Open the dashboard → **Morning Brief** → click **⚡ Generate Morning Brief**.
Claude reads your rules, your live portfolio and overnight news, and writes your brief.

## Switching family members
The chips at the top — All / PK / CK / NK / DK — switch every number on the page.

## If something breaks
Open this folder in Claude Cowork (or type `claude` in Terminal here) and simply
describe the problem in plain English. The system documentation (CLAUDE.md) tells
Claude how everything works. Example: "the dashboard shows a stale price for
Tata Power — fix it."

## Your rules file
`profile/one-pager.md` is YOUR document — open it in any editor and change your
rules anytime. Every brief obeys whatever it says.
```

- [ ] **Step 3: Start Dashboard.command + setup.sh + setup.ps1**

`Start Dashboard.command`:
```bash
#!/bin/bash
cd "$(dirname "$0")"
if [ ! -d .venv ]; then bash setup.sh; fi
./.venv/bin/python -m streamlit run app/dashboard.py
```

`setup.sh`:
```bash
#!/bin/bash
cd "$(dirname "$0")"
PY=$(command -v python3.12 || command -v python3.11 || command -v python3)
"$PY" -m venv .venv
./.venv/bin/pip install -r requirements.txt
mkdir -p data briefs profile
echo "Setup complete. Double-click 'Start Dashboard.command' to launch."
```

`setup.ps1`:
```powershell
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
New-Item -ItemType Directory -Force data, briefs, profile | Out-Null
Write-Host "Setup complete. Run .\start-dashboard.ps1 to launch."
```

Mark executable bits in git (works from Windows):
```bash
git add "Start Dashboard.command" setup.sh
git update-index --chmod=+x "Start Dashboard.command" setup.sh
```

- [ ] **Step 4: README.md — replace the Roadmap section's Phase 3 line and add a "Running the real dashboard" section** pointing to setup.ps1/setup.sh, the data-file drop, and README-SIR.md.

- [ ] **Step 5: Commit**

```bash
git add CLAUDE.md README-SIR.md "Start Dashboard.command" setup.sh setup.ps1 README.md
git commit -m "docs: handoff package — CLAUDE.md playbook, owner guide, launchers"
```

---

### Task 14: E2E with real data + final verification + push

**Files:**
- Modify: only if fixes needed.

- [ ] **Step 1: Full test suite** — `.\.venv\Scripts\python -m pytest -v` → all green.

- [ ] **Step 2: Real-data E2E (local only, never committed)**

```powershell
Copy-Item "report_data\Current Portfolio - All Members (1).xlsx" data\holdings.xlsx
Copy-Item "report_data\Portfolio Advisory Report - 50 Stocks.xlsx" data\advisory.xlsx
.\start-dashboard.ps1
```
Walk all 5 views. Checklist:
- Overview totals ≈ the Excel's own numbers (~₹4.79 Cr market value ballpark, moves with live prices); live-price count high (most of the 66 names mapped); member chips change every number.
- Holdings: ~66 consolidated rows, "Held By" matches spot-checks (ICICI Bank = CK + NK + PK); HDFC Bank shows its quirky avg cost without breaking; unlisted names (Oravel/ICSA) show `stale`.
- Rebalance: exits statuses sensible (all PENDING on first run — baseline snapshots); Gensol/Karuturi rows present; buys progress bars; "you are here" on Jul 2026.
- Morning Brief: generate once for real → brief cites actual positions.
- Profile: instructions card (Sir hasn't done the interview yet).

- [ ] **Step 3: git hygiene check** — `git status --short` must show NO files from data/, briefs/, profile/, report_data/.

- [ ] **Step 4: Push**

```bash
git push
```

---

## Self-Review (done at plan-writing time)

- **Spec coverage:** §3 layout → Tasks 1, 13 · §4.1 parser → T3 · §4.2 mapping → T4 · §4.3 prices → T5 · §4.4 portfolio/extras → T6 · §4.5 advisory → T7 · §5 views 1–5 → T8–T12 · §6 briefs → T11 · §7 handoff → T13 · §8 error cards → onboarding/BriefError/friendly cards in T8–T12 · §9 testing → per-task pytest + T14 E2E. No gaps.
- **Placeholder scan:** clean — the two deliberate "wrong version shown, use the corrected version" notes (fmt_inr in T6, strftime in T11) both include the final code.
- **Type consistency:** `ParseResult/Holding` (T3) consumed by T6/T7/T11 with same fields; `Quote` (T5) used in T6/T7 tests; `Portfolio.consolidated()/totals()/movers()` signatures consistent across T8–T11; status strings "DONE|IN PROGRESS|PENDING|REVIEW" consistent between T7 and T10; paths (`data/holdings.xlsx`, `data/advisory.xlsx`, `briefs/`, `profile/one-pager.md`) consistent across T8–T13.
```
