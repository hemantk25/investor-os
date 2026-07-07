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
- "Only some holdings show up / totals look low" → the member sheets in the Excel
  have rows with only a stock name and no ISIN/qty (incomplete export). Get a
  complete export from ICICI Direct, or see the note in
  `docs/superpowers/specs/2026-07-07-investor-os-phase3-dashboard-design.md`.
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
