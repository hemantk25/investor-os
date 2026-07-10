# Design — Investor OS: News Engine, 3-Part Morning Brief, News Page, Goal Tracker

**Date:** 2026-07-08
**Status:** Approved in discussion; pending user spec review
**Builds on:** the Flask/Jinja Stitch frontend (all 5 pages live), the Codex wave
(SQLite storage `data/investor_os.sqlite`, watchlist boards, manual holdings
ledger, refresh runner `app/refresh.py`), 56 tests green at `bd7a844`.

## 1. Decisions (locked with Hemant)

- **Nav becomes 7 items, in order:** Overview · Holdings · Watchlist ·
  Morning Brief · News · Rebalance · Goal. **Investor Profile leaves the nav**;
  route `/profile` stays and is linked from the Goal page ("View your full
  rules →"). The one-pager file remains the engine input for briefs + goals.
- **News source = RSS/Yahoo feeds fetched by Python** (real links, no AI, no
  keys): Google News RSS + yfinance per-ticker news → SQLite. Claude (via
  `claude -p`, Sir's subscription) only *summarizes* fetched headlines for the
  Morning Brief and may cite only the links we pass it.
- **Goal scope = whole family portfolio** (All members, the dashboard's
  consolidated equity+extras total). Target from Paresh's real one-pager
  (now at `profile/one-pager.md`, gitignored): **₹20 Cr by 2031-07**, hurdle
  **16% CAGR**, **₹5L/month SIP**, bands **40/40/20 large/mid/small**,
  small-cap hard cap **20%**. Baseline = portfolio value the day the Goal
  page first runs (stored, editable).

## 2. News engine (`app/news.py` + storage)

**Schema (add to `storage.init_db`):**
```sql
CREATE TABLE IF NOT EXISTS news_items (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  url_hash TEXT NOT NULL UNIQUE,        -- sha1(url)
  title TEXT NOT NULL, url TEXT NOT NULL,
  publisher TEXT, published_at TEXT,    -- ISO, best-effort from feed
  market TEXT NOT NULL,                 -- India|US|UAE|Canada|Global
  isin TEXT,                            -- set when fetched for a holding
  holding_name TEXT,                    -- display name of that holding
  fetched_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS security_meta (
  symbol TEXT PRIMARY KEY,              -- NSE symbol
  market_cap REAL, sector TEXT, industry TEXT,
  fetched_at TEXT NOT NULL              -- TTL 7 days
);
```

**Fetchers (dependency: `feedparser>=6`):**
- *Holdings track:* for each consolidated holding (top 40 by value): Google
  News RSS query `"<holding name> NSE"` (hl=en-IN&gl=IN&ceid=IN:en), plus
  `yfinance.Ticker(sym+".NS").news`. Items tagged `isin` + `holding_name`,
  market="India" (or the ticker's market later).
- *Markets track:* one query per market tab — India ("Nifty OR Sensex OR
  Indian stock market"), US ("US stock market OR S&P 500 OR Nasdaq"),
  UAE ("UAE stocks OR DFM OR ADX"), Canada ("TSX OR Canadian stock market"),
  Global ("global markets") — each with the matching hl/gl/ceid locale.
- Each feed capped (10 items/holding, 25/market), 10s timeout per feed,
  failures silently skipped (best-effort). Dedupe on `url_hash` (INSERT OR
  IGNORE). Prune: delete items older than 14 days beyond the newest 500.
- `fetch_all(data_dir, pf) -> dict` counts; wired into `refresh.run_refresh`
  and a POST `/news/refresh` button. **Never fetched inline on page GET** —
  pages always render from SQLite instantly with a freshness stamp.

## 3. Morning Brief — restructure + move

- Nav position: after Watchlist, before News.
- `brief.py` prompt now receives: (a) the one-pager, (b) portfolio snapshot,
  (c) the last-48h news items (id, title, publisher, url, holding tag) — and
  the instruction: *write exactly three markdown sections with these exact
  headings, citing ONLY the provided article urls as markdown links:*
  `## MARKET BRIEF` (top market-moving stories relevant to this India-heavy
  book; 2–3 lines each + link) · `## MY STOCKS` (news specifically about his
  holdings: results, management, deals; link each) · `## IMPACT NOTES`
  (2–3 lines interpreting the measured impacts, no invented numbers).
- Output saved as `briefs/YYYY-MM-DD.md` (unchanged persistence). The brief
  page splits the markdown on the three `## ` markers into three cards; a
  brief without markers renders as one card (backward compatible with old
  briefs).
- **Impact table is computed in Python, not by the LLM:** holdings that have
  a news item in the last 48h → columns: holding · headline (linked) ·
  day % (live quote) · ₹ day impact on the position
  (`value − value/(1+day_pct/100)`) · position value. Rendered above
  Claude's IMPACT NOTES card.
- The "Weekly Newsletter (sample)" card is removed from this page
  (superseded by the News page).

## 4. News page (`/news`, template `news.html`)

- Tabs: **All · India · US · UAE · Canada · Global** (`?market=` param,
  server-side, same pattern as rebalance tabs) + a **"Mentions your
  holdings"** chip (`?mine=1`) filtering to `isin IS NOT NULL`.
- Headline cards: title (external link, `target=_blank rel=noopener`),
  publisher, time-ago, holding chip when tagged. Sorted newest first,
  capped 50 per view. Freshness stamp + "Refresh news" button (POST
  `/news/refresh` → runs fetch_all → redirect back).
- Zero AI involvement; page renders instantly from SQLite.

## 5. Goal page (`/goal`, template `goal.html`, `app/goal.py`)

**Config `data/goal.json`** (auto-seeded on first run; Sir edits by hand or
via Claude Code):
```json
{ "target_value": 200000000, "target_date": "2031-07-31",
  "expected_cagr_pct": 16.0, "sip_monthly": 500000,
  "baseline_value": null, "baseline_date": null,
  "bands_pct": {"large": 40, "mid": 40, "small": 20},
  "small_cap_max_pct": 20,
  "cap_large_min_cr": 100000, "cap_mid_min_cr": 33000 }
```
`baseline_value/date` auto-fill with the current All-members total on first
load, then stay fixed (editable in the file).

**Computations (`app/goal.py`, pure functions):**
- *Required path:* monthly rate `r=(1+cagr)^(1/12)−1`; for month m since
  baseline: `required(m) = V0·(1+r)^m + SIP·((1+r)^m − 1)/r`.
- *Ahead/behind:* current value vs `required(months_elapsed)` in ₹ and %.
- *Implied CAGR from today:* bisection solve of
  `V_now·(1+x)^(n/12) + SIP·annuity(x, n) = target` over remaining months n.
- *Actual curve:* daily rows from `portfolio_snapshots` (member='All');
  when sparse (<2 rows), fall back to the reconstructed price-history series
  used by Overview.
- *Cap classification:* per equity holding, `security_meta.market_cap`
  (yfinance `Ticker.info["marketCap"]`, fetched lazily, cached 7 days,
  best-effort). `large ≥ cap_large_min_cr`, `mid ≥ cap_mid_min_cr`, else
  small; unknown → "Unclassified" bucket shown separately, never guessed.
- *Compliance:* small-cap % vs 20% cap; commodity/crypto detection via
  `security_meta.sector/industry` keyword list (mining, metals, oil, gas,
  coal, commodity); zero-findings renders a green chip, hits render red
  with the holding names.

**Render:** KPI cards (Current · Required today · Ahead/Behind · Implied
CAGR needed) → progress chart (actual teal line vs required dashed line,
inline SVG via `charts.area_path` extended with a second path) → allocation
vs bands (three band bars: actual% vs target% + small-cap breach flag) →
compliance chips → "View your full rules →" link to `/profile`.

## 6. Folded-in fix: manual/Excel dedupe

In `holdings_ledger.apply_events`: when a manual event's `(isin, member)`
matches an Excel-sourced holding in the same parse, **suppress the manual
lot** and append `"manual entry #<id> (<name>) suppressed — now present in
the ICICI Excel"` to `pr.skipped` (surfaces in the existing skipped-rows
panel + a notice on the Holdings manual list marking the row "in Excel now").

## 7. Error handling

- All network fetchers best-effort with timeouts; pages never block on the
  network and never show stack traces; freshness stamps everywhere.
- `claude -p` failures keep the existing BriefError card with the fix hint.
- Missing `goal.json` → auto-seed; unparseable → friendly card naming the file.

## 8. Out of scope (this cycle)

- Telegram push (Phase 4), scheduled cron (refresh runner stays manual/CLI),
  UI/UX polish pass (explicitly deferred by Hemant until after features),
  per-member goals, dividend/XIRR analytics, paid news APIs.

## 9. Testing

- Unit: news normalization/dedupe/prune + market tagging (feedparser mocked
  with local fixture XML); goal math (required path, implied CAGR bisection,
  classification thresholds, band drift) — pure functions, exact numbers;
  brief markdown splitter (3 sections, legacy fallback); dedupe fix
  (manual+Excel same ISIN+member → suppressed + skipped note).
- Routes: `/news` (tabs, mine=1), `/goal` (seeds goal.json in tmp dir),
  `/news/refresh` redirect; nav order + profile absence asserted on one page.
- Existing 56 tests stay green; CSS rebuilt after template work;
  `test_no_cdn.py` still passes (new templates: no external assets besides
  article `href`s, which are links not assets).

## 10. Risks

- Google News RSS shape/rate changes → feedparser + per-feed try/except;
  page still renders stored items.
- yfinance `.info` is slow per ticker → lazy + 7-day cache + "Unclassified"
  bucket; never blocks page render (fetch happens in refresh, not GET).
- LLM citing wrong links → prompt restricts to provided urls; renderer only
  autolinks urls present in the DB set (belt-and-braces check).
- Sparse snapshots early on → chart falls back to reconstructed series until
  the snapshot table accumulates.
