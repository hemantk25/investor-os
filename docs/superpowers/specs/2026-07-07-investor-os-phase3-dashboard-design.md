# Design — Investor OS Phase 3: Real Local-First Dashboard

**Date:** 2026-07-07
**Author:** Hemant (with Claude)
**Status:** Approved in discussion; pending user spec review

---

## 1. Background & Goal

Phase 1 (demo mockup) is done and approved in direction. Phase 3 builds the
**real dashboard**: a local-first Streamlit app that runs on Paresh Karia's
Mac, reads the family's actual ICICI Direct holdings from a weekly Excel
download, shows live NSE prices, and generates AI morning briefs through
Claude Code on his existing Claude Pro subscription — no servers, no API
keys, no recurring cost.

Decided this cycle (with CEO buy-in):
- **Dashboard first**; Telegram bot is the next cycle (Phase 4).
- **Local-first**: everything runs on Sir's machine; Claude Code (Pro
  subscription) is both the AI engine and the maintenance interface after
  Hemant hands off.
- **Data scope**: equity book auto-ingested from the ICICI Excel; other
  asset classes (MF/gold/FD/cash) via a hand-edited `extras.json`.
- **Rebalance Tracker** against the "Portfolio Advisory Report — 50
  Stocks" Excel is in scope for v1.

## 2. Facts About the Real Data (verified 2026-07-07)

`Current Portfolio - All Members (1).xlsx` (ICICI Direct export, weekly):
- Sheets: `Summary`, `Consolidated`, `PK`, `CK`, `NK`, `DK`.
- Member sheets have a title row, then header row, then data rows with
  columns: `Sr. | Stock Name | Symbol | ISIN | Qty Held | CMP (₹) | % Chg |
  Market Value (₹) | Avg Buy Price (₹) | Total Cost (₹) | Unrealised
  Gain/Loss (₹) | Gain/Loss %`.
- **Symbols are ICICI Direct codes** (e.g. HDFBAN, LARTOU), NOT NSE
  tickers. **ISIN is the reliable key.**
- Known quirks the parser MUST handle: some rows have no avg buy price
  (Summary footnote: "stocks with no purchase…"); unlisted/suspended
  holdings exist (e.g. Oravel Stays pre-IPO, ICSA); split/bonus-distorted
  avg prices (HDFC Bank avg ₹12.99).
- Family scale: 146 positions, 66 unique stocks, ~₹2.49 Cr cost →
  ~₹4.79 Cr market value.

`Portfolio Advisory Report - 50 Stocks.xlsx`:
- Sheets: `Target 50-Stock Portfolio` (sector-grouped, status KEEP /
  KEEP (TRIM) / etc., target %, conviction stars, thesis),
  `Exit List (25 Stocks)` (category, priority, est. proceeds, reason),
  `New Buys (10 Stocks)` (allocation ₹ range, target %, entry strategy,
  horizon), `Execution Schedule` (month-by-month from Jul 2026),
  `Returns Projection`.

Real files live in `report_data/` locally and are **gitignored — the repo
is public and must never contain real data.**

## 3. Repo vs. Instance Separation

- **Repo (`investor-os`, public):** all code under `app/`, tests under
  `tests/`, a committable synthetic fixture Excel (fake data, same
  format), docs. No real data ever.
- **Instance (Sir's Mac, private folder `investor-os/`):** the app code +
  his real files:

```
investor-os/                     # instance folder on Sir's Mac
├── CLAUDE.md                    # system docs + maintenance playbook
├── README-SIR.md                # one-page user guide (weekly ritual)
├── app/                         # the code (from repo)
│   ├── dashboard.py             # Streamlit entry point (UI only)
│   ├── parser.py                # ICICI Excel → Holding objects
│   ├── mapping.py               # ISIN → NSE ticker (NSE list + overrides)
│   ├── prices.py                # yfinance batch quotes, 5-min cache
│   ├── portfolio.py             # merge holdings + extras; member filters; totals
│   ├── advisory.py              # advisory.xlsx → rebalance model
│   ├── brief.py                 # build prompt, run `claude -p`, save brief
│   └── theme.py                 # brand CSS (gold/navy, matches demo)
├── data/
│   ├── holdings.xlsx            # Sir drops the weekly ICICI download here
│   ├── advisory.xlsx            # the 50-stock advisory report
│   ├── extras.json              # manual MF/gold/FD/cash lines (member-tagged)
│   ├── isin-map.csv             # cached NSE ISIN↔ticker map (auto-built)
│   ├── overrides.csv            # manual ISIN→ticker fixes (rarely needed)
│   ├── advisory-baseline.json   # auto-created on first advisory parse (§4.5)
│   └── rebalance-status.json    # optional manual status overrides (§4.5)
├── briefs/                      # YYYY-MM-DD.md, newest shown in dashboard
├── profile/
│   └── one-pager.md             # Sir's investor one-pager (when he does it)
├── .streamlit/config.toml       # dark theme
├── Start Dashboard.command      # macOS double-click launcher
├── start-dashboard.ps1          # Windows dev launcher
└── setup.sh / setup.ps1         # one-time: venv + pip install
```

## 4. Data Pipeline

1. **parser.py** reads `data/holdings.xlsx`. Source of truth = the four
   member sheets (auto-detected: any sheet whose header row matches the
   ICICI column signature; member id = sheet name). The `Consolidated`
   and `Summary` sheets are ignored (recomputed, never trusted).
   Output: list of `Holding {member, name, icici_symbol, isin, qty,
   avg_cost|None, excel_cmp, excel_asof}`. Rows without ISIN or qty ≤ 0
   are skipped and reported. Missing avg cost → `cost_known=False`
   (position shows value but is excluded from P/L% and flagged ⚠ in UI).
2. **mapping.py** maps ISIN → NSE ticker. First run downloads NSE's
   equity list (EQUITY_L.csv) and caches `data/isin-map.csv`; refresh
   only on demand ("Refresh symbol map" button). `data/overrides.csv`
   wins over the cache. Unmapped ISINs (unlisted/suspended) fall back to
   Excel CMP permanently and are badged "unlisted/stale".
3. **prices.py** batch-fetches `.NS` tickers via yfinance with a 5-minute
   in-process cache. Any fetch failure → Excel CMP fallback + "stale"
   badge. Day-change % comes from yfinance (prev close), else Excel
   `% Chg`.
4. **portfolio.py** merges parsed holdings + `extras.json` (schema:
   `[{member, label, asset_class: mf|gold|debt|cash, value, invested?,
   note?}]`), computes per-member and consolidated views (consolidation
   merges equities by ISIN: sum qty, weighted avg cost where known,
   "Held By" list), and all derived numbers (totals, unrealised P/L,
   day P/L, allocation, movers). Indian formatting (₹, lakh/crore)
   everywhere.
5. **advisory.py** parses the four advisory sheets into a rebalance
   model. Exit status auto-derived: a stock on the exit list whose
   consolidated qty is now 0 → DONE; qty reduced ≥ 25% vs the report
   baseline → IN PROGRESS; else PENDING. New-buy progress = current
   consolidated value in that stock vs its allocation band. Baseline
   quantities are snapshotted into `data/advisory-baseline.json` on
   first parse (so later holdings changes measure progress against a
   fixed start point). A manual `data/rebalance-status.json` can
   override any row's status.

## 5. Views (Streamlit, branded like the approved demo)

Member chips **[All] [PK] [CK] [NK] [DK]** in the header; every view
recomputes for the selection. Views (sidebar):

1. **Overview** — hero metrics (Total Value, Unrealised P/L on known-cost
   positions, Day P/L, per-class split incl. extras), allocation donut,
   top movers (day %), largest positions, data freshness line (Excel file
   date + price fetch time).
2. **Holdings** — sortable table grouped by asset class; consolidated
   view shows "Held By"; ⚠ flag where cost unknown; stale/unlisted
   badges; search box.
3. **Rebalance** — three tabs: Exits (25 rows, status DONE/IN
   PROGRESS/PENDING with auto/manual source), New Buys (10 rows,
   deployment progress bars vs allocation band), Schedule (months with
   "you are here" on the current month).
4. **Morning Brief** — renders newest `briefs/*.md`; date picker for past
   briefs; **[⚡ Generate Morning Brief]** runs brief.py; shows spinner
   and streams the file in when done. If `claude` CLI is missing or not
   logged in: friendly card with the exact one-line fix, plus the manual
   fallback ("open this folder in Claude Code / Cowork and say: write
   today's brief").
5. **Profile** — renders `profile/one-pager.md`; if absent, shows the
   interview instructions (link to prompts file) instead.

## 6. AI Brief Generation (no API key)

`brief.py`: builds a prompt containing (a) the one-pager (if present),
(b) a compact JSON snapshot of the consolidated + per-member portfolio
with live prices, (c) today's date, (d) instructions matching the demo's
brief format (MARKETS OVERNIGHT / IMPACT ON YOUR PORTFOLIO / SUGGESTED
ACTIONS checked against the one-pager rules). Runs
`claude -p <prompt> --allowed-tools WebSearch` as a subprocess (Sir's
logged-in Claude Code CLI, billed to his Pro subscription), writes output
to `briefs/YYYY-MM-DD.md` (overwrite same-day). Timeout 5 minutes;
non-zero exit → error card with stderr summary and the manual fallback.
No scheduling in v1 (that is Phase 4); Sir clicks the button with his
morning tea.

## 7. Handoff Package

- **CLAUDE.md** (instance folder): what each file/module does, the data
  flow, the weekly ritual, a maintenance playbook of likely asks
  ("dashboard won't start", "add a new family member", "ICICI changed
  the Excel format", "add a stock to overrides") each phrased as
  what-to-tell-Claude-Code.
- **README-SIR.md**: one page, non-technical. Weekly ritual: log into
  ICICI Direct → download holdings Excel → drag into `data/` (replace) →
  double-click Start Dashboard.
- **Start Dashboard.command** (chmod +x; activates venv, runs
  `streamlit run app/dashboard.py`, opens browser) and
  **start-dashboard.ps1** for the Windows dev machine.
- **setup.sh / setup.ps1**: one-time environment setup (Python check,
  venv, `pip install -r requirements.txt`).

## 8. Error Handling Principles

- No stack traces in the UI. Every failure state renders a card that
  says what happened and what to do (in Sir's terms).
- Missing `holdings.xlsx` → onboarding card with the download ritual.
- Parser skips bad rows and lists them in an expandable "rows skipped"
  panel — never refuses the whole file for one bad row.
- All network calls (NSE list, yfinance) are best-effort with cached/
  Excel fallbacks; the dashboard must render fully offline.

## 9. Testing & Verification

- **pytest** unit tests for parser.py (against a committable synthetic
  fixture Excel with fake data replicating the ICICI format incl. the
  quirks: missing avg cost, unlisted ISIN, member sheets), mapping.py
  (override precedence, unmapped fallback), portfolio.py (consolidation
  math, member filter, extras merge, weighted avg cost), advisory.py
  (status derivation vs baseline).
- **Manual E2E** on the dev machine against the real `report_data/`
  files (copied into a local instance folder, never committed).
- **Handoff verification on Sir's Mac**: setup script run, real Excel
  drop, dashboard opens, prices live, brief generates via his Claude
  login.
- Brief generation is smoke-tested on the dev machine with Hemant's own
  Claude Code login.

## 10. Out of Scope (v1 / this cycle)

- Telegram bot, scheduled/push briefs, LaunchAgent (Phase 4).
- ICICI Breeze API integration (kept as a future option).
- TradingView watchlist ingestion (future; format already known: txt).
- MF CAS statement parsing; extras.json covers those classes manually.
- Multi-broker support; cloud anything; Supabase.

## 11. Risks & Mitigations

- **`claude -p` behaviour differs by version / not logged in** →
  detection + manual Cowork fallback path is first-class, not an
  afterthought.
- **yfinance breakage/rate limits** → batch fetch, 5-min cache, Excel
  CMP fallback; dashboard never depends on it to render.
- **ICICI changes export format** → header-signature detection + a
  CLAUDE.md playbook entry telling Sir to ask Claude Code to adapt
  parser.py (tests make that safe).
- **NSE list format changes** → overrides.csv escape hatch.
