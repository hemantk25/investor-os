# Investor OS — System Guide (read me first, Claude)

This folder is Paresh Karia's personal investment dashboard. You (Claude Code /
Cowork) are its maintenance interface. The owner is non-technical — when he asks
for changes, do them end-to-end and verify before reporting done.

## How it works
- `data/holdings.xlsx` — weekly ICICI Direct export. Member sheets (PK/CK/NK/DK)
  are parsed by `app/parser.py` (ISIN is the key; symbols in the file are ICICI
  codes, NOT NSE tickers).
- Holdings are file-only in the visible dashboard. The source of truth is
  `data/holdings.xlsx`; old manual holding/sell events may remain in SQLite but
  are ignored for current totals and UI.
- `app/mapping.py` maps ISIN → NSE symbol (cache `data/isin-map.csv`; manual fixes
  in `data/overrides.csv` — isin,symbol — which always win).
- `app/prices.py` fetches live prices from Yahoo Finance (`SYMBOL.NS`). On any
  failure the dashboard falls back to the CMP inside the Excel and shows "stale".
- `app/portfolio.py` consolidates across members and computes all totals.
- `app/server.py` is the Flask app. It renders Jinja templates in `app/templates/`
  with the prebuilt Tailwind CSS file at `app/static/app.css`.
- `app/view_models.py` and `app/charts.py` turn portfolio/advisory data into
  template-ready dictionaries and inline SVG chart paths.
- `app/storage.py` owns the private SQLite database at `data/investor_os.sqlite`
  for holding events, portfolio snapshots, watchlists, quote snapshots, news,
  security metadata, and app state.
- `app/watchlist.py` manages the TradingView-style local watchlist workspace,
  boards, filters, quotes, and TXT import/export. There is no direct TradingView
  API dependency.
- `data/advisory.xlsx` + `app/advisory.py` power the Rebalance view. Baseline
  quantities are frozen in `data/advisory-baseline.json` (delete it to re-baseline).
  Manual status overrides: `data/rebalance-status.json` e.g. {"Oravel Stays (OYO)": "DONE"}.
- `app/news.py` fetches market and portfolio-related news from Google News RSS
  and Yahoo Finance feeds, normalizes/dedupes links, and stores them in SQLite.
- `app/goal.py` powers the Goal page: required path, implied CAGR, market-cap
  bands, compliance checks, and security metadata refresh.
- `app/brief.py` generates the morning brief by running `claude -p` (the owner's
  Claude subscription). Briefs land in `briefs/YYYY-MM-DD.md`; the UI currently
  shows Market Brief plus the Python-computed Impact table and future-impact
  signals. Older brief files may contain hidden My Stocks/Impact Notes sections.
- `app/refresh.py` is the local refresh entrypoint. `python -m app.refresh`
  updates watchlist quotes, portfolio snapshots, security metadata, news, and
  `last_refresh` state.
- `data/goal.json` is the editable goal config. Defaults are seeded on first
  Goal-page visit: target value, target date, expected CAGR, monthly SIP,
  large/mid/small band targets, and small-cap max.
- `profile/one-pager.md` — the owner's investor profile. Injected into every brief.
- Run tests with: `python -m pytest` (fixtures are fake data in tests/fixtures/).

Visible side-nav pages are: Overview, Holdings, Watchlist, Morning Brief, News,
Rebalance, and Goal. `/profile` still exists and is linked from Goal/Brief, but
it is intentionally not in the side nav.

## Weekly ritual (owner does this)
Download holdings Excel from ICICI Direct → replace `data/holdings.xlsx` → open
the dashboard (`start-dashboard.ps1` on Windows).

## Local refresh
Use the Overview or Watchlist refresh button, the News page's **Refresh news**
button, or run:

`python -m app.refresh`

This is the same command a future Windows Task Scheduler job should call. It is
manual/local for now; there is no always-on service.

## Maintenance playbook — likely requests and what to do
- "Dashboard won't start" → run `./setup.sh`, then `Start Dashboard.command`;
  check Python 3.11+ exists (`python3 --version`). The app serves at
  `http://127.0.0.1:8555`.
- "Change how a page looks" → edit the matching template in `app/templates/`.
  If you changed Tailwind classes, rebuild CSS with:
  `npx tailwindcss@3 -c app/tailwind/tailwind.config.js -i app/tailwind/input.css -o app/static/app.css --minify`.
  Text, copy, and Python logic changes usually need no CSS rebuild.
- "A stock shows stale price" → its ISIN is missing from the NSE map. Add a line
  to `data/overrides.csv`. Unlisted holdings (pre-IPO etc.) stay stale by design.
- "Only some holdings show up / totals look low" → the member sheets in the Excel
  have rows with only a stock name and no ISIN/qty (incomplete export). Get a
  complete export from ICICI Direct, or see the note in
  `docs/superpowers/specs/2026-07-07-investor-os-phase3-dashboard-design.md`.
- "ICICI changed the Excel format" → adjust `_find_header`/column detection in
  `app/parser.py`; run `python -m pytest tests/test_parser.py` before finishing.
- "Add a family member" → nothing to do; any new member sheet in the Excel is
  picked up automatically.
- "Add/edit/sell a holding" → do not use manual UI; it is intentionally disabled.
  Replace `data/holdings.xlsx` with the latest broker export.
- "Add gold/FD/MF" → edit `data/extras.json`:
  [{"member":"PK","label":"SGB 2022","asset_class":"gold","value":500000,"invested":400000}]
- "Change watchlists" → use `/watchlist`; items/boards live in SQLite. TXT
  import/export is TradingView-compatible comma-separated symbols such as
  `NSE:RELIANCE,NASDAQ:MSFT`.
- "News feels stale" → click **Refresh news** on `/news`, or run
  `python -m app.refresh`. News is fetched and stored locally; page loads do not
  need to refetch.
- "Change the brief style" → edit `build_prompt` in `app/brief.py`; keep the UI
  focused on Market Brief and Impact unless the owner asks for more sections.
- "Change the goal target/date/bands" → edit `data/goal.json`. If it is corrupt,
  the Goal page renders with defaults and shows a friendly warning.
- "Goal market-cap bands are unclassified" → run `python -m app.refresh` so
  security metadata can fill from Yahoo Finance; some unavailable rows are normal.
- "Mark an exit as done" → `data/rebalance-status.json`.
- NEVER commit anything in `data/`, `briefs/`, or `profile/` — real financial
  data; the GitHub repo is public.
