# Investor OS — Drop-in Data Folders + Daily Start: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement spec `docs/superpowers/specs/2026-07-13-investor-os-dropin-data-daily-start-design.md`: newest-file-wins drop boxes (`data/holdings/`, `data/advisory/`), a watchlist screenshot→CLI import path, a one-shot `python -m app.refresh` with a plain-English freshness report, daily-start prompt + launchers, root cleanup, and Telegram de-scope.

**Architecture:** New tiny `app/datafiles.py` owns path resolution + corrupt-fallback parsing; `app/server.py` and `app/refresh.py` consume it instead of hardcoded paths. `app/watchlist_cli.py` wraps `watchlist.import_text` with CLI-level dedupe. `run_refresh` becomes the orchestrator with per-stage guards and a report dict that `main()` prints as prose. Docs/launchers wrap it.

**Tech Stack:** existing (Flask, openpyxl, yfinance, feedparser, pytest). No new dependencies.

## Global Constraints

- Newest-mtime `*.xlsx` wins in `data/holdings/` (flat `data/holdings.xlsx` competes on mtime — back-compat); same for `data/advisory/` + flat `advisory.xlsx`. `~$*` and `*.tmp` ignored.
- No watchlist file drop-box; watchlist updates only via UI or `python -m app.watchlist_cli import "<SYMS>" --market … --category … --group …`.
- Refresh stages independently guarded — one failure never aborts the rest; report `warnings` list, never stack traces. Warnings: holdings file >10 days old; skipped >10% of rows; zero live prices.
- Pages still never fetch on GET; refresh is the only orchestration point.
- No real data in git (`/data/`, `/briefs/`, `/profile/` gitignored). Suite (122) stays green; TDD for new logic. `INVESTOR_OS_DATA` override respected.
- Telegram references removed from README/CLAUDE.md (no code exists).
- Commit after every task; push at the end.

## Interfaces

```python
# app/datafiles.py (new)
def holdings_candidates(data_dir: Path) -> list[Path]     # newest-first
def advisory_candidates(data_dir: Path) -> list[Path]
def latest_holdings(data_dir: Path) -> Path | None
def latest_advisory(data_dir: Path) -> Path | None
def resolve_and_parse_holdings(data_dir) -> tuple[ParseResult | None, Path | None, list[str]]
    # tries candidates newest-first; unparseable file -> warning + next; (None,None,warns) if none

# app/refresh.py (rewritten run_refresh)
def run_refresh(data_dir=None, pf=None) -> dict  # report:
    # {holdings_file, holdings_date, rows, skipped, advisory_file,
    #  watchlist_quotes, history_warmed, security_meta, news_items,
    #  portfolio_snapshots, warnings: [str]}

# app/watchlist_cli.py (new)
def main(argv: list[str] | None = None) -> int   # 0 ok, 2 bad input
```

---

### Task 1: `app/datafiles.py` + server/refresh path wiring

**Files:** Create `app/datafiles.py`, `tests/test_datafiles.py`; Modify `app/server.py` (drop `HOLDINGS` const; resolve per request; advisory path; onboarding/manual-disabled copy), `app/refresh.py` (`load_portfolio_for_refresh` uses resolver), `app/templates/overview.html` (onboarding card copy → `data/holdings/`).

- [ ] **Step 1: tests/test_datafiles.py (RED first)**

```python
import time
from pathlib import Path
from app import datafiles


def _touch(p: Path, mtime_offset: float = 0):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"x")
    t = time.time() + mtime_offset
    import os
    os.utime(p, (t, t))


def test_newest_wins_across_subfolder_and_flat(tmp_path):
    _touch(tmp_path / "holdings.xlsx", -100)          # flat, older
    _touch(tmp_path / "holdings" / "july.xlsx", -50)
    _touch(tmp_path / "holdings" / "latest.xlsx", 0)  # newest
    assert datafiles.latest_holdings(tmp_path).name == "latest.xlsx"
    names = [p.name for p in datafiles.holdings_candidates(tmp_path)]
    assert names == ["latest.xlsx", "july.xlsx", "holdings.xlsx"]


def test_tmp_and_lock_files_ignored(tmp_path):
    _touch(tmp_path / "holdings" / "~$open.xlsx", 10)
    _touch(tmp_path / "holdings" / "real.xlsx", 0)
    _touch(tmp_path / "holdings" / "part.tmp", 20)
    assert datafiles.latest_holdings(tmp_path).name == "real.xlsx"


def test_empty_returns_none(tmp_path):
    assert datafiles.latest_holdings(tmp_path) is None
    assert datafiles.latest_advisory(tmp_path) is None


def test_resolve_and_parse_falls_back_on_corrupt(tmp_path):
    import shutil
    fix = Path(__file__).parent / "fixtures" / "sample-holdings.xlsx"
    shutil.copy(fix, tmp_path / "holdings" / "good.xlsx") if (tmp_path / "holdings").mkdir(parents=True, exist_ok=True) is None else None
    _touch(tmp_path / "holdings" / "corrupt.xlsx", 100)   # newest but not a real xlsx
    pr, path, warns = datafiles.resolve_and_parse_holdings(tmp_path)
    assert path.name == "good.xlsx" and pr is not None and len(pr.holdings) > 0
    assert any("corrupt.xlsx" in w for w in warns)


def test_resolve_none_when_nothing(tmp_path):
    pr, path, warns = datafiles.resolve_and_parse_holdings(tmp_path)
    assert pr is None and path is None and warns == []
```
(Fix the copy line to plain: `(tmp_path/"holdings").mkdir(parents=True, exist_ok=True); shutil.copy(fix, tmp_path/"holdings"/"good.xlsx")` — two statements, and give good.xlsx an OLDER mtime than corrupt.xlsx.)

- [ ] **Step 2: RED** — `.\.venv\Scripts\python -m pytest tests\test_datafiles.py -q` → ModuleNotFoundError.

- [ ] **Step 3: app/datafiles.py**

```python
from __future__ import annotations
from pathlib import Path

_EXCLUDE_PREFIX = "~$"
_EXCLUDE_SUFFIX = ".tmp"


def _candidates(data_dir: Path, subdir: str, flat_name: str) -> list[Path]:
    out: list[Path] = []
    sub = Path(data_dir) / subdir
    if sub.is_dir():
        out.extend(p for p in sub.glob("*.xlsx") if p.is_file())
    flat = Path(data_dir) / flat_name
    if flat.is_file():
        out.append(flat)
    out = [p for p in out
           if not p.name.startswith(_EXCLUDE_PREFIX) and not p.name.endswith(_EXCLUDE_SUFFIX)]
    return sorted(out, key=lambda p: p.stat().st_mtime, reverse=True)


def holdings_candidates(data_dir) -> list[Path]:
    return _candidates(Path(data_dir), "holdings", "holdings.xlsx")


def advisory_candidates(data_dir) -> list[Path]:
    return _candidates(Path(data_dir), "advisory", "advisory.xlsx")


def latest_holdings(data_dir) -> Path | None:
    c = holdings_candidates(data_dir)
    return c[0] if c else None


def latest_advisory(data_dir) -> Path | None:
    c = advisory_candidates(data_dir)
    return c[0] if c else None


def resolve_and_parse_holdings(data_dir):
    """Newest-first; skip unparseable files with a warning. -> (pr, path, warnings)"""
    from app import parser
    warnings: list[str] = []
    for path in holdings_candidates(data_dir):
        try:
            return parser.parse_holdings(path), path, warnings
        except Exception as exc:
            warnings.append(f"could not read {path.name} ({type(exc).__name__}) — trying next file")
    return None, None, warnings
```

- [ ] **Step 4: Wire server.py** — remove `HOLDINGS = DATA / "holdings.xlsx"`; `load_portfolio()` uses `pr, path, _ = datafiles.resolve_and_parse_holdings(DATA)`; return None when pr None (rest unchanged: isin_map/quotes/extras/build). Advisory route: `advp = datafiles.latest_advisory(DATA)` + `if advp is None:` friendly card (update copy: "Drop the advisory report into `data/advisory/`"). Manual-disabled response strings: "Replace data/holdings.xlsx" → "Drop the new ICICI export into data/holdings/". Overview onboarding card copy likewise.
- [ ] **Step 5: Wire refresh.py `load_portfolio_for_refresh`** to the same resolver (keep returning None when nothing).
- [ ] **Step 6: GREEN + full suite** (existing route tests that copy fixture to `tmp/holdings.xlsx` still pass via flat back-compat). Commit `feat(app): drop-in data folders with newest-file-wins resolution`.

---

### Task 2: One-shot refresh with freshness report

**Files:** Modify `app/refresh.py` (rewrite `run_refresh` + `main`), `tests/test_refresh.py` (extend).

- [ ] **Step 1: RED tests** (all network mocked via monkeypatch on `prices.fetch_market_quotes`, `prices.fetch_quotes`, `prices.fetch_history`, `news.fetch_all`, `goal.refresh_security_meta`):
  - `test_report_fields(tmp_path,...)`: fixture xlsx at `tmp/holdings/latest.xlsx` → report has holdings_file=="latest.xlsx", rows>0, skipped>=0, watchlist_quotes int, history_warmed bool/int, news_items int, portfolio_snapshots>0, warnings list.
  - `test_stage_failure_does_not_abort`: make `news.fetch_all` raise → run_refresh still returns; news_items==0; other counts intact; a warning mentions news.
  - `test_warning_old_file`: fixture with mtime set 20 days back → warnings contain "old"/"days".
  - `test_warning_high_skip_ratio`: monkeypatch `datafiles.resolve_and_parse_holdings` to return a ParseResult with 2 holdings + 100 skipped → warning mentions "incomplete".
- [ ] **Step 2: Implement run_refresh** (order per spec §4): resolve+parse holdings (capture file name/date/rows/skipped + resolver warnings) → build pf (isin map, quotes over holdings) → watchlist quotes (existing block) → `prices.fetch_history` warm for consolidated nse symbols period "6mo" (guarded; history_warmed = number of symbols warmed) → `goal.refresh_security_meta` (guarded) → `news.fetch_all` (guarded) → snapshot + last_refresh. Compute warnings: file age >10d (`(now - mtime).days`), skip ratio >10% (`skipped/(rows+skipped)`), zero live quotes when holdings exist. Advisory: `datafiles.latest_advisory` name in report (no parsing needed here). `main()` prints:
```
Investor OS refresh — <today>
Holdings : latest.xlsx (12 Jul 2026) · 146 rows · 0 skipped
Advisory : Portfolio Advisory Report.xlsx
Prices   : 141/146 live · history warmed (6M)
News     : 38 items stored
Snapshot : written (All + 4 members)
Warnings : none   (or bulleted list)
```
- [ ] **Step 3: GREEN + full suite.** Commit `feat(app): one-shot refresh with plain-english freshness report`.

---

### Task 3: watchlist_cli (screenshot import path)

**Files:** Create `app/watchlist_cli.py`, `tests/test_watchlist_cli.py`.

- [ ] **Step 1: RED tests**
```python
from app import watchlist, watchlist_cli


def test_import_adds_and_dedupes(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("INVESTOR_OS_DATA", str(tmp_path))
    rc = watchlist_cli.main(["import", "NSE:RELIANCE,NASDAQ:MSFT",
                             "--market", "India", "--category", "Stocks", "--group", "Custom"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "2" in out
    symbols = {i["symbol"] for i in watchlist.load(tmp_path)}
    assert {"NSE:RELIANCE", "NASDAQ:MSFT"} <= symbols
    before = len(watchlist.load(tmp_path))
    rc2 = watchlist_cli.main(["import", "NSE:RELIANCE", "--market", "India"])
    assert rc2 == 0 and len(watchlist.load(tmp_path)) == before   # no duplicate
    assert "skipped" in capsys.readouterr().out.lower()


def test_import_empty_is_error(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("INVESTOR_OS_DATA", str(tmp_path))
    assert watchlist_cli.main(["import", "   "]) == 2
```
- [ ] **Step 2: Implement** — argparse with `import` subcommand (`symbols` positional, `--market Global --category Stocks --group Custom --member All`); resolve data dir from `INVESTOR_OS_DATA` else `BASE/"data"`; dedupe at CLI level: `existing = {i["symbol"] for i in watchlist.load(data_dir)}`, split incoming on commas, normalise upper/strip, partition into new vs skipped; call `watchlist.import_text(data_dir, ",".join(new), market=…, group=…, member=…, category=…)` only for new; print `Imported N symbols (M skipped as already present).`; empty input → print usage hint, return 2. `if __name__ == "__main__": raise SystemExit(main())`.
- [ ] **Step 3: GREEN + full suite.** Commit `feat(app): watchlist_cli for screenshot-based imports`.

---

### Task 4: Cleanup, prompts, launchers, docs, E2E, push

**Files:** git mv reference files; Create `PROMPT_DAILY_START.md`, `daily-start.ps1`, `Daily Start.command`; Modify `CLAUDE.md`, `README-SIR.md`, `README.md`, `GOOGLE_DRIVE_HANDOFF.md`, `prepare-drive-handoff.ps1`, `setup.ps1`, `setup.sh`, `PROMPT_FOR_CLAUDE_DASHBOARD.md` (data-folder mentions).

- [ ] **Step 1: Moves**
```bash
mkdir -p docs/reference
git mv AI-Advisor-Build-Guide.pdf "ASSET INVESTOR PROMPT.md" "ASSET INVESTOR PROMPT.md.docx" cowork-investor-os-system-prompt.md cowork-investor-os-system-prompt.md.docx docs/reference/
git mv demo docs/demo
```
Local data (not git): `mkdir data/holdings data/advisory`; copy the two report_data Excels into them (`Current Portfolio…` → data/holdings/, `Portfolio Advisory…` → data/advisory/); delete flat `data/holdings.xlsx`/`advisory.xlsx` copies and `report_data/` (local only; gitignore entries stay). Update `setup.ps1`/`setup.sh` to `mkdir data/holdings data/advisory briefs profile`.
- [ ] **Step 2: PROMPT_DAILY_START.md** (verbatim):
```markdown
# Daily Start — paste this into Claude Code (opened on this folder)

Start my Investor OS dashboard. Do these steps in order and don't skip the report:

1. Run the refresh: `./.venv/bin/python -m app.refresh` (Windows:
   `.\.venv\Scripts\python -m app.refresh`). If the venv is missing, run
   `bash setup.sh` (Windows: `./setup.ps1`) first.
2. Read the freshness report it prints and explain it to me in plain English:
   which holdings file was used and how old it is, how many rows loaded and
   skipped, live-price coverage, how many news items came in, and EVERY
   warning — especially "incomplete export" or "file is old". If the holdings
   file is old or incomplete, remind me to download a fresh full export from
   ICICI Direct and drop it into data/holdings/ (no renaming needed).
3. Start the dashboard: `./.venv/bin/python -m flask --app app.server run
   --port 8555` (Windows: `.\.venv\Scripts\python -m flask --app app.server
   run --port 8555`), run it in the background, then give me the link
   http://127.0.0.1:8555 and a one-line summary of my portfolio today.

If I say "I updated the data folder", do the same three steps again.
If I paste a screenshot of a TradingView watchlist, read the symbols from the
image, convert them to EXCHANGE:SYMBOL form, and run:
`python -m app.watchlist_cli import "SYM1,SYM2,…" --market <India|US|UAE|Canada|Global> --category Stocks --group Custom`
then tell me how many were added.
```
- [ ] **Step 3: Launchers** — `daily-start.ps1`:
```powershell
if (-not (Test-Path .venv)) { python -m venv .venv; .\.venv\Scripts\pip install -r requirements.txt }
.\.venv\Scripts\python -m app.refresh
Start-Process "http://127.0.0.1:8555"
.\.venv\Scripts\python -m flask --app app.server run --port 8555
```
`Daily Start.command` (chmod +x via `git update-index --chmod=+x`):
```bash
#!/bin/bash
cd "$(dirname "$0")"
if [ ! -d .venv ]; then bash setup.sh; fi
./.venv/bin/python -m app.refresh
( sleep 2; open http://127.0.0.1:8555 ) &
./.venv/bin/python -m flask --app app.server run --port 8555
```
- [ ] **Step 4: Docs** — CLAUDE.md: replace the holdings/advisory path lines with the drop-box rules (newest-wins, no renaming), document refresh stages + report, add playbook entries ("I updated the data folder" → run refresh, explain report, restart dashboard; "watchlist screenshot" → extract symbols → watchlist_cli; "holdings look stale" → check data/holdings newest file date), delete Telegram/Phase-4 mentions. README-SIR: 3-step ritual + the watchlist screenshot step ("this is the one extra thing to learn"). README: roadmap Phase 4 = drop-in data + daily start (done), Telegram line removed. GOOGLE_DRIVE_HANDOFF + prepare-drive-handoff.ps1: include `PROMPT_DAILY_START.md`, `daily-start.ps1`, `Daily Start.command`, `data/holdings|advisory` folders; exclude `docs/`. PROMPT_FOR_CLAUDE_DASHBOARD.md: update file paths (data/holdings/ etc.).
- [ ] **Step 5: E2E + push** — `.\.venv\Scripts\python -m pytest -q` all green; run `python -m app.refresh` for real (network on) → sane report; start server, spot-check `/`, `/holdings`, `/goal`, `/news`; `git status` shows no data files; commit `feat(app): daily-start flow, drop-in folders live, root cleanup, telegram de-scoped`; `git push origin phase3-dashboard`.

## Self-Review
- Spec coverage: §2 moves→T4 · §3 resolvers+CLI→T1,T3 · §4 refresh→T2 · §5 prompt/launchers/docs→T4 · §7 error handling→T1 (fallback) + T2 (guards) · §8 tests→T1–T3 + suite in T4. No gaps.
- Placeholders: none; all code/copy literal (Task-1 Step-1 note fixes its own fixture-copy line explicitly).
- Type consistency: `resolve_and_parse_holdings` tuple shape used identically in server (T1 Step 4) and refresh (T2); `watchlist_cli.main(argv)->int` matches tests; report keys in T2 match the Interfaces block.
```
