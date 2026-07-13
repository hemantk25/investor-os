# Design — Investor OS: Drop-in Data Folders, One-Shot Refresh, Daily-Start Prompt

**Date:** 2026-07-13
**Status:** Approved in discussion; pending user spec review
**Builds on:** feature-complete v1 at `a7eee5b` (branch `phase3-dashboard`, 122 tests green).

## 1. Decisions (locked with Hemant)

- **Telegram/Phase-4 is removed from scope permanently.** No code exists; strike
  it from README/CLAUDE.md roadmaps. The product is local-first: the owner opens
  the dashboard via Claude Code / a launcher; push alerts have no role.
- **Root cleanup:** video-era reference material moves under `docs/`; the flat
  `data/` becomes a drop-box structure; `report_data/` is retired.
- **Newest-file-wins ingestion:** the owner never renames a download.
- **Watchlists: NO TXT drop-box.** TradingView's export needs a premium
  subscription the owner doesn't have. Instead: the owner screenshots his
  TradingView watchlist, pastes the image into Claude Code, and says "add this
  watchlist" — Claude reads the symbols from the screenshot and imports them
  via a small CLI (`python -m app.watchlist_cli`). Documented in CLAUDE.md +
  README-SIR as the taught extra step.
- **One-shot refresh + daily-start prompt:** one command loads everything and
  reports freshness in plain English; a paste-able prompt (and a double-click
  launcher) wraps it.

## 2. Folder layout

**Root after cleanup** (repo): `app/ data/ briefs/ profile/ prompts/ docs/
tests/` + `requirements.txt`, setup/start/build scripts, `CLAUDE.md`,
`README.md`, `README-SIR.md`, `PROMPT_DAILY_START.md`,
`PROMPT_FOR_CLAUDE_DASHBOARD.md`, `GOOGLE_DRIVE_HANDOFF.md`,
`prepare-drive-handoff.ps1`.

Moves (git mv): `AI-Advisor-Build-Guide.pdf`, `ASSET INVESTOR PROMPT.md`(+.docx),
`cowork-investor-os-system-prompt.md`(+.docx) → `docs/reference/`;
`demo/` → `docs/demo/`. `prompts/` stays at root (UI copy references it).
`report_data/` (gitignored, real data): its two Excels are copied into the new
drop-boxes below, then the folder is deleted locally; the `.gitignore` entry
stays as a guard.

**New `data/` layout:**
```
data/
  holdings/      # ICICI holdings exports, any *.xlsx name — newest wins
  advisory/      # advisory report exports, any *.xlsx name — newest wins
  goal.json extras.json overrides.csv isin-map.csv investor_os.sqlite
  advisory-baseline.json rebalance-status.json        # app-managed, flat
```
(Watchlists live in SQLite only; updates come via the dashboard UI or the
screenshot→Claude→`watchlist_cli` flow — no file drop-box.)

## 3. Resolution rules (`app/datafiles.py`, new small module)

- `latest_holdings(data_dir) -> Path | None`: newest-mtime `*.xlsx` among
  `data/holdings/*` ∪ flat `data/holdings.xlsx` (back-compat — flat file
  competes on mtime). Same for `latest_advisory` (subfolder `advisory/`, flat
  `advisory.xlsx`).
- `app/watchlist_cli.py` (new, tiny): `python -m app.watchlist_cli import
  "NSE:RELIANCE,NASDAQ:MSFT" --market India --category Stocks --group Custom`
  → wraps the existing `watchlist.import_text`; prints how many symbols were
  added/skipped. This is the command Claude Code runs after reading a
  watchlist screenshot the owner pastes.
- Temp/lock files (`~$*`, `.tmp`) are ignored. Empty folders → None/[] and the
  dashboard shows the onboarding card pointing at `data/holdings/`.
- `app/server.py` and `app/refresh.py` switch from hardcoded
  `DATA/"holdings.xlsx"` / `DATA/"advisory.xlsx"` to these resolvers; the
  resolved holdings path's mtime keeps feeding the existing cache key and
  freshness line. Onboarding copy updated to the new ritual.

## 4. One-shot refresh (`python -m app.refresh`)

Extends the existing `run_refresh` into the single "load everything" step, in
order, each stage guarded (a failure never aborts the rest):
1. Resolve newest holdings + advisory (report filenames + file dates).
2. `mapping.ensure_map` (existing cache behavior).
3. Live quotes: holdings symbols + watchlist symbols + `MARKET_METRIC_SYMBOLS`.
4. Warm price history for the default 6M overview chart.
5. `goal.refresh_security_meta` (existing).
6. `news.fetch_all` (existing).
7. `holdings_ledger.record_snapshot` + `last_refresh` state (existing).

Returns/prints a **freshness report** (also reused by the dashboard's existing
freshness lines): holdings file name + file date + rows parsed + rows skipped,
advisory file name, watchlist TXTs imported, live-price coverage n/m, news
items stored, snapshot written. Loud warnings: holdings file older than 10
days; skipped > 10% of rows ("incomplete export — ask ICICI for a full
download"); zero live prices (offline).

## 5. Daily start

- **`PROMPT_DAILY_START.md`** (root): the exact prompt the owner pastes into a
  Claude Code session opened on this folder. It instructs Claude to: run
  `python -m app.refresh` (via the venv), read the freshness report, explain it
  to the owner in plain English (including the warnings), start the dashboard
  (`start-dashboard.ps1` / `Start Dashboard.command` logic) and give the URL,
  and — when the owner says "I updated the data folder" — do the same flow.
- **`Daily Start.command`** (mac) + **`daily-start.ps1`** (Windows): refresh →
  launch server → open browser. Mirrors the prompt without Claude.
- `CLAUDE.md`: mechanism documented (drop-box rules, refresh stages,
  watchlist_cli) + playbook entries ("I updated the data folder", "holdings
  look stale", "owner pastes a watchlist screenshot → read the symbols,
  normalise to EXCHANGE:SYMBOL, run `python -m app.watchlist_cli import …`,
  confirm the count"). Telegram references removed.
- `README-SIR.md`: rewritten as the 3-step ritual (download → drop into the
  matching `data/` subfolder → paste the daily prompt or double-click Daily
  Start). `README.md` roadmap updated (Telegram line removed; Phase 4 = this
  wave). `GOOGLE_DRIVE_HANDOFF.md` + `prepare-drive-handoff.ps1` updated for
  the new folders (handoff includes `data/holdings|advisory|watchlists`
  structure, excludes `docs/`).

## 6. Out of scope

Telegram/push (removed permanently), cron/Task Scheduler automation, UI/UX
polish pass (separate upcoming wave), multi-broker ingestion.

## 7. Error handling

- Refresh stages independently guarded; report lists per-stage failures as
  warnings, never a stack trace.
- Unreadable/corrupt dropped Excel → that file is skipped with a named warning
  and the next-newest file is used; dashboard keeps rendering last-good data.
- No matching files anywhere → onboarding card with the drop-box path.

## 8. Testing

- `tests/test_datafiles.py`: newest-wins across subfolder+flat, tmp-file
  exclusion, empty → None, corrupt-newest falls back to next-newest (via
  parse attempt in refresh). `watchlist_cli` import test (symbols added,
  bad input → non-zero exit + message, idempotent re-run reports skipped).
- `tests/test_refresh.py`: extended — all network mocked; asserts stage
  ordering tolerance (one stage raising doesn't stop others), report fields,
  warning triggers (old file date, high skip ratio).
- Route smoke: onboarding card shows new path copy when data empty; suite
  (122) stays green; no-CDN test untouched.
- Manual E2E: drop the real Excels into the new folders, run
  `python -m app.refresh`, confirm report; start dashboard; walk pages.
