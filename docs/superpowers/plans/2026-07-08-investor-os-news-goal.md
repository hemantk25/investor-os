# Investor OS — News Engine, 3-Part Brief, News Page, Goal Tracker: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the approved spec `docs/superpowers/specs/2026-07-08-investor-os-news-goal-design.md`: a Python news engine (RSS/Yahoo → SQLite, real links), the restructured 3-part Morning Brief with a Python-computed impact table, a News page with market tabs, a Goal tracker page driven by `data/goal.json` (₹20 Cr / 2031 / 16% / ₹5L SIP / 40-40-20 bands), the manual-vs-Excel dedupe fix, and the nav reorder (Profile out of nav).

**Architecture:** Follow the established pattern exactly: pure logic modules (`app/news.py`, `app/goal.py`) + storage in the existing SQLite (`app/storage.py` schema), thin routes in `app/server.py`, Jinja templates matching the Stitch design, view-model functions in `app/view_models.py`, all network calls best-effort with caches, pages never fetch inline on GET. `claude -p` (Sir's subscription) only summarizes fetched headlines.

**Tech Stack:** existing (Flask/Jinja/openpyxl/yfinance/requests/markdown) + `feedparser>=6`. Tailwind rebuild via `bash build-css.sh` after template changes.

## Global Constraints

- **No real data in git** (`/data/`, `/briefs/`, `/profile/` gitignored). No CDN/external assets in served templates (`tests/test_no_cdn.py` must stay green; external article `href` links are allowed — they are links, not assets).
- Pages render instantly from SQLite; **network fetches only in refresh flows/buttons, never inline on page GET**. All fetchers: timeouts + try/except → skip; freshness stamps in UI.
- Nav order (7): Overview `/` · Holdings `/holdings` · Watchlist `/watchlist` · Morning Brief `/brief` · News `/news` · Rebalance `/rebalance` · Goal `/goal`. `/profile` route stays but is NOT in nav (linked from Goal page).
- Money in Indian format via existing `portfolio.fmt_inr/fmt_short/fmt_pct`.
- Existing 56 tests stay green throughout. TDD for all new logic. Data dir override `INVESTOR_OS_DATA` respected everywhere (tests use tmp dirs).
- Markets enum: `India|US|UAE|Canada|Global`. News caps: 10 items/holding feed, 25/market feed, top-40 holdings by value, prune >14 days beyond newest 500, dedupe `sha1(url)`.
- Goal defaults (auto-seeded `data/goal.json`): target_value 200000000, target_date "2031-07-31", expected_cagr_pct 16.0, sip_monthly 500000, bands 40/40/20, small_cap_max_pct 20, cap_large_min_cr 100000, cap_mid_min_cr 33000. Baseline auto-fills once from the All-members total.
- Commit after every task.

## Interfaces (single source of truth)

```python
# app/news.py
MARKETS = ["India", "US", "UAE", "Canada", "Global"]
def market_feed_url(market: str) -> str            # Google News RSS w/ locale
def holding_feed_url(name: str) -> str             # '"<name>" NSE', IN locale
def normalize_entries(parsed, market: str, isin: str | None, holding_name: str | None) -> list[dict]
    # feedparser result -> [{title,url,publisher,published_at,market,isin,holding_name}]
def save_items(data_dir: Path, items: list[dict]) -> int          # INSERT OR IGNORE, returns inserted
def fetch_all(data_dir: Path, pf) -> dict                         # {"holdings": n, "markets": n}
def load_items(data_dir: Path, market: str | None = None, mine: bool = False,
               within_hours: int | None = None, limit: int = 50) -> list[dict]
def prune(data_dir: Path) -> int
def last_fetched(data_dir: Path) -> str | None                    # ISO or None

# app/goal.py
def load_goal(data_dir: Path, current_total: float | None = None) -> dict   # seeds file+baseline
def required_value(goal: dict, on_date: date) -> float
def required_series(goal: dict, upto: date, points: int = 60) -> list[tuple[str, float]]
def implied_cagr(goal: dict, current_value: float, today: date) -> float | None  # None = unreachable(>100%)
def classify_caps(cons_positions, meta: dict[str, dict], goal: dict) -> dict
    # {"large": {...pct,value}, "mid":…, "small":…, "unclassified":…, "small_breach": bool}
def compliance(cons_positions, meta: dict[str, dict]) -> list[dict]
    # [{"rule": "No commodities", "ok": bool, "detail": "…names…"}]
def refresh_security_meta(data_dir: Path, pf, ttl_days: int = 7) -> int
def load_security_meta(data_dir: Path) -> dict[str, dict]   # symbol -> {market_cap,sector,industry}

# app/brief.py (changed)
def build_prompt(one_pager, snapshot, today, news_items: list[dict]) -> str   # 3-section contract
def split_brief(md_text: str) -> dict   # {"market": html, "stocks": html, "impact": html} or {"single": html}
def sanitize_links(html: str, allowed_urls: set[str]) -> str
def impact_rows(pf, news_items: list[dict]) -> list[dict]
    # holdings w/ news <48h: {name, headline, url, day_pct, day_impact, value}

# app/charts.py (added)
def dual_paths(actual: list[float], required: list[float], w=1000, h=250) -> dict
    # shared min/max scale -> {"actual_line", "required_line", "area"} (area under actual)

# storage.init_db additions: news_items, security_meta tables (spec §2 schema verbatim)
```

---

### Task 1: News engine (`app/news.py`) + schema + tests

**Files:** Create `app/news.py`, `tests/test_news.py`; Modify `app/storage.py` (add the two spec §2 tables to `init_db`), `requirements.txt` (+`feedparser>=6`).

**Steps (TDD):**
- [ ] Add `feedparser>=6` to requirements.txt; `pip install feedparser` into `.venv`.
- [ ] Write `tests/test_news.py` FIRST, run RED. Tests use an inline RSS XML fixture string parsed with `feedparser.parse(xml_string)` — no network:

```python
RSS = """<?xml version="1.0"?><rss version="2.0"><channel><title>t</title>
<item><title>Reliance wins big order</title><link>https://example.com/a1</link>
<source url="https://ex.com">Mint</source><pubDate>Tue, 07 Jul 2026 04:00:00 GMT</pubDate></item>
<item><title>Dup story</title><link>https://example.com/a1</link></item>
<item><title>Nifty ends higher</title><link>https://example.com/a2</link></item>
</channel></rss>"""
```
  - `test_normalize_entries`: feedparser.parse(RSS) → normalize(market="India", isin="INE002A01018", holding_name="Reliance Industries") → 3 dicts with title/url/publisher("Mint" for first)/published_at ISO/market/isin.
  - `test_save_dedupes_by_url` (tmp_path): save 3 normalized items → returns 2 (same url deduped); saving again → 0.
  - `test_load_filters`: after save, `load_items(market="India")` returns items newest-first; `load_items(mine=True)` returns only isin-tagged; `within_hours=1` with old published_at still matches on fetched_at (filter on `fetched_at` for recency guarantees).
  - `test_prune_keeps_recent`: insert 3 items with fetched_at 20 days old (direct SQL) + 1 fresh → prune → old gone.
  - `test_feed_urls`: `market_feed_url("US")` contains `gl=US`; `holding_feed_url("Tata Power")` contains `%22Tata+Power%22` and `ceid=IN`.
- [ ] Implement `app/storage.py` schema additions (spec §2 SQL verbatim) and `app/news.py`:

```python
LOCALES = {"India": ("en-IN","IN","IN:en"), "US": ("en-US","US","US:en"),
           "UAE": ("en-AE","AE","AE:en"), "Canada": ("en-CA","CA","CA:en"),
           "Global": ("en-US","US","US:en")}
QUERIES = {"India": "Nifty OR Sensex OR Indian stock market",
           "US": "US stock market OR S&P 500 OR Nasdaq",
           "UAE": "UAE stocks OR DFM OR ADX", "Canada": "TSX OR Canadian stock market",
           "Global": "global markets"}
def market_feed_url(market):
    hl, gl, ceid = LOCALES[market]
    return ("https://news.google.com/rss/search?q=" + quote_plus(QUERIES[market])
            + f"&hl={hl}&gl={gl}&ceid={quote_plus(ceid)}")
def holding_feed_url(name):
    return ("https://news.google.com/rss/search?q=" + quote_plus(f'"{name}" NSE')
            + "&hl=en-IN&gl=IN&ceid=" + quote_plus("IN:en"))
```
  `normalize_entries`: publisher from `entry.get("source",{}).get("title")`; published_at from `entry.get("published_parsed")` → ISO via `datetime(*pp[:6]).isoformat()` else None. `save_items`: `INSERT OR IGNORE` on `url_hash=sha1(url.encode()).hexdigest()`, fetched_at=storage.now_iso(). `fetch_all(data_dir, pf)`: markets loop (25 cap) + top-40 consolidated holdings by value (10 cap each; also try `yfinance.Ticker(sym+".NS").news` mapping fields `title/link or content.canonicalUrl.url/publisher` inside try/except) — every feed in try/except with `socket.setdefaulttimeout(10)` guard, then `prune`. `load_items`: WHERE clauses per args, ORDER BY COALESCE(published_at, fetched_at) DESC LIMIT. `prune`: DELETE WHERE fetched_at < now-14d AND id NOT IN (SELECT id ORDER BY fetched_at DESC LIMIT 500). `last_fetched`: MAX(fetched_at).
- [ ] GREEN + full suite. Commit `feat(app): news engine — rss/yahoo fetchers, sqlite store`.

---

### Task 2: News page + nav reorder + icons

**Files:** Create `app/templates/news.html`; Modify `app/templates/base.html` (nav), `app/templates/_icons.html` (+`globe`, `target` line-SVGs), `app/server.py` (routes `/news`, POST `/news/refresh`), `app/view_models.py` (`news_ctx`), `tests/test_routes.py` (news + nav tests).

**Steps:**
- [ ] RED: route tests — `/news` 200 with tab links for all 5 markets + All; `/news?market=India` 200; `/news?mine=1` 200; POST `/news/refresh` redirects; nav asserts on `/`: "Morning Brief" appears BEFORE "News" which is BEFORE "Rebalance" in the HTML; "Investor Profile" NOT in the sidebar nav (but `/profile` still 200).
- [ ] `view_models.news_ctx(data_dir, market, mine)` → `{"items":[{title,url,publisher,ago,holding_name}], "market": market or "All", "mine": mine, "markets": ["All"]+news.MARKETS, "fetched": human ts or None}`. `ago` helper: "2h ago"/"3d ago" from published_at/fetched_at.
- [ ] `server.py`:
```python
@app.route("/news")
def news_page():
    member = _member_arg()
    ctx = vm.news_ctx(DATA, request.args.get("market"), request.args.get("mine") == "1")
    pf = load_portfolio()
    ctx.update(vm.common(pf, "news", member) if pf else _empty("news", "News"))
    ctx["page"] = "News"; ctx["empty"] = False
    return render_template("news.html", **ctx)

@app.route("/news/refresh", methods=["POST"])
def news_refresh():
    from app import news as nmod
    nmod.fetch_all(DATA, load_portfolio())
    return redirect(url_for("news_page"))
```
- [ ] `news.html`: extends base; tab row (same pill pattern as rebalance tabs) linking `?market=<m>` (+`&mine=1` preserved), "Mentions your holdings" chip toggling `mine`; freshness line + Refresh button form; headline cards list — title as `<a href target="_blank" rel="noopener">`, publisher · ago muted, holding chip when tagged; empty state: "No news stored yet — click Refresh news."
- [ ] base.html nav_items → 7 entries with icons: overview/dashboard, holdings/wallet, watchlist/bell, brief/news, news/globe, rebalance/rebalance, goal/target (goal route exists Task 5 — nav added now; `/goal` placeholder route added in server.py returning base with "Coming soon" body so nav isn't a dead link). Remove profile entry. Add `globe` + `target` SVGs to `_icons.html`.
- [ ] GREEN; `bash build-css.sh`; full suite. Commit `feat(app): news page, nav reorder, profile out of nav`.

---

### Task 3: Morning Brief restructure

**Files:** Modify `app/brief.py`, `app/templates/brief.html`, `app/server.py` (`/brief` context), `app/view_models.py` (brief_ctx additions), `tests/test_brief.py`.

**Steps:**
- [ ] RED tests: `test_prompt_includes_news_and_contract` (prompt contains "## MARKET BRIEF", "## MY STOCKS", "## IMPACT NOTES", the article url, and "ONLY" citation instruction); `test_split_brief_three_sections` (markdown with the three H2s → dict with 3 html values); `test_split_brief_legacy` (no markers → {"single": html}); `test_sanitize_links_strips_unknown` (html with allowed+unknown `<a>` → unknown replaced by its inner text); `test_impact_rows` (fixture pf + fake news item tagged to ALPHA isin, fetched now → one row with day_pct 2.0 and day_impact == value − value/1.02).
- [ ] Implement in `brief.py`:
  - `build_prompt(one_pager, snapshot, today, news_items)` — existing body + a `NEWS (cite ONLY these urls as markdown links):` block listing up to 30 items as `- [id] title — publisher — url — holding:<name or ->`, and the exact output contract: three sections with those exact H2 headings; MARKET BRIEF = market-moving stories for this India-heavy book, 2–3 lines each + link; MY STOCKS = news about held stocks + link each; IMPACT NOTES = 2–3 lines interpreting measured moves, NO invented numbers.
  - `split_brief(md)` — split on `^## ` headings via regex, map heading-contains MARKET/STOCKS/IMPACT → keys via `markdown.markdown(...)`; else `{"single": ...}`.
  - `sanitize_links(html, allowed)` — `re.sub(r'<a\s[^>]*href="([^"]+)"[^>]*>(.*?)</a>', lambda m: m.group(0) if m.group(1) in allowed else m.group(2), html)`.
  - `impact_rows(pf, news_items)` — newest item per isin (within_hours=48 items passed in), join `pf.consolidated()` by isin, day_pct not None → `{name, headline, url, publisher, day_pct, day_impact, value}` sorted by |day_impact| desc.
  - `generate_brief` passes `news.load_items(base_dir_data, within_hours=48, limit=30)` into the prompt (import inside function; data dir = the app's DATA — pass as arg `generate_brief(pf, base_dir, data_dir)`).
- [ ] `view_models.brief_ctx` → also return `sections` (split_brief of chosen md, sanitized against DB urls ∪ () ), `impact` rows, drop the newsletter block. `server.py /brief` passes `data_dir`. `brief.html`: three cards (Market Brief / My Stocks / Impact) — impact card = Python table (holding · headline link · day% colored · ₹ impact · position value) THEN Claude's IMPACT NOTES html; single-section fallback renders one card; keep Generate button/error/claude-hint; DELETE the Weekly Newsletter card.
- [ ] GREEN; rebuild CSS; full suite. Commit `feat(app): 3-part morning brief with real-link contract + measured impact table`.

---

### Task 4: Goal engine (`app/goal.py`) + security meta

**Files:** Create `app/goal.py`, `tests/test_goal.py`; Modify `app/refresh.py` (call `goal.refresh_security_meta`).

**Steps:**
- [ ] RED tests (pure math, exact numbers):
  - `test_seed_and_baseline(tmp_path)`: `load_goal(tmp, current_total=48_000_000)` creates file with defaults + baseline_value 48000000, baseline_date today; second call with different total does NOT change baseline.
  - `test_required_value_no_time`: baseline day → required == baseline.
  - `test_required_value_one_year`: V0=1e8, SIP=500000, cagr=16 → after 12 months `required == 1e8*1.16 + 500000*(((1.16)-1)/r)` computed with r=(1.16)**(1/12)-1 (assert within ₹1).
  - `test_implied_cagr_roundtrip`: goal target set so that exactly 16% is needed → implied within ±0.2pp; already-past-target → 0.0; absurd target in 1 month → None.
  - `test_classify_caps`: three fake cons positions with meta caps 2e12 (₹2L Cr → large), 5e11 (mid), 1e11 (small); bands output pcts sum≈100 (of classified), `small_breach` True when small >20%; missing meta → "unclassified".
  - `test_compliance_flags_commodity`: meta industry "Copper & Mining" → rule "No commodities" ok=False with name in detail; clean set → ok=True. Crypto rule always ok=True unless industry/sector contains "crypto".
- [ ] Implement per Interfaces. Key code:
```python
def _monthly(rate_annual): return (1 + rate_annual) ** (1/12) - 1
def required_value(goal, on_date):
    v0, t0 = goal["baseline_value"], date.fromisoformat(goal["baseline_date"])
    m = max(0.0, (on_date - t0).days / 30.4375)
    r = _monthly(goal["expected_cagr_pct"] / 100)
    sip = goal["sip_monthly"]
    return v0 * (1 + r) ** m + (sip * (((1 + r) ** m - 1) / r) if r else sip * m)
def implied_cagr(goal, current_value, today):
    target, td = goal["target_value"], date.fromisoformat(goal["target_date"])
    n = (td - today).days / 30.4375
    if n <= 0: return None
    def fv(x):
        r = _monthly(x)
        return current_value * (1 + r) ** n + (goal["sip_monthly"] * (((1 + r) ** n - 1) / r) if r else goal["sip_monthly"] * n)
    if fv(0.0) >= target: return 0.0
    lo, hi = 0.0, 1.0
    if fv(hi) < target: return None
    for _ in range(60):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if fv(mid) < target else (lo, mid)
    return round(hi * 100, 1)
```
  `classify_caps`: thresholds `goal["cap_large_min_cr"]*1e7`, `cap_mid_min_cr*1e7` against `meta[sym]["market_cap"]`. `refresh_security_meta`: for consolidated nse_symbols missing/stale in security_meta (7d TTL), `yf.Ticker(sym+".NS").info` in try/except, store marketCap/sector/industry; cap 25 lookups per run. `load_security_meta` reads table into dict. Wire `goal.refresh_security_meta(data_dir, pf)` into `refresh.run_refresh` (try/except, count in result) and add `news.fetch_all(data_dir, pf)` there too (spec §2 wiring) if not already done in Task 1/2.
- [ ] GREEN; full suite. Commit `feat(app): goal engine — required path, implied cagr, cap bands, compliance`.

---

### Task 5: Goal page

**Files:** Create `app/templates/goal.html`; Modify `app/server.py` (replace `/goal` placeholder), `app/view_models.py` (`goal_ctx`), `app/charts.py` (`dual_paths`), `tests/test_charts.py` (+dual), `tests/test_routes.py` (+goal), `tests/test_view_models.py` (+goal_ctx).

**Steps:**
- [ ] RED: `test_dual_paths_shared_scale` (actual [100,200], required [150,250] → both paths start "M"; scale shared so actual's 200 maps lower y than required's 250); `goal_ctx` test with fixture pf + tmp goal.json → kpis list len 4, bands dict, chart dict, compliance list; route test `/goal` 200 contains "₹20" or "Goal".
- [ ] `charts.dual_paths`: combined lo/hi over both series; reuse the point-mapping from `area_path`; return actual line+area and required line (dashed styling applied in template via stroke-dasharray).
- [ ] `view_models.goal_ctx(pf, data_dir, base_dir)`:
  - `goal = goal.load_goal(data_dir, current_total=pf.totals().total_value)`
  - actual series: `portfolio_snapshots` member='All' ordered by date (SQL via storage.connect); if <2 rows → fallback `charts.portfolio_series(pf, None, prices.fetch_history(...['6mo']))`... **no network on GET**: fallback uses cached history only if present in `prices._hist_cache`, else single-point flat series `[current, current]`.
  - required series: `goal.required_series(goal, today)` sampled same length as actual (interpolate by date range endpoints).
  - kpis: Current (`fmt_short`), Required today, Ahead/Behind (₹ + %, tone up/down), Implied CAGR needed (or "On track"/"Review target"). Bands: classify_caps vs bands_pct; compliance list; `profile_link=True`.
- [ ] `goal.html`: KPI cards (reuse `.mcard`-equivalent Stitch card classes from overview.html), dual-line SVG chart card (teal actual + dashed slate required, small legend), bands card (three rows: label, actual% bar vs target% marker, red flag on small breach + unclassified note), compliance chips (green ✓/red ✗ + detail), link row "View your full rules →" `/profile`.
- [ ] GREEN; rebuild CSS; full suite. Commit `feat(app): goal tracker page`.

---

### Task 6: Manual/Excel dedupe fix

**Files:** Modify `app/holdings_ledger.py` (`apply_events`), `app/view_models.py`+`app/templates/holdings.html` (manual list "in Excel now" notice), `tests/test_holdings_ledger.py`.

**Steps:**
- [ ] RED: `test_manual_suppressed_when_excel_has_same` — pr with Excel holding (isin X, member PK) + manual event same isin+member → apply_events result contains only the Excel lot; `pr.skipped` gains a message containing "suppressed"; different member manual survives.
- [ ] Implement: in `apply_events`, build `excel_keys = {(h.isin, h.member) for h in pr.holdings}` (before merging); manual holdings whose `(isin, member)` ∈ excel_keys are skipped with `pr.skipped.append(f"manual entry #{id} ({name}) suppressed — now present in the ICICI Excel")`; mark surviving manual dicts in `list_manual`-driven UI: `holdings` view-model flags `in_excel` per manual item, template shows a muted "in Excel now — this manual entry is ignored" badge.
- [ ] GREEN; full suite. Commit `fix(app): suppress manual holdings duplicated by the weekly Excel`.

---

### Task 7: Wiring, docs, QA, push

**Files:** Modify `app/refresh.py` (ensure news+secmeta wired + counts), `CLAUDE.md`, `README-SIR.md`, `README.md`; rebuild `app/static/app.css`.

**Steps:**
- [ ] Confirm `run_refresh` returns counts incl. `news_items`, `security_meta`; `tests/test_refresh.py` updated accordingly (mock fetchers).
- [ ] Docs: CLAUDE.md — new modules map (news.py, goal.py), goal.json knobs, nav list, playbook entries ("change the goal target" → edit data/goal.json; "news feels stale" → click Refresh news or run `python -m app.refresh`); README-SIR — one line each for News/Goal pages; README — feature list refresh.
- [ ] `bash build-css.sh`; full suite green; `git grep -n "cdn\." app/templates` clean.
- [ ] Manual E2E on real data: start app, walk all 7 pages, click News refresh (real fetch), generate one real brief, verify Goal seeds `data/goal.json` with live baseline and renders bands (some Unclassified expected until secmeta fills).
- [ ] Update `.superpowers/sdd/progress.md`; commit `chore(app): wiring, docs, css for news+goal wave`; **push to origin**.

## Self-Review

- Spec coverage: §1 nav→T2 · §2 engine/schema/wiring→T1,T7 · §3 brief→T3 · §4 news page→T2 · §5 goal→T4,T5 · §6 dedupe→T6 · §7 errors→in each task's constraints · §9 tests→per task. No gaps.
- Placeholders: none — code given for all non-template logic; templates specified by binding + existing-pattern reference (consistent with prior plan's accepted convention).
- Type consistency: `news.load_items(...within_hours, mine)` used by T2 ctx + T3 impact; `goal.load_goal(data_dir, current_total)` used in T5 ctx; `dual_paths` consumed only by goal.html; `generate_brief(pf, base_dir, data_dir)` signature change confined to T3 (server.py updated same task).
```
